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
Unit tests for Settings API
"""

import json

import unittest

import YOMP.app
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  webservices_assertions as assertions
)
from paste.fixture import TestApp
from htmengine import utils as app_utils
from YOMP.app import YOMPAppConfig
from YOMP.app.webservices import settings_api



class SettingsHandlerTest(unittest.TestCase):


  @classmethod
  def setUpClass(cls):
    cls.default_aws_access_key = YOMP.app.config.get("aws",
     "aws_access_key_id")
    cls.default_aws_secret_key = YOMP.app.config.get("aws",
     "aws_secret_access_key")
    cls.configurable_options = {
      "aws": set([
        u"aws_access_key_id",
        u"aws_secret_access_key"])}


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(settings_api.app.wsgifunc())


  # YOMP.conf is puposefully restored in tearDown considering that
  # testcases run any order
  # This will make sure we have clean config for each testcase
  def tearDown(self):
    config = YOMPAppConfig(mode=YOMPAppConfig.MODE_OVERRIDE_ONLY)
    if not config.has_section("aws"):
      config.add_section("aws")
    config.set("aws", "aws_secret_access_key", self.default_aws_secret_key)
    config.set("aws", "aws_access_key_id", self.default_aws_access_key)
    config.save()


  def testDefaultGetList(self):
    response = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    for config in self.configurable_options:
      self.assertTrue(result.has_key(config))
      for key in self.configurable_options[config]:
        if key in settings_api.HIDDEN_SETTINGS[config]:
          self.assertNotIn(key, result[config])
        else:
          self.assertIn(key, result[config])


  def testDefaultGetSpecificSection(self):
    response = self.app.get("/aws", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = app_utils.jsonDecode(response.body)
    self.assertIsInstance(result, dict)
    for key in set(self.configurable_options["aws"]):
      if key in settings_api.HIDDEN_SETTINGS["aws"]:
        self.assertNotIn(key, result)
      else:
        self.assertIn(key, result)


 # handling Assertionerror as TestApp throws
 # AssertionError: Content-Type header found in a 204 response,
 # which must not return content.
  def testPostTSection(self):
    try:
      self.app.post("/aws", json.dumps(
        {"aws_access_key_id" : "dummy_value_aws_key"}), headers=self.headers)
    except AssertionError, ae:
      print ae.message
    finally:
      config = YOMPAppConfig()
      self.assertEqual(config.get("aws", "aws_access_key_id"),
        "dummy_value_aws_key")


 # handling Assertionerror as TestApp throws
 # AssertionError: Content-Type header found in a 204 response,
 # which must not return content.
  def testPostAll(self):
    try:
      self.app.post("/", json.dumps(
        { "aws" : {"aws_secret_access_key" : "dummy_value_aws_secret",
          "aws_access_key_id" : "dummy_value_aws_key_id"}
         }), headers=self.headers)
    except AssertionError, ae:
      print ae.message
    finally:
      config = YOMPAppConfig()
      self.assertEqual(config.get("aws", "aws_secret_access_key"),
        "dummy_value_aws_secret")
      self.assertEqual(config.get("aws", "aws_access_key_id"),
        "dummy_value_aws_key_id")



if __name__ == "__main__":
  unittest.main()
