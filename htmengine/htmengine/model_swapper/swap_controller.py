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
This module implements the SwapController class that orchestrates model swapping
across a fixed set of SlotAgent instances based on incoming model commands and
records.
"""

from functools import partial
import logging
import Queue
import threading
import time

from nupic.support.decorators import logExceptions, logEntryExit

from htmengine.model_swapper import ModelSwapperConfig
from htmengine.model_swapper.model_swapper_interface import (
    ModelSwapperInterface)
from htmengine.model_swapper.slot_agent import SlotAgent
from nta.utils.error_handling import abortProgramOnAnyException
from htmengine import htmengine_logging


_MODULE_NAME = "htmengine.model_swapper.swap_controller"



def _getLogger():
  return htmengine_logging.getExtendedLogger(_MODULE_NAME)



class SwapController(object):
  """ Orchestrate model swapping across a fixed set of SlotAgent instances based
  on incoming model commands and records.
  """


  # Event methods for the SwapController's event loop. These are handled by
  # instance methods with names constructed as follows:
  # "_handle" + method + "Event" (e.g., _handleStopEventLoopRequestEvent)
  _NEW_INPUT_NOTIFY_METHOD = "NewInputNotify"
  _MODEL_DONE_NOTIFY_METHOD = "ModelDoneNotify"
  _STOP_EVENT_LOOP_REQUEST_METHOD = "StopEventLoopRequest"


  _NOTIFICATION_READER_THREAD_START_WAIT_TIMEOUT_SEC = 5
  _NOTIFICATION_READER_THREAD_JOIN_TIMEOUT_SEC = 10

  _EXIT_CODE_ON_FAILURE_OF_NOTIFICATION_READER_THREAD = 1

  def __init__(self, concurrency):
    """
    concurrency: allowed number of model slots
    """
    self._logger = _getLogger()

    self._profiling = (
      ModelSwapperConfig().getboolean("debugging", "profiling") or
      self._logger.isEnabledFor(logging.DEBUG))

    # Allowed number of model slots
    self._concurrency = concurrency

    # Input-reader thread target function sets this when it starts running to
    # let our event loop know that things are off to a good start
    self._notificationReaderStartedEvent = threading.Event()

    self._notificationMutex = threading.Lock()
    # Mutex used to guaranteed that no further model input notifications will
    # be added to main event queue once self._stopNotificationReader is set

    # _runNotificationReaderThread will not process any more notifications
    # once it detects that this flag is true
    self._stopNotificationReader = False

    # The event loop will exit some time after an event handler sets this flag
    # to True
    self._eventLoopStopPending = False

    # (non-thread-safe) The tuple of all slot agents
    self._slotAgents = tuple(SlotAgent(slotID=i) for i in xrange(concurrency))
    assert self._slotAgents

    # Thread-safe event queue for SwapController
    self._eventQ = Queue.Queue()

    # Main event loop's ModelSwapperInterface instance. MUST NOT use from
    # threads because ModelSwapperInterface
    self._mainSwapper = ModelSwapperInterface()

    # A (non-thread-safe) FIFO of models that are waiting to be scheduled for
    # running; there is incoming data for them that needs to be processed
    self._waitingModelsFIFO = []

    # A (non-thread-safe) map of modelIDs to _RunningModelInfo instances
    self._runningModelsMap = dict()

    # A (non-thread-safe) list of free slot indexes into the self._slotsAgents
    # tuple
    self._freeSlots = list(xrange(len(self._slotAgents)))

    # (non-thread-safe) Indexes of SlotAgents pending preemption
    self._pendingPreemptSlotsSet = set()

    self._notificationReaderThread = threading.Thread(
      target=self._runNotificationReaderThread,
      name="%s-input-reader-%s" % (self.__class__.__name__, id(self)))
    # Allow process to exit even if thread is still running
    self._notificationReaderThread.setDaemon(True)


  @logEntryExit(_getLogger, logging.INFO)
  @logExceptions(_getLogger)
  def run(self):
    """ Run SwapController; blocking """
    # Start our input-reader thread
    self._logger.info("Starting Notification Reader thread")
    self._notificationReaderThread.start()
    self._notificationReaderStartedEvent.wait(
      timeout=self._NOTIFICATION_READER_THREAD_START_WAIT_TIMEOUT_SEC)
    assert self._notificationReaderStartedEvent.is_set(), \
      "Notification-reader thread failed to start in time"

    self._logger.info("Notification Reader started, now entering Event Loop")

    requestedStopOfRemainingModels = False

    while True:
      if self._eventLoopStopPending:
        if not self._runningModelsMap and not self._waitingModelsFIFO:
          # All models are idle now, so close Slot Agents and bail out
          for sa in self._slotAgents:
            sa.close()

          self._logger.info("Closed all Slot Agents; leaving event loop")
          break

        elif not self._waitingModelsFIFO and not requestedStopOfRemainingModels:
          # Only running models remain, so request to stop them gracefully
          assert self._runningModelsMap

          for modelInfo in self._runningModelsMap.itervalues():
            if modelInfo.slotIndex not in self._pendingPreemptSlotsSet:
              self._slotAgents[modelInfo.slotIndex].stopModel()
              self._pendingPreemptSlotsSet.add(modelInfo.slotIndex)

          requestedStopOfRemainingModels = True
          self._logger.info("Requested stop of remaining running models")


      # Get and handle next event
      evt = self._eventQ.get()
      method = evt["method"]
      handler = getattr(self, "_handle" + method + "Event")
      handler(**evt)


  def requestStopTS(self):
    """ [thread-safe; non-blocking] Enqueue a request to stop the
    SwapController. This will cause the instance's run() method to return
    eventually
    """
    # This will prevent notification reader thread from processing any more
    # notifications. By the time we release the lock, no new notifications
    # will be placed in our event queue, so we can proceed with graceful
    # shutdown.
    with self._notificationMutex:
      self._stopNotificationReader = True

    self._logger.info("Requested stop of notification processing")

    # Asynchronously request graceful shutdown of our event loop. This allows
    # all remaining events from the notification-reader to be handled
    # prior to commensing graceful shutdown.
    self._logger.info("Requesting event-loop shutdown")
    self._eventQ.put({"method" : self._STOP_EVENT_LOOP_REQUEST_METHOD})


  def _newInputNotifyTS(self, modelID):
    """ [thread-safe] Notify Model Swapper that new input data arrived for the
    given model

    :param modelID: ID of the model for which new data arrived
    """
    self._eventQ.put(
      {"method" : self._NEW_INPUT_NOTIFY_METHOD, "modelID" : modelID})


  def _modelDoneNotifyTS(self, modelID, exitStatus):
    """ [thread-safe] Notify Model Swapper that a ModelRunner process completed.
    This method is passed as a callback to the SlotAgent that
    runs the model.

    :param modelID: model ID of model that completed execution
    :param exitStatus: the model's ModelRunner process exit status per
      os.WEXITSTATUS
    """
    self._eventQ.put({"method" : self._MODEL_DONE_NOTIFY_METHOD,
                      "modelID" : modelID, "exitStatus" : exitStatus,
                      "endTime" : time.time()})


  def _handleStopEventLoopRequestEvent(self, method):  # pylint: disable=W0613
    """ Set a flag to signal our event loop that it's time for graceful shutdown
    of the event loop. The event is enqueued by the "stop request" hander after
    it blocks further processing of notifications by notification reader.
    """
    self._eventLoopStopPending = True
    self._logger.info("Set _eventLoopStopPending")


  def _handleNewInputNotifyEvent(self, method,  # pylint: disable=W0613
                                 modelID):
    """ Notification that new input was queued up for a particular model """
    runningModelInfo = self._runningModelsMap.get(modelID)
    if runningModelInfo is not None:
      # This model is already running
      runningModelInfo.updateTimestamp()

    elif modelID not in self._waitingModelsFIFO:
      # This model was not running and is not awaiting execution

      # TODO: for a large _waitingModelsFIFO, the membership check may be slow.
      #  Consider employing a map of all models of interest with current state
      #  (waiting/pending/running/idle) reflected in the items for O(1) lookups,
      #  but profile first to see if it's a problem!

      # NOTE: it's possible that the model has already processed all its input
      #  and we're handling this notification belatedly, and this may result in
      #  unnecessary start-up of its ModelRunner. We should generally be pretty
      #  well caught up with notifications, and this shouldn't be an issue.
      #  However, if necessary, we can mitigate this by checking the model's
      #  input queue *just before* starting the model.

      if self._freeSlots:
        # No models should be waiting if we have a free slot
        assert not self._waitingModelsFIFO, repr(self._waitingModelsFIFO)

        # Assign the model to a free slot
        self._assignModelToFreeSlot(modelID)

      else:
        # This model needs to wait until resources become available
        self._waitingModelsFIFO.append(modelID)

        if self._profiling:
          self._logger.info("{TAG:SWAP.SC.MODEL.WAIT} model=%s; "
                            "numWaitingModels=%s; numPendingPreemptSlots=%s",
                            modelID, len(self._waitingModelsFIFO),
                            len(self._pendingPreemptSlotsSet))

        self._requestPreemptionOfRunningSlotIfNeededAndPossible()


  def _handleModelDoneNotifyEvent(self, method,  # pylint: disable=W0613
                                  modelID, exitStatus, endTime):
    """ Notification that a particular model completed execution and the
    SlotAgent that ran it is now available for a new assignment.

    exitStatus: the exit status of the ModelRunner process (per os.WEXITSTATUS)
    """
    doneModelInfo = self._runningModelsMap.pop(modelID)


    if self._profiling:
      self._logger.info(
        "{TAG:SWAP.SC.MODEL.DONE} model=%s; slot=%d; exitStatus=%d; "
        "duration=%s; numRunningModels=%s; numWaitingModels=%s", modelID,
        doneModelInfo.slotIndex, exitStatus, endTime - doneModelInfo.startTime,
        len(self._runningModelsMap), len(self._waitingModelsFIFO))

    assert doneModelInfo.slotIndex not in self._freeSlots
    assert 0 <= doneModelInfo.slotIndex < len(self._slotAgents)
    assert len(self._freeSlots) < len(self._slotAgents)

    self._freeSlots.append(doneModelInfo.slotIndex)

    # Drop the slot from pending-preempt set in case it was scheduled for
    # preemption
    self._pendingPreemptSlotsSet.discard(doneModelInfo.slotIndex)

    # Ack SlotAgent to ready it for the next model
    self._slotAgents[doneModelInfo.slotIndex].releaseSlot()

    if self._mainSwapper.modelInputPending(modelID):
      # There is more unprocessed input data for the completed model,
      # so notify ourselves asynchronously to schedule this model
      self._newInputNotifyTS(modelID)

    if self._waitingModelsFIFO:
      # Start a waiting model, now that we know there is a free slot
      newModelID = self._waitingModelsFIFO.pop(0)
      self._assignModelToFreeSlot(newModelID)

      self._requestPreemptionOfRunningSlotIfNeededAndPossible()


  def _assignModelToFreeSlot(self, modelID):
    """ Assign the given model to a free slot """
    assert modelID not in self._runningModelsMap
    assert modelID not in self._waitingModelsFIFO

    freeSlotIndex = self._freeSlots.pop()

    self._slotAgents[freeSlotIndex].startModel(
      modelID=modelID,
      modelFinishedCallback=partial(self._modelDoneNotifyTS, modelID))

    self._runningModelsMap[modelID] = _RunningModelInfo(freeSlotIndex)

    assert ((len(self._runningModelsMap) + len(self._freeSlots)) ==
            len(self._slotAgents)), (
      len(self._runningModelsMap), len(self._freeSlots), len(self._slotAgents))

    self._logger.debug(
      "{TAG:SWAP.SC.MODEL.ASSIGN} model=%s; slot=%s; numRunningModels=%s; "
      "numFreeSlots=%s; numWaitingModels=%s; numPendingPreemptSlots=%s",
      modelID, freeSlotIndex, len(self._runningModelsMap), len(self._freeSlots),
      len(self._waitingModelsFIFO), len(self._pendingPreemptSlotsSet))


  def _requestPreemptionOfRunningSlotIfNeededAndPossible(self):
    """ Schedule a single slot for preemption if needed and possible """
    # There shouldn't be any free slots when we're asked to preempt
    assert not self._freeSlots, repr(self._freeSlots)

    if (len(self._waitingModelsFIFO) <= len(self._pendingPreemptSlotsSet) or
        len(self._pendingPreemptSlotsSet) >= len(self._slotAgents)):
      # Not needed or no preemptable slots
      return

    # Find an LRU non-pending-preempt busy slot agent, and request to
    # preempt it
    lru = sorted(
      ((i.slotIndex, i.timestamp)
        for i in self._runningModelsMap.itervalues()
        if i.slotIndex not in self._pendingPreemptSlotsSet),
      key=lambda element: element[1])

    slotIndex, timestamp = lru.pop(0)

    # Request preemption of the LRU slot
    self._slotAgents[slotIndex].stopModel()
    self._pendingPreemptSlotsSet.add(slotIndex)

    if self._profiling:
      self._logger.info(
        "{TAG:SWAP.SC.SLOT.PREEMPT.REQ} slot=%d with timestamp=%s; "
        "numWaitingModels=%s; numPendingPreemptSlots=%s",
        slotIndex, timestamp, len(self._waitingModelsFIFO),
        len(self._pendingPreemptSlotsSet))


  @abortProgramOnAnyException(
    _EXIT_CODE_ON_FAILURE_OF_NOTIFICATION_READER_THREAD,
    logger=_getLogger())
  @logEntryExit(_getLogger, logging.INFO)
  @logExceptions(_getLogger)
  def _runNotificationReaderThread(self):
    """ Read model data notifications and pass them to the event loop """
    self._logger.info("Notification Reader thread is running")

    # Let the main event loop know that this thread started successfully
    self._notificationReaderStartedEvent.set()


    with ModelSwapperInterface() as swapperAPI:
      # First, make sure our notification message queue exists, so we don't
      # miss any new notifications while we're checking for models with pending
      # input
      self._logger.info("SWAPPER_API: %r", swapperAPI)
      swapperAPI.initSchedulerNotification()

      # At start, notify main event loop of each model whose input is non-empty
      self._logger.info("Checking for models with pending input")

      i = 0
      for i, modelID in enumerate(swapperAPI.getModelsWithInputPending(), 1):
        self._logger.debug("Input pending for model=%s", modelID)
        self._newInputNotifyTS(modelID=modelID)

      self._logger.info("%s model(s) had pending input", i)

      # Service the SwapController's input queue util stop is requested
      with swapperAPI.consumeModelSchedulerNotifications() as consumer:
        numHandledNotifications = 0
        try:
          for notification in consumer:

            with self._notificationMutex:

              if self._stopNotificationReader:
                self._logger.info(
                  "Notification reader exiting due to stop request")
                break

              self._newInputNotifyTS(modelID=notification.value)

              notification.ack()

              numHandledNotifications += 1
          else:
            raise Exception("Unexpected termination of consumer loop in "
                            "Notification Reader")
        finally:
          self._logger.info(
            "Control is leaving notification reader loop after processing %s "
            "notifications", numHandledNotifications)



class _RunningModelInfo(object):
  """ Information about a running model """


  def __init__(self, slotIndex):
    self._slotIndex = slotIndex
    now = time.time()
    self._startTime = now
    self._activityTimestamp = now


  def updateTimestamp(self):
    """ Update input activity timestamp """
    self._activityTimestamp = time.time()


  @property
  def startTime(self):
    """ The time (time.time()) that this _RunningModelInfo instance was
    instantiated
    """
    return self._startTime


  @property
  def timestamp(self):
    """ Input activity timestamp """
    return self._activityTimestamp


  @property
  def slotIndex(self):
    return self._slotIndex
