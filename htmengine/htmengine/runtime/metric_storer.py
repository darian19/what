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

"""Pulls metric data from a queue and populates the database.

This process is designed work in parallel with metric_listener for accepting
metrics and adding them to the database.

TODO: Get just the values for metrics from the database that we need instead
of the entire rows. We might only need the `uid`.
"""

from collections import defaultdict
import datetime
import itertools
import json
import logging
import os
import time

from htmengine import (raiseExceptionOnMissingRequiredApplicationConfigPath,
                       repository)
from htmengine.adapters.datasource import createCustomDatasourceAdapter
import htmengine.exceptions
from htmengine.htmengine_logging import getExtendedLogger
from htmengine.runtime.metric_listener import parsePlaintext, Protocol
from htmengine.runtime.metric_streamer_util import MetricStreamer
from htmengine.model_swapper.model_swapper_interface import (
    MessageBusConnector, ModelSwapperInterface)

from nta.utils.config import Config
from nta.utils.logging_support_raw import LoggingSupport



LOGGER = getExtendedLogger(__name__)

MAX_CACHED_METRICS = 15000
CACHED_METRICS_TO_KEEP = 10000
MAX_MESSAGES_PER_BATCH = 200
POLL_DELAY_SEC = 1

# Dict mapping metric name to [metric, lastAccessedDatetime]
gCustomMetrics = None


gProfiling = False



def _handleBatch(engine, messages, messageRxTimes, metricStreamer,
                 modelSwapper):
  """Process a batch of messages from the queue.

  This parses the message contents as JSON and uses the 'protocol' field to
  determine how to parse the 'data' in the message. The data is added to the
  database and sent through the metric streamer.

  The Metric objects are cached in gCustomMetrics to minimize database
  lookups.

  :param engine: SQLAlchemy engine object
  :type engine: sqlalchemy.engine.Engine
  :param messages: a list of queue messages to process
  :param messageRxTimes: optional sequence of message-receive times (from
    time.time()) if profiling corresponding to the messages in `messages` arg,
    else empty list

  :param metricStreamer: a :class:`MetricStreamer` instance to use
  :param modelSwapper: a :class:`ModelSwapperInterface` instance to use
  """
  # Use the protocol to determine the message format
  data = []
  for m, rxTime in itertools.izip_longest(messages, messageRxTimes):
    try:
      message = json.loads(m.body)
      protocol = message["protocol"]
      rawData = message["data"]
    except ValueError:
      LOGGER.warn("Discarding message with unknown format: %s", m.body)
      return
    if protocol == Protocol.PLAIN:
      for row in rawData:
        try:
          data.append(parsePlaintext(row))
          if gProfiling and rxTime is not None:
            metricName, _value, metricTimestamp = data[-1]
            LOGGER.info(
              "{TAG:CUSSTR.DATA.RX} metricName=%s; timestamp=%s; rxTime=%.4f",
              metricName, metricTimestamp.isoformat() + "Z", rxTime)
        except ValueError:
          LOGGER.warn("Discarding plaintext message that can't be parsed: %s",
                      row.strip())
    else:
      LOGGER.warn("Discarding message with unknown protocol: %s", protocol)
      return
  # Make sure we got some valid data
  if not data:
    return
  # Create a dict mapping metric name to data list
  dataDict = defaultdict(list)
  for record in data:
    dataDict[record[0]].append(record)

  LOGGER.info("Processing %i records for %i models from %i batches.",
              len(data), len(dataDict), len(messages))

  # For each metric, create the metric if it doesn't exist and add the data
  _addMetricData(engine, dataDict, metricStreamer, modelSwapper)



def _addMetricData(engine, dataDict, metricStreamer, modelSwapper):
  """Send metric data for each metric to the metric streamer.

  TODO: document args
  """
  # For each metric, create the metric if it doesn't exist and add the data
  for metricName, metricData in dataDict.iteritems():
    if metricName not in gCustomMetrics:
      # Metric doesn't exist, create it
      _addMetric(engine, metricName)
    else:
      gCustomMetrics[metricName][1] = datetime.datetime.utcnow()
    # Add the data
    metricData = [(dt, value) for _, value, dt in metricData]

    try:
      metricStreamer.streamMetricData(metricData,
                                      gCustomMetrics[metricName][0].uid,
                                      modelSwapper)
    except htmengine.exceptions.ObjectNotFoundError:
      # The metric may have been deleted and re-created, so attempt to update
      # the cache.
      _addMetric(engine, metricName)
      try:
        metricStreamer.streamMetricData(metricData,
                                        gCustomMetrics[metricName][0].uid,
                                        modelSwapper)
      except htmengine.exceptions.ObjectNotFoundError:
        LOGGER.exception("Failed to add data for metric %s with uid %s",
                         metricName, gCustomMetrics[metricName][0].uid)
    except Exception:  # Exception excludes KeyboardInterrupt from supervisor
      LOGGER.exception("Error adding custom metric data: %r", metricData)



def _addMetric(engine, metricName):
  """Add the new metric to the database."""
  if metricName in gCustomMetrics:
    try:
      # Attempt to reload the metric
      metricId = gCustomMetrics[metricName][0].uid
      with engine.connect() as conn:
        gCustomMetrics[metricName][0] = repository.getMetric(conn, metricId)
      return
    except htmengine.exceptions.ObjectNotFoundError:
      # Do nothing, we will create new metric and update cache below
      pass

  # Use the adapter to create the metric
  try:
    metricId = createCustomDatasourceAdapter().createMetric(metricName)
  except htmengine.exceptions.MetricAlreadyExists as e:
    metricId = e.uid

  with engine.connect() as conn:
    metric = repository.getMetric(conn, metricId)

  # Add it to our cache
  gCustomMetrics[metricName] = [metric, datetime.datetime.utcnow()]

  _trimMetricCache()



def _trimMetricCache():
  # Make sure we don't have too many cached metrics now
  if len(gCustomMetrics) > MAX_CACHED_METRICS:
    # Compute the number of metrics we want to remove
    numMetricsToRemove = len(gCustomMetrics) - CACHED_METRICS_TO_KEEP
    # Get a list of metric names sorted by last accessed time
    metricList = []
    for name, (_metric, ts) in gCustomMetrics.iteritems():
      metricList.append((ts, name))
    metricList.sort()
    # Remove the metrics accessed least recently
    for _, name in metricList[:numMetricsToRemove]:
      del gCustomMetrics[name]


@raiseExceptionOnMissingRequiredApplicationConfigPath
def runServer():
  # Get the current list of custom metrics
  appConfig = Config("application.conf",
                     os.environ["APPLICATION_CONFIG_PATH"])

  engine = repository.engineFactory(appConfig)
  global gCustomMetrics
  now = datetime.datetime.utcnow()

  with engine.connect() as conn:
    gCustomMetrics = dict(
      (m.name, [m, now]) for m in repository.getCustomMetrics(conn))

  queueName = appConfig.get("metric_listener", "queue_name")

  global gProfiling
  gProfiling = (appConfig.getboolean("debugging", "profiling") or
                LOGGER.isEnabledFor(logging.DEBUG))
  del appConfig

  metricStreamer = MetricStreamer()
  modelSwapper = ModelSwapperInterface()

  with MessageBusConnector() as bus:
    if not bus.isMessageQeueuePresent(queueName):
      bus.createMessageQueue(mqName=queueName, durable=True)
    LOGGER.info("Waiting for messages. To exit, press CTRL+C")
    with bus.consume(queueName) as consumer:
      messages = []
      messageRxTimes = []
      while True:
        message = consumer.pollOneMessage()
        if message is not None:
          messages.append(message)
          if gProfiling:
            messageRxTimes.append(time.time())

        if message is None or len(messages) >= MAX_MESSAGES_PER_BATCH:
          if messages:
            # Process the batch
            try:
              _handleBatch(engine,
                           messages,
                           messageRxTimes,
                           metricStreamer,
                           modelSwapper)
            except Exception:  # pylint: disable=W0703
              LOGGER.exception("Unknown failure in processing messages.")
              # Make sure that we ack messages when there is an unexpected error
              # to avoid getting hung forever on one bad record.

            # Ack all the messages
            messages[-1].ack(multiple=True)
            # Clear the message buffer
            messages = []
            messageRxTimes = []
          else:
            # Queue is empty, wait before retrying
            time.sleep(POLL_DELAY_SEC)



if __name__ == "__main__":
  LoggingSupport.initService()

  runServer()
