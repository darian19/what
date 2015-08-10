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

"""Integration test for the model_runner subsystem of model swapper."""

# Disable warning: Access to a protected member
# pylint: disable=W0212


import datetime
import itertools
import logging
import subprocess
import sys
import threading
import traceback


import unittest

from nupic.data.fieldmeta import FieldMetaInfo, FieldMetaSpecial, FieldMetaType

from htmengine import htmengineerrno

from htmengine.algorithms.modelSelection.clusterParams import (
    getScalarMetricWithTimeOfDayParams)

from htmengine.model_checkpoint_mgr import model_checkpoint_mgr

from htmengine.model_swapper import model_runner

from htmengine.model_swapper.model_swapper_interface import (
    ModelCommandResult, ModelInferenceResult, ModelInputRow,
    ModelSwapperInterface)

from nta.utils.message_bus_connector import MessageBusConnector

from htmengine.model_swapper.model_swapper_test_utils import (
    ModelSwapperIsolationPatch)
from nta.utils.test_utils import ManagedSubprocessTerminator

from nta.utils.logging_support_raw import LoggingSupport



_LOGGER = logging.getLogger("model_runner_int_test")


def setUpModule():
  LoggingSupport.initTestApp()


@ModelSwapperIsolationPatch(clientLabel="ModelRunnerIntTestCase",
                            logger=_LOGGER)
class ModelRunnerIntTestCase(unittest.TestCase):
  """Tests the model runner at integration-test level."""


  @classmethod
  def _startModelRunnerSubprocess(cls, modelID):
    """
    :returns: the model runner subprocess wrapped in ManagedSubprocessTerminator
    """
    p = subprocess.Popen(
      args=[sys.executable,
            "-m", "htmengine.model_swapper.model_runner",
            "--modelID=" + str(modelID)],
      stdin=subprocess.PIPE, close_fds=True)

    _LOGGER.info("Started model_runner subprocess=%s for modelID=%s",
                 p.pid, modelID)
    return ManagedSubprocessTerminator(p)


  def _consumeResults(self, numExpectedBatches, timeout):
    def runConsumerThread(destList, numExpectedBatches):
      with ModelSwapperInterface() as swapper:
        with swapper.consumeResults() as consumer:
          for batch in consumer:
            destList.append(batch)
            batch.ack()
            _LOGGER.info("Got result batch=%r", batch)
            if len(destList) == numExpectedBatches:
              break

    batches = []
    consumerThread = threading.Thread(
      target=runConsumerThread,
      args=(batches, numExpectedBatches))
    consumerThread.setDaemon(True)
    consumerThread.start()
    consumerThread.join(timeout=timeout)
    if consumerThread.isAlive():
      _LOGGER.error("testModelSwapper: consumer thread is still alive")
    self.assertFalse(consumerThread.isAlive())

    return batches


  def _waitForProcessToStopAndCheck(self, processObj, expectedReturnCode=0):
    # Signal Model Scheduler Service subprocess to shut down and wait for it
    waitResult = dict()
    def runWaiterThread():
      try:
        waitResult["returnCode"] = processObj.wait()
      except:
        _LOGGER.exception("Waiting for process=%r failed", processObj)
        waitResult["exceptionInfo"] = traceback.format_exc()
        raise
      return

    waiterThread = threading.Thread(target=runWaiterThread)
    waiterThread.setDaemon(True)
    waiterThread.start()
    waiterThread.join(timeout=30)
    self.assertFalse(waiterThread.isAlive())

    self.assertIn("returnCode", waitResult)

    if expectedReturnCode is not None:
      self.assertEqual(waitResult["returnCode"], expectedReturnCode,
                       msg=repr(waitResult))


  def testRunModelWithFullThenIncrementalCheckpoints(self):
    # Have model_runner create a full checkpoint, then incremental checkpoint
    modelID = "foobar"

    checkpointMgr = model_checkpoint_mgr.ModelCheckpointMgr()

    with ModelSwapperInterface() as swapperAPI:
      possibleModels = getScalarMetricWithTimeOfDayParams(metricData=[0],
                                                         minVal=0,
                                                         maxVal=1000)

      # Submit requests including a model creation command and two data rows.
      args = possibleModels[0]
      args["inputRecordSchema"] = (
          FieldMetaInfo("c0", FieldMetaType.datetime,
                        FieldMetaSpecial.timestamp),
          FieldMetaInfo("c1", FieldMetaType.float,
                        FieldMetaSpecial.none),
      )

      # Define the model
      _LOGGER.info("Defining the model")
      swapperAPI.defineModel(modelID=modelID, args=args,
                             commandID="defineModelCmd1")

      # Send input rows to the model
      inputRows = [
          ModelInputRow(rowID="rowfoo",
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 00), 5.3]),
          ModelInputRow(rowID="rowbar",
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 15), 2.4]),
      ]

      _LOGGER.info("Submitting batch of %d input rows with ids=[%s..%s]...",
                   len(inputRows), inputRows[0].rowID, inputRows[-1].rowID)
      swapperAPI.submitRequests(modelID=modelID, requests=inputRows)

      # Run model_runner and collect results
      with self._startModelRunnerSubprocess(modelID) as modelRunnerProcess:
        resultBatches = self._consumeResults(numExpectedBatches=2, timeout=15)
        self._waitForProcessToStopAndCheck(modelRunnerProcess)

      with MessageBusConnector() as bus:
        # The results message queue should be empty now
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

      self.assertEqual(len(resultBatches), 2, repr(resultBatches))

      # First result batch should be the first defineModel result
      batch = resultBatches[0]
      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(len(batch.objects), 1)

      result = batch.objects[0]
      self.assertIsInstance(result, ModelCommandResult)
      self.assertEqual(result.method, "defineModel")
      self.assertEqual(result.status, htmengineerrno.SUCCESS)
      self.assertEqual(result.commandID, "defineModelCmd1")

      # The second result batch should be for the two input rows
      batch = resultBatches[1]
      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(len(batch.objects), len(inputRows))

      for inputRow, result in zip(inputRows, batch.objects):
        self.assertIsInstance(result, ModelInferenceResult)
        self.assertEqual(result.status, htmengineerrno.SUCCESS)
        self.assertEqual(result.rowID, inputRow.rowID)
        self.assertIsInstance(result.anomalyScore, float)

      # Verify model checkpoint
      model = checkpointMgr.load(modelID)
      del model

      attrs = checkpointMgr.loadCheckpointAttributes(modelID)
      self.assertIn(model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME,
                    attrs, msg=repr(attrs))
      self.assertEqual(
        len(attrs[model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME]),
        2, msg=repr(attrs))
      self.assertNotIn(
        model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME,
        attrs, msg=repr(attrs))

      # Now, check incremental checkpointing
      inputRows2 = [
          ModelInputRow(rowID=2,
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 20), 2.7]),
          ModelInputRow(rowID=3,
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 25), 3.9]),
      ]

      _LOGGER.info("Submitting batch of %d input rows with ids=[%s..%s]...",
                   len(inputRows2), inputRows2[0].rowID, inputRows2[-1].rowID)
      inputBatchID = swapperAPI.submitRequests(modelID=modelID,
                                               requests=inputRows2)

      with self._startModelRunnerSubprocess(modelID) as modelRunnerProcess:
        resultBatches = self._consumeResults(numExpectedBatches=1, timeout=15)
        self._waitForProcessToStopAndCheck(modelRunnerProcess)

      with MessageBusConnector() as bus:
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

      batch = resultBatches[0]
      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(len(batch.objects), len(inputRows2))

      for inputRow, result in zip(inputRows2, batch.objects):
        self.assertIsInstance(result, ModelInferenceResult)
        self.assertEqual(result.status, htmengineerrno.SUCCESS)
        self.assertEqual(result.rowID, inputRow.rowID)
        self.assertIsInstance(result.anomalyScore, float)

      model = checkpointMgr.load(modelID)
      del model

      attrs = checkpointMgr.loadCheckpointAttributes(modelID)
      self.assertIn(model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME,
                    attrs, msg=repr(attrs))
      self.assertSequenceEqual(
        attrs[model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME],
        [inputBatchID], msg=repr(attrs))

      self.assertIn(
        model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME,
        attrs, msg=repr(attrs))

      self.assertSequenceEqual(
        model_runner._ModelArchiver._decodeDataSamples(
          attrs[model_runner._ModelArchiver.
                _INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME]),
        [row.data for row in inputRows2], msg=repr(attrs))

      # Final run with incremental checkpointing
      inputRows3 = [
          ModelInputRow(rowID=4,
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 30), 4.7]),
          ModelInputRow(rowID=5,
                        data=[datetime.datetime(2014, 5, 23, 8, 13, 35), 5.9]),
      ]

      _LOGGER.info("Submitting batch of %d input rows with ids=[%s..%s]...",
                   len(inputRows3), inputRows3[0].rowID, inputRows3[-1].rowID)
      inputBatchID = swapperAPI.submitRequests(modelID=modelID,
                                               requests=inputRows3)

      with self._startModelRunnerSubprocess(modelID) as modelRunnerProcess:
        resultBatches = self._consumeResults(numExpectedBatches=1, timeout=15)
        self._waitForProcessToStopAndCheck(modelRunnerProcess)

      with MessageBusConnector() as bus:
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

      batch = resultBatches[0]
      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(len(batch.objects), len(inputRows3))

      for inputRow, result in zip(inputRows3, batch.objects):
        self.assertIsInstance(result, ModelInferenceResult)
        self.assertEqual(result.status, htmengineerrno.SUCCESS)
        self.assertEqual(result.rowID, inputRow.rowID)
        self.assertIsInstance(result.anomalyScore, float)

      model = checkpointMgr.load(modelID)
      del model

      attrs = checkpointMgr.loadCheckpointAttributes(modelID)

      self.assertIn(model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME,
                    attrs, msg=repr(attrs))
      self.assertSequenceEqual(
        attrs[model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME],
        [inputBatchID], msg=repr(attrs))

      self.assertIn(
        model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME,
        attrs, msg=repr(attrs))
      self.assertSequenceEqual(
        model_runner._ModelArchiver._decodeDataSamples(
          attrs[model_runner._ModelArchiver.
                _INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME]),
        [row.data for row in itertools.chain(inputRows2, inputRows3)],
        msg=repr(attrs))

      # Delete the model
      _LOGGER.info("Deleting the model=%s", modelID)
      swapperAPI.deleteModel(modelID=modelID, commandID="deleteModelCmd1")

      with self._startModelRunnerSubprocess(modelID) as modelRunnerProcess:
        resultBatches = self._consumeResults(numExpectedBatches=1, timeout=15)
        self._waitForProcessToStopAndCheck(modelRunnerProcess)

      self.assertEqual(len(resultBatches), 1, repr(resultBatches))

      # First result batch should be the first defineModel result
      batch = resultBatches[0]
      self.assertEqual(batch.modelID, modelID)
      self.assertEqual(len(batch.objects), 1)

      result = batch.objects[0]
      self.assertIsInstance(result, ModelCommandResult)
      self.assertEqual(result.method, "deleteModel")
      self.assertEqual(result.status, htmengineerrno.SUCCESS)
      self.assertEqual(result.commandID, "deleteModelCmd1")

      with MessageBusConnector() as bus:
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

        # The model input queue should be deleted now
        self.assertFalse(
          bus.isMessageQeueuePresent(
            swapperAPI._getModelInputQName(modelID=modelID)))

      # The model checkpoint should be gone too
      with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
        checkpointMgr.load(modelID)

      with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
        checkpointMgr.loadModelDefinition(modelID)

      with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
        checkpointMgr.loadCheckpointAttributes(modelID)

      with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
        checkpointMgr.remove(modelID)



if __name__ == '__main__':
  unittest.main()
