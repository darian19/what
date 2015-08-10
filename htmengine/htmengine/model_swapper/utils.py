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
Miscellaneous utilties used by Model Swaper subsystems.
"""

import errno
import fcntl
import os
import signal
import threading


from nupic.support.decorators import logExceptions

from htmengine.model_swapper.model_swapper_interface import (
  ModelSwapperInterface)

from htmengine import htmengine_logging
from htmengine.utils import createGuid

_MODULE_NAME = "htmengine.model_swapper.utils"



def _getLogger():
  return htmengine_logging.getExtendedLogger(_MODULE_NAME)



class ChildProcessReaper(object):
  """ Must be initialized only from the main thread and used only as a
  singleton!

  Monitors SIGCHLD and reaps completed child processes and notifies interested
  parties.
  """


  _singleton = None


  @classmethod
  def init(cls):
    """ [WARNING: NOT thread-safe] Initialize ChildProcessReaper. MUST be called
    from the MAIN thread of the process before using other API's, such as
    register and unregister.
    """
    if cls._singleton is None:
      cls._singleton = cls()


  @classmethod
  def register(cls, cb):
    """ [thread-safe] Register a child process reaper callback.

    cb is passed two args: pid and returnCode. If the process was terminated by
      signal, returnCode is a negative number whose absolute value is the signal
      number; otherwise, the returnCode is the os.WEXITSTATUS of the process's
      exit status bitfield.
    """
    cls._singleton._register(cb)  # pylint: disable=W0212


  @classmethod
  def unregister(cls, cb):
    """ [thread-safe] Unregister a child process reaper callback.
    """
    cls._singleton._unregister(cb)  # pylint: disable=W0212


  def __init__(self):
    assert self._singleton is None

    self.mutex = threading.Lock()
    self._callbacks = set()

    self._sigchldPending = False
    self._signalPipeReadFD, self._signalPipeWriteFD = os.pipe()
    # Make the write end non-blocking to prevent accidental deadlocking of the
    # signal dispatcher
    fcntl.fcntl(
      self._signalPipeWriteFD,
      fcntl.F_SETFL,
      fcntl.fcntl(self._signalPipeWriteFD, fcntl.F_GETFL) | os.O_NONBLOCK)

    self._reaperThread = threading.Thread(target=self._runReaperThread,
                                          name="sigchld-reaper")
    # Allow process to exit even if thread is still running
    self._reaperThread.setDaemon(True)
    self._reaperThread.start()

    def handleSigchld(signalnum, _frame):
      if self._sigchldPending:
        return

      self._sigchldPending = True
      try:
        os.write(self._signalPipeWriteFD, chr(signalnum))
      except IOError as e:
        if e.errno not in [errno.EWOULDBLOCK, errno.EAGAIN]:
          raise

        # Drop the signal since we were overwhelmed by signals to the point of
        # running out of pipe buffer (this shouldn't happen)


    signal.signal(signal.SIGCHLD, handleSigchld)


  def _register(self, cb):
    with self.mutex:
      self._callbacks.add(cb)

  def _unregister(self, cb):
    with self.mutex:
      self._callbacks.remove(cb)


  @logExceptions(_getLogger)
  def _runReaperThread(self):
    while True:
      try:
        os.read(self._signalPipeReadFD, 1)
      except IOError as e:
        if e.errno != errno.EINTR:
          raise

        # System call was interrupted by signal - restart it
        continue
      else:
        self._sigchldPending = False
        while True:
          try:
            r = os.waitpid(0, os.WNOHANG)
          except OSError as e:
            if e.errno != errno.ECHILD:
              raise
            break
          else:
            pid, exitStatus = r
            if os.WIFSIGNALED(exitStatus):
              returnCode = -os.WTERMSIG(exitStatus)
            elif os.WIFEXITED(exitStatus):
              returnCode = os.WEXITSTATUS(exitStatus)
            else:
              # Should never happen
              raise RuntimeError("Unexpected child exit status: %r" %
                                 (exitStatus,))
            with self.mutex:
              for cb in self._callbacks:
                cb(pid, returnCode)


def createHTMModel(modelId, params):
  """ Dispatch command to create HTM model

  :param modelId: unique identifier of the metric row

  :param modelParams: model params for creating a scalar model per ModelSwapper
    interface

  :param modelSwapper: htmengine.model_swapper.model_swapper_interface object
  """
  with ModelSwapperInterface() as modelSwapper:
    modelSwapper.defineModel(modelID=modelId, args=params,
                             commandID=createGuid())



def deleteHTMModel(modelId):
  with ModelSwapperInterface() as modelSwapper:
    modelSwapper.deleteModel(modelID=modelId, commandID=createGuid())




