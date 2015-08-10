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
Script to check if twitter screen names are still valid. 
Email notifications are sent for unmapped screen names.  
Each time a screen name is reported successfully, we add it to a table keeping 
track of unmapped screen names that were already reported -- to avoid duplicate
emails reporting the same unmapped screen name. 

This script is intended to be called periodically via crontab or equivalent.
"""

import logging
from optparse import OptionParser
import os

import tweepy

from nta.utils import error_reporting
from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors import logging_support
from twitter_direct_agent import loadMetricSpecs
from twitter_direct_agent import DEFAULT_CONSUMER_KEY
from twitter_direct_agent import DEFAULT_CONSUMER_SECRET
from twitter_direct_agent import DEFAULT_ACCESS_TOKEN
from twitter_direct_agent import DEFAULT_ACCESS_TOKEN_SECRET



# For emailing
ERROR_REPORT_EMAIL_AWS_REGION = os.environ.get(
  "ERROR_REPORT_EMAIL_AWS_REGION")
ERROR_REPORT_EMAIL_SES_ENDPOINT = os.environ.get(
  "ERROR_REPORT_EMAIL_SES_ENDPOINT")
ERROR_REPORT_EMAIL_SENDER_ADDRESS = os.environ.get(
  "ERROR_REPORT_EMAIL_SENDER_ADDRESS")
AWS_ACCESS_KEY_ID = os.environ.get(
  "AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get(
  "AWS_SECRET_ACCESS_KEY")
ERROR_REPORT_EMAIL_RECIPIENTS = os.environ.get(
  "ERROR_REPORT_EMAIL_RECIPIENTS")



# Initialize logging
g_log = logging.getLogger("check_twitter_screen_names")



def _checkTwitterScreenNames(consumerKey,
                            consumerSecret,
                            accessToken,
                            accessTokenSecret,
                            errorReportEmailAwsRegion,
                            errorReportEmailSesEndpoint,
                            errorReportEmailSenderAddress,
                            awsAccessKeyId,
                            awsSecretAccessKey,
                            errorReportEmailRecipients):
  """ 
  Check if twitter screen names are still valid. 
  Email notifications are sent for unmapped screen names.  
  Each time an unmapped screen name is reported successfully, we add it to a
  table keeping track of unmapped screen names that were already reported -- to
  avoid duplicate emails reporting the same unmapped screen name. 

  :param consumerKey: Twitter consumer key
  :param consumerSecret: Twitter consumer secret
  :param accessToken: Twitter access token
  :param accessTokenSecret: Twitter access token secret
  :param errorReportEmailAwsRegion: AWS region for error report email
  :type errorReportEmailAwsRegion: string
  :param errorReportEmailSesEndpoint: AWS/SES endpoint for error report email
  :type errorReportEmailSesEndpoint: string
  :param errorReportEmailSenderAddress: Sender address for error report email
  :type errorReportEmailSenderAddress: string
  :param awsAccessKeyId: AWS access key ID for error report email
  :type awsAccessKeyId: string
  :param awsSecretAccessKey: AWS secret access key for error report email
  :type awsSecretAccessKey: string
  :param errorReportEmailRecipients: Recipients error report email
  :type errorReportEmailRecipients: list of strings
  """
  
  authHandler = tweepy.OAuthHandler(consumerKey, consumerSecret)
  authHandler.set_access_token(accessToken, accessTokenSecret)    
  tweepyApi = tweepy.API(authHandler)

  # list of screen names
  metricSpecs = loadMetricSpecs()
  screenNames = []
  for spec in metricSpecs:
    for screenName in spec.screenNames:
      screenNames.append(screenName.lower())

  unmappedScreenNames = _resolveUnmappedScreenNames(tweepyApi, screenNames)
  
  if unmappedScreenNames:
    g_log.error("No mappings for screenNames=%s", unmappedScreenNames)
    
    if errorReportEmailRecipients:
      _reportUnmappedScreenNames(unmappedScreenNames=unmappedScreenNames,
                                 awsRegion=errorReportEmailAwsRegion,
                                 sesEndpoint=errorReportEmailSesEndpoint,
                                 senderAddress=errorReportEmailSenderAddress,
                                 awsAccessKeyId=awsAccessKeyId,
                                 awsSecretAccessKey=awsSecretAccessKey,
                                 recipients=errorReportEmailRecipients)
    else:
      g_log.error("Email about unmapped screen names can't be sent. "
                  "Environment variable ERROR_REPORT_EMAIL_RECIPIENTS is "
                  "undefined.")

  else:
    # clearing rows of twitter_handle_failures table
    _deleteScreenNameFailures()
    g_log.info("All screen names resolved successfully")



def _resolveUnmappedScreenNames(tweepyApi, screenNames):
  """ 
  Map the given Twitter Screen Names to the corresponding User IDs and return

  :param tweepyApi: tweepy API object configured with the necessary AuthHandler
  :type tweepyApi: tweepy.API
  :param screenNames: list of screen names
  :type screenNames: list of strings
  :returns: set of unmapped screen names
  :rtype: set of strings
  """
  
  # Get twitter Ids corresponding to screen names and build a userId-to-metric
  # map
  maxLookupItems = 100  # twitter's users/lookup limit
  lookupSlices = [screenNames[n:n + maxLookupItems]
                  for n in xrange(0, len(screenNames), maxLookupItems)]
  mappedScreenNames = []
  for names in lookupSlices:
    try:
      users = tweepyApi.lookup_users(screen_names=names)
    except Exception:
      g_log.exception("tweepyApi.lookup_users failed for names=%s", names)
      raise

    # NOTE: Users that weren't found will be missing from results
    for user in users:
      screenName = user.screen_name.lower()
      userId = user.id_str
      g_log.debug("screenName=%s mapped to userId=%s", screenName, userId)

      mappedScreenNames.append(screenName)

  unmappedScreenNames = set(screenNames).difference(mappedScreenNames)
  return unmappedScreenNames



@collectorsdb.retryOnTransientErrors
def _saveScreenNameFailure(unmappedScreenName):
  """
  Save unmapped twitter handle in database

  :param unmappedScreenName: the twitter handle that is not valid anymore
  :type unmappedScreenName: string
  """

  ins = (collectorsdb.schema.twitterHandleFailures.insert()
         .prefix_with('IGNORE', dialect="mysql")
         .values(handle=unmappedScreenName))

  collectorsdb.engineFactory().execute(ins)

  g_log.info("Saved unmapped twitter handle; handle=%s", unmappedScreenName)



@collectorsdb.retryOnTransientErrors
def _deleteScreenNameFailures():
  """
  Clear rows from the twitter_handle_failures table. 
  """

  result = collectorsdb.engineFactory().execute(
    collectorsdb.schema.twitterHandleFailures.delete())

  if result.rowcount:
    g_log.info("Deleted %s rows from %s table",
               result.rowcount, collectorsdb.schema.twitterHandleFailures)



@collectorsdb.retryOnTransientErrors
def _screenNameFailureReported(screenName):
  """ Check if a specific twitter handle already exists in the
  tweet_handle_failures table.

  :param screenName: twitter handle
  :type screenName: string
  :returns: True, if twitter handle is already in the table. False, otherwise
  :rtype: Boolean
  """
  table = collectorsdb.schema.twitterHandleFailures

  sel = (table.select().where(table.c.handle == screenName))
  rows = collectorsdb.engineFactory().execute(sel)

  return rows.rowcount != 0



def _reportUnmappedScreenNames(unmappedScreenNames,
                               awsRegion,
                               sesEndpoint,
                               senderAddress,
                               awsAccessKeyId,
                               awsSecretAccessKey,
                               recipients):
  """
  Report unmapped twitter handles. 
  Notify via email if unmapped screen name has not already been reported.
  After emailing, log unmapped twitter handle in DB to prevent re-reporting.

  :param unmappedScreenNames: the twitter handles that are not valid anymore
  :type unmappedScreenNames: list of strings
  :param awsRegion: AWS region for report email
  :type awsRegion: string
  :param sesEndpoint: AWS/SES endpoint for report email
  :type sesEndpoint: string
  :param senderAddress: Sender address for report email
  :type senderAddress: string
  :param awsAccessKeyId: AWS access key ID for report email
  :type awsAccessKeyId: string
  :param awsSecretAccessKey: AWS secret access key for report email
  :type awsSecretAccessKey: string
  :param recipients: Recipients report email
  :type recipients: sequence of strings
    
  """
  
  for unmappedScreenName in unmappedScreenNames:
    if not _screenNameFailureReported(unmappedScreenName):
  
      subject = "Twitter handle '%s' is invalid" % unmappedScreenName
      body = "Twitter handle '%s' needs to be updated." % unmappedScreenName
      try:
        error_reporting.sendEmailViaSES(
          subject=subject, 
          body=body, 
          recipients=recipients, 
          awsRegion=awsRegion,
          sesEndpoint=sesEndpoint,
          senderAddress=senderAddress,
          awsAccessKeyId=awsAccessKeyId,
          awsSecretAccessKey=awsSecretAccessKey)
      except Exception:
        g_log.exception("sendEmailViaSES faield")
        raise
      else:
        # Create entry in DB for this unmapped handle.
        # Since it was successfully reported and we don't want to report it
        # anymore.
        _saveScreenNameFailure(unmappedScreenName)
    else:
      g_log.info("Invalid twitter handle '%s' already reported. Will not send "
                 "email again." % unmappedScreenName)



def _parseArgs():
  """
  :returns: dict of arg names and values:
    consumerKey
    consumerSecret
    accessToken
    accessTokenSecret
    errorReportEmailAwsRegion
    errorReportEmailSesEndpoint
    errorReportEmailSenderAddress
    awsAccessKeyId
    awsSecretAccessKey
    errorReportEmailRecipients
  """
  
  helpString = (
    "%prog [options]\n"
    "This script sends email notifications to report unmapped screen names, if "
    "they haven't already been reported.\n"
    "/!\ This script depends on the following environment variables:\n"
    "* TAURUS_TWITTER_CONSUMER_KEY: Twitter consumer key.\n"
    "* TAURUS_TWITTER_CONSUMER_SECRET: Twitter consumer secret.\n"
    "* TAURUS_TWITTER_ACCESS_TOKEN: Twitter access token.\n"
    "* TAURUS_TWITTER_ACCESS_TOKEN_SECRET: Twitter access token secret.\n"
    "* ERROR_REPORT_EMAIL_AWS_REGION: AWS region for error report email.\n"
    "* ERROR_REPORT_EMAIL_SES_ENDPOINT: SES endpoint for error report email.\n"
    "* ERROR_REPORT_EMAIL_SENDER_ADDRESS: Sender address for error report "
    "email.\n"
    "* AWS_ACCESS_KEY_ID: AWS access key ID for error report email.\n"
    "* AWS_SECRET_ACCESS_KEY: AWS secret access key for error report email.\n"
    "* ERROR_REPORT_EMAIL_RECIPIENTS: Recipients error report email. Email "
    "addresses need to be comma separated.\n"
    "                                 Example => 'recipient1@numenta.com, "
    "recipient2@numenta.com'\n")

  parser = OptionParser(helpString)

  parser.add_option(
      "--ckey",
      action="store",
      type="string",
      dest="consumerKey",
      default=DEFAULT_CONSUMER_KEY,
      help="Twitter consumer key [default: %default]")

  parser.add_option(
      "--csecret",
      action="store",
      type="string",
      dest="consumerSecret",
      default=DEFAULT_CONSUMER_SECRET,
      help="Twitter consumer secret [default: %default]")

  parser.add_option(
      "--atoken",
      action="store",
      type="string",
      dest="accessToken",
      default=DEFAULT_ACCESS_TOKEN,
      help="Twitter access token [default: %default]")

  parser.add_option(
      "--atokensecret",
      action="store",
      type="string",
      dest="accessTokenSecret",
      default=DEFAULT_ACCESS_TOKEN_SECRET,
      help="Twitter access token secret [default: %default]")
  
  parser.add_option(
      "--awsregion",
      action="store",
      type="string",
      dest="errorReportEmailAwsRegion",
      default=ERROR_REPORT_EMAIL_AWS_REGION,
      help="AWS region for error report email [default: %default]")
  
  parser.add_option(
      "--sesendpoint",
      action="store",
      type="string",
      dest="errorReportEmailSesEndpoint",
      default=ERROR_REPORT_EMAIL_SES_ENDPOINT,
      help="SES endpoint for error report email [default: %default]")
  
  parser.add_option(
      "--senderaddress",
      action="store",
      type="string",
      dest="errorReportEmailSenderAddress",
      default=ERROR_REPORT_EMAIL_SENDER_ADDRESS,
      help="Sender address for error report email [default: %default]")
  
  parser.add_option(
      "--awsid",
      action="store",
      type="string",
      dest="awsAccessKeyId",
      default=AWS_ACCESS_KEY_ID,
      help="AWS access key ID for error report email [default: %default]")
  
  parser.add_option(
      "--awssecret",
      action="store",
      type="string",
      dest="awsSecretAccessKey",
      default=AWS_SECRET_ACCESS_KEY,
      help="AWS secret access key for error report email [default: %default]")
  
  parser.add_option(
      "--recipients",
      action="store",
      type="string",
      dest="errorReportEmailRecipients",
      default=ERROR_REPORT_EMAIL_RECIPIENTS,
      help=("Recipients error report email. Email addresses need to be comma "
            "separated. Example: "
            "'recipient1@numenta.com, recipient2@numenta.com' "
            "[default: %default]"))

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if options.errorReportEmailAwsRegion:
    options.errorReportEmailAwsRegion = (
      options.errorReportEmailAwsRegion.strip())
  if not options.errorReportEmailAwsRegion:
    msg = ("Option --awsregion or environment variable "
           "ERROR_REPORT_EMAIL_AWS_REGION is empty or undefined.")
    parser.error(msg)

  if options.errorReportEmailSenderAddress:
    options.errorReportEmailSenderAddress = (
      options.errorReportEmailSenderAddress.strip())
  if not options.errorReportEmailSenderAddress:
    msg = ("Option --senderaddress or environment variable "
           "ERROR_REPORT_EMAIL_SENDER_ADDRESS is empty or undefined.")
    parser.error(msg)

  # parsing comma separated list of email
  parsedErrorReportEmailRecipients = None
  if options.errorReportEmailRecipients:
    recipients = options.errorReportEmailRecipients
    parsedErrorReportEmailRecipients = [
      addr.strip() for addr in recipients.split(",")
      if addr.strip()]
  if not parsedErrorReportEmailRecipients:
    msg = ("Option --recipients or environment variable "
           "ERROR_REPORT_EMAIL_RECIPIENTS is empty or undefined.")
    parser.error(msg)

  if not options.awsAccessKeyId:
    msg = ("Option --awsid or environment variable "
           "AWS_ACCESS_KEY_ID is empty or undefined.")
    parser.error(msg)

  if not options.awsSecretAccessKey:
    msg = ("Option --awssecret or environment variable "
           "AWS_SECRET_ACCESS_KEY is empty or undefined.")
    parser.error(msg)

  return dict(
    consumerKey=options.consumerKey,
    consumerSecret=options.consumerSecret,
    accessToken=options.accessToken,
    accessTokenSecret=options.accessTokenSecret,
    errorReportEmailAwsRegion=options.errorReportEmailAwsRegion,
    errorReportEmailSesEndpoint=options.errorReportEmailSesEndpoint,
    errorReportEmailSenderAddress=options.errorReportEmailSenderAddress,
    awsAccessKeyId=options.awsAccessKeyId,
    awsSecretAccessKey=options.awsSecretAccessKey,
    errorReportEmailRecipients=parsedErrorReportEmailRecipients
    )



def main():
  """ NOTE: main may be used as "console script" entry point by setuptools
  """
  
  logging_support.LoggingSupport.initTool()

  try:
    options = _parseArgs()
    
    g_log.info("Running with options=%r", options)
    
    _checkTwitterScreenNames(**options)
  except Exception:
    g_log.exception("%s failed", __name__)



if __name__ == "__main__":
  main()
  
