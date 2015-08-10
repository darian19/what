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

# TODO remove this when MER-1172 is resolved
# Unused variable warning for getPostDeleteResponse has been
# disabled. Some of code is in non execution mode. Remove this when
# MER-1170 is resolved
# pylint: disable= W0612

"""
Integration tests for Instances Api
"""
import json

import unittest
from paste.fixture import TestApp, AppError

import YOMP.app
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)
from YOMP.app.webservices import instances_api
from htmengine import utils as app_utils
from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository



# We need any valid EC2 instanceId as test data. Curretnly we
# are using jenkins-master's testLifecycleForSingleInstanceInstanceId and other details for validation.
# which is running production releases. In case this node is replaced please
# update testdata which new stable node details (e.g rpmbuilder etc)
# As a positive test for posting multiple instance, we need two instances
# belonging to same region currently its us-west-2. Keep this in mind
# while updating replacing testdata for rpm-builder, YOMP-docs
VALID_EC2_INSTANCES = {
  "jenkins-master":{
    "instanceId":"i-f52075fe",
    "region":"us-west-2"
  },
  "rpm-builder":{
    "instanceId":"i-12d67826",
    "region":"us-west-2"
  },
  "YOMP-docs":{
    "instanceId":"i-5c890c6b",
    "region":"us-west-2"
  }
}



class InstancesApiSingleTest(unittest.TestCase):
  """
  Integration tests methods for single instance
  """


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testLifecycleForSingleInstance(self):
    """
    Test for Get '/_instances'
    response is validated for appropriate headers, body and status
    Make sure app returns empty list at initial step

    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke post with valid instanceId

    Test for get '/_instances/{instanceId}'
    response is validated for appropriate headers, body and status
    Check if you can invoke get on previously post'ed instance Instance

    Test for delete '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    This invokes delete call on previously monitored instance

    Test for get '/_instances/{instanceId}'
    response is validated for appropriate headers, body and status
    This invokes get call with instanceId which is deleted from monitored list
    """

    # check initial empty response with get request
    initialGetResponse = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, initialGetResponse)
    initialGetResult = app_utils.jsonDecode(initialGetResponse.body)
    self.assertItemsEqual(initialGetResult, [])

    # Post single instance details to add under monitor
    region = VALID_EC2_INSTANCES["jenkins-master"]["region"]
    namespace = "EC2"
    instanceId = "%s/AWS/%s/%s" % (
      region, namespace, VALID_EC2_INSTANCES["jenkins-master"]["instanceId"])
    postResponse = self.app.post("/" + instanceId, headers=self.headers)
    assertions.assertSuccess(self, postResponse)
    postResult = app_utils.jsonDecode(postResponse.body)
    self.assertIsInstance(postResult, dict)
    self.assertEqual(postResult, {"result": "success"})

    # Verify that instance is successfully added under monitor
    getPostCheckResponse = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, getPostCheckResponse)
    getPostCheckResult = app_utils.jsonDecode(getPostCheckResponse.body)
    self.assertEqual(len(getPostCheckResult), 1)
    instanceResult = getPostCheckResult[0]
    self.assertEqual(region, instanceResult["location"])
    self.assertTrue(instanceId, instanceResult["server"])

    # Delete instance from monitor
    deleteResponse = self.app.delete("/", headers=self.headers,
                                     params=json.dumps([instanceId]))
    assertions.assertDeleteSuccessResponse(self, deleteResponse)

    # Check get reponse to confirm that instance has been deleted successfully
    getPostDeleteResponse = self.app.get("", headers=self.headers)
    postResult = app_utils.jsonDecode(getPostDeleteResponse.body)
    self.assertEqual(postResult, [])

    # TODO:  Assertion pending MER-1170
    #assertions.assertNotFound(self, getPostDeleteResponse)
    #self.assertEqual("Instance %s was not found" % instanceId,
    # getPostDeleteResponse.body)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostWithInvalidRegion(self):
    """
    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke Api call with region that does not exists
    """
    region = "fake-region"
    namespace = "EC2"
    instanceId = VALID_EC2_INSTANCES["jenkins-master"]["instanceId"]
    response = self.app.post("/%s/AWS/%s/%s" % (region, namespace, instanceId),
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostWithInvalidNamespace(self):
    """
    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke Api call with namespace that does not exists
    """
    region = "us-west-2"
    namespace = "foo"
    instanceId = VALID_EC2_INSTANCES["jenkins-master"]["instanceId"]
    response = self.app.post("/%s/AWS/%s/%s" % (region, namespace, instanceId),
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostWithInvalidServiceName(self):
    """
    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke Api call with namespace that does not exists. Specifically
    replace AWS with some invalid string making namespace invalid
    """
    region = "us-west-2"
    namespace = "EC2"
    instanceId = VALID_EC2_INSTANCES["jenkins-master"]["instanceId"]
    response = self.app.post("/%s/foo/%s/%s" % (region, namespace, instanceId),
      headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Not supported.", response.body)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostWithInvalidInstanceId(self):
    """
    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke Api call with instanceId that does not exists

    Expect a 200 OK even when attempting to POST to an invalid instance,
    this saves the overhead of asking AWS if we're dealing with a valid
    instance every POST.

    We expect the CLI user to know what instance ID he/she is looking for.
    """
    region = "us-west-2"
    namespace = "EC2"
    instanceId = "abcd1234"
    response = self.app.post("/%s/AWS/%s/%s" % (region, namespace, instanceId),
      headers=self.headers, status="*")
    assertions.assertSuccess(self, response)

  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostInstanceIdToIncorrectNamespace(self):
    """
    Test for post '/_instances/region/namespace/instanceId'
    response is validated for appropriate headers, body and status
    Invoke Api call with instance to incorrect namespace.
    e.g post YOMP-docs-elb to AWS/EC2

    Expect a 200 OK even when attempting to POST an instance to the wrong
    namespace, this saves the overhead of asking AWS if we're dealing with a
    valid instance in the given namespace with every POST request.

    We expect the CLI user to know what instance ID he/she is looking for.
    """
    region = "us-west-2"
    namespace = "EC2"
    instanceId = "YOMP-docs-elb"
    response = self.app.post("/%s/AWS/%s/%s" % (region, namespace, instanceId),
      headers=self.headers, status="*")
    assertions.assertSuccess(self, response)


  @ManagedTempRepository("InstancesApiSingleInstance")
  def testPostWithoutInstanceId(self):
    """
    Test for post '/_instances/region/namespace/instanceId' without instanceId
    response is validated for appropriate headers, body and status
    This invokes post call with without instanceId
    """
    response = self.app.post("/us-west-2/AWS/EC2/",
     headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Invalid request", response.body)



class InstancesApiMultipleInstanceTest(unittest.TestCase):
  """
  Integration tests methods for multiple instaces
  """


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @ManagedTempRepository("InstancesApiMultiple")
  def testLifecycleForMultipleInstances(self):
    """
    Test for Get '/_instances'
    response is validated for appropriate headers, body and status
    This expects response from application in initial stage when
    no instances are under monitor

    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    post multiple instances

    Test for Get '/_instances'
    response is validated for appropriate headers, body and status
    This test check for listed monitored instances from previous step

    Test for delete '/_instances'
    response is validated for appropriate headers, body and status
    invoke delete with valid instanceId for listed monitored instances
    from previous step


    Test for Get '/_instances'
    response is validated for appropriate headers, body and status
    This invokes get call to assert that all instances which were
    under monitor have been deleted and we get empty response
    """
    # Check instance list at initial phase for empty response
    getIntialResponse = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, getIntialResponse)
    getIntialResult = app_utils.jsonDecode(getIntialResponse.body)
    self.assertItemsEqual(getIntialResult, [])


    # Test for post '/_instances'

    # TODO: Until MER-1172 is resolved
    # test will execute this as temporary. This will add expected instances
    # under monitor. Which will be used for further tests
    # here adding
    params = [VALID_EC2_INSTANCES["rpm-builder"]["instanceId"],
      VALID_EC2_INSTANCES["YOMP-docs"]["instanceId"]]
    region = "us-west-2"
    namespace = "EC2"
    for instance in params:
      postResponse = self.app.post("/%s/AWS/%s/%s" % (region,
       namespace, instance), headers=self.headers)
      assertions.assertSuccess(self, postResponse)
      postResult = app_utils.jsonDecode(postResponse.body)
      self.assertIsInstance(postResult, dict)
      self.assertEqual(postResult, {"result": "success"})

    # TODO Use Api calls below once MER-1172 is resolved

    #postResponse = self.app.post("/us-west-2/AWS/EC2",
    #  params=app_utils.jsonEncode(params), headers=self.headers, status="*")
    #assertions.assertSuccess(self, response)
    #postResult = app_utils.jsonDecode(postResponse.body)
    #self.assertIsInstance(postResult, dict)
    #self.assertEqual(postResult, {"result": "success"})

    # Test for Get '/_instances'
    getPostCheckResponse = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, getPostCheckResponse)
    getPostCheckResult = app_utils.jsonDecode(getPostCheckResponse.body)
    instanceIds = []
    self.assertIsInstance(getPostCheckResult, list)
    for instance in getPostCheckResult:
      instanceIds.append(instance["server"])
      self.assertEqual(instance["namespace"], "AWS/EC2")
      self.assertEqual(instance["location"], "us-west-2")
    self.assertItemsEqual([instanceId.rpartition("/")[2]
                           for instanceId in instanceIds], params)

    # Delete instances under monitor
    deleteResponse = self.app.delete("",
                                     params=app_utils.jsonEncode(instanceIds),
                                     headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, deleteResponse)

    # check instances to confirm the delete action
    getPostDeleteCheckResponse = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, getPostDeleteCheckResponse)
    getPostDeleteResult = app_utils.jsonDecode(getPostDeleteCheckResponse.body)
    self.assertItemsEqual(getPostDeleteResult, [])


  @ManagedTempRepository("InstancesApiMultiple")
  def testPostMultipleWithEmptyData(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    Invoke post with empty data
    """
    params = []
    response = self.app.post("/us-west-2/AWS/EC2",
      params=app_utils.jsonEncode(params), headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("InvalidArgumentsError", response.body)


  @ManagedTempRepository("InstancesApiMultiple")
  def testPostMultipleWithNonJsonData(self):
    """
    Test for '/_instances'
    response is validated for appropriate headers, body and status
    Invoke post with non-json data
    """
    params = []
    response = self.app.post("/us-west-2/AWS/EC2",
      params=params, headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Invalid request", response.body)


  @ManagedTempRepository("InstancesApiMultiple")
  def testPostMultipleWithInvalidInstanceId(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    Invoke post with invalid instanceId

    Expect a 200 OK even when attempting to POST to an invalid instance,
    this saves the overhead of asking AWS if we're dealing with a valid
    instance every POST.

    We expect the CLI user to know what instance ID he/she is looking for.
    """
    params = ["abcd1234"]
    response = self.app.post("/us-west-2/AWS/EC2",
      params=app_utils.jsonEncode(params), headers=self.headers, status="*")
    assertions.assertSuccess(self, response)


  @ManagedTempRepository("InstancesApiMultiple")
  def testPostMultipleWithInstanceToIncorrectNamespace(self):
    """
    Test for post'/_instances'
    response is validated for appropriate headers, body and status
    Invoke post with valid instance id to incorrect namespace

    Expect a 200 OK even when attempting to POST an instance to the wrong
    namespace, this saves the overhead of asking AWS if we're dealing with a
    valid instance in the given namespace with every POST request.

    We expect the CLI user to know what instance ID he/she is looking for.

    """
    params = ["YOMP-docs-elb"]
    response = self.app.post("/us-west-2/AWS/EC2",
      params=app_utils.jsonEncode(params), headers=self.headers, status="*")
    assertions.assertSuccess(self, response)


  @ManagedTempRepository("InstancesApiMultiple")
  def testPostMultipleWithInstanceToIncorrectRegion(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    invoke post with valid instance id to incorrect region
    """
    params = [VALID_EC2_INSTANCES["jenkins-master"]]
    response = self.app.post("/us-east-1/AWS/EC2",
      params=app_utils.jsonEncode(params), headers=self.headers, status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("InvalidArgumentsError", response.body)


  @ManagedTempRepository("InstancesApiMultiple")
  def testDeleteMultipleWithEmptyData(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    invoke delete with empty data
    """
    params = []

    with self.assertRaises(AppError) as err:
      self.app.delete("",
                      params=app_utils.jsonEncode(params),
                      headers=self.headers)

    self.assertIn("Missing instances in DELETE request", str(err.exception))


  @ManagedTempRepository("InstancesApiMultiple")
  def testDeleteMultipleWithInvalidInstanceId(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    invoke delete with invalid Instance id
    """
    params = ["abcd1234"]
    response = self.app.delete("", params=app_utils.jsonEncode(params),
      headers=self.headers, status="*")
    assertions.assertNotFound(self, response)
    self.assertIn("Not able to delete", response.body)


  @ManagedTempRepository("InstancesApiMultiple")
  def testDeleteMultipleinstancesWithInvalidData(self):
    """
    Test for post '/_instances'
    response is validated for appropriate headers, body and status
    invoke delete with invalid Instance id
    """
    params = []
    response = self.app.delete("", params=params, headers=self.headers,
      status="*")
    assertions.assertBadRequest(self, response, "json")
    self.assertIn("Invalid request", response.body)



class InstancesApiUnhappyTest(unittest.TestCase):
  """
  Unhappy tests forInstances API
  """


  def setUp(self):
    self.app = TestApp(instances_api.app.wsgifunc())
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
    invalidHeaders = getInvalidHTTPHeaders()
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
    self.assertEqual(headers["Allow"], "GET, DELETE")




if __name__ == '__main__':
  unittest.main()
