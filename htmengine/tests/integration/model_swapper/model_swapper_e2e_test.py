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

"""Integration test for the model swapper system."""

import datetime
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
from htmengine.model_swapper.model_swapper_interface import (
  ModelCommandResult,
  ModelInferenceResult,
  ModelInputRow,
  ModelSwapperInterface)
from nta.utils.message_bus_connector import MessageBusConnector

from htmengine.model_swapper.model_swapper_test_utils import (
  ModelSwapperIsolationPatch)

from nta.utils.logging_support_raw import LoggingSupport



_LOGGER = logging.getLogger("model_swapper_e2e_test")


def setUpModule():
  LoggingSupport.initTestApp()



# Disable warning: Access to a protected member
# pylint: disable=W0212



@ModelSwapperIsolationPatch(clientLabel="ModelSwapperE2ETestCase",
                            logger=_LOGGER)
class ModelSwapperE2ETestCase(unittest.TestCase):
  """Tests the entire engine by exercising the model swapper interface."""

  @classmethod
  def _startModelSchedulerSubprocess(cls, concurrency=5):
    p = subprocess.Popen(
      args=[sys.executable,
            "-m", "htmengine.model_swapper.model_scheduler_service",
            "--concurrency=" + str(concurrency)],
      stdin=subprocess.PIPE, close_fds=True)

    _LOGGER.info("Started model_scheduler_service subprocess=%s", p)
    return p


  def _consumeResults(self, numExpected, timeout):
    def runConsumerThread(destList, numExpected):
      with ModelSwapperInterface() as swapper:
        with swapper.consumeResults() as consumer:
          for batch in consumer:
            destList.append(batch)
            batch.ack()
            _LOGGER.info("Got result batch=%r", batch)
            if len(destList) == numExpected:
              break

    batches = []
    consumerThread = threading.Thread(
      target=runConsumerThread,
      args=(batches, numExpected))
    consumerThread.setDaemon(True)
    consumerThread.start()
    consumerThread.join(timeout=timeout)
    if consumerThread.isAlive():
      _LOGGER.error("testModelSwapper: consumer thread is still alive")
    self.assertFalse(consumerThread.isAlive())

    return batches



  def testModelSwapper(self):
    """Simple end-to-end test of the model swapper system."""

    modelSchedulerSubprocess = self._startModelSchedulerSubprocess()
    self.addCleanup(lambda: modelSchedulerSubprocess.kill()
                    if modelSchedulerSubprocess.returncode is None
                    else None)

    modelID = "foobar"
    resultBatches = []

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

      # Attempt to define the same model again
      _LOGGER.info("Defining the model again")
      swapperAPI.defineModel(modelID=modelID, args=args,
                             commandID="defineModelCmd2")

      # Send input rows to the model
      inputRows = [
          ModelInputRow(rowID="rowfoo",
                        data=[datetime.datetime(2013, 5, 23, 8, 13, 00), 5.3]),
          ModelInputRow(rowID="rowbar",
                        data=[datetime.datetime(2013, 5, 23, 8, 13, 15), 2.4]),
      ]
      _LOGGER.info("Submitting batch of %d input rows...", len(inputRows))
      swapperAPI.submitRequests(modelID=modelID, requests=inputRows)

      _LOGGER.info("These models have pending input: %s",
                   swapperAPI.getModelsWithInputPending())

      # Retrieve all results.
      # NOTE: We collect results via background thread to avoid
      # deadlocking the test runner in the event consuming blocks unexpectedly
      _LOGGER.info("Reading all batches of results...")

      numBatchesExpected = 3
      resultBatches.extend(
        self._consumeResults(numBatchesExpected, timeout=20))

      self.assertEqual(len(resultBatches), numBatchesExpected)

      with MessageBusConnector() as bus:
        # The results message queue should be empty now
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))


      # Delete the model
      _LOGGER.info("Deleting the model")
      swapperAPI.deleteModel(modelID=modelID, commandID="deleteModelCmd1")

      _LOGGER.info("Waiting for model deletion result")
      resultBatches.extend(self._consumeResults(1, timeout=20))

      self.assertEqual(len(resultBatches), 4)

      with MessageBusConnector() as bus:
        # The results message queue should be empty now
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

        # The model input queue should be deleted now
        self.assertFalse(
          bus.isMessageQeueuePresent(
            swapperAPI._getModelInputQName(modelID=modelID)))

      # Try deleting the model again, to make sure there are no exceptions
      _LOGGER.info("Attempting to delete the model again")
      swapperAPI.deleteModel(modelID=modelID, commandID="deleteModelCmd1")


    # Verify results

    # First result batch should be the first defineModel result
    batch = resultBatches[0]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "defineModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "defineModelCmd1")

    # The second result batch should for the second defineModel result for the
    # same model
    batch = resultBatches[1]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "defineModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "defineModelCmd2")

    # The third batch should be for the two input rows
    batch = resultBatches[2]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), len(inputRows))

    for inputRow, result in zip(inputRows, batch.objects):
      self.assertIsInstance(result, ModelInferenceResult)
      self.assertEqual(result.status, htmengineerrno.SUCCESS)
      self.assertEqual(result.rowID, inputRow.rowID)
      self.assertIsInstance(result.anomalyScore, float)

    # The fourth batch should be for the "deleteModel"
    batch = resultBatches[3]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "deleteModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "deleteModelCmd1")

    # Signal Model Scheduler Service subprocess to shut down and wait for it
    waitResult = dict()
    def runWaiterThread():
      try:
        waitResult["returnCode"] = modelSchedulerSubprocess.wait()
      except:
        _LOGGER.exception("Waiting for modelSchedulerSubprocess failed")
        waitResult["exceptionInfo"] = traceback.format_exc()
        raise
      return

    modelSchedulerSubprocess.terminate()
    waiterThread = threading.Thread(target=runWaiterThread)
    waiterThread.setDaemon(True)
    waiterThread.start()
    waiterThread.join(timeout=30)
    self.assertFalse(waiterThread.isAlive())

    self.assertEqual(waitResult["returnCode"], 0, msg=repr(waitResult))


  @unittest.skip("MER-1499")
  def testCloneModel(self):

    modelSchedulerSubprocess = self._startModelSchedulerSubprocess()
    self.addCleanup(lambda: modelSchedulerSubprocess.kill()
                    if modelSchedulerSubprocess.returncode is None
                    else None)

    modelID = "abc"
    destModelID = "def"

    resultBatches = []

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

      resultBatches.extend(self._consumeResults(1, timeout=20))
      self.assertEqual(len(resultBatches), 1)

      # Clone the just-defined model
      _LOGGER.info("Cloning model")
      swapperAPI.cloneModel(modelID, destModelID,
                            commandID="cloneModelCmd1")

      resultBatches.extend(self._consumeResults(1, timeout=20))
      self.assertEqual(len(resultBatches), 2)

      # Send input rows to the clone
      inputRows = [
          ModelInputRow(rowID="rowfoo",
                        data=[datetime.datetime(2013, 5, 23, 8, 13, 00), 5.3]),
          ModelInputRow(rowID="rowbar",
                        data=[datetime.datetime(2013, 5, 23, 8, 13, 15), 2.4]),
      ]
      _LOGGER.info("Submitting batch of %d input rows...", len(inputRows))
      swapperAPI.submitRequests(modelID=destModelID, requests=inputRows)

      _LOGGER.info("These models have pending input: %s",
                   swapperAPI.getModelsWithInputPending())

      resultBatches.extend(self._consumeResults(1, timeout=20))
      self.assertEqual(len(resultBatches), 3)

      with MessageBusConnector() as bus:
        # The results message queue should be empty now
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))


      # Delete the model
      _LOGGER.info("Deleting the model")
      swapperAPI.deleteModel(modelID=destModelID,
                             commandID="deleteModelCmd1")

      _LOGGER.info("Waiting for model deletion result")
      resultBatches.extend(self._consumeResults(1, timeout=20))

      self.assertEqual(len(resultBatches), 4)

      with MessageBusConnector() as bus:
        # The results message queue should be empty now
        self.assertTrue(bus.isEmpty(swapperAPI._resultsQueueName))

        # The model input queue should be deleted now
        self.assertFalse(
          bus.isMessageQeueuePresent(
            swapperAPI._getModelInputQName(modelID=destModelID)))


    # Verify results

    # First result batch should be the defineModel result
    batch = resultBatches[0]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "defineModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "defineModelCmd1")

    # The second result batch should for the cloneModel result
    batch = resultBatches[1]
    self.assertEqual(batch.modelID, modelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "cloneModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "cloneModelCmd1")

    # The third batch should be for the two input rows
    batch = resultBatches[2]
    self.assertEqual(batch.modelID, destModelID)
    self.assertEqual(len(batch.objects), len(inputRows))

    for inputRow, result in zip(inputRows, batch.objects):
      self.assertIsInstance(result, ModelInferenceResult)
      self.assertEqual(result.status, htmengineerrno.SUCCESS)
      self.assertEqual(result.rowID, inputRow.rowID)
      self.assertIsInstance(result.anomalyScore, float)

    # The fourth batch should be for the "deleteModel"
    batch = resultBatches[3]
    self.assertEqual(batch.modelID, destModelID)
    self.assertEqual(len(batch.objects), 1)

    result = batch.objects[0]
    self.assertIsInstance(result, ModelCommandResult)
    self.assertEqual(result.method, "deleteModel")
    self.assertEqual(result.status, htmengineerrno.SUCCESS)
    self.assertEqual(result.commandID, "deleteModelCmd1")

    # Signal Model Scheduler Service subprocess to shut down and wait for it
    waitResult = dict()
    def runWaiterThread():
      try:
        waitResult["returnCode"] = modelSchedulerSubprocess.wait()
      except:
        _LOGGER.exception("Waiting for modelSchedulerSubprocess failed")
        waitResult["exceptionInfo"] = traceback.format_exc()
        raise
      return

    modelSchedulerSubprocess.terminate()
    waiterThread = threading.Thread(target=runWaiterThread)
    waiterThread.setDaemon(True)
    waiterThread.start()
    waiterThread.join(timeout=30)
    self.assertFalse(waiterThread.isAlive())

    self.assertEqual(waitResult["returnCode"], 0, msg=repr(waitResult))



if __name__ == '__main__':
  unittest.main()
