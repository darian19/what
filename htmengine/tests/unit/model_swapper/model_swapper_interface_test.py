#!/usr/bin/env python
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
Unit tests for the model_swapper_interface classes
"""

import copy
import datetime
import json
import os
import unittest
import uuid


from mock import patch, Mock

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from htmengine.model_swapper import ModelSwapperConfig
from htmengine.model_swapper import model_swapper_interface
from htmengine.model_swapper.model_swapper_interface import \
  MessageBusConnector, message_bus_connector, \
  ModelCommand, ModelCommandResult, ModelInputRow, ModelInferenceResult, \
  BatchPackager, RequestMessagePackager, ResultMessagePackager, \
  ModelSwapperInterface, _ModelRequestResultBase



# Disable warning: Access to a protected member
# pylint: disable=W0212

# Disable warning: Method could be a function
# pylint: disable=R0201



modelSwapperConfig = ModelSwapperConfig()



class ModelCommandTestCase(unittest.TestCase):
  """
  Unit tests for ModelCommand
  """


  def testModelCommandConstructorNoArgs(self):
    commandID = 1
    method = "defineModel"
    args = None
    command = ModelCommand(commandID=commandID, method=method, args=args)
    self.assertEqual(command.commandID, commandID)
    self.assertEqual(command.method, method)
    self.assertEqual(command.args, args)

    self.assertIn("ModelCommand<", str(command))
    self.assertIn("ModelCommand<", repr(command))


  def testModelCommandConstructorAllParams(self):
    commandID = 1
    method = "defineModel"
    args = {'key1': 4098, 'key2': 4139}
    command = ModelCommand(commandID=commandID, method=method,
                           args=copy.copy(args))
    self.assertEqual(command.commandID, commandID)
    self.assertEqual(command.method, method)
    self.assertEqual(command.args, args)

    self.assertIn("ModelCommand<", str(command))
    self.assertIn("ModelCommand<", repr(command))


  def testModelCommandConstructorInvalidArgs(self):
    commandID = 1
    method = "defineModel"
    args = "None"
    with self.assertRaises(AssertionError) as cm:
      ModelCommand(commandID=commandID, method=method, args=args)
    self.assertIn("Expected dict instance as args", cm.exception.args[0])


  def testModelCommandSerializableState(self):
    commandID = 1
    method = "defineModel"
    args = {'key1': 4098, 'key2': 4139}
    command = ModelCommand(commandID=commandID, method=method,
                           args=copy.copy(args))
    self.assertEqual(command.commandID, commandID)
    self.assertEqual(command.method, method)
    self.assertEqual(command.args, args)

    command2 = _ModelRequestResultBase.__createFromState__(
      command.__getstate__())

    self.assertEqual(command2.commandID, commandID)
    self.assertEqual(command2.method, method)
    self.assertEqual(command2.args, args)

    self.assertIn("ModelCommand<", str(command2))
    self.assertIn("ModelCommand<", repr(command2))



class ModelCommandResultTestCase(unittest.TestCase):
  """
  Unit tests for ModelCommandResult
  """


  def _implTestCreateSuccessfulModelCommandResult(self, args):
    commandID = 1
    method = "testMethod"
    status = 0
    commandResult = ModelCommandResult(commandID=commandID, method=method,
                                       status=status, args=copy.copy(args))
    self.assertEqual(commandResult.commandID, commandID)
    self.assertEqual(commandResult.method, method)
    self.assertEqual(commandResult.status, status)
    self.assertEqual(commandResult.args, args)
    self.assertIsNone(commandResult.errorMessage)

    self.assertIn("ModelCommandResult<", str(commandResult))
    self.assertIn("ModelCommandResult<", repr(commandResult))


  def testModelCommandResultConstructorWithZeroStatusAndNoneArgs(self):
    self._implTestCreateSuccessfulModelCommandResult(args=None)


  def testModelCommandResultConstructorWithAllArgs(self):
    self._implTestCreateSuccessfulModelCommandResult(
      args={'key1': 4098, 'key2': 4139})


  def testModelCommandResultConstructorInvalidArgs(self):
    commandID = 1
    method = "testMethod"
    status = 0
    args = "None"
    with self.assertRaises(AssertionError) as cm:
      ModelCommandResult(commandID=commandID, method=method, status=status,
                         args=args)
    self.assertIn("Expected dict instance as args", cm.exception.args[0])


  def testModelCommandResultConstructorWithZeroStatusArgsAndErrorMessage(self):
    commandID = 1
    method = "testMethod"
    status = 0
    args = {'key1': 4098, 'key2': 4139}
    errorMessage = "None"
    with self.assertRaises(AssertionError) as cm:
      ModelCommandResult(commandID=commandID, method=method, status=status,
                         args=args, errorMessage=errorMessage)
    self.assertIn("Unexpected errorMessage with status=0", cm.exception.args[0])


  def testModelCommandResultConstructorWithNonZeroStatusAndErrorMessage(self):
    commandID = 1
    method = "testMethod"
    status = 1
    errorMessage = "None"
    commandResult = ModelCommandResult(commandID=commandID, method=method,
                                       status=status, errorMessage=errorMessage)
    self.assertEqual(commandResult.commandID, commandID)
    self.assertEqual(commandResult.method, method)
    self.assertEqual(commandResult.status, status)
    self.assertEqual(commandResult.errorMessage, errorMessage)
    self.assertIsNone(commandResult.args)
    self.assertIn("ModelCommandResult<", str(commandResult))
    self.assertIn("ModelCommandResult<", repr(commandResult))


  def testModelCommandResultConstructorWithNonZeroStatusAndMissingErrorMessage(
      self):
    commandID = 1
    method = "testMethod"
    status = 1
    with self.assertRaises(AssertionError) as cm:
      ModelCommandResult(commandID=commandID, method=method, status=status)
    self.assertIn("Unexpected errorMessage type with non-zero status",
                  cm.exception.args[0])


  def testModelCommandResultConstructorWithNonZeroStatusAndUnexpectedArgs(self):
    commandID = 1
    method = "testMethod"
    status = 1
    args = {'key1': 4098, 'key2': 4139}
    with self.assertRaises(AssertionError) as cm:
      ModelCommandResult(commandID=commandID, method=method, status=status,
                         args=args, errorMessage="describes error")
    self.assertIn("Unexpected args with non-zero status", cm.exception.args[0])


  def testModelCommandResultConstructorInvalidStatus(self):
    commandID = 1
    method = "testMethod"
    status = "invalid"
    args = {'key1': 4098, 'key2': 4139}
    with self.assertRaises(AssertionError) as cm:
      ModelCommandResult(commandID=commandID, method=method, status=status,
                         args=args)
    self.assertIn("Expected int or long as status", cm.exception.args[0])


  def _implModelCommandResultSerializableStateWithZeroStatus(self, args):
    commandID = 1
    method = "testMethod"
    status = 0
    commandResult = ModelCommandResult(commandID=commandID, method=method,
                                       status=status, args=copy.copy(args))
    self.assertEqual(commandResult.commandID, commandID)
    self.assertEqual(commandResult.method, method)
    self.assertEqual(commandResult.status, status)
    self.assertEqual(commandResult.args, args)
    self.assertIsNone(commandResult.errorMessage)

    commandResult2 = _ModelRequestResultBase.__createFromState__(
      commandResult.__getstate__())

    self.assertEqual(commandResult2.commandID, commandID)
    self.assertEqual(commandResult2.method, method)
    self.assertEqual(commandResult2.status, status)
    self.assertEqual(commandResult2.args, args)
    self.assertIsNone(commandResult2.errorMessage)
    self.assertIn("ModelCommandResult<", str(commandResult2))
    self.assertIn("ModelCommandResult<", repr(commandResult2))


  def testModelCommandResultSerializableStateWithZeroStatusAndNoneArgs(self):
    self._implModelCommandResultSerializableStateWithZeroStatus(args=None)


  def testModelCommandResultSerializableStateWithZeroStatusAndArgs(self):
    self._implModelCommandResultSerializableStateWithZeroStatus(
      args={'key1': 4098, 'key2': 4139})


  def testModelCommandResultSerializableStateWithNonZeroStatus(self):
    commandID = 1
    method = "testMethod"
    status = 1
    errorMessage = "something bad happened"
    commandResult = ModelCommandResult(commandID=commandID, method=method,
                                       status=status, errorMessage=errorMessage)
    self.assertEqual(commandResult.commandID, commandID)
    self.assertEqual(commandResult.method, method)
    self.assertEqual(commandResult.status, status)
    self.assertEqual(commandResult.errorMessage, errorMessage)
    self.assertIsNone(commandResult.args)
    self.assertIn("ModelCommandResult<", str(commandResult))
    self.assertIn("ModelCommandResult<", repr(commandResult))

    commandResult2 = _ModelRequestResultBase.__createFromState__(
      commandResult.__getstate__())

    self.assertEqual(commandResult2.commandID, commandID)
    self.assertEqual(commandResult2.method, method)
    self.assertEqual(commandResult2.status, status)
    self.assertEqual(commandResult2.errorMessage, errorMessage)
    self.assertIsNone(commandResult2.args)
    self.assertIn("ModelCommandResult<", str(commandResult2))
    self.assertIn("ModelCommandResult<", repr(commandResult2))



class ModelInputRowTestCase(unittest.TestCase):
  """
  Unit tests for ModelInputRow
  """


  def testModelInputRowConstructor(self):
    rowID = 1
    data = [1, 2, datetime.datetime.utcnow()]
    inputRow = ModelInputRow(rowID=rowID, data=copy.copy(data))
    self.assertEqual(inputRow.rowID, rowID)
    self.assertEqual(inputRow.data, data)
    self.assertIn("ModelInputRow<", str(inputRow))
    self.assertIn("ModelInputRow<", repr(inputRow))


  def testModelInputRowConstructorInvalidData(self):
    with self.assertRaises(AssertionError) as cm:
      ModelInputRow(rowID=1, data=None)
    self.assertIn("Expected list or tuple as data, but got",
                  cm.exception.args[0])

    with self.assertRaises(AssertionError) as cm:
      ModelInputRow(rowID=1, data=[])
    self.assertIn("Expected non-empty sequence as data, but got",
                  cm.exception.args[0])


  def testModelInputRowConstructorFromSerializableState(self):
    rowID = 1
    data = [1, 2, datetime.datetime.utcnow()]
    inputRow = ModelInputRow(rowID=rowID, data=copy.copy(data))
    self.assertEqual(inputRow.rowID, rowID)
    self.assertEqual(inputRow.data, data)
    self.assertIn("ModelInputRow<", str(inputRow))
    self.assertIn("ModelInputRow<", repr(inputRow))

    inputRow2 = _ModelRequestResultBase.__createFromState__(
      inputRow.__getstate__())

    self.assertEqual(inputRow2.rowID, rowID)
    self.assertEqual(inputRow2.data, data)
    self.assertIn("ModelInputRow<", str(inputRow2))
    self.assertIn("ModelInputRow<", repr(inputRow2))



class ModelInferenceResultTestCase(unittest.TestCase):
  """
  Unit tests for ModelInferenceResult
  """


  def testModelInferenceResultConstructorWithSuccessStatus(self):
    rowID = 1
    status = 0
    anomalyScore = 1.95
    inferenceResult = ModelInferenceResult(rowID=rowID, status=status,
      anomalyScore=anomalyScore)
    self.assertEqual(inferenceResult.rowID, rowID)
    self.assertEqual(inferenceResult.status, status)
    self.assertEqual(inferenceResult.anomalyScore, anomalyScore)
    self.assertIsNone(inferenceResult.errorMessage)
    self.assertIn("ModelInferenceResult<", str(inferenceResult))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult))
    self.assertIn("anomalyScore", repr(inferenceResult))


  def testModelInferenceResultConstructorWithErrorStatus(self):
    rowID = 1
    status = 1
    errorMessage = "something bad"
    inferenceResult = ModelInferenceResult(rowID=rowID, status=status,
      errorMessage=errorMessage)
    self.assertEqual(inferenceResult.rowID, rowID)
    self.assertEqual(inferenceResult.status, status)
    self.assertIsNone(inferenceResult.anomalyScore)
    self.assertEqual(inferenceResult.errorMessage, errorMessage)
    self.assertIn("ModelInferenceResult<", str(inferenceResult))
    self.assertIn("errorMsg", str(inferenceResult))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult))
    self.assertIn("errorMsg", repr(inferenceResult))


  def testModelInferenceResultConstructorInvalidAnomalyScore(self):
    rowID = 1
    status = 0
    anomalyScore = "None"

    with self.assertRaises(AssertionError) as cm:
      ModelInferenceResult(rowID=rowID, status=status,
                           anomalyScore=anomalyScore)
    self.assertIn("Expected numeric anomaly score with status=0, but got",
                  cm.exception.args[0])


  def testModelInferenceResultConstructorMissingErrorMessage(self):
    rowID = 1
    status = 1
    errorMessage = None
    with self.assertRaises(AssertionError) as cm:
      ModelInferenceResult(rowID=rowID, status=status,
        errorMessage=errorMessage)
    self.assertIn("Unexpected errorMessage type with non-zero status",
                  cm.exception.args[0])


  def testModelInferenceResultSerializableStateWithAnomalyScore(self):
    rowID = 1
    status = 0
    anomalyScore = 9.72
    inferenceResult = ModelInferenceResult(rowID=rowID, status=status,
      anomalyScore=anomalyScore)
    self.assertEqual(inferenceResult.rowID, rowID)
    self.assertEqual(inferenceResult.status, status)
    self.assertEqual(inferenceResult.anomalyScore, anomalyScore)
    self.assertIsNone(inferenceResult.errorMessage)
    self.assertIn("ModelInferenceResult<", str(inferenceResult))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult))

    inferenceResult2 = _ModelRequestResultBase.__createFromState__(
      inferenceResult.__getstate__())

    self.assertEqual(inferenceResult2.rowID, rowID)
    self.assertEqual(inferenceResult2.status, status)
    self.assertEqual(inferenceResult2.anomalyScore, anomalyScore)
    self.assertIsNone(inferenceResult2.errorMessage)
    self.assertIn("ModelInferenceResult<", str(inferenceResult2))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult2))


  def testModelInferenceResultSerializableStateWithErrorMessage(self):
    rowID = 1
    status = 1
    errorMessage = "error"
    inferenceResult = ModelInferenceResult(rowID=rowID, status=status,
      errorMessage=errorMessage)
    self.assertEqual(inferenceResult.rowID, rowID)
    self.assertEqual(inferenceResult.status, status)
    self.assertEqual(inferenceResult.errorMessage, errorMessage)
    self.assertIsNone(inferenceResult.anomalyScore)
    self.assertIn("ModelInferenceResult<", str(inferenceResult))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult))

    inferenceResult2 = _ModelRequestResultBase.__createFromState__(
      inferenceResult.__getstate__())

    self.assertEqual(inferenceResult2.rowID, rowID)
    self.assertEqual(inferenceResult2.status, status)
    self.assertEqual(inferenceResult2.errorMessage, errorMessage)
    self.assertIsNone(inferenceResult2.anomalyScore)
    self.assertIn("ModelInferenceResult<", str(inferenceResult2))
    self.assertIn("ModelInferenceResult<", repr(inferenceResult2))



class BatchPackagerTestCase(unittest.TestCase):
  """
  Unit tests for BatchPackager
  """

  def testMarshalUnmarshal(self):
    inputBatch = [
        ModelCommandResult(commandID="commandID", method="testMethod", status=1,
          errorMessage="errorMessage"),
        ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
        ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"]),
      ]
    batchState = BatchPackager.marshal(batch=inputBatch)

    requestBatch = BatchPackager.unmarshal(batchState=batchState)
    self.assertEqual(requestBatch[0].commandID, inputBatch[0].commandID)
    self.assertEqual(requestBatch[1].rowID, inputBatch[1].rowID)
    self.assertEqual(requestBatch[2].rowID, inputBatch[2].rowID)



class RequestMessagePackagerTestCase(unittest.TestCase):
  """
  Unit tests for RequestMessagePackager
  """

  def testMarshalAndUnmarshal(self):
    requestBatch = [
        ModelCommand(commandID="abc", method="defineModel",
          args={'key1': 4098, 'key2': 4139}),
        ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
        ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"]),
      ]
    batchState = BatchPackager.marshal(batch=requestBatch)
    msg = RequestMessagePackager.marshal(batchID="foobar",
                                         batchState=batchState)

    r = RequestMessagePackager.unmarshal(msg)

    self.assertEqual(r.batchID, "foobar")
    self.assertEqual(r.batchState, batchState)

    # Make sure we aren't forgetting to test any returned fields
    self.assertEqual(set(["batchID", "batchState"]), set(r._fields))



class ResultMessagePackagerTestCase(unittest.TestCase):
  """
  Unit tests for ResultMessagePackager
  """

  def testMarshalAndUnmarshal(self):
    resultBatch = [
      ModelCommandResult(commandID="abc", method="testMethod", status=0,
        args={'key1': 4098, 'key2': 4139}),
      ModelInferenceResult(rowID="foo", status=0, anomalyScore=1),
      ModelInferenceResult(rowID="bar", status=0, anomalyScore=2)
      ]
    batchState = BatchPackager.marshal(batch=resultBatch)
    msg = ResultMessagePackager.marshal(modelID="foobar", batchState=batchState)

    r = ResultMessagePackager.unmarshal(msg)

    self.assertEqual(r.modelID, "foobar")
    self.assertEqual(r.batchState, batchState)


    # Make sure we aren't forgetting to test any returned fields
    self.assertEqual(set(["modelID", "batchState"]), set(r._fields))



class ModelSwapperInterfaceTestCase(unittest.TestCase):
  """
  Unit tests for ModelSwapperInterface

  TODO: test the scenario where submitRequests attempts to send notification to
    model scheduler, but the notification queue hasn't been created yet.
  """


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testConstruct(self, _messageBusConnectorClassMock):
    interface = ModelSwapperInterface()
    self.assertIsNotNone(interface._bus)
    self.assertEqual(len(interface._consumers), 0)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testContextManager(self, _messageBusConnectorClassMock):
    with ModelSwapperInterface() as interface:
      self.assertIsNotNone(interface._bus)
      self.assertEqual(len(interface._consumers), 0)

    self.assertIsNone(interface._bus)
    self.assertEqual(len(interface._consumers), 0)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testMessageQueueNameOverrideViaConfig(self,
                                            _messageBusConnectorClassMock):

    notificationQName = self.__class__.__name__ + ".NOTIFICATION_QUEUE"
    resultsQName = self.__class__.__name__ + ".OUTPUT_QUEUE"
    modelInputQPrefix = self.__class__.__name__ + ".MODEL_INPUT_QUEUE_PREFIX"

    with ConfigAttributePatch(
        modelSwapperConfig.CONFIG_NAME,
        modelSwapperConfig.baseConfigDir,
        ((ModelSwapperInterface._CONFIG_SECTION,
          ModelSwapperInterface._SCHEDULER_NOTIFICATION_Q_OPTION_NAME,
          notificationQName),
         (ModelSwapperInterface._CONFIG_SECTION,
          ModelSwapperInterface._RESULTS_Q_OPTION_NAME,
          resultsQName),
         (ModelSwapperInterface._CONFIG_SECTION,
          ModelSwapperInterface._MODEL_INPUT_Q_PREFIX_OPTION_NAME,
          modelInputQPrefix))):

      swapperAPI = ModelSwapperInterface()

      self.assertEqual(swapperAPI._schedulerNotificationQueueName,
                       notificationQName)
      self.assertEqual(swapperAPI._resultsQueueName,
                       resultsQName)
      self.assertEqual(swapperAPI._modelInputQueueNamePrefix,
                       modelInputQPrefix)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testSubmitRequestsWithContextManager(self, messageBusConnectorClassMock):
    requests = [
      ModelCommand(commandID="abc", method="defineModel",
        args={'key1': 4098, 'key2': 4139}),
      ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
      ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"])
    ]

    modelID = "foofar"

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    with ModelSwapperInterface() as interface:
      batchID = interface.submitRequests(modelID=modelID, requests=requests)

      modelMQName = interface._modelInputQueueNamePrefix + modelID
      notificationMQName = interface._schedulerNotificationQueueName

    # Verify
    self.assertIsInstance(batchID, str)

    msg = RequestMessagePackager.marshal(
      batchID=batchID,
      batchState=BatchPackager.marshal(batch=requests))

    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)

    messageBusConnectorMock.publish.assert_any_call(
      modelMQName, msg, persistent=True)

    messageBusConnectorMock.publish.assert_any_call(
      notificationMQName, json.dumps(modelID), persistent=False)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                publish=Mock(spec_set=MessageBusConnector.publish))
  def testSubmitRequestsWithModelNotFoundException(
      self, messageBusConnectorClassMock):
    requests = [
      ModelCommand(commandID="abc", method="defineModel",
        args={'key1': 4098, 'key2': 4139}),
      ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
      ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"])
    ]

    modelID = "foofar"

    # Configure mock
    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.publish.side_effect = (
      message_bus_connector.MessageQueueNotFound(
        "expected exception from publish to non-existent model"))

    # Run
    with self.assertRaises(
        model_swapper_interface.ModelNotFound) as assertionCM:
      with ModelSwapperInterface() as interface:
        interface.submitRequests(modelID=modelID, requests=requests)

    # Verify
    self.assertIn("expected exception from publish to non-existent model",
                  assertionCM.exception.args[0])

    self.assertEqual(messageBusConnectorMock.publish.call_count, 1)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                publish=Mock(spec_set=MessageBusConnector.publish))
  def testSubmitRequestsWithNotificationQueueNotFound(
      self, messageBusConnectorClassMock):
    # It should be okay to submit a request before the model scheduler
    # notification message queue is created at startup of model scheduler
    requests = [
      ModelCommand(commandID="abc", method="defineModel",
        args={'key1': 4098, 'key2': 4139}),
      ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
      ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"])
    ]

    modelID = "foofar"

    # Configure mock
    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.publish.side_effect = (
      Mock(),
      message_bus_connector.MessageQueueNotFound(
        "expected exception from publishing of notification"))

    # Run
    with ModelSwapperInterface() as interface:
      batchID = interface.submitRequests(modelID=modelID, requests=requests)

    # Verify
    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)

    self.assertIsInstance(batchID, str)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    consume=Mock(spec_set=MessageBusConnector.consume))
  def testContextManagerAndConsumeRequests(self, messageBusConnectorClassMock):
    expectedRequests = (
      ModelCommand(commandID="abc", method="defineModel",
                   args={'key1': 4098, 'key2': 4139}),
      ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
      ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"]),
    )
    modelID = "foobar"
    batchID = uuid.uuid1().hex
    msg = RequestMessagePackager.marshal(
      batchID=batchID,
      batchState=BatchPackager.marshal(batch=expectedRequests))

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    ackMock = Mock(return_value=None)
    messageBusConnectorMock.consume.return_value = Mock(
      spec_set=message_bus_connector._QueueConsumer,
      __iter__=lambda *args, **kwargs: iter(
        [message_bus_connector._ConsumedMessage(
          body=msg, ack=ackMock)]))

    with ModelSwapperInterface() as interface:
      self.assertEqual(len(interface._consumers), 0)

      with interface.consumeRequests(modelID) as consumer:
        self.assertIsNotNone(consumer._mqConsumer)
        self.assertEqual(len(interface._consumers), 1)

        batch = next(iter(consumer))

        self.assertEqual(batch.batchID, batchID)
        self.assertEqual(batch.objects, expectedRequests)
        self.assertTrue(callable(batch.ack))
        self.assertIs(batch.ack, ackMock)

        # Make sure we didn't skip any fields
        self.assertEqual(set(batch._fields), set(["batchID", "objects", "ack"]))


      self.assertIsNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 0)

    self.assertEqual(len(interface._consumers), 0)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    consume=Mock(spec_set=MessageBusConnector.consume))
  def testConsumeRequestsNonBlocking(self, messageBusConnectorClassMock):
    expectedRequests = (
      ModelCommand(commandID="abc", method="defineModel",
                   args={'key1': 4098, 'key2': 4139}),
      ModelInputRow(rowID="foo", data=[1, 2, "Sep 21 02:24:21 UTC 2013"]),
      ModelInputRow(rowID="bar", data=[9, 54, "Sep 21 02:24:38 UTC 2013"]),
    )
    modelID = "foobar"
    batchID = uuid.uuid1().hex
    msg = RequestMessagePackager.marshal(
      batchID=batchID,
      batchState=BatchPackager.marshal(batch=expectedRequests))

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    ackMock = Mock(return_value=None)
    messageBusConnectorMock.consume.return_value = Mock(
      spec_set=message_bus_connector._QueueConsumer,
      __iter__=lambda *args, **kwargs: iter(
        [message_bus_connector._ConsumedMessage(body=msg, ack=ackMock)]))

    with ModelSwapperInterface() as interface:
      self.assertEqual(len(interface._consumers), 0)

      with interface.consumeRequests(modelID, blocking=False) as consumer:
        self.assertIsNotNone(consumer._mqConsumer)
        self.assertEqual(len(interface._consumers), 1)

        batch = next(iter(consumer))

        self.assertEqual(batch.batchID, batchID)
        self.assertEqual(batch.objects, expectedRequests)
        self.assertTrue(callable(batch.ack))
        self.assertIs(batch.ack, ackMock)

        # Make sure we didn't skip any fields
        self.assertEqual(set(batch._fields), set(["batchID", "objects", "ack"]))


      self.assertIsNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 0)

    self.assertEqual(len(interface._consumers), 0)

    modelMQName = interface._modelInputQueueNamePrefix + modelID

    messageBusConnectorMock.consume.assert_called_once_with(
      modelMQName, blocking=False)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                consume=Mock(spec_set=MessageBusConnector.consume))
  @patch.object(model_swapper_interface, "_ConsumedResultBatch", autospec=True)
  def testConsumeRequestsWithModelNotFoundException(
      self, _consumedResultBatchClassMock, messageBusConnectorClassMock):
    # Model requests consumer should raise model_swapper_interface.ModelNotFound
    # if the model's input endpoint doesn't exist

    # Configure mocks

    def fakeConsumer(results):
      if results is None:
        raise message_bus_connector.MessageQueueNotFound("from mock test")

      for r in results:
        yield r

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.consume.return_value = fakeConsumer(None)

    # Run
    with self.assertRaises(model_swapper_interface.ModelNotFound) as raisesCM:
      with ModelSwapperInterface() as interface:
        with interface.consumeRequests("abcdef") as consumer:
          _results = tuple(consumer)

    # Verify

    self.assertIn(
      "Attempt to consume requests from model=abcdef is impossible",
      raisesCM.exception.args[0])


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testDefineModel(self, messageBusConnectorClassMock):
    modelID = "model_foo"
    args = dict()
    commandID = "command_bar"
    with ModelSwapperInterface() as interface:
      interface.defineModel(modelID=modelID, args=args, commandID=commandID)

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    self.assertEqual(messageBusConnectorMock.createMessageQueue.call_count, 1)

    # One call to publish the request batch and the second to publish
    # notification to model scheduler
    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testDeleteModel(self, messageBusConnectorClassMock):
    modelID = "model_foo"
    commandID = "command_bar"
    with ModelSwapperInterface() as interface:
      interface.deleteModel(modelID=modelID, commandID=commandID)

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    self.assertEqual(messageBusConnectorMock.purge.call_count, 1)

    # One call to publish the request batch and the second to publish
    # notification to model scheduler
    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testDeleteNonExistentModelPurge(self, messageBusConnectorClassMock):
    modelID = "model_foo"
    commandID = "command_bar"

    # Configure mocks

    exception = message_bus_connector.MessageQueueNotFound(
                  "publish failed in mock test")

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.purge.side_effect = exception

    # Run

    with ModelSwapperInterface() as interface:
      interface.deleteModel(modelID=modelID, commandID=commandID)

    # Verify

    self.assertEqual(messageBusConnectorMock.purge.call_count, 1)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testDeleteNonExistentModelPublish(self, messageBusConnectorClassMock):
    modelID = "model_foo"
    commandID = "command_bar"

    # Configure mocks

    exception = message_bus_connector.MessageQueueNotFound(
                  "publish failed in mock test")

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.publish.side_effect = exception

    # Run

    with ModelSwapperInterface() as interface:
      interface.deleteModel(modelID=modelID, commandID=commandID)

    # Verify

    self.assertEqual(messageBusConnectorMock.purge.call_count, 1)
    self.assertEqual(messageBusConnectorMock.publish.call_count, 1)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testCleanUpAfterModelDeletion(self, messageBusConnectorClassMock):
    modelID = "model_foo"
    with ModelSwapperInterface() as interface:
      interface.cleanUpAfterModelDeletion(modelID=modelID)

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    self.assertEqual(messageBusConnectorMock.deleteMessageQueue.call_count, 1)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    isEmpty=Mock(spec_set=MessageBusConnector.isEmpty))
  def testModelInputPendingYes(self, messageBusConnectorClassMock):
    modelID = "model_foo"

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.isEmpty.return_value = False

    with ModelSwapperInterface() as interface:
      inputPending = interface.modelInputPending(modelID=modelID)


    self.assertEqual(messageBusConnectorMock.isEmpty.call_count, 1)

    self.assertTrue(inputPending)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    isEmpty=Mock(spec_set=MessageBusConnector.isEmpty))
  def testModelInputPendingNo(self, messageBusConnectorClassMock):
    modelID = "model_foo"

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.isEmpty.return_value = True

    with ModelSwapperInterface() as interface:
      inputPending = interface.modelInputPending(modelID=modelID)


    self.assertEqual(messageBusConnectorMock.isEmpty.call_count, 1)

    self.assertFalse(inputPending)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    isEmpty=Mock(spec_set=MessageBusConnector.isEmpty))
  def testModelInputPendingMessageQueueNotFoundInterpretedAsNo(
    self, messageBusConnectorClassMock):
    modelID = "model_foo"

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.isEmpty.side_effect = (
      message_bus_connector.MessageQueueNotFound)

    with ModelSwapperInterface() as interface:
      inputPending = interface.modelInputPending(modelID=modelID)

    self.assertEqual(messageBusConnectorMock.isEmpty.call_count, 1)

    self.assertFalse(inputPending)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    isEmpty=Mock(spec_set=MessageBusConnector.isEmpty),
    getAllMessageQueues=Mock(spec_set=MessageBusConnector.getAllMessageQueues))
  def testGetModelsWithInputPending(self, messageBusConnectorClassMock):
    modelsPendingMap = {
      "model_one": True,
      "disappeared_one": None,
      "model_two": True,
      "model_three": False,
      "disappeared_two": None,
      "model_four": False,
      "model_five": True
    }

    with ModelSwapperInterface() as interface:
      allMessageQueues = [interface._getModelInputQName(modelID)
                          for modelID in modelsPendingMap]

    isEmptyResults = [
      (not pending if pending is not None
       else message_bus_connector.MessageQueueNotFound(mq))
      for mq, pending in modelsPendingMap.iteritems()]

    # Add some queue names that don't look like model input queue names
    allMessageQueues.extend(
      ("not.model.input.queue1", "not.model.input.queue2"))
    isEmptyResults.extend((False, False))

    # Configure message bus connector mock
    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.isEmpty.side_effect = isEmptyResults
    messageBusConnectorMock.getAllMessageQueues.return_value = (
      allMessageQueues)

    # Go for it!
    with ModelSwapperInterface() as interface:
      actualModelsWithInput = interface.getModelsWithInputPending()

    self.assertEqual(messageBusConnectorMock.isEmpty.call_count,
                     len(modelsPendingMap))

    self.assertEqual(messageBusConnectorMock.getAllMessageQueues.call_count, 1)

    # Verify results
    expectedSet = set(modelID for modelID, pending
                      in modelsPendingMap.iteritems() if pending)
    self.assertEqual(set(actualModelsWithInput), expectedSet)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testSubmitResults(self, messageBusConnectorClassMock):
    results = [
      ModelCommandResult(commandID="abc", method="testMethod", status=0,
        args={'key1': 4098, 'key2': 4139}),
      ModelInferenceResult(rowID="foo", status=0, anomalyScore=1),
      ModelInferenceResult(rowID="bar", status=0, anomalyScore=2)
    ]

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    interface = ModelSwapperInterface()

    modelID = "foofar"
    msg = ResultMessagePackager.marshal(
      modelID=modelID,
      batchState=BatchPackager.marshal(batch=results))

    interface.submitResults(modelID=modelID, results=results)

    mqName = interface._resultsQueueName

    messageBusConnectorMock.publish.assert_called_once_with(mqName, msg,
                                                            persistent=True)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                publish=Mock(spec_set=MessageBusConnector.publish))
  def testSubmitResultsRecoveryFromMessageQueueNotFound(
      self, messageBusConnectorClassMock):
    # submitResults recovers from the initial MessageQueueNotFound by creating
    # the results message queue and re-publishing the message
    results = [
      ModelCommandResult(commandID="abc", method="testMethod", status=0,
        args={'key1': 4098, 'key2': 4139}),
      ModelInferenceResult(rowID="foo", status=0, anomalyScore=1),
      ModelInferenceResult(rowID="bar", status=0, anomalyScore=2)
    ]

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.publish.side_effect = (
      message_bus_connector.MessageQueueNotFound("from mock test"),
      Mock())

    modelID = "foofar"

    with ModelSwapperInterface() as interface:
      interface.submitResults(modelID=modelID, results=results)

      mqName = interface._resultsQueueName

    # Verify
    messageBusConnectorMock.createMessageQueue.assert_called_once_with(
      mqName, durable=True)

    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)

    msg = ResultMessagePackager.marshal(
      modelID=modelID,
      batchState=BatchPackager.marshal(batch=results))

    messageBusConnectorMock.publish.assert_called_with(mqName, msg,
                                                       persistent=True)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                publish=Mock(spec_set=MessageBusConnector.publish))
  def testSubmitResultsFailure(self, messageBusConnectorClassMock):
    results = [
      ModelCommandResult(commandID="abc", method="testMethod", status=0,
        args={'key1': 4098, 'key2': 4139}),
      ModelInferenceResult(rowID="foo", status=0, anomalyScore=1),
      ModelInferenceResult(rowID="bar", status=0, anomalyScore=2)
    ]

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.publish.side_effect = (
      message_bus_connector.MessageQueueNotFound("from mock test"),
      Exception("re-publish failed in mock test"))

    modelID = "foofar"

    with self.assertRaises(Exception) as raisesCM:
      with ModelSwapperInterface() as interface:
        mqName = interface._resultsQueueName
        interface.submitResults(modelID=modelID, results=results)

    # Verify
    self.assertEqual(raisesCM.exception.args[0],
                     "re-publish failed in mock test")

    messageBusConnectorMock.createMessageQueue.assert_called_once_with(
      mqName, durable=True)

    self.assertEqual(messageBusConnectorMock.publish.call_count, 2)

    msg = ResultMessagePackager.marshal(
      modelID=modelID,
      batchState=BatchPackager.marshal(batch=results))

    messageBusConnectorMock.publish.assert_called_with(mqName, msg,
                                                       persistent=True)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    consume=Mock(spec_set=MessageBusConnector.consume))
  def testContextManagerAndConsumeResults(self, messageBusConnectorClassMock):
    expectedResults = (
      ModelCommandResult(commandID="abc", method="testMethod", status=0,
        args={'key1': 4098, 'key2': 4139}),
      ModelInferenceResult(rowID="foo", status=0, anomalyScore=1.3),
      ModelInferenceResult(rowID="bar", status=0, anomalyScore=2.9)
    )
    modelID = "foobar"
    msg = ResultMessagePackager.marshal(
      modelID=modelID,
      batchState=BatchPackager.marshal(batch=expectedResults))

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    ackMock = Mock(return_value=None)
    messageBusConnectorMock.consume.return_value = Mock(
      spec_set=message_bus_connector._QueueConsumer,
      __iter__=lambda *args, **kwargs: iter(
        [message_bus_connector._ConsumedMessage(
          body=msg, ack=ackMock)]))

    with ModelSwapperInterface() as interface:
      self.assertEqual(len(interface._consumers), 0)

      consumer = interface.consumeResults()
      self.assertIsNotNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 1)

      batch = next(iter(consumer))

      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(batch.objects, expectedResults)
      self.assertTrue(callable(batch.ack))
      self.assertIs(batch.ack, ackMock)

      self.assertEqual(set(batch._fields), set(["modelID", "objects", "ack"]))

      consumer.close()
      self.assertIsNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 0)

    self.assertEqual(len(interface._consumers), 0)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                consume=Mock(spec_set=MessageBusConnector.consume))
  @patch.object(model_swapper_interface, "_ConsumedResultBatch", autospec=True)
  def testConsumeResultsWithRecoveryFromMessageQueueNotFound(
      self, _consumedResultBatchClassMock, messageBusConnectorClassMock):
    # Model results consumer should recover from initial MessageQueueNotFound
    # by creating the message queue and restarting consumption

    # Configure mocks

    def fakeConsumer(results):
      if results is None:
        raise message_bus_connector.MessageQueueNotFound("from mock test")

      for r in results:
        yield r

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.consume.side_effect = [
      fakeConsumer(None), fakeConsumer(xrange(5))]

    # Run
    with ModelSwapperInterface() as interface:
      with interface.consumeResults() as consumer:
        results = tuple(consumer)

    # Verify

    self.assertEqual(messageBusConnectorMock.consume.call_count, 2)
    self.assertEqual(len(results), 5)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True,
                consume=Mock(spec_set=MessageBusConnector.consume))
  @patch.object(model_swapper_interface, "_ConsumedResultBatch", autospec=True)
  def testConsumeResultsWithNoSecondRecoveryFromMessageQueueNotFound(
      self, _consumedResultBatchClassMock, messageBusConnectorClassMock):
    # Model results consumer should recover from initial MessageQueueNotFound
    # by creating the message queue and restarting consumption

    # Configure mocks

    def fakeConsumer(results):
      if results is None:
        raise message_bus_connector.MessageQueueNotFound("from mock test")

      for r in results:
        yield r

    messageBusConnectorMock = messageBusConnectorClassMock.return_value
    messageBusConnectorMock.consume.side_effect = [
      fakeConsumer(None), fakeConsumer(None)]

    # Run
    with self.assertRaises(
        message_bus_connector.MessageQueueNotFound) as raisesCM:
      with ModelSwapperInterface() as interface:
        with interface.consumeResults() as consumer:
          _results = tuple(consumer)

    # Verify
    self.assertEqual(raisesCM.exception.args[0], "from mock test")
    self.assertEqual(messageBusConnectorMock.consume.call_count, 2)


  @patch.object(model_swapper_interface, "MessageBusConnector", autospec=True)
  def testInitSchedulerNotification(self, messageBusConnectorClassMock):
    with ModelSwapperInterface() as interface:
      interface.initSchedulerNotification()

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    self.assertEqual(messageBusConnectorMock.createMessageQueue.call_count, 1)


  @patch.object(
    model_swapper_interface, "MessageBusConnector", autospec=True,
    consume=Mock(spec_set=MessageBusConnector.consume))
  def testConsumeModelSchedulerNotifications(self,
                                             messageBusConnectorClassMock):
    modelID = "foobar"
    msg = json.dumps(modelID)

    messageBusConnectorMock = messageBusConnectorClassMock.return_value

    ackMock = Mock(return_value=None)
    messageBusConnectorMock.consume.return_value = Mock(
      spec_set=message_bus_connector._QueueConsumer,
      __iter__=lambda *args, **kwargs: iter(
        [message_bus_connector._ConsumedMessage(body=msg, ack=ackMock)]))

    with ModelSwapperInterface() as interface:
      self.assertEqual(len(interface._consumers), 0)

      consumer = interface.consumeModelSchedulerNotifications()
      self.assertIsNotNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 1)

      notification = next(iter(consumer))

      self.assertEqual(notification.value, modelID)
      self.assertTrue(callable(notification.ack))
      self.assertIs(notification.ack, ackMock)

      consumer.close()
      self.assertIsNone(consumer._mqConsumer)
      self.assertEqual(len(interface._consumers), 0)

    self.assertEqual(len(interface._consumers), 0)



if __name__ == '__main__':
  unittest.main()
