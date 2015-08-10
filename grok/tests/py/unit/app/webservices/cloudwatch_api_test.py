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
Unit tests for Cloudwatch API
"""
import unittest

from mock import patch
from paste.fixture import TestApp

import YOMP.app
from htmengine import utils as app_utils
import YOMP.app.adapters.datasource as datasource_adapter_factory
from YOMP.app.webservices import cloudwatch_api
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)




class CWDefaultHandlerTest(unittest.TestCase):
  """
  Unit tests CWDefaultHandler
  """

  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    self.resources = adapter.describeSupportedMetrics()
    self.regions = adapter.describeRegions()


  def _getCloudWatchCommon(self, url, expectedResult):
    response = self.app.get(url, headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    self.assertEqual(result, expectedResult)


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testCWDefaultHandlerDefault(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = []
    adapterMock.return_value.describeSupportedMetrics.return_value = {}
    self._getCloudWatchCommon("", {"regions": {}, "namespaces": {}})


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testCWDefaultHandlerDefaultWithSlash(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = []
    adapterMock.return_value.describeSupportedMetrics.return_value = {}
    self._getCloudWatchCommon("/", {"regions": {}, "namespaces": {}})




class CWNamespaceHandlerTest(unittest.TestCase):
  """
  Unit tests CWNamespaceHandler
  """


  @classmethod
  def setUpClass(cls):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    cls.resources = adapter.describeSupportedMetrics()
    cls.regions = adapter.describeRegions()


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(cloudwatch_api.app.wsgifunc())


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetListNamespaceNoRegions(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/namespaces'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = []
    response = self.app.get("/namespaces", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    # Added Autostacks namespaces to this list for now, to maintain API
    # backwards-compatibility during adapter refactor
    self.assertEqual(result, {'Autostacks': {'metrics': ['InstanceCount']}})


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetNamespaceAWSType(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/AWS/<namespace>'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/AWS/EC2", headers=self.headers)
    #self.assertTrue(getMetrics.called)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result,
                     {'AWS/EC2': {'dimensions': ['InstanceId',
                                                 'AutoScalingGroupName'],
                                  'metrics': ['CPUUtilization',
                                              'NetworkIn',
                                              'DiskWriteBytes',
                                              'NetworkOut',
                                              'DiskReadBytes']}})


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetNamespaceAWSInvalidType(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/AWS/<invalid_namespace>'
    response is validated for appropriate headers, body and status
    response is validated for error message
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/AWS/foo", headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual("Namespace 'AWS/foo' was not found", response.body)



class TestCWRegionsHandler(unittest.TestCase):
  """
  Unit tests CWRegionsHandler
  """


  @classmethod
  def setUpClass(cls):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    cls.resources = adapter.describeSupportedMetrics()
    cls.regions = adapter.describeRegions()



  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(cloudwatch_api.app.wsgifunc())


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetListRegionsEmptyResponse(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/regions'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = []
    response = self.app.get("/regions", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, {})


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetListRegionsNonEmptyResponse(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/regions'
    response is validated for appropriate headers, body and status
    and pre-defined values
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    response = self.app.get("/regions", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, dict(self.regions))


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetListRegionMetricsEmptyResponse(self, adapterMock):
    """
    Test for Get '/_metrics/cloudwatch/regions/<invalid-region-name>'
    response is validated for appropriate headers, body and status
    response is validated against expected error message
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    response = self.app.get('/regions/fake-region', status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Region 'fake-region' was not found", response.body)



class TestCWInstanceHandler(unittest.TestCase):
  """
  Units tests CWInstanceHandler
  """


  @classmethod
  def setUpClass(cls):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    cls.resources = adapter.describeSupportedMetrics()
    cls.regions = adapter.describeRegions()


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(cloudwatch_api.app.wsgifunc())


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetInstanceWithInvalidRegion(self, adapterMock):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/'
    with invalid region
    response is validated for appropriate headers, body and status
    and error message
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/fake-region/AWS/EC2/instances/i-832311",
      headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual(response.body, "Region 'fake-region' was not found")


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetInstanceWithInvalidNamespace(self, adapterMock):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/<InstancdId>'
    with invalid InstancceId
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/us-east-1/AWS/foo/instances/i-832311",
      headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual(response.body, "Namespace 'AWS/foo' was not found")


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetInstanceWithDimension(self,adapterMock):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/\
    instances/<InstancdId>'
    with valid InstancceId
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    adapterMock.return_value.describeResources.return_value = [
      {'grn': u'aws://us-west-2/Instance/i-548acc3a',
       'name': u'Bar',
       'resID': u'i-548acc3a'}]

    response = self.app.get("/us-east-1/AWS/EC2/instances/i-548acc3a",
                            headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertTrue(all(metric["metric"]
                        in self.resources['AWS::EC2::Instance']
                        for metric in result))


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetInstanceWithDimensionNotFoundEmpty(self, adapterMock):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/\
    instances/<InstancdId>/Dimenion'
    with invalid InstancceId
    response is validated for appropriate headers, body and status
    Tests scenario when given instance name is not
    present in ouput from getDimensionsFromRegion
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    adapterMock.return_value.describeResources.return_value = [
      {'grn': u'aws://us-west-2/Instance/i-548acc3a',
       'name': u'Bar',
       'resID': u'i-548acc3a'}]

    response = self.app.get("/us-east-1/AWS/EC2/instances/i-1234567a",
                                headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, [])



class TestCWMetricHandler(unittest.TestCase):
  """
  Unit tests CWMetricHandler
  """


  @classmethod
  def setUpClass(cls):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    cls.resources = adapter.describeSupportedMetrics()
    cls.regions = adapter.describeRegions()

  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(cloudwatch_api.app.wsgifunc())


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetMetricsWithInvalidRegion(self, adapterMock):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    with invalid region
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/fake-region/AWS/EC2/CPUUtilization",
         headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual(response.body, "Region 'fake-region' was not found")

  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetMetricInvalidNamespace(self, adapterMock):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    with invalid namespace
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    response = self.app.get("/us-east-1/AWS/foo/CPUUtilization",
       headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual(response.body, "Namespace 'AWS/foo' was not found")

  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetMetricValidInputEmptyResponse(self, adapterMock):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    response is validated for appropriate headers, body and status
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    adapterMock.return_value.describeResources.return_value = []
    response = self.app.get("/us-east-1/AWS/EC2/CPUUtilization",
      headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertEqual(result, [])


  @patch("YOMP.app.webservices.cloudwatch_api.datasource_adapter_factory."
         "createCloudwatchDatasourceAdapter")
  def testGetMetricDimensionWithResponse(self, adapterMock):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    response is validated for appropriate headers, body and status
    and response is validated with pre-defined responses
    """
    adapterMock.return_value.describeRegions.return_value = self.regions
    adapterMock.return_value.describeSupportedMetrics.return_value = (
      self.resources)
    adapterMock.return_value.describeResources.return_value = [
      {'grn': u'aws://us-west-2/Instance/i-d48ccaba',
       'name': u'Foo',
       'resID': u'i-d48ccaba'},
      {'grn': u'aws://us-west-2/Instance/i-548acc3a',
       'name': u'Bar',
       'resID': u'i-548acc3a'}]

    response = self.app.get("/us-east-1/AWS/EC2/CPUUtilization",
      headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertItemsEqual(result,
      [
        {'datasource': 'cloudwatch',
         'dimensions': {'InstanceId': 'i-d48ccaba'},
         'metric': 'CPUUtilization',
         'namespace': 'AWS/EC2',
         'region': 'us-east-1'},
        {'datasource': 'cloudwatch',
         'dimensions': {'InstanceId': 'i-548acc3a'},
         'metric': 'CPUUtilization',
         'namespace': 'AWS/EC2',
         'region': 'us-east-1'},
        {'datasource': 'cloudwatch',
         'dimensions': {'AutoScalingGroupName': 'i-d48ccaba'},
         'metric': 'CPUUtilization',
         'namespace': 'AWS/EC2',
         'region': 'us-east-1'},
        {'datasource': 'cloudwatch',
         'dimensions': {'AutoScalingGroupName': 'i-548acc3a'},
         'metric': 'CPUUtilization',
         'namespace': 'AWS/EC2',
         'region': 'us-east-1'}
      ])



class CWApiUnhappyTest(unittest.TestCase):
  """
  Unhappy tests for Cloudwatch API
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    response is validated for appropriate headers and body
    """
    response = self.app.get("", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    response is validated for appropriate headers and body
    """
    invalidHeaders =  getInvalidHTTPHeaders()
    response = self.app.get("", status="*", headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidRoute(self):
    """
    Invoke non supported route
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/foo", status="*", headers=self.headers)
    assertions.assertRouteNotFound(self, response)


  def testInvalidMethod(self):
    """
    Invoe non supported methods
    resoponse is validated for appropriate headers and body
    """
    response = self.app.post("", status="*", headers=self.headers)
    assertions.assertMethodNotAllowed(self, response)
    headers = dict(response.headers)
    self.assertEqual(headers["Allow"], "GET")



if __name__ == "__main__":
  unittest.main()
