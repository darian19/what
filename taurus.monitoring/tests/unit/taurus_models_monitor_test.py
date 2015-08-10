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
Unittest of taurus/monitoring/models_monitor/taurus_models_monitor.py
"""
import unittest

from mock import patch, Mock
import requests

from htmengine.repository.queries import MetricStatus

import taurus.monitoring.models_monitor.taurus_models_monitor as modelsMonitor



class TaurusModelsMonitorTest(unittest.TestCase):


  def testGetIssueString(self):
    n = "name"
    msg = "watsup"
    res = modelsMonitor._getIssueString(n, msg)
    self.assertTrue(n in res)
    self.assertTrue(msg in res)


  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor._reportIssue")
  @patch("requests.get")
  def testConnectAndCheckModelsRequestsException(self,
                                                 getMock,
                                                 reportIssueMock,
                                                 removeIssueMock):
    """
    Tests encountering a RequestException.
    """
    url = "url"
    apiKey = "key"
    timeout = 1.0

    excMessage = "Mock RequestException"
    getMock.side_effect = requests.exceptions.RequestException(excMessage)

    # Code under test
    modelsMonitor._connectAndCheckModels(url, apiKey, timeout, {})

    getMock.assert_called_once_with(url, auth=(apiKey, ""), timeout=timeout,
                                    verify=False)
    self.assertFalse(removeIssueMock.called)
    self.assertTrue(reportIssueMock.called)


  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor._reportIssue")
  @patch("requests.get")
  def testConnectAndCheckModelsResponseCode(self,
                                            getMock,
                                            reportIssueMock,
                                            removeIssueMock):
    """
    Test a request Response whose status code is not 200
    """
    url = "url"
    apiKey = "key"
    timeout = 1.0

    # Mock the returned value of requests.get, a requests.Response
    responseMock = Mock(spec=requests.models.Response)
    responseMock.status_code = 404
    getMock.return_value = responseMock
    emailParams = {"key":"val"}

    # Code under test
    modelsMonitor._connectAndCheckModels(url, apiKey, timeout, emailParams)

    getMock.assert_called_once_with(url, auth=(apiKey, ""), timeout=timeout,
                                    verify=False)
    removeIssueMock.assert_called_once_with(
      modelsMonitor._FLAG_REQUESTS_EXCEPTION)
    reportIssueMock.assert_called_once_with(
      modelsMonitor._FLAG_HTTP_STATUS_CODE,
      url,
      modelsMonitor._getIssueString("Received abnormal HTTP status code", 404),
      {"key":"val"}
    )


  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor._reportIssue")
  @patch("requests.get")
  def testConnectAndCheckModelsValueError(self,
                                          getMock,
                                          reportIssueMock,
                                          removeIssueMock):
    """
    Tests a requests Response whose status code is 200, but whose
    json method raises a ValueError.
    """
    url = "url"
    apiKey = "key"
    timeout = 1.0

    responseMock = Mock(spec=requests.models.Response)
    responseMock.status_code = 200
    responseMock.json.side_effect = ValueError()
    getMock.return_value = responseMock

    # Code under test
    modelsMonitor._connectAndCheckModels(url, apiKey, timeout, {"k":"v"})

    getMock.assert_called_once_with(url, auth=(apiKey, ""), timeout=timeout,
                                    verify=False)
    removeIssueMock.assert_any_call(modelsMonitor._FLAG_REQUESTS_EXCEPTION)
    removeIssueMock.assert_any_call(modelsMonitor._FLAG_HTTP_STATUS_CODE)
    reportIssueMock.assert_called_once_with(modelsMonitor._FLAG_RESPONSE_JSON,
                                            url,
                                            "ValueError encountered loading "
                                            "JSON.",
                                            {"k":"v"})


  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_checkModelsStatus")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("requests.get")
  def testConnectAndCheckModelsSuccess(self,
                                       getMock,
                                       removeIssueMock,
                                       checkModelsStatusMock):
    """
    Tests case where no connection errors occur.
    """
    url = "url"
    apiKey = "key"
    timeout = 1.0

    responseMock = Mock(spec=requests.models.Response)
    responseMock.status_code = 200
    responseMock.json.return_value = "{}"
    getMock.return_value = responseMock
    emailParams = {"key": "value"}

    # Code under test
    modelsMonitor._connectAndCheckModels(url, apiKey, timeout, emailParams)

    getMock.assert_called_once_with(url, auth=(apiKey, ""), timeout=timeout,
                                    verify=False)
    removeIssueMock.assert_any_call(modelsMonitor._FLAG_REQUESTS_EXCEPTION)
    removeIssueMock.assert_any_call(modelsMonitor._FLAG_HTTP_STATUS_CODE)
    removeIssueMock.assert_any_call(modelsMonitor._FLAG_RESPONSE_JSON)
    checkModelsStatusMock.assert_called_once_with("{}", url, {"key": "value"})


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_addIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_containsIssueFlag")
  def testCheckModelsStatusNoModels(self,
                                    containsIssueMock,
                                    addIssueMock,
                                    removeIssueMock,
                                    sendEmailMock):
    url = "foo.bar"
    testJson = []
    emailParams = {}

    # Code under test
    modelsMonitor._checkModelsStatus(testJson, url, emailParams)

    self.assertFalse(containsIssueMock.called)
    self.assertFalse(addIssueMock.called)
    self.assertFalse(removeIssueMock.called)
    self.assertFalse(sendEmailMock.called)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_addIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_containsIssueFlag")
  def testCheckModelsStatusGoodModels(self,
                                      containsIssueMock,
                                      addIssueMock,
                                      removeIssueMock,
                                      sendEmailMock):
    url = "foo.bar"
    testJson = [{u"uid": "123", u"status": MetricStatus.ACTIVE},
                {u"uid": "456", u"status": MetricStatus.ACTIVE}]
    emailParams = {}

    # Code under test
    modelsMonitor._checkModelsStatus(testJson, url, emailParams)

    removeIssueMock.assert_any_call("123")
    removeIssueMock.assert_any_call("456")

    self.assertFalse(containsIssueMock.called)
    self.assertFalse(addIssueMock.called)
    self.assertFalse(sendEmailMock.called)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_addIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_containsIssueFlag")
  def testCheckModelsStatusErrorModels_AlreadyReported(self,
                                                       containsIssueMock,
                                                       addIssueMock,
                                                       removeIssueMock,
                                                       sendEmailMock):
    url = "foo.bar"
    testJson = [{u"uid": "123", u"status": MetricStatus.ERROR},
                {u"uid": "456", u"status": MetricStatus.ERROR}]
    containsIssueMock.return_value = True
    emailParams = {}

    # Code under test
    modelsMonitor._checkModelsStatus(testJson, url, emailParams)

    containsIssueMock.assert_any_call("123")
    containsIssueMock.assert_any_call("456")

    self.assertFalse(removeIssueMock.called)
    self.assertFalse(addIssueMock.called)
    self.assertFalse(sendEmailMock.called)


  @patch("nta.utils.error_reporting.sendMonitorErrorEmail")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_removeIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_addIssueFlag")
  @patch("taurus.monitoring.models_monitor.taurus_models_monitor."
         "_containsIssueFlag")
  def testCheckModelsStatusErrorModels_NotAlreadyReported(self,
                                                          containsIssueMock,
                                                          addIssueMock,
                                                          removeIssueMock,
                                                          sendEmailMock):
    url = "foo.bar"
    testJson = [{u"uid": "123", u"status": MetricStatus.ERROR},
                {u"uid": "456", u"status": MetricStatus.ERROR}]
    containsIssueMock.return_value = False
    emailParams = {}

    # Code under test
    modelsMonitor._checkModelsStatus(testJson, url, emailParams)

    containsIssueMock.assert_any_call("123")
    containsIssueMock.assert_any_call("456")
    addIssueMock.assert_any_call("123", "123")
    addIssueMock.assert_any_call("456", "456")

    self.assertFalse(removeIssueMock.called)
    self.assertTrue(sendEmailMock.called)



if __name__ == "__main__":
  unittest.main()
