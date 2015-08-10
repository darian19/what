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

import sqlalchemy
from sqlalchemy.exc import OperationalError

from nta.utils import error_reporting
from nta.utils.config import Config
from taurus.engine import logging_support

from taurus.monitoring import taurus_monitor_utils as monitorUtils
from taurus.monitoring.monitorsdb import schema



g_logger = logging.getLogger(__file__)



_FLAG_METRIC_ORDER = "Metric data out-of-order"
_FLAG_DATABASE_ISSUE = OperationalError.__module__ + OperationalError.__name__
_DB_ERROR_FLAG_FILE = "dbErrorFlagFile.csv"
_MONITOR_NAME = __file__.split("/")[-1]

# SELECT a.uid, count(rowid), min(rowid), max(rowid), min(timestamp),
#   max(timestamp), m.name FROM metric_data a
#     JOIN metric m on a.uid = m.uid
#      WHERE a.timestamp > (SELECT b.timestamp FROM metric_data b WHERE
#          a.uid = b.uid AND b.rowid = (a.rowid + "1")) group by uid;""
_SQL_QUERY = ("SELECT a.uid, count(rowid), min(rowid), max(rowid), "
              "min(timestamp),\n"
              "max(timestamp), m.name FROM metric_data a \n"
              "JOIN metric m on a.uid = m.uid\n"
              "WHERE a.timestamp > (SELECT b.timestamp FROM metric_data b "
              "WHERE\n"
              "a.uid = b.uid AND b.rowid = (a.rowid + \"1\")) group by uid;")



def _getOutOfOrderMetrics(connection, query):
  """
  Checks the timestamp order of rows of the metric_data table in the taurus db.

  :param connection: DB connection
  :type connection: sqlalchemy.engine.base.Connection
  :param query: A mysql query
  :type query: string
  :return The result of the database query
  :rtype sqlalchemy.engine.result.ResultProxy
  """
  resultProxy = connection.execute(query)
  return resultProxy.fetchall()



def _reportMetrics(monitoredResource, metrics, emailParams):
  """
  Sends email notification of specified out-of-order metrics. Avoids sending
  duplicate notifications using monitorsdb.

  :param monitoredResource: Path of the database containing metric_data table
  :type monitoredResource: string
  :param metrics: A list of out-of-order metric rows
  :type metrics: list
  :param emailParams: Parameters for sending email
  :type emailParams: dict
  """
  if len(metrics) > 0:
    message = ("The following rows of metric_data table were out of order:\n"
              "UID \tcount(rowid) \tmin(rowid) \tmax(rowid) \tmin(timestamp) "
              "\tmax(timestamp) \tmetric name\n")
    for row in metrics:
      message += str(row) + "\n"
    g_logger.info(message)

    if not monitorUtils.containsErrorFlag(schema.metricOrderMonitorErrorFlags,
                                          _FLAG_METRIC_ORDER):
      monitorUtils.addErrorFlag(schema.metricOrderMonitorErrorFlags,
                                _FLAG_METRIC_ORDER, _FLAG_METRIC_ORDER)
      g_logger.info("Check FAILS -- metric order error found. Sending an "
                    "error report.")
      error_reporting.sendMonitorErrorEmail(
        monitorName=_MONITOR_NAME,
        resourceName=monitoredResource,
        message=message,
        params=emailParams)
    else:
      g_logger.info("Check FAILS -- metric order error found. Error "
                    "flag exists; error report suppressed.")

  else:
    g_logger.info("Check PASSES -- all metrics were found to be in order =)")
    monitorUtils.removeErrorFlag(schema.metricOrderMonitorErrorFlags,
                                 _FLAG_METRIC_ORDER)



def _reportDatabaseIssue(issueUID, monitoredResource, issueMessage,
                         emailParams):
  """
  Reports a database issue only if flag is not present in local file.

  :param issueUID: Unique issue ID
  :type issueUID: string
  :param monitoredResource: Description of resource being monitored
  :type monitoredResource: string
  :param issueMessage: Issue details
  :type issueMessage: string
  :param emailParams: Parameters for sending email
  :type emailParams: dict
  """
  with open(_DB_ERROR_FLAG_FILE, "rb") as fp:
    try:
      flagDict = json.load(fp)
    except ValueError:
      g_logger.exception("Failed to load JSON from db error flag file")
      raise

    if issueUID not in flagDict:
      g_logger.info("Reporting database connection issue: %s and adding flag "
                    "to local flag file.", issueUID)
      flagDict[issueUID] = issueUID
      error_reporting.sendMonitorErrorEmail(
          monitorName=_MONITOR_NAME,
          resourceName=monitoredResource,
          message=issueMessage,
          params=emailParams)
    else:
      g_logger.info("Suppressing the urge to report issue %s because a local "
                    "file flag for this issue exists.", issueUID)

  with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
    json.dump(flagDict, fp)



def _clearDatabaseIssue(issueUID):
  """
  Clears a database issue if a flag is present in local flag file.

  :param issueUID: Unique issue ID
  :type issueUID: string
  """
  with open(_DB_ERROR_FLAG_FILE, "rb") as fp:
    try:
      flagDict = json.load(fp)
    except ValueError:
      g_logger.exception("Failed to load JSON from db error flag file")
      raise

    if issueUID in flagDict:
      del flagDict[issueUID]
      g_logger.debug("Cleared database issue flag: %s", issueUID)

  with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
    json.dump(flagDict, fp)



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

    monitoredResource = config.get("S1", "MONITORED_RESOURCE")
    monitoredResourceNoPwd = (monitoredResource.split(":")[0] + ":" +
                              monitoredResource.split(":")[1] + ":***@" +
                              monitoredResource.split(":")[2].split("@")[1])

    emailParams = dict(senderAddress=config.get("S1", "EMAIL_SENDER_ADDRESS"),
                       recipients=config.get("S1", "EMAIL_RECIPIENTS"),
                       awsRegion= config.get("S1", "EMAIL_AWS_REGION"),
                       sesEndpoint=config.get("S1", "EMAIL_SES_ENDPOINT"),
                       awsAccessKeyId=None,
                       awsSecretAccessKey=None)

    if args.testEmail:
      g_logger.info("Sending an email for test purposes.")
      error_reporting.sendMonitorErrorEmail(
          monitorName=_MONITOR_NAME,
          resourceName=monitoredResourceNoPwd,
          message="Test issue",
          isTest=True,
          params=emailParams)

    # Create a db error flag file if one doesn't already exist
    if not os.path.isfile(_DB_ERROR_FLAG_FILE):
      g_logger.debug("Creating the database error flag file.")
      with open(_DB_ERROR_FLAG_FILE, "wb") as fp:
        json.dump({}, fp)

    # Perform the primary check of metric_data table order
    g_logger.debug("Connecting to resource: %s", monitoredResourceNoPwd)
    engine = sqlalchemy.create_engine(monitoredResource)
    connection = engine.connect()
    metrics = _getOutOfOrderMetrics(connection, _SQL_QUERY)
    _reportMetrics(monitoredResourceNoPwd, metrics, emailParams)

    # If previous method does not throw exception, then we come here and clear
    # the database issue flag
    _clearDatabaseIssue(_FLAG_DATABASE_ISSUE)

  except OperationalError:
    # If database connection fails, report issue
    g_logger.critical("Failed due to " + _FLAG_DATABASE_ISSUE)
    _reportDatabaseIssue(_FLAG_DATABASE_ISSUE,
                         monitoredResourceNoPwd,
                         traceback.format_exc(),
                         emailParams)
  except Exception:
    # If any unexpected exception occurs, try to send an email with traceback
    g_logger.critical("%s failed due to unexpected Exception. \n",
                      traceback.format_exc())
    error_reporting.sendMonitorErrorEmail(
        monitorName=_MONITOR_NAME,
        resourceName=monitoredResourceNoPwd,
        message=traceback.format_exc(),
        params=emailParams)



if __name__ == "__main__":
  main()
