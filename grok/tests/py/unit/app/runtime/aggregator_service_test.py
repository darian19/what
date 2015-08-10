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

""" Unit tests for aggregator_service.py """

# Disable pylint warning: "Access to a protected member"
# pylint: disable=W0212

import datetime
import unittest

from mock import Mock, patch

from YOMP.app import exceptions as app_exceptions

from YOMP.app.runtime import aggregator_service

from YOMP.app.runtime.aggregator_metric_collection import (
  AutostackMetricRequest,
  InstanceMetricData,
  MetricRecord,
  MetricCollection)

from YOMP.app.runtime import aggregator_utils

from htmengine.model_swapper.model_swapper_interface import \
  ModelSwapperInterface


class AggregatorServiceTestCase(unittest.TestCase):

  def setUp(self):
    class MetricRowSpec(object):
      uid = "abc"
      name = None
      datasource = None
      description = None
      server = None
      status = None
      last_timestamp = None

    class AutostackRowSpec(object):
      uid = "def"

    timeRange = aggregator_utils.TimeRange(
      datetime.datetime.utcnow(),
      datetime.datetime.utcnow())

    self.MetricRowSpec = MetricRowSpec
    self.AutostackRowSpec = AutostackRowSpec
    self.timeRange = timeRange


  @patch("YOMP.app.runtime.aggregator_service.MetricStreamer",
         autospec=True)
  @patch("YOMP.app.runtime.aggregator_service.EC2InstanceMetricGetter",
         autospec=True)
  @patch.object(aggregator_service, "repository", autospec=True)
  @patch("sqlalchemy.engine.Engine", autospec=True)
  def testMetricNotFoundFromSetLastTimestamp(self,
                                             engineMock,
                                             repoMock,
                                             ec2InstanceMetricGetterMock,
                                             _metricStreamerMock):
    """Test handling of ObjectNotFoundError when calling
    repository.setMetricLastTimestamp in _processAutostackMetricRequests.
    In this case, we expect _processAutostackMetricRequests to skip this
    collection and continue processing the next one(s)
    """

    # Ignore attemting to look for MySQL transient errors.
    # We're not testing those here.
    repoMock.retryOnTransientErrors.side_effect = lambda f: f

    # Define metric to skip over
    errMetric = Mock(spec_set=self.MetricRowSpec)
    errMetric.name = "errMetric"

    errInstanceID = "i-00000"
    errRefID = 0  # index into requests sequence
    errRequest = AutostackMetricRequest(
      refID=errRefID,
      autostack=Mock(spec_set=self.AutostackRowSpec),
      metric=errMetric
    )

    errMetricRecord = MetricRecord(timestamp=datetime.datetime.utcnow(),
                                   value=2)
    errData = InstanceMetricData(
      instanceID=errInstanceID,
      records=[errMetricRecord])

    errCollection = MetricCollection(
      refID=errRefID,
      slices=[errData],
      timeRange=self.timeRange,
      nextMetricTime=self.timeRange.end)

    # Define "ok" metric
    okMetric = Mock(spec_set=self.MetricRowSpec)
    okMetric.name = "okMetric"

    okInstanceID = "i-11111"
    okRefID = 1  # index into requests sequence
    okRequest = AutostackMetricRequest(
      refID=okRefID,
      autostack=Mock(spec_set=self.AutostackRowSpec),
      metric=okMetric
    )

    okDataValue = 111
    okMetricRecord = MetricRecord(timestamp=datetime.datetime.utcnow(),
                                  value=okDataValue)
    okData = InstanceMetricData(
      instanceID=okInstanceID,
      records=[okMetricRecord])

    okCollection = MetricCollection(
      refID=okRefID,
      slices=[okData],
      timeRange=self.timeRange,
      nextMetricTime=self.timeRange.end)

    # Make setMetricLastTimestamp error on first call (error metric) and pass
    # on second call (ok metric)
    repoMock.setMetricLastTimestamp.side_effect = (
      app_exceptions.ObjectNotFoundError("Expected: things happen"), None)

    requests = [errRequest, okRequest]
    collections = [errCollection, okCollection]
    metricGetterInstanceMock = ec2InstanceMetricGetterMock.return_value
    metricGetterInstanceMock.collectMetricData.return_value = iter(collections)

    streamedData = []
    _metricStreamerMock.return_value.streamMetricData.side_effect = (
      lambda data, *args, **kwargs: streamedData.append(data))

    aggSvc = aggregator_service.AggregatorService()
    with patch.object(aggregator_service, "getAggregationFn", autospec=True,
                      return_value=None):
      aggSvc._processAutostackMetricRequests(
        engine=engineMock,
        requests=requests,
        modelSwapper=Mock(spec_set=ModelSwapperInterface))

    self.assertEqual(len(streamedData), 1)
    self.assertEqual(len(streamedData[0]), 1)
    self.assertEqual(streamedData[0][0][1], okDataValue)



if __name__ == "__main__":
  unittest.main()
