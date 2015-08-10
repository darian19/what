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
Unit tests for Annotations API
"""
import unittest
import json
from paste.fixture import TestApp, AppError
from mock import patch
from YOMP import logging_support
import YOMP.app
from YOMP.app import (
    exceptions as app_exceptions,
    repository)
import htmengine.utils as app_utils
from YOMP.app.webservices import annotations_api
from YOMP.test_utils.app.webservices import getDefaultHTTPHeaders



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



@patch.object(repository, "engineFactory", autospec=True)
class AnnotationsHandlerTest(unittest.TestCase):

  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(annotations_api.app.wsgifunc())
    self.annotation = {
      "uid": "f4aa70b361f04036b0b39530900f38fa",
      "timestamp": "2014-01-25 05:00:00",
      "created": "2014-01-25 07:14:06",
      "device": "device1",
      "user": "John Doe",
      "server": "YOMPdb2",
      "message": "My annotation",
      "data": None
    }
    # Prepare request as annotation without "uid" or "created" fields
    self.request = self.annotation.copy()
    del self.request["uid"]
    del self.request["created"]


  @patch("YOMP.app.repository.getAnnotationById")
  def testGETAnnotationById(self, getAnnotationById, _):
    """
      Test Get Annotation

      Request::

        GET /_annotations/{uid}

    Response::

      HTTP 200 Ok
      [
        {
           "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
           "device", "1231AC32FE",
           "created":"2013-08-27 16:46:51",
           "timestamp":"2013-08-27 16:45:00",
           "user":"John Doe",
           "server":" AWS/EC2/i-53f52b67",
           "message":" The CPU Utilization was high ...",
           "data": { Optional JSON Object }
         }
      ]
    """
    getAnnotationById.return_value = self.annotation

    response = self.app.get("/%s" % self.annotation["uid"],
                            headers=self.headers)
    self.assertEqual(response.status, 200)
    actual = json.loads(response.body)
    expected = json.loads(app_utils.jsonEncode(self.annotation))

    self.assertDictEqual(expected, actual[0])


  @patch("YOMP.app.repository.getAnnotationById")
  def testGETAnnotationByIdNotFound(self, getAnnotationById, _):
    """
      Test Get Annotation for unknown uid

      Request::

        GET /_annotations/{uid}

    Response::

      HTTP 404 Not Found

    """
    getAnnotationById.side_effect = app_exceptions.ObjectNotFoundError
    with self.assertRaises(AppError) as e:
      self.app.get("/dummy", headers=self.headers)

    self.assertIn("Bad response: 404 Not Found", str(e.exception))


  @patch("YOMP.app.repository.getAnnotations")
  def testGetAnnotations(self, getAnnotations, _):
    """
      Test Get Annotation

      Request::

        GET /_annotations?device={device}&user={user}&server={server}
                          &from={from}&to={to}

    Response::

      HTTP 200 Ok
      [
        {
           "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
           "device", "1231AC32FE",
           "created":"2013-08-27 16:46:51",
           "timestamp":"2013-08-27 16:45:00",
           "user":"John Doe",
           "server":" AWS/EC2/i-53f52b67",
           "message":" The CPU Utilization was high ...",
           "data": { Optional JSON Object }
         },
        ...
      ]
    """
    getAnnotations.return_value = [self.annotation]

    response = self.app.get("?%s=%s" % ("server", "dummy"),
                            headers=self.headers)
    self.assertEqual(response.status, 200)
    actual = json.loads(response.body)
    expected = json.loads(app_utils.jsonEncode(self.annotation))

    self.assertDictEqual(expected, actual[0])


  @patch("YOMP.app.repository.deleteAnnotationById")
  def testDeleteAnnotationNotFound(self, deleteAnnotationById, _):
    """
    Test Delete unknown Annotation

    Request::

      DELETE /_annotations/{uid}

    Response::

      HTTP 404 Not Found
    """
    deleteAnnotationById.side_effect = app_exceptions.ObjectNotFoundError
    with self.assertRaises(AppError) as e:
      self.app.delete("/dummy", headers=self.headers)

    self.assertIn("Bad response: 404 Not Found", str(e.exception))


  @patch("YOMP.app.repository.deleteAnnotationById")
  def testDeleteAnnotation(self, deleteAnnotationById, _):
    """
    Test Delete Annotation

    Request::

      DELETE /_annotations/{uid}

    Response::

      HTTP 204 No Content
    """
    response = self.app.delete("/%s" % self.annotation["uid"],
                               headers=self.headers)
    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    self.assertTrue(deleteAnnotationById.called)


  @patch("YOMP.app.repository.addAnnotation")
  def testAddAnnotation(self, addAnnotation, _):
    """
    Test Create new Annotation

    Request::

      POST /_annotations

      {
         "device", "1231AC32FE",
         "timestamp":"2013-08-27 16:45:00",
         "user":"John Doe",
         "server":" AWS/EC2/i-53f52b67",
         "message":" The CPU Utilization was high ...",
         "data": { Optional JSON Object }
      }

    Response::

      HTTP Status 201 Created

      {
         "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
         "device", "1231AC32FE",
         "created":"2013-08-27 16:46:51",
         "timestamp":"2013-08-27 16:45:00",
         "user":"John Doe",
         "server":" AWS/EC2/i-53f52b67",
         "message":" The CPU Utilization was high ...",
         "data": { Optional JSON Object }
      }
    """
    addAnnotation.return_value = self.annotation

    response = self.app.post("", app_utils.jsonEncode(self.request),
                             headers=self.headers)
    self.assertEqual(response.status, 201)
    actual = json.loads(response.body)
    # The result should contain new "uid" and "created" fields
    self.assertIn("uid", actual)
    self.assertIn("created", actual)
    # All the other fields should match request
    self.assertDictContainsSubset(self.request, actual)


  def testAddAnnotationIncomplete(self, _):
    """
    Test Failed to Create incomplete Annotation

    Response::

      HTTP Status 400 Missing "field" in request
    """
    # Annotation without timestamp
    badRequest = self.request.copy()
    del badRequest["timestamp"]
    with self.assertRaises(AppError) as e:
      self.app.post("", app_utils.jsonEncode(badRequest), headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message, "Missing 'timestamp' in request")

    # Annotation without device
    badRequest = self.request.copy()
    del badRequest["device"]
    with self.assertRaises(AppError) as e:
      self.app.post("", app_utils.jsonEncode(badRequest), headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message, "Missing 'device' in request")

    # Annotation without server
    badRequest = self.request.copy()
    del badRequest["server"]
    with self.assertRaises(AppError) as e:
      self.app.post("", app_utils.jsonEncode(badRequest), headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message, "Missing 'server' in request")

    # Annotation without user
    badRequest = self.request.copy()
    del badRequest["user"]
    with self.assertRaises(AppError) as e:
      self.app.post("", app_utils.jsonEncode(badRequest), headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message, "Missing 'user' in request")

    # Annotation without data and message
    badRequest = self.request.copy()
    del badRequest["message"]
    del badRequest["data"]
    with self.assertRaises(AppError) as e:
      self.app.post("", app_utils.jsonEncode(badRequest), headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message,
                             "Annotation must contain either 'message' or 'data'")


  def testAddAnnotationInvalidJSON(self, _):
    """
    Test failed to create annotation with invalid JSON argument

    Response::

      HTTP Status 400 Invalid JSON in request
    """
    badRequest = "{Not a JSON Request}"
    with self.assertRaises(AppError) as e:
      self.app.post("", badRequest, headers=self.headers)

    error = e.exception
    self.assertRegexpMatches(error.message, "Invalid JSON in request")



if __name__ == "__main__":
  unittest.main()
