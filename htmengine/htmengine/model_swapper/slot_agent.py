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
This module implements the SlotAgent class that manages a single ModelRunner
execution slot within a Model Scheduler service instance.
"""

import errno
import os
import Queue
import signal
import subprocess
import sys
import threading


from nupic.support.decorators import logExceptions

from htmengine import htmengine_logging

from nta.utils.error_handling import abortProgramOnAnyException



_MODULE_NAME = "htmengine.model_swapper.slot_agent"


_EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD = 1


def _getLogger():
  return htmengine_logging.getExtendedLogger(_MODULE_NAME)



class ModelRunnerProxy(object):
  """ Proxy for creating, controlling, and monitoring a ModelRunner process """


  _MAX_WAIT_FOR_GRACEFUL_STOP_SEC = 60*4
  _MAX_WAIT_AFTER_SIGKILL_SEC = 10


  class ModelRunnerIOError(Exception):
    """ Error communicating with ModelRunner; it probably died """
    pass


  def __init__(self, modelID, onTermination, logger):
    """
    :param onTermination: thread-safe callback that will be called on
      termination of the ModelRunner process
    """
    self._logger = logger
    self._modelID = modelID
    self._onTermination = onTermination

    self._process = subprocess.Popen(
      args=[sys.executable,
            "-m", "htmengine.model_swapper.model_runner",
            "--modelID=" + str(modelID)],
      stdin=subprocess.PIPE,
      close_fds=True)

    self._pid = self._process.pid

    self._logger.debug("%r: Started ModelRunner", self)

    # Start thread that notifies our client when the process terminates
    self._monitorThread = threading.Thread(
      target=self._runProcessMonitorThread,
      name="%s-waitPID-%s" % (self.__class__.__name__, self._pid,))
    self._monitorThread.setDaemon(True)
    self._monitorThread.start()


  def __repr__(self):
    return "%s<model=%s, pid=%s, returnCode=%s>" % (
      self.__class__.__name__, self._modelID,
      self._pid, self._process.returncode)


  def stopGracefully(self):
    """ Gracefully Stop Model Runner; blocking.

    :returns: return code from ModelRunner process
    """
    # Signal to ModelRunner that it should stop after it finishes processing
    # the input that we have sent it thus far
    self._logger.debug("%r: Stopping ModelRunner", self)
    self._process.stdin.close()

    # Wait for it to finish
    pid = self._pid
    self._monitorThread.join(timeout=self._MAX_WAIT_FOR_GRACEFUL_STOP_SEC)
    if self._monitorThread.isAlive():
      # Timed out, so force-kill it this time
      self._logger.error("%r: Graceful shutdown of ModelRunner timed out; "
                         "sending it SIGKILL", self)
      try:
        os.kill(pid, signal.SIGKILL)
      except OSError as e:
        if e.errno == errno.ESRCH:
          # "no such process" - our thread must have already reaped it, and
          # should be exiting shortly
          pass
        else:
          raise

      # Wait for it again - it should exit really soon
      self._monitorThread.join(timeout=self._MAX_WAIT_AFTER_SIGKILL_SEC)
      assert not self._monitorThread.isAlive()

    assert self._process.returncode is not None
    self._logger.debug("%r: ModelRunner stopped", self)
    return self._process.returncode


  def sendStrings(self, strings):
    """ Send strings to ModelRunner. Does not add line separators.

    :param strings: sequence of strings to send to ModelRunner.
    """
    try:
      self._process.stdin.writelines(strings)
    except IOError as e:
      self._logger.exception("%r: IO error writing strings to ModelRunner",
                             self)
      raise self.ModelRunnerIOError("%r: IO error writing strings to "
                                    "ModelRunner: %r" % (self, e))


  def flush(self):
    """ Flush an cached data that is destined for ModelRunner """
    try:
      self._process.stdin.flush()
    except IOError as e:
      self._logger.exception("%r: IO error flushing ModelRunner's stdin",
                             self)
      raise self.ModelRunnerIOError("%r: IO error flushing ModelRunner's "
                                    "stdin: %r" % (self, e))


  @abortProgramOnAnyException(
    _EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD,
    logger=_getLogger())
  @logExceptions(_getLogger)
  def _runProcessMonitorThread(self):
    self._logger.debug("%s: _runProcessMonitorThread is running", self)
    self._process.wait()
    self._logger.debug("%s: ModelRunner subprocess terminated", self)
    self._onTermination()



class SlotAgent(object):
  """ Manage a single ModelRunner execution slot within a Model Scheduler
  service instance """

  # Commands to the agent's command thread
  _START_MODEL_METHOD = "start-model"
  _STOP_MODEL_METHOD = "stop-model"
  _RELEASE_SLOT_METHOD = "release-model"
  _CLOSE_AGENT_METHOD = "close"
  _MODEL_RUNNER_EXITED = "model-runner-exited"

  _THREAD_JOIN_TIMEOUT_SEC = 60


  def __init__(self, slotID):
    """
    slotID: slot identifier for logging
    """
    self._logger = _getLogger()

    self._slotID = slotID

    # ID of the model, if any, currently associated with this SlotAgent
    # instance; used for logging and error-checking at the interface only.
    # WARNING: not syncrhonized with the event loop thread!
    self._modelID = None

    self._eventQ = Queue.Queue()

    # Create our event loop thread instance
    self._thread = threading.Thread(target=self._runEventLoop,
                                    name="SlotAgentEventLoop-" + str(id(self)))
    # Allow process to exit even if thread is still running
    self._thread.setDaemon(True)
    # Start our event loop
    self._thread.start()


  def __repr__(self):
    return "%s<slotID=%s, modelID=%s>" % (self.__class__.__name__,
                                          self._slotID, self._modelID)


  def close(self):
    """ Close the SlotAgent as soon as possible; blocking.
    Abort ModelRunner, if any, without invoking the user-supplied
    modelFinishedCallback and without requiring the releaseSlot
    handshake. See also stopModel and releaseSlot.
    """
    self._logger.debug("%r: {TAG:SWAP.SA.CLOSE.REQ} model=%s",
                       self, self._modelID)
    self._eventQ.put({"method" : self._CLOSE_AGENT_METHOD})
    self._thread.join(timeout=self._THREAD_JOIN_TIMEOUT_SEC)
    assert not self._thread.isAlive(), (
      "SlotAgent's event loop thread didn't stop")
    self._thread = None
    self._logger.debug("%r: {TAG:SWAP.SA.CLOSE.JOIN.DONE}", self)


  def startModel(self, modelID, modelFinishedCallback):
    """ Submit a request to start the requested model with the given modelID
    and feed it input records and commands from the given input queue.

    :param modelID: model ID (string)
    :param modelFinishedCallback: callback to inform of completion; takes one
      arg: ModelRunner process exit status number per os.WEXITSTATUS (0 when
      successful).
    """
    self._logger.debug("%r: {TAG:SWAP.SA.MODEL.START.REQ} model=%s",
                       self, modelID)
    assert self._modelID is None, repr(self._modelID)

    self._modelID = modelID
    self._eventQ.put({"method" : self._START_MODEL_METHOD,
                      "modelID" : modelID,
                      "modelFinishedCallback" : modelFinishedCallback})


  def stopModel(self):
    """ Submit a request to stop running this SlotAgent's current model
    gracefully; the request completes asynchronously; the slot agent will invoke
    the user-supplied modelFinishedCallback upon completion; the callback MUST
    be acnowledged via releaseSlot() before starting the next model; See
    startModel for more info about modelFinishedCallback.
    """
    assert self._modelID is not None
    self._logger.debug("%r: {TAG:SWAP.SA.MODEL.STOP.REQ} model=%s",
                       self, self._modelID)
    self._eventQ.put({"method" : self._STOP_MODEL_METHOD})


  def releaseSlot(self):
    """ The user (SwapController) needs to call this method to sync up with the
    Slot Agent after accounting for modelFinishedCallback. This helps with
    diagnostics by letting the Slot Agent know that it shouldn't expect any more
    model-specific events until the next startModel request.
    """
    assert self._modelID is not None
    self._logger.debug("%r: {TAG:SWAP.SA.MODEL.RELEASE.REQ} model=%s",
                       self, self._modelID)
    self._modelID = None
    self._eventQ.put({"method" : self._RELEASE_SLOT_METHOD})


  @abortProgramOnAnyException(
    _EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD,
    logger=_getLogger())
  @logExceptions(_getLogger)
  def _runEventLoop(self):
    """ Thread function for servicing the slot: starts the ModelRunner process,
    feeds data to it, stops it, detects the stop, and notifies user that it
    stopped.

    TODO: do we need to explicitly exit the process if there is an exception in
          the context of the thread?
    """
    modelState = None

    while True:
      doStopModel = doClose = False

      # Process the next SlotAgent command
      evt = self._eventQ.get()
      method = evt["method"]

      if method is self._START_MODEL_METHOD:
        assert modelState is None, repr(modelState)
        modelID = evt["modelID"]
        self._logger.debug("%r: {TAG:SWAP.SA.MODEL.STARTING} model=%s", self,
                           modelID)
        modelRunner = ModelRunnerProxy(
          modelID=modelID,
          onTermination=lambda: self._eventQ.put(
            {"method" : self._MODEL_RUNNER_EXITED}),
          logger=self._logger)
        modelState = _CurrentModelState(
          modelID=evt["modelID"], modelRunner=modelRunner,
          modelFinishedCallback=evt["modelFinishedCallback"])
        self._logger.info("%r: {TAG:SWAP.SA.MODEL.STARTED} modelState=%s", self,
                          modelState)

      elif method is self._STOP_MODEL_METHOD:
        assert not modelState.stopModelRequested
        modelState.stopModelRequested = True
        doStopModel = True

      elif method is self._MODEL_RUNNER_EXITED:
        # ModelRunner proxy informed us that model runner process exited
        # NOTE: we will get this method regardless of whether it exited on its
        # own or at our request.
        self._logger.debug("%s: received ModelRunner termination notification",
                           self)
        if not modelState.stopModelPending:
          doStopModel = True

      elif method is self._RELEASE_SLOT_METHOD:
        assert modelState.stopModelPending, (
          "Handling release-slot, but stopModelPending is False")
        assert modelState.modelExitStatus is not None, (
          "Handling release-slot, but modelExitStatus is None")
        self._logger.debug(
          "%r: {TAG:SWAP.SA.SLOT.RELEASE.DONE} modelState=%s", self, modelState)
        modelState = None

      elif method is self._CLOSE_AGENT_METHOD:
        doClose = True

      else:
        assert False, "Unexpected method: " + str(method)


      def stopModel(doCallback):
        modelState.stopModelPending = True
        self._logger.debug(
          "%r: {TAG:SWAP.SA.MODEL.STOP.PENDING} modelState=%r",
          self, modelState)
        modelState.modelExitStatus = modelState.modelRunner.stopGracefully()
        self._logger.info("%r: {TAG:SWAP.SA.MODEL.STOP.DONE} modelState=%r",
                          self, modelState)
        if doCallback:
          modelState.modelFinishedCallback(modelState.modelExitStatus)


      if doStopModel or doClose:
        if doClose:
          self._logger.debug("%r: {TAG:SWAP.SA.CLOSE.PENDING} modelState=%r",
                             self, modelState)

        if modelState is not None:
          if not modelState.stopModelPending:
            stopModel(doCallback=not doClose)
          elif doStopModel:
            # NOTE: this may happen when we experience a failure in IO with the
            #  model and stop it at about the same time that the user requested
            #  model-stop
            self._logger.warn(
              "%r: Got model-stop request while model stop was "
              "already pending; modelState=%r", self, modelState)

        if doClose:
          # Model is stopped, we're done!
          break


    self._logger.debug("%r: {TAG:SWAP.SA.CLOSE.DONE}", self)



class _CurrentModelState(object):
  """ State of the model being processed; used by SlotAgent implementation """

  # We make use of __slots__ so that the interpreter will catch typos in
  # member assignments
  __slots__ = ("modelID", "modelRunner", "modelFinishedCallback",
               "stopModelPending", "stopModelRequested", "modelFailed",
               "modelExitStatus", "numInputBatchesForwarded")


  def __init__(self, modelID, modelRunner, modelFinishedCallback):
    # Model ID of the model being executed in the ModelRunner process
    self.modelID = modelID


    # A ModelRunnerProxy-like instance
    self.modelRunner = modelRunner

    # Method to call when ModelRunner process exits
    self.modelFinishedCallback = modelFinishedCallback

    # True when we're waiting for ModelRunner to exit gracefully after
    # ModelSwapper tells us to stop the model or when we detect an error sending
    # data to the ModelRunner process or when ModelRunner exits prematurely
    self.stopModelPending = False

    # True when stop-model was formally requested via SlotAgent.stopModel
    self.stopModelRequested = False

    # True when model failed (e.g., due to IOError sending data to
    # ModelRunner); can coinside with stopModelRequested
    self.modelFailed = False

    # ModelRunner's exist status when its exit is detected
    self.modelExitStatus = None

    # Number of input batch objects forwarded to ModelRunner for processing
    self.numInputBatchesForwarded = 0


  def __repr__(self):
    return ("%s<modelID=%s, stopPend=%s, stopReq=%s, modelFailed=%s, "
            "exitStatus=%s, modelRunner=%r>") % (
      self.__class__.__name__, self.modelID, self.stopModelPending,
      self.stopModelRequested, self.modelFailed, self.modelExitStatus,
      self.modelRunner)
