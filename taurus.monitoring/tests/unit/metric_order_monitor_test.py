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
Unittest of taurus/monitoring/metric_order/metric_order_monitor.py
"""

import json
import os
import unittest

from mock import Mock, patch
import sqlalchemy

from taurus.monitoring.metric_order_monitor import metric_order_monitor as monitor



class MetricOrderMonitorTest(unittest.TestCase):


  def setUp(self):
    monitor._EMAIL_PARAMS = {}
    monitor._MONITORED_RESOURCE = "db"

    if not os.path.isfile(monitor._DB_ERROR_FLAG_FILE):
      with open(monitor._DB_ERROR_FLAG_FILE, "wb") as fp:
        json.dump({}, fp)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("json.dump")
  @patch("json.load")
  def testReportDatabaseIssue_ValueError(self, loadMock, dumpMock,
                                         sendEmailMock):
    issueUID = "123"
    monitoredResource = "db"
    issueMessage = "hi"
    emailParams = {}
    loadMock.side_effect = ValueError("")

    # Function under test
    with self.assertRaises(ValueError):
      monitor._reportDatabaseIssue(issueUID, monitoredResource, issueMessage,
                                   emailParams)

    self.assertTrue(loadMock.called)
    self.assertFalse(dumpMock.called)
    self.assertFalse(sendEmailMock.called)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("json.dump")
  @patch("json.load")
  def testReportDatabaseIssue_AlreadyFlagged(self, loadMock, dumpMock,
                                             sendEmailMock):
    issueUID = "123"
    monitoredResource = "db"
    issueMessage = "hi"
    emailParams = {}
    loadMock.return_value = {"123": "123"}

    # Function under test
    monitor._reportDatabaseIssue(issueUID, monitoredResource, issueMessage,
                                 emailParams)

    self.assertTrue(loadMock.called)
    self.assertTrue(dumpMock.called)
    self.assertFalse(sendEmailMock.called)
    self.assertIn({"123": "123"}, dumpMock.call_args[0])


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("json.dump")
  @patch("json.load")
  def testReportDatabaseIssue_NotFlagged(self, loadMock, dumpMock,
                                         sendEmailMock):
    issueUID = "123"
    monitoredResource = "db"
    issueMessage = "hi"
    emailParams = {}
    loadMock.return_value = {}

    # Function under test
    monitor._reportDatabaseIssue(issueUID, monitoredResource, issueMessage,
                                 emailParams)

    self.assertTrue(loadMock.called)
    self.assertTrue(dumpMock.called)
    self.assertTrue(sendEmailMock.called)
    sendEmailMock.assert_called_once_with(
      monitorName=monitor._MONITOR_NAME,
      resourceName=monitoredResource,
      message=issueMessage,
      params={})
    self.assertIn({"123": "123"}, dumpMock.call_args[0])


  @patch("json.dump")
  @patch("json.load")
  def testClearDatabaseIssue_NotPresent(self, loadMock, dumpMock):
    issueUID = "123"
    loadMock.return_value = {"456": "456"}

    # Test
    monitor._clearDatabaseIssue(issueUID)

    self.assertTrue(loadMock.called)
    self.assertTrue(dumpMock.called)
    self.assertEquals({"456": "456"}, dumpMock.call_args[0][0])


  @patch("json.dump")
  @patch("json.load")
  def testClearDatabaseIssue_Present(self, loadMock, dumpMock):
    issueUID = "456"
    loadMock.return_value = {"123": "123", "456": "456"}

    # Test
    monitor._clearDatabaseIssue(issueUID)

    self.assertTrue(loadMock.called)
    self.assertTrue(dumpMock.called)
    self.assertEquals({"123": "123"}, dumpMock.call_args[0][0])


  def testGetOutOfOrderMetrics(self):
    # Code requiring mocking
    # resultProxy = connection.execute(query)
    # return resultProxy.fetchall()

    resultProxyMock = Mock(spec=sqlalchemy.engine.result.ResultProxy)
    resultProxyMock.fetchall.return_value = ["a", "b", "c"]

    connectionMock = Mock(spec=sqlalchemy.engine.base.Connection)
    connectionMock.execute.return_value = resultProxyMock

    query = "abc"

    # Test method
    result = monitor._getOutOfOrderMetrics(connectionMock, query)

    # Asserts
    connectionMock.execute.assert_called_once_with(query)
    self.assertEquals(["a", "b", "c"], result)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.taurus_monitor_utils.removeErrorFlag")
  @patch("taurus.monitoring.taurus_monitor_utils.addErrorFlag")
  @patch("taurus.monitoring.taurus_monitor_utils.containsErrorFlag")
  def testReportMetrics_NoFailures(self, containsMock, addMock, removeMock,
                                   sendEmailMock):
    monitoredResource = ""
    emailParams = {}
    metrics = []

    # Test
    monitor._reportMetrics(monitoredResource, metrics, emailParams)

    self.assertFalse(containsMock.called)
    self.assertFalse(addMock.called)
    self.assertFalse(sendEmailMock.called)
    self.assertTrue(removeMock.called)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.taurus_monitor_utils.removeErrorFlag")
  @patch("taurus.monitoring.taurus_monitor_utils.addErrorFlag")
  @patch("taurus.monitoring.taurus_monitor_utils.containsErrorFlag")
  def testReportMetrics_HasFailures(self, containsMock, addMock, removeMock,
                                    sendEmailMock):
    monitoredResource = ""
    metrics = ["1", "2", "3"]
    emailParams = {}
    containsMock.return_value = False

    # Test
    monitor._reportMetrics(monitoredResource, metrics, emailParams)

    self.assertTrue(containsMock.called)
    self.assertTrue(addMock.called)
    self.assertTrue(sendEmailMock.called)

    sendEmailMock.assert_called_once_with(
      monitorName=monitor._MONITOR_NAME,
      resourceName=monitoredResource,
      message="The following rows of metric_data table were out of "
              "order:\n1\n2\n3\n",
      params={})

    self.assertFalse(removeMock.called)




if __name__ == "__main__":
  unittest.main()
