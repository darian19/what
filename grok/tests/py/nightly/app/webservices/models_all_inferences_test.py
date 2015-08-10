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
import sys
from random import randrange
from datetime import datetime
from time import sleep, time, strftime, localtime
import unittest

from paste.fixture import TestApp
from sqlalchemy import sql

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

import YOMP.app
from YOMP.app.webservices import models_api
from YOMP.app import utils
from YOMP.app import repository
from YOMP.app.repository import schema
from YOMP.test_utils.app.webservices import getDefaultHTTPHeaders
from YOMP.test_utils.app.webservices import (
  webservices_assertions as assertions
)
from YOMP.test_utils import aws_utils as aws


# NOTE: The aws credentials in application.conf initially have empty
#  string values, expecting to be set via the /YOMP/welcome screen. Since this
#  test doesn't involve YOMP-api, we will get the credentials from environment
#  variables as that the test environments are expected to set and apply them
#  config overrides.
@ConfigAttributePatch(
  YOMP.app.config.CONFIG_NAME,
  YOMP.app.config.baseConfigDir,
  (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
   ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"]),)
)
class TestModelAllInferences(unittest.TestCase):
  """
    Test to check if last_rowid model inferences are being created properly.
    How this test works : After the metrics are created, wait for 15 minutes
    for cloudwatch data to come in. Check the last_rowid for each metric
    and then wait until the model inference for the last_rowid for each metric
    is calculated.

    The test exits with non-zero status if it takes more than 20 minutes to create
    the initial models or if inferences for last_rowid takes more than 2 hours to
    be calculated.
  """


  maxDiff = None
  assert len(os.environ["AWS_ACCESS_KEY_ID"]) > 0
  assert len(os.environ["AWS_SECRET_ACCESS_KEY"]) > 0


  def setUp(self):
    self.app = TestApp(models_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.data = self.createTestData()

  def createTestData(self):
    print "Searching for instances in us-west-2 that are running since 15 days or more."
    instances = aws.getLongRunningEC2Instances("us-west-2", os.environ["AWS_ACCESS_KEY_ID"],
        os.environ["AWS_SECRET_ACCESS_KEY"], 15)
    print "Found %s instance(s)." % len(instances)
    metrics = ["CPUUtilization", "DiskReadBytes", "DiskWriteBytes", "NetworkIn", "NetworkOut"]
    testData = []
    for instance in instances:
      for metric in metrics:
        model = {
             "region": "us-west-2",
             "namespace": "AWS/EC2",
             "datasource": "cloudwatch",
             "metric": metric,
             "dimensions": {
               "InstanceId": instance.id
          }
        }
        testData.append(model)
    return testData


  def testModelInferencesLifeCycle(self):
    startTime = time()
    for model in sorted(self.data):
      #create a model; post is forwarded to put
      print "Creating metric for %s : " % model
      response = self.app.put("/", json.dumps(model),
          headers=self.headers)
      assertions.assertSuccess(self, response, code=201)

    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    getAllModelsResult = utils.jsonDecode(response.body)
    totalMetricCount = len(getAllModelsResult)
    self.assertEqual(totalMetricCount, len(self.data))

    #Get the uids of all the metrics created.
    uids = [metric['uid'] for metric in getAllModelsResult]

    while True:
      with repository.engineFactory().connect() as conn:
        initialModelCount = conn.execute(
          sql.select([sql.func.count()], from_obj=schema.metric_data)
          .where(schema.metric_data.c.rowid == 1)).scalar()
      if initialModelCount == totalMetricCount:
        print "Done creating all the initial models."
        break

      # Exit the test with some non-zero status if the test has run for more
      # than 20 minutes to just create the initial models.
      # Should not take more than that.

      currentElapsedTime = (time() - startTime) / 60
      print "Current elapsed time %s" % currentElapsedTime
      if currentElapsedTime > 20:
        print "More than 20 minutes has elapsed. Timing out."
        sys.exit(42)
      print "%s initial models created." % initialModelCount
      print "Creating initial models for rest of the %s metrics" \
        "..." % (totalMetricCount - initialModelCount)
      sleep(60)


    #Sleep for a long time.
    minutes = 15
    print "Sleeping for %s minutes to let things settled down." % minutes
    while minutes > 0:
      print "Resume in %s minutes." % minutes
      minutes -= 1
      sleep(60)

    modelCreationDuration = (time() - startTime) / 60

    with repository.engineFactory().connect() as conn:
      lastRowIds = {uid: repository.getMetric(conn, uid).last_rowid
                    for uid in uids}
    modelInferenceWithNonNullAnomalyScore = []
    modelIds = lastRowIds.keys()
    while True:
      print set(modelInferenceWithNonNullAnomalyScore)
      if len(modelIds) == len(set(modelInferenceWithNonNullAnomalyScore)):
        print "Model inferences created for last_rowids for all the models."
        break
      for uid in modelIds:
        with repository.engineFactory().connect() as conn:
          anomalyNullCount = conn.execute(
            sql.select([sql.func.count()], from_obj=schema.metric_data)
            .where(schema.metric_data.c.rowid == lastRowIds[uid])
            .where(schema.metric_data.c.uid == uid)
            .where(schema.metric_data.c.anomaly_score == None)).scalar()
        print "Model (%s) - Last Row ID (%s) : %s" \
          % (uid, lastRowIds[uid], anomalyNullCount)
        if anomalyNullCount == 0:
          modelInferenceWithNonNullAnomalyScore.append(uid)

      # Exit the test with some non-zero status if the test has run for more
      # than 2 hours

      currentElapsedTime = (time() - startTime) / 60
      print "Current elapsed time %s" % currentElapsedTime
      if currentElapsedTime > 120:
        print "More than 2 hours has elapsed. Timing out."
        sys.exit(42)
      print "Going back to sleep for 60s..."
      sleep(60)

    self.assertEqual(anomalyNullCount, 0)
    timeToCalculateAllInferences = time()


    def getMetricDataWithRowID(metricDataList, rowid):
      '''
        Helper method to get the metric data of the nth row for a certain uid
      '''
      for metricData in metricDataList:
        if metricData[3] == rowid:
          return metricData


    def testMetricDataForRandomRowID(uid):
      '''
        This tests if the metric data returned by the GET call :
          _models/<uid>/data
        has anomaly_score consistent with what is there in the actual
        database by asserting it against a dao.MetricData.get() call
        It repeats the process for 5 random sample rows for each uid
        in the database.

        Algorithm :
        - Query the MetricDataHandler GET call for a certain uid
        - Check if response is OK
        - Find the last row id for the uid
        - Select a random row between 1 and last row id
        - Find the anomaly score for that row id
        - Assert on the anomaly score
      '''
      response = self.app.get("/%s/data" %uid, headers=self.headers)
      assertions.assertSuccess(self, response)
      getAllModelsResult = utils.jsonDecode(response.body)
      with repository.engineFactory().connect() as conn:
        lastRowID = repository.getMetric(conn, uid).last_rowid
      for _ in range(5):
        randomRowID = randrange(1, lastRowID)
        with repository.engineFactory().connect() as conn:
          singleMetricData = repository.getMetricData(
            conn,
            uid,
            rowid=randomRowID).first()
        metricData = getMetricDataWithRowID(getAllModelsResult['data'],
          randomRowID)
        self.assertEqual(metricData[2], singleMetricData.anomaly_score)
        self.assertEqual(datetime.strptime(metricData[0],
          '%Y-%m-%d %H:%M:%S'), singleMetricData.timestamp)

    map(testMetricDataForRandomRowID, uids)


    def testMetricDataAnomalyAsQueryParams(uid):
      '''
        This test makes MetricDataHandler GET calls with anomaly param :
          _models/<uid>/data?anomaly=<>
      '''
      queryString = ("SELECT * FROM metric_data WHERE uid='%s' "
                     "   and abs(anomaly_score - 0) > 1e-5 LIMIT 1") % uid
      with repository.engineFactory().connect() as conn:
        sampleMetricData = conn.execute(queryString).first()
      anomalyScore = sampleMetricData.anomaly_score
      response = self.app.get("/%s/data?anomaly=%s"
        % (uid, anomalyScore), headers=self.headers)
      assertions.assertSuccess(self, response)
      getAllModelsResult = utils.jsonDecode(response.body)
      for metricData in getAllModelsResult['data']:
        self.assertGreaterEqual(metricData[2], anomalyScore)

    map(testMetricDataAnomalyAsQueryParams, uids)


    def testMetricDataTimeStampQueryParams(uid):
      '''
        This test makes MetricDataHandler GET calls with from and to params :
          _models/<uid>/data?from=<>&to=<>
      '''
      with repository.engineFactory().connect() as conn:
        firstMetricData = conn.execute(
          sql.select([schema.metric_data])
          .where(schema.metric_data.c.uid == uid)
          .order_by(sql.expression.asc(schema.metric_data.c.timestamp))
          .limit(1)).fetchall()

        lastMetricData = conn.execute(
          sql.select([schema.metric_data])
          .where(schema.metric_data.c.uid == uid)
          .order_by(sql.expression.desc(schema.metric_data.c.timestamp))
          .limit(1)).fetchall()
      firstTimeStamp = firstMetricData[0].timestamp
      lastTimeStamp = lastMetricData[0].timestamp
      response = self.app.get("/%s/data?from=%s&to=%s"
        % (uid, firstTimeStamp, lastTimeStamp), headers=self.headers)
      assertions.assertSuccess(self, response)
      getAllModelsResult = utils.jsonDecode(response.body)
      for metricData in getAllModelsResult['data']:
        self.assertGreaterEqual(datetime.strptime(metricData[0],
          '%Y-%m-%d %H:%M:%S'), firstTimeStamp)
        self.assertLessEqual(datetime.strptime(metricData[0],
          '%Y-%m-%d %H:%M:%S'), lastTimeStamp)

    map(testMetricDataTimeStampQueryParams, uids)


    def testMetricDataQueryParams(uid):
      '''
        This test makes MetricDataHandler GET calls with various params :
          _models/<uid>/data?from=<>&to=<>&anomaly=<>
      '''
      with repository.engineFactory().connect() as conn:
        firstMetricData = conn.execute(
          "SELECT * FROM `metric_data` WHERE `uid`='%s' "
          "and abs(`anomaly_score` - 0) > 1e-5 "
          "ORDER BY `timestamp` ASC LIMIT 1" % uid).fetchall()
        lastMetricData = conn.execute(
          "SELECT * FROM `metric_data` WHERE `uid`='%s' "
          "and abs(`anomaly_score` - 0) > 1e-5 "
          "ORDER BY `timestamp` DESC LIMIT 1" % uid).fetchall()
      firstTimeStamp = firstMetricData[0].timestamp
      lastTimeStamp = lastMetricData[0].timestamp
      anomalyScore = firstMetricData[0].anomaly_score
      response = self.app.get("/%s/data?from=%s&to=%s&anomaly=%s"
        % (uid, firstTimeStamp, lastTimeStamp, anomalyScore),
        headers=self.headers)
      assertions.assertSuccess(self, response)
      getAllModelsResult = utils.jsonDecode(response.body)
      for metricData in getAllModelsResult['data']:
        self.assertGreaterEqual(metricData[2], anomalyScore)
        self.assertGreaterEqual(datetime.strptime(metricData[0],
          '%Y-%m-%d %H:%M:%S'), firstTimeStamp)
        self.assertLessEqual(datetime.strptime(metricData[0],
          '%Y-%m-%d %H:%M:%S'), lastTimeStamp)

    map(testMetricDataQueryParams, uids)


    endTime = (time() - startTime) / 60

    print "Test started at        : %s" % \
          strftime('%Y-%m-%d %H:%M:%S', localtime(startTime))
    print "Test finished at       : %s" % \
          strftime('%Y-%m-%d %H:%M:%S', localtime(endTime))
    print "Total metric count     : %s" % totalMetricCount
    print "Initial models created : %s" % initialModelCount
    print "Approximate time taken to create inital models : %s minutes" \
      % modelCreationDuration
    print "Approximate time taken to calculate all inferences : %s minutes" \
      % ((timeToCalculateAllInferences - startTime) / 60)
    print "Approximate time taken for all the tests to finish : %s minutes" \
      % ((time() - startTime) / 60)


if __name__ == '__main__':
  unittest.main()
