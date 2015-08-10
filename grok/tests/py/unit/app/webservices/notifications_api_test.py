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
import copy
import os
import datetime
import json
import unittest
import uuid
from paste.fixture import TestApp
from mock import Mock, patch

import YOMP.app
from YOMP.app import repository
from htmengine import utils as app_utils
from YOMP.app.exceptions import ObjectNotFoundError
from YOMP.app.webservices import notifications_api

from YOMP.test_utils.app.webservices import getDefaultHTTPHeaders


@patch.object(repository, "engineFactory", autospec=True)
class TestNotificationsHandler(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.model_list = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/models_list.json")))


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(notifications_api.app.wsgifunc())

    # Set up dummy notification assets
    self.deviceId = str(uuid.uuid4())
    self.notificationId = str(uuid.uuid4())

    metricParams = {u"region":u"us-east-1", u"DBInstanceIdentifier":u"YOMPdb2"}
    self.metric = {"uid": u"cebe9fab-f416-4845-8dab-02d292244112",
                   "datasource": u"cloudwatch",
                   "name": u"AWS/RDS/DatabaseConnections",
                   "description": u"The number of database connections in use "
                                  u"by Amazon RDS database",
                   "server": u"YOMPdb2",
                   "location": u"us-east-1",
                   "parameters": app_utils.jsonEncode(metricParams),
                   "status": 1,
                   "message":None,
                   "collector_error": None,
                   "last_timestamp": u"2013-08-15 21:25:00",
                   "poll_interval": 60,
                   "tag_name": None,
                   "model_params": None,
                   "last_rowid": 20277}

    self.notification = {"uid": self.deviceId,
                         "metric": self.metric["uid"],
                         "device": self.deviceId,
                         "windowsize": 3600,
                         "timestamp": datetime.datetime.utcnow(),
                         "acknowledged": 0,
                         "seen": 0,
                         "ses_message_id": None,
                         "rowid": 666}

    self.settings = {"uid": self.deviceId,
                     "windowsize": 3600,
                     "sensitivity": 0.99999,
                     "email_addr": "mail@host.tld",
                     "last_timestamp": datetime.datetime.utcnow()}


  @patch.object(repository, "getNotification", autospec=True)
  def testGETNotification(self, getNotificationMock, _engineMock):
    """ Test GETing single notification from Notification API
    """
    getNotificationMock.return_value = self.notification


    response = self.app.get("/%s/%s" % (self.notification["device"],
                                        self.notification["uid"]),
                            headers=self.headers)

    self.assertEqual(response.status, 200)
    result = json.loads(response.body)

    notificationDict = copy.deepcopy(self.notification)
    del notificationDict["ses_message_id"]
    del notificationDict["rowid"]

    jsonNotification = json.loads(app_utils.jsonEncode(notificationDict))

    self.assertDictEqual(result, jsonNotification)


  @patch.object(repository, "batchAcknowledgeNotifications", autospec=True)
  def testDELETENotification(self, batchAcknowledgeMock, engineMock):
    """ Test notification DELETE endpoint
    """
    response = self.app.delete("/%s/%s" %
                               (self.notification["device"],
                                self.notification["uid"]),
                               headers=self.headers)

    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    self.assertTrue(batchAcknowledgeMock.called)
    batchAcknowledgeMock.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value,
      [self.notification["uid"]])


  @patch.object(repository, "batchAcknowledgeNotifications", autospec=True)
  def testDELETENotificationBatch(self, batchAcknowledgeMock, engineMock):
    """ Test notification DELETE endpoint (batch)
    """
    uids = [self.notification["uid"],
            self.notification["uid"]]
    response = self.app.delete("/%s" % self.notification["device"],
                               app_utils.jsonEncode(uids),
                               headers=self.headers)

    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    self.assertTrue(batchAcknowledgeMock.called)
    batchAcknowledgeMock.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value, uids)


  @patch.object(repository, "batchAcknowledgeNotifications", autospec=True)
  def testAcknowledgeNotificationBatch(self, batchAcknowledgeMock, engineMock):
    """ Test notification POST endpoint (batch)
    """
    uids = [self.notification["uid"],
            self.notification["uid"]]
    response = self.app.post("/%s/acknowledge" %
                             self.notification["device"],
                             app_utils.jsonEncode(uids),
                             headers=self.headers)

    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    self.assertTrue(batchAcknowledgeMock.called)
    batchAcknowledgeMock.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value, uids)


  @patch.object(repository, "batchSeeNotifications", autospec=True)
  def testSeeNotificationBatch(self, batchaSeeMock, engineMock):
    """ Test notification POST endpoint (batch)
    """
    uids = [self.notification["uid"],
            self.notification["uid"]]
    response = self.app.post("/%s/see" % self.notification["device"],
                             app_utils.jsonEncode(uids),
                             headers=self.headers)

    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    self.assertTrue(batchaSeeMock.called)
    batchaSeeMock.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value, uids)


  @patch("YOMP.app.webservices.notifications_api.repository", autospec=True)
  def testGETNotificationHistory(self, repositoryMock, _engineMock):
    """ Test GET notification history
    """
    repositoryMock.getUnseenNotificationList = Mock(return_value = [self.notification])

    response = self.app.get("/%s/history" %
                            self.notification["device"],
                            headers=self.headers)

    self.assertEqual(response.status, 200)
    result = json.loads(response.body)

    notificationDict = copy.deepcopy(self.notification)
    del notificationDict["ses_message_id"]
    del notificationDict["rowid"]
    jsonNotifications = json.loads(app_utils.jsonEncode([notificationDict]))
    self.assertSequenceEqual(result, jsonNotifications)


  @patch("YOMP.app.webservices.notifications_api.repository", autospec=True)
  def testGETNotificationSettings(self, repositoryMock, _engineMock):
    """ Test GET notification settings
    """
    repositoryMock.getDeviceNotificationSettings = Mock(return_value = self.settings)

    response = self.app.get("/%s/settings" %
                            self.notification["device"],
                            headers=self.headers)

    self.assertEqual(response.status, 200)
    result = json.loads(response.body)

    settingsDict = copy.deepcopy(self.settings)
    jsonNotificationSettings = json.loads(app_utils.jsonEncode(settingsDict))

    self.assertDictEqual(result, jsonNotificationSettings)


  @patch("YOMP.app.webservices.notifications_api.repository", autospec=True)
  def testPUTNotificationSettingsUpdate(self, repositoryMock, engineMock):
    """ Test PUT notification settings (update)
    """
    repositoryMock.getDeviceNotificationSettings = Mock(return_value=self.settings)

    update = {
      "windowsize": 3601,
      "sensitivity": 0.999999,
      "email_addr": "updated@host.tld"}

    response = self.app.put("/%s/settings" %
                            self.notification["device"],
                            app_utils.jsonEncode(update),
                            headers=self.headers)

    self.assertEqual(response.status, 204)
    self.assertFalse(response.body)
    repositoryMock.updateDeviceNotificationSettings.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value,
      self.notification["device"],
      {"windowsize": 3601,
       "sensitivity": 0.999999,
       "email_addr": "updated@host.tld"})


  @patch("YOMP.app.webservices.notifications_api.repository", autospec=True)
  def testPUTNotificationSettingsCreate(self, repositoryMock, engineMock):
    """ Test PUT notification settings (create)
    """

    repositoryMock.getDeviceNotificationSettings.side_effect = (
      ObjectNotFoundError("No settings yet"))

    update = {
      "windowsize": 3601,
      "sensitivity": 0.999999,
      "email_addr": "updated@host.tld"}



    response = self.app.put("/%s/settings" %
                            self.notification["device"],
                            app_utils.jsonEncode(update),
                            headers=self.headers)

    self.assertEqual(response.status, 201)
    self.assertFalse(response.body)
    self.assertTrue(repositoryMock.getDeviceNotificationSettings.called)
    repositoryMock.addDeviceNotificationSettings.assert_called_with(
      engineMock.return_value.connect.return_value.__enter__.return_value,
      self.notification["device"],
      update["windowsize"],
      update["sensitivity"],
      update["email_addr"])


if __name__ == "__main__":
  unittest.main()
