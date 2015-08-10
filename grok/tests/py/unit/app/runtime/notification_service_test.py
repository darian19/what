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

"""Unit tests for notification service."""

import datetime
import unittest

from mock import Mock, patch
import pytz

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

import YOMP.app
from YOMP.app.runtime import notification_service



@patch.object(notification_service, "_queryAvailabilityZone",
              autospec=True, return_value=None)
@patch.object(notification_service, "repository", autospec=True)
class NotificationServiceTest(unittest.TestCase):
  """Unit tests for notification service."""

  def setUp(self):
    class NotificationSettingsSpec(object):
      uid = None
      windowsize = None
      sensitivity = None
      email_addr = None
      last_timestamp = None

    self.settingObj = Mock(spec_set=NotificationSettingsSpec,
                         uid="1", windowsize=3600, email_addr="foo@bar.com",
                         last_timestamp=None)

  def sendNotificationEmail(self, timezoneMock, notificationObj):
    """Returns mocked sendEmail"""
    # Mock out pytz timezone call
    timezoneMock.return_value = pytz.timezone("US/Eastern")

    # Send notification email
    service = notification_service.NotificationService()
    with patch("sqlalchemy.engine") as mockEngine:
      service.sendNotificationEmail(mockEngine, self.settingObj,
                                    notificationObj)

  @ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                        YOMP.app.config.baseConfigDir,
                        (("notifications", "sender",
                          "test@numenta.com"),))
  @patch('YOMP.app.runtime.notification_service.timezone')
  @patch("YOMP.app.runtime.notification_service.ses_utils.sendEmail")
  def testSendNotificationEmailDefault(self, sendEmailMock, timezoneMock,
                                       repoMock, _availabilityZoneMock):
    """TODO: Add description of test"""

    class MetricSpec(object):
      uid = None
      name = None
      server = None
      datasource = None
      tag_name = None
    metricRowMock = Mock(uid="abc",
                         spec_set=MetricSpec,
                         server="us-west-2/AWS/ELB/YOMP-docs-elb",
                         datasource="cloudwatch",
                         tag_name=None)
    metricRowMock.name = "AWS/ELB/RequestCount"

    repoMock.getMetric.return_value = metricRowMock

    class NotificationSpec(object):
      uid = None
      metric = None
      timestamp = None
    notificationRowMock = Mock(uid="xyz",
                               spec_set=NotificationSpec,
                               metric=metricRowMock,
                               timestamp=datetime.datetime(2014, 3, 19, 20, 23))

    sendEmailMock.return_value = None

    """
"RECIPIENT=%s Sending email. " % (notificationObj.uid,
                     metricObj.server, metricObj.uid, metricObj.name,
                     settingObj.uid, settingObj.email_addr))
    """

    self.sendNotificationEmail(timezoneMock, notificationRowMock)

    (_args, kwargs) = sendEmailMock.call_args_list[0]

    # Make assertions based on expected results given template at
    # conf/notification-body-default.tpl.  Changes to template MAY
    # require changes to these assertions

    self.assertTrue(
      kwargs["body"].startswith("YOMP has detected unusual behavior."))
    self.assertIn("Instance:\t\t\tus-west-2/AWS/ELB/YOMP-docs-elb",
                  kwargs["body"])
    self.assertIn("Metric:\t\t\tAWS/ELB/RequestCount",
                  kwargs["body"])
    self.assertIn("Time (UTC):\t\tWednesday, March 19, 2014 08:23 PM",
                  kwargs["body"])
    self.assertIn("Time (EDT):\t\tWednesday, March 19, 2014 04:23 PM",
                  kwargs["body"])
    self.assertTrue(kwargs["body"].endswith(("Email notification settings are "
                                             "controlled in the YOMP mobile ap"
                                             "plication.\r\n")))

    self.assertEqual(kwargs["toAddresses"], "foo@bar.com")


  @ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                        YOMP.app.config.baseConfigDir,
                        (("notifications", "sender",
                          "test@numenta.com"),))
  @patch('YOMP.app.runtime.notification_service.timezone')
  @patch("YOMP.app.runtime.notification_service.ses_utils.sendEmail")
  def testSendNotificationEmailCustom(self, sendEmailMock, timezoneMock,
                                      repoMock, _availabilityZoneMock):
    """TODO: Add description of test"""
    class MetricSpec(object):
      uid = None
      name = None
      server = None
      datasource = None
      tag_name = None
    metricRowMock = Mock(uid="abc",
                         spec_set=MetricSpec,
                         datasource="custom",
                         tag_name=None)
    metricRowMock.name = "cpu_usage"

    repoMock.getMetric.return_value = metricRowMock

    class NotificationSpec(object):
      uid = None
      metric = None
      timestamp = None
    notificationRowMock = Mock(uid="xyz",
                               spec_set=NotificationSpec,
                               metric=metricRowMock,
                               timestamp=datetime.datetime(2014, 3, 19, 20, 23))

    sendEmailMock.return_value = None

    self.sendNotificationEmail(timezoneMock, notificationRowMock)

    (_args, kwargs) = sendEmailMock.call_args_list[0]

    # Make assertions based on expected results given template at
    # conf/notification-body-default.tpl.  Changes to template MAY
    # require changes to these assertions

    self.assertTrue(
      kwargs["body"].startswith("YOMP has detected unusual behavior."))
    self.assertNotIn("Instance:\t",
                  kwargs["body"])
    self.assertIn("Metric:\t\t\tcpu_usage",
                  kwargs["body"])
    self.assertIn("Time (UTC):\t\tWednesday, March 19, 2014 08:23 PM",
                  kwargs["body"])
    self.assertIn("Time (EDT):\t\tWednesday, March 19, 2014 04:23 PM",
                  kwargs["body"])
    self.assertTrue(kwargs["body"].endswith(("Email notification settings are "
                                             "controlled in the YOMP mobile ap"
                                             "plication.\r\n")))

    self.assertEqual(kwargs["toAddresses"], "foo@bar.com")



if __name__ == "__main__":
  unittest.main()
