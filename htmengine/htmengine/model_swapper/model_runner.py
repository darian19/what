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
This module implements the Model Runner process that runs an OPF model. These
processes are started by the Model Scheduler service.
"""

import base64
import cPickle as pickle
import logging
from optparse import OptionParser
import select
import sys
import time
import traceback


from nupic.data.fieldmeta import FieldMetaInfo
from nupic.data.record_stream import RecordStreamIface
from nupic.frameworks.opf.modelfactory import ModelFactory
from nupic.support.decorators import logExceptions

from htmengine import htmengineerrno
from htmengine.htmengine_logging import getExtendedLogger, getStandardLogPrefix
from htmengine.model_checkpoint_mgr import model_checkpoint_mgr
from htmengine.model_checkpoint_mgr.model_checkpoint_mgr import (
    ModelCheckpointMgr)
from htmengine.model_swapper import ModelSwapperConfig
from htmengine.model_swapper.model_swapper_interface import (
    ModelCommand, ModelCommandResult,
    ModelInferenceResult, ModelInputRow, ModelSwapperInterface)

from nta.utils.logging_support_raw import LoggingSupport



_MODULE_NAME = "htmengine.model_runner"



def _getLogger():
  return getExtendedLogger(_MODULE_NAME)



class _ModelRunnerError(Exception):
  """ Exception with a htmengineerrno error code accessible via the "errno"
  instance variable
  """
  def __init__(self, errno, msg):
    """
    errno: a non-zero htmengine.htmengineerrno error code
    msg: a human-readable error message for debugging.
    """
    assert errno != 0
    super(_ModelRunnerError, self).__init__("%s: %s" % (errno, msg))
    self._errno = errno


  @property
  def errno(self):
    return self._errno



class ModelRunner(object):

  # How many exception traceback tail characters to include in error results
  _MAX_TRACEBACK_TAIL = 100


  def __init__(self, modelID):
    """
    :param modelID: model ID; string
    """
    self._logger = _getLogger()

    self._modelID = modelID

    self._swapperAPI = ModelSwapperInterface()

    self._archiver = _ModelArchiver(self._modelID)

    # "deleteModel" command handler sets this flag to force our processing
    # loop to terminate
    self._done = False

    modelSwapperConfig = ModelSwapperConfig()

    self._targetMaxRequestsPerCheckpoint = modelSwapperConfig.getint(
      "model_runner", "target_requests_per_checkpoint")

    self._profiling = (
      modelSwapperConfig.getboolean("debugging", "profiling") or
      self._logger.isEnabledFor(logging.DEBUG))

    if self._profiling:
      self._logger.info("Profiling is turned on")

      self._modelLoadSec = 0


  @property
  def _model(self):
    """ An OPF Model object or None if not loaded yet """
    return self._archiver.model


  @property
  def _inputRowEncoder(self):
    """ An _InputRowEncoder object or None if model not loaded yet """
    return self._archiver.inputRowEncoder


  @property
  def _checkpointMgr(self):
    return self._archiver.checkpointMgr


  def __repr__(self):
    return "%s<modelID=%s>" % (self.__class__.__name__, self._modelID)


  def __enter__(self):
    """ Context Manager protocol method. Allows a ModelRunner instance
    to be used in a "with" statement for automatic clean-up

    Parameters:
    ------------------------------------------------------------------------
    retval:     self.
    """
    return self


  def __exit__(self, _excType, _excVal, _excTb):
    """ Context Manager protocol method. Allows a ModelRunner instance
    to be used in a "with" statement for automatic cleanup

    Returns: False so as not to suppress the exception, if any
    """
    self.close()
    return False


  def close(self):
    """ Clean up """
    self._logger.debug("%r: Closing...", self)
    self._swapperAPI.close()


  @logExceptions(_getLogger)
  def run(self):
    startTime = time.time()

    self._logger.debug("%r: Starting run", self)

    totalBatches = 0
    totalRequests = 0
    totalDupBatches = 0

    # Retrieve the batch IDs that went into the current checkpont since previous
    # checkpoint
    modelCheckpointBatchIDSet = self._archiver.modelCheckpointBatchIDSet

    try:
      while not self._done:
        currentRunBatchIDSet = set()
        currentRunInputSamples = []
        currentRunNumRequests = 0
        lastRequestBatch = None

        with self._swapperAPI.consumeRequests(
            modelID=self._modelID, blocking=False) as consumer:

          if self._profiling:
            batchStartTime = time.time()

          # Process the next run of batches until
          # self._targetMaxRequestsPerCheckpoint is reached or exceeded
          for candidateBatch in consumer:
            if (candidateBatch.batchID in currentRunBatchIDSet or
                candidateBatch.batchID in modelCheckpointBatchIDSet):
              self._logger.warn(
                "%r: Already processed this batch=%s, skipping it (we must "
                "have lost channel/connection before or during ack)",
                self, candidateBatch.batchID)

              # Make it go away for good
              candidateBatch.ack()
              totalDupBatches += 1
              continue

            # NOTE: lastRequestBatch is used after this loop to ack this and
            # preceeding batches
            lastRequestBatch = candidateBatch

            currentRunBatchIDSet.add(lastRequestBatch.batchID)

            totalBatches += 1

            inputObjects = lastRequestBatch.objects
            numItems = len(inputObjects)
            currentRunNumRequests += numItems
            totalRequests += numItems

            self._logger.debug(
              "%r: Processing input batch #%s; batch=%s, numItems=%s...",
              self, totalBatches, lastRequestBatch.batchID, numItems)

            if self._profiling:
              procStartTime = time.time()
              self._modelLoadSec = 0

            # Process the input batch
            results = self._processInputBatch(inputObjects,
                                              currentRunInputSamples)

            # Send results
            if self._profiling:
              submitStartTime = time.time()

            self._swapperAPI.submitResults(modelID=self._modelID,
                                           results=results)

            if self._profiling:
              now = time.time()

              tailRowTimestampISO = tailRowID = None
              # Assumption: no empty batches
              if isinstance(inputObjects[-1], ModelInputRow):
                # Assumption: entire batch consistes of ModelInputRow objects
                tailRowTimestampISO = inputObjects[-1].data[0].isoformat() + "Z"
                tailRowID = inputObjects[-1].rowID

              self._logger.info(
                "{TAG:SWAP.MR.BATCH.DONE} model=%s; batch=%s; numItems=%s; "
                "tailRowID=%s; tailRowTS=%s; duration=%.4fs; "
                "loadDuration=%.4fs; procDuration=%.4fs; submitDuration=%.4fs; "
                "totalBatches=%s; totalItems=%s", self._modelID,
                lastRequestBatch.batchID, len(results), tailRowID,
                tailRowTimestampISO, now - batchStartTime, self._modelLoadSec,
                submitStartTime - procStartTime - self._modelLoadSec,
                now - submitStartTime, totalBatches, totalRequests)

            if self._done:
              self._logger.debug("%r: command handler requested exit, leaving "
                                 "consumer loop", self)
              break

            if currentRunNumRequests >= self._targetMaxRequestsPerCheckpoint:
              self._logger.debug("End of current run: currentRunNumRequests=%s",
                                 currentRunNumRequests)
              break
          else: # for
            self._done = True
            self._logger.debug(
              "%r: No more input batches, leaving consumer loop", self)

          # Checkpoint the model and ack all request batches processed in this
          # run
          if lastRequestBatch is not None:
            assert len(currentRunBatchIDSet) > 0

            modelCheckpointBatchIDSet = currentRunBatchIDSet

            # Checkpoint the model.
            if self._model is not None:

              if self._profiling:
                checkpointStartTime = time.time()

              self._archiver.saveModel(
                currentRunBatchIDSet=currentRunBatchIDSet,
                currentRunInputSamples=currentRunInputSamples)

              if self._profiling:
                self._logger.info(
                  "%r: {TAG:SWAP.MR.CHKPT.DONE} currentRunNumRequests=%s; "
                  "currentRunNumBatches=%s; duration=%.4fs",
                  self, currentRunNumRequests, len(currentRunBatchIDSet),
                  time.time() - checkpointStartTime)

            # Ack the last request batch and all unacked batches before it
            # consumed during this run
            lastRequestBatch.ack(multiple=True)

          if not self._done:
            # Check if SwapController wants to preempt us (it closes the other
            # end of our stdin to signal the intention)
            readReadyList = select.select((sys.stdin,), (), (), 0)[0]
            if readReadyList:
              self._logger.debug("%r: SwapController wants to preempt us, "
                                "leaving", self)
              self._done = True
    finally:
      if totalBatches == 0:
        self._logger.warn("%r: zero input batches were processed", self)

      self._logger.info(
        "%r: {TAG:SWAP.MR.FINAL.SUMMARY} totalBatches=%s; totalRequests=%s; "
        "totalDupBatches=%s; duration=%s", self, totalBatches, totalRequests,
        totalDupBatches, time.time() - startTime)



  def _processInputBatch(self, inputObjects, currentRunInputSamples):
    """ Process a batch of model commands and/or inference input data rows

    :param inputObjects: a sequence of ModelCommand or ModelInputRow objects

    :param currentRunInputSamples: a list; the data of input rows will be
      appended to this list for input rows that were processed successfully

    :returns: a sequence of the corresponding ModelCommandResult or
      ModelInferenceResult objects
    TODO: unit-test return value
    """
    results = []

    for request in inputObjects:
      if isinstance(request, ModelCommand):
        results.append(self._processModelCommand(request))

      elif isinstance(request, ModelInputRow):
        results.append(self._processInputRow(request, currentRunInputSamples))

      else:
        raise ValueError("Unexpected request: " + repr(request))

    return results


  def _processModelCommand(self, command):
    """
    command: ModelCommand instance

    Returns: a ModelCommandResult instance
    """
    self._logger.info("%r: Processing model command: %r", self, command)
    try:
      if command.method == "defineModel":
        return self._defineModel(command)
      elif command.method == "deleteModel":
        return self._deleteModel(command)
      elif command.method == "cloneModel":
        return self._cloneModel(command)
      else:
        raise _ModelRunnerError(
          errno=htmengineerrno.ERR_INVALID_ARG,
          msg="Unknown command method=%s" % (command.method,))

    except (Exception, _ModelRunnerError) as e:  # pylint: disable=W0703
      self._logger.exception("%r: %r failed;", self, command)
      return ModelCommandResult(
        commandID=command.commandID, method=command.method,
        status=e.errno if isinstance(e, _ModelRunnerError) else htmengineerrno.ERR,
        errorMessage="%r failed on modelID=%s: %s. (tb: ...%s)" % (
          command, self._modelID, str(e) or repr(e),
          traceback.format_exc()[-self._MAX_TRACEBACK_TAIL:]))


  def _defineModel(self, command):
    """ Handle the "defineModel" command

    command: ModelCommand instance for the "defineModel" command

    retval: ModelCommandResult instance

    raises _ModelRunnerError
    """
    newModelDefinition = dict(
      modelParams=dict(modelConfig=command.args["modelConfig"],
                       inferenceArgs=command.args["inferenceArgs"]),
      inputSchema=command.args["inputRecordSchema"]
    )

    try:
      self._checkpointMgr.define(modelID=self._modelID,
                                 definition=newModelDefinition)
      assert self._model is None
    except model_checkpoint_mgr.ModelAlreadyExists:
      # Check if the existing model has the same definition
      existingModelDefinition = self._checkpointMgr.loadModelDefinition(
        self._modelID)

      if newModelDefinition != existingModelDefinition:
        self._logger.error(
          "defineModel: modelID=%s already exists with different "
          "creation meta data; existing=%r; new=%r", self._modelID,
          existingModelDefinition, newModelDefinition)

        raise _ModelRunnerError(
          errno=htmengineerrno.ERR_MODEL_ALREADY_EXISTS,
          msg="defineModel: modelID=%s already exists with different "
              "creation meta data" % (self._modelID,))
      else:
        # newModelDefinition is the same as existingModelDefinition; might be
        # side-effect of at-least-once delivery guarantee of the reliable data
        # path, so treat it as success
        self._logger.warn(
          "defineModel: modelID=%s already exists with same creation meta "
          "data (side-effect of at-least-once delivery guarantee?)",
          self._modelID)

    return ModelCommandResult(commandID=command.commandID,
                              method=command.method, status=0)


  def _cloneModel(self, command):
    """ Handle the "cloneModel" command

    command: ModelCommand instance for the "cloneModel" command

    retval: ModelCommandResult instance
    """
    try:
      self._checkpointMgr.clone(self._modelID, command.args["modelID"])
    except model_checkpoint_mgr.ModelNotFound as e:
      errorMessage = "%r: Cloning failed - source model not found (%r)" % (
        self, e,)
      self._logger.error(errorMessage)
      return ModelCommandResult(commandID=command.commandID,
                                method=command.method,
                                status=htmengineerrno.ERR_NO_SUCH_MODEL,
                                errorMessage=errorMessage)
    except model_checkpoint_mgr.ModelAlreadyExists as e:
      # Assuming it's the result of at-least-once delivery semantics
      self._logger.warn(
        "%r: Cloning destination already exists, suppressing (%r)", self, e)

    return ModelCommandResult(commandID=command.commandID,
                              method=command.method, status=0)


  def _deleteModel(self, command):
    """ Handle the "deleteModel" command

    command: ModelCommand instance for the "deleteModel" command

    retval: ModelCommandResult instance

    raises _ModelRunnerError
    """
    try:
      # Delete the model's checkpoint
      try:
        self._checkpointMgr.remove(modelID=self._modelID)
      except model_checkpoint_mgr.ModelNotFound:
        # Suppress it: could be side-effect of at-least-once delivery
        # guarantee, so treat it as success
        self._logger.warn("deleteModel: modelID=%s not found (side-effect "
                          "of at-least-once delivery guarantee?); "
                          "suppressing error", self._modelID)
      # Clean up model's resources in ModelSwapperInterface
      self._swapperAPI.cleanUpAfterModelDeletion(self._modelID)
    finally:
      self._archiver = _ModelArchiver(self._modelID)
      self._done = True

    return ModelCommandResult(commandID=command.commandID,
                              method=command.method, status=0)


  def _processInputRow(self, row, currentRunInputSamples):
    """
    :param row: ModelInputRow instance

    :param currentRunInputSamples: a list; the input row's data will be appended
      to this list if the row is processed successfully

    :returns: a ModelInferenceResult instance
    """
    try:
      if self._model is None:
        self._loadModel()

      # Convert a flat input row into a format that is consumable by an OPF
      # model
      self._inputRowEncoder.appendRecord(row.data)
      inputRecord = self._inputRowEncoder.getNextRecordDict()

      # Infer
      r = self._model.run(inputRecord)

      currentRunInputSamples.append(row.data)

      return ModelInferenceResult(
        rowID=row.rowID,
        status=0,
        anomalyScore=r.inferences["anomalyScore"])

    except (Exception, _ModelRunnerError) as e:  # pylint: disable=W0703
      self._logger.exception("%r: Inference failed for row=%r", self, row)
      return ModelInferenceResult(rowID=row.rowID,
        status=e.errno if isinstance(e, _ModelRunnerError) else htmengineerrno.ERR,
        errorMessage="Inference failed for rowID=%s of modelID=%s (%r): "
          "(tb: ...%s)" % (row.rowID, self._modelID, e,
                           traceback.format_exc()[-self._MAX_TRACEBACK_TAIL:]))


  def _loadModel(self):
    """ Load the model and construct the input row encoder

    Side-effect: self._model and self._inputRowEncoder are loaded;
      self._modelLoadSec is set if profiling is turned on
    """
    if self._model is None:
      if self._profiling:
        startTime = time.time()

      # Load the model
      self._archiver.loadModel()

      if self._profiling:
        self._modelLoadSec = time.time() - startTime



class _ModelArchiver(object):
  """ Helper class for loading/creating and checkpointing model
  """

  # Name of the attribute that is stored as an integral component of the
  # checkpoint. This attribute contains a list of batchIDs that were processed
  # since the previous checkpoint.
  _BATCH_IDS_CHECKPOINT_ATTR_NAME = "batchIDs"

  # Name of the attribute that is stored as an integral component of the
  # checkpoint. It contains a list of ModelInputRow objects processed since
  # the last full checkpoint for use in preparing the last incremental
  # model checkpoint for new input. The value is in pickle string format.
  _INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME = "incrementalInputSamples"

  _MAX_INCREMENTAL_CHECKPOINT_DATA_ROWS = 100


  def __init__(self, modelID):
    """
    :param modelID: model ID; string
    """
    self._modelID = modelID

    # The model object from OPF ModelFactory; set up by the loadModel() method
    self._model = None

    # The _InputRowEncoder object; set up by the loadModel() method
    self._inputRowEncoder = None

    self._checkpointMgr = ModelCheckpointMgr()

    # True if model was loaded from existing checkpoint or after a full
    # checkpoint is made; False initially if model was created from
    # params. This informs us whether an incremental checkpoint is possible.
    self._hasCheckpoint = False

    self._modelCheckpointBatchIDSetCache = None

    # Input data samples that have accumulated since last full checkpoint
    self._inputSamplesSinceLastFullCheckpointCache = None


  @property
  def model(self):
    """ An OPF Model object or None if not loaded yet """
    return self._model


  @property
  def inputRowEncoder(self):
    """ An _InputRowEncoder object or None if model not loaded yet """
    return self._inputRowEncoder


  @property
  def modelCheckpointBatchIDSet(self):
    """ A sequence of input batch identifiers associated with current
    model checkpoint
    """
    if self._modelCheckpointBatchIDSetCache is None:
      self._loadCheckpointAttributes()
    return self._modelCheckpointBatchIDSetCache


  @property
  def checkpointMgr(self):
    return self._checkpointMgr


  @property
  def _inputSamplesSinceLastFullCheckpoint(self):
    if self._inputSamplesSinceLastFullCheckpointCache is None:
      self._loadCheckpointAttributes()
    return self._inputSamplesSinceLastFullCheckpointCache


  @_inputSamplesSinceLastFullCheckpoint.setter
  def _inputSamplesSinceLastFullCheckpoint(self, value):
    self._inputSamplesSinceLastFullCheckpointCache = value


  @classmethod
  def _encodeDataSamples(cls, dataSamples):
    """
    :param dataSamples: a sequence of data samples to be saved as the
      _INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME checkpoint attribute

    :returns: a string encoding of the data samples
    """
    return base64.standard_b64encode(pickle.dumps(dataSamples,
                                                  pickle.HIGHEST_PROTOCOL))


  @classmethod
  def _decodeDataSamples(cls, dataSamples):
    """
    :param dataSamples: string-encoded data samples from the
      _INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME checkpoint attribute

    :returns: a sequence of data samples
    """
    return pickle.loads(base64.standard_b64decode(dataSamples))


  def _loadCheckpointAttributes(self):
    # Load the checkpoint attributes
    try:
      checkpointAttributes = self._checkpointMgr.loadCheckpointAttributes(
        self._modelID)
    except model_checkpoint_mgr.ModelNotFound:
      self._modelCheckpointBatchIDSetCache = set()
      self._inputSamplesSinceLastFullCheckpoint = []
    else:
      self._modelCheckpointBatchIDSetCache = set(
        checkpointAttributes[self._BATCH_IDS_CHECKPOINT_ATTR_NAME])

      inputSamples = checkpointAttributes.get(
        self._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME)
      if inputSamples:
        self._inputSamplesSinceLastFullCheckpoint = self._decodeDataSamples(
          inputSamples)
      else:
        self._inputSamplesSinceLastFullCheckpoint = []


  def loadModel(self):
    """ Load the model and construct the input row encoder. On success,
    the loaded model may be accessed via the `model` attribute

    :raises: model_checkpoint_mgr.ModelNotFound
    """
    if self._model is not None:
      return

    modelDefinition = None

    # Load the model
    try:
      self._model = self._checkpointMgr.load(self._modelID)
      self._hasCheckpoint = True
    except model_checkpoint_mgr.ModelNotFound:
      # So, we didn't have a checkpoint... try to create our model from model
      # definition params
      self._hasCheckpoint = False
      try:
        modelDefinition = self._checkpointMgr.loadModelDefinition(self._modelID)
      except model_checkpoint_mgr.ModelNotFound:
        raise _ModelRunnerError(errno=htmengineerrno.ERR_NO_SUCH_MODEL,
                                msg="modelID=%s not found" % (self._modelID))
      else:
        modelParams = modelDefinition["modelParams"]

      # TODO: when creating the model from params, do we need to call
      #   its model.setFieldStatistics() method? And where will the
      #   fieldStats come from, anyway?
      self._model = ModelFactory.create(
        modelConfig=modelParams["modelConfig"])
      self._model.enableLearning()
      self._model.enableInference(modelParams["inferenceArgs"])


    # Construct the object for converting a flat input row into a format
    # that is consumable by an OPF model
    try:
      if modelDefinition is None:
        modelDefinition = self._checkpointMgr.loadModelDefinition(
          self._modelID)
    except model_checkpoint_mgr.ModelNotFound:
      raise _ModelRunnerError(errno=htmengineerrno.ERR_NO_SUCH_MODEL,
                              msg="modelID=%s not found" % (self._modelID))
    else:
      inputSchema = modelDefinition["inputSchema"]

    # Convert it to a sequence of FieldMetaInfo instances
    # NOTE: if loadMetaInfo didn't raise, we expect "inputSchema" to be
    #   present; it would be a logic error if it isn't.
    inputFieldsMeta = tuple(FieldMetaInfo(*f) for f in inputSchema)

    self._inputRowEncoder = _InputRowEncoder(fieldsMeta=inputFieldsMeta)

    # If the checkpoint was incremental, feed the cached data into the model
    for inputSample in self._inputSamplesSinceLastFullCheckpoint:
      # Convert a flat input sample into a format that is consumable by an OPF
      # model
      self._inputRowEncoder.appendRecord(inputSample)

      # Infer
      self._model.run(self._inputRowEncoder.getNextRecordDict())


  def saveModel(self, currentRunBatchIDSet, currentRunInputSamples):
    """
    :param currentRunBatchIDSet: a set of batch ids to be saved in model
      checkpoint attributes

    :param currentRunInputSamples: a sequence of model input data sample objects
      for incremental checkpoint; will be saved in checkpoint attributes if an
      incremental checkpoint is performed.
    """
    if self._model is not None:
      self._modelCheckpointBatchIDSetCache = currentRunBatchIDSet.copy()

      if (not self._hasCheckpoint or
          (len(self._inputSamplesSinceLastFullCheckpoint) +
           len(currentRunInputSamples)) >
          self._MAX_INCREMENTAL_CHECKPOINT_DATA_ROWS):
        # Perform a full checkpoint
        self._inputSamplesSinceLastFullCheckpointCache = []

        self._checkpointMgr.save(
          modelID=self._modelID, model=self._model,
          attributes={
            self._BATCH_IDS_CHECKPOINT_ATTR_NAME:
              list(self._modelCheckpointBatchIDSetCache)})

        self._hasCheckpoint = True
      else:
        # Perform an incremental checkpoint
        self._inputSamplesSinceLastFullCheckpoint.extend(currentRunInputSamples)
        attributes = {
          self._BATCH_IDS_CHECKPOINT_ATTR_NAME:
            list(self._modelCheckpointBatchIDSetCache),

          self._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME:
            self._encodeDataSamples(self._inputSamplesSinceLastFullCheckpoint)
        }

        self._checkpointMgr.updateCheckpointAttributes(self._modelID,
                                                       attributes)



class _InputRowEncoder(RecordStreamIface):
  """ We make use of NuPIC's RecordStreamIface for converting a flat input
  row to a dict and adding other fields as required in an input record
  for passing to an OPF model.

  In particular, we're interested in RecordStreamIface.getNextRecordDict().
  """

  def __init__(self, fieldsMeta):
    super(_InputRowEncoder, self).__init__()
    self._fieldsMeta = fieldsMeta
    self._fieldNames = tuple(f.name for f in fieldsMeta)
    self._row = None


  def appendRecord(self, record, inputRef=None):
    """ [ABC method implementation] Saves the record in the underlying storage.
    """
    assert self._row is None
    assert isinstance(record, (list, tuple))
    self._row = record


  def getNextRecord(self, useCache=True):
    """ [ABC method implementation] Returns next available data record from the
    storage. If useCache is False, then don't read ahead and don't cache any
    records.

    retval: a data row (a list or tuple) if available; None, if no more records
             in the table (End of Stream - EOS); empty sequence (list or tuple)
             when timing out while waiting for the next record.
    """
    assert self._row is not None
    row = self._row
    self._row = None
    return row


  def getFieldNames(self):
    """ [ABC method implementation] Returns an array of field names associated
    with the data.
    """
    return self._fieldNames


  def getFields(self):
    """ [ABC method implementation] Returns a sequence of
    nupic.data.fieldmeta.FieldMetaInfo name/type/special tuples for each field
    in the stream. Might be None, if that information is provided externally
    (thru stream def, for example).
    """
    return self._fieldsMeta


  # Satisfy Abstract Base Class requirements for the ABC RecordStreamIface
  # methods that are no-ops for us.
  #
  # TODO: this seems ugly; is there a better way (short of maintaining a
  # separate copy of the getNextRecordDict implementation)
  close = None
  getRecordsRange = None
  getNextRecordIdx = None
  getLastRecords = None
  removeOldData = None
  appendRecords = None
  getBookmark = None
  recordsExistAfter = None
  seekFromEnd = None
  getStats = None
  clearStats = None
  getError = None
  setError = None
  isCompleted = None
  setCompleted = None
  setTimeout = None
  flush = None



def main(argv):
  # Parse command line options
  helpString = (
    "%prog [options]\n"
    "This script runs the Model Runner process.")
  parser = OptionParser(helpString)

  parser.add_option("--modelID", action="store", type="str",
    help="The Model ID string that identifies the model to run.")

  (options, args) = parser.parse_args(argv[1:])
  if len(args) > 0:
    parser.error("Didn't expect any positional args (%r)." % (args,))

  if options.modelID is None:
    parser.error("Missing model ID in command-line")

  with ModelRunner(modelID=options.modelID) as runner:
    runner.run()



if __name__ == "__main__":
  # NOTE: we initialize logging as a service so that our logging output will be
  # funneled via console to our parent process (model_scheduler service)
  LoggingSupport.initService()

  logger = _getLogger()
  logger.setLogPrefix('<%s, SERVICE=MRUN> ' % getStandardLogPrefix())

  try:
    logger.info("{TAG:SWAP.MR.START} argv=%r", sys.argv)
    main(sys.argv)
  except SystemExit as e:
    if e.code != 0:
      logger.exception("{TAG:SWAP.MR.STOP.ABORT}")
      raise
  except:
    logger.exception("{TAG:SWAP.MR.STOP.ABORT}")
    raise

  logger.info("{TAG:SWAP.MR.STOP.OK}")
