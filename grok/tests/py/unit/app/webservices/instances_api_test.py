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

"""Unit tests for Instances API"""

import glob
import json
import os
import unittest

from mock import patch, Mock
from paste.fixture import TestApp

from YOMP.app import config, YOMP_HOME, repository
from htmengine import utils as app_utils
from YOMP.app.adapters import datasource
from YOMP.app.exceptions import QuotaError
from YOMP.app.webservices import instances_api, models_api
from YOMP.test_utils.app.webservices import (
    getDefaultHTTPHeaders, webservices_assertions as assertions)



@patch.object(repository, "engineFactory", autospec=True)
class InstancesHandlerTest(unittest.TestCase):
  """Unit tests for class InstancesHandler from Instances API."""


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(config)


  def _getInstancesHandlerCommon(self, instancesMock, route, expectedResult):
    """
    This method wraps around common testing path for all GET routes which falls
    to listing all available instances
    instancesMock : Mock for Instances class
    route : route under test for current testcase
    expectedResult : expected response from API call
    """
    response = self.app.get(route, headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)
    self.assertEqual(result, expectedResult)
    self.assertTrue(instancesMock.getInstances.called)


  @patch.object(repository, "getInstances", autospec=True)
  def testGetInstancesHandlerEmptyResponse(self, getInstancesMock,
                                           engineFactoryMock):
    """
    Test for Get "/_instances"
    response is validated for appropriate headers, body and status
    """
    getInstancesMock.return_value = []

    response = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)

    self.assertIsInstance(result, list)
    self.assertEqual(result, [])
    self.assertTrue(getInstancesMock.called)
    getInstancesMock.assert_called_with(
      engineFactoryMock.return_value.connect.return_value.__enter__
      .return_value)


  @patch.object(repository, "getInstances", autospec=True)
  def testGetInstancesHandlerNonEmptyResponse(self, getInstancesMock,
                                              engineFactoryMock):
    """
    Test for Get "/_instances"
    response is validated for appropriate headers, body and status
    """
    instancesAPIData = json.load(open(os.path.join(YOMP_HOME,
      "tests/py/data/app/webservices/instances_api.json")))
    getInstancesMock.return_value = instancesAPIData["getInstances"]

    response = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)

    self.assertIsInstance(result, list)
    self.assertEqual(result, instancesAPIData["getInstances"])
    self.assertTrue(getInstancesMock.called)
    getInstancesMock.assert_called_with(
      engineFactoryMock.return_value.connect.return_value.__enter__
      .return_value)



  @patch.object(repository, "getInstances", autospec=True)
  def testGetInstancesHandlerEmptyResponseWithSlash(self, getInstancesMock,
                                                    engineFactoryMock):
    """
    Test for Get "/_instances/"
    response is validated for appropriate headers, body and status
    """
    getInstancesMock.return_value = []

    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)

    self.assertIsInstance(result, list)
    self.assertEqual(result, [])
    self.assertTrue(getInstancesMock.called)
    getInstancesMock.assert_called_with(
      engineFactoryMock.return_value.connect.return_value.__enter__
      .return_value)


  @patch("YOMP.app.webservices.instances_api.repository.getInstances",
         autospec=True)
  def testGetInstancesHandlerNonEmptyResponseWithSlash(self,
                                                       getInstancesMock,
                                                       engineFactoryMock):
    """
    Test for Get "/_instances/"
    response is validated for appropriate headers, body and status
    """
    instancesAPIData = json.load(open(os.path.join(YOMP_HOME,
      "tests/py/data/app/webservices/instances_api.json")))
    getInstancesMock.return_value = instancesAPIData["getInstances"]

    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)

    self.assertIsInstance(result, list)
    self.assertEqual(result, instancesAPIData["getInstances"])
    self.assertTrue(getInstancesMock.called)
    getInstancesMock.assert_called_with(
      engineFactoryMock.return_value.connect.return_value.__enter__
      .return_value)


  @patch.object(repository, "listMetricIDsForInstance", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.deleteModel",
    new=Mock(spec_set=models_api.ModelHandler.deleteModel))
  def testDeleteInstancesHandler(self, listMetricIDsMock, engineFactoryMock):
    """
    Test for Delete "/_instances"
    response is validated for appropriate headers, body and status
    """
    listMetricIDsMock.return_value = \
      ["2490fb7a9df5470fa3678530c4cb0a43", "b491ab2310ef4a799b14c08fa3e09f1c"]
    params = ["YOMP-docs-elb", "i-e16bd2d5"]
    response = self.app.delete("", params=app_utils.jsonEncode(params),
      headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, response)
    self.assertTrue(listMetricIDsMock.called)
    listMetricIDsMock.assert_called_with(
      (engineFactoryMock.return_value.connect.return_value.__enter__
       .return_value),
      params[1])



  @patch.object(repository, "listMetricIDsForInstance", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.deleteModel",
    new=Mock(spec_set=models_api.ModelHandler.deleteModel))
  def testDeleteInstancesHandlerNonJSONData(self, listMetricIDsMock,
                                            _engineFactoryMock):
    """
    Test for Delete "/_instances" with non JSON input
    response is validated for appropriate headers, body and status
    """
    response = self.app.delete("", params="params", headers=self.headers,
     status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertFalse(listMetricIDsMock.called)


  @patch.object(repository, "listMetricIDsForInstance", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.deleteModel",
    new=Mock(spec_set=models_api.ModelHandler.deleteModel))
  def testDeleteInstancesHandlerEmptyData(self, listMetricIDsMock,
                                            _engineFactoryMock):
    """
    Test for Delete "/_instances" with with empty input data
    response is validated for appropriate headers, body and status
    """
    params = []
    response = self.app.delete("", params=app_utils.jsonEncode(params),
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertFalse(listMetricIDsMock.called)



@patch.object(repository, "engineFactory", autospec=True)
class InstanceHandlerTest(unittest.TestCase):
  """Unit tests for class InstanceHandler from Instances API."""


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(config)


  @patch.object(repository, "listMetricIDsForInstance", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.deleteModel",
    new=Mock(spec_set=models_api.ModelHandler.deleteModel))
  def testDeleteInstanceHandler(self, listMetricIDsMock, engineFactoryMock):
    """
    Test for Delete "/_instances/<instanceId>"
    response is validated for appropriate headers, body and status
    """
    listMetricIDsMock.return_value = ["2490fb7a9df5470fa3678530c4cb0a43",
                                      "b491ab2310ef4a799b14c08fa3e09f1c"]
    response = self.app.delete("", headers=self.headers,
                               params=json.dumps(["i-cd660efb"]))

    assertions.assertDeleteSuccessResponse(self, response)
    self.assertTrue(listMetricIDsMock.called)
    listMetricIDsMock.assert_called_once_with(
      (engineFactoryMock.return_value.connect.return_value.__enter__
       .return_value),
      "i-cd660efb")



@patch.object(repository, "engineFactory", autospec=True)
class InstanceDefaultsHandlerTest(unittest.TestCase):
  """Unit tests for class InstanceDefaultsHandler from Instances API."""


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(config)


  @patch.object(repository, "listMetricIDsForInstance", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel))
  def testInstanceDefaultsHandlerPOST(
      self, listMetricIDsMock, _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId"
    response is validated for appropriate headers, body and status
    """

    listMetricIDsMock.return_value = []

    region = "us-west-2"

    # Currently we are not supporting certain namespaces
    # unsupportedNamespaces reflects such unsupported namespaces
    # These namespaces are currently validated for "400 Bad Request"
    # and expected error message.
    # Update this list with changes in namespace support
    unsupportedNamespaces = ("Billing", "StorageGateway")

    for namespace in unsupportedNamespaces:
      response = self.app.post(
          "/%s/AWS/%s/abcd1234" % (region, namespace), headers=self.headers,
          status="*")
      assertions.assertBadRequest(self, response, "json")
      result = json.loads(response.body)["result"]
      self.assertTrue(result.startswith("Not supported."))

    cwAdapter = datasource.createDatasourceAdapter("cloudwatch")
    supportedNamespaces = set()
    for resourceInfo in cwAdapter.describeSupportedMetrics().values():
      for metricInfo in resourceInfo.values():
        supportedNamespaces.add(metricInfo["namespace"])

    for namespace in supportedNamespaces:
      response = self.app.post(
          "/%s/%s/abcd1234" % (region, namespace), headers=self.headers)
      assertions.assertSuccess(self, response)
      result = app_utils.jsonDecode(response.body)
      self.assertIsInstance(result, dict)
      self.assertEqual(result, {"result": "success"})


  @patch.object(repository, "getMetricCountForServer", autospec=True)
  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel,
      side_effect=QuotaError("Server limit reached.")))
  def testInstanceDefaultsHandlerPOSTQuotaError(self,
      getMetricCountForServerMock, _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId"
    Test for QuotaError thrown when reached number of server limit
    reached
    """

    getMetricCountForServerMock.return_value = 0

    response = self.app.post("/us-west-2/AWS/EC2/abcd1234",
     headers=self.headers, status="*")
    assertions.assertForbiddenResponse(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, {"result": "Server limit reached."})


  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel))
  def testInstanceDefaultsHandlerPOSTWithoutInstanceId(self,
                                                       _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId" without instanceId
    response is validated for appropriate headers, body and status
    """
    response = self.app.post("/us-west-2/AWS/EC2/",
     headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Invalid request", response.body)


  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel))
  def testInstanceDefaultsHandlerPOSTInvalidNamespace(self, _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId" with invalid
    namespace
    response is validated for appropriate headers, body and status
    """
    response = self.app.post("/us-west-2/AWS/foo/abcd1234",
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)


  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel))
  def testInstanceDefaultsHandlerPOSTInvalidNamespeceInsteadAWS(
      self, _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId" with invalid
    namespace.
    response is validated for appropriate headers, body and status
    """
    response = self.app.post("/us-west-2/foo/EC2/abcd1234",
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)


  @patch("YOMP.app.webservices.models_api.ModelHandler.createModel",
    new=Mock(spec_set=models_api.ModelHandler.createModel))
  def testInstanceDefaultsHandlerPOSTInvalidRegion(self, _engineFactoryMock):
    """
    Test for POST "/_instances/region/namespace/instanceId" with invalid
    region
    response is validated for appropriate headers, body and status
    """
    response = self.app.post("/fake-region/AWS/EC2/abcd1234",
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)



if __name__ == "__main__":
  unittest.main()
