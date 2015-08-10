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

"""Logic for aggregating metric data"""

import collections
import math
import numbers

from YOMP.app import repository
from YOMP.app.runtime.aggregator_metric_collection import (
    EC2InstanceMetricGetter)



def average(values):
  return sum(values) / len(values)


def aggregate(slices, aggregationFn=average):
  """Aggregate values from multiple metrics by timestamp.

  :param metric: Metric instance.
  :param slices: slices from aggregator_metric_collection.MetricCollection.
      NOTE: see MetricCollection documentation for important details and
      examples.
  :returns: a sequence of aggregated metric data records suitable for sending
      to app MetricStreamer
  :rtype: a (possibly empty) sequence of metric data records; each metric data
      record is a tuple (timestamp, value)
          timestamp: UTC datetime.datetime object
          value: value of the metric
  """
  # Group the metrics into buckets by timestamp
  instanceMetricMap = collections.defaultdict(list)
  for instanceMetric in slices:
    for metricRecord in instanceMetric.records:
      instanceMetricMap[metricRecord.timestamp].append(metricRecord.value)

  # Aggregate and return the metrics in timestamp order
  return [(timestamp, aggregationFn(values))
          for timestamp, values in sorted(instanceMetricMap.iteritems())]


def getStatistics(metric):
  """Get aggregate statistics for an Autostack metric.

  The metric must belong to an Autostack or a ValueError will be raised. If AWS
  returns no stats and there is no data in the database then an
  ObjectNotFoundError will be raised.

  :param metric: the Autostack metric to get statistics for
  :type metric: TODO

  :returns: metric statistics
  :rtype: dict {"min": minVal, "max": maxVal}

  :raises: ValueError if the metric doesn't not belong to an Autostack

  :raises: YOMP.app.exceptions.ObjectNotFoundError if the metric or the
      corresponding autostack doesn't exist; this may happen if it got deleted
      by another process in the meantime.

  :raises: YOMP.app.exceptions.MetricStatisticsNotReadyError if there are no or
      insufficent samples at this time; this may also happen if the metric and
      its data were deleted by another process in the meantime
  """
  engine = repository.engineFactory()

  if metric.datasource != "autostack":
    raise ValueError(
      "Metric must belong to an Autostack but has datasource=%r"
      % metric.datasource)
  metricGetter = EC2InstanceMetricGetter()
  try:
    with engine.connect() as conn:
      autostack = repository.getAutostackFromMetric(conn, metric.uid)
    instanceMetricList = metricGetter.collectMetricStatistics(autostack, metric)
  finally:
    metricGetter.close()

  n = 0
  mins = 0.0
  maxs = 0.0
  for instanceMetric in instanceMetricList:
    assert len(instanceMetric.records) == 1
    metricRecord = instanceMetric.records[0]
    stats = metricRecord.value

    if (not isinstance(stats["min"], numbers.Number) or
        math.isnan(stats["min"]) or
        not isinstance(stats["max"], numbers.Number) or
        math.isnan(stats["max"])):
      # Cloudwatch gave us bogus data for this metric so we will exclude it
      continue

    mins += stats["min"]
    maxs += stats["max"]
    n += 1

  if n == 0:
    # Fall back to metric_data when we don't get anything from AWS. This may
    # raise an MetricStatisticsNotReadyError if there is no or not enough data.
    with engine.connect() as conn:
      dbStats = repository.getMetricStats(conn, metric.uid)
    minVal = dbStats["min"]
    maxVal = dbStats["max"]
  else:
    minVal = mins / n
    maxVal = maxs / n

  # Now add the 20% buffer on the range
  buff = (maxVal - minVal) * 0.2
  minVal -= buff
  maxVal += buff

  return {"min": minVal,
          "max": maxVal}
