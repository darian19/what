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


import datetime
import json
import logging
import random
import socket
import string
import time
import unittest

from boto.dynamodb2.exceptions import ItemNotFound
from boto.dynamodb2.table import Table

from nta.utils.date_time_utils import epochFromNaiveUTCDatetime
from nta.utils import error_handling
from nta.utils.message_bus_connector import MessageBusConnector

from htmengine import repository
from htmengine.exceptions import MetricAlreadyMonitored
from htmengine.repository.queries import MetricStatus
from htmengine.test_utils.test_case_base import TestCaseBase
from htmengine.adapters.datasource import createDatasourceAdapter

import taurus.engine
from taurus.engine.exceptions import ObjectNotFoundError
from taurus.engine import logging_support
from taurus.engine.runtime.dynamodb.definitions import (
    InstanceDataHourlyDynamoDBDefinition,
    MetricDynamoDBDefinition,
    MetricDataDynamoDBDefinition,
    MetricTweetsDynamoDBDefinition)
from taurus.engine.runtime.dynamodb.dynamodb_service import DynamoDBService

LOGGER = logging.getLogger(__name__)

# Decorator for retrying dynamodb operations that failed due to transient error
_RETRY_ON_ITEM_NOT_FOUND_DYNAMODB_ERROR = error_handling.retry(
  timeoutSec=300, initialRetryDelaySec=0.5, maxRetryDelaySec=10,
  retryExceptions=(ItemNotFound,),
  logger=LOGGER
)



class DynamoDBServiceTest(TestCaseBase):


  @classmethod
  def setUpClass(cls):
    cls.engine = repository.engineFactory(taurus.engine.config)


  def setUp(self):
    self.config = taurus.engine.config
    self.plaintextPort = self.config.getint("metric_listener", "plaintext_port")


  @staticmethod
  def _deleteMetric(metricName):
    adapter = createDatasourceAdapter("custom")
    adapter.deleteMetricByName(metricName)


  @staticmethod
  def _deleteModel(metricId):
    adapter = createDatasourceAdapter("custom")
    adapter.unmonitorMetric(metricId)


  def _createModel(self, nativeMetric):
    adapter = createDatasourceAdapter("custom")
    try:
      metricId = adapter.monitorMetric(nativeMetric)
    except MetricAlreadyMonitored as e:
      metricId = e.uid

    engine = repository.engineFactory(config=self.config)

    with engine.begin() as conn:
      return repository.getMetric(conn, metricId)

  def testPathwayToDynamoDB(self):
    """ Test metric data pathway to dynamodb
    """

    metricName = "TEST." + "".join(random.sample(string.ascii_letters, 16))

    nativeMetric = {
      "modelParams": {
        "minResolution": 0.2,
        "min": 0.0,
        "max": 10000.0,
      },
      "datasource": "custom",
      "metricSpec": {
        "metric": metricName,
        "resource": "Test",
        "userInfo": {
          "symbol": "TEST",
          "metricType": "TwitterVolume",
          "metricTypeName": "Twitter Volume",
        }
      }
    }
    metricName = nativeMetric["metricSpec"]["metric"]
    instanceName = nativeMetric["metricSpec"]["resource"]
    userInfo = nativeMetric["metricSpec"]["userInfo"]

    now = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    data = [
      (5000.0, now - datetime.timedelta(minutes=10)),
      (6000.0, now - datetime.timedelta(minutes=5)),
      (7000.0, now),
    ]

    # We'll be explicitly deleting the metric below, but we need to add a
    # cleanup step that runs in case there is some other failure that prevents
    # that part of the test from being reached.

    def gracefulDelete():
      try:
        self._deleteMetric(metricName)
      except ObjectNotFoundError:
        pass

    self.addCleanup(gracefulDelete)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for metricValue, ts in data:
      sock.sendall("%s %r %s\n" % (metricName,
                                   metricValue,
                                   epochFromNaiveUTCDatetime(ts)))

    self.gracefullyCloseSocket(sock)

    uid = self.checkMetricCreated(metricName)

    # Save the uid for later
    LOGGER.info("Metric %s has uid: %s", metricName, uid)

    # Send model creation request
    model = self._createModel(nativeMetric)
    parameters = json.loads(model.parameters)
    self.assertEqual(parameters["metricSpec"]["userInfo"], userInfo)

    for _ in xrange(60):
      with self.engine.begin() as conn:
        metric = repository.getMetric(conn, uid)

      if metric.status == MetricStatus.ACTIVE:
        break
      LOGGER.info("Model=%s not ready. Sleeping 1 second...", uid)
      time.sleep(1)
    else:
      self.fail("Model results not available within 5 minutes")

    # Check that the data all got processed
    self.checkModelResultsSize(uid, 3)

    # Now check that the data was published to dynamodb...
    dynamodb = DynamoDBService.connectDynamoDB()

    metricTable = Table(MetricDynamoDBDefinition().tableName,
                        connection=dynamodb)
    metricItem = metricTable.lookup(uid)
    self.assertEqual(metricItem["uid"], uid)
    self.assertEqual(metricItem["name"], metricName)
    self.assertEqual(metricItem["metricType"], "TwitterVolume")
    self.assertEqual(metricItem["metricTypeName"], "Twitter Volume")
    self.assertEqual(metricItem["symbol"], "TEST")

    metricDataTable = Table(MetricDataDynamoDBDefinition().tableName,
                            connection=dynamodb)
    instanceDataAnomalyScores = {}
    for metricValue, ts in data:
      for _ in xrange(60):
        try:
          metricDataItem = metricDataTable.lookup(uid, ts.isoformat())
          break
        except ItemNotFound as exc:
          time.sleep(1)
          continue
      else:
        self.fail("Metric data not found within 60 seconds")
      # There is no server-side cleanup for metric data, so remove it here for
      # now to avoid accumulating test data
      self.addCleanup(metricDataItem.delete)
      self.assertEqual(metricValue, metricDataItem["metric_value"])
      dt = datetime.datetime.strptime(metricDataItem["timestamp"],
                                      "%Y-%m-%dT%H:%M:%S")
      self.assertEqual(ts, dt)
      ts = ts.replace(minute=0, second=0, microsecond=0)
      date = ts.strftime("%Y-%m-%d")
      hour = ts.strftime("%H")
      key = (date, hour)
      maxVal = instanceDataAnomalyScores.get(key, 0.0)
      instanceDataAnomalyScores[key] = max(
          maxVal, metricDataItem["anomaly_score"])

    # And check that the aggregated instance data is updated
    instanceDataHourlyTable = Table(
        InstanceDataHourlyDynamoDBDefinition().tableName, connection=dynamodb)
    for key, anomalyScore in instanceDataAnomalyScores.iteritems():
      date, hour = key
      instanceDataHourlyItem = _RETRY_ON_ITEM_NOT_FOUND_DYNAMODB_ERROR(
        instanceDataHourlyTable.lookup
      )(instanceName, "%sT%s" % (date, hour))
      self.addCleanup(instanceDataHourlyItem.delete)
      self.assertAlmostEqual(
          anomalyScore,
          float(instanceDataHourlyItem["anomaly_score"]["TwitterVolume"]))
      self.assertEqual(date, instanceDataHourlyItem["date"])
      self.assertEqual(hour, instanceDataHourlyItem["hour"])

    # Now send some twitter data and validate that it made it to dynamodb

    twitterData = [
      {
        "metric_name": metricName,
        "tweet_uid": uid,
        "created_at": "2015-02-19T19:43:24.870109",
        "agg_ts": "2015-02-19T19:43:24.870118",
        "text": "Tweet text",
        "userid": "10",
        "username": "Tweet username",
        "retweet_count": "0"
      }
    ]

    with MessageBusConnector() as messageBus:
      messageBus.publishExg(
        exchange=self.config.get("non_metric_data", "exchange_name"),
        routingKey=(
          self.config.get("non_metric_data", "exchange_name") + ".twitter"),
        body=json.dumps(twitterData)
      )

    metricTweetsTable = Table(MetricTweetsDynamoDBDefinition().tableName,
                              connection=dynamodb)
    for _ in xrange(60):
      try:
        metricTweetItem = metricTweetsTable.lookup("-".join((metricName, uid)),
          "2015-02-19T19:43:24.870118"
        )
        break
      except ItemNotFound as exc:
        time.sleep(1)
        continue
    else:
      self.fail("Metric tweet item not found within 60 seconds")

    # There is no server-side cleanup for tweet data, so remove it here for
    # now to avoid accumulating test data
    self.addCleanup(metricTweetItem.delete)
    self.assertEqual(metricTweetItem["username"], twitterData[0]["username"])
    self.assertEqual(metricTweetItem["tweet_uid"], twitterData[0]["tweet_uid"])
    self.assertEqual(metricTweetItem["created_at"], twitterData[0]["created_at"])
    self.assertEqual(metricTweetItem["agg_ts"], twitterData[0]["agg_ts"])
    self.assertEqual(metricTweetItem["text"], twitterData[0]["text"])
    self.assertEqual(metricTweetItem["userid"], twitterData[0]["userid"])
    self.assertEqual(metricTweetItem["username"], twitterData[0]["username"])
    self.assertEqual(metricTweetItem["retweet_count"], twitterData[0]["retweet_count"])

    queryResult = metricTweetsTable.query_2(
      metric_name__eq=metricName,
      agg_ts__eq=twitterData[0]["agg_ts"],
      index="taurus.metric_data-metric_name_index")
    queriedMetricTweetItem = next(queryResult)

    self.assertEqual(queriedMetricTweetItem["username"], twitterData[0]["username"])
    self.assertEqual(queriedMetricTweetItem["tweet_uid"], twitterData[0]["tweet_uid"])
    self.assertEqual(queriedMetricTweetItem["created_at"], twitterData[0]["created_at"])
    self.assertEqual(queriedMetricTweetItem["agg_ts"], twitterData[0]["agg_ts"])
    self.assertEqual(queriedMetricTweetItem["text"], twitterData[0]["text"])
    self.assertEqual(queriedMetricTweetItem["userid"], twitterData[0]["userid"])
    self.assertEqual(queriedMetricTweetItem["username"], twitterData[0]["username"])
    self.assertEqual(queriedMetricTweetItem["retweet_count"], twitterData[0]["retweet_count"])

    # Delete metric and ensure metric is deleted from dynamodb, too
    self._deleteMetric(metricName)

    for _ in xrange(60):
      time.sleep(1)
      try:
        metricItem = metricTable.lookup(uid)
      except ItemNotFound as err:
        break
    else:
      self.fail("Metric not deleted from dynamodb")



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



if __name__ == "__main__":
  unittest.main()
