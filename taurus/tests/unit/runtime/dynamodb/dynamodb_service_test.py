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
Unit tests for taurus.engine.runtime.dynamodb.dynamodb_runtime
"""

from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
import json
import time

from mock import ANY, MagicMock, Mock, patch
import unittest

from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.exceptions import ResourceNotFoundException
from boto.dynamodb2.table import BatchTable

from nta.utils import amqp
from nta.utils.date_time_utils import epochFromNaiveUTCDatetime

from htmengine.runtime.anomaly_service import AnomalyService

import taurus.engine
from taurus.engine import logging_support
from taurus.engine.runtime.dynamodb import dynamodb_service
from taurus.engine.runtime.dynamodb.dynamodb_service import DynamoDBService
from taurus.engine.runtime.dynamodb.definitions.dynamodbdefinition import (
  DynamoDBDefinition)
from taurus.engine.runtime.dynamodb.definitions.\
    instance_data_hourly_dynamodbdefinition import (
        InstanceDataHourlyDynamoDBDefinition)



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



class DynamoTableTemplate(dynamodb_service.Table):
  table_name = Mock()



def _gracefulCreateTableMock(definition):
  """ Mock for DynamoDBService._gracefulCreateTable
  """

  batchTableMock = MagicMock(
    spec_set=BatchTable,
    put_item=Mock(spec_set=BatchTable.put_item))
  batchTableMock.__enter__ = Mock(return_value=batchTableMock)
  batchTableMock.__exit__ = Mock(return_value=False)

  return Mock(
    spec_set=DynamoTableTemplate,
    table_name=definition.tableName,
    batch_write=MagicMock(
      spec_set="boto.dynamodb2.table.batch_write",
      return_value=batchTableMock
    )
  )



@patch.object(DynamoDBService, "_gracefulCreateTable",
              side_effect=_gracefulCreateTableMock,
              spec_set=DynamoDBService._gracefulCreateTable)
@patch.object(DynamoDBService, "connectDynamoDB",
              spec_set=DynamoDBService.connectDynamoDB)
class DynamoDBServiceTestCase(unittest.TestCase):

  def testDynamoDBServiceInit(self, connectDynamoDB, _gracefulCreateTable):
    service = DynamoDBService()
    self.assertTrue(hasattr(service, "run"))
    self.assertTrue(connectDynamoDB.called, "Service did not attempt to "
      "authenticate with DynamoDB API during initialization")
    self.assertTrue(_gracefulCreateTable.called, "Service did not attempt to "
      "create any dynamodb tables")
    for callArgs, _ in _gracefulCreateTable.call_args_list:
      self.assertIsInstance(callArgs[0], DynamoDBDefinition, "Service "
        "attempted to create a table using something that isn't a subclass of "
        "DynamoDBDefinition")


  @patch("taurus.engine.runtime.dynamodb.dynamodb_service.amqp."
         "synchronous_amqp_client.SynchronousAmqpClient",
         autospec=True)
  def testDynamoDBServiceRun(self, amqpClientClassMock, connectDynamoDB,
      _gracefulCreateTable):
    """ Very basic test to validate that the service follows AMQP protocol.

    Upon `run()`, it should:

    1. Connecto to RabbitMQ
    2. Open a channel
    3. Declare two exchanges; one for model results, and one for non-metric
      data
    4. Declare a durable "dynamodb" queue
    5. Bind the "dynamodb" queue to the two exchanges
    6. Start consuming.
    """

    amqpClientMock = MagicMock(
        spec_set=(
         dynamodb_service.amqp.synchronous_amqp_client.SynchronousAmqpClient))
    amqpClientMock.__enter__.return_value = amqpClientMock

    amqpClientClassMock.return_value = amqpClientMock

    DynamoDBService().run()

    self.assertTrue(amqpClientClassMock.called,
                    "Service did not connect to rabbitmq")

    self.assertTrue(amqpClientMock.declareExchange.called)

    amqpClientMock.declareExchange.assert_any_call(
      durable=True,
      exchangeType="fanout",
      exchange=taurus.engine.config.get("metric_streamer", "results_exchange_name"))

    amqpClientMock.declareExchange.assert_any_call(
      durable=True,
      exchangeType="topic",
      exchange=taurus.engine.config.get("non_metric_data", "exchange_name"))

    amqpClientMock.declareQueue.assert_called_once_with(ANY, durable=True)

    amqpClientMock.bindQueue.assert_any_call(
      queue=amqpClientMock.declareQueue.return_value.queue,
      exchange=taurus.engine.config.get("metric_streamer", "results_exchange_name"),
      routingKey="")

    amqpClientMock.bindQueue.assert_any_call(
      exchange=taurus.engine.config.get("non_metric_data", "exchange_name"),
      queue=amqpClientMock.declareQueue.return_value.queue,
      routingKey="#")

    self.assertTrue(amqpClientMock.readEvents.called)



  @patch.object(
    AnomalyService, "deserializeModelResult",
    spec_set=AnomalyService.deserializeModelResult)
  @patch("taurus.engine.runtime.dynamodb.dynamodb_service.amqp",
         autospec=True)
  def testMessageHandlerRoutesMetricDataToDynamoDB(
      self, _amqpUtilsMock,
      deserializeModelResult, connectDynamoDB, _gracefulCreateTable):
    """ Given a batch of model inference results, send the appropriate data to
    DynamoDB tables according to design in an environment where both rabbitmq
    and dynamodb are mocked out
    """

    # We're going to mostly mock out all of the arguments to
    # DynamoDBService.messageHandler() since it is normally called by amqp lib.
    # Then simulate the process of handling an inbound batch of model inference
    # results and assert that the appropriate put_item() calls are made at the
    # other end.
    message = amqp.messages.ConsumerMessage(
      body=Mock(),
      properties=Mock(headers=dict()),
      methodInfo=amqp.messages.MessageDeliveryInfo(consumerTag=Mock(),
                                                   deliveryTag=Mock(),
                                                   redelivered=False,
                                                   exchange=Mock(),
                                                   routingKey=""),
      ackImpl=Mock(),
      nackImpl=Mock())

    # We will have to bypass the normal serialize/deserialize phases to avoid
    # dependency on sqlalchemy rowproxy.  Instead, we'll just mock out the
    # AnomalyService.deserializeModelResult() call, returning an object that
    # approximates a batch of model inference results as much as possible

    now = int(time.time())

    resultRow = dict(
      rowid=4790,
      ts=now,
      value=9305.0,
      rawAnomaly=0.775,
      anomaly=0.999840891
    )

    metricId = "3b035a5916994f2bb950f5717138f94b"

    deserializeModelResult.return_value = dict(
      metric=dict(
        uid=metricId,
        name="XIGNITE.AGN.VOLUME",
        description="XIGNITE.AGN.VOLUME",
        resource="Resource-of-XIGNITE.AGN.VOLUME",
        location = "",
        datasource = "custom",
        spec=dict(
          userInfo=dict(
            symbol="AGN",
            metricType="StockVolume",
            metricTypeName="Stock Volume"
          )
        )
      ),

      results=[resultRow]
    )

    service = DynamoDBService()
    service.messageHandler(message)

    deserializeModelResult.assert_called_once_with(message.body)

    mockMetricDataPutItem = (
      service._metric_data.batch_write.return_value.__enter__
      .return_value.put_item)
    data = dynamodb_service.convertInferenceResultRowToMetricDataItem(
      metricId, resultRow)
    mockMetricDataPutItem.assert_called_once_with(data=data._asdict(),
                                                  overwrite=True)

    self.assertFalse(service._metric_tweets.batch_write.called)


    # Make sure that a model command result doesn't get mistaken for an
    # inference result batch
    deserializeModelResult.return_value = Mock()
    message.properties = Mock(headers=dict(dataType="model-cmd-result"))
    message.body = Mock()
    service = DynamoDBService()
    with patch.object(service, "_handleModelCommandResult",
                      spec_set=service._handleModelCommandResult):
      service.messageHandler(message)
      service._handleModelCommandResult.assert_called_once_with(message.body)


  @patch.object(AnomalyService, "deserializeModelResult",
                spec_set=AnomalyService.deserializeModelResult)
  @patch("taurus.engine.runtime.dynamodb.dynamodb_service.amqp",
         autospec=True)
  def testModelResultHandlerSkipsStaleBatch(
      self, _amqpUtilsMock,
      deserializeModelResult, connectDynamoDB, _gracefulCreateTable):
    """ Given a stale batch of model inference results, verify that it isn't
    saved to DynamoDB
    """

    # We're going to mostly mock out all of the arguments to
    # DynamoDBService.messageHandler() since it is normally called by amqp lib.
    # Then simulate the process of handling an inbound batch of model inference
    # results and assert that the appropriate put_item() calls are made at the
    # other end.

    message = amqp.messages.ConsumerMessage(
      body=Mock(),
      properties=Mock(headers=dict()),
      methodInfo=amqp.messages.MessageDeliveryInfo(consumerTag=Mock(),
                                                   deliveryTag=Mock(),
                                                   redelivered=False,
                                                   exchange=Mock(),
                                                   routingKey=""),
      ackImpl=Mock(),
      nackImpl=Mock())

    # We will have to bypass the normal serialize/deserialize phases to avoid
    # dependency on sqlalchemy rowproxy.  Instead, we'll just mock out the
    # AnomalyService.deserializeModelResult() call, returning an object that
    # approximates a batch of model inference results as much as possible

    ts = epochFromNaiveUTCDatetime(
      datetime.utcnow().replace(microsecond=0) -
      timedelta(days=DynamoDBService._FRESH_DATA_THRESHOLD_DAYS + 1))

    resultRow = dict(
      rowid=4790,
      ts=ts,
      value=9305.0,
      rawAnomaly=0.775,
      anomaly=0.999840891
    )

    metricId = "3b035a5916994f2bb950f5717138f94b"

    deserializeModelResult.return_value = dict(
      metric=dict(
        uid=metricId,
        name="XIGNITE.AGN.VOLUME",
        description="XIGNITE.AGN.VOLUME",
        resource="Resource-of-XIGNITE.AGN.VOLUME",
        location = "",
        datasource = "custom",
        spec=dict(
          userInfo=dict(
            symbol="AGN",
            metricType="StockVolume",
            metricTypeName="Stock Volume"
          )
        )
      ),

      results=[resultRow]
    )

    service = DynamoDBService()
    publishMetricDataPatch = patch.object(
      service, "_publishMetricData",
      spec_set=service._publishMetricData)
    publishInstancePatch = patch.object(
      service, "_publishInstanceDataHourly",
      spec_set=service._publishInstanceDataHourly)
    with publishMetricDataPatch as publishMetricDataMock, \
        publishInstancePatch as publishInstanceMock:
      service.messageHandler(message)

      deserializeModelResult.assert_called_once_with(message.body)
      self.assertEqual(publishMetricDataMock.call_count, 0)
      self.assertEqual(publishInstanceMock.call_count, 0)


  #zzz
  @patch("taurus.engine.runtime.dynamodb.dynamodb_service.amqp",
         autospec=True)
  def testMessageHandlerRoutesTweetDataToDynamoDB(
      self, _amqpUtilsMock,
      connectDynamoDB, _gracefulCreateTable):
    """ Simple test for twitter interface
    """

##    channel = Mock()
##    method = Mock(routing_key="taurus.data.non-metric.twitter")
##    properties = Mock()

    tweetData = [
      {
        "metric_name": "Metric Name",
        "tweet_uid": "3b035a5916994f2bb950f5717138f94b",
        "created_at": "2015-02-19T19:43:24.870109",
        "agg_ts": "2015-02-19T19:43:24.870118",
        "text": "Tweet text",
        "userid": "10",
        "username": "Tweet username",
        "retweet_count": "0"
      }
    ]

    message = amqp.messages.ConsumerMessage(
      body=json.dumps(tweetData),
      properties=Mock(),
      methodInfo=amqp.messages.MessageDeliveryInfo(
        consumerTag=Mock(),
        deliveryTag=Mock(),
        redelivered=False,
        exchange=Mock(),
        routingKey="taurus.data.non-metric.twitter"),
      ackImpl=Mock(),
      nackImpl=Mock())

    service = DynamoDBService()
    service.messageHandler(message)

    (service
     ._metric_tweets
     .batch_write
     .return_value
     .__enter__
     .return_value
     .put_item
     .assert_called_once_with(
      data=OrderedDict(
        [
          ("metric_name_tweet_uid",
           "Metric Name-3b035a5916994f2bb950f5717138f94b"),
          ("metric_name", "Metric Name"),
          ("tweet_uid", "3b035a5916994f2bb950f5717138f94b"),
          ("created_at", "2015-02-19T19:43:24.870109"),
          ("agg_ts", "2015-02-19T19:43:24.870118"),
          ("text", "Tweet text"),
          ("userid", "10"),
          ("username", "Tweet username"),
          ("retweet_count", "0")
        ]
      ),
      overwrite=True))


  def testPublishMetricDataWithDuplicateKeys(self, connectDynamoDB,
                                             _gracefulCreateTable):
    """ Test for elimination of rows with duplicate keys by _publishMetricData
    """
    metricId = "3b035a5916994f2bb950f5717138f94b"

    rowTemplate = dict(
      rowid=99,
      ts=epochFromNaiveUTCDatetime(datetime(2015, 3, 20, 0, 46, 28)),
      value=10305.0,
      rawAnomaly=0.275,
      anomaly=0.999840891
    )

    row1 = dict(rowTemplate)
    row2 = dict(rowTemplate)
    row2["rowid"] = row1["rowid"] + 1
    rows = [row1, row2]

    service = DynamoDBService()

    service._publishMetricData(metricId, rows)

    data = dynamodb_service.convertInferenceResultRowToMetricDataItem(metricId,
                                                                      row1)
    mockPutItem = (service._metric_data.batch_write.return_value.__enter__
                   .return_value.put_item)
    mockPutItem.assert_called_once_with(data=data._asdict(), overwrite=True)


  def testPublishInstanceDataHourly(self, connectDynamoDB,
                                    _gracefulCreateTable):
    connectionMock = Mock(spec_set=DynamoDBConnection)
    connectionMock.update_item.side_effect = ResourceNotFoundException(
        400, "item not found")
    connectDynamoDB.return_value = connectionMock
    tableName = InstanceDataHourlyDynamoDBDefinition().tableName
    instanceName = "testName"
    condition = "attribute_not_exists(instance_id)"
    rows = [
        dict(
            rowid=99,
            ts=epochFromNaiveUTCDatetime(datetime(2015, 2, 20, 0, 46, 28)),
            value=10305.0,
            rawAnomaly=0.275,
            anomaly=0.999840891
        ),
        dict(
            rowid=100,
            ts=epochFromNaiveUTCDatetime(datetime(2015, 2, 20, 0, 51, 28)),
            value=9305.0,
            rawAnomaly=0.975,
            anomaly=0.999990891
        ),
        dict(
            rowid=101,
            ts=epochFromNaiveUTCDatetime(datetime(2015, 2, 20, 0, 56, 20)),
            value=6111.0,
            rawAnomaly=0.775,
            anomaly=0.999940891
        ),
        dict(
            rowid=102,
            ts=epochFromNaiveUTCDatetime(datetime(2015, 2, 20, 1, 1, 38)),
            value=7092.0,
            rawAnomaly=0.775,
            anomaly=0.999640891
        )
    ]

    service = DynamoDBService()

    # Run the function under test
    service._publishInstanceDataHourly(instanceName, "TwitterVolume", rows)

    # Validate results
    self.assertEqual(connectionMock.update_item.call_count, 2)
    self.assertEqual(connectionMock.put_item.call_count, 2)
    calls = connectionMock.put_item.call_args_list

    kwargs0 = calls[0][1]
    item0 = kwargs0["item"]
    self.assertDictEqual(item0["instance_id"], {"S": instanceName})
    self.assertEqual(item0["date_hour"], {"S": "2015-02-20T00"})
    self.assertEqual(item0["date"], {"S": "2015-02-20"})
    self.assertEqual(item0["hour"], {"S": "00"})
    self.assertDictEqual(item0["anomaly_score"]["M"]["TwitterVolume"],
                         {"N": "0.99999"})
    self.assertEqual(kwargs0["condition_expression"], condition)

    kwargs1 = calls[1][1]
    item1 = kwargs1["item"]
    self.assertEqual(item1["instance_id"], {"S": instanceName})
    self.assertEqual(item1["date_hour"], {"S": "2015-02-20T01"})
    self.assertEqual(item1["date"], {"S": "2015-02-20"})
    self.assertEqual(item1["hour"], {"S": "01"})
    self.assertDictEqual(item1["anomaly_score"]["M"]["TwitterVolume"],
                         {"N": "0.99964"})
    self.assertEqual(kwargs1["condition_expression"], condition)


if __name__ == "__main__":
  unittest.main()
