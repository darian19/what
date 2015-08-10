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
Integration test for :class:`YOMP.app.webservices.annotations_api`

  1. Happy path
    * Create Annotation
    * Get Annotation by annotation Id
    * Get Annotation by device id
    * Get Annotation by instance id
    * Get Annotation by date (from, to)
    * Delete annotation
  2. Test Required Fields
    * Unable to create incomplete annotation (missing required fields)
    * Unable to create annotation with unknown instance id
    * Unable to create annotation with invalid timestamp
    * Do not delete annotations when metric is deleted
    * Delete annotations when instance is deleted
  3. Test Security
    * Unable to create annotation using invalid apikey
    * Unable to delete annotation using invalid apikey
    * Unable to get annotations using invalid apikey
"""
import json
import unittest
from paste.fixture import TestApp, AppError
from YOMP.app import config as app_config
from htmengine import utils as app_utils
from YOMP.app.webservices import (annotations_api, instances_api, models_api)
from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository
from YOMP.test_utils.app.webservices import (
    getDefaultHTTPHeaders,
    getInvalidHTTPHeaders,
    webservices_assertions as assertions
)

# We need any valid EC2 instanceId as test data. Currently we
# are using jenkins-master's InstanceId and other details for validation.
# which is running production releases. In case this node is replaced please
# update testdata which new stable node details (e.g rpmbuilder etc)
VALID_EC2_INSTANCES = {
    "name": "jenkins-master",
    "instanceId":"i-f52075fe",
    "region":"us-west-2"
}



class AnnotationHandlerTest(unittest.TestCase):


  def _createEC2Instance(self):
    """
    Created EC2 instance to be used by the tests
    :return: Instance ID
    :rtype: str
    """
    app = TestApp(instances_api.app.wsgifunc())

    response = app.post("/" + self.instanceId, headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    self.assertEqual(result, {"result": "success"})


  def _deleteInstance(self):
    """
    Delete test EC2 instance created by :py:meth:`_createEC2Instance`
    """
    app = TestApp(instances_api.app.wsgifunc())
    response = app.delete("/", params=json.dumps([self.instanceId]),
                          headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    self.assertEqual(result, {"result": "success"})


  def _deleteOneMetric(self):
    """
    Delete one metric from test EC2 instance
    """
    app = TestApp(models_api.app.wsgifunc())
    response = app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, list)
    app.delete("/" + result[0]['uid'], headers=self.headers)


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(app_config)
    self.invalidHeaders = getInvalidHTTPHeaders()
    self.app = TestApp(annotations_api.app.wsgifunc())
    self.annotation = {
        "uid": "f4aa70b361f04036b0b39530900f38fa",
        "timestamp": "2014-01-25 05:00:00",
        "created": "2014-01-25 07:14:06",
        "device": "device1",
        "user": "Demo User",
        "server": "us-west-2/AWS/EC2/i-f52075fe",
        "message": "My annotation",
        "data": None
    }
    self.instanceId = "%s/AWS/EC2/%s" % (
        VALID_EC2_INSTANCES["region"],
        VALID_EC2_INSTANCES["instanceId"])

    # Prepare request as annotation without "uid" or "created" fields
    self.request = self.annotation.copy()
    self.request["server"] = self.instanceId
    del self.request["uid"]
    del self.request["created"]


  @ManagedTempRepository("Lifecycle")
  def testAnnotationLifecycle(self):
    """
    **Happy Path**

    * Make sure annotation was successfully created and all fields were
      initialized.
    * Make sure user can get annotation by ID and fail (Not Found) if he uses
      the wrong ID
    * Make sure user can get annotations by device and receive an empty array if
      he uses the wrong device
    * Make sure user can get annotations by instance and receive an empty array
      if he uses the wrong instance
    * Make sure user can get annotation by date and receive an empty array if he
      uses dates out of range
    * Make sure user can delete annotations
    """
    # Create Instance before annotation
    self._createEC2Instance()

    # Create Annotation
    response = self.app.post("", app_utils.jsonEncode(self.request),
                                        headers=self.headers)
    self.assertEqual(response.status, 201)

    # Use this newly created annotation as expected annotation from now on
    expectedAnnotation = app_utils.jsonDecode(response.body)

    # The result should contain new "uid" and "created" fields
    self.assertIn("uid", expectedAnnotation)
    self.assertIn("created", expectedAnnotation)
    # All the other fields should match request
    self.assertDictContainsSubset(self.request, expectedAnnotation)

    # Get Annotation By ID
    response = self.app.get("/" + expectedAnnotation["uid"],
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    # Get Annotation with wrong ID
    with self.assertRaises(AppError) as e:
      response = self.app.get("/dummy", headers=self.headers)
    self.assertIn("Bad response: 404 Not Found", str(e.exception))

    # Get all annotations
    response = self.app.get("/", headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertItemsEqual([expectedAnnotation], actual)

    # Get Annotations by Device
    response = self.app.get("/", {"device": self.request["device"]},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    # Get Annotations with wrong Device
    response = self.app.get("/", {"device": "dummy"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)

    # Get Annotations by server
    response = self.app.get("/", {"server": self.request["server"]},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    # Get Annotations with wrong server
    response = self.app.get("/", {"server": "dummy"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)

    # Get Annotations by date
    response = self.app.get("/", {"from": "2014-01-01 00:00:00"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    response = self.app.get("/", {"from": self.request["timestamp"]},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    response = self.app.get("/", {"to": self.request["timestamp"]},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    response = self.app.get("/", {"from": "2014-01-01 00:00:00",
                                             "to": "2014-12-31 00:00:00"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertDictEqual(expectedAnnotation, actual[0])

    # Get Annotations with date out of range
    response = self.app.get("/", {"from": "2014-12-31 00:00:00"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)

    response = self.app.get("/", {"to": "2014-01-01 00:00:00"},
                                       headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)

    # Delete annotation with wrong ID
    with self.assertRaises(AppError) as e:
      self.app.delete("/dummy", headers=self.headers)
    self.assertIn("Bad response: 404 Not Found", str(e.exception))

    # Make sure no annotation was deleted
    response = self.app.get("/", headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertItemsEqual([expectedAnnotation], actual)

    # Delete annotation
    response = self.app.delete("/" + expectedAnnotation["uid"],
                                          headers=self.headers)
    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)

    # Make sure annotation was deleted
    response = self.app.get("/", headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)


  @ManagedTempRepository("DataIntegrity")
  def testAnnotationDataIntegrity(self):
    """
    **Test Required Fields**

    * Make sure user is not allowed to add annotations without device
    * Make sure user is not allowed to add annotations without timestamp
    * Make sure user is not allowed to add annotations without instance
    * Make sure user is not allowed to add annotations with invalid/unknown
      instance
    * Do not delete annotations when metric is deleted
    * Delete annotations when instance is deleted
    """
    # Create Instance before annotation
    self._createEC2Instance()

    # Create request without "device"
    req = self.request.copy()
    del req["device"]
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(req),
                               headers=self.headers)

    # Create request without "timestamp"
    req = self.request.copy()
    del req["timestamp"]
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(req),
                               headers=self.headers)

    # Create request without "instance"
    req = self.request.copy()
    del req["server"]
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(req),
                               headers=self.headers)

    # Create request with invalid/unknown "instance"
    req = self.request.copy()
    req["server"] = "dummy"
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(req),
                               headers=self.headers)

    # Create request without "message" and "data"
    req = self.request.copy()
    del req["message"]
    del req["data"]
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(req),
                               headers=self.headers)


    # Add annotation
    response = self.app.post("", app_utils.jsonEncode(self.request),
                                        headers=self.headers)
    self.assertEqual(response.status, 201)

    # Use this newly created annotation as expected annotation from now on
    expectedAnnotation = app_utils.jsonDecode(response.body)

    # Do not delete annotations when metric is deleted

    # Delete metric
    self._deleteOneMetric()

    # Make sure no annotation was deleted
    response = self.app.get("/", headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertItemsEqual([expectedAnnotation], actual)

    # Delete annotations when instance is deleted
    self._deleteInstance()

    # Make sure annotation was deleted
    response = self.app.get("/", headers=self.headers)
    actual = app_utils.jsonDecode(response.body)
    self.assertTrue(len(actual) == 0)


  @ManagedTempRepository("Security")
  def testAnnotationSecurity(self):
    """
    **Test Security**

    * Make sure user is unable to add annotation using invalid key
    * Make sure user is unable to delete annotation using invalid key
    * Make sure user is unable to get annotation using invalid key
    """
    # Create Instance before annotation
    self._createEC2Instance()

    # Create single annotation for testing
    response = self.app.post("", app_utils.jsonEncode(self.request),
                                        headers=self.headers)
    expectedAnnotation = app_utils.jsonDecode(response.body)


    # Make sure user is unable to add annotation using invalid key
    with self.assertRaises(AppError):
      self.app.post("", app_utils.jsonEncode(self.request),
                               headers=self.invalidHeaders)

    # Make sure user is unable to get annotation using invalid key
    with self.assertRaises(AppError):
      self.app.get("/", headers=self.invalidHeaders)

    with self.assertRaises(AppError):
      self.app.get("/", {"device": self.request["device"]},
                              headers=self.invalidHeaders)

    with self.assertRaises(AppError):
      self.app.get("/" + expectedAnnotation["uid"],
                              headers=self.invalidHeaders)

    # Make sure user is unable to delete annotation using invalid key
    with self.assertRaises(AppError):
      self.app.delete("/" + expectedAnnotation["uid"],
                                 headers=self.invalidHeaders)


if __name__ == '__main__':
  unittest.main()
