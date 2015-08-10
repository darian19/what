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
Unit tests for the Model Swapper's SlotAgent class
"""

from functools import partial
import Queue
import os
import threading
import unittest


from mock import Mock, patch


from htmengine.model_swapper import slot_agent

from nta.utils.logging_support_raw import LoggingSupport



# Disable warning: Access to a protected member
# pylint: disable=W0212



def setUpModule():
  LoggingSupport.initTestApp()



class SlotAgentTestCase(unittest.TestCase):
  """ ModelSwapper's SlotAgent unit tests """


  @patch.object(slot_agent, "ModelRunnerProxy", autospec=True,
                side_effect=RuntimeError(
                  "ModelRunnerProxy constructor should not have been called"))
  def testCreateSlotAgentAndCloseIt(self, _modelRunnerProxyClassMock):
    sa = slot_agent.SlotAgent(slotID=1)
    self.assertIsNotNone(sa._thread)

    t = threading.Thread(target=sa.close)
    t.setDaemon(True)
    t.start()
    t.join(timeout=5)
    self.assertFalse(t.isAlive())
    self.assertIsNone(sa._thread)


  @patch.object(
    slot_agent, "ModelRunnerProxy", autospec=True,
    stopGracefully=Mock(spec_set=slot_agent.ModelRunnerProxy.stopGracefully))
  def testStartModelAndStopIt(self, modelRunnerProxyClassMock):
    modelFinishedQ = Queue.Queue()

    def modelFinishedCallback(modelID, exitStatus):
      modelFinishedQ.put((modelID, exitStatus))

    # Configure ModelRunnerProxy instance mock
    modelRunnerProxyMock = modelRunnerProxyClassMock.return_value
    modelRunnerProxyMock.stopGracefully.side_effect = lambda: 0

    sa = slot_agent.SlotAgent(slotID=1)

    modelID = "abc"
    sa.startModel(
      modelID=modelID,
      modelFinishedCallback=partial(modelFinishedCallback, modelID))
    sa.stopModel()
    self.assertEqual((modelID, 0), modelFinishedQ.get(timeout=5))
    sa.releaseSlot()

    t = threading.Thread(target=sa.close)
    t.setDaemon(True)
    t.start()
    t.join(timeout=5)
    self.assertFalse(t.isAlive())
    self.assertIsNone(sa._thread)

    # Verify ModelRunnerProxy constructor calls
    self.assertEqual(modelRunnerProxyClassMock.call_count, 1)

    # Very modelRunnerProxyMock.stopGracefully calls
    self.assertEqual(modelRunnerProxyMock.stopGracefully.call_count, 1)


  @patch.object(
    slot_agent, "ModelRunnerProxy", autospec=True,
    stopGracefully=Mock(spec_set=slot_agent.ModelRunnerProxy.stopGracefully))
  def testStartModelAndCloseSlotAgent(self, modelRunnerProxyClassMock):
    modelFinishedQ = Queue.Queue()

    def modelFinishedCallback(modelID, exitStatus):
      modelFinishedQ.put((modelID, exitStatus))

    # Configure ModelRunnerProxy instance mock
    modelRunnerProxyMock = modelRunnerProxyClassMock.return_value
    modelRunnerProxyMock.stopGracefully.side_effect = lambda: 0

    sa = slot_agent.SlotAgent(slotID=1)

    modelID = "abc"
    sa.startModel(
      modelID=modelID,
      modelFinishedCallback=partial(modelFinishedCallback, modelID))

    t = threading.Thread(target=sa.close)
    t.setDaemon(True)
    t.start()
    t.join(timeout=5)
    self.assertFalse(t.isAlive())
    self.assertIsNone(sa._thread)

    # Make sure modelFinishedCallback wasn't called
    self.assertTrue(modelFinishedQ.empty())

    # Verify ModelRunnerProxy constructor calls
    self.assertEqual(modelRunnerProxyClassMock.call_count, 1)

    # Verify modelRunnerProxyMock.stopGracefully calls
    self.assertEqual(modelRunnerProxyMock.stopGracefully.call_count, 1)


  @patch.object(slot_agent, "ModelRunnerProxy", autospec=True)
  def testSwapModelsInSlotAgent(self, modelRunnerProxyClassMock):
    # Create mock ModelRunnerProxy factory
    modelRunnerProxyMocks = []
    def createModelRunnerProxyMock(
      modelID, onTermination, logger):  # pylint: disable=W0613
      modelRunnerProxyMock = Mock(
        spec_set=slot_agent.ModelRunnerProxy,
        stopGracefully=Mock(
          spec_set=slot_agent.ModelRunnerProxy.stopGracefully,
          return_value=0))

      modelRunnerProxyMocks.append(modelRunnerProxyMock)

      return modelRunnerProxyMock


    modelRunnerProxyClassMock.side_effect = createModelRunnerProxyMock

    modelFinishedQ = Queue.Queue()

    def modelFinishedCallback(modelID, exitStatus):
      modelFinishedQ.put((modelID, exitStatus))

    sa = slot_agent.SlotAgent(slotID=1)

    # Test swapping of the models in the single SlotAgent instance
    modelIDs = ["abc", "def"]

    for modelID in modelIDs:
      sa.startModel(
        modelID=modelID,
        modelFinishedCallback=partial(modelFinishedCallback, modelID))
      sa.stopModel()
      self.assertEqual((modelID, 0), modelFinishedQ.get(timeout=5))
      sa.releaseSlot()

    # Close slot agent
    t = threading.Thread(target=sa.close)
    t.setDaemon(True)
    t.start()
    t.join(timeout=5)
    self.assertFalse(t.isAlive())
    self.assertIsNone(sa._thread)

    # Verify ModelRunnerProxy constructor calls
    self.assertEqual(modelRunnerProxyClassMock.call_count, len(modelIDs))

    # Very modelRunnerProxyMock.stopGracefully calls
    self.assertEqual(len(modelRunnerProxyMocks), len(modelIDs))
    for modelRunnerProxyMock in modelRunnerProxyMocks:
      self.assertEqual(modelRunnerProxyMock.stopGracefully.call_count, 1)


  @patch.object(
    slot_agent, "ModelRunnerProxy", autospec=True,
    side_effect=RuntimeError("Something that should trigger "
                             "os._exit() from SlotAgent event loop."))
  def testSystemExitOnUnhandledExceptionInEventLoopThread(
    self, _modelRunnerProxyClassMock):
    # Test that an unhandled exception in SlotAgent's event loop thread results
    # in os._exit().

    modelFinishedQ = Queue.Queue()
    def modelFinishedCallback(modelID, exitStatus):
      modelFinishedQ.put((modelID, exitStatus))

    # Patch os._exit and run model in SlotAgent
    osExitCodeQ = Queue.Queue()
    with patch.object(os, "_exit", autospec=True,
                      side_effect=osExitCodeQ.put):
      sa = slot_agent.SlotAgent(slotID=1)

      modelID = "abc"
      sa.startModel(
        modelID=modelID,
        modelFinishedCallback=partial(modelFinishedCallback, modelID))

      # Wait for the call to os._exit()
      # NOTE: if we get the Queue.Empty exception, it means that we didn't get
      #  the expected call to os._exit()
      exitCode = osExitCodeQ.get(timeout=5)
      self.assertEqual(
        exitCode,
        slot_agent._EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD)
      self.assertNotEqual(exitCode, 0)



if __name__ == '__main__':
  unittest.main()
