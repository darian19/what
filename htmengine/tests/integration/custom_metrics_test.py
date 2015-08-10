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

"""Integration test for custom metrics."""

import calendar
import datetime
import json
import logging
import os
import socket
import time
import unittest

from htmengine import repository
from htmengine.exceptions import MetricStatisticsNotReadyError
from htmengine.repository.queries import MetricStatus
from htmengine.runtime.scalar_metric_utils import (
  MODEL_CREATION_RECORD_THRESHOLD)
from htmengine.test_utils.test_case_base import TestCaseBase
from htmengine.adapters.datasource import createDatasourceAdapter

from nta.utils.config import Config



LOGGER = logging.getLogger(__name__)


g_config = Config("application.conf",
                  os.environ.get("APPLICATION_CONFIG_PATH"))


class CustomMetricsTest(TestCaseBase):
  """Integration tests for htmengine custom metrics."""


  @classmethod
  def setUpClass(cls):
    cls.engine = repository.engineFactory(g_config)


  def setUp(self):
    self.config = g_config
    self.plaintextPort = self.config.getint("metric_listener",
                                            "plaintext_port")


  def testUnevenTimestamps(self):
    """ Tests that a custom metric with uneven timestamps is still properly
    fed into htmengine and no data goes missing.
    """
    metricName = "testUnevenTimestamps.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    thirdTimeStamp = int(time.time()) - 300
    secondTimeStamp = thirdTimeStamp - 300
    firstTimeStamp = secondTimeStamp - 299

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 %d\n" % (metricName, firstTimeStamp))
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Create a model for the custom metric
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 5.0}}

    result = self._createModel(nativeMetric)

    ts1 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(firstTimeStamp))
    self.checkModelResults(uid, [[ts1, 5.0, 0.0, 1]])

    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 %d\n" % (metricName, secondTimeStamp))
    sock.sendall("%s 5.0 %d\n" % (metricName, thirdTimeStamp))
    self.gracefullyCloseSocket(sock)

    ts3 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(thirdTimeStamp))
    ts2 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(secondTimeStamp))

    self.checkModelResults(uid, [[ts3, 5.0, 0.0, 3],
                                 [ts2, 5.0, 0.0, 2],
                                 [ts1, 5.0, 0.0, 1]])


  def testCreateDelete(self):
    """Tests sending metric data over same TCP connection.

    This tests creating the metric and model and validating results.
    """
    metricName = "testCreateDelete.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self._deleteModel(uid)

    self.checkMetricUnmonitoredById(uid)
    self.checkModelResultsDeleted(uid)

    self._deleteMetric(metricName)

    self.checkMetricDeleted(metricName)


  def testCreateDelete2(self):
    """Tests creating a metric that was previously created and deleted."""
    metricName = "testCreateDelete.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid,
                                   "unit": "Percent"},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self._deleteMetric(metricName)

    self.checkMetricDeleted(metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 6.0 1386201900\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self._deleteMetric(metricName)

    self.checkMetricDeleted(metricName)


  def testStats(self):
    """Tests that stats are computed correctly."""
    metricName = "testStats.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    sock.sendall("%s 6.0 1386288000\n" % metricName)
    sock.sendall("%s 7.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    time.sleep(5)
    for _attempt in xrange(6):
      try:
        uid = self.checkMetricCreated(metricName, numRecords=3)
        LOGGER.info("Metric %s has uid: %s", metricName, uid)
        break
      except:
        time.sleep(10)
    else:
      self.fail("Metric not created within a reasonable amount of time.")

    # Check that stats are computed correctly from the database
    for _attempt in xrange(6):
      try:
        with repository.engineFactory(self.config).connect() as conn:
          stats = repository.getMetricStats(conn, uid)
        self.assertSetEqual(set(stats.keys()), set(("min", "max")))
        self.assertAlmostEqual(stats["min"], 5.0)
        self.assertAlmostEqual(stats["max"], 7.0)
        break
      except MetricStatisticsNotReadyError:
        time.sleep(10)
    else:
      self.fail("Metric created, but statistics not ready within a reasonable"
                " amount of time.")


  def testMinMax(self):
    """Tests that the min and max are set correctly when not specified."""
    metricName = "testMinMax.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    ts = 1386201600
    sock.sendall("%s 5000.0 %i\n" % (metricName, ts))
    for _i in xrange(MODEL_CREATION_RECORD_THRESHOLD - 1):
      ts += 300
      sock.sendall("%s 7000.0 %i\n" % (metricName, ts))
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(
        metricName, numRecords=MODEL_CREATION_RECORD_THRESHOLD)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.status, MetricStatus.CREATE_PENDING)

    # Check the min and max for the model
    self.checkEncoderResolution(uid, 0.0, 7000.0)


  def test_MinMaxDelayedCreation(self):
    """Tests that the min and max are set correctly when not specified."""

    metricName = "testMinMaxDelayedCreation.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    def timeGenerator():
      """Generator for unix timestamps."""
      dt = datetime.datetime.utcnow() - datetime.timedelta(hours=25)
      td = datetime.timedelta(minutes=5)
      while True:
        dt += td
        yield int(calendar.timegm(dt.utctimetuple()))
    nextTime = timeGenerator()

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 0.0 %i\n" % (metricName, nextTime.next()))
    sock.sendall("%s 100.0 %i\n" % (metricName, nextTime.next()))
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid}}
    model = self._createModel(nativeMetric)
    self.assertEqual(model.status, MetricStatus.PENDING_DATA)

    # Add more data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for _ in xrange(MODEL_CREATION_RECORD_THRESHOLD - 2):
      sock.sendall("%s 7000.0 %i\n" % (metricName, nextTime.next()))
    self.gracefullyCloseSocket(sock)

    for _ in xrange(60):
      with self.engine.begin() as conn:
        metric = repository.getMetric(conn, uid)

      if metric.status == MetricStatus.ACTIVE:
        break
      LOGGER.info("Model=%s not ready.  Sleeping 5 seconds...")
      time.sleep(5)
    else:
      self.fail("Model results not available within 5 minutes")

    # Check the min and max for the model
    self.checkEncoderResolution(uid, 0.0, 7000.0)

    # Check that the data all got processed
    self.checkModelResultsSize(uid, MODEL_CREATION_RECORD_THRESHOLD)


  def test_MinMaxDelayedCreationNoMetricIntegrityErrorMER2190(self):
    """Tests that delayed creation doesn't cause integrity error in
    custom-metric model. It sends more than MODEL_CREATION_RECORD_THRESHOLD
    rows """
    metricName = ("testMinMaxDelayedCreationNoMetricIntegrityErrorMER2190.%i"
                  % int(time.time()))
    LOGGER.info("Running test with metric name: %s", metricName)

    totalRowsToSend = MODEL_CREATION_RECORD_THRESHOLD + 700

    self.addCleanup(self._deleteMetric, metricName)

    def timeGenerator():
      """Generator for unix timestamps."""
      backoff = datetime.timedelta(minutes=5 * (totalRowsToSend + 1))
      dt = datetime.datetime.utcnow() - backoff
      td = datetime.timedelta(minutes=5)
      while True:
        dt += td
        yield int(calendar.timegm(dt.utctimetuple()))
    nextTime = timeGenerator()

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 0.0 %i\n" % (metricName, nextTime.next()))
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid}}

    model = self._createModel(nativeMetric)
    self.assertEqual(model.status, MetricStatus.PENDING_DATA)

    # Add more data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for _ in xrange(totalRowsToSend - 1):
      sock.sendall("%s 7000.0 %i\n" % (metricName, nextTime.next()))
    self.gracefullyCloseSocket(sock)

    for _ in xrange(60):
      with self.engine.begin() as conn:
        metric = repository.getMetric(conn, uid)

      if metric.status == MetricStatus.ACTIVE:
        break
      LOGGER.info("Model=%s not ready.  Sleeping 5 seconds...")
      time.sleep(5)
    else:
      self.fail("Model results not available within 5 minutes")

    # Check that the data all got processed
    self.checkModelResultsSize(uid, totalRowsToSend)


  def test_MinMaxExplicitMin(self):
    """Tests that max is required if min is specified."""
    metricName = "testMinMaxExplicitMin.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5000.0 1386201600\n" % metricName)
    sock.sendall("%s 6000.0 1386288000\n" % metricName)
    sock.sendall("%s 7000.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 5000.0}}

    with self.assertRaises(ValueError) as err:
      self._createModel(nativeMetric)

    self.assertIn("min and max params must both be None or non-None",
                  str(err.exception))

    self.checkMetricUnmonitoredById(uid)


  def test_MinMaxExplicit(self):
    """Tests that min and max are correctly set for explicit min and max."""
    metricName = "testMinMaxExplicit.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5000.0 1386201600\n" % metricName)
    sock.sendall("%s 6000.0 1386288000\n" % metricName)
    sock.sendall("%s 7000.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 5000.0,
                                    "max": 10000.0}}

    self._createModel(nativeMetric)

    # Check the min and max for the model
    self.checkEncoderResolution(uid, 5000.0, 10000.0)


  def testMonitorWithResource(self):
    """Tests that the resource can be set."""
    metricName = "testMonitorWithResource.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)
    resourceName = "Test Resource"

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5000.0 1386201600\n" % metricName)
    sock.sendall("%s 6000.0 1386288000\n" % metricName)
    sock.sendall("%s 7000.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid,
                                   "resource": resourceName},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}
    model = self._createModel(nativeMetric)
    parameters = json.loads(model.parameters)

    self.assertEqual(parameters["metricSpec"]["resource"], resourceName)
    self.assertEqual(model.server, resourceName)


  def testMonitorWithUserInfo(self):
    """Tests that userInfo can be set."""
    metricName = "testMonitorWithUserInfo.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)
    userInfo = {
      "symbol": "test-user-info"
    }

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5000.0 1386201600\n" % metricName)
    sock.sendall("%s 6000.0 1386288000\n" % metricName)
    sock.sendall("%s 7000.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid,
                                   "userInfo": userInfo},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}
    model = self._createModel(nativeMetric)
    parameters = json.loads(model.parameters)
    self.assertEqual(parameters["metricSpec"]["userInfo"], userInfo)


  def testBatchSend(self):
    """Tests sending metric data over same TCP connection.

    This tests creating the metric and model and validating results.
    """
    metricName = "testBatchSend.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    sock.sendall("%s 6.0 1386288000\n" % metricName)
    sock.sendall("%s 7.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName, numRecords=3)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self.checkModelResults(uid, [["2013-12-07 00:00:00", 7.0, 0.0, 3],
                                 ["2013-12-06 00:00:00", 6.0, 0.0, 2],
                                 ["2013-12-05 00:00:00", 5.0, 0.0, 1]])
    LOGGER.info("Model results confirmed")


  def testOneByOneSend(self):
    """Tests sending records over separate, non-overlapping TCP connections."""
    metricName = "testOneByOneSend.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 6.0 1386288000\n" % metricName)
    self.gracefullyCloseSocket(sock)
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 7.0 1386374400\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 7.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self.checkModelResults(uid, [["2013-12-07 00:00:00", 7.0, 0.0, 3],
                                 ["2013-12-06 00:00:00", 6.0, 0.0, 2],
                                 ["2013-12-05 00:00:00", 5.0, 0.0, 1]])


  def testFloatTimestamps(self):
    """Tests sending metric data with floating point timestamps."""
    metricName = "testBatchSend.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 1386201600.0\n" % metricName)
    sock.sendall("%s 6.0 1386288000.021\n" % metricName)
    sock.sendall("%s 7.0 1386374400.0\n" % metricName)
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName, numRecords=3)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self.checkModelResults(uid, [["2013-12-07 00:00:00", 7.0, 0.0, 3],
                                 ["2013-12-06 00:00:00", 6.0, 0.0, 2],
                                 ["2013-12-05 00:00:00", 5.0, 0.0, 1]])


  def testSimultaneousConnections(self):
    """Tests sending multiple metrics over concurrent connections."""
    runIdentifier = int(time.time())
    metricName1 = "testSimultaneousConnections1.%i" % runIdentifier
    metricName2 = "testSimultaneousConnections2.%i" % runIdentifier
    LOGGER.info("Running test with metric name 1: %s", metricName1)
    LOGGER.info("Running test with metric name 2: %s", metricName2)

    self.addCleanup(self._deleteMetric, metricName1)
    self.addCleanup(self._deleteMetric, metricName2)

    # Add custom metric data
    # Connect and send from first connection
    sock1 = socket.socket()
    self.addCleanup(self.gracefullyCloseSocket, sock1)
    sock1.connect(("localhost", self.plaintextPort))
    sock1.sendall("%s 5.0 1386201600\n" % metricName1)
    # Connect and send from second connection
    sock2 = socket.socket()
    self.addCleanup(self.gracefullyCloseSocket, sock2)
    sock2.connect(("localhost", self.plaintextPort))
    sock2.sendall("%s 9.0 1386374400\n" % metricName2)
    # Send again from first connection
    sock1.sendall("%s 6.0 1386288000\n" % metricName1)
    # Make sure the socket connections are fully flushed and closed
    self.gracefullyCloseSocket(sock1)
    self.gracefullyCloseSocket(sock2)

    # Check the metrics are created
    uid1 = self.checkMetricCreated(metricName1)
    uid2 = self.checkMetricCreated(metricName2)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName1, uid1)
    LOGGER.info("Metric %s has uid: %s", metricName2, uid2)

    # Send model creation requests
    nativeMetric1 = {"datasource": "custom",
                    "metricSpec": {"uid": uid1},
                     "modelParams": {"min": 0.0,
                                     "max": 6.0}}

    model1 = self._createModel(nativeMetric1)

    nativeMetric2 = {"datasource": "custom",
                     "metricSpec": {"uid": uid2},
                     "modelParams": {"min": 0.0,
                                     "max": 9.0}}
    model2 = self._createModel(nativeMetric2)

    # Validate first metric
    self.assertEqual(model1.uid, uid1)
    self.assertEqual(model1.name, metricName1)
    self.assertEqual(model1.server, metricName1)

    # Validate second metric
    self.assertEqual(model2.uid, uid2)
    self.assertEqual(model2.name, metricName2)
    self.assertEqual(model2.server, metricName2)

    self.checkModelResults(uid1, [["2013-12-06 00:00:00", 6.0, 0.0, 2],
                                  ["2013-12-05 00:00:00", 5.0, 0.0, 1]])

    self.checkModelResults(uid2, [["2013-12-07 00:00:00", 9.0, 0.0, 1]])


  def testInvalidData(self):
    """Tests sending invalid metric data.

    This test doesn't create a model or check model results. Instead, it sends
    several invalid records and then a valid record and checks that a model is
    created before cleaning up.
    """
    metricName = "testInvalidData.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("invalid1\n")
    sock.sendall("invalid2\n")
    sock.sendall("invalid3\n")
    sock.sendall("invalid4\n")
    sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    # Check that the metric is created from the record sent after the invalid
    # data
    self.checkMetricCreated(metricName)


  def testExport(self):
    """Tests exporting custom metrics."""
    metricName = "testBatchSend.%i" % int(time.time())
    LOGGER.info("Running test with metric name: %s", metricName)

    self.addCleanup(self._deleteMetric, metricName)

    # Get the timestamp for 14 days ago (the limit for exporting data)
    baseTimestamp = int(time.time()) - (60 * 60 * 24 * 14)
    ts1 = baseTimestamp - (60 * 5)
    dt1 = datetime.datetime.utcfromtimestamp(ts1).strftime("%Y-%m-%d %H:%M:%S")
    ts2 = baseTimestamp + (60 * 5)
    dt2 = datetime.datetime.utcfromtimestamp(ts2).strftime("%Y-%m-%d %H:%M:%S")
    ts3 = baseTimestamp + (60 * 10)
    dt3 = datetime.datetime.utcfromtimestamp(ts3).strftime("%Y-%m-%d %H:%M:%S")

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("%s 5.0 %i\n" % (metricName, ts1))
    sock.sendall("%s 6.0 %i\n" % (metricName, ts2))
    sock.sendall("%s 7.0 %i\n" % (metricName, ts3))
    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    nativeMetric = {"datasource": "custom",
                    "metricSpec": {"uid": uid},
                    "modelParams": {"min": 0.0,
                                    "max": 100.0}}

    model = self._createModel(nativeMetric)

    self.assertEqual(model.uid, uid)
    self.assertEqual(model.name, metricName)
    self.assertEqual(model.server, metricName)

    self.checkModelResults(uid, [[dt3, 7.0, 0.0, 3], [dt2, 6.0, 0.0, 2],
                                 [dt1, 5.0, 0.0, 1]])

    exported = createDatasourceAdapter("custom").exportModel(uid)

    self.assertEqual(exported["metricSpec"]["metric"], metricName)
    self.assertEqual(exported["datasource"], "custom")
    self.assertEqual(len(exported["data"]), 2)
    self.assertSequenceEqual(exported["data"][0],
                             [6.0, datetime.datetime.utcfromtimestamp(ts2)])
    self.assertSequenceEqual(exported["data"][1],
                             [7.0, datetime.datetime.utcfromtimestamp(ts3)])



def setUpModule():
  logging.basicConfig(level=logging.DEBUG)



if __name__ == "__main__":
  unittest.main()
