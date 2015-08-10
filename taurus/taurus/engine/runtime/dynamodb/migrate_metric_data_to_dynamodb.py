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

import argparse
import datetime
from itertools import groupby, izip_longest
import json
import select
import socket
import sys

from taurus.engine import config, repository, logging_support, taurus_logging
from taurus.engine.repository.schema import metric_data

from nta.utils import amqp
from nta.utils.date_time_utils import epochFromNaiveUTCDatetime
from nta.utils.message_bus_connector import MessageBusConnector
from nta.utils.message_bus_connector import MessageProperties
from nta.utils.sqlalchemy_utils import retryOnTransientErrors

from htmengine import htmengineerrno

from htmengine.runtime import anomaly_service



DEFAULT_CHUNKSIZE = 25 # Max number of rows to include in a single batch



g_log = taurus_logging.getExtendedLogger(__name__)



def replayMetricDataToModelResultsExchange(messageBus,
                                           chunksize=DEFAULT_CHUNKSIZE):
  """ Reads metric data and synthesizes model inference result messages to the
  "model results" exchange, simulating the end result of the AnomalyService.
  This will afford the dynamodb service an opportunity to backfill older data
  :param messageBus: message bus connection
  :type messageBus: nta.utils.message_bus_connector.MessageBusConnector
  """
  engine = repository.engineFactory()

  twoWeeksAgo = datetime.datetime.utcnow() - datetime.timedelta(days=14)

  # Properties for publishing model command results on RabbitMQ exchange
  # (same as AnomalyService)
  modelCommandResultProperties = MessageProperties(
      deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE,
      headers=dict(dataType="model-cmd-result"))

  # Properties for publishing model inference results on RabbitMQ exchange
  # (same as AnomalyService)
  modelInferenceResultProperties = MessageProperties(
    deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE)

  g_log.info("Getting metric data...")
  result = repository.getMetricData(engine,
                                    score=0,
                                    fromTimestamp=twoWeeksAgo,
                                    sort=[metric_data.c.uid,
                                          metric_data.c.rowid.asc()])
  numMetricDataRows = result.rowcount
  g_log.info("Got %d rows", numMetricDataRows)

  numModels = 0
  for uid, group in groupby(result, key=lambda x: x.uid):

    @retryOnTransientErrors
    def _getMetric():
      return repository.getMetric(engine, uid)

    metricObj = _getMetric()

    # Send defineModel command to ensure that the metric table entry is created
    numModels += 1
    modelCommandResult = {
      "status": htmengineerrno.SUCCESS,
      "method": "defineModel",
      "modelId": uid,
      "modelInfo": {
        "metricName": metricObj.name,
        "resource": metricObj.server,
        "modelSpec": json.loads(metricObj.parameters)
      }
    }

    # Serialize
    payload = anomaly_service.AnomalyService._serializeModelResult(
      modelCommandResult)

    g_log.info("Sending `defineModel` command: %r", repr(modelCommandResult))
    messageBus.publishExg(
      exchange=config.get("metric_streamer", "results_exchange_name"),
      routingKey="",
      body=payload,
      properties=modelCommandResultProperties)

    metricInfo = dict(
      uid=metricObj.uid,
      name=metricObj.name,
      description=metricObj.description,
      resource=metricObj.server,
      location=metricObj.location,
      datasource=metricObj.datasource,
      spec=json.loads(metricObj.parameters)["metricSpec"]
    )

    args = [iter(group)] * chunksize
    for num, chunk in enumerate(izip_longest(fillvalue=None, *args)):
      # Create
      inferenceResultsMessage = dict(
        metric=metricInfo,

        results=[
          dict(
            rowid=row.rowid,
            ts=epochFromNaiveUTCDatetime(row.timestamp),
            value=row.metric_value,
            rawAnomaly=row.raw_anomaly_score,
            anomaly=row.anomaly_score
          )
          for row in chunk if row is not None
        ]
      )

      # Serialize
      payload = anomaly_service.AnomalyService._serializeModelResult(
        inferenceResultsMessage)

      g_log.info(
        "uid=%s chunk=%d rows=%d payload_size=%d bytes from %s to %s",
        uid,
        num,
        len(inferenceResultsMessage["results"]),
        sys.getsizeof(payload),
        datetime.datetime.utcfromtimestamp(
          inferenceResultsMessage["results"][0].ts),
        datetime.datetime.utcfromtimestamp(
          inferenceResultsMessage["results"][-1].timestamp))

      messageBus.publishExg(
        exchange=config.get("metric_streamer", "results_exchange_name"),
        routingKey="",
        body=payload,
        properties=modelInferenceResultProperties)


  g_log.info("Done! numMetricDataRows=%d; numModels=%d",
             numMetricDataRows, numModels)



if __name__ == "__main__":
  logging_support.LoggingSupport.initTool()

  parser = argparse.ArgumentParser(
    description="Replay metric data to model results exchange")
  parser.add_argument("--chunksize",
                      type=int,
                      default=DEFAULT_CHUNKSIZE,
                      metavar="NUM",
                      help=("Maximum number of records to include in a batch of"
                            "model inference results message to model results "
                            "exchange"))

  _args = parser.parse_args()

  with MessageBusConnector() as messageBus:
    replayMetricDataToModelResultsExchange(messageBus=messageBus,
                                           chunksize=_args.chunksize)
