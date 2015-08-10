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

"""Unit tests for aggregation functions."""

import datetime
import unittest

from mock import Mock, patch

from YOMP.app.exceptions import MetricStatisticsNotReadyError
from YOMP.app.runtime import aggregation
from YOMP.app.runtime.aggregator_metric_collection import (InstanceMetricData,
                                                           MetricRecord)


class AggregateTest(unittest.TestCase):
  """Unit tests for the aggregate function."""


  def testAggregationEmptyList(self):
    """No values in input list."""
    result = aggregation.aggregate([])
    self.assertSequenceEqual(result, ())


  def testAggregationEmptyTuple(self):
    """No values in input tuple."""
    result = aggregation.aggregate(())
    self.assertSequenceEqual(result, ())


  def testAggregationNoValues(self):
    """Single metric with no values."""
    slices = (
        InstanceMetricData("id", ()),
    )
    result = aggregation.aggregate(slices)
    self.assertEqual(len(result), 0)


  def testAggregationSingleValue(self):
    """Single metric with single value."""
    timestamp = datetime.datetime.utcnow()
    slices = (
        InstanceMetricData("id", (
            MetricRecord(timestamp, 100.0),
        )),
    )
    result = aggregation.aggregate(slices)
    self.assertEqual(len(result), 1)
    self.assertIsInstance(result[0], tuple)
    self.assertSequenceEqual(result[0], (timestamp, 100.0))


  def testAggregationMultipleValues(self):
    """Single metric with multiple values at different timestamps."""
    timestamp2 = datetime.datetime.utcnow()
    timestamp1 = timestamp2 - datetime.timedelta(minutes=5)
    slices = (
        InstanceMetricData("id", (
            MetricRecord(timestamp1, 100.0),
            MetricRecord(timestamp2, 50.0),
        )),
    )
    result = aggregation.aggregate(slices)
    self.assertEqual(len(result), 2)
    self.assertIsInstance(result[0], tuple)
    self.assertIsInstance(result[1], tuple)
    self.assertSequenceEqual(result[0], (timestamp1, 100.0))
    self.assertSequenceEqual(result[1], (timestamp2, 50.0))


  def testAggregationMultipleMetricsAligned(self):
    """Multiple metrics with matching timestamps."""
    timestamp2 = datetime.datetime.utcnow()
    timestamp1 = timestamp2 - datetime.timedelta(minutes=5)
    slices = (
        InstanceMetricData("id1", (
            MetricRecord(timestamp1, 100.0),
            MetricRecord(timestamp2, 50.0),
        )),
        InstanceMetricData("id2", (
            MetricRecord(timestamp1, 80.0),
            MetricRecord(timestamp2, 30.0),
        )),
    )
    result = aggregation.aggregate(slices)
    self.assertEqual(len(result), 2)
    self.assertIsInstance(result[0], tuple)
    self.assertIsInstance(result[1], tuple)
    self.assertSequenceEqual(result[0], (timestamp1, 90.0))
    self.assertSequenceEqual(result[1], (timestamp2, 40.0))


  def testAggregationMultipleMetricsAlignedSum(self):
    """Multiple metrics with matching timestamps."""
    timestamp2 = datetime.datetime.utcnow()
    timestamp1 = timestamp2 - datetime.timedelta(minutes=5)
    slices = (
        InstanceMetricData("id1", (
            MetricRecord(timestamp1, 100.0),
            MetricRecord(timestamp2, 50.0),
        )),
        InstanceMetricData("id2", (
            MetricRecord(timestamp1, 80.0),
            MetricRecord(timestamp2, 30.0),
        )),
    )
    result = aggregation.aggregate(slices, aggregationFn=sum)
    self.assertEqual(len(result), 2)
    self.assertIsInstance(result[0], tuple)
    self.assertIsInstance(result[1], tuple)
    self.assertSequenceEqual(result[0], (timestamp1, 180.0))
    self.assertSequenceEqual(result[1], (timestamp2, 80.0))


  def testAggregationMultipleMetricsMisaligned(self):
    """Multiple metrics with both matching and non-matching timestamps."""
    timestamp3 = datetime.datetime.utcnow()
    timestamp2 = timestamp3 - datetime.timedelta(minutes=5)
    timestamp1 = timestamp2 - datetime.timedelta(minutes=5)
    slices = (
        InstanceMetricData("id1", (
            MetricRecord(timestamp1, 100.0),
            MetricRecord(timestamp2, 50.0),
        )),
        InstanceMetricData("id2", (
            MetricRecord(timestamp2, 80.0),
            MetricRecord(timestamp3, 30.0),
        )),
    )
    result = aggregation.aggregate(slices)
    self.assertEqual(len(result), 3)
    self.assertIsInstance(result[0], tuple)
    self.assertIsInstance(result[1], tuple)
    self.assertIsInstance(result[2], tuple)
    self.assertSequenceEqual(result[0], (timestamp1, 100.0))
    self.assertSequenceEqual(result[1], (timestamp2, 65.0))
    self.assertSequenceEqual(result[2], (timestamp3, 30.0))



class GetStatisticsTest(unittest.TestCase):
  """Unit tests for the getStatistics function."""

  @patch("YOMP.app.runtime.aggregation.repository")
  @patch("YOMP.app.runtime.aggregation.EC2InstanceMetricGetter")
  def testGetStatisticsNoData(self, ec2InstanceMetricGetterMock,
                                 repositoryMock):
    metricID = "abc"
    class MetricRowSpec(object):
      uid = None
      datasource = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        uid=metricID,
        datasource="autostack")
    autostackMock = Mock()
    repositoryMock.getAutostackFromMetric = Mock(return_value=autostackMock)
    repositoryMock.getMetricStats.side_effect = MetricStatisticsNotReadyError()
    metricGetterMock = Mock()

    ec2InstanceMetricGetterMock.return_value = metricGetterMock
    metricGetterMock.collectMetricStatistics.return_value = []

    # Call the function under test
    with self.assertRaises(MetricStatisticsNotReadyError):
      aggregation.getStatistics(metricRowMock)

    self.assertEqual(repositoryMock.getAutostackFromMetric.call_args[0][1],
                     metricID)

    metricGetterMock.collectMetricStatistics.assert_called_once_with(
        autostackMock, metricRowMock)
    metricGetterMock.close.assert_called_once()


  @patch("YOMP.app.runtime.aggregation.repository")
  @patch("YOMP.app.runtime.aggregation.EC2InstanceMetricGetter")
  def testGetStatisticsSingleInstance(self, ec2InstanceMetricGetterMock,
                                      repositoryMock):
    metricID = "abc"
    class MetricRowSpec(object):
      uid = None
      datasource = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        uid=metricID,
        datasource="autostack")

    autostackMock = Mock()
    repositoryMock.getAutostackFromMetric = Mock(return_value=autostackMock)

    metricGetterMock = Mock()
    ec2InstanceMetricGetterMock.return_value = metricGetterMock
    metricGetterMock.collectMetricStatistics.return_value = [
        InstanceMetricData(
            instanceID="tempID",
            records=[MetricRecord(timestamp=None,
                                  value={"min": 5.0, "max": 20.0})]),
    ]

    # Call the function under test
    stats = aggregation.getStatistics(metricRowMock)

    # Validate stats
    self.assertSetEqual(set(stats.keys()), set(("min", "max")))
    # Make sure to include 20% buffer on range
    self.assertAlmostEqual(stats["min"], 2.0)
    self.assertAlmostEqual(stats["max"], 23.0)

    # Validate mocks were called correctly
    self.assertEqual(repositoryMock.getAutostackFromMetric.call_args[0][1],
                     metricID)

    metricGetterMock.collectMetricStatistics.assert_called_once_with(
        autostackMock, metricRowMock)
    metricGetterMock.close.assert_called_once()


  @patch("YOMP.app.runtime.aggregation.repository.engineFactory", autospec=True)
  @patch("YOMP.app.repository.getAutostackFromMetric", autospec=True)
  @patch("YOMP.app.runtime.aggregation.EC2InstanceMetricGetter", autospec=True)
  def testGetStatisticsMultpleInstances(self, ec2InstanceMetricGetterMock,
                                        getAutostackFromMetricMock,
                                        _engineFactoryMock):

    metricID = "abc"
    class MetricRowSpec(object):
      uid = None
      datasource = None
    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        uid=metricID,
        datasource="autostack")
    autostackMock = Mock()
    getAutostackFromMetricMock.return_value = autostackMock

    metricGetterMock = Mock()
    ec2InstanceMetricGetterMock.return_value = metricGetterMock
    metricGetterMock.collectMetricStatistics.return_value = [
        InstanceMetricData(
            instanceID="tempID1",
            records=[MetricRecord(timestamp=None,
                                  value={"min": 5.0, "max": 20.0})]),
        InstanceMetricData(
            instanceID="tempID2",
            records=[MetricRecord(timestamp=None,
                                  value={"min": 15.0, "max": 30.0})]),
    ]

    # Call the function under test
    stats = aggregation.getStatistics(metricRowMock)

    # Validate stats
    self.assertSetEqual(set(stats.keys()), set(("min", "max")))
    # Make sure to include 20% buffer on range
    self.assertAlmostEqual(stats["min"], 7.0)
    self.assertAlmostEqual(stats["max"], 28.0)

    # Validate mocks were called correctly
    self.assertEqual(getAutostackFromMetricMock.call_args[0][1], metricID)

    metricGetterMock.collectMetricStatistics.assert_called_once_with(
        autostackMock, metricRowMock)
    metricGetterMock.close.assert_called_once()



if __name__ == "__main__":
  unittest.main()
