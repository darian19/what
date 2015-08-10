# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""
This module implements the the Model Swapper Interface, including the utilities
that are required for it. It's designed to work hand-in-hand with the Model
Swapper layers so as to avoid unnecessary decoding/re-incoded between the
sub-layers.

App layer submits a request batch::

    from datetime import datetime
    from htmengine.model_swapper.model_swapper_interface import (
        ModelCommand, ModelInputRow, ModelSwapperInterface)

    # Define the model
    with ModelSwapperInterface() as swapper:
      swapper.defineModel(modelID="0123456789abcdef", args=dict(...),
                          commandID="abcdcb0123454321")

    # After receiving confirmation that model was created successfully, start
    # feeding data to the model
    with ModelSwapperInterface() as swapper:
      requests = [
        ModelInputRow(rowID="foo", data=[1, 2, datetime.utcnow()),
        ModelInputRow(rowID="bar", data=[9, 54, datetime.utcnow())]
      swapper.submitRequests(modelID="foofar", requests=requests)

App layer reads results::

    from htmengine.model_swapper.model_swapper_interface import (
        ModelCommandResult, ModelInferenceResult, ModelSwapperInterface)

    with ModelSwapperInterface() as swapper:
      with swapper.consumeResults() as consumer

        for batch in consumer:
          for r in batch.objects:
            try:
              if isinstance(r, ModelCommandResult):
                processCommandResult(batch.modelID, r)
              elif isinstance(r, ModelInferenceResult):
                processInferenceResult(batch.modelID, r)
              else:
                <throw a fit>
            except model_swapper_interface.ModelNotFound:
              <the model was likely deleted (via web interface?)>

            batch.ack()
"""

from collections import namedtuple
import datetime
import json
import time
import types
import uuid
import weakref

from htmengine import exceptions as engine_exceptions
from htmengine.model_swapper import ModelSwapperConfig

from nta.utils.date_time_utils import epochFromNaiveUTCDatetime
from nta.utils import message_bus_connector
from nta.utils.message_bus_connector import MessageBusConnector

from htmengine import htmengine_logging

_MODULE_NAME = "htmengine.model_swapper.model_swapper_interface"



def _getLogger():
  return htmengine_logging.getExtendedLogger(_MODULE_NAME)



class ModelNotFound(engine_exceptions.HTMEngineError):
  """ The requested model was not found (already deleted?) """
  pass



class _ModelRequestResultBase(object):
  """ Common reusable methods for Model request and result classes, such as
  ModelCommand and ModelInferenceResult.

  NOTE: this class assumes that command and result classes register themselves
  with our factory via our __register__ decorator and also define the
  following class members:
    __slots__: sequence that contains names of the instance attributes that need
      to be serialized/deserialized by our default implementations of
      __getstate__ and __setstate__ (in addition to the standard use of
      __slots__)
    __STATE_SIGNATURE__: A short string representing the class used in
      serialization and deserialization
  """

  # Map of state signatures to the corresponding subclasses populated by our
  # __register__ decorator and used by our __createFromState__ class
  # method (NOTE that the builtin __subclasses__ member only registers immediate
  # subclasses)
  __factoryClassMap = weakref.WeakValueDictionary()

  def __eq__(self, other):
    """ Equality operator; helpful in mock tests; e.g., assert_called_once_with
    """
    if other.__class__ is not self.__class__:
      raise NotImplementedError

    return self.__getstate__() == other.__getstate__()


  @classmethod
  def __register__(cls, clientCls):
    """ Decorator for registering commands and results with the factory; this
    information is used by our __createFromState__ class method
    """
    assert clientCls.__STATE_SIGNATURE__ not in cls.__factoryClassMap, (
      repr(clientCls.__STATE_SIGNATURE__))
    cls.__factoryClassMap[clientCls.__STATE_SIGNATURE__] = clientCls
    return clientCls


  @classmethod
  def __createFromState__(cls, clientState):
    """ Construct the client instance from clientState sequence; the first
    element of clientState must be its __STATE_SIGNATURE__ value. Used by
    BatchPackager.unmarshall()
    """
    obj = object.__new__(cls.__factoryClassMap[clientState[0]])
    obj.__setstate__(clientState)
    return obj


  def __getstate__(self):
    """ Return state suitable for serializing; used by BatchPackager. """
    state = [self.__STATE_SIGNATURE__]
    state.extend(getattr(self, slot) for slot in self.__class__.__slots__)
    return state


  def __setstate__(self, state):
    """ Initialize instance members from given state that was produced by
    __getstate__; used by our __createFromState__ class method.
    """
    assert state[0] == self.__STATE_SIGNATURE__, repr(state)
    attributes = self.__class__.__slots__
    assert len(state) == 1 + len(attributes), repr([len(state), state])
    for i, name in enumerate(attributes):
      setattr(self, name, state[i+1])



@_ModelRequestResultBase.__register__
class ModelCommand(_ModelRequestResultBase):
  """ Model command container

  Instance attributes:
    commandID: command id of the command
    method: method string of the command
    args: args of the command (args); dict or None
  """

  # NOTE: also used by serialization/deserialization in our base class
  __slots__ = ("commandID", "method", "args")

  __STATE_SIGNATURE__ = "mc"


  def __init__(self, commandID, method, args=None):
    """ Initialize from command id, method, and an optional args dict

      :param commandID: command id of the command
      :param method: method string of the command
      :param args: args of the command (args); dict or None
    """
    assert isinstance(method, types.StringTypes)
    assert isinstance(args, (dict, None.__class__)), (
      "Expected dict instance as args, but got: " + repr(args))

    self.commandID = commandID
    self.method = method
    self.args = args


  def __repr__(self):
    return "%s<commandID=%s, method=%s>" % (
      self.__class__.__name__, self.commandID, self.method)



@_ModelRequestResultBase.__register__
class ModelCommandResult(_ModelRequestResultBase):
  """ Model command result container

  Instance attributes:
    commandID: command id of the corresponding command
    method: method string of the corresponding command
    status: integer; 0 (zero) means success, otherwise
      it's an error code from htmengine.htmengineerno
    args: successful response parameters if status is 0 (dict or None), None
      otherwise
    errorMessage: error message if status is non-zero, None otherwise
  """

  # NOTE: also used by serialization/deserialization in our base class
  __slots__ = ("commandID", "method", "status", "args", "errorMessage")

  __STATE_SIGNATURE__ = "mcR"


  def __init__(self, commandID, method, status, args=None, errorMessage=None):
    """ __init__(commandID, method, status, args|errorMessage)

      :param commandID: command id of the corresponding command
      :param method: method string of the corresponding command
      :param status: integer; 0 (zero) means success, otherwise it's an error
        code from htmengine.htmengineerno
      :param args: successful response parameters if status is 0 (dict or None),
        omit otherwise
      :param errorMessage: error message if status is non-zero, omit otherwise
    """
    assert isinstance(method, types.StringTypes)
    assert isinstance(status, (int, long)), (
      "Expected int or long as status, but got: " + repr(status))
    if status == 0:
      assert isinstance(args, (dict, None.__class__)), (
        "Expected dict instance as args with status=0, but got: " + repr(args))
      assert errorMessage is None, (
        "Unexpected errorMessage with status=0: " + repr(errorMessage))
    else:
      assert isinstance(errorMessage, types.StringTypes), (
        "Unexpected errorMessage type with non-zero status: " +
        repr(errorMessage))
      assert args is None, ("Unexpected args with non-zero status: " +
                            repr(dict(status=status, args=args)))

    self.commandID = commandID
    self.method = method
    self.status = status
    self.args = args
    self.errorMessage = errorMessage


  def __repr__(self):
    return "%s<commandID=%s, method=%s, status=%s%s>" % (
      self.__class__.__name__, self.commandID, self.method, self.status,
      "" if self.status == 0 else ", errorMsg=%s" % (self.errorMessage,))



@_ModelRequestResultBase.__register__
class ModelInputRow(_ModelRequestResultBase):
  """ Model input row container

  Instance attributes:
    rowID: row id of the row
    data = sequence of field values
  """

  # NOTE: also used by serialization/deserialization in our base class
  __slots__ = ("rowID", "data")

  __STATE_SIGNATURE__ = "i"


  def __init__(self, rowID, data):
    """ Initialize from rowID and data. NOTE: The instance assumes ownership of
    the passed arguments.

    :param rowID: row id of the row
    :param data: sequence of field values (non-empty list or tuple);
      numeric field values: are populated in their native numeric format (
      integer or float).

      datetime field values: must be populated as datetime.datetime instances.
    """
    assert isinstance(data, (list, tuple)), (
      "Expected list or tuple as data, but got: " + repr(data))
    assert data, "Expected non-empty sequence as data, but got: " + repr(data)

    self.rowID = rowID
    self.data = data


  def __repr__(self):
    return "%s<rowID=%s, data=%r>" % (
      self.__class__.__name__, self.rowID, self.data)


  def __getstate__(self):
    """ Return state suitable for serializing; used by BatchPackager. NOTE: we
    implement our own serializer because of special handling of datetime.
    """
    encodedData = []
    datetimeIndexes = []
    for i, item in enumerate(self.data):
      if isinstance(item, datetime.datetime):
        item = self._encodeDateTime(item)
        datetimeIndexes.append(i)

      encodedData.append(item)
    return [self.__STATE_SIGNATURE__, self.rowID, encodedData, datetimeIndexes]


  def __setstate__(self, state):
    """ Initialize instance members from given state that was produced by
    __getstate__; used by BatchPackager. NOTE: we implement our own
    initialization because of special handling of datetime.
    """
    assert len(state) == 4, repr([len(state), state])
    requestType, self.rowID, data, datetimeIndexes = state
    assert requestType == self.__STATE_SIGNATURE__, repr(requestType)

    if  datetimeIndexes:
      for i in datetimeIndexes:
        data[i] = self._decodeDateTime(data[i])

    self.data = data


  @classmethod
  def _encodeDateTime(cls, dateTime):
    """ Encode a datetime instance for serialization. This encoder is non-lossy.

    :param dateTime: a datetime.datetime instance to encode

    :returns: an opaque datetime state value suitable for use in
      ModelInputRow.__getstate__().
    """
    return [int(epochFromNaiveUTCDatetime(dateTime)), dateTime.microsecond]


  @classmethod
  def _decodeDateTime(cls, state):
    """ Decode the the opaque datetime state value into a datetime.datetime
    instance; this is the inverse of ModelInputRow._encodeDateTime. This decoder
    is non-lossy.

    :param state: the opaque datetime state value produced by
      ModelInputRow._encodeDateTime()

    :returns: the corresponding datetime.datetime instance suitable for use in
      ModelInputRow.__setstate__().
    """
    seconds, microseconds = state
    return (datetime.datetime.utcfromtimestamp(seconds) +
            datetime.timedelta(microseconds=microseconds))



@_ModelRequestResultBase.__register__
class ModelInferenceResult(_ModelRequestResultBase):
  """ Model inference result container """

  # NOTE: also used by serialization/deserialization in our base class
  __slots__ = ("rowID", "status", "anomalyScore", "errorMessage")

  __STATE_SIGNATURE__ = "iR"


  def __init__(self, rowID, status, anomalyScore=None, errorMessage=None):
    """ __init__(rowID, status, anomalyScore|errorMessage)

    :param rowID: rowID id of the corresponding input record
    :param status: integer; 0 (zero) means success, otherwise it's an error code
      from htmengine.htmengineerno
    :param anomalyScore: the Anomaly Score floating point value if status is 0
      (zero), omit otherwise
    :param errorMessage: error message if status is non-zero, omit otherwise
    """
    assert isinstance(status, (int, long)), (
      "Expected int or long as status, but got: " + repr(status))

    if status == 0:
      assert isinstance(anomalyScore, (int, long, float)), (
        "Expected numeric anomaly score with status=0, but got: " +
        repr(anomalyScore))
      assert errorMessage is None, (
        "Unexpected errorMessage with status=0: " + repr(errorMessage))
    else:
      assert isinstance(errorMessage, types.StringTypes), (
        "Unexpected errorMessage type with non-zero status: " +
        repr(errorMessage))
      assert anomalyScore is None, (
        "Unexpected anomaly score with non-zero status: " + repr(errorMessage))

    self.rowID = rowID
    self.status = status
    self.anomalyScore = anomalyScore
    self.errorMessage = errorMessage


  def __repr__(self):
    return "%s<rowID=%s, status=%s%s>" % (
      self.__class__.__name__, self.rowID, self.status,
      (", anomalyScore=%s" % (self.anomalyScore,) if self.status == 0
       else ", errorMsg=%s" % (self.errorMessage,)))



class BatchPackager(object):
  """ Serializer for a batch of request or result items """


  @classmethod
  def marshal(cls, batch):
    """ Marshal a batch of requests or results into a string, preserving their
    order.

    The returned string will NOT contain newlines (this makes it convenient to
    write newline-separated batches to stdout and readline them from stdin
    without further escaping of the data).

    :param batch: a sequence of requests or results (instances of ModelCommand,
      ModelInputRow)

    :returns: a string representation of the given batch, preserving order.
      The returned string will not contain newlines.

    Example::

        requestBatch = [
          ModelInputRow(rowID="foo", row=[1, 2, "Sep 21 02:24:21 UTC 2013"),
          ModelInputRow(rowID="bar", row=[9, 54, "Sep 21 02:24:38 UTC 2013"),
        ]
        batchState = BatchPackager.marshal(batch=requestBatch)

    And similar for a result batch.
    """
    return json.dumps([o.__getstate__() for o in batch])


  @classmethod
  def unmarshal(cls, batchState):
    """ Unmarshal the given batchState string into a sequence of request or
    result instances (e.g., ModelCommand, ModelInputRow), preserving the
    original order
    """
    return tuple(_ModelRequestResultBase.__createFromState__(itemState)
                 for itemState in json.loads(batchState))



class RequestMessagePackager(object):
  """ Serializer for a request message """

  _UnmarshalResultSet = namedtuple("_UnmarshalResultSet", "batchID batchState")

  @classmethod
  def marshal(cls, batchID, batchState):
    """ Combine the batchID and the batch state string into a message string

    :param batchID: uuid of the batch; string; must not contain newline
      characters
    :param batchState: serialized request batch as returned body
      BatchPackager.marshal()


    Example:

        requestBatch = [
          ModelInputRow(rowID="foo", row=[1, 2, "Sep 21 02:24:21 UTC 2013"),
          ModelInputRow(rowID="bar", row=[9, 54, "Sep 21 02:24:38 UTC 2013"),
        ]
        batchState = BatchPackager.marshal(batch=requestBatch)
        msg = RequestMessagePackager.marshal(batchID="foobaruuid",
                                             batchState=batchState)
    """
    return batchID + "\n" + batchState


  @classmethod
  def unmarshal(cls, msg):
    """ Unmarshal a request message string

    :returns: a RequestMessagePackager._UnmarshalResultSet instance

    Example:
      r = RequestMessagePackager.unmarshal(msg)
      processRequests(r.batchID, BatchPackager.unmarshal(r.batchState))
    """
    batchID, batchState = msg.split("\n", 1)
    return cls._UnmarshalResultSet(batchID=batchID, batchState=batchState)



class ResultMessagePackager(object):
  """ Serializer for a result message """

  _UnmarshalResultSet = namedtuple("_UnmarshalResultSet", "modelID batchState")

  @classmethod
  def marshal(cls, modelID, batchState):
    """ Combine the modelID and the batch state string into a message string

    :param modelID: id of the model; string; must not contain newline characters
    :param batchState: serialized result batch as returned by
      BatchPackager.marshal()


    Example:

        resultBatch = [
          ModelCommandResult(commandID="abc", method="testMethod", status=0,
            args={'key1': 4098, 'key2': 4139}),
          ModelInferenceResult(rowID="foo", status=0, anomalyScore=1),
          ModelInferenceResult(rowID="bar", status=0, anomalyScore=2)
        ]
        msg = ResultMessagePackager.marshal(
          modelID="foobar",
          batchState=BatchPackager.marshal(batch=resultBatch))
    """
    return modelID + "\n" + batchState


  @classmethod
  def unmarshal(cls, msg):
    """ Split a message string into a tuple of (modelID, batchState), where
    modelID is the modelID and batchState are as defined in our "marshal"
    method.

    Example:
      r = ResultMessagePackager.unmarshal(msg)
      processResults(r.modelID, BatchPackager.unmarshal(r.batchState))
    """
    modelID, batchState = msg.split("\n", 1)
    return cls._UnmarshalResultSet(modelID=modelID, batchState=batchState)



class ModelSwapperInterface(object):
  """
  This is the interface class to connect the application layer to the Model
  Swapper.
  """

  #_INPUT_Q_OPTION_NAME = "input_queue"

  #_INPUT_Q_ENV_VAR = ModelSwapperConfig.getEnvVarOverrideName(
  #  configName=ModelSwapperConfig.CONFIG_NAME,
  #  section=_CONFIG_SECTION,
  #  option=_INPUT_Q_OPTION_NAME)
  #""" For testing: environment variable for overriding input queue name """

  _CONFIG_SECTION = "interface_bus"

  _RESULTS_Q_OPTION_NAME = "results_queue"

  # For testing: environment variable for overriding output queue name
  _RESULTS_Q_ENV_VAR = ModelSwapperConfig()._getEnvVarOverrideName(
    configName=ModelSwapperConfig.CONFIG_NAME,
    section=_CONFIG_SECTION,
    option=_RESULTS_Q_OPTION_NAME)

  _SCHEDULER_NOTIFICATION_Q_OPTION_NAME = "scheduler_notification_queue"

  _MODEL_INPUT_Q_PREFIX_OPTION_NAME = "model_input_queue_prefix"


  def __init__(self):
    """
    Initialize the ModelSwapperInterface. This uses a lazy loading of the input
    and output queues with no pre-meditation.
    """
    self._logger = _getLogger()

    config = ModelSwapperConfig()

    self._resultsQueueName = config.get(
      self._CONFIG_SECTION, self._RESULTS_Q_OPTION_NAME)

    # The name of a model's input message queue is the concatenation of this
    # prefix and the modelID
    self._modelInputQueueNamePrefix = config.get(
      self._CONFIG_SECTION, self._MODEL_INPUT_Q_PREFIX_OPTION_NAME)

    self._schedulerNotificationQueueName = config.get(
      self._CONFIG_SECTION, self._SCHEDULER_NOTIFICATION_Q_OPTION_NAME)

    # Message bus connector
    self._bus = MessageBusConnector()

    # Outstanding request and/or response consumer instances
    self._consumers = []


  def __enter__(self):
    """ Context Manager protocol method. Allows a ModelSwapperInterface instance
    to be used in a "with" statement for automatic clean-up

    Parameters:
    ------------------------------------------------------------------------
    retval:     self.
    """
    return self


  def __exit__(self, _excType, _excVal, _excTb):
    """ Context Manager protocol method. Allows a ModelSwapperInterface instance
    to be used in a "with" statement for automatic cleanup

    :returns: False so as not to suppress the exception, if any
    """
    self.close()
    return False


  def close(self):
    """
    Gracefully close ModelSwapperInterface instance (e.g., tear down
    connections). If this is not called, the underlying connections will
    eventually timeout, but it is good practice to close explicitly.
    """
    if self._consumers:
      self._logger.error(
        "While closing %s, discovered %s unclosed consumers; will "
        "attempt to close them now", self.__class__.__name__,
        len(self._consumers))

      for consumer in tuple(self._consumers):
        consumer.close()

      assert not self._consumers

    try:
      self._bus.close()
    finally:
      self._bus = None


  def _onConsumerClosed(self, consumer):
    """ Called by consumer instance's close() method to remove the consumer from
    our outstanding consumers list
    """
    self._consumers.remove(consumer)


  def _getModelInputQName(self, modelID):
    return self._modelInputQueueNamePrefix + modelID


  def _getModelIDFromInputQName(self, mqName):
    assert mqName.startswith(self._modelInputQueueNamePrefix), (
      "mq=%s doesn't start with %s") % (
      mqName, self._modelInputQueueNamePrefix)

    return mqName[len(self._modelInputQueueNamePrefix):]


  def defineModel(self, modelID, args, commandID):
    """ Initialize model's input message queue and send the "defineModel"
    command. The ModelCommandResult will be delivered asynchronously, along with
    the corresponding commandID and no args, to the process that is consuming
    ModelSwapper results.

    :param modelID: a hex string that uniquely identifies the target model.
    :param args: dict with the following properties:
      "modelConfig": model config dict suitable for passing to OPF
        ModelFactory.create()
      "inferenceArgs": Model inference arguments suitable for passing to
        model.enableInference()
      "inputRecordSchema": a sequence  of nupic.data.fieldmeta.FieldMetaInfo
        instances with field names/types/special as expected by the model and in
        the same order as they will appear in input records. This is needed in
        order to avoid the overhead of passing fields names with each and every
        input record, while permitting the necessary dictionaries to be
        constructed by ModelRunner for input to the OPF Model.
    :param commandID: a numeric or string id to associate with the command and
      result.
    """
    # TODO: validate input args dict against schema

    mqName = self._getModelInputQName(modelID)

    self._bus.createMessageQueue(mqName, durable=True)

    self.submitRequests(modelID,
                        (ModelCommand(commandID, "defineModel", args),))


  def cloneModel(self, modelID, newModelID, commandID):
    """ Initiate cloning of an existing model. Initialize the new
    model's input message queue and send the "cloneModel" command to the source
    model. The ModelCommandResult will be delivered asynchronously, along with
    the corresponding commandID and no args, to the process that is consuming
    ModelSwapper results.

    :param modelID: a hex string that uniquely identifies the existing model.
    :param newModelID: a hex string that uniquely identifies the new model.
    :param commandID: a numeric or string id to associate with the command and
      result.

    :raises: ModelNotFound if the source model's input endpoint doesn't exist
    """
    # Create the model input message queue for the new model
    self._bus.createMessageQueue(self._getModelInputQName(newModelID),
                                 durable=True)

    self.submitRequests(
      modelID,
      (ModelCommand(commandID, "cloneModel", args={"modelID": newModelID}),))


  def deleteModel(self, modelID, commandID):
    """ Submit a request to delete a model. The ModelCommandResult will be
    delivered asynchronously, along with the corresponding commandID and no
    args, to the process that is consuming ModelSwapper results.

    This method is idempotent.

    :param modelID: a hex string that uniquely identifies the target model.
    :param commandID: a numeric or string id to associate with the command and
                      result.
    """
    # First, purge unread input messages for this model, if any, to avoid
    # unnecessary processing before the model is deleted
    mq = self._getModelInputQName(modelID)
    self._logger.info("deleteModel: purging mq=%s before submitting "
                      "deleteModel command for model=%s", mq, modelID)
    try:
      self._bus.purge(mq)
    except message_bus_connector.MessageQueueNotFound:
      # deleteModel is an idempotent operation: assume this exception is
      # due to repeated attempt
      pass
    else:
      try:
        self.submitRequests(modelID, (ModelCommand(commandID, "deleteModel"),))
      except ModelNotFound:
        # deleteModel is an idempotent operation: assume this exception is
        # due to repeated attempt
        pass


  def cleanUpAfterModelDeletion(self, modelID):
    """ For use by Engine's ModelRunner after it deletes a model: clean up
    resources that ModelSwapperInterface created to support the model, such
    as deleting the model's input message queue
    """
    self._bus.deleteMessageQueue(self._getModelInputQName(modelID))


  def modelInputPending(self, modelID):
    """ Check if input requests are pending for a model

    :param modelID: a string that uniquely identifies the target model.

    :returns: True if the model's input queue exists and is non-empty;
              False if the model's input queue is non-empty or doesn't exist
    """
    try:
      return not self._bus.isEmpty(self._getModelInputQName(modelID))
    except message_bus_connector.MessageQueueNotFound:
      return False


  def getModelsWithInputPending(self):
    """ Get model IDs of all models with pending input (non-empty input queues)

    :returns: (possibly empty) sequence of model IDs whose input streams are
      non-empty
    """
    # NOTE: queues may be deleted as we're running through the list, so we need
    # to play it safe
    def safeIsInputPending(mq):
      try:
        return not self._bus.isEmpty(mq)
      except message_bus_connector.MessageQueueNotFound:
        return False

    prefix = self._modelInputQueueNamePrefix
    return tuple(
      self._getModelIDFromInputQName(mq)
      for mq in self._bus.getAllMessageQueues()
      if mq.startswith(prefix) and safeIsInputPending(mq))


  def submitRequests(self, modelID, requests):
    """
    Submit a batch of requests for processing by a model with the given modelID.

    NOTE: it's an error to submit requests for a model after calling
    deleteModel()

    Keyword arguments:
    :param modelID: a string that uniquely identifies the target model.

    :param requests: a sequence of ModelCommand and/or ModelInputRow instances.
      NOTE: To create or delete a model, call the createModel or deleteModel
      method instead of submitting the "defineModel" or "deleteModel" commands.
      Together, the sequence of requests constitutes a request "batch".

    :returns: UUID of the submitted batch (intended for test code only)

    :raises: ModelNotFound if model's input endpoint doesn't exist

    Requests for a specific model will be processed in the submitted order.
    The results will be delivered asynchronously, along with the corresponding
    requestIDs, to the process that is consuming ModelSwapper results.

    NOTE: This assumes retry logic will be handled by the underlying MQ
    implementation.
    """
    batchID = uuid.uuid1().hex
    msg = RequestMessagePackager.marshal(
      batchID=batchID,
      batchState=BatchPackager.marshal(batch=requests))

    mqName = self._getModelInputQName(modelID)
    try:
      self._bus.publish(mqName, msg, persistent=True)
    except message_bus_connector.MessageQueueNotFound as e:
      self._logger.warn(
        "App layer attempted to submit numRequests=%s to model=%s, but its "
        "input queue doesn't exist. Likely a race condition with model "
        "deletion path.", len(requests), modelID)
      raise ModelNotFound(repr(e))
    except:
      self._logger.exception(
        "Failed to publish request batch=%s for model=%s via mq=%s; "
        "msgLen=%s; msgPrefix=%r. NOTE: it's an error to submit requests to a "
        "model after deleting it.", batchID, modelID, mqName, len(msg),
        msg[:32])
      raise

    # Send a notification to Model Scheduler so it will schedule the model
    # for processing input
    try:
      self._bus.publish(self._schedulerNotificationQueueName,
                        json.dumps(modelID), persistent=False)
    except message_bus_connector.MessageQueueNotFound:
      # If it's not fully up yet, its notification queue might not have been
      # created, which is ok
      self._logger.warn(
        "Couldn't send model data notification to Model Scheduler: mq=%s not "
        "found. Model Scheduler service not started or initialized the mq yet?",
        self._schedulerNotificationQueueName)
    return batchID


  def consumeRequests(self, modelID, blocking=True):
    """ Create an instance of the _MessageConsumer iterable for reading model
    requests, a batch at a time. The iterable yields _ConsumedRequestBatch
    instances.

    NOTE: This API is intended for Engine Model Runners.

    :param modelID: a string that uniquely identifies the target model.
    :param blocking: if True, the iterable will block until another batch becomes
      available; if False, the iterable will terminate iteration when no more
      batches are available in the queue. [defaults to True]

    :returns: an instance of model_swapper_interface._MessageConsumer iterable;
      IMPORTANT: the caller is responsible for closing it before closing this
      ModelSwapperInterface instance (hint: use the returned _MessageConsumer
      instance as Context Manager)

    :raises: ModelNotFound if model's input endpoint doesn't exist
            TODO: need tests for consumeRequests with ModelNotFound

    Example:
      with ModelSwapperInterface() as swapper:
        with swapper.consumeRequests(modelID) as consumer:
          for batch in consumer:
            processRequests(batchID=batch.batchID, requests=batch.objects)
            batch.ack()
    """
    mq = self._getModelInputQName(modelID)

    def onQueueNotFound():
      msg = ("Attempt to consume requests from model=%s is impossible because "
             "its input queue doesn't exist. Likely a race condition with "
             "model deletion path.") % (modelID,)
      self._logger.warn(msg)
      raise ModelNotFound(msg)

    consumer = _MessageConsumer(mqName=mq,
                                blocking=blocking,
                                decode=_ConsumedRequestBatch.decodeMessage,
                                swapper=self,
                                bus=self._bus,
                                onQueueNotFound=onQueueNotFound)

    self._consumers.append(consumer)

    return consumer


  def _initResultsMessageQueue(self):
    self._bus.createMessageQueue(self._resultsQueueName, durable=True)


  def submitResults(self, modelID, results):
    """
    Submit a batch of results (used by ModelSwapper layer)

    Keyword arguments:
    :param modelID: a string that uniquely identifies the target model.

    :param results: a sequence of ModelCommandResult and/or ModelInferenceResult
      instances

    NOTE: This assumes retry logic will be handled by the underlying MQ
    implementation.
    """
    msg = ResultMessagePackager.marshal(
      modelID=modelID,
      batchState=BatchPackager.marshal(batch=results))
    try:
      try:
        self._bus.publish(self._resultsQueueName, msg, persistent=True)
      except message_bus_connector.MessageQueueNotFound:
        self._logger.info("submitResults: results mq=%s didn't exist; "
                          "declaring now and re-publishing message",
                          self._resultsQueueName)
        self._initResultsMessageQueue()
        self._bus.publish(self._resultsQueueName, msg, persistent=True)
    except:
      self._logger.exception(
        "submitResults: Failed to publish results from model=%s via mq=%s; "
        "msgLen=%s; msgPrefix=%r", modelID, self._resultsQueueName, len(msg),
        msg[:32])
      raise


  def consumeResults(self):
    """ Create an instance of the _MessageConsumer iterable for reading model
    results, a batch at a time. The iterable yields _ConsumedResultBatch
    instances.

    :returns: an instance of model_swapper_interface._MessageConsumer iterable;
      IMPORTANT: the caller is responsible for closing it before closing this
      ModelSwapperInterface instance (hint: use the returned _MessageConsumer
      instance as Context Manager)

    Example:
      with ModelSwapperInterface() as swapper:
        with swapper.consumeResults() as consumer:
          for batch in consumer:
            processResults(modelID=batch.modelID, results=batch.objects)
            batch.ack()
    """
    consumer = _MessageConsumer(mqName=self._resultsQueueName,
                                blocking=True,
                                decode=_ConsumedResultBatch.decodeMessage,
                                swapper=self,
                                bus=self._bus,
                                onQueueNotFound=self._initResultsMessageQueue)

    self._consumers.append(consumer)

    return consumer


  def initSchedulerNotification(self):
    """ Initialize Model Scheduler's notification message queue; for use by
    Model Scheduler.
    """
    self._bus.createMessageQueue(self._schedulerNotificationQueueName,
                                 durable=False)


  def consumeModelSchedulerNotifications(self):
    """ Create an instance of the _MessageConsumer iterable for reading model
    scheduler notifications. The iterable yields _ConsumedNotification
    instances.

    :returns: an instance of model_swapper_interface._MessageConsumer iterable;
      IMPORTANT: the caller is responsible for closing it before closing this
      ModelSwapperInterface instance (hint: use the returned _MessageConsumer
      instance as Context Manager)

    Example:
      with ModelSwapperInterface() as swapper:
        with swapper.consumeModelSchedulerNotifications() as consumer:
          for notification in consumer:
            processNotification(notification.value)
            notification.ack()
    """
    consumer = _MessageConsumer(mqName=self._schedulerNotificationQueueName,
                                blocking=True,
                                decode=_ConsumedNotification.decodeMessage,
                                swapper=self,
                                bus=self._bus)

    self._consumers.append(consumer)

    return consumer



class _ConsumedRequestBatch(  # pylint: disable=W0232
    namedtuple("_ConsumedRequestBatchBase", "batchID objects ack")):
  """ Container for a consumed request batch

  batchID: UUID of the batch batch
  objects: sequence of request objects (instances of ModelCommand,
    ModelInputRow, etc.)
  ack: function to call to ack the batch: NoneType ack(multiple=False);
    recepient is responsible for ACK'ing each batch in order get more messages
    and also for supporting the "at-least-once" delivery guarantee.
  """


  @classmethod
  def decodeMessage(cls, msg):
    """ Factory method that accepts an instance of
    message_bus_connector._ConsumedMessage and returns an instance of
    _ConsumedRequestBatch that should be yielded by the _MessageConsumer
    iterable

    :param msg: instance of message_bus_connector._ConsumedMessage

    :returns: an instance of _ConsumedRequestBatch that should be yielded by the
      _MessageConsumer iterable
    """
    r = RequestMessagePackager.unmarshal(msg.body)
    return cls(batchID=r.batchID, objects=BatchPackager.unmarshal(r.batchState),
               ack=msg.ack)



class _ConsumedResultBatch(  # pylint: disable=W0232
    namedtuple("_ConsumedResultBatchBase", "modelID objects ack")):
  """ Container for a consumed result batch

  modelID: ID of the model that's responsible for this batch
  objects: sequence of result objects (instances of ModelCommandResult, etc.)
  ack: function to call to ack the batch: NoneType ack(multiple=False);
    recepient is responsible for ACK'ing each batch in order get more messages
    and also for supporting the "at-least-once" delivery guarantee.
  """


  @classmethod
  def decodeMessage(cls, msg):
    """ Factory method that accepts an instance of
    message_bus_connector._ConsumedMessage and returns an instance of
    _ConsumedResultBatch that should be yielded by the _MessageConsumer iterable

    :param msg: instance of message_bus_connector._ConsumedMessage

    :returns: an instance of _ConsumedResultBatch that should be yielded by the
      _MessageConsumer iterable
    """
    r = ResultMessagePackager.unmarshal(msg.body)
    return cls(modelID=r.modelID, objects=BatchPackager.unmarshal(r.batchState),
               ack=msg.ack)



class _ConsumedNotification(  # pylint: disable=W0232
    namedtuple("_ConsumedNotificationBase", "value ack")):
  """ Container for a consumed Model Scheduler notification

  value: notification object
  ack: function to call to ack the message: NoneType ack(multiple=False);
    recepient is responsible for ACK'ing each batch in order get more messages
    and also for supporting the "at-least-once" delivery guarantee.
  """

  @classmethod
  def decodeMessage(cls, msg):
    """ Factory method that accepts an instance of
    message_bus_connector._ConsumedMessage and returns an instance of
      _ConsumedNotification that should be yielded by the _MessageConsumer
      iterable

    :param msg: instance of message_bus_connector._ConsumedMessage

    :returns: value that should be yielded by the _MessageConsumer iterable
    """
    return cls(value=json.loads(msg.body), ack=msg.ack)



class _MessageConsumer(object):
  """ An instance of this class is an iterable that reads messages from a
  specific queue and yields instances of consumer-requested class.
  """

  def __init__(self, mqName, blocking, decode, swapper,
               bus, onQueueNotFound=None):
    """
    :param mqName: the name of the target message queue
    :param blocking: if True, the iterable will block until another batch
      becomes available; if False, the iterable will terminate iteration when no
      more batches are available in the queue.
    :param decode: a callable that accepts an instance of
      message_bus_connector._ConsumedMessage and returns the value that should
      be yielded by the iterable.
    :param swapper: the host ModelSwapperInterface instance
    :param bus: the host ModelSwapperInterface's MessageBusConnector instance
    :param onQueueNotFound: `NoneType onQueueNotFound()` to be called the first
      time an attempt to consume messages from the queue results in
      message_bus_connector.MessageQueueNotFound exception. onQueueNotFound is
      expected to create the queue. After calling onQueueNotFound, the consumer
      will attempt to restart the iterator.
    """
    self._logger = _getLogger()
    self._mqName = mqName
    self._blocking = blocking
    self._decode = decode
    self._swapper = swapper
    self._bus = bus
    self._onQueueNotFound = onQueueNotFound

    self._mqConsumer = self._createMessageQueueConsumer()


  def _createMessageQueueConsumer(self):
    return self._bus.consume(self._mqName, blocking=self._blocking)


  def __enter__(self):
    return self


  def __exit__(self, _excType, _excVal, _excTb):
    self.close()
    return False


  def __iter__(self):
    """ yield an instance of consumer-requested class when a batch becomes
    available
    """
    onQueueNotFoundCalled = False

    while True:
      try:
        for msg in self._mqConsumer:
          yield self._decode(msg)
      except message_bus_connector.MessageQueueNotFound:
        if self._onQueueNotFound is None or onQueueNotFoundCalled:
          raise

        # Take an opportunity to resolve the error and try again
        self._onQueueNotFound()
        onQueueNotFoundCalled = True

        self._mqConsumer.close()
        self._mqConsumer = self._createMessageQueueConsumer()
      else:
        break


  def close(self):
    """ Clean up """
    if self._mqConsumer is None:
      return

    self._swapper._onConsumerClosed(self)  # pylint: disable=W0212
    self._swapper = None

    self._decode = None
    self._bus = None
    self._onQueueNotFound = None

    try:
      self._mqConsumer.close()
    finally:
      self._mqConsumer = None
