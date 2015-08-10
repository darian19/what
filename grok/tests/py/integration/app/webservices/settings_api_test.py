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
Integration test Settings API
"""
import unittest
import  YOMP.app
from paste.fixture import TestApp, AppError
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)
from htmengine import utils as app_utils
from YOMP.app import YOMPAppConfig
from YOMP.app.webservices import settings_api



class SettingsHandlerTest(unittest.TestCase):
  """
  Integration test settings API
  """


  @classmethod
  def setUpClass(cls):

    cls.configurable_options = {
      "aws": set([
        u"aws_access_key_id",
        u"aws_secret_access_key"])}


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(settings_api.app.wsgifunc())


  def testSettingsHandlerDefault(self):
    """
    Test for GET for '/_settings', List All Settings
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("", headers=self.headers)

    assertions.assertResponseHeaders(self, response)
    assertions.assertResponseBody(self, response)
    assertions.assertResponseStatusCode(self, response, 200)

    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    for config in self.configurable_options:
      self.assertTrue(result.has_key(config))
      for key in self.configurable_options[config]:
        if key in settings_api.HIDDEN_SETTINGS[config]:
          self.assertNotIn(key, result[config])
        else:
          self.assertIn(key, result[config])


  def testGETValidSection(self):
    """
    Test for GET for '/_settings/section, List Some Settings
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/aws", headers=self.headers)

    assertions.assertResponseHeaders(self, response)
    assertions.assertResponseBody(self, response)
    assertions.assertResponseStatusCode(self, response, 200)

    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    for key in set(self.configurable_options["aws"]):
      if key in settings_api.HIDDEN_SETTINGS["aws"]:
        self.assertNotIn(key, result)
      else:
        self.assertIn(key, result)


  def testGETInvalidSection(self):
    """
    Test for GET for '/_settings/section, List Some invalid Settings
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/dddd", headers=self.headers)

    assertions.assertResponseHeaders(self, response)
    assertions.assertResponseBody(self, response)
    assertions.assertResponseStatusCode(self, response, 200)
    self.assertEqual(app_utils.jsonDecode(response.body), {})


  # handling Assertionerror as TestApp throws
  # AssertionError: Content-Type header found in a 204 response,
  # which must not return content.
  def testPOSTSection(self):
    """
    Test for POST for '/_settings', Set some setting
    resoponse is validated for appropriate headers and body
    """
    # IMPORTANT: functions are executed in reverse order from when they are
    # added so we need to add config.save first.
    configBackup = YOMPAppConfig(mode=YOMPAppConfig.MODE_OVERRIDE_ONLY)
    self.addCleanup(configBackup.save)
    del configBackup

    try:
      self.app.post("/aws", app_utils.jsonEncode(
        {"aws_access_key_id" : "dummy_aws_key1"}), headers=self.headers)
    except AssertionError, ae:
      print ae.message
    finally:
      config = YOMPAppConfig()
      self.assertEqual(config.get("aws", "aws_access_key_id"),
                       "dummy_aws_key1")


  def testPOSTSectionInvalid(self):
    """
    Test for POST for '/_settings', Set some invalid setting
    resoponse is validated for appropriate headers and body
    """
    with self.assertRaises(AppError) as e:
      self.app.post("/foo", app_utils.jsonEncode(
        {"aws_access_key_id" : "dummy_aws_key2"}), headers=self.headers)
    self.assertIn("Bad response: 400 Bad Request (not 200 OK or 3xx redirect"
    " for /foo)\nFailed to update configuration settings", str(e.exception))


 # handling Assertionerror as TestApp throws
 # AssertionError: Content-Type header found in a 204 response,
 # which must not return content.
  def testPOSTAll(self):
    """
    Test for POST for '/_settings', Set All Settings
    resoponse is validated for appropriate headers and body
    """
    # Set up cleanup calls for resetting the config values
    # IMPORTANT: functions are executed in reverse order from when they are
    # added so we need to add config.save first.
    configBackup = YOMPAppConfig(mode=YOMPAppConfig.MODE_OVERRIDE_ONLY)
    self.addCleanup(configBackup.save)
    del configBackup

    try:
      # Make the POST request
      self.app.post(
          "/", app_utils.jsonEncode(
              {"aws": {"aws_access_key_id": "dummy_aws_key3",
                       "aws_secret_access_key": "dummy_aws_secret3"}}),
          headers=self.headers)
    except AssertionError, ae:
      print ae.message
    finally:
      config = YOMPAppConfig()
      self.assertEqual(config.get("aws", "aws_access_key_id"),
                       "dummy_aws_key3")
      self.assertEqual(config.get("aws", "aws_secret_access_key"),
                       "dummy_aws_secret3")



class SettingsApiUnhappyTest(unittest.TestCase):
  """
  Unhappy tests for cloudwatch API
  """


  def setUp(self):
    self.app = TestApp(settings_api.app.wsgifunc())
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


  def testInvalidMethod(self):
    """
    Invoke non supported method
    resoponse is validated for appropriate headers and body
    """
    response = self.app.put("", status="*", headers=self.headers)
    assertions.assertMethodNotAllowed(self, response)
    headers = dict(response.headers)
    self.assertEqual(headers["Allow"], "GET, POST")



if __name__ == "__main__":
  unittest.main()
