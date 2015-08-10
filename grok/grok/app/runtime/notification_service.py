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

from datetime import datetime, timedelta
import locale
locale.setlocale(locale.LC_ALL, "en_US")
import math
import os.path
from pkg_resources import resource_filename
import sys
import StringIO
import traceback
import uuid

from boto.exception import BotoServerError
from pytz import timezone
import requests

from nta.utils import amqp

from YOMP import logging_support
from YOMP.YOMP_logging import getExtendedLogger

import YOMP.app
from YOMP.app import repository
from YOMP.app.aws import ses_utils
from htmengine.runtime.anomaly_service import AnomalyService



# How many days until we remove a notification device
_NOTIFICATION_DEVICE_STALE_DAYS = 30



def _queryAvailabilityZone():
  """ Query AWS for the machine's availability zone

  NOTE: we break it out into a separate function to make it easy for unit tests
    to patch.

  :return: AWS availability-zone instance metadata or None if not available.
  """
  try:
    # Attempt to detect EC2 region
    instanceDataResult = requests.get(("http://instance-data/latest/meta-data/p"
                                       "lacement/availability-zone"))
  except requests.exceptions.ConnectionError:
    return None
  else:
    return instanceDataResult



def _getCurrentRegion():
  """ Retrieve current region from AWS and cache the result

  NOTE: This used to be retrieved directly into a global variable, which added
    significant delays when running unit test on a dev laptop while on a
    different network (e.g., from home) and there was no way to patch it.
  """
  try:
    return _getCurrentRegion.currentRegion
  except AttributeError:
    pass

  instanceDataResult = _queryAvailabilityZone()
  if instanceDataResult is not None:
    currentRegion = instanceDataResult.text.strip()[:-1]
  else:
    currentRegion = YOMP.app.config.get("aws", "default_region")

  _getCurrentRegion.currentRegion = currentRegion
  return _getCurrentRegion.currentRegion



def humanFriendlyBytes(num, base=1000, units=("Bytes", "kB", "MB", "GB", "TB",
                                              "PB", "EB", "ZB", "YB")):
  """ Normalize raw bytes value into a human-friendly value.

      For example, humanFriendlyBytes(1234567) returns (1.234567, 'MB'),
      humanFriendlyBytes(12300000000) returns (12.3, 'GB')

      :param num: Number
      :param base: Numeric base
      :param units: Sequence of human-friendly units
      :returns: tuple of normalized byte value and unit
      :rtype: tuple
  """
  if abs(num) > 0:
    unit = units[int(math.log(abs(num), base))]

    while num >= base:
      num = num/float(base)

  else:
    unit = units[0]

  return (num, unit)


def localizedTimestamp(timestamp,
                       region=None,
                       zones={"ap-northeast-1": "Asia/Tokyo",
                              "ap-southeast-1": "Asia/Singapore",
                              "ap-southeast-2": "Australia/Sydney",
                              "cn-north-1": "Asia/Shanghai",
                              "eu-west-1": "GMT",
                              "sa-east-1": "America/Sao_Paulo",
                              "us-east-1": "US/Eastern",
                              "us-west-1": "US/Pacific",
                              "us-west-2": "US/Pacific"}):
  """ Get localized timestamp.

      :param timestamp: Timestamp
      :type timestamp: datetime instance
      :param region: AWS Region on which to base timezone selection
      :type region: str
      :param zones: Mapping of AWS regions to Timezones.  If region not found
        in zones, "UTC" will be used.
      :type zones: dict
      :returns: Timestamp with localized timezone
      :rtype: datetime instance
  """
  if region is None:
    region = _getCurrentRegion()

  zone = timezone(zones.get(region, "UTC"))
  return zone.localize(timestamp+zone.utcoffset(timestamp))


class NotificationService(object):
  """ Notification Service to monitor model inference results and trigger
      notifications where appropriate.

      Binds a "notifications" queue to the model results fanout exchange
      defined in the ``results_exchange_name`` configuration directive of the
      ``metric_streamer`` configuration section.
  """
  def __init__(self):
    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()

    self._log = getExtendedLogger(self.__class__.__name__)
    self._modelResultsExchange = (
      YOMP.app.config.get("metric_streamer", "results_exchange_name"))


  def sendNotificationEmail(self, engine, settingObj, notificationObj):
    """ Send notification email through Amazon SES

        :param engine: SQLAlchemy engine object
        :type engine: sqlalchemy.engine.Engine
        :param settingObj: Device settings
        :type settingObj: NotificationSettings
        :param notificationObj: Notification
        :type notificationObj: Notification

        See conf/notification-body.tpl (or relevant notification body
        configuration value) for template value.  Values are substituted using
        python's `str.format(**data)` function where `data` is a dict
        containing the following keys:

        ============ ===========
        Key          Description
        ============ ===========
        notification Notification instance
        data         MetricData row that triggered notification
        date         Formatted date (%A, %B %d, %Y)
        time         Formatted time (%I:%M %p (%Z))
        unit         Canonical unit for metric value
        ============ ===========
    """

    subject = YOMP.app.config.get("notifications", "subject")

    bodyType = "default"
    with engine.connect() as conn:
      metricObj = repository.getMetric(conn, notificationObj.metric)
    if metricObj.datasource == "custom":
      bodyType = "custom"

    body = open(resource_filename(YOMP.__name__, os.path.join("../conf",
      YOMP.app.config.get("notifications", "body_" + bodyType)))).read()
    body = body.replace("\n", "\r\n") # Ensure windows newlines

    # Template variable storage (to be expanded in call to str.format())
    templated = dict(notification=notificationObj)

    # Metric
    templated["metric"] = metricObj

    # Instance
    templated["instance"] = metricObj.tag_name or metricObj.server

    # Date/time
    templated["timestampUTC"] = notificationObj.timestamp.strftime(
                                  "%A, %B %d, %Y %I:%M %p")
    localtime = localizedTimestamp(notificationObj.timestamp)
    templated["timestampLocal"] = localtime.strftime(
                                    "%A, %B %d, %Y %I:%M %p")
    templated["timezoneLocal"] = localtime.strftime("%Z")

    # Region
    templated["region"] = _getCurrentRegion()


    self._log.info("NOTIFICATION=%s SERVER=%s METRICID=%s METRIC=%s DEVICE=%s "
                   "RECIPIENT=%s Sending email. " % (notificationObj.uid,
                   metricObj.server, metricObj.uid, metricObj.name,
                   settingObj.uid, settingObj.email_addr))

    try:
      # Send through SES
      messageId = ses_utils.sendEmail(subject=subject.format(**templated),
                                      body=body.format(**templated),
                                      toAddresses=settingObj.email_addr)

      if messageId is not None:
        # Record AWS SES Message ID
        with engine.connect() as conn:
          repository.updateNotificationMessageId(conn,
                                                 notificationObj.uid,
                                                 messageId)

          self._log.info("NOTIFICATION=%s SESMESSAGEID=%s Email sent. " % (
                         notificationObj.uid, messageId))


    except BotoServerError:
      self._log.exception("Unable to send email.")


  def messageHandler(self, message):
    """ Inspect all inbound model results in a batch for anomaly thresholds and
        trigger notifications where applicable.

        :param amqp.messages.ConsumerMessage message: ``message.body`` is a
          serialized batch of model inference results generated in
          ``AnomalyService`` and must be deserialized using
          ``AnomalyService.deserializeModelResult()``. The message conforms to
          htmengine/runtime/json_schema/model_inference_results_msg_schema.json
    """
    if message.properties.headers and "dataType" in message.properties.headers:
      # Not a model inference result
      return

    YOMP.app.config.loadConfig() # reload config on every batch
    engine = repository.engineFactory()
    # Cache minimum threshold to trigger any notification to avoid permuting
    # settings x metricDataRows
    try:
      try:
        batch = AnomalyService.deserializeModelResult(message.body)
      except Exception:
        self._log.exception("Error deserializing model result")
        raise

      # Load all settings for all users (once per incoming batch)
      with engine.connect() as conn:
        settings = repository.retryOnTransientErrors(
            repository.getAllNotificationSettings)(conn)

      self._log.debug("settings: %r" % settings)

      if settings:
        minThreshold = min(setting.sensitivity for setting in settings)
      else:
        minThreshold = 0.99999

      metricInfo = batch["metric"]
      metricId = metricInfo["uid"]
      resource = metricInfo["resource"]


      for row in batch["results"]:

        if row["anomaly"] >= minThreshold:
          for settingObj in settings:
            if row["rowid"] <= 1000:
              continue # Not enough data

            rowDatetime = datetime.utcfromtimestamp(row["ts"])

            if rowDatetime < datetime.utcnow() - timedelta(seconds=3600):
              continue # Skip old

            if row["anomaly"] >= settingObj.sensitivity:
              # First let's clear any old users out of the database.
              with engine.connect() as conn:
                repository.retryOnTransientErrors(
                    repository.deleteStaleNotificationDevices)(
                        conn, _NOTIFICATION_DEVICE_STALE_DAYS)

              # If anomaly_score meets or exceeds any of the device
              # notification sensitivity settings, trigger notification.
              # repository.addNotification() will handle throttling.
              notificationId = str(uuid.uuid4())

              with engine.connect() as conn:
                result = repository.retryOnTransientErrors(
                    repository.addNotification)(conn,
                                                uid=notificationId,
                                                server=resource,
                                                metric=metricId,
                                                rowid=row["rowid"],
                                                device=settingObj.uid,
                                                windowsize=(
                                                  settingObj.windowsize),
                                                timestamp=rowDatetime,
                                                acknowledged=0,
                                                seen=0)

              self._log.info("NOTIFICATION=%s SERVER=%s METRICID=%s DEVICE=%s "
                             "Notification generated. " % (notificationId,
                             resource, metricId,
                             settingObj.uid))

              if (result is not None and
                  result.rowcount > 0 and
                  settingObj.email_addr):
                # Notification was generated.  Attempt to send email
                with engine.connect() as conn:
                  notificationObj = repository.getNotification(conn,
                                                               notificationId)

                self.sendNotificationEmail(engine,
                                           settingObj,
                                           notificationObj)

          if not settings:
            # There are no device notification settings stored on this server,
            # no notifications will be generated.  However, log that a
            # an anomaly was detected and notification would be sent if there
            # were any configured devices
            self._log.info("<%r>" % (metricInfo) + (
                                          "{TAG:APP.NOTIFICATION} Anomaly "
                                          "detected at %s, but no devices are "
                                          "configured.") % rowDatetime)

    finally:
      message.ack()

    # Do cleanup
    with engine.connect() as conn:
      repository.clearOldNotifications(conn) # Delete all notifications outside
                                             # of 30-day window


  def run(self):
    try:
      self._log.info("Starting YOMP Notification Service")

      def configChannel(amqpClient):
        amqpClient.requestQoS(prefetchCount=1)

      # Open connection to rabbitmq
      with amqp.synchronous_amqp_client.SynchronousAmqpClient(
          amqp.connection.getRabbitmqConnectionParameters(),
          channelConfigCb=configChannel) as amqpClient:

        # make sure the queue and exchanges exists and the queue is bound
        amqpClient.declareExchange(self._modelResultsExchange,
                                   durable=True,
                                   exchangeType="fanout")

        result = amqpClient.declareQueue("notifications", durable=True)

        amqpClient.bindQueue(queue=result.queue,
                             exchange=self._modelResultsExchange,
                             routingKey="")

        # Start consuming messages
        consumer = amqpClient.createConsumer(result.queue)

        for evt in amqpClient.readEvents():
          if isinstance(evt, amqp.messages.ConsumerMessage):
            self.messageHandler(evt)

          elif isinstance(evt, amqp.consumer.ConsumerCancellation):
            # Bad news: this likely means that our queue was deleted externally
            msg = "Consumer cancelled by broker: %r (%r)" % (evt, consumer)
            self._log.critical(msg)
            raise Exception(msg)

          else:
            self._log.warning("Unexpected amqp event=%r", evt)

    except amqp.exceptions.AmqpConnectionError:
      self._log.exception("RabbitMQ connection failed")
      raise
    except amqp.exceptions.AmqpChannelError:
      self._log.exception("RabbitMQ channel failed")
      raise
    except Exception as ex:
      self._log.exception("Error Streaming data: %s", ex)
      raise
    except KeyboardInterrupt:
      self._log.info("Stopping YOMP Notification Service: KeyboardInterrupt")
    finally:
      self._log.info("YOMP Notification Service is exiting")



if __name__ == "__main__":
  g_log = getExtendedLogger("NotificationService")
  logging_support.LoggingSupport.initService()
  try:
    NotificationService().run()
  except KeyboardInterrupt:
    pass
  except Exception as e:
    outp = StringIO.StringIO()
    ex_type, ex, tb = sys.exc_info()
    traceback.print_tb(tb, file=outp)
    outp.seek(0)
    g_log.info(outp.read())
    g_log.exception("Unexpected Error")
    sys.exit(1)
