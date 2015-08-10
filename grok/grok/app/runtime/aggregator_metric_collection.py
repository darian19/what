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
Aggregator service's metric-collection utilitities.

NOTE: The first phase supports only AWS/EC2 Instances.
"""

from collections import defaultdict, namedtuple
import copy
from datetime import datetime, timedelta
import itertools
import math
import multiprocessing
import time

from boto.ec2 import cloudwatch
from boto.exception import BotoServerError

from nupic.support.decorators import logExceptions

from YOMP import logging_support
from YOMP.YOMP_logging import (getExtendedLogger,
                               getMetricLogPrefix,
                               getAutostackLogPrefix)

from YOMP.app.adapters.datasource.autostack.autostack_metric_adapter import (
  AutostackMetricAdapterBase)
from YOMP.app.aws import cloudwatch_utils
import YOMP.app.exceptions as app_exceptions
from YOMP.app.runtime.aggregator_instances import getAutostackInstances
from YOMP.app.runtime.aggregator_utils import getAWSCredentials, TimeRange



_MODULE_NAME = "YOMP.aggregator_metric_collection"



def _getLogger():
  return getExtendedLogger(_MODULE_NAME)



def _getCollectWorkerLogger():
  return getExtendedLogger(_MODULE_NAME + ".COLLECTOR")



def _getInstanceWorkerLogger():
  return getExtendedLogger(_MODULE_NAME + ".INSTANCE")



# refID: a reference ID value to be returned in the corresponding
#   MetricCollection object. The refID value in each AutostackMetricRequest
#   object must be unique within each sequence of AutostackMetricRequest objects
#   submitted to EC2InstanceMetricGetter.collectMetricData(). a refID must also
#   be hashable. E.g., the index of the AutostackMetricRequest object within the
#   submitted sequence of requests can be used as a refID.
# autostack: Autostack instance
# metric: aggregate Metric instance
AutostackMetricRequest = namedtuple("AutostackMetricRequest",
                                    "refID autostack metric")


# timestamp: datetime.datetime instance; UTC
# value: floating point number of a single statistic was requested; or a dict
#   of statistic-name/value properties if multiple statistics were requested
MetricRecord = namedtuple("MetricRecord", "timestamp value")


# Metric data or metric statistics collected from a specific AWS/EC2 Instance
# instanceID: instance id of the EC2 instance (string)
# records: a (possibly-empty) sequence of MetricRecord objects sorted by
#     timestamp in ascending order
InstanceMetricData = namedtuple("InstanceMetricData", "instanceID records")


# Metric data collection result for a given AutostackMetricRequest object
# refID: user reference identifier provided by user in the corresponding
#   AutostackMetricRequest object.
# slices: a (possibly empty) unordered sequence of InstanceMetricData objects.
#         Across slices, corresponding metric records have the same timestamp.
#         An empty sequence may result from no instances matching filter.
#         E.g.,
#           [
#             InstanceMetricData(instanceID3, (i3.r1, i3.r2, i3.r3,))
#             InstanceMetricData(instanceID2, (i2.r2,))
#             InstanceMetricData(instanceID1, ())
#             InstanceMetricData(instanceID4, (i4.r3, i4.r5, i4.r8,))
#           ]
#
#           In the above example: i3.r2 and i2.r2 have the same Timestamp, as do
#                                 i3.r3 and i4.r3
# timeRange: aggregator_utils.TimeRange object indicating UTC time range for the
#            metric data query
# nextMetricTime: datetime.datetime UTC start time of the next metric
#                 collection
MetricCollection = namedtuple("MetricCollection",
                              "refID slices timeRange nextMetricTime")


# Used my metric collection iterator to collect incoming slices for a given
#     MetricCollection
# expectedNumSlices: The number of metric data "slices" expected in this
#     collection. The iterator will yield the MetricCollection object once
#     the expected number of slices are collected
# collection: A MetricCollection object that will be yielded once all the
#     expected metric data slices are collected by the worker pool.
_MetricCollectionAccumulator = namedtuple(  # pylint: disable=C0103
  "_MetricCollectionAccumulator",
  "expectedNumSlices collection")


class _MetricCollectionTask(object):
  """ Metric collection task parameters for metric collection worker process.

  NOTE: Used for both metric data and metric statistics (e.g., min/max)
  collection.
  """
  __slots__ = ("refID", "metricID", "region", "instanceID", "metricName",
               "stats", "unit", "period", "timeRange",)

  def __init__(self, refID, metricID, region, instanceID, metricName, stats,
               unit, period, timeRange):
    """
    :param refID: reference value returned in result and used by caller to
                associate the result with the user's request
    :param metricID: unique id of the metric associated with the task (for
                     diagnostics)
    :param region: name of EC2 region (e.g., "us-west-2")
    :param instanceID: EC2 identifier of the Instance (e.g., "i-07419a30")
    :param metricName: Name of AWS CloudWatch metric (e.g., "CPUUtilization")
    :param stats: Specifies which statistic(s) to return; either a single
                  CloudWatch statistics identifier or a sequence of them (e.g.,
                  "Average")
    :param unit: CloudWatch metric data unit (e.g., "Percent")
    :param period: metric data period in seconds (multiple of 60)
    :param timeRange: aggregator_utils.TimeRange object indicating UTC time
                      range for the query
    """
    # TODO: unit-test
    self.refID = refID
    self.metricID = metricID
    self.region = region
    self.instanceID = instanceID
    self.metricName = metricName
    self.stats = stats
    self.unit = unit
    self.period = period
    self.timeRange = timeRange


  def __repr__(self):
    # TODO: unit-test
    return ("%s<ref=%s, metric=%s, region=%s, instance=%s, metric=%s, stats=%s "
            "unit=%s, period=%ss, range=%s>") % (
      self.__class__.__name__, self.refID, self.metricID, self.region,
      self.instanceID, self.metricName, self.stats, self.unit, self.period,
      self.timeRange)



class _MetricCollectionTaskResult(object):
  """ Metric data/statistics collection task result as returned by process pool
  worker

  attributes:

  creationTime: Time when work started on this task in seconds since unix epoch;
      for diagnostics

  duration: The amount of time, in seconds, consumed by collection;
      for diagnostics)

  refID: reference value passed by caller via task and returned in result that
      is used by caller to associate the result with the user's request

  metricID: unique id of the metric associated with the result; for diagnostics

  instanceID: EC2 Instance ID; string

  exception: If there was an error, will be set to the exception instance, and
      the `data` member should be treated as undefined; None on success

  data: A sequence of data MetricRecord objects that were collected, ordered by
      timestamp in ascending order; empty sequence if no metric data was
      available in the requested time range. Undefined if `exception` is not
      None.
  """
  __slots__ = ("creationTime", "duration", "refID", "metricID", "instanceID",
               "exception", "data",)


  def __init__(self, refID, metricID, instanceID):
    """
    :param refID: reference value passed by caller via task and returned in
        result that is used by caller to associate the result with the user's
        request
    :param metricID: unique id of the metric associated with the result (for
        diagnostics)
    :param instanceID: EC2 Instance ID
    """
    # TODO: unit-test

    self.creationTime = time.time()

    self.duration = 0

    self.refID = refID

    self.metricID = metricID

    self.instanceID = instanceID

    self.exception = None

    self.data = None


  def __repr__(self):
    # TODO: unit-test
    return (
      "%s<ref=%s, metric=%s, instance=%s, ex=%r, numRows=%d, started=%sZ, "
      "duration=%ss>" %
      (self.__class__.__name__, self.refID, self.metricID, self.instanceID,
       self.exception, len(self.data) if self.data else 0,
       datetime.utcfromtimestamp(self.creationTime).isoformat(),
       self.duration))



class _InstanceCacheValue(object):
  __slots__ = ("region", "filters", "instances", "lastUseTimestamp")

  def __init__(self, region, filters, instances):
    """ A value in cache of instances

    :param region: EC2 region of the Autostack
    :type region: string

    :param filters: One or more filters. Each filter consists of an instance tag
        name and one or more values for that tag; the instances matched by a
        single filter are the union of instances that have that tag with any of
        the specified values. When multiple filters are used, they match
        instances that match all the filters (intersection).

    :type filters: a dict; the each key is an Instance tag name and the
        corresponding value is a sequence of one or more tag values.

    :param instances: a possibly-empty sequence of
                      aggregator_instances.InstanceInfo objects
    """
    self.region = region

    if not isinstance(filters, dict):
      raise TypeError("filters arg is not a dict: %r" % (type(filters),))
    self.filters = copy.deepcopy(filters)

    # a possibly-empty sequence of aggregator_instances.InstanceInfo objects
    self.instances = instances[:]

    self.lastUseTimestamp = None
    self.use()


  def use(self):
    """ Update last-use timestamp """
    self.lastUseTimestamp = time.time()



class _MetricCollectionIterator(object):
  """ EC2InstanceMetricGetter.collectMetricData returns an instance of this
  class to be iterated for the resulting MetricCollection objects.

  # TODO: unit-test
  """

  def __init__(self, taskResultsIter, collectionAccumulatorMap, numTasks, log):
    """
    :param taskResultsIter: iterator that yields _MetricCollectionTaskResult
        objects for a given sequence of AutostackMetricRequest objects.
    :param collectionAccumulatorMap: a dict of the expected
        refID-to-_MetricCollectionAccumulator mappings. The refID values are the
        ones provided by user in the corresponding AutostackMetricRequest
        objects.
    :param numTasks: The number of metric-collection tasks submitted
    :param log: python logger instance
    """
    now = time.time()
    self._creationTime = now

    # Last time control returned to consumer
    self._lastConsumerTime = now

    # Time during consumption that the iterator was idle (amount of time between
    # iteration calls)
    self._consumerOverheadSec = 0

    self._taskResultsIter = taskResultsIter
    self._accumulatorMap = collectionAccumulatorMap
    self._numTasks = numTasks
    self._log = log

    self._done = False

    self._numFailedTasks = 0
    self._numTaskResults = 0

    self._numCollections = len(collectionAccumulatorMap)


  def __iter__(self):
    return self


  def next(self):
    """ Waits for completion of the next metric collection group and returns it
    :returns: the next completed MetricCollection object, if collection is
        ongoing, otherwise raises StopIteration if the collection has
        completed.
    """
    self._consumerOverheadSec += time.time() - self._lastConsumerTime

    try:
      for taskResult in self._taskResultsIter:
        self._numTaskResults += 1

        if taskResult.exception is not None:
          self._numFailedTasks += 1

        accumulator = self._accumulatorMap[taskResult.refID]
        collection = accumulator.collection
        assert len(collection.slices) < accumulator.expectedNumSlices, (
          accumulator)

        if taskResult.exception is None:
          collection.slices.append(
            InstanceMetricData(instanceID=taskResult.instanceID,
                               records=taskResult.data))
        else:
          self._log.error("Metric collection task failed: result=%r",
                          taskResult)
          collection.slices.append(
            InstanceMetricData(instanceID=taskResult.instanceID,
                               records=()))

        if len(collection.slices) == accumulator.expectedNumSlices:
          self._accumulatorMap.pop(taskResult.refID)
          return collection

      # No more task results
      assert self._numTaskResults == self._numTasks, (self._numTaskResults,
                                                      self._numTasks)

      # Dole out metric collections that didn't match any instances
      try:
        _refID, accumulator = self._accumulatorMap.popitem()
      except KeyError:
        # No more metric collections to dole out
        if not self._done:
          self._done = True
          self._log.info(
            "Completed iteration of metric data collections: "
            "numCollections=%d; numTasks=%d; numFailedTasks=%s; "
            "duration=%ss; consumerOverhead=%ss",
            self._numCollections, self._numTasks, self._numFailedTasks,
            time.time() - self._creationTime, self._consumerOverheadSec)
        raise StopIteration
      else:
        # Dole out an instance-less metric collection
        assert accumulator.expectedNumSlices == 0, accumulator
        assert len(accumulator.collection.slices) == 0, accumulator

        return accumulator.collection
    finally:
      self._lastConsumerTime = time.time()



@logExceptions(_getInstanceWorkerLogger)
def _matchAutostackInstances(task):
  """ Executed via multiprocessing Pool: Retrieve instances matching an
  autostack

  :param task: Descriptions of Autostack
  :type task: A three-tuple: (autostackID, region, filters,). See
      aggregator_instances.getAutostackInstances for description of `filters`

  :returns: a sequence of zero or more aggregator_instances.InstanceInfo objects
      matching the given task
  """
  log = _getInstanceWorkerLogger()

  log.debug("_matchAutostackInstances: task=%r", task)

  autostackID, region, filters = task

  matchStartTime = time.time()

  instances = getAutostackInstances(regionName=region, filters=filters)

  log.info("Retrieved Autostack instances: autostack=%s; region=%s; "
           "filters=%s; numInstances=%d; duration=%ss",
           autostackID, region, filters, len(instances),
           time.time() - matchStartTime)

  return instances



@logExceptions(_getCollectWorkerLogger)
def _collectMetrics(task):
  """ Executed via multiprocessing Pool: Collect metric data

  :param task: a _MetricCollectionTask object

  :returns: a _MetricCollectionTaskResult object
  """
  log = getExtendedLogger(_MODULE_NAME + ".COLLECTOR")

  taskResult = _MetricCollectionTaskResult(
    refID=task.refID,
    metricID=task.metricID,
    instanceID=task.instanceID)
  try:
    if task.metricName == "InstanceCount":
      timestamp = datetime.utcnow().replace(second=0, microsecond=0)
      taskResult.data = (MetricRecord(timestamp=timestamp,
                                      value=1.0),)
    else:
      backoffSec = 0.75
      backoffGrowthFactor = 1.5
      maxBackoffSec = 5
      rawdata = None
      while rawdata is None:
        try:
          cw = cloudwatch.connect_to_region(region_name=task.region,
                                            **getAWSCredentials())

          rawdata = cw.get_metric_statistics(
            period=task.period,
            start_time=task.timeRange.start,
            end_time=task.timeRange.end,
            metric_name=task.metricName,
            namespace="AWS/EC2",
            statistics=task.stats,
            dimensions=dict(InstanceId=task.instanceID),
            unit=task.unit)
        except BotoServerError as e:
          if e.status == 400 and e.error_code == "Throttling":
            # TODO: unit-test

            log.info("Throttling: %r", e)

            if backoffSec <= maxBackoffSec:
              time.sleep(backoffSec)
              backoffSec *= backoffGrowthFactor
            else:
              raise app_exceptions.MetricThrottleError(repr(e))
          else:
            raise

      # Sort the data by timestamp in ascending order
      rawdata.sort(key=lambda row: row["Timestamp"])

      # Convert raw data to MetricRecord objects
      def getValue(rawDataItem, stats):
        if isinstance(stats, basestring):
          return rawDataItem[stats]
        else:
          return dict((field, rawDataItem[field]) for field in stats)

      taskResult.data = tuple(
        MetricRecord(timestamp=rawItem["Timestamp"],
                     value=getValue(rawItem, task.stats))
      for rawItem in rawdata)

  except Exception as e:  # pylint: disable=W0703
    log.exception("Error in task=%r", task)
    taskResult.exception = e
  finally:
    taskResult.duration = time.time() - taskResult.creationTime

  return taskResult



class EC2InstanceMetricGetter(object):

  # The keys are the AWS CloudWatch names and the values are the corresponding
  # YOMP runtime names of those statistics
  _STATS_OF_INTEREST = {
    "Maximum": "max",
    "Minimum": "min"
  }

  # Number of concurrent worker processes used for querying metrics
  _WORKER_PROCESS_POOL_SIZE = 35

  # Interval for updating our cache of instances associated with autostacks
  _INSTANCE_CACHE_UPDATE_INTERVAL_SEC = 10 * 60

  # Instance cache garbage collection interval: 24 hours
  _INSTANCE_CACHE_GC_INTERVAL_SEC = 24 * 60 * 60

  _MAX_INSTANCE_CACHE_ITEM_AGE_SEC = 12 * 60 * 60


  def __init__(self):
    self._log = _getLogger()


    # A cache of instances belonging to each auto-stack; each key is an
    # Autostack's uid and the corresponding value is an _InstanceCacheValue
    # object
    self._instanceCache = dict()

    # Timestamp of the last time we updated instance cache. The update interval
    # is EC2InstanceMetricGetter._INSTANCE_CACHE_UPDATE_INTERVAL_SEC
    self._lastInstanceCacheUpdateTimestamp = time.time()

    # Timestamp of the last time we garbage-collected the Autostacks insance
    # cache. The garbage-collection interval is
    # EC2InstanceMetricGetter._INSTANCE_CACHE_GC_INTERVAL_SEC
    self._lastInstanceCacheGCTimestamp = time.time()

    # NOTE: the process pool must be created BEFORE this main (parent) process
    # creates any global or class-level shared resources that are also used by
    # the pool workers (e.g., boto connections) that would have undersirable
    # consequences when replicated into and used by forked child processes
    # (e.g., the same MySQL connection socket file descriptor used by multiple
    # processes). And we can't take advantage of the process Pool's
    # maxtasksperchild feature either (for the same reason)
    self._processPool = multiprocessing.Pool(
      processes=self._WORKER_PROCESS_POOL_SIZE,
      initializer=logging_support.LoggingSupport.initService,
      maxtasksperchild=None)


  def close(self):
    """ Clean up: terminate process pool, etc. """
    self._log.info("Closing...")
    self._processPool.close()
    self._processPool.join()
    self._processPool = None


  def collectMetricData(self, requests):
    """ Collect metric data for each of the requested Autostack models

    NOTE: presently supports only EC2 Instance metrics

    NOTE: not thread-safe

    :param requests: Metric collection requests
    :type requests: A sequence of AutostackMetricRequest objects

    :returns: An iterator that doles out metric data collected from each
        autostack's instances for the requested Metrics in no particular order.
        Each MetricCollection object produced by the iterator includes the refID
        value from the corresponding AutostackMetricRequest object. NOTE: There
        may be gaps in individual data sequences corresponding to periods when
        the corresponding resource was inactive
    :rtype: _MetricCollectionIterator
    """
    # Update Autostack instance cache
    autostackMap = dict((request.autostack.uid, request.autostack)
                        for request in requests)

    self._updateInstanceCache(autostackMap.values())

    # Create tasks to be executed concurrently
    tasks, accumulatorMap = self._createMetricDataCollectionTasks(
      requests,
      self._instanceCache)

    # Execute collections tasks concurrently
    # TODO: evaluate performance with
    #   chunksize=max(1, len(tasks)//self._WORKER_PROCESS_POOL_SIZE)
    taskResultsIter = self._processPool.imap_unordered(_collectMetrics, tasks,
                                                       chunksize=1)

    return _MetricCollectionIterator(
      taskResultsIter=taskResultsIter,
      collectionAccumulatorMap=accumulatorMap,
      numTasks=len(tasks),
      log=self._log)


  def collectMetricStatistics(self, autostack, metric):
    """ Get a sequence of min/max statistics for a given metric from the
    Autostack's instances

    :param autostack: an autostack object
    :type autostack: TODO

    :param metric: a metric object linked to the given autostack
    :type metric: TODO

    :returns: a possibly empty, unordered sequence of InstanceMetricData
      objects, each containing a single MetricRecord object in its `records`
      attribute.
    """
    self._updateInstanceCache((autostack,))

    executionStart = time.time()

    # Initialize the result
    result = tuple()

    # Determine the maximum time range for gathering individual statistics
    timeSlice = self._getMetricStatisticsTimeSlice(period=metric.poll_interval)

    # Create tasks for concurrent execution
    tasks = self._createMetricStatisticsCollectionTasks(
      autostack=autostack,
      metric=metric,
      stats=self._STATS_OF_INTEREST.keys(),
      timeSlice=timeSlice,
      instanceCache=self._instanceCache)

    # Execute the tasks, if any, via worker pool
    numFailedTasks = 0
    sampleInfo = None
    if tasks:
      # TODO: evaluate performance with
      #   chunksize=max(1, len(tasks)//self._WORKER_PROCESS_POOL_SIZE)
      taskResults = self._processPool.map(_collectMetrics, tasks, chunksize=1)

      assert len(taskResults) == len(tasks), (len(taskResults), len(tasks))

      result, numFailedTasks, sampleInfo = (
        self._processMetricStatisticsResults(
          taskResults=taskResults,
          log=self._log))

    self._log.info(
      "Completed collection of stats for metric=<%s> of autostack=<%s>: "
      "numTasks=%d; numFailedTasks=%s; sampleCounts=%s; numSlices=%s; "
      "duration=%ss",
      getMetricLogPrefix(metric), getAutostackLogPrefix(autostack), len(tasks),
      numFailedTasks, sampleInfo, len(result), time.time() - executionStart)

    return result


  @classmethod
  def _createMetricDataCollectionTasks(cls, requests, instanceCache):
    """ Create tasks to be executed concurrently from the given collection
    requests.

    :param requests: Metric collection requests
    :type requests: A sequence of AutostackMetricRequest objects

    :param instanceCache: Autostack instance cache. All Autostacks referenced in
                          requests are expected to be present in instance cache
    :type instanceCache: a dict, where each key is an Autostack uid and the
                         corresponding value is an _InstanceCacheValue object

    :returns: data collection tasks and request
        refID-to-_MetricCollectionAccumulator mappings
    :rtype: A two-tuple:
        The first element is a sequence of _MetricCollectionTask objects with
        refID values from the corresponding AutostackMetricRequest objects;
        The second elment is a dict of the
        refID-to-_MetricCollectionAccumulator mappings. The refID values are the
        ones provided by user in the corresponding AutostackMetricRequest
        objects.
    """
    accumulatorMap = dict()
    tasks = []
    for request in requests:
      refID = request.refID
      autostack = request.autostack
      metric = request.metric
      period = metric.poll_interval
      slaveDatasource = AutostackMetricAdapterBase.getMetricDatasource(metric)

      if slaveDatasource == "autostacks":
        timeRange = cls._getMetricCollectionTimeSliceForAutostackMetric(
          period=period)
      else:
        timeRange = cls._getMetricCollectionTimeSlice(
          startTime=metric.last_timestamp,
          period=period)

      instanceCacheItem = instanceCache[autostack.uid]

      region = autostack.region

      metricAdapter = AutostackMetricAdapterBase.getMetricAdapter(
        slaveDatasource)
      queryParams = metricAdapter.getQueryParams(metric.name)
      metricName = metric.name.split("/")[-1]
      stats = queryParams["statistics"]
      unit = queryParams["unit"]

      # Generate metric data collection tasks for the current request
      for instance in instanceCacheItem.instances:
        # instance is an aggregator_instances.InstanceInfo object
        task = _MetricCollectionTask(
          refID=refID,
          metricID=metric.uid,
          region=region,
          instanceID=instance.instanceID,
          metricName=metricName,
          stats=stats,
          unit=unit,
          period=period,
          timeRange=timeRange)

        tasks.append(task)

      # Create the metric collection accumulator for the current request
      assert refID not in accumulatorMap
      accumulatorMap[refID] = _MetricCollectionAccumulator(
        expectedNumSlices=len(instanceCacheItem.instances),
        collection=MetricCollection(
          refID=refID, slices=[], timeRange=timeRange,
          nextMetricTime=timeRange.end))

    return tasks, accumulatorMap


  @classmethod
  def _createMetricStatisticsCollectionTasks(
      cls,
      autostack,
      metric,
      stats,
      timeSlice,
      instanceCache):
    """ Create tasks to be executed concurrently from the given collection
    requests.

    NOTE: making a separate function to benefit unit-testing

    :param autostack: an autostack object
    :type autostack: TODO

    :param metric: a metric object linked to the given autostack
    :type metric: TODO

    :param stats: a sequence of AWS CloudWatch statistic names to be
        retrieved; e.g., ("Maximum", "Minimum")

    :param timeSlice: the time range of the metric data for which the statistics
        are to be gathered.
    :type timeSlice: YOMP.app.runtime.aggregator_utils.TimeRange

    :param instanceCache: Autostack instance cache. All Autostacks referenced in
        requests are expected to be present in instance cache
    :type instanceCache: a dict, where each key is an Autostack uid and the
        corresponding value is an _InstanceCacheValue object

    :returns: statistic collection tasks for execution by the _collectMetrics
        function via the worker pool
    :rtype: a sequence of _MetricCollectionTask objects
    """
    # Generate metric statistics collection tasks
    tasks = []
    instanceCacheItem = instanceCache[autostack.uid]
    granularity = int((timeSlice.end - timeSlice.start).total_seconds())
    for instance in instanceCacheItem.instances:
      # instance is an .aggregator_instances.InstanceInfo object
      task = _MetricCollectionTask(
        refID=0,
        metricID=metric.uid,
        region=autostack.region,
        instanceID=instance.instanceID,
        metricName=metric.name,
        stats=stats,
        unit=None,
        period=granularity,
        timeRange=timeSlice)

      tasks.append(task)

    return tasks


  @classmethod
  def _processMetricStatisticsResults(cls, taskResults, log):
    """ Convert given task results to a sequence of instance-metrics

    :param taskResults: Results of metric statistics collection tasks
    :type taskResults: sequence of _MetricCollectionTaskResult objects

    :param log: a logger object for logging messages

    :returns: statistics of intenrest that were collected from each instance of
        the requested Autostack/metric; also the task failure count and
        diagnostic info
    :rtype: a three-tuple:
        First element: a possibly empty, unordered sequence of
          InstanceMetricData objects containing a single MetricRecord object.
        Second element: task failure count.
        Third element: diagnostic info about samples

    TODO: unit-test
    """
    instanceMetricsList = []

    numFailedTasks = 0
    sampleInfo = defaultdict(int)

    for taskResult in taskResults:
      if taskResult.exception is not None:
        numFailedTasks += 1
      else:
        if len(taskResult.data) > 1:
          log.error(
            "Metric statistics task returned more than one record: "
            "numRecords=%d; taskResult=%s", len(taskResult.data), taskResult)

        if taskResult.data:
          statistics = dict()
          for statName, value in taskResult.data[0].value.iteritems():
            if not isinstance(value, float):
              log.error("Unexpected value=%s of type=%s for stat=%s in "
                        "taskResult=%s", value, type(value), statName,
                        taskResult)
              continue

            if math.isnan(value):
              # TODO: Not sure if NaN is to be expected. adapters.cloudwatch
              # had some logic to deal with them. If they are normal,
              # then downgrade the log statement to `debug`
              log.error("NaN value for stat=%s of taskResult=%s",
                        statName, taskResult)
              continue

            localStatName = cls._STATS_OF_INTEREST[statName]
            statistics[localStatName] = value
            sampleInfo[localStatName] += 1

          if statistics:
            instanceMetricsList.append(
              InstanceMetricData(
                instanceID=taskResult.instanceID,
                records=(MetricRecord(timestamp=taskResult.data[0].timestamp,
                                      value=statistics),)))

    return instanceMetricsList, numFailedTasks, sampleInfo


  @classmethod
  def _garbageCollectInstanceCache(cls, instanceCache):
    originalItemCount = len(instanceCache)

    for uid, cacheItem in instanceCache.items():
      if ((time.time() - cacheItem.lastUseTimestamp) >
          cls._MAX_INSTANCE_CACHE_ITEM_AGE_SEC):
        instanceCache.pop(uid)

    newItemCount = len(instanceCache)
    _getLogger().info("Garbage-collected Autostacks instance cache: "
                      "newItemCount=%d; originalItemCount=%d; numPurged=%d",
                      newItemCount, originalItemCount,
                      originalItemCount - newItemCount)


  def _updateInstanceCache(self, autostacks):
    """ Garbage-collect Autostacks instance cache if it's time. Update
    Autostacks instance cache for the given Autostacks, if missing;
    refresh the entire Autostacks instance cache if it's time for refreshing
    Also refresh last-used timestamps of instance cache entries corresponding to
    the given Autostacks.

    :param autostacks: Autostack objects from the current collection request
    :type autostacks: List of nametuple as returned by
      repository.getAutostackMetricsPendingDataCollection().  Each autostack
      item has attributes that match columns defined in
      YOMP.app.repository.schema.autostack.  See also: AggregatorService.run()
    """
    # Garbage-collect the Autostack instance cache
    if ((time.time() - self._lastInstanceCacheGCTimestamp) >
        self._INSTANCE_CACHE_GC_INTERVAL_SEC):
      self._garbageCollectInstanceCache(self._instanceCache)
      self._lastInstanceCacheGCTimestamp = time.time()

    # Check if there are new autostacks that were not in cache and also
    # update last-use timestamp of the cache items that were
    autostacksToRefresh = []
    for autostack in autostacks:
      if autostack.uid not in self._instanceCache:
        autostacksToRefresh.append(
          (autostack.uid,
           autostack.region,
           autostack.filters,))

    refreshingEntireCache = False

    if ((time.time() - self._lastInstanceCacheUpdateTimestamp) >
        self._INSTANCE_CACHE_UPDATE_INTERVAL_SEC):
      # It's time to refresh the entire cache
      refreshingEntireCache = True
      for uid, cacheItem in self._instanceCache.iteritems():
        autostacksToRefresh.append((uid, cacheItem.region, cacheItem.filters,))

    if autostacksToRefresh:
      self._log.info(
        "Refreshing Autostack instance cache: entire=%r; numAutostacks=%d",
        refreshingEntireCache, len(autostacksToRefresh))

      cacheRefreshStart = time.time()

      self._instanceCache.update(
        self._fetchInstanceCacheItems(autostacksToRefresh))

      self._log.info(
        "Refreshed Autostack instance cache: entire=%r; numAutostacks=%d; "
        "totalAutostacks=%d; duration=%ss", refreshingEntireCache,
        len(autostacksToRefresh), len(self._instanceCache),
        time.time() - cacheRefreshStart)

      if refreshingEntireCache:
        self._lastInstanceCacheUpdateTimestamp = time.time()

    # Update last-used timestamps of affected autostacks in instance cache
    for autostack in autostacks:
      self._instanceCache[autostack.uid].use()


  def _fetchInstanceCacheItems(self, autostackDescriptions):
    """ Query AWS and build instance cache items for the given Autostack
    descriptions.

    :param autostackDescriptions: Descriptions of Autostacks to update
    :type autostackDescriptions: A sequence of three-tuples:
        ((autostackID, region, filters,), ...). See
        aggregator_instances.getAutostackInstances for description of
        `filters`

    :returns: Instances corresponding to the given Autostack descriptions
    :rtype: A sequence of two-tuples: (autostackID, _InstanceCacheValue())
    """

    # Execute tasks concurrently via process pool
    resultItems = []
    resultsIter = self._processPool.imap(_matchAutostackInstances,
                                         autostackDescriptions)
    for (autostackID, region, filters), instances in itertools.izip_longest(
        autostackDescriptions, resultsIter):
      # Create Autostack instance cache items for the completed region
      resultItems.append(
        (autostackID, _InstanceCacheValue(region=region, filters=filters,
                                          instances=instances),))

    return resultItems


  @classmethod
  def _getData(cls, regionName, instanceID, metricName, stats, unit, period,
              startTime, endTime):
    """ For experimentation """
    cw = cloudwatch.connect_to_region(region_name=regionName,
                                      **getAWSCredentials())

    data = cw.get_metric_statistics(
      period=period,
      start_time=startTime,
      end_time=endTime,
      metric_name=metricName,
      namespace="AWS/EC2",
      statistics=stats,
      dimensions=dict(InstanceId=instanceID),
      unit=unit)

    return data


  @classmethod
  def _getMetricCollectionTimeSliceForAutostackMetric(cls, period):
    """ Determine metric data collection time range, truncated at the time
    indicated by the current time window.

    :param period: Metric period in seconds; must be multiple of 60
    :type period: integer
    :returns: time range for collecting metrics for the current time window.
    :rtype: YOMP.app.runtime.aggregator_utils.TimeRange
    """
    now = datetime.utcnow().replace(second=0, microsecond=0)
    endTime = now - timedelta(
      seconds=cloudwatch_utils.getMetricCollectionBackoffSeconds(period))
    startTime = endTime - timedelta(seconds=period)

    return TimeRange(start=startTime, end=endTime)


  @classmethod
  def _getMetricCollectionTimeSlice(cls, startTime, period):
    """ Determine metric data collection time range.

    :param startTime: UTC start time of planned metric data collection; may be
                      None when called for the first time, in which case a start
                      time will be calculated and returned in the result (even
                      if there is not enough time for at least one period of
                      metric data collection)
    :type startTime: datetime.datetime
    :param period: Metric period in seconds; must be multiple of 60
    :type period: integer
    :returns: time range for collecting metrics adjusted for integral number of
              periods. If there is not enough time for at least one period,
              then end-time will be set equal to start-time
    :rtype: YOMP.app.runtime.aggregator_utils.TimeRange
    """
    startTime, endTime = cloudwatch_utils.getMetricCollectionTimeRange(
      startTime=startTime,
      endTime=None,
      period=period)

    return TimeRange(start=startTime, end=endTime)


  @classmethod
  def _getMetricStatisticsTimeSlice(cls, period):
    """ Determine metric statistics collection time range for the maximum range
    appropriate for aggregation of the statistic values of an Autostack

    :param period: Metric period in seconds; must be multiple of 60
    :type period: integer
    :returns: time range for collecting metric statistics adjusted for integral
              number of metric periods.
    :rtype: YOMP.app.runtime.aggregator_utils.TimeRange
    """
    startTime, endTime = cloudwatch_utils.getMetricCollectionTimeRange(
      startTime=None,
      endTime=None,
      period=period)

    return TimeRange(start=startTime, end=endTime)
