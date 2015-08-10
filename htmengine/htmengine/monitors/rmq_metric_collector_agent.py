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
A script that collects statistics from a RabbitMQ server and emits them
as metrics to the destination htmengine application server.

The following metrics are collected and emitted by default, where <prefix> is
the value of the --metric-prefix command-line option:

  <prefix>-allq-ready.avg - average number of READY messages in all queues

  <prefix>-q-taurus.metric.custom.data-ready.avg - average number of READY
    messages in htmengine's Metric Storer input queue

  <prefix>-q-taurus.mswapper.results-ready.avg - average number of READY
    messages in htmengine's Anomaly Service input queue

  <prefix>-q-taurus.mswapper.scheduler.notification-ready.avg - average number
    of READY messages in htmengine's Model Scheduler notification input queue
"""

from datetime import datetime
from datetime import timedelta
import json
import logging
from optparse import OptionParser
import os
import socket
import sys
import time

import requests

from nta.utils import logging_support_raw
from nta.utils.config import Config
from nta.utils.error_handling import retry

from htmengine.model_swapper import ModelSwapperConfig
import htmengine.utils

from nta.utils import amqp


_BASE_API_URL = "http://%(rmqHost)s:%(rmqPort)s/api"


# Aggregation period
_AGG_PERIOD_SEC = 300

# Interval between samples in seconds
_SAMPLE_INCR_SEC = 1


# Custom metric name format for average ready messages in specific queue, where
# metricPrefix is the user-supplied value of the --metric-prefix command-line
# option
_Q_AVG_READY_METRIC_FORMAT = "%(metricPrefix)s-q-%(queueName)s-ready.avg"

# Custom metric name format for average ready messages in all queues on broker,
# where metricPrefix is the user-supplied value of the --metric-prefix
# command-line option
_ALLQ_AVG_READY_METRIC_FORMAT = "%(metricPrefix)s-allq-ready.avg"


# Common RabbitMQ Management Interface parameters for retrieving message queue
# length information
_BASE_Q_LENGTH_QUERY_PARAMS = (
  ("lengths_age", _AGG_PERIOD_SEC),
  ("lengths_incr", _SAMPLE_INCR_SEC),
)


_EPOCH_DATETIME = datetime.utcfromtimestamp(0)



g_log = logging.getLogger("rmq_metric_collector_agent")



# Retry decorator for specific errors
_RETRY_ON_REQUESTS_ERROR = retry(
  timeoutSec=10, initialRetryDelaySec=0.05, maxRetryDelaySec=1,
  retryExceptions=(
    # requests retries on DNS errors, but not on connection errors
    requests.exceptions.ConnectionError,
  ),
  logger=g_log
)



def _parseArgs():
  """
  :returns: dict of arg names and values:
    rmqHost: Host of RabbitMQ management interface
    rmqHost: Port number of RabbitMQ management interface
    rmqUser: RabbitMQ username
    rmqPassword: RabbitMQ password
    rmqQueues: sequence of vhost-qualified RabbitMQ queue names to monitor
      e.g., ["%2f/taurus.metric.custom.data",
             "%2f/taurus.mswapper.results",
             "%2f/taurus.mswapper.scheduler.notification"]
    metricDestHost: Host of metric destination address; None for dry-run
    metricDestPort: Port number of metric destination address
    metricPrefix: prefix for emitted metric names
  """
  usage = (
    "%prog [options]\n\n"
    "Collects statistics from a RabbitMQ server and emits them "
    "as metrics to the destination htmengine app server.\n"
    "\n"
    "The following metrics are collected and emitted by default, where\n"
    "<prefix> is the value of the --metric-prefix command-line option.\n"
    "\t<prefix>-allq-ready.avg - average number of READY messages in all\n"
    "\t\tqueues.\n"
    "\n"
    "\t<prefix>-q-taurus.metric.custom.data-ready.avg - average number of\n"
    "\t\tREADY messages in htmengine's Metric Storer input queue.\n"
    "\n"
    "\t<prefix>-q-taurus.mswapper.results-ready.avg - average number of READY\n"
    "\t\tmessages in htmengine's Anomaly Service input queue.\n"
    "\n"
    "\t<prefix>-q-taurus.mswapper.scheduler.notification-ready.avg - average\n"
    "\t\tnumber of READY messages in htmengine's Model Scheduler notification\n"
    "\t\tinput queue"
  )

  parser = OptionParser(usage=usage)

  # Get params to use as option defaults
  rmqParams = amqp.connection.RabbitmqManagementConnectionParams()

  parser.add_option(
    "--rmq-addr",
    action="store",
    type="string",
    dest="rmqAddr",
    default="%s:%d" % (rmqParams.host, rmqParams.port),
    help=("Address and port host:port of RabbitMQ Management interface "
          "[default: %default]"))

  parser.add_option(
    "--rmq-user",
    action="store",
    type="string",
    dest="rmqUser",
    default=rmqParams.username,
    help="Username for RabbitMQ authentication [default: %default]")

  parser.add_option(
    "--rmq-pass",
    action="store",
    type="string",
    dest="rmqPassword",
    default=rmqParams.password,
    help="Password for RabbitMQ authentication [default: %default]")

  rmqVhost = (rmqParams.vhost if rmqParams.vhost != "/"
              else "%" + rmqParams.vhost.encode("hex"))
  appConfig = Config("application.conf", os.environ.get("APPLICATION_CONFIG_PATH"))
  swapperConfig = ModelSwapperConfig()
  defaultQueues = [
    swapperConfig.get("interface_bus", "results_queue"),
    swapperConfig.get("interface_bus", "scheduler_notification_queue"),
    appConfig.get("metric_listener", "queue_name")
  ]
  defaultQueues = ["%s/%s" % (rmqVhost, q) for q in defaultQueues]

  parser.add_option(
    "--rmq-queues",
    action="store",
    type="string",
    dest="rmqQueues",
    default=",".join(defaultQueues),
    help=("RabbitMQ message queues to monitor; comma-separated, "
          "vhost-qualified; [default: %default]"))

  parser.add_option(
      "--dryrun",
      action="store_true",
      default=False,
      dest="dryRun",
      help=("Use this flag to do a dry run: retrieve data and log it; mutually "
            "exclusive with --metric-addr"))

  parser.add_option(
    "--metric-addr",
    action="store",
    type="string",
    dest="metricDestAddr",
    help=("Destination address for metrics as host:port; typically address of "
          "htmengine custom metrics listener; htmengine default metric "
          "listener port is 2003"))

  parser.add_option(
    "--metric-prefix",
    action="store",
    type="string",
    dest="metricPrefix",
    help="Prefix for metric names")

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    msg = "Unexpected remaining args: %r" % (remainingArgs,)
    g_log.error(msg)
    parser.error(msg)


  if not options.rmqAddr:
    msg = "Missing address of RabbitMQ server"
    g_log.error(msg)
    parser.error(msg)

  rmqHost, _, rmqPort = options.rmqAddr.rpartition(":")
  if not rmqHost:
    msg = "Missing Hostname or IP address of RabbitMQ management interface."
    g_log.error(msg)
    parser.error(msg)

  if not rmqPort:
    msg = "Missing port number of RabbitMQ management interface."
    g_log.error(msg)
    parser.error(msg)

  try:
    rmqPort = int(rmqPort)
  except ValueError:
    msg = ("RabbitMQ Management Interface port must be an integer, but got %r"
           % (metricDestPort,))
    g_log.exception(msg)
    parser.error(msg)

  if not options.rmqUser:
    msg = "Missing RabbitMQ user name."
    g_log.error(msg)
    parser.error(msg)

  if not options.rmqPassword:
    msg = "Missing RabbitMQ password."
    g_log.error(msg)
    parser.error(msg)

  if not options.rmqQueues:
    msg = "Missing vhost-qualified message queue names"
    g_log.error(msg)
    parser.error(msg)

  rmqQueues = options.rmqQueues.split(",")

  if options.dryRun:
    if options.metricDestAddr:
      msg = "--dryrun is mutually exclusive with --metric-addr"
      g_log.error(msg)
      parser.error(msg)

    metricDestHost = metricDestPort = None
  else:
    if not options.metricDestAddr:
      msg = "Missing address of metric destination server"
      g_log.error(msg)
      parser.error(msg)

    metricDestHost, _, metricDestPort = options.metricDestAddr.rpartition(":")
    if not metricDestHost:
      msg = "Missing Hostname or IP address of metric destination server."
      g_log.error(msg)
      parser.error(msg)

    if not metricDestPort:
      msg = "Missing port number of metric destination server."
      g_log.error(msg)
      parser.error(msg)

    try:
      metricDestPort = int(metricDestPort)
    except ValueError:
      msg = "Metric destination port must be an integer, but got %r" % (
        metricDestPort,)
      g_log.exception(msg)
      parser.error(msg)

  options.metricPrefix = (options.metricPrefix.strip()
                          if options.metricPrefix is not None else None)
  if not options.metricPrefix:
    msg = "Missing or empty metric name prefix"
    g_log.error(msg)
    parser.error(msg)


  return dict(
    rmqHost=rmqHost,
    rmqPort=rmqPort,
    rmqUser=options.rmqUser,
    rmqPassword=options.rmqPassword,
    rmqQueues=rmqQueues,
    metricDestHost=metricDestHost,
    metricDestPort=metricDestPort,
    metricPrefix=options.metricPrefix
  )



@_RETRY_ON_REQUESTS_ERROR
def _httpGetWithRetries(session, url, params):
  """ Wrap requests.Session.get in necessary retries

  :params session: requests.Session instance with auth configured
  :param url: URL string
  :param params: params dict to pass to requests.Session.get

  :returns: requests.models.Response instance. see requests.Session.get for
    details
  """
  return session.get(url, params=params)



def _getOverallAverageReadyMessages(session, options):
  """ Retrieve overall message queue average ready message count over the past
  _AGG_PERIOD_SEC using RabbitMQ Management interface

  :param session: requests.Session instance with auth configured.
  :param options: command-line options dict per _parseArgs

  :returns: Average number of ready messages in the broker
  :rtype: floating point number
  """
  url = "%s/overview" % ((_BASE_API_URL % options),)

  params = {
    # Specify desired columns to improve speed and reduce data transfer size
    "columns": "queue_totals.messages_ready_details.avg"
  }
  params.update(_BASE_Q_LENGTH_QUERY_PARAMS)

  g_log.debug("_getOverallAverageReadyMessages: url=%s; params=%s",
              url, params)

  response = None
  try:
    response = _httpGetWithRetries(session, url, params)

    response.raise_for_status()
  except Exception:
    g_log.exception(
      "_getOverallAverageReadyMessages failed; url=%r; params=%r; response=%r",
      url, params, response)
    raise


  result = json.loads(response.text)
  g_log.debug("_getOverallAverageReadyMessages: result=%s:", result)

  if not result:
    return 0

  try:
    averageReadyMessages = (
      result["queue_totals"]["messages_ready_details"]["avg"])
  except KeyError:
    averageReadyMessages = 0
  else:
    if averageReadyMessages is None:
      averageReadyMessages = 0

  return averageReadyMessages



def _getQueueAverageReadyMessages(session, options, qspec):
  """ Retrieve specific message queue's average ready message count over the past
  _AGG_PERIOD_SEC using RabbitMQ Management interface

  :param session: requests.Session instance with auth configured.
  :param options: command-line options dict per _parseArgs
  :param qspec: vhost-qualified message queue name with vhost component
    %hex-encoded if required; e.g., "%2f/taurus.metric.custom.data"

  :returns: Average number of ready messages in queue
  :rtype: floating point number
  """
  url = "%s/queues/%s" % ((_BASE_API_URL % options), qspec)

  params = {
    # Specify desired columns to improve speed and reduce data transfer size
    "columns": "messages_ready_details.avg"
  }
  params.update(_BASE_Q_LENGTH_QUERY_PARAMS)

  g_log.debug("_getQueueAverageReadyMessages: url=%s; params=%s",
              url, params)

  response = None
  try:
    response = _httpGetWithRetries(session, url, params)

    response.raise_for_status()
  except Exception:
    g_log.exception(
      "_getQueueAverageReadyMessages failed; url=%r; params=%r; response=%r",
      url, params, response)
    raise


  result = json.loads(response.text)
  g_log.debug("_getQueueAverageReadyMessages: result=%s", result)

  if not result:
    return 0

  try:
    averageReadyMessages = (
      result["messages_ready_details"]["avg"])
  except KeyError:
    averageReadyMessages = 0
  else:
    if averageReadyMessages is None:
      averageReadyMessages = 0

  return averageReadyMessages



def _formatMetricSample(metricName, value, sampleDatetime):
  """ Create a string that may be sent as a metric data sample to htmengine's
  Metric Listener

  :param metricName: name of the metric
  :param sampleDatetime: UTC datetime of the sample
  :param value: scalar value of the sample

  :returns: formatted sample string
  """
  timestamp = (sampleDatetime - _EPOCH_DATETIME).total_seconds()
  return "%s %f %f" % (metricName, value, timestamp)



def _emitMetricSamples(samples, host, port):
  """ Emit metric data samples to the htmengine's Metric Listener

  :param samples: sequence of formatted samples (see _formatMetricSample)
  :param host: hostname or ip address of htmengine's Metric Listener
  :param port: TCP/IP port number of htmengine's Metric Listener
  """
  dest = (host, port)
  sock = socket.socket()
  try:
    sock.connect(dest)
    sock.sendall("\n".join(samples))
  except Exception:
    g_log.exception("Failed to emit samples to dest=%s", dest)
  finally:
    sock.close()



def main():
  logging_support_raw.LoggingSupport.initService()

  try:
    options = _parseArgs()
    g_log.info("Running %s with options=%r", sys.argv[0], options)

    overallAvgReadyMetricName = _ALLQ_AVG_READY_METRIC_FORMAT % {
      "metricPrefix": options["metricPrefix"]}
    queueAvgReadyMetricNames = [
      _Q_AVG_READY_METRIC_FORMAT % {
        "metricPrefix": options["metricPrefix"],
        "queueName": qspec.rpartition("/")[-1]}
      for qspec in options["rmqQueues"]
    ]

    session = requests.Session()
    session.auth=(options["rmqUser"], options["rmqPassword"])

    delta = timedelta(seconds=_AGG_PERIOD_SEC)
    sampleDatetime = datetime.utcnow()
    sampleDatetime = htmengine.utils.roundUpDatetime(sampleDatetime,
                                                     _AGG_PERIOD_SEC)

    while True:
      waitSec = (sampleDatetime - datetime.utcnow()).total_seconds()
      if waitSec > 0:
        time.sleep(waitSec)

      samples = []

      avg = _getOverallAverageReadyMessages(session, options)
      g_log.debug("overallAvgReadyMessages=%s", avg)
      samples.append(
        _formatMetricSample(overallAvgReadyMetricName,
                            avg,
                            sampleDatetime)
      )

      for qspec, metricName in zip(options["rmqQueues"],
                                   queueAvgReadyMetricNames):
        avg = _getQueueAverageReadyMessages(session, options, qspec)
        g_log.debug("q=%s; averageReadyQMessages=%s", qspec,  avg)
        samples.append(
          _formatMetricSample(metricName, avg, sampleDatetime)
        )

      if options["metricDestHost"] is not None:
        _emitMetricSamples(samples,
                           options["metricDestHost"],
                           options["metricDestPort"])
      else:
        g_log.info("dry-run samples: %r", samples)

      # Next sample time
      sampleDatetime += delta
  except Exception:
    g_log.exception("rmq_metric_collector_agent failed")
    raise



if __name__ == "__main__":
  main()
