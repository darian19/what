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

import json
import os
import unittest

from mock import patch
from paste.fixture import AppError, TestApp
import web

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

import YOMP.app
from YOMP.app import repository
from htmengine import utils as app_utils
from YOMP.app.exceptions import AuthFailure, AWSPermissionsError
from YOMP.app.webservices import metrics_api, webapp
from YOMP.test_utils.app.webservices import (
  webservices_assertions as assertions,
  getDefaultHTTPHeaders
)



class DefaultHandlerTest(unittest.TestCase):


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(webapp.app.wsgifunc())


  def testDefaultHandlerGET(self):
    response = self.app.get("", headers=self.headers)
    self.assertEqual(response.status, 303)
    self.assertEqual(response.full_status, "303 See Other")
    headers = dict(response.headers)
    self.assertEqual(headers["Content-Type"], "text/html")
    self.assertEqual(headers["Location"], "http://localhost/static/index.html")


  def testDefaultHandlerGETWithSlash(self):
    response = self.app.get("/", headers=self.headers)
    self.assertEqual(response.status, 303)
    self.assertEqual(response.full_status, "303 See Other")
    headers = dict(response.headers)
    self.assertEqual(headers["Content-Type"], "text/html")
    self.assertEqual(headers["Location"], "http://localhost/static/index.html")



@patch("YOMP.app.webservices.webapp.instance_utils.getInstanceData",
       autospec=True, return_value={})
class YOMPHandlerTest(unittest.TestCase):


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(webapp.app.wsgifunc())


  @patch.object(web.template, "render")
  def testYOMPHandlerGET(self, render, _instanceDataMock):
    response = self.app.get("/YOMP", headers=self.headers)
    self.assertTrue(render.called)
    assertions.assertResponseStatusCode(self, response, code=200)
    headers = dict(response.headers)
    self.assertEqual(headers["Content-Type"], "text/html; charset=UTF-8")



@ConfigAttributePatch(
    YOMP.app.config.CONFIG_NAME,
    YOMP.app.config.baseConfigDir,
    (("aws", "aws_access_key_id", ""),
     ("aws", "aws_secret_access_key", ""))
)
class AWSAuthHandlerTest(unittest.TestCase):


  def setUp(self):
    #self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(webapp.app.wsgifunc())


  @patch("YOMP.app.webservices.webapp.checkEC2Authorization")
  def testAuthInvalidCredentials(self, checkEC2AuthorizationMock):
    errorMessage = ("AWS was not able to validate the provided access "
                    "credentials")
    exc = AuthFailure(errorMessage)
    checkEC2AuthorizationMock.side_effect = exc
    requestBody = {
        "aws_access_key_id": "bad_key",
        "aws_secret_access_key": "bad_key",
    }

    with self.assertRaises(AppError) as cm:
      self.app.post("/_auth", json.dumps(requestBody))

    checkEC2AuthorizationMock.assert_called_once_with("bad_key", "bad_key")

    self.assertIn(errorMessage, cm.exception.message)


  @patch("YOMP.app.webservices.webapp.checkEC2Authorization")
  def testAuthCredentialsMissingPermissions(self, checkEC2AuthorizationMock):
    errorMessage = ("IAM credentials don't have correct permissions.")
    exc = AWSPermissionsError(errorMessage)
    checkEC2AuthorizationMock.side_effect = exc
    requestBody = {
        "aws_access_key_id": "good_key",
        "aws_secret_access_key": "good_key",
    }

    with self.assertRaises(AppError) as cm:
      self.app.post("/_auth", json.dumps(requestBody))

    checkEC2AuthorizationMock.assert_called_once_with("good_key", "good_key")

    self.assertIn(errorMessage, cm.exception.message)



class AjaxTest(unittest.TestCase):


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(webapp.app.wsgifunc())


  def testSettingsAPIGET(self):
    response = self.app.get("/_settings", headers=self.headers)
    assertions.assertSuccess(self, response)


  @patch.object(repository, "engineFactory", autospec=True)
  @patch.object(repository, "getInstanceStatusHistory", autospec=True)
  @patch.object(repository, 'getAllModels', autospec=True)
  def testModelsAPIGET(self,
                       getAllMetricsMock,
                       getInstanceStatusHistoryMock,
                       engineFactoryMock, *args):
    #import pdb; pdb.set_trace()
    getAllMetricsMock.return_value = []
    getInstanceStatusHistoryMock.return_value = []
    response = self.app.get("/_models", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, [])
    self.assertTrue(getAllMetricsMock.called)


  @patch.object(metrics_api.MetricsHandler, "getDatasources")
  def testMetricsAPIGETDataSources(self, getDatasources):
    getDatasources.return_value = []
    response = self.app.get("/_metrics/datasources", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, [])
    self.assertTrue(getDatasources.called)


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testMetricsAPIGETCouldWatch(self, adapterMock):
    adapterMock.return_value.describeRegions.return_value = []
    adapterMock.return_value.describeSupportedMetrics.return_value = {}
    response = self.app.get("/_metrics/cloudwatch", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, {'regions': {}, 'namespaces': {}})


class TestMessageHandler(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.web_data = open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/msg_manager.txt")).read()
    cls.message_manager_data = json.load(
        open(os.path.join(
            YOMP.app.YOMP_HOME,
            "tests/py/data/app/webservices/message_manager_data.json")))


  def setUp(self):
    self.app = TestApp(webapp.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  def testPOSTWithExplicit(self):
    response = self.app.post("/_msgs", self.web_data, headers=self.headers)
    assertions.assertSuccess(self, response)
    self.assertEqual(json.loads(response.body), self.message_manager_data)

  #TODO
  def testPOSTWithoutExaplicit(self):
    pass


if __name__ == "__main__":
  unittest.main()
