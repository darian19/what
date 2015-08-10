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
Integration test metrics API
"""
import unittest

from paste.fixture import TestApp

import YOMP.app
from YOMP.app.webservices import metrics_api
from htmengine import utils

from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)



class MetricsHandlerTest(unittest.TestCase):
  """
  Integration tests for  metrics API
  """


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(metrics_api.app.wsgifunc())


  @ManagedTempRepository("MettricsHandlerTest")
  def testGETDatasources(self):
    """
    Test for GET for '/_metrics/datasources'
    response is validated for appropriate headers and body
    """
    response = self.app.get('/datasources', headers=self.headers)
    assertions.assertSuccess(self, response)
    self.assertIsInstance(utils.jsonDecode(response.body), list)
    self.assertSetEqual(set(utils.jsonDecode(response.body)),
                     set(["autostack", "custom", "cloudwatch"]))



class MetricsApiUnhappyTest(unittest.TestCase):
  """
  Unhappy tests for Metrics  API
  """


  def setUp(self):
    self.app = TestApp(metrics_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  def testNoAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    resoponse is validated for appropriate headers and body
    """
    response = self.app.get("/datasources", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  def testInvalidAuthHeaders(self):
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    resoponse is validated for appropriate headers and body
    """
    invalidHeaders = getInvalidHTTPHeaders()
    response = self.app.get("/datasources", status="*", headers=invalidHeaders)
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
    response = self.app.post("/datasources", status="*", headers=self.headers)
    assertions.assertMethodNotAllowed(self, response)
    headers = dict(response.headers)
    self.assertEqual(headers["Allow"], "GET")



if __name__ == '__main__':
  unittest.main()
