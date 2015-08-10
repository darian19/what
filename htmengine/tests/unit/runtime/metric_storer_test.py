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

"""Tests the metric storer."""

# Disable pylint warning: "access to protected member"
# pylint: disable=W0212

import datetime
import unittest

from mock import MagicMock, patch

from htmengine.runtime import metric_storer


class MetricStorerTest(unittest.TestCase):

  @patch("htmengine.runtime.metric_storer._addMetric")
  @patch("sqlalchemy.engine")
  def testHandleBatchSingle(self, mockEngine, addMetricMock):
    # Create mocks
    metric_storer.gCustomMetrics = {}
    metricMock = MagicMock()
    def addMetricSideEffect(*_args, **_kwargs):
      metric_storer.gCustomMetrics["test.metric"] = [
          metricMock, datetime.datetime.utcnow()]
    addMetricMock.side_effect = addMetricSideEffect
    modelSwapperMock = MagicMock()
    metricStreamerMock = MagicMock()
    body = '{"protocol": "plain", "data": ["test.metric 4.0 1386792175"]}'
    message = MagicMock()
    message.body = body
    # Call the function under test
    metric_storer._handleBatch(mockEngine, [message], [], metricStreamerMock,
                               modelSwapperMock)
    # Check the results
    addMetricMock.assert_called_once_with(mockEngine, "test.metric")
    metricStreamerMock.streamMetricData.assert_called_once()
    data, _uid, modelSwapper = metricStreamerMock.streamMetricData.call_args[0]
    self.assertIs(modelSwapper, modelSwapperMock)
    self.assertEqual(len(data), 1)
    self.assertEqual(len(data[0]), 2)
    self.assertEqual(repr(data[0][0]),
                     "datetime.datetime(2013, 12, 11, 20, 2, 55)")
    self.assertAlmostEqual(data[0][1], 4.0)

  @patch.object(metric_storer, "LOGGER")
  @patch("sqlalchemy.engine")
  def testHandleDataInvalidProtocol(self, mockEngine, loggingMock):
    """Ensure _handleData doesn't throw an exception for unknown protocol."""
    # Call the function under test
    body = ('{"protocol": "unknown_protocol",'
            ' "data": ["test.metric 4.0 1386792175"]}')
    message = MagicMock()
    message.body = body
    metric_storer._handleBatch(mockEngine, [message], [], MagicMock(),
                               MagicMock())
    # Check the results
    self.assertTrue(loggingMock.warn.called)


  @patch.object(metric_storer, "LOGGER")
  @patch("sqlalchemy.engine")
  def testHandleDataInvalidBody(self, mockEngine, loggingMock):
    """Make sure _handleData doesn't throw an exception for invalid data."""
    # Call the function under test
    body = '{"protocol": "plain", "data": ["test.metric 4.0 12:30PM"]}'
    message = MagicMock()
    message.body = body
    metric_storer._handleBatch(mockEngine, [message], [], MagicMock(),
                               MagicMock())
    # Check the results
    self.assertTrue(loggingMock.warn.called)


  def testTrimMetricCacheNoMetrics(self):
    metric_storer.MAX_CACHED_METRICS = 5
    metric_storer.CACHED_METRICS_TO_KEEP = 3
    metric_storer.gCustomMetrics = {}

    metric_storer._trimMetricCache()

    self.assertDictEqual(metric_storer.gCustomMetrics, {})


  def testTrimMetricCacheOneMetric(self):
    metric_storer.MAX_CACHED_METRICS = 5
    metric_storer.CACHED_METRICS_TO_KEEP = 3
    m1 = (MagicMock(), datetime.datetime.utcnow())
    metric_storer.gCustomMetrics = {"m1": m1}

    metric_storer._trimMetricCache()

    self.assertDictEqual(metric_storer.gCustomMetrics, {"m1": m1})


  def testTrimMetricCacheMaxMetric(self):
    metric_storer.MAX_CACHED_METRICS = 5
    metric_storer.CACHED_METRICS_TO_KEEP = 3
    startDT = datetime.datetime.utcnow()
    m1 = (MagicMock(), startDT)
    m2 = (MagicMock(), startDT)
    m3 = (MagicMock(), startDT)
    m4 = (MagicMock(), startDT)
    m5 = (MagicMock(), startDT)
    metric_storer.gCustomMetrics = {
        "m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5}

    metric_storer._trimMetricCache()

    self.assertDictEqual(metric_storer.gCustomMetrics,
                         {"m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5})


  def testTrimMetricCacheOverLimit(self):
    metric_storer.MAX_CACHED_METRICS = 5
    metric_storer.CACHED_METRICS_TO_KEEP = 3
    startDT = datetime.datetime.utcnow()
    td = datetime.timedelta(minutes=1)
    m1 = (MagicMock(), startDT - (td * 5))
    m2 = (MagicMock(), startDT - (td * 4))
    m3 = (MagicMock(), startDT - (td * 3))
    m4 = (MagicMock(), startDT - (td * 2))
    m5 = (MagicMock(), startDT - td)
    m6 = (MagicMock(), startDT)
    metric_storer.gCustomMetrics = {
        "m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5, "m6": m6}

    metric_storer._trimMetricCache()

    self.assertDictEqual(
        metric_storer.gCustomMetrics,
        {"m4": m4, "m5": m5, "m6": m6})



if __name__ == "__main__":
  unittest.main()
