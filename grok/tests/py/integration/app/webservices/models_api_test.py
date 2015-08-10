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
import logging
import os
import json
import time
from random import randrange
import unittest
from paste.fixture import TestApp
import requests

import YOMP.app
from YOMP.app import repository
from YOMP.app.webservices import models_api
from htmengine import utils

from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)
from YOMP.test_utils import aws_utils
from htmengine.exceptions import ObjectNotFoundError
from YOMP.test_utils.app.sqlalchemy_test_utils import\
 ManagedTempRepository

from YOMP import logging_support

import time


g_logger = logging.getLogger("integration.model_api_test")


def setUpModule():
  logging_support.LoggingSupport.initTestApp()



class TestModelHandler(unittest.TestCase):
  """
  Integration test for Model Handler API
  """



  def setUp(self):
    self.app = TestApp(models_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    data = open(os.path.join(YOMP.app.YOMP_HOME,
     "tests/py/data/app/webservices/models_api_integration_test.json")).read()
    self.modelsTestData = json.loads(data)


  def _checkCreateModelResult(self, postResult, metricSpec):
    dimensions = metricSpec["dimensions"]
    expectedRegion = metricSpec["region"]
    expectedNamespace = metricSpec["namespace"]
    expectedInstanceId = dimensions["InstanceId"]

    self.assertItemsEqual(postResult.keys(),
                          self.modelsTestData["create_response"].keys())

    self.assertEqual(postResult["server"],
      "%s/%s/%s" % (expectedRegion, expectedNamespace, expectedInstanceId))

    self.assertEqual(postResult["location"], expectedRegion)

    self.assertEqual(postResult["name"],
                     expectedNamespace + "/" + metricSpec["metric"])


  def testCompleteModelsApiLifecycle(self):
    """
      Happy path testing for the route "/_models"
    """
    # get all models in the system when there are no models
    # expected response is []
    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    allModelsResult = utils.jsonDecode(response.body)
    self.assertEqual(len(allModelsResult), 0)
    self.assertIsInstance(allModelsResult, list)

    data = self.modelsTestData["create_data"]

    # create a model using PUT;
    # Any HTTP POST call is forwarded to HTTP PUT in the Model API.
    #   def POST(self):
    #      return self.PUT()
    # The tests are just calling PUT.
    # TODO: wouldn't POST be a better method to test in that case, since it
    #  would exercise both POST and PUT?
    response = self.app.put("/", utils.jsonEncode(data), headers=self.headers)
    assertions.assertSuccess(self, response, code=201)
    postResult = utils.jsonDecode(response.body)
    self.assertEqual(len(postResult), 1)
    self._checkCreateModelResult(postResult[0], data)

    # get model that was previously created
    uid = postResult[0]["uid"]
    response = self.app.get("/%s" % uid, headers=self.headers)
    assertions.assertSuccess(self, response)
    getModelResult = utils.jsonDecode(response.body)
    self.assertItemsEqual(getModelResult[0].keys(),
      self.modelsTestData["get_response"].keys())

    # get all models in the system
    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    allModelsResult = utils.jsonDecode(response.body)
    self.assertItemsEqual(allModelsResult[0].keys(),
      self.modelsTestData["get_response"].keys())
    self.assertItemsEqual(allModelsResult[0].keys(),
      self.modelsTestData["get_response"].keys())
    self.assertEqual(len(allModelsResult), 1)

    # Repeat the request to monitor same metric and verify that it returns the
    # same model uid instead of creating a new one
    response = self.app.post("/", utils.jsonEncode(data), headers=self.headers)

    assertions.assertSuccess(self, response, code=201)
    postResult = utils.jsonDecode(response.body)
    self.assertEqual(postResult[0]["uid"], uid)
    self.assertEqual(len(postResult), 1)
    self._checkCreateModelResult(postResult[0], data)

    # Compare http and https responses for all models
    for x in range(3):
      https_response = requests.get("https://localhost/_models",
                                    headers=self.headers,
                                    verify=False)
      http_response = requests.get("http://localhost/_models",
                                   headers=self.headers)

      self.assertEqual(http_response.status_code, 200)
      self.assertEqual(https_response.status_code, 200)

      httpsData = json.loads(https_response.text)

      try:
        self.assertIsInstance(httpsData, list)
        self.assertTrue(httpsData)
        for item in httpsData:
          self.assertIn("status", item)
          self.assertIn("last_rowid", item)
          self.assertIn("display_name", item)
          self.assertIn("uid", item)
          self.assertIn("datasource", item)

        httpData = json.loads(http_response.text)
        self.assertIsInstance(httpData, list)
        self.assertTrue(httpData)
        for item in httpData:
          self.assertIn("status", item)
          self.assertIn("last_rowid", item)
          self.assertIn("display_name", item)
          self.assertIn("uid", item)
          self.assertIn("datasource", item)

        self.assertEqual(http_response.text, https_response.text)

        break
      except AssertionError:
        time.sleep(10)

    else:
      self.fail("Unable to synchronize http and https responses.")

    # Compare http and https response for all models data
    https_response = requests.get("https://localhost/_models/data",
                                  headers=self.headers,
                                  verify=False)
    http_response = requests.get("http://localhost/_models/data",
                                 headers=self.headers)

    self.assertEqual(http_response.status_code, 200)
    self.assertEqual(https_response.status_code, 200)

    httpData = json.loads(http_response.text)
    self.assertIsInstance(httpData, dict)
    self.assertItemsEqual(httpData.keys(), ["metrics", "names"])
    self.assertItemsEqual(httpData["names"], ["timestamp",
                                              "value",
                                              "anomaly_score",
                                              "rowid"])

    httpsData = json.loads(https_response.text)
    self.assertIsInstance(httpsData, dict)
    self.assertItemsEqual(httpsData.keys(), ["metrics", "names"])
    self.assertItemsEqual(httpsData["names"], ["timestamp",
                                               "value",
                                               "anomaly_score",
                                               "rowid"])

    # delete the model that was created earlier
    response = self.app.delete("/%s" % uid, headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, response)


  @ManagedTempRepository("TestModelHandler")
  def testMonitorMetricViaModelSpec(self):
    """
      Happy path testing for the route "/_models" with new modelSpec format
    """
    modelSpec = {
      "datasource": "cloudwatch",

      "metricSpec": {
        "region": "us-west-2",
        "namespace": "AWS/EC2",
        "metric": "CPUUtilization",
        "dimensions": {
          "InstanceId": "i-12d67826"
        }
      },

      "modelParams": {
        "min": 0,  # optional
        "max": 100  # optional
      }
    }

    # create a model
    response = self.app.post("/", utils.jsonEncode(modelSpec),
                             headers=self.headers)
    assertions.assertSuccess(self, response, code=201)
    postResult = utils.jsonDecode(response.body)
    self.assertEqual(len(postResult), 1)
    self._checkCreateModelResult(postResult[0], modelSpec["metricSpec"])

    # get model that was previously created
    uid = postResult[0]["uid"]
    response = self.app.get("/%s" % uid, headers=self.headers)
    assertions.assertSuccess(self, response)
    getModelResult = utils.jsonDecode(response.body)
    self.assertItemsEqual(getModelResult[0].keys(),
      self.modelsTestData["get_response"].keys())

    # get all models in the system
    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    allModelsResult = utils.jsonDecode(response.body)
    self.assertItemsEqual(allModelsResult[0].keys(),
      self.modelsTestData["get_response"].keys())
    self.assertItemsEqual(allModelsResult[0].keys(),
      self.modelsTestData["get_response"].keys())
    self.assertEqual(len(allModelsResult), 1)

    # Repeat the request to monitor same metric and verify that it returns the
    # same model uid instead of creating a new one
    response = self.app.post("/", utils.jsonEncode(modelSpec),
                             headers=self.headers)
    assertions.assertSuccess(self, response, code=201)
    postResult = utils.jsonDecode(response.body)
    self.assertEqual(postResult[0]["uid"], uid)
    self.assertEqual(len(postResult), 1)
    self._checkCreateModelResult(postResult[0], modelSpec["metricSpec"])

    # Unmonitor the metric
    response = self.app.delete("/%s" % uid, headers=self.headers)
    assertions.assertDeleteSuccessResponse(self, response)



  @ManagedTempRepository("TestModelHandler")
  def testGetNonExistentModelUID(self):
    """
      Test for the get call with non-existent Model uid.
    """
    response = self.app.get("/f00bar", status="*", headers=self.headers)
    assertions.assertObjectNotFoundError(self, response)


  @ManagedTempRepository("TestModelHandler")
  def testDeleteNonExistentModelUID(self):
    """
      Test for the delete call with non-existent Model uid.
    """
    response = self.app.delete("/f00bar", status="*", headers=self.headers)
    assertions.assertObjectNotFoundError(self, response)


  @ManagedTempRepository("TestModelHandler")
  def testInvalidJsonModelsApi(self):
    """
      Test for the invalid json.
    """
    data = self.modelsTestData["create_data"]
    response = self.app.put("/", data, status="*", headers=self.headers)
    self.assertIn("No JSON object could be decoded", response.body)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithEmptyRegionArg(self):
    """
      Test for the missing empty datasource field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_empty_region"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithInvalidRegionKey(self):
    """
      Test for the invalid region field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_invalid_region_key"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithEmptyDatasourceArg(self):
    """
      Test for the missing empty datasource field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_empty_ds_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithInvalidDatasourceArg(self):
    """
      Test for the invalid metric field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_invalid_ds_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithEmptyMetricArg(self):
    """
      Test for the missing empty metric field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_empty_metric_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithInvalidMetricArg(self):
    """
      Test for the invalid metric field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_invalid_metric_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertBadRequest(self, response, "json")

    response = self.app.get("/", headers=self.headers)
    self.assertFalse(json.loads(response.body),
                     "Model actually created with invalid metric")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithEmptyDimensionsArg(self):
    """
      Test for the missing empty dimension field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_empty_dimension_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithInvalidDimensionsArg(self):
    """
      Test for the invalid dimension field in json.
    """
    data = utils.jsonEncode(
      self.modelsTestData["create_invalid_dimension_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertBadRequest(self, response, "json")

    response = self.app.get("/", headers=self.headers)
    self.assertFalse(json.loads(response.body),
                     "Model actually created with invalid dimension")


  @ManagedTempRepository("TestModelHandler")
  def testCreateModelWithEmptyInstanceIdArg(self):
    """
      Test for the empty dimension field in json.
    """
    data = utils.jsonEncode(self.modelsTestData["create_empty_instanceid_data"])
    response = self.app.put("/", data, status="*", headers=self.headers)
    assertions.assertInvalidArgumentsError(self, response, "json")


  @ManagedTempRepository("TestModelHandler")
  def testNoAuthHeaders(self):
    """
    Negative test for authentication guarded route.
    invoke get request without passing authentication headers
    response is validated for appropriate headers and body
    """
    response = self.app.get("/", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  @ManagedTempRepository("TestModelHandler")
  def testInvalidAuthHeaders(self):
    """
    Negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    response is validated for appropriate headers and body
    """
    invalidHeaders = getInvalidHTTPHeaders()
    response = self.app.get("/", status="*", headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)


  @ManagedTempRepository("TestModelHandler")
  def testPutMethodWithNoData(self):
    """
    Test making a PUT call with no data.
    """
    response = self.app.put("/", status="*", headers=self.headers)
    self.assertIn("Metric data is missing", response.body)
    assertions.assertBadRequest(self, response)



class MetricDataHandlerTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    """
    Setup steps for all test cases.
    Focus for these is to cover all API checks for ModelDataHandler.
    Hence, this does all setup creating metric, waiting for
    metricData across all testcases, all API call for querying metricData
    will be against single metric created in setup
    Setup Process
    1) Update conf with aws credentials, ManagedTempRepository will not
       work in this test
    2) Select test instance such that its running from longer time,
       We are using instance older than 15 days
    3) Create Metric, wait for min metricData rows to become available
       Set to 100, configurable
    4) Pick testRowId, set it lower value this will make sure to have
       Non NULL value for anomaly_score field for given row while invoking
       GET with consitions, set to 5
    5) Decide queryParams for anomalyScore, to and from timestamp
    """
    cls.headers = getDefaultHTTPHeaders(YOMP.app.config)

    # All other sevices needs AWS credentials to work
    # Set AWS credentials
    YOMP.app.config.loadConfig()

    # Select test instance such that its running from longer time
    g_logger.info("Getting long-running EC2 Instances")
    instances = aws_utils.getLongRunningEC2Instances("us-west-2",
      YOMP.app.config.get("aws", "aws_access_key_id"),
      YOMP.app.config.get("aws", "aws_secret_access_key"), 15)
    testInstance = instances[randrange(1, len(instances))]

    createModelData = {
      "region": "us-west-2",
      "namespace": "AWS/EC2",
      "datasource": "cloudwatch",
      "metric": "CPUUtilization",
      "dimensions": {
        "InstanceId": testInstance.id
      }
    }

    # Number of minimum rows
    cls.minDataRows = 100

    cls.app = TestApp(models_api.app.wsgifunc())

    # create test metric
    g_logger.info("Creating test metric; modelSpec=%s", createModelData)
    response = cls.app.put("/", utils.jsonEncode(createModelData),
     headers=cls.headers)
    postResult = utils.jsonDecode(response.body)
    maxWaitTime = 600
    waitTimeMetricData = 0
    waitAnomalyScore = 0


    # Wait for enough metric data to be available
    cls.uid = postResult[0]["uid"]
    engine = repository.engineFactory()
    with engine.connect() as conn:
      cls.metricData = [row for row
                         in repository.getMetricData(conn, cls.uid)]
    with engine.connect() as conn:
      cls.testMetric = repository.getMetric(conn, cls.uid)

    # Confirm that we have enough metricData
    g_logger.info("Waiting for metric data")
    while (len(cls.metricData) < cls.minDataRows and
           waitTimeMetricData < maxWaitTime):
      g_logger.info("not ready, waiting for metric data: got %d of %d ...",
                    len(cls.metricData), cls.minDataRows)
      time.sleep(5)
      waitTimeMetricData += 5
      with engine.connect() as conn:
        cls.metricData = [row for row
                           in repository.getMetricData(conn, cls.uid)]

    # taking lower value for testRowId, this will make sure to have
    # Non NULL value for anomaly_score field for given row
    cls.testRowId = 5

    with engine.connect() as conn:
      cls.testMetricRow = (repository.getMetricData(conn,
                                                     cls.uid,
                                                     rowid=cls.testRowId)
                          .fetchone())

    # Make sure we did not receive None etc for anomaly score
    g_logger.info("cls.testMetricRow.anomaly_score=%r",
                  cls.testMetricRow.anomaly_score)
    g_logger.info("waitAnomalyScore=%r", waitAnomalyScore)
    while (cls.testMetricRow.anomaly_score is None and
           waitAnomalyScore < maxWaitTime):
      g_logger.info("anomaly_score not ready, sleeping...")
      time.sleep(5)
      waitAnomalyScore += 5
      with engine.connect() as conn:
        cls.testMetricRow = (repository.getMetricData(conn,
                                                      cls.uid,
                                                      rowid=cls.testRowId)
                            .fetchone())

    # Decide queryParams for anomalyScore, to and from timestamp
    cls.testAnomalyScore = cls.testMetricRow.anomaly_score
    cls.testTimeStamp = cls.testMetricRow.timestamp


  @classmethod
  def tearDownClass(cls):
    try:
      engine = repository.engineFactory()
      with engine.connect() as conn:
        repository.deleteMetric(conn, cls.uid)

      with engine.connect() as conn:
        _ = repository.getMetric(conn, cls.uid)
    except ObjectNotFoundError:
      g_logger.info("Successful clean-up")
    else:
      g_logger.error("Test failed to delete metric=%s", cls.uid)


  def testGetModelDataWithModelUId(self):
    """
    test GET /metricId/data
    """
    getMetricDataResponse = self.app.get("/%s/data" % self.uid,
      headers=self.headers)
    assertions.assertSuccess(self, getMetricDataResponse)
    getMetricDataResult = utils.jsonDecode(getMetricDataResponse.body)
    self.assertIsInstance(getMetricDataResult, dict)
    self.assertItemsEqual(getMetricDataResult.keys(), ["data", "names"])
    self.assertGreater(len(getMetricDataResult["data"]), 0)


  def testGetModelDataWithModelUIdAndToTimeStamp(self):
    """
    test GET /metricId/data?to=timeStamp
    """
    getMetricDataWithToTimeStampResponse = self.app.get("/%s/data?to=%s" % \
      (self.uid, self.testTimeStamp), headers=self.headers)
    getMetricDataWithToTimeStampResult = utils.jsonDecode(
      getMetricDataWithToTimeStampResponse.body)
    g_logger.info("getMetricDataWithToTimeStampResult=%r",
                  getMetricDataWithToTimeStampResult)
    assertions.assertSuccess(self, getMetricDataWithToTimeStampResponse)
    self.assertGreater(len(getMetricDataWithToTimeStampResult["data"]), 0)
    # We wait for minimum rows to be available for givem metric
    # We are using lower value for rowId  to get Non NULL value anomaly_score
    # We get all available metric data rows, if condition is
    # not applied on DB query and hence the GET call will return all data rows
    # Asserting following will make sure that we have received result with
    # applied condition.
    # ( In this case len(metricData) would be greater than result length)
    self.assertGreater(len(self.metricData),
      len(getMetricDataWithToTimeStampResult["data"]))


  def testGetModelDataWithModelUIdAndAnomalyScore(self):
    """
    test GET /metricId/data?anomaly=testanomalyScore
    """
    getMetricDataWithAnomalyQueryResponse = self.app.get(
      "/%s/data?anomaly=%s" % (self.uid, self.testAnomalyScore),
      headers=self.headers)
    getMetricDataWithAnomalyQueryResult = utils.jsonDecode(
      getMetricDataWithAnomalyQueryResponse.body)

    assertions.assertSuccess(self, getMetricDataWithAnomalyQueryResponse)
    self.assertIsInstance(getMetricDataWithAnomalyQueryResult, dict)
    self.assertItemsEqual(getMetricDataWithAnomalyQueryResult.keys(),
     ["data", "names"])
    self.assertGreater(len(getMetricDataWithAnomalyQueryResult["data"]), 0)
    # we are parsing amomaly scores from reponse and chekcing if each of it
    # is satisfying value condition set with GET request.
    # If for some reason this parameter is not applied on DB query, we get
    # full response for this request
    # We are making sure each value for anomaly_score in result matches with
    # condition set in GET request, hence the assertion
    anomalyScores = \
      [row[2] for row in getMetricDataWithAnomalyQueryResult["data"]]
    failedScores = [a for a in anomalyScores if a < self.testAnomalyScore]
    self.assertEqual(failedScores, [])


  def testGetModelDataWithModelUIdAndFromTimeStamp(self):
    """
    test GET /metricId/data?from=timeStamp
    """
    getMetricDataWithFromTimeStampResponse = self.app.get(
      "/%s/data?from=%s" % (self.uid, self.testTimeStamp),
      headers=self.headers)
    getMetricDataWithFromTimeStampResult = utils.jsonDecode(
      getMetricDataWithFromTimeStampResponse.body)
    assertions.assertSuccess(self, getMetricDataWithFromTimeStampResponse)
    self.assertGreater(len(getMetricDataWithFromTimeStampResult["data"]), 0)
    # We wait for minimum rows to be available for givem metric
    # We are using lower value for rowId  to get Non NULL value anomaly_score
    # We get all available metric data rows, if condition is
    # not applied on DB query and hence the GET call will return all data rows
    # Asserting following will make sure that we have received result with
    # applied condition.
    # ( In this case len(metricData) would be greater than result length)
    self.assertGreater(len(self.metricData),
      len(getMetricDataWithFromTimeStampResult["data"]))


  def testGetAllModelData(self):
    """
    test GET /data
    """
    getAllMetricDataResponse = self.app.get("/%s/data" % self.uid,
      headers=self.headers)
    assertions.assertSuccess(self, getAllMetricDataResponse)
    getAllMetricDataResult = utils.jsonDecode(getAllMetricDataResponse.body)
    assertions.assertSuccess(self, getAllMetricDataResponse)
    self.assertIsInstance(getAllMetricDataResult, dict)
    self.assertItemsEqual(getAllMetricDataResult.keys(), ["data", "names"])

    # Compare http and https response
    https_response = requests.get("https://localhost/_models/%s/data"
                                  % self.uid,
                                  headers=self.headers,
                                  verify=False)

    httpsData = json.loads(https_response.text)
    self.assertIsInstance(httpsData, dict)
    self.assertItemsEqual(httpsData.keys(), ["data", "names"])
    self.assertItemsEqual(httpsData["names"], ["timestamp",
                                               "value",
                                               "anomaly_score",
                                               "rowid"])
    self.assertIsInstance(httpsData["data"], list)
    self.assertTrue(all(isinstance(row, list) and len(row) == 4
                        for row in httpsData["data"]))

    http_response = requests.get("http://localhost/_models/%s/data"
                                 % self.uid,
                                 headers=self.headers)
    httpData = json.loads(http_response.text)
    self.assertIsInstance(httpData, dict)
    self.assertItemsEqual(httpData.keys(), ["data", "names"])
    self.assertItemsEqual(httpData["names"], ["timestamp",
                                              "value",
                                              "anomaly_score",
                                              "rowid"])
    self.assertIsInstance(httpData["data"], list)
    self.assertTrue(all(isinstance(row, list) and len(row) == 4
                        for row in httpData["data"]))



if __name__ == "__main__":
  unittest.main()
