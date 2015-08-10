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

import argparse
import json
import logging
import os
import traceback

import requests
from sqlalchemy.exc import OperationalError

from htmengine.repository.queries import MetricStatus
from nta.utils import error_reporting
from nta.utils.config import Config
from taurus.engine import logging_support

from taurus.monitoring import monitorsdb
from taurus.monitoring.monitorsdb import CONF_DIR
from taurus.monitoring.monitorsdb import schema



_FLAG_OPERATIONAL_ERROR = "SQL Alchemy Operational Error"
_FLAG_REQUESTS_EXCEPTION = "Requests Exception"
_FLAG_HTTP_STATUS_CODE = "HTTP Status Code Issue"
_FLAG_RESPONSE_JSON = "Response JSON Error"
_FLAG_DATABASE_ISSUE = "sqlalchemy.exc.OperationalError"
_DB_ERROR_FLAG_FILE = "dbErrorFlagFile.csv"
_MONITOR_NAME = __file__.split("/")[-1]



g_logger = logging.getLogger("taurus_models_monitor")



def _getIssueString(name, details):
  """
  Gets a string representation of an issue.

  :param name: issue name
  :param details: issue details
  :returns issue string
  """
  return "Issue: {0}\n\nDescription: {1}".format(name, details)



@monitorsdb.retryOnTransientErrors
def _containsIssueFlag(uid):
  """
  Checks whether issue(s) with specified uid is(are) present in
  monitor_error_flags table.

  :param uid: a unique issue id
  :type uid: string
  :returns: True is there exist any row(s) in the table having specified uid,
            False otherwise
  :rtype: Boolean
  """
  table = schema.modelsMonitorErrorFlags
  sel = table.select().where(table.c.uid == uid)
  issues = monitorsdb.engineFactory().execute(sel).fetchall()
  return len(issues) > 0



@monitorsdb.retryOnTransientErrors
def _addIssueFlag(uid, name):
  """
  Adds issue to monitor_error_flags table.

  :param uid: a unique issue id
  :type uid: string
  :param name: name of issue
  :type name: string
  """
  table = schema.modelsMonitorErrorFlags
  ins = table.insert().prefix_with("IGNORE", dialect="mysql").values(
      uid=uid,
      name=name,
      should_report=False)
  monitorsdb.engineFactory().execute(ins)
  g_logger.debug("Added new issue flag for %s", name)



@monitorsdb.retryOnTransientErrors
def _removeIssueFlag(uid):
  """
  Removes issue from monitor_error_flags table.

  :param uid: a unique issue id
  :type uid: string
  """
  table = schema.modelsMonitorErrorFlags
  cmd = table.delete().where(table.c.uid == uid)
  result = monitorsdb.engineFactory().execute(cmd)
  if result.rowcount > 0:
    g_logger.debug("Cleared issue flag with uid: %s", uid)



def _reportIssue(uid, url, issueMessage, emailParams):
  """
  Reports an issue if no database flag is present.
  :param uid: Unique issue ID
  :param url: request URL
  :param issueMessage: Issue details
  """
  if not _containsIssueFlag(uid):
    _addIssueFlag(uid, uid)
    error_reporting.sendMonitorErrorEmail(monitorName=_MONITOR_NAME,
                                          resourceName=url,
                                          message=issueMessage,
                                          params=emailParams)
  else:
    g_logger.info("Asked to report issue %s, however db flag for issue "
                  "exists.", uid)



def _reportDatabaseIssue(uid, url, issueMessage, emailParams):
  """
  Reports a database issue only if flag is not present in local file.
  :param uid: Unique issue ID
  :param url: request URL
  :param issueMessage: Issue details
  """
  with open(_DB_ERROR_FLAG_FILE, "rb") as fp:
    try:
      flagDict = json.load(fp)
    except ValueError:
      g_logger.exception("Failed to load JSON from db error flag file")
      raise

    if uid not in flagDict:
      flagDict[uid] = uid
      error_reporting.sendMonitorErrorEmail(monitorName=_MONITOR_NAME,
                                            resourceName=url,
                                            message=issueMessage,
                                            params=emailParams)
    else:
      g_logger.info("Suppressing the urge to report issue %s because a local "
                    "file flag for this issue exists.", uid)

  with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
    json.dump(flagDict, fp)



def _clearDatabaseIssue(uid):
  """
  Clears a database issue if flag is present in local file.
  :param uid: Unique issue ID
  """
  with open(_DB_ERROR_FLAG_FILE, "rb") as fp:
    try:
      flagDict = json.load(fp)
    except ValueError:
      g_logger.exception("Failed to load JSON from db error flag file")
      raise

    if uid in flagDict:
      del flagDict[uid]
      g_logger.debug("Cleared database issue flag: %s", uid)

  with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
    json.dump(flagDict, fp)



def _checkModelsStatus(modelsJson, url, emailParams):
  """
  For all models, checks if the model has an error status.
  If model was OK, but is now in error, its db flag is set and an email is
  sent.
  If model was in error and is still in error, no email is sent.
  If model was in error, but is now OK, its db flag is cleared.

  :param modelsJson: A JSON containing descriptions of the models.
  """
  g_logger.debug("Checking models' status")
  modelsInError = ""
  for model in modelsJson:
    uid = model["uid"]
    if model["status"] == MetricStatus.ERROR:
      if not _containsIssueFlag(uid):
        _addIssueFlag(uid, uid)
        modelsInError += str(model) + "\n\n"
    else:
      _removeIssueFlag(uid)

  if modelsInError != "":
    g_logger.info("Found models entering error status")
    issue = _getIssueString("Model(s) entering error status.\n", modelsInError)
    error_reporting.sendMonitorErrorEmail(monitorName=_MONITOR_NAME,
                                          resourceName=url,
                                          message=issue,
                                          params=emailParams)
  else:
    g_logger.info("Looking good -- no models were found in error status =)")



def _connectAndCheckModels(modelsUrl, apiKey, requestTimeout, emailParams):
  """
  Check the Taurus models for error status.

  :param modelsUrl
  :param apiKey
  :param requestTimeout
  :return A detected issue message or None
  :rtype string
  """
  try:
    g_logger.debug("Connecting to Taurus models")
    response = requests.get(modelsUrl, auth=(apiKey, ""),
                            timeout=requestTimeout, verify=False)
    _removeIssueFlag(_FLAG_REQUESTS_EXCEPTION)
  except requests.exceptions.RequestException:
    g_logger.exception("RequestException calling: %s with apiKey %s and "
                       "timeout: %s", modelsUrl, apiKey, requestTimeout)
    issue = traceback.format_exc() + "\n"
    _reportIssue(_FLAG_REQUESTS_EXCEPTION, modelsUrl, issue, emailParams)
    return

  statusCode = response.status_code
  if statusCode is 200:
    _removeIssueFlag(_FLAG_HTTP_STATUS_CODE)
  else:
    g_logger.error("Received abnormal HTTP status code: %s", statusCode)
    issue = _getIssueString("Received abnormal HTTP status code", statusCode)
    _reportIssue(_FLAG_HTTP_STATUS_CODE, modelsUrl, issue, emailParams)
    return

  try:
    responseJson = response.json()
    _removeIssueFlag(_FLAG_RESPONSE_JSON)
  except ValueError:
    g_logger.error("ValueError encountered loading JSON. Response text: %s",
                   response.text)
    issue = "ValueError encountered loading JSON."
    _reportIssue(_FLAG_RESPONSE_JSON, modelsUrl, issue, emailParams)
    return

  _checkModelsStatus(responseJson, modelsUrl, emailParams)



def _getArgs():
  """
  Parses and returns command line arguments.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("--monitorConfPath",
                      help="Specify full path to monitor conf file")
  parser.add_argument("--loggingLevel", help="Specify logging level: DEBUG, "
                      "INFO, WARNING, ERROR, or CRITICAL",
                      default="WARNING")
  parser.add_argument("--loggingConsole", help="Specify logging output "
                      "console: stderror or stdout", default="stderr")
  parser.add_argument("--requestTimeout", help="Specify API request timeout "
                      "in seconds", type=float, default=60.0)
  parser.add_argument("--testEmail", help="Forces a warning email to be sent.",
                      action="store_true")
  return parser.parse_args()



def main():
  """
  NOTE: main also serves as entry point for "console script" generated by setup
  """
  try:
    args = _getArgs()
    logging_support.LoggingSupport.initLogging(loggingLevel=args.loggingLevel,
                                               console=args.loggingConsole,
                                               logToFile=True)

    confDir = os.path.dirname(args.monitorConfPath)
    confFileName = os.path.basename(args.monitorConfPath)
    config = Config(confFileName, confDir)

    modelsUrl = config.get("S1", "MODELS_MONITOR_TAURUS_MODELS_URL")
    apiKey = config.get("S1", "MODELS_MONITOR_TAURUS_API_KEY")

    emailParams = dict(senderAddress=config.get("S1", "MODELS_MONITOR_EMAIL_SENDER_ADDRESS"),
                       recipients=config.get("S1", "MODELS_MONITOR_EMAIL_RECIPIENTS"),
                       awsRegion= config.get("S1", "MODELS_MONITOR_EMAIL_AWS_REGION"),
                       sesEndpoint=config.get("S1", "MODELS_MONITOR_EMAIL_SES_ENDPOINT"),
                       awsAccessKeyId=None,
                       awsSecretAccessKey=None)

    dbConf= os.getenv("TAURUS_MONITORS_DB_CONFIG_PATH",
                      "Couldn't read TAURUS_MONITORS_DB_CONFIG_PATH")
    g_logger.info("TAURUS_MONITORS_DB_CONFIG_PATH: %s", dbConf)
    g_logger.info("DB CONF DIR: %s", CONF_DIR)

    if args.testEmail:
      g_logger.info("Sending an email for test purposes.")
      error_reporting.sendMonitorErrorEmail(monitorName=_MONITOR_NAME,
                                            resourceName=modelsUrl,
                                            message="Test issue",
                                            isTest=True,
                                            params=emailParams)

    # Create a db error flag file if it doesn't already exist
    if not os.path.isfile(_DB_ERROR_FLAG_FILE):
      g_logger.debug("Making DB error flag file")
      with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
        json.dump({}, fp)

    _connectAndCheckModels(modelsUrl, apiKey, args.requestTimeout, emailParams)
    _clearDatabaseIssue("sqlalchemy.exc.OperationalError")

  except OperationalError:
    g_logger.critical("Failed due to sqlalchemy.exc.OperationalError")
    issue = _getIssueString("sqlalchemy.exc.OperationalError",
                            traceback.format_exc())
    _reportDatabaseIssue("sqlalchemy.exc.OperationalError", modelsUrl, issue,
                         emailParams)
  except Exception:
    # Unexpected Exceptions are reported every time.
    g_logger.critical("%s failed due to unexpected Exception. \n", __name__)
    g_logger.critical("Traceback:\n", exc_info=True)
    issue = _getIssueString("Unexpected Exception", traceback.format_exc())
    error_reporting.sendMonitorErrorEmail(monitorName=_MONITOR_NAME,
                                          resourceName=modelsUrl,
                                          message=issue,
                                          params=emailParams)



if __name__ == "__main__":
  main()
