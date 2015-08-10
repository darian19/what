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

""" DynamoDB Service

Subscribes to a dynamodb queue bound to model results and non-metric data
fanout exchanges and forwards data to dynamodb for consumption by mobile
client.
"""

from datetime import datetime, timedelta
from decimal import Context, Underflow, Clamped, Overflow
import json
import os
import sys

import boto.dynamodb2
from boto.dynamodb2.exceptions import (
    ConditionalCheckFailedException, ItemNotFound, ResourceNotFoundException,
    ValidationException, ProvisionedThroughputExceededException)
from boto.dynamodb2.table import Table
from boto.exception import JSONResponseError

from nta.utils import amqp
from nta.utils import error_handling

import taurus.engine
from taurus.engine import taurus_logging
from taurus.engine.exceptions import InsufficientConfigurationError
from taurus.engine.runtime.dynamodb.definitions import (
  InstanceDataHourlyDynamoDBDefinition,
  MetricDynamoDBDefinition,
  MetricDataDynamoDBDefinition,
  MetricTweetsDynamoDBDefinition)

from htmengine import htmengineerrno, utils
from htmengine.runtime.anomaly_service import AnomalyService

from taurus.engine import logging_support



g_log = taurus_logging.getExtendedLogger(__name__)



# FIXME Hack around boto bug #2413
# See https://YOMPhub.com/boto/boto/issues/2413
FIXED_DYNAMODB_CONTEXT = Context(
  Emin=-128,
  Emax=126,
  rounding=None,
  prec=5, # Reduce precision for overall reduction in payload size
  traps=[
    Clamped,
    Overflow,
    Underflow
  ]
)



# Decorator for retrying dynamodb operations that failed due to transient error
_RETRY_ON_TRANSIENT_DYNAMODB_ERROR = error_handling.retry(
  timeoutSec=10, initialRetryDelaySec=0.5, maxRetryDelaySec=2,
  retryExceptions=(ProvisionedThroughputExceededException,),
  logger=g_log
)



def convertDefineModelResultToMetricItem(modelCommandResult):
  """ Convert "defineModel" Model Command Result to MetricItem suitable for
  publishing to dynamodb.

  :param dict modelCommandResult:  See model_command_result_amqp_message.json
    for schema.
  :returns: MetricItem instance suitable for publishing to the `taurus.metric`
    dynamodb table.
  :rtype: Instance of namedtuple implemented in
    `MetricDynamoDBDefinition().Item()` constructor
  """
  modelId = modelCommandResult["modelId"]
  modelInfo = modelCommandResult["modelInfo"]
  metricName = modelInfo["metricName"]
  resource = modelInfo["resource"]
  modelSpec = modelInfo["modelSpec"]

  userInfo = modelSpec["metricSpec"].get("userInfo", {})
  return MetricDynamoDBDefinition().Item(
    display_name=resource,
    name=metricName,
    server=resource,
    uid=modelId,
    metricType=userInfo.get("metricType"),
    metricTypeName=userInfo.get("metricTypeName"),
    symbol=userInfo.get("symbol"))



def convertInferenceResultRowToMetricDataItem(metricId, row):
  """ Convert model inference result row to MetricDataItem suitable for
  publishing to dynamodb, applying workaround for boto bug:

    https://YOMPhub.com/boto/boto/issues/2413

  :param str metricId: unique metric identifier
  :param row: model inference result row
  :type row: results item per model_inference_results_msg_schema.json
  :returns: MetricDataItem instance suitable for publishing to the
    `taurus.metric_data` dynamodb table.
  :rtype: Instance of namedtuple implemented in
    `MetricDataDynamoDBDefinition().Item()` constructor
  """
  return MetricDataDynamoDBDefinition().Item(
    uid=metricId,
    timestamp=datetime.utcfromtimestamp(row["ts"]).isoformat(),
    anomaly_score=(
      FIXED_DYNAMODB_CONTEXT.create_decimal_from_float(row["anomaly"])),
    metric_value=(
      FIXED_DYNAMODB_CONTEXT.create_decimal_from_float(row["value"])),
  )



class DynamoDBService(object):
  """ Binds a "dynamodb" queue to:
      - The model results fanout exchange defined in the
        ``results_exchange_name`` configuration directive of the
        ``metric_streamer`` configuration section.
      - Non-metric data topic exchange defined in the ``exchange_name``
        configuration directive of the ``non_metric_data`` configuration
        section
  """

  _FRESH_DATA_THRESHOLD_DAYS = 14

  def __init__(self):
    self._queueName = "dynamodb"
    self._modelResultsExchange = (
      taurus.engine.config.get("metric_streamer", "results_exchange_name"))
    self._nonMetricDataExchange = (
      taurus.engine.config.get("non_metric_data", "exchange_name"))

    self.dynamodb = self.connectDynamoDB()

    self._metric = None
    self._metric_data = None
    self._metric_tweets = None
    self.createDynamoDBSchema()


  def _gracefulCreateTable(self, definition):
    """ Create dynamodb table.  Return pre-existing table if `table_name`
    exists already.

    `**kwargs` is applied to `Table.create()` and must not contain `table_name`
    or `connection`.

    :param definition: Table name
    :type definitionj: Instance of DynamoDBDefinition subclass
    :returns: DynamoDB Table
    :rtype: boto.dynamodb2.table.Table
    """
    try:
      table = Table.create(definition.tableName,
                           connection=self.dynamodb,
                           **definition.tableCreateKwargs)
      g_log.info("Created %r", definition)
    except JSONResponseError as err:
      if err.status == 400 and err.error_code == u'ResourceInUseException':
        table = Table(definition.tableName, connection=self.dynamodb)
      else:
        raise

    return table


  def createDynamoDBSchema(self):
    """ Apply full dynamodb table schema definitions.
    """
    self._metric = self._gracefulCreateTable(MetricDynamoDBDefinition())
    self._metric_data = (
      self._gracefulCreateTable(MetricDataDynamoDBDefinition()))
    self._metric_tweets = (
      self._gracefulCreateTable(MetricTweetsDynamoDBDefinition()))
    self._instance_data_hourly = self._gracefulCreateTable(
        InstanceDataHourlyDynamoDBDefinition())


  @staticmethod
  def connectDynamoDB():
    """ Get DynamoDB connection using Taurus config for credentials

    For DynamoDB Local Tool::

      [dynamodb]
      host = 127.0.0.1
      port = 8300
      aws_region = us-west-2
      is_secure=False

    Note: Both host AND port must be non-blank for access to local tool.

    For live AWS::

      [dynamodb]
      host =
      port =
      aws_region = us-west-2
      is_secure=False

    Note: aws_access_key_id and aws_secret_access_key are retrieved from
    environment variables that must be set for production and staging servers.

    :raises: InsufficientConfigurationError
    """

    region = taurus.engine.config.get("dynamodb", "aws_region")

    connectKwargs = {
      "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "taurus"),
      "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "taurus"),
      "is_secure": taurus.engine.config.getboolean("dynamodb", "is_secure"),
    }

    host = taurus.engine.config.get("dynamodb", "host")
    port = taurus.engine.config.get("dynamodb", "port")

    if host:
      if not port:
        raise InsufficientConfigurationError(
          "Missing required value for [dynamodb] port for given host")

      # Using DynamoDB local emulation tool
      connectKwargs["host"] = host
      connectKwargs["port"] = port

    elif port:
      raise InsufficientConfigurationError(
          "Missing required value for [dynamodb] host for given port")

    return boto.dynamodb2.connect_to_region(region, **connectKwargs)


  def _publishMetricData(self, metricId, rows):
    """ Specific handler for metric data rows.  Publishes to the
    `taurus.data.metric_data` dynamodb table.

    :param str metricId: unique metric identifier
    :param rows: model inference result rows per "results" property of
      htmengine/runtime/json_schema/model_inference_results_msg_schema.json
    :type rows: Sequence of dicts
    """
    with self._metric_data.batch_write() as dynamodbBatchWrite:
      processedKeys = set()
      for row in rows:
        data=convertInferenceResultRowToMetricDataItem(metricId, row)

        # Safeguard against erroneously-provided duplicate timestamp in batch
        key = (data.uid, data.timestamp)
        if key in processedKeys:
          # This would trigger ValidationException from DynamoDB with the
          # message "Provided list of item keys contains duplicates"
          g_log.error("Duplicate metric_data key in batch write: data=%r from "
                      "row=%r from batchLen=%d", data, row, len(rows))
          continue

        dynamodbBatchWrite.put_item(data=data._asdict(), overwrite=True)
        processedKeys.add(key)


  def _publishInstanceDataHourly(self, instanceName, metricType, rows):
    """ Specific handler for instance data rows.  Publishes to the
    `taurus.data.instance_data_hourly` dynamodb table.

    :param instanceName: name of the instance
    :type instanceName: str

    :param metricType: the metric type identifier
    :type metricType: str

    :param rows: model inference result rows per "results" property of
      htmengine/runtime/json_schema/model_inference_results_msg_schema.json
    :type rows: Sequence of dicts
    """
    hourToMaxScore = {}
    for row in rows:
      # row.timestamp is a datetime instance
      ts = datetime.utcfromtimestamp(row["ts"]).replace(minute=0,
                                                        second=0,
                                                        microsecond=0)
      # Store the max anomaly likelihood for the period
      hourToMaxScore[ts] = max(hourToMaxScore.get(ts, 0.0),
                               row["anomaly"])
    for ts, score in sorted(hourToMaxScore.iteritems()):
      score = FIXED_DYNAMODB_CONTEXT.create_decimal_from_float(score)
      dateHour = ts.strftime("%Y-%m-%dT%H")

      data = {
          "instance_id": {"S": instanceName},
          "date_hour": {"S": dateHour},
          "date": {"S": ts.strftime("%Y-%m-%d")},
          "hour": {"S": ts.strftime("%H")},
          "anomaly_score": {"M": {metricType: {"N": str(score)}}},
      }
      # Validate the data fields against the schema
      InstanceDataHourlyDynamoDBDefinition().Item(**data)

      # First try a conditional update for the anomaly score for this metric
      updateKey = {"instance_id": data["instance_id"],
                   "date_hour": data["date_hour"]}
      anomalyScoreMetric = "anomaly_score.%s" % metricType
      updateCondition = ("attribute_not_exists(%(asm)s) or "
                         "%(asm)s < :value" % {"asm": anomalyScoreMetric})
      updateValues = {":value": {"N": str(score)}}
      updateExpression = "SET %s = :value" % anomalyScoreMetric

      @_RETRY_ON_TRANSIENT_DYNAMODB_ERROR
      def updateItemWithRetries():
        self.dynamodb.update_item(self._instance_data_hourly.table_name,
                                  key=updateKey,
                                  update_expression=updateExpression,
                                  condition_expression=updateCondition,
                                  expression_attribute_values=updateValues)

      try:
        updateItemWithRetries()
      except ResourceNotFoundException:
        # There is no row yet, so continue on to PutItem
        pass
      except ValidationException:
        # It's OK, let's continue and try the PutItem
        pass
      except ConditionalCheckFailedException:
        # The existing value is larger so we are done
        continue
      except Exception:
        g_log.exception("update_item failed: table=%s; updateKey=%s; "
                        "update=%s; condition=%s; values=%s",
                        self._instance_data_hourly.table_name, updateKey,
                        updateExpression, updateCondition, updateValues)
        raise
      else:
        # There was no exception, the update succeeded, we are done
        continue

      # If the UpdateItem failed with ResourceNotFoundException, put the row
      # and continue to next iteration of the loop

      putCondition = "attribute_not_exists(instance_id)"

      @_RETRY_ON_TRANSIENT_DYNAMODB_ERROR
      def putItemWithRetries(item, condition):
        self.dynamodb.put_item(
          self._instance_data_hourly.table_name,
          item=item,
          condition_expression=condition)

      try:
        putItemWithRetries(data, putCondition)
      except ConditionalCheckFailedException:
        # No problem, row already exists!
        pass
      except Exception:
        g_log.exception("put_item failed: table=%s; condition=%s; item=%s",
                        self._instance_data_hourly.table_name, putCondition,
                        data)
        raise
      else:
        # There was no exception, the put succeeded, we are done
        continue

      # In the case that a parallel process beat us to it
      try:
        updateItemWithRetries()
      except ConditionalCheckFailedException:
        # The existing value is larger so we are done
        continue
      except Exception:
        g_log.exception("update_item failed: table=%s; updateKey=%s; "
                        "update=%s; condition=%s; values=%s",
                        self._instance_data_hourly.table_name, updateKey,
                        updateExpression, updateCondition, updateValues)
        raise



  def _handleModelInferenceResults(self, body):
    """ Model results batch handler. Publishes metric data to DynamoDB for a
    given model inference results batch pulled off of the `dynamodb` queue.

    :param body: Serialized message payload; the message is compliant with
      htmengine/runtime/json_schema/model_inference_results_msg_schema.json.
    :type body: str
    """
    try:
      batch = AnomalyService.deserializeModelResult(body)
    except Exception:
      g_log.exception("Error deserializing model result")
      raise

    metricId = batch["metric"]["uid"]
    metricName = batch["metric"]["name"]

    g_log.info("Handling %d model result(s) for %s - %s",
               len(batch["results"]), metricId, metricName)

    if not batch["results"]:
      g_log.error("Empty results in model inference results batch; model=%s",
                  metricId)
      return

    lastRow = batch["results"][-1]
    if (datetime.utcfromtimestamp(lastRow["ts"]) <
        (datetime.utcnow() -
         timedelta(days=self._FRESH_DATA_THRESHOLD_DAYS))):
      g_log.info("Dropping stale result batch from model=%s; first=%s; last=%s",
                 metricId, batch["results"][0], lastRow)
      return

    instanceName = batch["metric"]["resource"]

    metricSpec = batch["metric"]["spec"]
    userInfo = metricSpec.get("userInfo", {})
    metricType = userInfo.get("metricType")
    metricTypeName = userInfo.get("metricTypeName")
    symbol = userInfo.get("symbol")

    # Although not relevant in a production setting, since dynamodb service
    # sits atop htmengine and is running during htmengine integration tests
    # there are inbound custom metrics that lack crucial Taurus-specific
    # user-data not intended to be published on dynamodb.  If the metric lacks
    # any of the Taurus-required `metricType`, `metricTypeName`, or `symbol`
    # userInfo keys, log it as a warning and don't publish to dynamodb.

    if not metricType:
      g_log.warning("Missing value for metricType, uid=%s, name=%s",
                    metricId, metricName)
      return

    if not metricTypeName:
      g_log.warning("Missing value for metricTypeName, uid=%s, name=%s",
                    metricId, metricName)
      return

    if not symbol:
      g_log.warning("Missing value for symbol, uid=%s, name=%s",
                    metricId, metricName)
      return

    self._publishMetricData(metricId, batch["results"])
    self._publishInstanceDataHourly(instanceName, metricType,
                                    batch["results"])


  def _handleNonMetricTweetData(self, body):
    """ Twitter handler. Publishes non-metric data to DynamoDB for twitter
    data pulled off of the `dynamodb` queue.

    :param str body: Incoming message payload as a JSON-encoded list of objects,
      with each object per
      ``taurus/metric_collectors/twitterdirect/tweet_export_schema.json``
    """
    payload = json.loads(body)
    g_log.info("Handling %d non-metric tweet item(s)", len(payload))
    with self._metric_tweets.batch_write() as dynamodbBatchWrite:
      for item in payload:
        item["metric_name_tweet_uid"] = (
          "-".join((item["metric_name"], item["tweet_uid"])))
        data = MetricTweetsDynamoDBDefinition().Item(**item)
        dynamodbBatchWrite.put_item(data=data._asdict(), overwrite=True)


  def _purgeMetricFromDynamoDB(self, uid):
    """ Purge metric from dynamodb metric table
    :param uid: Metric uid
    """
    g_log.info("Removing %s from dynamodb", uid)
    try:
      metricItem = self._metric.lookup(uid, consistent=True)
      metricItem.delete()
    except ItemNotFound as err:
      g_log.warning("Nothing to remove.  %s", str(err))


  def _handleModelCommandResult(self, body):
    """ ModelCommandResult handler.  Handles model creation/deletion events and
    makes the associated put_item() and delete() calls to appropriate dynamodb
    tables

    :param body: Incoming message payload
    :type body: str
    """
    try:
      modelCommandResult = AnomalyService.deserializeModelResult(body)
    except Exception:
      g_log.exception("Error deserializing model command result")
      raise

    if modelCommandResult["status"] != htmengineerrno.SUCCESS:
      return # Ignore...

    if modelCommandResult["method"] == "defineModel":
      g_log.info("Handling `defineModel` for %s",
                     modelCommandResult.get("modelId"))
      metricItem = convertDefineModelResultToMetricItem(modelCommandResult)
      g_log.info("Saving %r to dynamodb", metricItem)
      self._metric.put_item(data=metricItem._asdict(), overwrite=True)

    elif modelCommandResult["method"] == "deleteModel":
      self._purgeMetricFromDynamoDB(modelCommandResult["modelId"])



  def messageHandler(self, message):
    """ Inspect all inbound model results and non-metric data.  Cache in
    DynamoDB for consumption by mobile client.

    We will key off of routing key to determine specific handler for inbound
    message.  If routing key is `None`, attempt to decode message using
    `AnomalyService.deserializeModelResult()`.

    Tweet data must have routing key of "taurus.metric_data.tweets".

    :param amqp.messages.ConsumerMessage message: ``message.body`` is one of:
        Serialized batch of model inference results generated in
          ``AnomalyService`` and must be deserialized using
          ``AnomalyService.deserializeModelResult()``. Per
          htmengine/runtime/json_schema/model_inference_results_msg_schema.json

        Serialized ``ModelCommandResult`` generated in ``AnomalyService``
          per model_command_result_amqp_message.json and must be deserialized
          using ``AnomalyService.deserializeModelResult()``

        Non-metric tweets: Incoming message payload as a JSON-encoded list of
          objects, with each object formatted per
          ``taurus/metric_collectors/twitterdirect/tweet_export_schema.json``
    """
    if message.methodInfo.routingKey == "taurus.data.non-metric.twitter":
      self._handleNonMetricTweetData(message.body)
    elif message.methodInfo.routingKey is None:
      g_log.warning("Unrecognized routing key.")
    else:
      dataType = (message.properties.headers.get("dataType")
                  if message.properties.headers else None)
      if not dataType:
        self._handleModelInferenceResults(message.body)
      elif dataType == "model-cmd-result":
        self._handleModelCommandResult(message.body)
      else:
        g_log.warning("Unexpected message header dataType=%s", dataType)

    message.ack()


  def _declareExchanges(self, amqpClient):
    """ Declares model results and non-metric data exchanges
    """
    amqpClient.declareExchange(exchange=self._modelResultsExchange,
                               exchangeType="fanout",
                               durable=True)
    amqpClient.declareExchange(exchange=self._nonMetricDataExchange,
                               exchangeType="topic",
                               durable=True)


  def _declareQueueAndBindToExchanges(self, amqpClient):
    """ Declares dynamodb queue and binds to model results and non-metric data
    exchanges.
    """
    result = amqpClient.declareQueue(self._queueName, durable=True)

    amqpClient.bindQueue(exchange=self._modelResultsExchange,
                         queue=result.queue, routingKey="")

    # Note: We're using a topic exchange with a permissive wildcard routing
    # key.  This routes all messages from the non-metric data exchange into
    # the shared `dynamodb` queue.  Why didn't we go with a simple fanout
    # exchange?  We may decide later to have less permissive
    # routing keys and more specialized queues, and fanout exchanges don't
    # allow routing keys.  Why is this important?  We _may_ want to break the
    # code up into more specialized components for each of the sources of
    # data, or we may need to tweek concurrency for performance reasons.  This
    # allows us to manage the routing with AMQP primitives in RabbitMQ rather
    # than in the dynamodb service at runtime.  For now, if we run into
    # performance issues and need multiple concurrent  workers, it should be
    # enough to tweak the number of processes in supervisor config to allow
    # more simultaneous processes.

    amqpClient.bindQueue(exchange=self._nonMetricDataExchange,
                           queue=result.queue,
                           routingKey="#")  # substitute for zero or more
                                             # words.


  def run(self):
    g_log.info("Running")

    def _configChannel(amqpClient):
      amqpClient.requestQoS(
          prefetchCount=taurus.engine.config.getint("dynamodb",
                                                    "prefetch_count"))

    try:
      # Open connection to rabbitmq
      with amqp.synchronous_amqp_client.SynchronousAmqpClient(
          amqp.connection.getRabbitmqConnectionParameters(),
          channelConfigCb=_configChannel) as amqpClient:

        self._declareExchanges(amqpClient)
        self._declareQueueAndBindToExchanges(amqpClient)
        consumer = amqpClient.createConsumer(self._queueName)

        # Start consuming messages
        for evt in amqpClient.readEvents():
          if isinstance(evt, amqp.messages.ConsumerMessage):
            self.messageHandler(evt)
          elif isinstance(evt, amqp.consumer.ConsumerCancellation):
            # Bad news: this likely means that our queue was deleted externally
            msg = "Consumer cancelled by broker: %r (%r)" % (evt, consumer)
            g_log.critical(msg)
            raise Exception(msg)
          else:
            g_log.warning("Unexpected amqp event=%r", evt)

    except amqp.exceptions.AmqpConnectionError:
      g_log.exception("RabbitMQ connection failed")
      raise
    except amqp.exceptions.AmqpChannelError:
      g_log.exception("RabbitMQ channel failed")
      raise
    except Exception:
      g_log.exception("Uncaught exception.  Stopping.")
      raise
    except KeyboardInterrupt:
      g_log.info("Stopping Taurus DynamoDB Service", exc_info=True)
    finally:
      g_log.info("Stopping Taurus DynamoDB Service")



if __name__ == "__main__":
  logging_support.LoggingSupport.initService()
  try:
    DynamoDBService().run()
  except KeyboardInterrupt:
    pass
  except Exception as e:
    g_log.exception("Unexpected Error")
    sys.exit(1)
