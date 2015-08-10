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
Unit tests for Metrics API
"""
import json
import os

import unittest
from mock import Mock, patch
from paste.fixture import TestApp

import YOMP.app
from YOMP.app.webservices import metrics_api, handlers
from YOMP.app.adapters.datasource.cloudwatch import _CloudwatchDatasourceAdapter
from htmengine import utils as app_utils
from YOMP.test_utils.app.webservices import (
  webservices_assertions as assertions,
  getDefaultHTTPHeaders
)




class TesMetetricsHandler(unittest.TestCase):
  """
  Unit tests for MetricsHandler
  """


  @classmethod
  def setUpClass(cls):
    cls.metrics = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/cw_metric.json")))


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(metrics_api.app.wsgifunc())


  @patch.object(handlers, "web", spec_set=handlers.web)
  @patch("YOMP.app.webservices.metrics_api.listDatasourceNames", autospec=True)
  def testGetDatasourcesWithReturnValue(self, listDatasourceNamesMock, web):
    """
    Test getDatasources
    """
    def get(key, default):
      headers = dict([
          ("HTTP_" + header.upper(), value)
            for (header, value)
              in self.headers.items()])
      return headers.get(key, default)

    web.ctx.env.get.side_effect = get

    metricsHandler = metrics_api.MetricsHandler()
    listDatasourceNamesMock.return_value = ("autostack",
                                            "cloudwatch",
                                            "custom")
    result = metricsHandler.getDatasources()
    self.assertIsInstance(result, tuple)
    self.assertEqual(result, ("autostack", "cloudwatch", "custom"))


  @patch.object(handlers, "web", spec_set=handlers.web)
  @patch("YOMP.app.webservices.metrics_api.listDatasourceNames", autospec=True)
  def testGetDatasourcesWithReturnEmpty(self, listDatasourceNamesMock, web):
    """
    Test getDatasources
    """
    def get(key, default):
      headers = dict([
          ("HTTP_" + header.upper(), value)
            for (header, value)
              in self.headers.items()])
      return headers.get(key, default)

    web.ctx.env.get.side_effect = get

    metricsHandler = metrics_api.MetricsHandler()
    listDatasourceNamesMock.return_value = tuple()
    result = metricsHandler.getDatasources()
    self.assertIsInstance(result, tuple)
    self.assertEqual(result, tuple())
    self.assertIsNotNone(result)


  @patch("YOMP.app.webservices.metrics_api.MetricsHandler.getDatasources")
  def testGetMetricsWithEmptyResponse(self, getDatasourcesMock):
    """
    Test get "/datasources"
    response is validated for appropriate headers, body and status
    """
    getDatasourcesMock.return_value = tuple()
    response = self.app.get("/datasources", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, [])


  @patch("YOMP.app.webservices.metrics_api.MetricsHandler.getDatasources")
  def testGetMetricsWithNonEmptyResponse(self, getDatasourcesMock):
    """
    Test get "/datasources", with non empty response
    response is validated for appropriate headers, body and status
    """
    getDatasourcesMock.return_value = ("autostack",
                                       "cloudwatch",
                                       "custom")
    response = self.app.get("/datasources", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, ["autostack", "cloudwatch", "custom"])


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetCloudwatch(self, adapterMock):
    """
    Test get "/cloudwatch", with non empty response
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeSupportedMetrics = Mock(
      spec_set=_CloudwatchDatasourceAdapter.describeSupportedMetrics,
      return_value = {})
    adapterMock.return_value.describeRegions = Mock(
      spec_set=_CloudwatchDatasourceAdapter.describeRegions,
      return_value = [])

    response = self.app.get("/cloudwatch", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, {'regions': {}, 'namespaces': {}})



if __name__ == "__main__":
  unittest.main()
