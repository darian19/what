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

import urlparse
import web

from htmengine import utils
from YOMP.app import repository
from YOMP.app.repository import schema
from YOMP.app.exceptions import ObjectNotFoundError
from YOMP.app.webservices import (AuthenticatedBaseHandler,
                                  ManagedConnectionWebapp)
from YOMP import YOMP_logging
from YOMP.YOMP_logging import anonymizeEmail


log = YOMP_logging.getExtendedLogger("webservices")

urls = (
  "/([-\w]*)/acknowledge", "NotificationHandler",
  "/([-\w]*)/see", "NotificationSeenHandler",
  "/([-\w]*)/history", "NotificationHistoryHandler",
  "/([-\w]*)/settings", "NotificationSettingsHandler",
  "/([-\w]*)/([-\w]*)", "NotificationHandler",
  "/([-\w]*)", "NotificationHandler",
 )


class NotificationHandler(AuthenticatedBaseHandler):
  fields = ["uid",
            "metric",
            "device",
            "windowsize",
            "timestamp",
            "seen",
            "acknowledged"]

  def GET(self, deviceId, notificationId):
    """
      Get single notification

      ::

          GET /_notifications/{deviceId}/{notificationId}

      Returns:

      ::

          {
            "uid": "e78599c4-758b-4c6e-87b1-daabaccff798",
            "timestamp": "2014-02-07 16:26:44",
            "metric": "e5511f295a474037a75bc966d02b67d2",
            "acknowledged": 0,
            "seen": 0,
            "windowsize": 3600,
            "device": "9a90eaf2-6374-4230-aa96-0830c0a737fe"
          }

      :param uid: Notification ID
      :type uid: str
      :param timestamp: Notification timestamp
      :type timestamp: timestamp
      :param metric: Metric that triggered notification
      :type metric: str
      :param acknowledged: Acknowledged status
      :type acknowledged: int
      :param seen: Seen status
      :type seen: int
      :param windowsize: Notification window in seconds during which no other
        notifications for a given instance should be sent to a given device
      :type windowsize: int
      :param device: Device ID
      :type device: str
    """
    # Update the last_timestamp for the notification device.
    try:
      with web.ctx.connFactory() as conn:
        repository.updateNotificationDeviceTimestamp(conn, deviceId)
    except ObjectNotFoundError:
      return web.notfound("Notification device not found: %s" % deviceId)

    try:
      with web.ctx.connFactory() as conn:
        notificationRow = repository.getNotification(conn,
                                                     notificationId,
                                                     NotificationHandler.fields)
      notificationDict = dict([(col, notificationRow[col])
                              for col in NotificationHandler.fields])

      if notificationRow["device"] != deviceId:
        return web.notfound("Device not found: %s" % deviceId)

      self.addStandardHeaders()
      return utils.jsonEncode(notificationDict)
    except ObjectNotFoundError:
      return web.notfound("Notification not found: %s" % notificationId)


  def DELETE(self, deviceId, notificationId=None):
    """
      Acknowledge notification

      ::

          DELETE /_notifications/{deviceId}/{notificationId}

      Or, acknowledge notifications in batches:

      ::

          DELETE /_notifications/{deviceId}

          [
            "e78599c4-758b-4c6e-87b1-daabaccff798",
            "4baa5ea6-5c94-46ee-b414-959bb973ddfb",
            "af531f3b-0e8b-41fa-94c4-a404526d791f",
            ...
          ]

      Acknowledged notifications will not appear in
      ``GET /_notifications/{deviceId}`` requests.
    """
    try:
      notificationIds = []

      if notificationId is not None:
        # Specific notification defined on url
        notificationIds.append(notificationId)
      else:
        # Read notifications from post data
        notificationIds = utils.jsonDecode(web.data())

      with web.ctx.connFactory() as conn:
        repository.batchAcknowledgeNotifications(conn, notificationIds)

      raise web.HTTPError(status="204 No Content")
    except (web.HTTPError) as ex:
      log.info(str(ex))
      raise ex
    except Exception as ex:
      log.exception("DELETE Failed")
      raise web.internalerror(ex)


  def POST(self, deviceId, notificationId=None):
    """
      Acknowledge notification (POST handler for
      /_notifications/{deviceId}/acknowledge)

      ::

          POST /_notifications/{deviceId}/acknowledge

          [
            "e78599c4-758b-4c6e-87b1-daabaccff798",
            "4baa5ea6-5c94-46ee-b414-959bb973ddfb",
            "af531f3b-0e8b-41fa-94c4-a404526d791f",
            ...
          ]

      Acknowledged notifications will not appear in
      ``GET /_notifications/{deviceId}`` requests.
    """
    return self.DELETE(deviceId, notificationId)



class NotificationSeenHandler(AuthenticatedBaseHandler):

  def POST(self, deviceId):
    """
      Mark notification as seen (POST handler for
      /_notifications/{deviceId}/see)

      ::

          POST /_notifications/{deviceId}/see

          [
            "e78599c4-758b-4c6e-87b1-daabaccff798",
            "4baa5ea6-5c94-46ee-b414-959bb973ddfb",
            "af531f3b-0e8b-41fa-94c4-a404526d791f",
            ...
          ]

      Seen notifications will not appear in
      ``GET /_notifications/{deviceId}`` requests.
    """
    try:
      notificationIds = utils.jsonDecode(web.data())

      with web.ctx.connFactory() as conn:
        repository.batchSeeNotifications(conn, notificationIds)
      raise web.HTTPError(status="204 No Content")
    except (web.HTTPError) as ex:
      log.info(str(ex))
      raise ex
    except Exception as ex:
      log.exception("POST Failed")
      raise web.internalerror(ex)



class NotificationHistoryHandler(AuthenticatedBaseHandler):

  def GET(self, deviceId):
    """
      Get notification history for device

      ::

          GET /_notifications/{deviceId}/history

      :param limit: (optional) max number of records to return
      :type limit: int

      Returns:

      ::

          [
            {
              "uid": "e78599c4-758b-4c6e-87b1-daabaccff798",
              "timestamp": "2014-02-07 16:26:44",
              "metric": "e5511f295a474037a75bc966d02b67d2",
              "acknowledged": 0,
              "windowsize": 3600,
              "device": "9a90eaf2-6374-4230-aa96-0830c0a737fe"
            },
            ...
          ]


      :param uid: Notification ID
      :type uid: str
      :param timestamp: Notification timestamp
      :type timestamp: timestamp
      :param metric: Metric that triggered notification
      :type metric: str
      :param acknowledged: Acknowledged status
      :type acknowledged: int
      :param seen: Seen status
      :type seen: int
      :param windowsize: Notification window in seconds during which no other
        notifications for a given instance should be sent to a given device
      :type windowsize: int
      :param device: Device ID
      :type device: str
    """
    # Update the last_timestamp for the notification device.
    try:
      with web.ctx.connFactory() as conn:
        repository.updateNotificationDeviceTimestamp(conn, deviceId)
    except ObjectNotFoundError:
      return web.notfound("Notification device not found: %s" % deviceId)

    queryParams = dict(urlparse.parse_qsl(web.ctx.env['QUERY_STRING']))
    if "limit" in queryParams:
      limit = int(queryParams["limit"])
    else:
      limit = None
    self.addStandardHeaders()
    with web.ctx.connFactory() as conn:
      notificationRows = repository.getUnseenNotificationList(
        conn, deviceId, limit, NotificationHandler.fields)

    notificationList = [dict([(col, notification[col])
                             for col in NotificationHandler.fields])
                        for notification in notificationRows]

    return utils.jsonEncode(notificationList)



class NotificationSettingsHandler(AuthenticatedBaseHandler):

  def GET(self, deviceId):
    """
      Get notification settings for device.

      ::

          GET /_notifications/{deviceId}/settings

      Returns:

      ::

          {
            "email_addr": "mail@host.tld",
            "windowsize": 3600,
            "sensitivity": 0.99999,
            "last_timestamp": "2014-02-06 00:00:00",
            "uid": "9a90eaf2-6374-4230-aa96-0830c0a737fe"
          }

      :param email_addr: Target email address associated with device
      :type email_addr: string
      :param windowsize: Notification window in seconds during which no other
        notifications for a given instance should be sent to a given device
      :type windowsize: int
      :param sensitivity: Anomaly score threshold that should trigger a
        notification
      :type sensitivity: float
      :param last_timestamp: Last updated timestamp
      :type last_timestamp: timestamp
      :param uid: Notification ID
      :type uid: str
    """
    if deviceId:
      try:
        with web.ctx.connFactory() as conn:
          settingsRow = repository.getDeviceNotificationSettings(conn, deviceId)

        settingsDict = dict([(col.name, settingsRow[col.name])
                            for col in schema.notification_settings.c])

        self.addStandardHeaders()
        return utils.jsonEncode(settingsDict)
      except ObjectNotFoundError:
        return web.notfound("Notification Settings not found: %s" % deviceId)
    else:
      log.error("Missing device ID, raising BadRequest exception")
      raise web.badrequest("Missing device ID")

  def PUT(self, deviceId):
    """
      Create, or update notification settings for device.

      ::

          PUT /_notifications/{deviceId}/settings

          {
            "email_addr": "mail@host.tld",
            "windowsize": 3600,
            "sensitivity": 0.99999
          }

      :param email_addr: Target email address associated with device
      :type email_addr: string
      :param windowsize: Notification window in seconds during which no other
        notifications for a given instance should be sent to a given device
      :type windowsize: int
      :param sensitivity: Anomaly score threshold that should trigger a
        notification
      :type sensitivity: float
    """
    data = web.data()

    if data:
      data = utils.jsonDecode(data) if isinstance(data, basestring) else data

      try:
        with web.ctx.connFactory() as conn:
          settingsRow = repository.getDeviceNotificationSettings(conn, deviceId)

        settingsDict = dict([(col.name, settingsRow[col.name])
                            for col in schema.notification_settings.c])
      except ObjectNotFoundError:
        settingsDict = None

      if settingsDict:
        # Update existing
        changes = dict()

        if "windowsize" in data:
          changes["windowsize"] = data["windowsize"]

        if "sensitivity" in data:
          changes["sensitivity"] = data["sensitivity"]

        if "email_addr" in data:
          changes["email_addr"] = data["email_addr"]

        if changes:
          log.info("Notification settings updated for email=%s, "
                   "deviceid=%s, %r",
                   anonymizeEmail(settingsDict["email_addr"]),
                   deviceId,
                   changes.keys())
          with web.ctx.connFactory() as conn:
            repository.updateDeviceNotificationSettings(conn, deviceId, changes)

        self.addStandardHeaders()
        for (header, value) in web.ctx.headers:
          if header == "Content-Type":
            web.ctx.headers.remove((header, value))
        raise web.HTTPError(status="204 No Content")

      else:
        # Create new settings

        if "windowsize" in data:
          windowsize = data["windowsize"]
        else:
          windowsize = 60*60 # TODO: Configurable default

        if "sensitivity" in data:
          sensitivity = data["sensitivity"]
        else:
          sensitivity = 0.99999 # TODO: Configurable default

        if "email_addr" in data:
          email_addr = data["email_addr"]
        else:
          email_addr = None

        with web.ctx.connFactory() as conn:
          repository.addDeviceNotificationSettings(conn,
                                                   deviceId,
                                                   windowsize,
                                                   sensitivity,
                                                   email_addr)
        log.info("Notification settings created for deviceid=%s", deviceId)
        self.addStandardHeaders()
        raise web.created("")

    else:
      # Metric data is missing
      log.error("Data is missing in request, raising BadRequest exception")
      raise web.badrequest("Metric data is missing")



app = ManagedConnectionWebapp(urls, globals())
