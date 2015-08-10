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

"""Utility functions for AWS SES."""

import boto.ses
from boto.regioninfo import RegionInfo

from YOMP.app import config



_SES_ENDPOINTS = {
    "eu-west-1": "email.eu-west-1.amazonaws.com",
    "us-east-1": "email.us-east-1.amazonaws.com",
    "us-west-2": "email.us-west-2.amazonaws.com",
}



def sendEmail(subject, body, toAddresses, region=None, sender=None):
  """Send an email with AWS SES.

  :param subject: Email subject header
  :param body: Email body
  :param toAddresses: Email recipient(s)
  :param region: AWS Region
  :param sender: Email sender
  :returns: SES Message ID or None
  """
  if region is None:
    region = config.get("aws", "default_region")

  if sender is None:
    sender = config.get("notifications", "sender")

  if region not in _SES_ENDPOINTS:
    raise ValueError("Region '%s' provided does not exist in known SES region "
                     "endpoints set." % region)

  regionInfo = RegionInfo(None, region, _SES_ENDPOINTS[region])

  awsAccessKeyId = config.get("notifications", "aws_access_key_id")
  awsSecretAccessKey = config.get("notifications", "aws_secret_access_key")
  if awsAccessKeyId == "" or awsSecretAccessKey == "":
    awsAccessKeyId = config.get("aws", "aws_access_key_id")
    awsSecretAccessKey = config.get("aws", "aws_secret_access_key")

  conn = boto.ses.SESConnection(region=regionInfo,
                                aws_access_key_id=awsAccessKeyId,
                                aws_secret_access_key=awsSecretAccessKey)

  # Send the email
  result = conn.send_email(source=sender,
                           subject=subject,
                           body=body,
                           to_addresses=toAddresses)

  # Return the SES message ID, or None if there is no message ID in the response
  if "SendEmailResponse" in result:
    if "SendEmailResult" in result["SendEmailResponse"]:
      if "MessageId" in result["SendEmailResponse"]["SendEmailResult"]:
        return result["SendEmailResponse"]["SendEmailResult"]["MessageId"]
  return None
