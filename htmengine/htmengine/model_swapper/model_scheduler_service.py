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
This module implements the Model Scheduler service that's responsible for the
scheduling of the execution of a potentially large number of OPF models within
the confines of a limited system resource footprint. It incorporates
SwapController and friends.
"""

import errno
import fcntl
import multiprocessing
from optparse import OptionParser
import os
import signal
import sys
import threading

import psutil

from htmengine.htmengine_logging import getExtendedLogger, getStandardLogPrefix

from htmengine.model_swapper.swap_controller import SwapController

from nta.utils.error_handling import abortProgramOnAnyException
from nta.utils.logging_support_raw import LoggingSupport



_MODULE_NAME = "htmengine.model_swapper.model_scheduler_service"

_MIN_CONCURRENCY = 2
_SWAP_CONTROLLER_JOIN_TIMEOUT = 60
_BASE_RAM_USAGE = 1073741824  # 1GB
_RAM_PER_SLOT = 2147483648  # 2 GB



def _getLogger():
  return getExtendedLogger(_MODULE_NAME)



class ModelSchedulerService(object):

  # Error code that will be passed to os._exit when the thread that runs
  # SwapController experiences an unhandled exception
  _ABORT_PROGRAM_ON_THREAD_EXCEPTION_EXIT_CODE = 1

  def __init__(self, concurrency):
    self._logger = _getLogger()
    self._concurrency = concurrency

    self._signalPipeReadFD, self._signalPipeWriteFD = os.pipe()
    # Make the write end non-blocking to prevent accidental deadlocking of the
    # signal dispatcher
    fcntl.fcntl(
      self._signalPipeWriteFD,
      fcntl.F_SETFL,
      fcntl.fcntl(self._signalPipeWriteFD, fcntl.F_GETFL) | os.O_NONBLOCK)

    # Register for signals of interest
    self._signalsOfInterest = [signal.SIGHUP, signal.SIGTERM, signal.SIGINT]
    for sig in self._signalsOfInterest:
      signal.signal(sig, self._handleSignal)

    # Create the slot agents and swap controller.
    self._swapController = SwapController(concurrency=concurrency)


  def __enter__(self):
    """ Context Manager protocol method. Allows a ModelSchedulerService instance
    to be used in a "with" statement for automatic clean-up

    Parameters:
    ------------------------------------------------------------------------
    retval:     self.
    """
    return self


  def __exit__(self, excType, excVal, excTb):
    """ Context Manager protocol method. Allows a ModelSchedulerService instance
    to be used in a "with" statement for automatic cleanup

    Returns: False so as not to suppress the exception, if any
    """
    self._close()
    return False


  def _close(self):
    """ Gracefully stop the Model Scheduler """
    self._logger.info("Closing...")

    # Unregister from signal notifications
    for sig in self._signalsOfInterest:
      signal.signal(sig, signal.SIG_DFL)

    os.close(self._signalPipeReadFD)
    self._signalPipeReadFD = None
    os.close(self._signalPipeWriteFD)
    self._signalPipeWriteFD = None


  def run(self):
    """
    Returns: True if service should be restarted, False otherwise
    """
    self._logger.info("Running: pid=%s", os.getpid())
    quitPipeFileObj = os.fdopen(os.dup(self._signalPipeReadFD))

    swapControllerThread = threading.Thread(
        target=self._runSwapControllerThread,
        name="%s-%s" % (self._swapController.__class__.__name__,
                        id(self._swapController)))
    swapControllerThread.setDaemon(True)
    swapControllerThread.start()

    while True:
      try:
        signalnum = int(quitPipeFileObj.readline())
      except IOError as e:
        if e.errno != errno.EINTR:
          raise

        # System call was interrupted by signal - restart it
        continue
      else:
        break
    self._logger.info("Stopping service due to signal %s", signalnum)

    # Call swap controller requestStopTS method and then join the thread
    # running its run method.
    self._swapController.requestStopTS()
    swapControllerThread.join(_SWAP_CONTROLLER_JOIN_TIMEOUT)
    assert not swapControllerThread.isAlive(), (
        "Swap controller thread did not join in the allotted time "
        "(%g seconds)." % _SWAP_CONTROLLER_JOIN_TIMEOUT)

    return signalnum == signal.SIGHUP


  @abortProgramOnAnyException(
    exitCode=_ABORT_PROGRAM_ON_THREAD_EXCEPTION_EXIT_CODE, logger=_getLogger())
  def _runSwapControllerThread(self):
    self._swapController.run()


  def _handleSignal(self, signalnum, _frame):
    """ Handle system signal; write it to the pipe so that it may be processed
    by the main thread.
    """
    try:
      os.write(self._signalPipeWriteFD, "%s\n" % (signalnum,))
    except IOError as e:
      if e.errno in [errno.EWOULDBLOCK, errno.EAGAIN]:
        # Drop the signal if we were overwhelmed by signals to the point of
        # running out of pipe buffer (this shouldn't happen)
        pass
      else:
        raise



def _getDefaultConcurrency(concurrency=None):
  logger = _getLogger()
  if concurrency is None:
    cpuCount = multiprocessing.cpu_count()
    memoryTotal = psutil.phymem_usage().total
    logger.info("CPU count: %i", cpuCount)
    logger.info("Total memory: %i", memoryTotal)
    concurrency = max(min(cpuCount - 1,
                          (memoryTotal - _BASE_RAM_USAGE) / _RAM_PER_SLOT),
                      _MIN_CONCURRENCY)
    logger.info("Computed concurrency for model scheduler: %i", concurrency)
  else:
    logger.info("Concurrency specified explicitly: %i", concurrency)
  return concurrency



def main(argv):
  # Parse command line options
  helpString = (
    "%prog [options]\n"
    "This script runs the htmengine Model Scheduler service.")
  parser = OptionParser(helpString)

  parser.add_option("--concurrency", action="store", type="int", default=None,
    help="An integer value that represents the maximum model "
         "concurrency. Defaults to max(# cores - 1, 1) [default: %default].")

  (options, args) = parser.parse_args(argv[1:])
  if len(args) > 0:
    parser.error("Didn't expect any positional args (%r)." % (args,))

  options.concurrency = _getDefaultConcurrency(options.concurrency)

  needRestart = True
  while needRestart:
    with ModelSchedulerService(concurrency=options.concurrency) as scheduler:
      needRestart = scheduler.run()



if __name__ == "__main__":
  LoggingSupport.initService()

  logger = _getLogger()
  logger.setLogPrefix('<%s, SERVICE=SCHED> ' % getStandardLogPrefix())

  try:
    logger.info("{TAG:SWAP.SCHED.START}")
    main(sys.argv)
  except SystemExit as e:
    if e.code != 0:
      logger.exception("{TAG:SWAP.SCHED.STOP.ABORT}")
      raise
  except:
    logger.exception("{TAG:SWAP.SCHED.STOP.ABORT}")
    raise

  logger.info("{TAG:SWAP.SCHED.STOP.OK}")
