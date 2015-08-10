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
Exercise the YOMP Custom Metrics functionality by gradually increasing the
number of YOMP Custom Models

NOTE: see prerequisites in this tool's help string
"""

from collections import namedtuple
import contextlib
import csv
import json
import logging
from optparse import OptionParser
import random
import socket
import threading
import time

import requests

from YOMP import logging_support
from nta.utils.error_handling import abortProgramOnAnyException



gLog = logging.getLogger(__name__)


_CsvRow = namedtuple(
  "_CsvRow",
  "timestamp totalModels modelGroupNumber numNewModels"
)


# We grow the number of YOMP Custom Metric models every period
# by "metric increment" specified via command-line options, which defaults to
#_DEFAULT_METRIC_INCREMENT
_METRIC_INCREASE_PERIOD_SEC = 10 * 60

_DEFAULT_METRIC_INCREMENT = 20

_DEFAULT_MINMODELS = _DEFAULT_METRIC_INCREMENT


# Maximum number of metrics per thread that feeds data to them
_MAX_METRICS_PER_FEEDER_THREAD = 20


# After reaching instance quota, we continue to feed the models for this
# additional duration
_FINAL_SNOOZE_SEC = 60 * 60

_METRIC_DATA_PERIOD = 5 * 60

# Connection port for plaintext custom metrics
_PLAINTEXT_PORT = 2003


def _createYOMPCustomModel(YOMPhost, apikey, metricName):
  """
  :returns: dictionary result of the _models POST request on success;
    None if quota limit was exceeded. Raises exception otherwise
  """
  payload = {
    "metric": metricName,
    "datasource": "custom",
    "min": 0.0, "max": 5000.0
  }

  for _retries in xrange(20):
    try:
      response = requests.post(
        "https://%s/_models" % (YOMPhost,),
        auth=(apikey, ""),
        data=json.dumps(payload),
        verify=False)

      if response.status_code == 201:
        return json.loads(response.text)

      # TODO: the check for "Server limit exceeded" is temporary for MER-1366
      if (response.status_code == 500 and
          "Server limit exceeded" in response.text):
        return None

      raise Exception("Unable to create model: %s (%s)" % (
        response, response.text))
    except Exception:  # pylint: disable=W0703
      gLog.exception("Transient error while creating model")
      time.sleep(2)
    else:
      break
  else:
    raise Exception("Create-model retry count exceeded")



@abortProgramOnAnyException(1, logger=gLog)
def feedMetricData(YOMPhost, metricNames):
  """ Thread function for feeding metric data to the given YOMP Custom Metrics
  """
  # Try to avoid thundering herd
  time.sleep(random.random() * _METRIC_DATA_PERIOD)

  while True:
    for _retries in xrange(20):
      try:
        with contextlib.closing(socket.socket()) as sock:
          sock.connect((YOMPhost, _PLAINTEXT_PORT))

          for metricName in metricNames:
            timestamp = int(time.time())
            sock.sendall("%s 0.0 %d\n" % (metricName, timestamp))
      except Exception:  # pylint: disable=W0703
        gLog.exception("Transient error while sending data")
        time.sleep(1)
      else:
        break
    else:
      raise Exception("Send-data retry count exceeded")

    time.sleep(_METRIC_DATA_PERIOD)



def main(YOMPhost, apikey, minmodels, metricIncrement, csvFilePath,
         feedforever):
  """
  :param YOMPhost: YOMP server's hostname or IP address string

  :param apikey: YOMP server's API key

  :param minmodels: Minimum number of models to add at start-up;
    NOTE: models are added in increments of metricIncrement

  :param metricIncrement: After initial models are created, additional models
    will be added (up to quota) every _METRIC_INCREASE_PERIOD_SEC seconds in
    batches specified by this arg

  :param feedforever: If True, continue to feed the models forever
  """
  gLog.info("Starting up: YOMPhost=%s; apikey=%s; minmodels=%d; "
            "csvFilePath=%s; feedforever=%s",
            YOMPhost, apikey, minmodels, csvFilePath, feedforever)

  if not csvFilePath:
    csvFilePath = "/dev/null"

  # Create CSV file, emit CSV header
  with open(csvFilePath, "w") as csvStream:
    csv.writer(csvStream).writerow(_CsvRow._fields)

  numModels = 0
  modelGroupNumber = 0
  instanceLimitReached = False

  starting = True

  while not instanceLimitReached:
    modelGroupNumber += 1

    # Create the next batch of models
    newMetricNames = []
    if starting:
      newTargetIncrement = minmodels
    else:
      newTargetIncrement = metricIncrement

    for metricNumber in xrange(numModels+1, numModels+newTargetIncrement+1):
      metricName = "stressMetric.%04d.%04d" % (
        modelGroupNumber, metricNumber)

      # Create the next model
      response = _createYOMPCustomModel(
        YOMPhost=YOMPhost,
        apikey=apikey,
        metricName=metricName)

      if response is not None:
        newMetricNames.append(metricName)
      else:
        instanceLimitReached = True
        gLog.info("Instance limit reached after %d models",
                  numModels + len(newMetricNames))
        break

    if not newMetricNames and (not starting or numModels == 0):
      break

    if newMetricNames:
      numModels += len(newMetricNames)

      gLog.info(
        "{TAG:CUS_STRESS.MODELS.ADDED} modelGroupNumber=%d, numNewModels=%d; "
        "totalModels=%d", modelGroupNumber, len(newMetricNames), numModels)

      # Append info to CSV stream
      with open(csvFilePath, "a") as csvStream:
        row = _CsvRow(
          timestamp=time.time(),
          totalModels=numModels,
          modelGroupNumber=modelGroupNumber,
          numNewModels=len(newMetricNames)
        )
        csv.writer(csvStream).writerow(row)

      # Start thread(s) that will feed these models
      for batch in (
          newMetricNames[i:i+_MAX_METRICS_PER_FEEDER_THREAD] for i in
          xrange(0, len(newMetricNames), _MAX_METRICS_PER_FEEDER_THREAD)):
        thread = threading.Thread(
          target=feedMetricData,
          kwargs=dict(
            YOMPhost=YOMPhost,
            metricNames=batch))
        thread.setDaemon(True)
        thread.start()

    if starting:
      starting = False

    if not instanceLimitReached:
      time.sleep(_METRIC_INCREASE_PERIOD_SEC)

  if feedforever:
    gLog.info("{TAG:CUSSTRESS.FEEDFOREVER}; totalModelsCreated=%d", numModels)
    while True:
      time.sleep(300)
  else:
    gLog.info("Continuing to feed the models for an additional %ss",
              _FINAL_SNOOZE_SEC)
    time.sleep(_FINAL_SNOOZE_SEC)

    gLog.info("{TAG:CUSSTRESS.DONE}; totalModelsCreated=%d", numModels)



def _parseArgs():
  """ Parses command-line args

  :returns: a dict;
    {"YOMPhost": <hostname or address>, "apikey": <api-key>,
     "minmodels": <num-models-to-create-at-start>,
     "csvFilePath": <output-csv-file-path>
     "feedforever": <feedforever>}
  """
  helpString = (
    "%%prog [OPTIONS] YOMPHOST YOMP_APIKEY\n"
    "Exercise the YOMP Custom Metrics functionality by gradually increasing "
    "the number of YOMP Custom Models and feeding data to each model on a "
    "5-minute interval.\n"
    "PREREQUISITES: profiling must be enabled on the YOMP server under "
    "test in application.conf and model-swapper.conf; YOMP log rotation must "
    "be disabled via `sudo crontab -e`"
    )

  parser = OptionParser(helpString)

  parser.add_option(
    "--minmodels",
    action="store",
    type="int",
    default=_DEFAULT_MINMODELS,
    dest="minmodels",
    help=("Initial number of models to create at beginning "
          "(not to exceed quota). [default: %default]"))

  parser.add_option(
    "--inc",
    action="store",
    type="int",
    default=_DEFAULT_METRIC_INCREMENT,
    dest="metricIncrement",
    help=("After initial models are created, additional models will be added "
          "(up to quota) every %d seconds in increments specified by this arg "
          "[default: %%default]" % (_METRIC_INCREASE_PERIOD_SEC,)))

  parser.add_option(
    "--csv",
    action="store",
    type="str",
    default="/dev/null",
    dest="csvFilePath",
    help=("CSV file path for outputting model counts as models are "
          "created. [default: %default]\n"))

  parser.add_option(
    "--feedforever",
    action="store_true",
    default=False,
    dest="feedforever",
    help=("Continue to feed the models forever. By default, the feeding will "
          "end %ss after the last model is created [default: %%default]" %
          (_FINAL_SNOOZE_SEC,)))

  (options, posArgs) = parser.parse_args()

  if len(posArgs) != 2:
    parser.error("Expected two positional args, but got %s: %s" % (
                 len(posArgs), posArgs,))

  if options.metricIncrement <= 0:
    parser.error("Expected positive metric increment, but got %r" %
                 (options.metricIncrement,))

  YOMPhost, apikey = posArgs

  return dict(YOMPhost=YOMPhost, apikey=apikey,
              minmodels=options.minmodels,
              metricIncrement=options.metricIncrement,
              csvFilePath=options.csvFilePath,
              feedforever=options.feedforever)



if __name__ == "__main__":
  logging_support.LoggingSupport.initTool()

  try:
    main(**_parseArgs())
  except Exception:
    gLog.exception("Failed")
    raise
