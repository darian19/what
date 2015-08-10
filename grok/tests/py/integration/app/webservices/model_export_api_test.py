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
import os
import json
import unittest
from paste.fixture import TestApp
import YOMP.app
from YOMP.app.webservices import models_api
from htmengine import utils
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  webservices_assertions as assertions
)
from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository



class TestModelExportHandler(unittest.TestCase):
  """
  Integration test for Model Export Handler API
  """


  def setUp(self):
    self.app = TestApp(models_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    data = open(os.path.join(YOMP.app.YOMP_HOME,
     "tests/py/data/app/webservices/models_api_integration_test.json")).read()
    self.modelsTestData = json.loads(data)

  @ManagedTempRepository("TestModelExportHandler")
  def testCompleteModelExportApiLifecycle(self):
    """
      Happy path testing for the route "/_models/export"
    """
    data = self.modelsTestData["create_data"]
    createResponse = self.app.put("/", utils.jsonEncode(data),
                       headers=self.headers)
    assertions.assertSuccess(self, createResponse, code=201)

    # NOTE: export uses a new format
    expectedExportSpec = {
      "datasource": data["datasource"],
      "metricSpec": {
        "region": data["region"],
        "namespace": data["namespace"],
        "metric": data["metric"],
        "dimensions": data["dimensions"]
      }
    }

    # Test export all data
    response = self.app.get("/export", headers=self.headers)
    assertions.assertSuccess(self, response)
    exportedData = utils.jsonDecode(response.body)
    self.assertIsInstance(exportedData, list)
    self.assertEqual(exportedData[0], expectedExportSpec)
    responseData = utils.jsonDecode(createResponse.body)
    uid = responseData[0]['uid']

    # Test for exporting single metric.
    response = self.app.get("/%s/export" % uid, headers=self.headers)
    assertions.assertSuccess(self, response)
    exportedData = utils.jsonDecode(response.body)
    self.assertIsInstance(exportedData, list)
    self.assertEqual(exportedData[0], expectedExportSpec)

    # Delete the model that was created earlier
    response = self.app.delete("/%s" % uid, headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, response)

    # Import the model from exported data
    response = self.app.put("/", utils.jsonEncode(exportedData),
                            headers=self.headers)
    assertions.assertSuccess(self, response, code=201)
    responseData = utils.jsonDecode(response.body)
    uid = responseData[0]['uid']

    # Export the newly-imported model
    response = self.app.get("/%s/export" % uid, headers=self.headers)
    assertions.assertSuccess(self, response)
    exportedData = utils.jsonDecode(response.body)
    self.assertIsInstance(exportedData, list)
    self.assertEqual(exportedData[0], expectedExportSpec)

    # Delete the model that was created earlier
    response = self.app.delete("/%s" % uid, headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, response)

    # Import the model using legacy format
    legacyImportSpec = dict(type="metric", **data)
    response = self.app.put("/", utils.jsonEncode(legacyImportSpec),
                            headers=self.headers)
    assertions.assertSuccess(self, response, code=201)
    responseData = utils.jsonDecode(response.body)
    uid = responseData[0]['uid']

    # Export the newly-imported model
    response = self.app.get("/%s/export" % uid, headers=self.headers)
    assertions.assertSuccess(self, response)
    exportedData = utils.jsonDecode(response.body)
    self.assertIsInstance(exportedData, list)
    self.assertEqual(exportedData[0], expectedExportSpec)


  @ManagedTempRepository("TestModelExportHandler")
  def testExportNonExistentModelUID(self):
    """
      Test for export of non existent model"
    """
    response = self.app.get("/f00bar/export", status="*", headers=self.headers)
    assertions.assertObjectNotFoundError(self, response)


if __name__ == "__main__":
  unittest.main()
