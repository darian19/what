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
Unit tests for the Model Swapper's SwapController class
"""

import logging
import os
import Queue
import sys
import threading
import time
import unittest


import mock
from mock import Mock, MagicMock, patch


from htmengine.model_swapper import model_swapper_interface
from htmengine.model_swapper import swap_controller
from htmengine.model_swapper.swap_controller import SwapController

from nta.utils.logging_support_raw import LoggingSupport



# Dispable warning: invalid name for variable; because @patch.multiple forces
# kwarg args of the same name as the patched attribute; e.g., SlotAgent
# pylint: disable=C0103

# Disable warning: Access to a protected member
# pylint: disable=W0212

# Disable warning: Catching too general exception
# pylint: disable=W0703



g_logger = logging.getLogger(
  "htmengine.tests.unit.model_swapper.swap_controller_test")


def setUpModule():
  LoggingSupport.initTestApp()


class _ExtendedQueue(Queue.Queue):
  """ Adds waitUntilEmpty capability """
  def __init__(self):
    Queue.Queue.__init__(self)
    self.__mutex = threading.Lock()
    self.__emptyCondition = threading.Condition(self.__mutex)


  def __updateWaitUntilEmptyState(self, ):
    """ Support waitUntilEmpty() """
    if Queue.Queue.empty(self):
      g_logger.info("Q became empty")
      self.__emptyCondition.acquire()
      try:
        self.__emptyCondition.notifyAll()
      finally:
        self.__emptyCondition.release()


  def get(self, block=True, timeout=None):
    """ Override Queue.Queue.get """
    msg = Queue.Queue.get(self, block=block, timeout=timeout)

    self.__updateWaitUntilEmptyState()

    return msg


  def get_nowait(self):
    msg = Queue.Queue.get_nowait(self)

    self.__updateWaitUntilEmptyState()

    return msg

  def put(self, item, block=True, timeout=None):
    """ Override Queue.Queue.put """
    Queue.Queue.put(self, item, block=block, timeout=timeout)


  def waitUntilEmpty(self, timeout):
    """ Not part of ModelSwapperInterface; part of test support logic. Waits for
    the queue to become empty or timeout. Raises AssertionError on timeout. NOTE
    that the Queue.Queue.join method doesn't support timeout, which prevents us
    from using it in our test logic for the fear of deadlocking the test.
    """
    self.__emptyCondition.acquire()
    try:
      endTime = time.time() + timeout
      while not Queue.Queue.empty(self):
        remainingTime = endTime - time.time()
        assert remainingTime > 0.0
        self.__emptyCondition.wait(remainingTime)

      g_logger.info("Wait is over for InputMessageQueue empty wait")
    finally:
      self.__emptyCondition.release()


class DummyConsumer(object):
  """ Functional in-proc replacement for consumer mocks
  """

  def __init__(self):
    self.q = _ExtendedQueue()


  def __enter__(self):
    return self


  def __exit__(self, *args):
    return False


  def __iter__(self):
    while True:
      yield self.q.get()



class _ModelInputDescriptor(object):
  """ For _DummySlotAgent """

  def __init__(self, requestBatches=None, consumeSizes=None):
    if requestBatches is None:
      self.requestBatchesQ = None
    else:
      self.requestBatchesQ = _ExtendedQueue()
      for batch in requestBatches:
        self.requestBatchesQ.put(batch)

    self.consumeSizesList = (list(consumeSizes)
                             if consumeSizes is not None else None)

    self.requestBatchesProcessedQ = _ExtendedQueue()



class _DummySlotAgent(object):
  """ A dummy SlotAgent implementation for testing; API-compatible with
  model_swapper.slot_agent.SlotAgent.

  See API documentation in htmengine.model_swapper.slot_agent.SlotAgent
  """

  def __init__(self, slotID, getModelInputDescriptor=None):
    """
    getModelInputDescriptor:
      _ModelInputDescriptor getModelInputDescriptor(modeID)
    """
    self.slotID = slotID
    self.getModelInputDescriptor = getModelInputDescriptor
    self.modelID = None
    self.stopModelPending = False
    self.modelFinishedCallback = None
    self.numCloseCalls = 0
    self.numStartModelCalls = 0
    self.numStopModelCalls = 0
    self.numReleaseSlotCalls = 0
    self.inputReaderThread = None


  def close(self):
    assert self.numCloseCalls == 0
    self.numCloseCalls += 1
    if self.modelID is not None and not self.stopModelPending:
      self._stopModel(doCallback=False)


  def startModel(self, modelID, modelFinishedCallback):
    self.numStartModelCalls += 1
    assert self.numCloseCalls == 0
    assert self.modelID is None, repr(self.modelID)
    assert modelID
    assert modelFinishedCallback
    assert callable(modelFinishedCallback)
    self.modelID = modelID
    self.modelFinishedCallback = modelFinishedCallback

    # Simulate reading of input messages by the model
    def runInputReaderThread(inQ, readSize, destQ):
      for _i in xrange(readSize):
        destQ.put(inQ.get())

    if self.getModelInputDescriptor is not None:
      inputDesc = self.getModelInputDescriptor(self.modelID)

      if inputDesc.consumeSizesList is not None:
        self.inputReaderThread = threading.Thread(
          target=runInputReaderThread,
          kwargs=dict(
            inQ=inputDesc.requestBatchesQ,
            readSize=inputDesc.consumeSizesList.pop(0),
            destQ=inputDesc.requestBatchesProcessedQ))
        self.inputReaderThread.setDaemon(True)
        self.inputReaderThread.start()


  def stopModel(self):
    self.numStopModelCalls += 1
    assert self.numCloseCalls == 0
    assert not self.stopModelPending
    assert self.modelID is not None
    self._stopModel(doCallback=True)


  def releaseSlot(self):
    self.numReleaseSlotCalls += 1
    assert self.numCloseCalls == 0
    assert self.stopModelPending
    assert self.modelID is not None
    self.stopModelPending = False
    self.modelID = None


  def _stopModel(self, doCallback):
    assert self.modelID is not None
    if self.inputReaderThread is not None:
      self.inputReaderThread.join()
      self.inputReaderThread = None

    if doCallback:
      self.modelFinishedCallback(0)
    self.modelFinishedCallback = None
    self.stopModelPending = True
    # NOTE: we leave resetting of modelID to releaseSlot


def _createModelSwapperInterfaceInstanceMock():
  swapperMock = MagicMock(
    spec_set=swap_controller.ModelSwapperInterface,
    __enter__=Mock(spec_set=swap_controller.ModelSwapperInterface.__enter__),

    consumeModelSchedulerNotifications=Mock(
      spec_set=swap_controller.ModelSwapperInterface. \
                                consumeModelSchedulerNotifications),

    modelInputPending=Mock(
      spec_set=swap_controller.ModelSwapperInterface.modelInputPending),

    initSchedulerNotification=Mock(
      spec_set=swap_controller.ModelSwapperInterface.initSchedulerNotification))

  swapperMock.__enter__.return_value = swapperMock


  return swapperMock



def _createModelInputNotification(modelID):
  return model_swapper_interface._ConsumedNotification(
      value=modelID,
      ack=Mock(spec_set=lambda: None, return_value=None))



class TestSwapController(unittest.TestCase):
  """ ModelSwapper's SwapController unit tests """


  @patch.multiple(swap_controller, autospec=True,
                  ModelSwapperInterface=mock.DEFAULT,
                  SlotAgent=mock.DEFAULT)
  def testCreateSwapControllerAndDeleteIt(self, **_kwargs):
    # Instantiates, then deletes SwapController
    sc = SwapController(concurrency=3)

    self.assertEqual(len(sc._slotAgents), 3)

    del sc


  @patch.object(swap_controller, "ModelSwapperInterface", autospec=True,
                return_value=_createModelSwapperInterfaceInstanceMock())
  @patch.object(swap_controller, "SlotAgent", autospec=True)
  def testRunSwapControllerAndStopIt(
    self, _slotAgentClassMock, modelSwapperInterfaceClassMock):
    # Instantiate SwapController instance, run it in a separate thread,
    # then stop SwapController.

    # Configure ModelSwapperInterface instance mock
    swapperMock = modelSwapperInterfaceClassMock.return_value
    notificationConsumer = DummyConsumer()
    swapperMock.consumeModelSchedulerNotifications.return_value = (
      notificationConsumer)

    sc = SwapController(concurrency=3)
    self.assertEqual(len(sc._slotAgents), 3)

    # Run it in a thread
    def runSwapControllerThread(sc, runResultQ):
      r = sc.run()
      runResultQ.put(r)

    runResultQ = Queue.Queue()
    scThread = threading.Thread(
      target=runSwapControllerThread,
      name="runSwapControllerThread",
      args=(sc, runResultQ))
    scThread.setDaemon(True)
    scThread.start()

    # Now stop it
    sc.requestStopTS()
    # Prod notification reader's consumer loop to detect the stop request and
    # exit gracefully by adding a dummy message
    notificationConsumer.q.put(None)

    # There isn't much going on, it should stop immediately
    scThread.join(timeout=5)
    self.assertFalse(scThread.isAlive())

    runResult = runResultQ.get_nowait()
    self.assertIsNone(runResult)


  @patch.object(swap_controller, "ModelSwapperInterface", autospec=True,
                return_value=_createModelSwapperInterfaceInstanceMock())
  @patch.object(swap_controller, "SlotAgent", autospec=True)
  def testSimpleSingleSuccessfulModelInputAndStop(
    self, slotAgentClassMock, modelSwapperInterfaceClassMock):
    # Instantiate SwapController instance, run it in a separate thread,
    # feed some data for one model, then stop SwapController.

    # Configure ModelSwapperInterface instance mock
    swapperMock = modelSwapperInterfaceClassMock.return_value
    notificationConsumer = DummyConsumer()
    swapperMock.consumeModelSchedulerNotifications.return_value = (
      notificationConsumer)
    swapperMock.modelInputPending.return_value = False

    # Configure SlotAgent class mock to create dummy slot agent instances and
    # add them to our list so that we can introspect them later
    modelID = "abcd"
    requestBatches = ("firstBatch", "secondBatch",)
    modelInputDesc = _ModelInputDescriptor(
      requestBatches=requestBatches,
      consumeSizes=[2,])
    modelInputDescriptors = {
      modelID: modelInputDesc
    }
    slotAgents = []
    slotAgentClassMock.side_effect = (lambda slotID:
      slotAgents.append(
        _DummySlotAgent(slotID, modelInputDescriptors.__getitem__))
      or slotAgents[-1])

    # Run SwapController in a thread
    concurrency = 3
    sc = SwapController(concurrency=concurrency)
    self.assertEqual(len(sc._slotAgents), concurrency)
    self.assertEqual(len(slotAgents), concurrency)

    def runSwapControllerThread(sc, runResultQ):
      try:
        g_logger.info("Swap Controller run-thread is running")
        r = sc.run()
        runResultQ.put(r)
      except:
        runResultQ.put(sys.exc_info()[1])
        raise
      finally:
        g_logger.info("Swap Controller run-thread is exiting")


    runResultQ = Queue.Queue()
    scThread = threading.Thread(
      target=runSwapControllerThread,
      name="runSwapControllerThread",
      args=(sc, runResultQ))
    scThread.setDaemon(True)
    scThread.start()

    # Prod SwapController to process model input
    notificationConsumer.q.put(_createModelInputNotification(modelID))

    # Wait for the model input queue to drain
    g_logger.info("Waiting for model inputQ to be empty")
    modelInputDesc.requestBatchesQ.waitUntilEmpty(timeout=5)
    self.assertTrue(modelInputDesc.requestBatchesQ.empty())
    g_logger.info("model inputQ is empty")

    # Now stop SwapController
    g_logger.info("Requesting SwapController to stop")
    sc.requestStopTS()

    # So that the notification reader thread detects stop request and exits:
    notificationConsumer.q.put(_createModelInputNotification(modelID))

    g_logger.info("Waiting for SwapController run-thread to stop")
    scThread.join(timeout=5)
    self.assertFalse(scThread.isAlive())
    g_logger.info("SwapController run-thread stopped")

    # Verify that SwapController.run() returned without error
    self.assertIsNone(runResultQ.get_nowait())

    # Verify that all slot agents were closed
    for sa in slotAgents:
      self.assertEqual(sa.numCloseCalls, 1)

    # Verify that a single slot agent handled all the input data
    targetSA = None
    for sa in slotAgents:
      if sa.numStartModelCalls > 0:
        self.assertIsNone(targetSA)
        targetSA = sa
        self.assertEqual(sa.numStartModelCalls, 1)
        self.assertEqual(sa.numStopModelCalls, 1)
        self.assertEqual(modelInputDesc.requestBatchesProcessedQ.qsize(),
                         len(requestBatches))
      else:
        self.assertEqual(sa.numStartModelCalls, 0)
        self.assertEqual(sa.numStopModelCalls, 0)

    self.assertIsNotNone(targetSA)


  @patch.object(swap_controller, "ModelSwapperInterface", autospec=True,
                return_value=_createModelSwapperInterfaceInstanceMock())
  @patch.object(swap_controller, "SlotAgent", autospec=True)
  def testModelPreemptionAndStop(
    self, slotAgentClassMock, modelSwapperInterfaceClassMock):
    # Test preemption of slots in SwapController

    # Configure ModelSwapperInterface instance mock
    swapperMock = modelSwapperInterfaceClassMock.return_value
    notificationConsumer = DummyConsumer()
    swapperMock.consumeModelSchedulerNotifications.return_value = (
      notificationConsumer)
    swapperMock.modelInputPending.side_effect = (lambda modelID:
      not modelInputDescriptors[modelID].requestBatchesQ.empty())

    # Configure SlotAgent class mock to create dummy slot agent instances and
    # add them to our list so that we can introspect them later
    concurrency = 3
    multiplier = 3
    numModels = concurrency * multiplier

    # Generate model IDs
    modelIDs = [hex(i) for i in xrange(numModels)]

    requestBatches = ("firstBatch", "secondBatch",)

    modelInputDescriptors = dict((
      modelID,
      _ModelInputDescriptor(
        requestBatches=requestBatches,
        consumeSizes=[1, 1]))
      for modelID in modelIDs)

    slotAgents = []
    slotAgentClassMock.side_effect = (lambda slotID:
      slotAgents.append(
        _DummySlotAgent(slotID, modelInputDescriptors.__getitem__))
      or slotAgents[-1])

    # Run SwapController in a thread
    sc = SwapController(concurrency=concurrency)
    self.assertEqual(len(sc._slotAgents), concurrency)
    self.assertEqual(len(slotAgents), concurrency)

    def runSwapControllerThread(sc, runResultQ):
      try:
        g_logger.info("Swap Controller run-thread is running")
        r = sc.run()
        runResultQ.put(r)
      finally:
        g_logger.info("Swap Controller run-thread is exiting")


    runResultQ = Queue.Queue()
    scThread = threading.Thread(
      target=runSwapControllerThread,
      name="runSwapControllerThread",
      args=(sc, runResultQ))
    scThread.setDaemon(True)
    scThread.start()

    # Prod SwapController to process all models
    for modelID in modelIDs:
      notificationConsumer.q.put(_createModelInputNotification(modelID))

    # Wait for model input queues to drain
    for modelID, desc in modelInputDescriptors.iteritems():
      g_logger.info("Waiting for model=%s inputQ to be empty", modelID)
      desc.requestBatchesQ.waitUntilEmpty(timeout=5)
      self.assertTrue(desc.requestBatchesQ.empty())
      g_logger.info("model=%s inputQ is empty", modelID)

    # Verify that all SlotAgents are occupied
    for sa in slotAgents:
      self.assertIsNotNone(sa.modelID)

    # Now stop SwapController
    g_logger.info("Requesting SwapController to stop")
    sc.requestStopTS()

    # So that the notification reader thread detects stop request and exits:
    notificationConsumer.q.put(_createModelInputNotification(modelID))

    g_logger.info("Waiting for SwapController run-thread to stop")
    scThread.join(timeout=5)
    self.assertFalse(scThread.isAlive())
    g_logger.info("SwapController run-thread stopped")

    # Verify that SwapController.run() returned without error
    self.assertIsNone(runResultQ.get_nowait())

    # Verify that all slot agents were closed
    for sa in slotAgents:
      self.assertEqual(sa.numCloseCalls, 1)

    # Verify that input data of all models was drained
    for modelID, desc in modelInputDescriptors.iteritems():
      g_logger.info("Verify empty input for model=%s", modelID)
      self.assertEqual(desc.requestBatchesQ.qsize(), 0)
      self.assertEqual(desc.requestBatchesProcessedQ.qsize(),
                       len(requestBatches))

    # Verify that all slot agents did work and were closed
    for sa in slotAgents:
      g_logger.info(
        "sa=%s: closeCalls=%s; startCalls=%s; stopCalls=%s; releaseCalls=%s",
        sa.slotID,
        sa.numCloseCalls,
        sa.numStartModelCalls,
        sa.numStopModelCalls,
        sa.numReleaseSlotCalls)

      self.assertEqual(sa.numCloseCalls, 1)

      self.assertEqual(sa.numStartModelCalls, multiplier * len(requestBatches))
      self.assertEqual(sa.numStopModelCalls, multiplier * len(requestBatches))
      self.assertEqual(sa.numReleaseSlotCalls, multiplier * len(requestBatches))


  @patch.object(swap_controller, "ModelSwapperInterface", autospec=True,
                return_value=_createModelSwapperInterfaceInstanceMock())
  @patch.object(swap_controller, "SlotAgent", autospec=True)
  @patch.object(os, "_exit", autospec=True)
  def testProgramAbortOnInputReaderThreadCrash(
    self, osExitMock, _slotAgentClassMock, modelSwapperInterfaceClassMock):
    # Verify that a crash in notification reader thread results in a call
    # to os._exit()

    # Configure ModelSwapperInterface mock
    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.initSchedulerNotification.side_effect = Exception(
      "testProgramAbortOnInputReaderThreadCrash")

    osExitArgQ = Queue.Queue()
    osExitMock.side_effect = osExitArgQ.put

    sc = SwapController(concurrency=1)
    self.assertEqual(len(sc._slotAgents), 1)

    # Request stop, so that the main loop will exit ASAP
    sc.requestStopTS()

    # Run SwapController in a thread
    def runSwapControllerThread(sc, runResultQ):
      try:
        g_logger.info("Swap Controller run-thread is running")
        try:
          r = sc.run()
        except Exception as e:
          runResultQ.put(e)
        else:
          runResultQ.put(r)
      finally:
        g_logger.info("Swap Controller run-thread is exiting")


    runResultQ = Queue.Queue()
    scThread = threading.Thread(
      target=runSwapControllerThread,
      name="runSwapControllerThread",
      args=(sc, runResultQ))
    scThread.setDaemon(True)
    scThread.start()

    # Wait for os._exit to be called
    self.assertEqual(
      osExitArgQ.get(timeout=5),
      SwapController._EXIT_CODE_ON_FAILURE_OF_NOTIFICATION_READER_THREAD)

    # Wait for the run-thread to stop
    g_logger.info("Waiting for SwapController run-thread to stop")
    scThread.join(timeout=5)
    self.assertFalse(scThread.isAlive())
    g_logger.info("SwapController run-thread stopped")

    runResult = runResultQ.get_nowait()
    self.assertIsNone(runResult)


  @patch.object(
    SwapController,
    "_NOTIFICATION_READER_THREAD_START_WAIT_TIMEOUT_SEC",
    new=0.1)
  @patch.object(swap_controller, "ModelSwapperInterface", autospec=True)
  @patch.object(swap_controller, "SlotAgent", autospec=True)
  def testDetectNotificationReaderThreadTargetCallFailed(
    self, _slotAgentClassMock, _modelSwapperInterfaceClassMock):
    # Reproduce failure to invoke the SwapController's input-reader thread
    # target and verify that SwapController's event loop raises the expected
    # exception

    sc = SwapController(concurrency=1)
    self.assertEqual(len(sc._slotAgents), 1)

    # Patch SwapController's input-thread object with one that will exhibit a
    # failure while trying to call the thread target
    def expectTwoArgs(_a, _b):
      pass
    t = threading.Thread(target=expectTwoArgs)
    t.setDaemon(True)
    patch.multiple(sc, _notificationReaderThread=t).start()

    # Attempt to run it in a thread
    def runSwapControllerThread(sc, runResultQ):
      try:
        g_logger.info("Swap Controller run-thread is running")
        try:
          r = sc.run()
        except Exception as e:
          runResultQ.put(e)
        else:
          runResultQ.put(r)
      finally:
        g_logger.info("Swap Controller run-thread is exiting")


    runResultQ = Queue.Queue()
    scThread = threading.Thread(
      target=runSwapControllerThread,
      name="runSwapControllerThread",
      args=(sc, runResultQ))
    scThread.setDaemon(True)
    scThread.start()

    # Wait for the run-thread to stop
    g_logger.info("Waiting for SwapController run-thread to stop")
    scThread.join(timeout=5)
    self.assertFalse(scThread.isAlive())
    g_logger.info("SwapController run-thread stopped")

    # Confirm the expected exception
    runResult = runResultQ.get_nowait()
    self.assertIsInstance(runResult, AssertionError)
    self.assertIn("Notification-reader thread failed to start in time",
                  runResult.args[0])



if __name__ == '__main__':
  unittest.main()
