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
Unit tests for YOMP.app.runtime.metric_collector
"""

# Disable warning: Used builtin function 'map' (bad-builtin)
# pylint: disable=W0141

# Disable warning: Method could be a function (no-self-use)
# pylint: disable=R0201

# Disable warning: No exception type(s) specified (bare-except)
# pylint: disable=W0702

import copy
import datetime
import itertools
import json
import multiprocessing
import sys
import threading
import time
import unittest

from collections import OrderedDict
from mock import patch, Mock
from boto.exception import BotoServerError

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from YOMP import logging_support
import YOMP.app
from YOMP.app.runtime import metric_collector
from YOMP.app.adapters.datasource.cloudwatch import _CloudwatchDatasourceAdapter



# Disable warning: Access to a protected member
# pylint: disable=W0212

# Disable warning: Invalid name (e.g., "MessageBusConnector") for type variable
# pylint: disable=C0103


def setUpModule():
  logging_support.LoggingSupport.initTestApp()



def _makeMetricMockInstance(metricPollInterval, timestamp, uid):
  class MetricRowSpec(object):
    name = None
    uid = None
    poll_interval = None
    last_timestamp = None
    collector_error = None
    server = None
    parameters = None
    datasource = None

  metricRowMock = Mock(spec_set=MetricRowSpec,
                        uid=uid, poll_interval=metricPollInterval,
                        last_timestamp=timestamp,
                        collector_error=None, server="fakeServer",
                        parameters=json.dumps({"metricSpec":{}}))
  metricRowMock.name = "TestName"
  return metricRowMock



def _makeFreshMetricMockInstance(metricPollInterval, uid):
  """ Returns a metric that doesn't need to be updated """
  return _makeMetricMockInstance(metricPollInterval,
                                 datetime.datetime.utcnow(), uid)


@patch.object(metric_collector, "multiprocessing", autospec=True)
@patch.object(metric_collector, "MetricStreamer", autospec=True)
@patch.object(metric_collector, "repository", autospec=True)
@patch.multiple(metric_collector.MetricCollector,
                _NO_PENDING_METRICS_SLEEP_SEC=0.001,
                _METRIC_QUARANTINE_DURATION_RATIO=0.0001,
                _RESOURCE_STATUS_UPDATE_INTERVAL_SEC=0.0)
@ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                      YOMP.app.config.baseConfigDir,
                      (("metric_collector", "poll_interval", "0.000001"),))
class MetricCollectorTestCase(unittest.TestCase):
  """
  Unit tests for YOMP.app.runtime.metric_collector
  """

  @patch.object(metric_collector, "createDatasourceAdapter", autospec=True)
  def testMetricCollectorRun(self, createAdapterMock, repoMock,
                             metricStreamerMock, multiprocessingMock):
    metricsPerChunk = 4

    # Configure multiprocessing
    def mapAsync(fn, tasks):
      class _(object):
        def wait(self):
          map(fn, tasks)
      return _()

    multiprocessingMock.Pool.return_value.map_async.side_effect = mapAsync
    multiprocessingMock.Pipe.side_effect = multiprocessing.Pipe
    multiprocessingMock.Manager = (
      Mock(return_value=(
        Mock(JoinableQueue=(
          Mock(side_effect=multiprocessing.JoinableQueue))))))

    metricPollInterval = 5

    now = datetime.datetime.today()

    resultsOfGetCloudwatchMetricsPendingDataCollection = [
      [],
      [_makeMetricMockInstance(metricPollInterval, now, 1)],
      [_makeMetricMockInstance(metricPollInterval, now, 2),
       _makeMetricMockInstance(metricPollInterval, now, 3)],
      KeyboardInterrupt("Fake KeyboardInterrupt to interrupt run-loop")
    ]

    repoMock.getCloudwatchMetricsPendingDataCollection.side_effect = (
      resultsOfGetCloudwatchMetricsPendingDataCollection)
    repoMock.retryOnTransientErrors.side_effect = lambda f: f

    # Configure the metric_collector.adapters module mock
    mockResults = [([], now),
                   ([[now, 1]] * metricsPerChunk,
                    now + datetime.timedelta(seconds=metricPollInterval)),
                   ([[now, 2]] * (metricsPerChunk * 5 + 1),
                    now + datetime.timedelta(seconds=metricPollInterval))]

    adapterInstanceMock = Mock(
      spec_set=_CloudwatchDatasourceAdapter)
    adapterInstanceMock.getMetricData.side_effect = mockResults
    adapterInstanceMock.getMetricResourceStatus.return_value = "status"

    createAdapterMock.return_value = adapterInstanceMock

    # Now, run MetricCollector and check results
    resultOfRunCollector = dict()
    def runCollector():
      try:
        collector = metric_collector.MetricCollector()
        resultOfRunCollector["returnCode"] = collector.run()
      except:
        resultOfRunCollector["exception"] = sys.exc_info()[1]
        raise
    with ConfigAttributePatch(
        YOMP.app.config.CONFIG_NAME,
        YOMP.app.config.baseConfigDir,
        (("metric_streamer", "chunk_size", str(metricsPerChunk)),)):

      # We run it in a thread in order to detect if MetricCollector.run fails to
      # return and to make sure that the test script will finish (in case run
      # doesn't)
      thread = threading.Thread(target=runCollector)
      thread.setDaemon(True)
      thread.start()

      thread.join(60)
      self.assertFalse(thread.isAlive())

    self.assertIn("exception", resultOfRunCollector)
    self.assertIsInstance(resultOfRunCollector["exception"], KeyboardInterrupt)
    self.assertNotIn("returnCode", resultOfRunCollector)

    self.assertEqual(adapterInstanceMock.getMetricData.call_count,
                     len(mockResults))

    # Validate that all expected data points were published

    # ... validate metricIDs
    metricIDs = [kwargs["metricID"]
                 for (args, kwargs) in metricStreamerMock.return_value
                                                         .streamMetricData
                                                         .call_args_list]
    expectedMetricIDs = []
    getDataIndex = 0
    for metrics in resultsOfGetCloudwatchMetricsPendingDataCollection:
      if not metrics or isinstance(metrics, BaseException):
        continue
      for m in metrics:
        results = mockResults[getDataIndex][0]
        if results:
          expectedMetricIDs.append(m.uid)

        getDataIndex += 1


    self.assertEqual(metricIDs, expectedMetricIDs)

    # ... validate data points
    dataPoints = list(itertools.chain(*[args[0]
                                        for (args, kwargs)
                                        in metricStreamerMock.return_value
                                                             .streamMetricData
                                                             .call_args_list]))
    expectedDataPoints = list(itertools.chain(
      *[copy.deepcopy(r[0]) for r in mockResults if r[0]]))
    self.assertEqual(dataPoints, expectedDataPoints)

    # Assert instance status collected
    self.assertTrue(adapterInstanceMock.getMetricResourceStatus.called)

    # saveMetricInstanceStatus uses a connection, not an engine
    mockConnection = (repoMock.engineFactory.return_value.begin.return_value
                      .__enter__.return_value)


    # Assert instance status recorded
    for metricObj in resultsOfGetCloudwatchMetricsPendingDataCollection[1]:
      repoMock.saveMetricInstanceStatus.assert_any_call(
        mockConnection,
        metricObj.server,
        adapterInstanceMock.getMetricResourceStatus.return_value)

    for metricObj in resultsOfGetCloudwatchMetricsPendingDataCollection[2]:
      repoMock.saveMetricInstanceStatus.assert_any_call(
        mockConnection,
        metricObj.server,
        adapterInstanceMock.getMetricResourceStatus.return_value)


  @patch.object(metric_collector, "createDatasourceAdapter", autospec=True)
  def testRecoveryFromBotoServerError(self, createAdapterMock, repoMock,
                                      metricStreamerMock, multiprocessingMock):
    """
    This test verifies recovery  and continuation for normal
    operation for metric collector after encoutering BotoServerError
    for getData call
    """
    exception = BotoServerError(500, "Fake BotoServerError")

    # Configure multiprocessing
    def mapAsync(fn, tasks):
      class _(object):
        def wait(self):
          map(fn, tasks)
      return _()

    multiprocessingMock.Pool.return_value.map_async.side_effect = mapAsync
    multiprocessingMock.Pipe.side_effect = multiprocessing.Pipe
    multiprocessingMock.Manager = (
      Mock(return_value=(
        Mock(JoinableQueue=(
          Mock(side_effect=multiprocessing.JoinableQueue))))))

    metricPollInterval = 5

    resultsOfGetCloudwatchMetricsPendingDataCollection = [
      [_makeFreshMetricMockInstance(metricPollInterval, 1)],
      [_makeFreshMetricMockInstance(metricPollInterval, 2)],
      [_makeFreshMetricMockInstance(metricPollInterval, 3)],
      KeyboardInterrupt("Fake KeyboardInterrupt to interrupt run-loop")
    ]

    repoMock.getCloudwatchMetricsPendingDataCollection.side_effect = (
      resultsOfGetCloudwatchMetricsPendingDataCollection)
    repoMock.retryOnTransientErrors.side_effect = lambda f: f

    # Configure the metric_collector.adapters module mock
    now = datetime.datetime.utcnow()
    mockResults = [exception,
                   ([[now, 1]],
                    now + datetime.timedelta(seconds=metricPollInterval)),
                   ([[now, 2]],
                    now + datetime.timedelta(seconds=metricPollInterval))]

    adapterInstanceMock = Mock(
      spec_set=_CloudwatchDatasourceAdapter)
    adapterInstanceMock.getMetricData.side_effect = mockResults
    adapterInstanceMock.getMetricResourceStatus.return_value = "status"

    createAdapterMock.return_value = adapterInstanceMock

    # Now, run MetricCollector and check results
    resultOfRunCollector = dict()
    def runCollector():
      try:
        collector = metric_collector.MetricCollector()
        resultOfRunCollector["returnCode"] = collector.run()
      except:
        resultOfRunCollector["exception"] = sys.exc_info()[1]

    # We run it in a thread in order to detect if MetricCollector.run fails to
    # return and to make sure that the test script will finish (in case run
    # doesn't)
    thread = threading.Thread(target=runCollector)
    thread.setDaemon(True)
    thread.start()

    thread.join(5)
    self.assertFalse(thread.isAlive())

    self.assertIn("exception", resultOfRunCollector)
    self.assertIsInstance(resultOfRunCollector["exception"], KeyboardInterrupt)
    self.assertNotIn("returnCode", resultOfRunCollector)

    # Verify that metric collector didn't call setStatus on the first metric
    # as the result of ClosedConnection
    self.assertFalse(repoMock.setMetricStatus.called)

    self.assertEqual(
      metricStreamerMock.return_value.streamMetricData.call_count,
      len(mockResults) -1)


  @patch.object(metric_collector, "createDatasourceAdapter", autospec=True)
  def testNoDataFromGetData(self, createAdapterMock, repoMock,
                            metricStreamerMock, multiprocessingMock):
    """
    This test verifies recovery  and continuation for normal operation for
    metric collector when data-adapter getData returns empty sequence
    """

    # Configure multiprocessing
    def mapAsync(fn, tasks):
      class _(object):
        def wait(self):
          map(fn, tasks)
      return _()

    multiprocessingMock.Pool.return_value.map_async.side_effect = mapAsync
    multiprocessingMock.Pipe.side_effect = multiprocessing.Pipe
    multiprocessingMock.Manager = (
      Mock(return_value=(
        Mock(JoinableQueue=(
          Mock(side_effect=multiprocessing.JoinableQueue))))))

    metricPollInterval = 5

    resultsOfGetCloudwatchMetricsPendingDataCollection = [
      [],
      [_makeFreshMetricMockInstance(metricPollInterval, 1)],
      [_makeFreshMetricMockInstance(metricPollInterval, 2),
       _makeFreshMetricMockInstance(metricPollInterval, 3)],
      KeyboardInterrupt("Fake KeyboardInterrupt to interrupt run-loop")
    ]

    repoMock.getCloudwatchMetricsPendingDataCollection.side_effect = (
      resultsOfGetCloudwatchMetricsPendingDataCollection)
    repoMock.retryOnTransientErrors.side_effect = lambda f: f

    # Set getMetricData to return None
    now = datetime.datetime.now()
    mockResults = [([], now),
                   ([], now),
                   ([], now),
                   ([], now)]

    adapterInstanceMock = Mock(
      spec_set=_CloudwatchDatasourceAdapter)
    adapterInstanceMock.getMetricData.side_effect = mockResults
    adapterInstanceMock.getMetricResourceStatus.return_value = "status"

    createAdapterMock.return_value = adapterInstanceMock

    # Now, run MetricCollector and check results
    resultOfRunCollector = dict()
    def runCollector():
      try:
        collector = metric_collector.MetricCollector()
        resultOfRunCollector["returnCode"] = collector.run()
      except:
        resultOfRunCollector["exception"] = sys.exc_info()[1]
        raise

    # We run it in a thread in order to detect if MetricCollector.run fails to
    # return and to make sure that the test script will finish (in case run
    # doesn't)
    thread = threading.Thread(target=runCollector)
    thread.setDaemon(True)
    thread.start()

    thread.join(5)
    self.assertFalse(thread.isAlive())
    self.assertIn("exception", resultOfRunCollector)
    self.assertIsInstance(resultOfRunCollector["exception"], KeyboardInterrupt)
    self.assertNotIn("returnCode", resultOfRunCollector)

    self.assertEqual((metricStreamerMock.return_value
                                        .streamMetricData
                                        .call_count), 0)
    self.assertEqual(
      repoMock.getCloudwatchMetricsPendingDataCollection.call_count,
      len(resultsOfGetCloudwatchMetricsPendingDataCollection))

  @patch("sqlalchemy.engine.Engine", autospec=True)
  def testProcessCollectedDataWithEmptyNewData(self, engineMock, *_mocks):
    # Test MetricCollector._processCollectedData with collection result
    # containing empty data set
    metricID = 1
    mockMetric = _makeFreshMetricMockInstance(metricPollInterval=5,
                                              uid=metricID)

    dataCollectionResult = metric_collector._DataCollectionResult(
      metricID=metricID)
    dataCollectionResult.data = []

    metricsToUpdate = OrderedDict()
    metricsToUpdate[mockMetric.uid] = mockMetric

    collector = metric_collector.MetricCollector()
    numEmpty, numErrors = collector._processCollectedData(
      engineMock,
      metricsToUpdate=metricsToUpdate,
      collectResult=dataCollectionResult,
      modelSwapper=Mock())

    self.assertEqual(numEmpty, 1)
    self.assertEqual(numErrors, 0)


  @patch("sqlalchemy.engine.Engine", autospec=True)
  def testProcessCollectedDataWithGetDataError(self, engineMock, *_mocks):
    # Test MetricCollector._processCollectedData with collection result
    # containing getData error
    metricID = 1

    mockMetric = _makeFreshMetricMockInstance(metricPollInterval=5,
                                              uid=metricID)

    dataCollectionResult = metric_collector._DataCollectionResult(
      metricID=metricID)
    dataCollectionResult.data = BotoServerError(
      500, "Fake getData BotoServerError")

    metricsToUpdate = OrderedDict()
    metricsToUpdate[mockMetric.uid] = mockMetric

    collector = metric_collector.MetricCollector()
    numEmpty, numErrors = collector._processCollectedData(
      engineMock,
      metricsToUpdate=metricsToUpdate,
      collectResult=dataCollectionResult,
      modelSwapper=Mock())

    self.assertEqual(numEmpty, 0)
    self.assertEqual(numErrors, 1)


  @patch("sqlalchemy.engine.Engine", autospec=True)
  def testProcessCollectedDataWithGetInstanceStatusError(self, engineMock,
                                                         *_mocks):
    # Test MetricCollector._processCollectedData with collection result
    # containing getInstanceStatus error
    metricID = 1

    mockMetric = _makeFreshMetricMockInstance(metricPollInterval=5,
                                              uid=metricID)

    dataCollectionResult = metric_collector._DataCollectionResult(
      metricID=metricID)
    dataCollectionResult.data = []
    dataCollectionResult.resourceStatus = BotoServerError(
      500, "Fake getInstanceStatus BotoServerError")

    metricsToUpdate = OrderedDict()
    metricsToUpdate[mockMetric.uid] = mockMetric

    collector = metric_collector.MetricCollector()
    numEmpty, numErrors = collector._processCollectedData(
      engineMock,
      metricsToUpdate=metricsToUpdate,
      collectResult=dataCollectionResult,
      modelSwapper=Mock())

    self.assertEqual(numEmpty, 1)
    self.assertEqual(numErrors, 1)


  @patch("sqlalchemy.engine.Engine", autospec=True)
  def testProcessCollectedDataWithClearingOfCollectorError(self, engineMock,
                                                           repoMock, *_mocks):
    # Test MetricCollector._processCollectedData with clearing of collector
    # error state
    metricID = 1

    mockMetric = _makeFreshMetricMockInstance(metricPollInterval=5,
                                              uid=metricID)
    mockMetric.collector_error = dict(deadline=time.time(), message="Blah")

    dataCollectionResult = metric_collector._DataCollectionResult(
      metricID=metricID)
    dataCollectionResult.data = []

    metricsToUpdate = OrderedDict()
    metricsToUpdate[mockMetric.uid] = mockMetric

    collector = metric_collector.MetricCollector()
    numEmpty, numErrors = collector._processCollectedData(
      engineMock,
      metricsToUpdate=metricsToUpdate,
      collectResult=dataCollectionResult,
      modelSwapper=Mock())

    self.assertEqual(numEmpty, 1)
    self.assertEqual(numErrors, 0)
    repoMock.retryOnTransientErrors('repository.setMetricCollectorError')\
      .assert_called_once_with(
        engineMock.connect.return_value.__enter__.return_value,
        metricID,
        None)



if __name__ == "__main__":
  unittest.main()
