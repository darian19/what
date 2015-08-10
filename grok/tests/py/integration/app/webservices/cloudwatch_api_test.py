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
Integration test cloudwatch API
"""
import json
import unittest
import os

from paste.fixture import TestApp

import YOMP.app
from htmengine import utils as app_utils
from YOMP.app.adapters.datasource import createCloudwatchDatasourceAdapter
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.webservices import cloudwatch_api

from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders
)
from YOMP.test_utils.app.webservices import (
  webservices_assertions as assertions)

from YOMP import logging_support



# We need any valid EC2 instanceId as test data. Currently we
# are using jenkins-master's InstanceId and other details for validation.
# which is running production releases. In case this node is replaced please
# update testdata which new stable node details (e.g rpmbuilder etc)
VALID_EC2_INSTANCE = {"InstanceId": "i-f52075fe",
                      "Name": "jenkins-master.YOMPsolutions.com",
                      "Description": "Jenkin Master(Python 2.7)"}



def setUpModule():
  logging_support.LoggingSupport.initTestApp()





class CWDefaultHandlerTest(unittest.TestCase):
  """
  Integration test CWDefaultHandler
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)

  def _testGETCloudWatchImpl(self, url):
    response = self.app.get(url, headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)

    supportedMetrics = createCloudwatchDatasourceAdapter().describeSupportedMetrics()

    for metrics in supportedMetrics.values():
      for metric, keys in metrics.items():
        self.assertIn(keys["namespace"],
                      result["namespaces"],
                      "Expected namespace (%s) not found in response." % (
                        keys["namespace"]))
        self.assertIn(metric,
                      result["namespaces"][keys["namespace"]]["metrics"],
                      "Expected metric (%s, %s) not found in response." % (
                        keys["namespace"], metric))


  @ManagedTempRepository("CWDefaultHandlerTest")
  def testGETCloudWatch(self):
    """
    Test for Get '/_metrics/cloudwatch'
    response is validated for appropriate headers, body and status
    response is validated against known namespaces and available metrics
    """
    self._testGETCloudWatchImpl("")


  @ManagedTempRepository("CWDefaultHandlerTest")
  def testGETCloudWatchWithSlash(self):
    """
    Test for Get '/_metrics/cloudwatch'
    response is validated for appropriate headers, body and status
    response is validated against known namespaces and available metrics
    """
    self. _testGETCloudWatchImpl("/")



class CWNamespaceHandlerTest(unittest.TestCase):
  """
  Integration test CWNamespaceHandler
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @staticmethod
  def _supportedAWSNamespaces():
    """ Compile set of supported AWS namespaces

    :returns: Set of known AWS Cloudwatch namespaces
    :rtype: set of str
    """
    return set(value
               for x in (createCloudwatchDatasourceAdapter()
                         .describeSupportedMetrics()
                         .values())
               for y in x.values()
               for key, value in y.items() if key == "namespace")


  @ManagedTempRepository("CWNamespaceHandlerTest")
  def testGETNamespaces(self):
    """
    Test for Get '/_metrics/cloudwatch/namespaces'
    response is validated for appropriate headers, body and status
    response is validated against known namespaces
    """
    response = self.app.get("/namespaces", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)

    supportedNamespaces = self._supportedAWSNamespaces() | set(["Autostacks"])

    self.assertEqual(supportedNamespaces, set(result.keys()))


  @ManagedTempRepository("CWNamespaceHandlerTest")
  def testGETSpecificNamespace(self):
    """
    Test for Get '/_metrics/cloudwatch/AWS/<namespace>'
    response is validated for appropriate headers, body and status
    response is validated against available metrics for each
    namespaces supported
    """
    for namespace in self._supportedAWSNamespaces():
      response = self.app.get("/%s" % namespace, headers=self.headers)
      assertions.assertSuccess(self, response)
      result = app_utils.jsonDecode(response.body)
      self.assertIsInstance(result, dict)


  @ManagedTempRepository("CWNamespaceHandlerTest")
  def testCWNamespaceHandlerNamespaceAWSInvalidType(self):
    """
    Test for Get '/_metrics/cloudwatch/AWS/<invalid_namespace>'
    response is validated for appropriate headers, body and status
    response is validated for error message
    """
    response = self.app.get('/AWS/foo', status="*", headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Namespace 'AWS/foo' was not found", response.body)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/namespaces", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
    """
    invalidHeaders =  getInvalidHTTPHeaders()
    response = self.app.get("/namespaces", status="*", headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)




class CWRegionsHandlerTest(unittest.TestCase):
  """
  Integration test CWRegionsHandler
  """
  @classmethod
  def setUpClass(cls):
    cls.regions = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/cw_regions.json")))

  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)

  @ManagedTempRepository("CWRegionsHandlerTest")
  def testGETListRegions(self):
    """
    Test for Get '/_metrics/cloudwatch/regions'
    response is validated for appropriate headers, body and status
    response is validated against json for supported regions
    """
    response = self.app.get("/regions", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    self.assertEqual(json.loads(response.body), self.regions)


  @ManagedTempRepository("CWRegionsHandlerTest")
  def testGETSpecificRegion(self):
    """
    Test for Get '/_metrics/cloudwatch/regions/<region-name>'
    response is validated for appropriate headers, body and status
    response is validated against expected information in response
    """
    response = self.app.get("/regions/us-west-2", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)
    attributes = ["name", "region", "namespace", "datasource", "identifier", \
     "metric", "dimensions"]

    for res in result:
      self.assertEqual(res["region"], "us-west-2")
      self.assertEqual(res["datasource"], "cloudwatch")
      self.assertItemsEqual(res.keys(), attributes)


  @ManagedTempRepository("CWRegionsHandlerTest")
  def testGETRegionInvalid(self):
    """
    Test for Get '/_metrics/cloudwatch/regions/<invalid-region-name>'
    response is validated for appropriate headers, body and status
    response is validated against expected error message
    """
    response = self.app.get('/regions/fake-region', status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Region 'fake-region' was not found", response.body)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/regions/us-west-2", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
    """
    invalidHeaders =  getInvalidHTTPHeaders()
    response = self.app.get("/regions/us-west-2",
                            status="*",
                            headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)



class CWInstanceHandlerTest(unittest.TestCase):
  """
  Integration test CWInstanceHandler
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETListInstancesForRegion(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances'
    response is validated for appropriate headers, body and status
    response is validated against response
    """
    response = self.app.get("/us-west-2/AWS/EC2",
                                              headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETSpecificInstanceFromRegion(self):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/<InstancdId>'
    response is validated for appropriate headers, body and status
    Test is currently using ec2 box for jenkins-master, this test also
    validates for retriving all supported metrics with dimensions
    """
    supportedMetrics = (
      createCloudwatchDatasourceAdapter().describeSupportedMetrics())
    ec2Metrics = supportedMetrics[ResourceTypeNames.EC2_INSTANCE].keys()

    # Instance used for following test is jenkins-master node
    response = self.app.get("/us-west-2/AWS/EC2/instances/%s"
        % VALID_EC2_INSTANCE["InstanceId"], headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)
    self.assertGreater(len(ec2Metrics), 0)
    self.assertGreater(len(result), 0)
    self.assertEqual(len(ec2Metrics), len(result))
    for res in result:
      self.assertEqual(res["region"], "us-west-2")
      self.assertEqual(res["namespace"], "AWS/EC2")
      self.assertEqual(res["datasource"], "cloudwatch")
      self.assertIn(res["metric"], ec2Metrics)
      self.assertIsInstance(res["dimensions"], dict)
      self.assertEqual(res["dimensions"]["InstanceId"],
        VALID_EC2_INSTANCE["InstanceId"])
      ec2Metrics.remove(res["metric"])

    self.assertEqual(ec2Metrics, [])


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETListInstancesForInvalidRegion(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/'
    with invalid region
    response is validated for appropriate headers, body and status
    and error message
    """
    response = self.app.get("/fake-region/AWS/EC2/instances", status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Region 'fake-region' was not found", response.body)


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETInstanceForInvalidInstance(self):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/<InstancdId>'
    with invalid InstancceId
    response is validated for appropriate headers, body and status

    Expect a 200 OK even when attempting to GET from an invalid instance,
    this saves the overhead of asking AWS if we're dealing with a valid
    instance every GET.

    We expect the CLI user to know what instance ID he/she is looking for.
    """
    response = self.app.get("/us-west-2/AWS/EC2/instances/abcd1234",
      status="*", headers=self.headers)
    assertions.assertSuccess(self, response)


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETListInstancesForInvalidNamespaceWithInstanceId(self):
    """
    Test for Get
    '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/<InstancdId>'
    with invalid namespace
    response is validated for appropriate headers, body and status
    and expected error message
    """
    response = self.app.get("/us-west-2/AWS/foo/instances/%s"
      % VALID_EC2_INSTANCE["InstanceId"], status="*", headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Namespace 'AWS/foo' was not found", response.body)


  @ManagedTempRepository("CWInstanceHandlerTest")
  def testGETListInstancesForInvalidNamespace(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/instances/'
    with invalid namespace
    response is validated for appropriate headers, body and status
    and expected error message
    """
    response = self.app.get("/us-west-2/AWS/foo/instances", status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Namespace 'AWS/foo' was not found", response.body)



  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/us-west-2/AWS/EC2/instances", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
    """
    invalidHeaders =  getInvalidHTTPHeaders()
    response = self.app.get("/us-west-2/AWS/EC2/instances", status="*",
      headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)




class CWMetricHandlerTest(unittest.TestCase):
  """
  Integration test CWMetricHandle
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @ManagedTempRepository("CWMetricHandlerTest")
  def testGETMetrics(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    response is validated for appropriate headers, body and status
    and response is validated with supported namespace and metric details
    """
    response = self.app.get("/us-west-2/AWS/EC2/CPUUtilization",
      headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)
    attributes = ["region", "namespace", "datasource", "metric", "dimensions"]
    for res in result:
      self.assertEqual(res["region"], "us-west-2")
      self.assertEqual(res["datasource"], "cloudwatch")
      self.assertEqual(res["metric"], "CPUUtilization")
      self.assertItemsEqual(res.keys(), attributes)
      self.assertIsInstance(res["dimensions"], dict)


  @ManagedTempRepository("CWMetricHandlerTest")
  def testGETMetricsInvalidRegion(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    with invalid region
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    response = self.app.get("/fake-region/AWS/EC2/CPUUtilization", status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Region 'fake-region' was not found", response.body)


  @ManagedTempRepository("CWMetricHandlerTest")
  def testGETListInstancesForInvalidNamespace(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    with invalid namespace
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    response = self.app.get("/us-west-2/AWS/foo/CPUUtilization", status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Namespace 'AWS/foo' was not found", response.body)


  @ManagedTempRepository("CWMetricHandlerTest")
  def testGETListInstancesForInvalidMetric(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName/'
    with invalid metric
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    response = self.app.get("/us-west-2/AWS/EC2/fake-metric", status="*",
     headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Metric 'fake-metric' was not found", response.body)


  @ManagedTempRepository("CWMetricHandlerTest")
  def testGETListInstancesForInvalidMetrcName(self):
    """
    Test for
    Get '/_metrics/cloudwatch/<region-name>/AWS/<namespace>/metricName'
    with invalid metric
    response is validated for appropriate headers, body and status
    and reponse  is validated for error message
    """
    response = self.app.get("/us-west-2/AWS/EC2/GroupTotalInstances",
      status="*", headers=self.headers)
    assertions.assertNotFound(self, response)
    self.assertIn("Metric 'GroupTotalInstances' was not found", response.body)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/us-west-2/AWS/EC2/CPUUtilization", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
    """
    invalidHeaders =  getInvalidHTTPHeaders()
    response = self.app.get("/us-west-2/AWS/EC2/CPUUtilization", status="*",
      headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)



class CWApiUnhapypTest(unittest.TestCase):
  """
  Unhappy tests for cloudwatch API
  """


  def setUp(self):
    self.app = TestApp(cloudwatch_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
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



if __name__ == '__main__':
  unittest.main()

