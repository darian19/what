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

"""Tests for AWS SES utility functions."""

import unittest

from boto.ses.connection import SESConnection
from mock import Mock, patch

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from YOMP.app import config
from YOMP.app.aws import ses_utils



class SesUtilsTest(unittest.TestCase):


  @ConfigAttributePatch(config.CONFIG_NAME,
                        config.baseConfigDir,
                        (("notifications", "aws_access_key_id", "mockKeyId"),
                         ("notifications", "aws_secret_access_key", "mockKey")))
  @patch("boto.ses.SESConnection")
  def testSendEmailNotificationsCredentialsNoMessageID(self, sesConnectionMock):
    subject = "subject"
    body = "body"
    toAddresses = ("jdoe@numenta.com",)
    region = "us-west-2"
    sender = "mock@numenta.com"

    connMock = Mock(spec_set=SESConnection)
    connMock.send_email.return_value = {}
    sesConnectionMock.return_value = connMock

    messageID = ses_utils.sendEmail(subject=subject,
                                    body=body,
                                    toAddresses=toAddresses,
                                    region=region,
                                    sender=sender)

    self.assertIsNone(messageID)
    args = sesConnectionMock.call_args[1]
    self.assertEqual(args["aws_access_key_id"], "mockKeyId")
    self.assertEqual(args["aws_secret_access_key"], "mockKey")
    connMock.send_email.assert_called_once_with(source=sender,
                                                subject=subject,
                                                body=body,
                                                to_addresses=toAddresses)


  @ConfigAttributePatch(config.CONFIG_NAME,
                        config.baseConfigDir,
                        (("notifications", "aws_access_key_id", ""),
                         ("notifications", "aws_secret_access_key", ""),
                         ("aws", "aws_access_key_id", "a"),
                         ("aws", "aws_secret_access_key", "b")))
  @patch("boto.ses.SESConnection")
  def testSendEmailAwsCredentialsNoMessageID(self, sesConnectionMock):
    subject = "subject"
    body = "body"
    toAddresses = ("jdoe@numenta.com",)
    region = "us-west-2"
    sender = "me@numenta.com"

    connMock = Mock(spec_set=SESConnection)
    sesConnectionMock.return_value = connMock
    connMock.send_email.return_value = {}

    messageID = ses_utils.sendEmail(
        subject=subject, body=body, toAddresses=toAddresses,
        region=region, sender=sender)

    self.assertIsNone(messageID)
    connMock.send_email.assert_called_once_with(source=sender, subject=subject,
                                                body=body,
                                                to_addresses=toAddresses)
    args = sesConnectionMock.call_args[1]
    self.assertEqual(args["aws_access_key_id"], "a")
    self.assertEqual(args["aws_secret_access_key"], "b")


  @ConfigAttributePatch(config.CONFIG_NAME,
                        config.baseConfigDir,
                        (("notifications", "sender", "mock@numenta.com"),
                         ("notifications", "aws_access_key_id", "mockKeyId"),
                         ("notifications", "aws_secret_access_key", "mockKey"),
                         ("aws", "default_region", "us-west-2")))
  @patch("boto.ses.SESConnection")
  def testSendEmailNoRegionOrSender(self, sesConnectionMock):
    subject = "subject"
    body = "body"
    toAddresses = ("jdoe@numenta.com",)

    connMock = Mock(spec_set=SESConnection)
    sesConnectionMock.return_value = connMock
    connMock.send_email.return_value = {}

    messageID = ses_utils.sendEmail(subject=subject, body=body,
                                    toAddresses=toAddresses)

    self.assertIsNone(messageID)
    connMock.send_email.assert_called_once_with(source="mock@numenta.com",
                                                subject=subject, body=body,
                                                to_addresses=toAddresses)
    args = sesConnectionMock.call_args[1]
    self.assertEqual(args["aws_access_key_id"], "mockKeyId")
    self.assertEqual(args["aws_secret_access_key"], "mockKey")


  @ConfigAttributePatch(config.CONFIG_NAME,
                        config.baseConfigDir,
                        (("notifications", "aws_access_key_id", "mockKeyId"),
                         ("notifications", "aws_secret_access_key", "mockKey")))
  @patch("boto.ses.SESConnection")
  def testSendEmailDefaultSenderWithMessageID(self, sesConnectionMock):
    subject = "subject"
    body = "body"
    toAddresses = ("jdoe@numenta.com",)
    region = "us-west-2"
    sender = "mock@numenta.com"

    connMock = Mock(spec_set=SESConnection)
    sesConnectionMock.return_value = connMock
    connMock.send_email.return_value = {
        "SendEmailResponse": {"SendEmailResult": {"MessageId": "messageID"}}}

    messageID = ses_utils.sendEmail(
        subject=subject, body=body, toAddresses=toAddresses,
        region=region, sender=sender)

    self.assertEqual(messageID, "messageID")
    connMock.send_email.assert_called_once_with(
        source=sender, subject=subject, body=body, to_addresses=toAddresses)


  def testSendEmailInvalidRegion(self):
    with self.assertRaises(ValueError) as cm:
      ses_utils.sendEmail(subject="subject",
                          body="body",
                          toAddresses=("jdoe@numenta.com",),
                          region="region",
                          sender="me@numenta.com")
    self.assertIn("Region 'region' provided does not exist in known SES region "
                  "endpoints set.", cm.exception.message)



if __name__ == "__main__":
  unittest.main()
