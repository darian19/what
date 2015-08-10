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
Utilities for reporting errors to Numenta via AWS/SES email.
"""
import datetime
import logging
import os
import socket

from boto.exception import BotoServerError
from boto.regioninfo import RegionInfo
import boto.ses



g_log = logging.getLogger(__name__)



def sendMonitorErrorEmail(monitorName, resourceName, message, isTest=False,
                          params=None):
  """
  Sends an email concerning a monitor related error.
  :param monitorName: Name of monitor detecting error
  :type monitorName: string
  :param resourceName: URL checked by this monitor
  :type resourceName: string
  :param message: a string message providing error details
  :type message: string
  :param isTest: flag signaling whether email is being sent as a test
  :type isTest: Boolean
  :param params: an optional dict that must contain the following keys:
                 senderAddress,
                 recipients,
                 awsRegion,
                 sesEndpoint,
                 awsAccessKeyId,
                 awsSecretAccessKey
  :type params: dict
  """
  subject = "Test Email: " if isTest else ""
  subject += "Monitor {0} has detected an error!".format(monitorName)

  # Add current datetime
  currentDatetime = datetime.datetime.now().ctime()
  monitorInfo = "Current Datetime:\t%s\n" % currentDatetime

  # Add name of machine running monitor
  try:
    hostName = socket.gethostname()
  except socket.error:
    hostName = "Couldn't get monitor host name"
    g_log.exception("Couldn't get monitor host name")
  monitorInfo += "Monitor running on:\t%s\n" % hostName

  # Add name of resource being monitored
  monitorInfo += "Resource being monitored:\t%s\n" % resourceName

  body = "This a test email only.\n" if isTest else ""
  body += "*Monitor Info*\n{0}\n*Error Details*\n{1}".format(monitorInfo,
                                                             message)

  sendErrorEmail(subject, body, params=params)



def sendErrorEmail(subject, body, params=None):
  """
  Report an error via email.

  Expects the following environment variables to be defined:
    ERROR_REPORT_EMAIL_AWS_REGION: AWS region for error report email.
    ERROR_REPORT_EMAIL_SES_ENDPOINT: SES endpoint for error report email.
    ERROR_REPORT_EMAIL_SENDER_ADDRESS: Sender address for error report email.
    ERROR_REPORT_EMAIL_RECIPIENTS: Recipients error report email. Email "
      addresses need to be comma separated.
      Example => 'recipient1@numenta.com, recipient2@numenta.com'
    AWS_ACCESS_KEY_ID: AWS access key ID for error report email.
    AWS_SECRET_ACCESS_KEY: AWS secret access key for error report email.

  Alternatively, these can be passed in as a dict:
  :param subject: Email subject
  :type subject: string
  :param body: Email body
  :type body: string
  :param params: an optional dict that must contain the following keys:
                 senderAddress,
                 recipients,
                 awsRegion,
                 sesEndpoint,
                 awsAccessKeyId,
                 awsSecretAccessKey
  """
  if params is None:
    params = _getErrorReportingParamsFromEnv()

  sendEmailViaSES(subject=subject, body=body, **params)



def validateErrorReportingEnvVars():
  """
  Peform basic validation of environment variables that are necessary for
  error-reporting.

  :raises ValueError: if a required environment variable is undefined or empty
  """
  # This performs the necessary validation
  _getErrorReportingParamsFromEnv()



def sendEmailViaSES(subject,
                    body,
                    recipients,
                    awsRegion,
                    sesEndpoint,
                    senderAddress,
                    awsAccessKeyId,
                    awsSecretAccessKey):
  """
  Send an email via AWS SES.

  :param subject: Email subject header
  :type subject: string
  :param body: Email body
  :type body: string
  :param recipients: Email recipient(s)
  :type recipients: sequence of strings
  :param awsRegion: AWS region for error report email
  :type awsRegion: string
  :param sesEndpoint: AWS/SES endpoint for error report email
  :type sesEndpoint: string
  :param senderAddress: Sender address for error report email
  :type senderAddress: string
  :param awsAccessKeyId: AWS access key ID for error report email
  :type awsAccessKeyId: string
  :param awsSecretAccessKey: AWS secret access key for error report email
  :type awsSecretAccessKey: string
  """
  try:
    regionInfo = RegionInfo(connection=None,
                            name=awsRegion,
                            endpoint=sesEndpoint,
                            connection_cls=None)

    conn = boto.ses.SESConnection(region=regionInfo,
                                  aws_access_key_id=awsAccessKeyId,
                                  aws_secret_access_key=awsSecretAccessKey)
  
    conn.send_email(source=senderAddress,
                    subject=subject,
                    body=body,
                    to_addresses=recipients)
    g_log.info("Called boto.ses.SESConnection.send_email. This does not "
               "necessarily mean that the email was successfully sent.")
    
  except BotoServerError:
    g_log.exception("Failed to send email via AWS/SES. subject='%s'" %
                    (subject,))
    raise
  except socket.gaierror:
    g_log.exception("Failed to connect to AWS/SES. Region=%s. SesEndpoint=%s" %
                    (awsRegion, sesEndpoint))
    raise



def _getErrorReportingParamsFromEnv():
  """
  Load error-reporting args from environment variables; performs basic
  validation on presence of their contents.

  :returns: dict with the following attributes:
    recipients: Email recipient(s); sequence of strings
    awsRegion: AWS region for error report email; string
    sesEndpoint: AWS/SES endpoint for error report email; string
    senderAddress: Sender address for error report email; string
    awsAccessKeyId: AWS access key ID for error report email; string
    awsSecretAccessKey: AWS secret access key for error report email; string

  :raises ValueError: if a required environment variable is undefined or empty
  """
  # Extract error-reporting parameters from environment variables
  senderAddress = os.environ.get("ERROR_REPORT_EMAIL_SENDER_ADDRESS")
  if senderAddress:
    senderAddress = senderAddress.strip()
  if not senderAddress:
    raise ValueError("Environment variable ERROR_REPORT_EMAIL_SENDER_ADDRESS "
                     "is blank or undefined")

  recipients = os.environ.get("ERROR_REPORT_EMAIL_RECIPIENTS")
  if recipients:
    recipients = [addr for addr in (s.strip() for s in recipients.split(","))
                  if addr]
  if not recipients:
    raise ValueError("Unspecified recipient(s) in "
                     "ERROR_REPORT_EMAIL_RECIPIENTS environment variable")

  awsRegion = os.environ.get("ERROR_REPORT_EMAIL_AWS_REGION")
  if awsRegion:
    awsRegion = awsRegion.strip()
  if not awsRegion:
    raise ValueError("Environment variable ERROR_REPORT_EMAIL_AWS_REGION "
                     "is blank or undefined")

  sesEndpoint = os.environ.get("ERROR_REPORT_EMAIL_SES_ENDPOINT")
  if sesEndpoint:
    sesEndpoint = sesEndpoint.strip()
  if not sesEndpoint:
    raise ValueError("Environment variable ERROR_REPORT_EMAIL_SES_ENDPOINT "
                     "is blank or undefined")

  awsAccessKeyId = os.environ.get("AWS_ACCESS_KEY_ID")
  if awsAccessKeyId:
    awsAccessKeyId = awsAccessKeyId.strip()
  if not awsAccessKeyId:
    raise ValueError("Environment variable AWS_ACCESS_KEY_ID "
                     "is blank or undefined")

  awsSecretAccessKey = os.environ.get("AWS_SECRET_ACCESS_KEY")
  if awsSecretAccessKey:
    awsSecretAccessKey = awsSecretAccessKey.strip()
  if not awsSecretAccessKey:
    raise ValueError("Environment variable AWS_SECRET_ACCESS_KEY "
                     "is blank or undefined")

  return dict(
    senderAddress=senderAddress,
    recipients=recipients,
    awsRegion=awsRegion,
    sesEndpoint=sesEndpoint,
    awsAccessKeyId=awsAccessKeyId,
    awsSecretAccessKey=awsSecretAccessKey
  )
