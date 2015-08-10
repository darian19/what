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
A service that polls metric data from providers

TODO: Need unit test for metric error grace period logic (see
  collector_error handling logic here)
"""
from collections import defaultdict, OrderedDict
from datetime import datetime
import logging
import multiprocessing
import sys
import threading
import time

from nupic.support.decorators import logExceptions

from YOMP import YOMP_logging, logging_support
import YOMP.app
import YOMP.app.exceptions as app_exceptions
from htmengine import utils

# import from YOMP or else datasource adapters won't register properly...
from YOMP.app.adapters.datasource import createDatasourceAdapter

from htmengine.runtime.metric_streamer_util import MetricStreamer
from YOMP.YOMP_logging import getStandardLogPrefix
from htmengine.model_swapper.model_swapper_interface import (
  ModelSwapperInterface
)

from YOMP.app import repository
from YOMP.app.repository.queries import MetricStatus

from nta.utils.error_handling import abortProgramOnAnyException



_MODULE_NAME = "YOMP.metric_collector"

_EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD = 1


def _getLogger():
  return YOMP_logging.getExtendedLogger(_MODULE_NAME)



class _DataCollectionTask(object):
  """ Data collection task parameters for data collection worker process
  """
  __slots__ = ("metricID", "datasource", "metricSpec", "rangeStart",
               "metricPeriod", "updateResourceStatus", "resultsQueue")

  def __init__(self, metricID, datasource, metricSpec, rangeStart, metricPeriod,
               updateResourceStatus, resultsQueue):
    """
    :param metricID: unique id of the metric associated with the task (presently
      only for diagnostics)
    :param datasource: datasource string (e.g., "cloudwatch")
    :param metricSpec: metricSpec dict for new datasource adapter
    :param rangeStart: start of data query range: datetime or None
    :param metricPeriod: metric data period in seconds
    :param updateResourceStatus: True to query the resource's status.
    :param resultsQueue: Results Queue
    """
    # TODO: unit-test

    self.metricID = metricID
    self.datasource = datasource
    self.metricSpec = metricSpec
    self.rangeStart = rangeStart
    self.metricPeriod = metricPeriod
    self.updateResourceStatus = updateResourceStatus
    self.resultsQueue = resultsQueue


  def __repr__(self):
    # TODO: unit-test
    return "%s<metric=%s, source=%s, start=%s, period=%s, updateStatus=%s>" % (
      self.__class__.__name__, self.metricID, self.datasource,
      (self.rangeStart.isoformat() + "Z"
       if self.rangeStart is not None else None),
      self.metricPeriod, self.updateResourceStatus)



class _DataCollectionResult(object):
  """ Metric data collection result as returned by process pool worker
  """
  __slots__ = ("metricID", "creationTime", "exception", "resourceStatus",
               "data", "nextCallStart", "duration",)


  def __init__(self, metricID):
    """
    param metricID: unique id of the metric associated with the result (
      presently only for diagnostics)
    """
    # TODO: unit-test

    # Time when work started on this task in seconds since unix epoch
    self.creationTime = time.time()

    # Unique ID of the metric associated with the result
    self.metricID = metricID

    # Status of resource as reported by the data adapter's getInstanceStatus
    # method; Exception-based object on error; None if not collected
    self.resourceStatus = None

    # A (possibly empty) sequence of collected data samples; Exception-based
    # object on error
    self.data = ()

    # datetime.datetime object indicating the UTC start time to use in next call
    # to this method, which may be None
    self.nextCallStart = None

    # The amount of time in seconds consumed by collection
    self.duration = 0


  def __repr__(self):
    # TODO: unit-test
    return (
      "%s<metric=%s, status=%r, numRows=%d, getDataError=%r, started=%sZ, "
      "duration=%.4fs>" %
      (self.__class__.__name__, self.metricID, self.resourceStatus,
       len(self.data) if not isinstance(self.data, Exception) else 0,
       self.data if isinstance(self.data, Exception) else None,
       datetime.utcfromtimestamp(self.creationTime).isoformat(),
       self.duration))



class _MetricInfoCacheItem(object):
  """ Information for optimizing metric's data polling. One of these is cached
  in memory for each metric whose data we attempted to collect. Each item
  maintains last access time to facilitate garbage-collection of obsolete items.

  # TODO: unit-test
  """
  __slots__ = ("_quarantineEndTime", "lastAccessTime",)


  def __init__(self):
    # Expiration time of the metric's quarantine in seconds since unix epoch;
    # collector will not attempt to poll this metric until this time is reached.
    # This is set to a time in the future after empty data or error is
    # encountered in the metric.
    self._quarantineEndTime = 0

    # Last time that a member (except this one) was accessed in seconds
    # since unix epoch; facilitates garbage-collection
    self.lastAccessTime = None
    self._touch()


  def _touch(self):
    self.lastAccessTime = time.time()


  @property
  def quarantineEndTime(self):
    self._touch()
    return self._quarantineEndTime


  @quarantineEndTime.setter
  def quarantineEndTime(self, value):
    self._quarantineEndTime = value
    self._touch()



class _ResourceInfoCacheItem(object):
  """ Information for optimizing resource status polling. One of these is cached
  in memory for each resource referenced by metrics whose data we attempted to
  collect.

  # TODO: unit-test
  """
  __slots__ = ("nextResourceStatusUpdateTime", "error")


  def __init__(self):
    # Unix epoch timestamp for next resource status update
    self.nextResourceStatusUpdateTime = 0

    # Exception-based object if last attempt to get resource status resulted in
    # error; None otherwise
    self.error = None



class MetricCollector(object):
  """
  This process is responsible for collecting data from all the metrics at
  a specified time interval
  """

  # Number of concurrent worker processes used for querying metrics
  _WORKER_PROCESS_POOL_SIZE = 10

  # Amount of time to sleep when there are no metrics pending data collection
  _NO_PENDING_METRICS_SLEEP_SEC = 10

  # Metric's period times this number is the duration of the metric's quarantine
  # time after a mettic errors out or returns empty data
  _METRIC_QUARANTINE_DURATION_RATIO = 0.5

  # The approximate time between status queries of a metric's resource to
  # avoid too many of the costly calls (e.g., Cloudwatch), especially during a
  # metric's catch-up phase
  _RESOURCE_STATUS_UPDATE_INTERVAL_SEC = 2.5 * 60

  # An self._metricInfoCache item may be garbage-collected when this much time
  # passes since last access to the item
  _METRIC_INFO_CACHE_ITEM_EXPIRATION_SEC = (60 * 60)

  _SENTINEL = None

  def __init__(self):
    self._log = YOMP_logging.getExtendedLogger(self.__class__.__name__)

    self._profiling = (
      YOMP.app.config.getboolean("debugging", "profiling") or
      self._log.isEnabledFor(logging.DEBUG))

    self._pollInterval = YOMP.app.config.getfloat(
      "metric_collector", "poll_interval")

    self._metricErrorGracePeriod = YOMP.app.config.getfloat(
      "metric_collector", "metric_error_grace_period")

    # Interval for periodic garbage collection of our caches (e.g.,
    # self._metricInfoCache and self._resourceInfoCache)
    self._cacheGarbageCollectionIntervalSec = self._metricErrorGracePeriod * 2

    # Time (unix epoch) when to run the next garbage collection of
    # self._metricInfoCache and self._resourceInfoCache; 0 triggers it ASAP as a
    # quick test of the logic. See self._cacheGarbageCollectionIntervalSec.
    self._nextCacheGarbageCollectionTime = 0

    # We use this to cache info about metrics that helps us avoid unnecessary
    # queries to the datasource. The keys are metric uid's and corresponding
    # values are _MetricInfoCacheItem objects.
    self._metricInfoCache = defaultdict(_MetricInfoCacheItem)

    # We use this to cache info about resources referenced by metrics to help
    # us avoid unnecessary resource-status queries to the datasource. The keys
    # are resource cananonical identifiers (from Metric.server) and
    # corresponding values are _ResourceInfoCacheItem objects.
    self._resourceInfoCache = defaultdict(_ResourceInfoCacheItem)

    self.metricStreamer = MetricStreamer()



  def _collectDataForMetrics(self, metricsToUpdate, processPool, resultsQueue):
    """ Collect data for the given metrics

    :param metricsToUpdate: a dict of Metric instances which are due for
      an update

    :param processPool: Process poll in which collection tasks are mapped.
    :type processPool: multiprocessing.Pool

    :param resultsQueue: Results Queue onto which collection results are
      published
    :type resultsQueue: multiprocessing.JoinableQueue

    :returns: Result of calling `processPool.map_async()`.  Call .wait() on the
      return value to block until all map tasks have been completed.
      Meanwhile, you may consume resultsQueue for the results as they become
      available.
    :rtype: multiprocessing.pool.AsyncResult
    """
    # Create task parameters for concurrent processing
    now = time.time()
    tasks = []
    for metricObj in metricsToUpdate.values():
      metricSpec = utils.jsonDecode(metricObj.parameters)["metricSpec"]

      resourceCacheItem = self._resourceInfoCache[metricObj.server]
      if now >= resourceCacheItem.nextResourceStatusUpdateTime:
        updateResourceStatus = True
        resourceCacheItem.nextResourceStatusUpdateTime = (
          now + self._RESOURCE_STATUS_UPDATE_INTERVAL_SEC)
      else:
        updateResourceStatus = False

      task = _DataCollectionTask(
        metricID=metricObj.uid,
        datasource=metricObj.datasource,
        metricSpec=metricSpec,
        rangeStart=metricObj.last_timestamp,
        metricPeriod=metricObj.poll_interval,
        updateResourceStatus=updateResourceStatus,
        resultsQueue=resultsQueue)

      tasks.append(task)

    # Process the tasks concurrently, return immediately
    return processPool.map_async(_collect, tasks)


  def _garbageCollectInfoCache(self):
    """ Remove stale items from self._metricInfoCache and clear
    self._resourceInfoCache

    TODO: unit-test
    """
    now = time.time()
    self._nextCacheGarbageCollectionTime = (
      now + self._cacheGarbageCollectionIntervalSec)

    # Clear resource info cache
    self._resourceInfoCache.clear()
    self._log.info("Garbage-collected resource info cache")

    # Gargabe-collect stale metric info cache items
    staleProperties = tuple(
      k for k, v in self._metricInfoCache.iteritems()
      if now > (v.lastAccessTime + self._METRIC_INFO_CACHE_ITEM_EXPIRATION_SEC))

    for k in staleProperties:
      self._metricInfoCache.pop(k)

    self._log.info("Garbage-collected stale=%d metric cache info items",
                   len(staleProperties))


  def _getCandidateMetrics(self, engine):
    """ Return the metrics that are due for an update

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :returns: a (possibly empty) sequence of Metric instances that are due for
      an update (after removing quarantined indexes)

    TODO: unit-test
    """
    with engine.connect() as conn:
      metricsToUpdate = repository.retryOnTransientErrors(
        repository.getCloudwatchMetricsPendingDataCollection)(conn)

    # Remove quarantined metrics
    quarantinedIndexes = None
    if metricsToUpdate:
      now = time.time()
      quarantinedIndexes = set(
        i for i, m in enumerate(metricsToUpdate)
        if now < self._metricInfoCache[m.uid].quarantineEndTime)

      metricsToUpdate = OrderedDict((m.uid, m)
                                    for i, m in enumerate(metricsToUpdate)
                                    if i not in quarantinedIndexes)

      if not metricsToUpdate:
        # TODO: unit-test
        self._log.debug("All candidate numMetrics=%d are quarantined",
                        len(quarantinedIndexes))

    return metricsToUpdate


  def _handleMetricCollectionError(self, engine, metricObj, startTime, error):
    """ Update the metric's collector_error member and promote the metric
    to ERROR state if needed

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param metricObj: Metric instance

    :param startTime: metric collection start time; unix epoch timestamp

    :param error: exception object that is the result of metric data collection
      or (possibly pending) resource status check
    """
    # Quarantine the metric temporarily
    self._metricInfoCache[metricObj.uid].quarantineEndTime = (
      startTime +
      metricObj.poll_interval * self._METRIC_QUARANTINE_DURATION_RATIO)

    try:
      if metricObj.collector_error is None:
        # TODO: unit-test
        # Begin error grace period for this metric
        deadline = time.time() + self._metricErrorGracePeriod
        with engine.connect() as conn:
          repository.retryOnTransientErrors(repository.setMetricCollectorError)(
            conn,
            metricObj.uid,
            utils.jsonEncode(dict(deadline=deadline,
                                  message=repr(error))))
        self._log.error(
          "Started error grace period on metric=<%r> through %sZ due to "
          "error=%r",
          metricObj, datetime.utcfromtimestamp(deadline).isoformat(), error)
      elif (time.time() >
            utils.jsonDecode(metricObj.collector_error)["deadline"]):
        # TODO: unit-test
        # Error grace period expired: promote the metric to ERROR state
        with engine.connect() as conn:
          repository.retryOnTransientErrors(repository.setMetricStatus)(
            conn, metricObj.uid, MetricStatus.ERROR, repr(error))
        self._log.error(
          "Metric Collector: grace period expired; placed metric=<%r> in "
          "ERROR state due to error=%r", metricObj, error)
    except app_exceptions.ObjectNotFoundError:
      # TODO: unit-test
      self._log.warning("Metric deleted? metric=%r", metricObj, exc_info=True)


  def _processCollectedData(self, engine, metricsToUpdate, modelSwapper,
                            collectResult):
    """ Process collected metrics data; publish it on the destination
    message queue, and update metric instance status and metric collection
    state.

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param metricsToUpdate: a sequence of Metric instances which were due for
      an update
    :type metricsToUpdate: collections.OrderedDict

    :param modelSwapper: ModelSwapperInterface object for running models

    :param collectResult: _DataCollectionResult object

    :returns: 2-tuple (numEmpty, numErrors), where numEmpty is the count of
      metrics with empty data (not ready or data gap) numErrors is the count
      of metrics with errors
    """

    numEmpty = numErrors = 0

    metricObj = metricsToUpdate[collectResult.metricID]
    # Update cached resource status
    resourceInfoCacheItem = self._resourceInfoCache[metricObj.server]
    newResourceStatus = None
    if collectResult.resourceStatus is not None:
      if isinstance(collectResult.resourceStatus, Exception):
        resourceInfoCacheItem.error = collectResult.resourceStatus
      else:
        newResourceStatus = collectResult.resourceStatus
        resourceInfoCacheItem.error = None

    if isinstance(collectResult.data, Exception):
      dataError = collectResult.data
      newData = None
      nextStartTime = None
    else:
      dataError = None
      newData = collectResult.data
      nextStartTime = collectResult.nextCallStart

    if newData is not None or newResourceStatus is not None:
      rangeStart = metricObj.last_timestamp

      if not newData:
        # Data is not ready yet or data gap
        numEmpty += 1
        self._metricInfoCache[metricObj.uid].quarantineEndTime = (
          collectResult.creationTime +
          metricObj.poll_interval * self._METRIC_QUARANTINE_DURATION_RATIO)
      else:
        headTS = newData[0][0]
        tailTS = newData[-1][0]

      startTime = time.time()

      # Update resource status and next metric start time
      @repository.retryOnTransientErrors
      def runSQL(engine):
        with engine.begin() as conn:
          try:
            # Save resource status
            if newResourceStatus is not None:
              repository.saveMetricInstanceStatus(conn,
                                                  metricObj.server,
                                                  newResourceStatus)

            # Save starting time for the next data query in metric row
            if nextStartTime is not None:
              repository.setMetricLastTimestamp(conn,
                                                metricObj.uid,
                                                nextStartTime)
          except app_exceptions.ObjectNotFoundError:
            self._log.warning("Metric deleted?", exc_info=True)

      if newResourceStatus is not None or nextStartTime is not None:
        runSQL(engine)

      if newData:
        # This is done outside the cursor context to minimize lock duration.
        #
        # NOTE: It is still possible for duplicate data to be sent to the
        # exchange so the recipient will need to de-dupe it. It is also
        # possible for the metric to be updated in the database but data not
        # sent to the exchange.
        try:
          self.metricStreamer.streamMetricData(newData,
                                               metricID=metricObj.uid,
                                               modelSwapper=modelSwapper)
        except ValueError:
          self._log.exception("Failed to stream metric data %r" % newData)
        except app_exceptions.ObjectNotFoundError:
          # We expect that the model exists but in the odd case that it has
          # already been deleted we don't want to crash the process.
          self._log.info("Metric not found when adding data.")

        if self._profiling:
          self._log.info(
            "{TAG:APP.MC.DATA.TO_STRM.DONE} numItems=%d for metric=%r; "
            "rangeStart=%s; ts=[%s]; duration=%.4fs; ",
            len(newData), metricObj,
            rangeStart.isoformat() + "Z" if rangeStart is not None else None,
            (("%sZ..%sZ" % (headTS.isoformat(), tailTS.isoformat()))
              if len(newData) > 1 else (headTS.isoformat() + "Z")),
            time.time() - startTime + collectResult.duration)
      else:
        if self._log.isEnabledFor(logging.DEBUG):
          self._log.debug(
            "{TAG:APP.MC.DATA.NONE} No data for metric=%r; rangeStart=%s; "
            "duration=%.4fs", metricObj,
            rangeStart.isoformat() + "Z" if rangeStart is not None else None,
            time.time() - startTime + collectResult.duration)

    # Take care of errors
    error = dataError or resourceInfoCacheItem.error
    if error is not None:
      # Metric data or resource status collection error
      numErrors += 1
      # Update metric error grace period and quarantine info
      self._handleMetricCollectionError(engine,
                                        metricObj,
                                        startTime=collectResult.creationTime,
                                        error=error)
    else:
      if metricObj.collector_error is not None:
        oldErrorInfo = metricObj.collector_error

        # There was pending collector error before, but no error this time, so
        # clear metric's collector_error
        try:
          with engine.connect() as conn:
            repository.retryOnTransientErrors(
              repository.setMetricCollectorError)(conn, metricObj.uid, None)
        except app_exceptions.ObjectNotFoundError:
          self._log.warning("Metric deleted?", exc_info=True)

        self._log.info("metric=<%r> exited error grace state %s",
                       metricObj, oldErrorInfo)

    return (numEmpty, numErrors)


  @abortProgramOnAnyException(
    _EXIT_CODE_ON_UNHANDLED_EXCEPTION_IN_THREAD,
    logger=_getLogger())
  @logExceptions(_getLogger)
  def _processAndDispatchThreadTarget(self, engine, metricsToUpdate,
                                      resultsQueue, modelSwapper, statsPipe):
    """ Process collected metrics data; publish it on the destination
    message queue, and update metric instance status and metric collection
    state.

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param metricsToUpdate: a sequence of Metric instances which were due for
      an update
    :type metricsToUpdate: collections.OrderedDict

    :param resultsQueue: Queue from which a sequence of _DataCollectionResult
      instances are processed
    :type resultsQueue: multiprocessing.JoinableQueue

    :param modelSwapper: ModelSwapperInterface object for running models

    :param statsPipe: Pipe in which the final statistics are conveyed in the
      form of a 2-tuple (numEmpty, numErrors), where numEmpty is the count of
      metrics with empty data (not ready or data gap) numErrors is the count
      of metrics with errors
    :type statsPipe: multiprocessing.Pipe (non-duplex)

    :returns: None
    """
    numEmpty = numErrors = 0

    while True:
      try:
        collectResult = resultsQueue.get(True)

        if collectResult is self._SENTINEL:
          # There are no more results to process
          break

        stats = self._processCollectedData(engine,
                                           metricsToUpdate,
                                           modelSwapper,
                                           collectResult)
        numEmpty += stats[0]
        numErrors += stats[1]

      finally:
        resultsQueue.task_done()

    statsPipe.send((numEmpty, numErrors))



  def run(self):
    """ Collect metric data and status for active metrics
    """
    # NOTE: the process pool must be created BEFORE this main (parent) process
    # creates any global or class-level shared resources (e.g., boto
    # connection) that would have undersirable consequences when
    # replicated into and used by forked child processes (e.g., the same MySQL
    # connection socket file descriptor used by multiple processes). And we
    # can't take advantage of the process Pool's maxtasksperchild feature
    # either (for the same reason)
    self._log.info("Starting YOMP Metric Collector")
    resultsQueue = multiprocessing.Manager().JoinableQueue()

    recvPipe, sendPipe = multiprocessing.Pipe(False)

    processPool = multiprocessing.Pool(
      processes=self._WORKER_PROCESS_POOL_SIZE,
      maxtasksperchild=None)

    try:
      with ModelSwapperInterface() as modelSwapper:
        engine = repository.engineFactory()
        while True:
          startTime = time.time()

          if startTime > self._nextCacheGarbageCollectionTime:
            # TODO: unit-test
            self._garbageCollectInfoCache()

          # Determine which metrics are due for an update
          metricsToUpdate = self._getCandidateMetrics(engine)

          filterDuration = time.time() - startTime

          if not metricsToUpdate:
            time.sleep(self._NO_PENDING_METRICS_SLEEP_SEC)
            continue

          # Collect metric data
          collectionStartTime = time.time()

          poolResults = self._collectDataForMetrics(metricsToUpdate,
                                                    processPool,
                                                    resultsQueue)

          # Process/dispatch results in parallel in another thread as results
          # become available in resultsQueue
          dispatchThread = (
            threading.Thread(target=self._processAndDispatchThreadTarget,
                             args=(engine,
                                   metricsToUpdate,
                                   resultsQueue,
                                   modelSwapper,
                                   sendPipe)))
          dispatchStartTime = time.time()
          dispatchThread.start()

          # Syncronize with processPool
          poolResults.wait() # Wait for collection tasks to complete

          metricPollDuration = time.time() - collectionStartTime

          resultsQueue.join() # Block until all tasks completed...

          # Syncronize with dispatchThread
          resultsQueue.put(self._SENTINEL) # Signal to dispatchThread that
                                           # there are no more results to
                                           # process.
          resultsQueue.join()
          numEmpty, numErrors = recvPipe.recv() # Get dispatchThread stats

          dispatchDuration = time.time() - dispatchStartTime

          self._log.info(
            "Processed numMetrics=%d; numEmpty=%d; numErrors=%d; "
            "duration=%.4fs (filter=%.4fs; query=%.4fs; dispatch=%.4fs)",
            len(metricsToUpdate), numEmpty, numErrors,
            time.time() - startTime, filterDuration,
            metricPollDuration, dispatchDuration)
    finally:
      self._log.info("Exiting Metric Collector run-loop")
      processPool.terminate()
      processPool.join()



def _collect(task):
  """ Executed via multiprocessing Pool: Collect metric data and corresponding
  resource status.

  :param task: a _DataCollectionTask instance
  """
  log = YOMP_logging.getExtendedLogger(MetricCollector.__name__)

  startTime = time.time()

  result = _DataCollectionResult(metricID=task.metricID)

  dsAdapter = None

  try:
    dsAdapter = createDatasourceAdapter(task.datasource)
    result.data, result.nextCallStart = dsAdapter.getMetricData(
      metricSpec=task.metricSpec,
      start=task.rangeStart,
      end=None)
  except Exception as e: # pylint: disable=W0703
    log.exception("getMetricData failed in task=%s", task)
    result.data = e

  try:
    if task.updateResourceStatus:
      result.resourceStatus = dsAdapter.getMetricResourceStatus(
        metricSpec=task.metricSpec)
  except Exception as e: # pylint: disable=W0703
    log.exception("getMetricResourceStatus failed in task=%s", task)
    result.resourceStatus = e

  result.duration = time.time() - startTime

  task.resultsQueue.put(result)

  return True



if __name__ == "__main__":
  logging_support.LoggingSupport.initService()

  logger = _getLogger()
  logger.setLogPrefix('<%s, SERVICE=METRIC> ' % getStandardLogPrefix())

  try:
    logger.info("{TAG:METRIC.START} argv=%r", sys.argv)
    MetricCollector().run()
  except KeyboardInterrupt as e:
    # We're being stopped by supervisord or <CTL-C>
    logger.info("Terminated via %r", e)
  except:
    logger.exception("{TAG:METRIC.STOP.ABORT}")
    raise

  logger.info("{TAG:METRIC.STOP.OK}")
