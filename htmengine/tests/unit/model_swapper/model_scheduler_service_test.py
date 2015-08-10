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
Unit tests for the Model Swapper's ModelSchedulerService class
"""

from collections import namedtuple
import multiprocessing
import os
import Queue
import signal
import threading
import unittest

from mock import patch, Mock
import psutil

from htmengine.model_swapper import model_scheduler_service
from htmengine.model_swapper.model_scheduler_service import (
  ModelSchedulerService)

from nta.utils.logging_support_raw import LoggingSupport



# Disable warning: Access to a protected member
# pylint: disable=W0212

MemoryUsage = namedtuple("MemoryUsage", ("total",))



def setUpModule():
  LoggingSupport.initTestApp()



@patch.object(model_scheduler_service, "SwapController", autospec=True,
              run=Mock(spec_set=model_scheduler_service.SwapController.run))
class TestModelSchedulerService(unittest.TestCase):
  """ ModelSwapper's ModelSchedulerService unit tests """


  def testCreateModelSchedulerAndCloseIt(self, *_args):
    # Instantiates, then closes ModelSchedulerService
    with ModelSchedulerService(concurrency=3) as ms:
      self.assertIsNotNone(ms._signalPipeReadFD)

    self.assertIsNone(ms._signalPipeReadFD)


  def _runModelSchedulerAndStopItViaSignal(self, signalnum,
                                           expectedRestartValue):
    """ Instantiates ModelSchedulerService instance, runs it in a thread,
    then sends it the given signal and verifies that it stopped gracefully
    and that the run() method returned the expected result.
    """

    def runModelSchedulerThread(ms, runResultQ):
      restart = ms.run()
      runResultQ.put(restart)

    with ModelSchedulerService(concurrency=3) as ms:
      runResultQ = Queue.Queue()
      msThread = threading.Thread(
        target=runModelSchedulerThread,
        name="runModelSchedulerThread",
        args=(ms, runResultQ))
      msThread.setDaemon(True)
      msThread.start()

      # Now stop it
      os.kill(os.getpid(), signalnum)
      msThread.join(timeout=5)
      self.assertFalse(msThread.isAlive())

      restart = runResultQ.get_nowait()
      self.assertEqual(restart, expectedRestartValue)

    self.assertIsNone(ms._signalPipeReadFD)
    self.assertIsNone(ms._signalPipeWriteFD)

    swapController = model_scheduler_service.SwapController.return_value
    swapController.requestStopTS.assert_called_once_with()


  def testRunModelSchedulerAndStopItViaSIGTERM(self, *_args):
    # Instantiates ModelSchedulerService instance, runs it in a thread,
    # then sends it SIGTERM and verifies that it stopped gracefully and that
    # the run() method returned the expected result.
    self._runModelSchedulerAndStopItViaSignal(signalnum=signal.SIGTERM,
                                              expectedRestartValue=False)


  def testRunModelSchedulerAndStopItViaSIGINT(self, *_args):
    # Instantiates ModelSchedulerService instance, runs it in a thread,
    # then sends it SIGINT and verifies that it stopped gracefully and that
    # the run() method returned the expected result.
    self._runModelSchedulerAndStopItViaSignal(signalnum=signal.SIGINT,
                                              expectedRestartValue=False)


  def testRunModelSchedulerAndStopItViaSIGHUP(self, *_args):
    # Instantiates ModelSchedulerService instance, runs it in a thread,
    # then sends it SIGHUP and verifies that it stopped gracefully and that
    # the run() method returned the expected result.
    self._runModelSchedulerAndStopItViaSignal(signalnum=signal.SIGHUP,
                                              expectedRestartValue=True)


  @patch.object(multiprocessing, "cpu_count", return_value=4, autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=21474836480), autospec=True)
  def testGetDefaultConcurrencyCpuBound(self, cpuCountMock, phymemUsageMock,
                                        *_args):
    """Default concurrency when CPU bound."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(), 3)
    cpuCountMock.assert_called_once_with()
    phymemUsageMock.assert_called_once_with()


  @patch.object(os, "_exit", autospec=True)
  def testProgramAbortOnSwapControllerThreadCrash(
      self, osExitMock, swapControllerClassMock):

    osExitArgQ = Queue.Queue()
    osExitMock.side_effect = osExitArgQ.put

    swapControllerMock = swapControllerClassMock.return_value
    swapControllerMock.run.side_effect = Exception(
      "testProgramAbortOnSwapControllerThreadCrash")

    # We run ModelSchedulerService in a thread to avoid deadlocking the test
    # runner if the service doesn't stop as expected
    def runModelSchedulerThread(ms, runResultQ):
      restart = ms.run()
      runResultQ.put(restart)

    with ModelSchedulerService(concurrency=3) as ms:
      runResultQ = Queue.Queue()
      msThread = threading.Thread(
        target=runModelSchedulerThread,
        name="runModelSchedulerThread",
        args=(ms, runResultQ))
      msThread.setDaemon(True)
      msThread.start()

      # Now wait for os._exit to be called
      try:
        exitCode = osExitArgQ.get(timeout=5)
      except Queue.Empty:
        self.fail("Program didn't get aborted via os._exit")

      self.assertEqual(
        exitCode,
        ModelSchedulerService._ABORT_PROGRAM_ON_THREAD_EXCEPTION_EXIT_CODE)

      # Stop ModelSchedulerService
      os.kill(os.getpid(), signal.SIGTERM)
      msThread.join(timeout=5)
      self.assertFalse(msThread.isAlive())

      restart = runResultQ.get_nowait()
      self.assertEqual(restart, False)

    self.assertIsNone(ms._signalPipeReadFD)
    self.assertIsNone(ms._signalPipeWriteFD)

    swapController = model_scheduler_service.SwapController.return_value
    swapController.requestStopTS.assert_called_once_with()



  @patch.object(multiprocessing, "cpu_count", return_value=1, autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=21474836480), autospec=True)
  def testGetDefaultConcurrencyOneCpu(self, cpuCountMock, phymemUsageMock,
                                      *_args):
    """Default concurrency with one CPU."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(), 2)
    cpuCountMock.assert_called_once_with()
    phymemUsageMock.assert_called_once_with()


  @patch.object(multiprocessing, "cpu_count", return_value=8, autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=6442450944), autospec=True)
  def testGetDefaultConcurrencyMemoryBound(self, cpuCountMock, phymemUsageMock,
                                           *_args):
    """Default concurrency when memory bound."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(), 2)
    cpuCountMock.assert_called_once_with()
    phymemUsageMock.assert_called_once_with()


  @patch.object(multiprocessing, "cpu_count", return_value=8, autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=1610612736), autospec=True)
  def testGetDefaultConcurrencyMinimalMemory1(self, cpuCountMock,
                                              phymemUsageMock, *_args):
    """Default concurrency when there is minimal memory after base memory."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(), 2)
    cpuCountMock.assert_called_once_with()
    phymemUsageMock.assert_called_once_with()


  @patch.object(multiprocessing, "cpu_count", return_value=8, autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=610612736), autospec=True)
  def testGetDefaultConcurrencyMinimalMemory2(self, cpuCountMock,
                                              phymemUsageMock, *_args):
    """Default concurrency when there is less memory than base allocation."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(), 2)
    cpuCountMock.assert_called_once_with()
    phymemUsageMock.assert_called_once_with()


  @patch.object(multiprocessing, "cpu_count", autospec=True)
  @patch.object(psutil, "phymem_usage",
                return_value=MemoryUsage(total=21474836480), autospec=True)
  def testGetDefaultConcurrencyExplicit(self, cpuCountMock, phymemUsageMock,
                                        *_args):
    """Concurrency when it is explicitly specified."""
    self.assertEqual(model_scheduler_service._getDefaultConcurrency(7), 7)
    self.assertFalse(cpuCountMock.called)
    self.assertFalse(phymemUsageMock.called)



if __name__ == "__main__":
  unittest.main()
