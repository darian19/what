#!/usr/bin/env python
#------------------------------------------------------------------------------
# Copyright 2013-2014 Numenta Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#------------------------------------------------------------------------------

"""Pull data from YOMP and upload to Datadog.

This script takes the metric ID for a YOMP metric and downloads the most recent
data. It is designed to be run every five minutes or so and will upload
duplicate records. This is fine as long as you don't select "sum" for the
aggregation method in Datadog.

The data is uploaded as two separate Datadog metrics. One for the values and one
for the anomaly scores. The YOMP metric server is used as the Datadog host. The
YOMP metric name is combined with either ".value" or ".anomalyScore" to make up
the Datadog metric name.

Anomaly scores are transformed from what the YOMP API returns into what is
shown in the YOMP mobile client as the height of the bars.

Note: This sample requires the `dogapi` library, which can be installed with
the samples bundle: `pip install YOMPcli[samples]`.
"""

import calendar
import datetime
import math
import optparse
import sys

from dogapi import dog_http_api

from YOMPcli.api import YOMPSession



def _getMetricServerAndName(YOMP, metricId):
  """Gets the server and metric names for the metric with the given ID.

  :param YOMP: the YOMPSession instance
  :param metricId: the YOMP metric ID for the desired metric
  :return: the server name and metric name for the YOMP metric
  """
  response = YOMP.get(YOMP.server + "/_models/" + metricId,
                      auth=YOMP.auth)
  model = response.json()[0]
  return model["server"], model["name"]



def _tranformAnomalyScore(score):
  """Transform anomaly score to match YOMP mobile bar height.

  :param score: the "anomaly_score" value returned by the YOMP API
  :return: the value corresponding to the height of the anomaly bars in YOMP
      mobile
  """
  if score > 0.99999:
    return 1.0

  return math.log(1.0000000001 - score) / math.log(1.0 - 0.9999999999)



def _getMetricData(YOMP, metricId, numRecords):
  """Get metric data from the YOMP API and convert to the Datadog format.

  This includes a data transformation for the anomaly score to a value that
  matches the height of the bars in the mobile client.

  :param YOMP: the YOMPSession instance
  :param metricId: the ID of the metric to get data for
  :param numRecords: the number of records to get from the API
  :return: a 2-tuple of values and anomalies lists where each element in the
      lists is a 2-tuple containing the unix timestamp and the value
  """
  url = YOMP.server + "/_models/" + metricId + "/data"
  if numRecords:
    url += "?limit=%i" % numRecords
  response = YOMP.get(url, auth=YOMP.auth)
  data = response.json()["data"]
  valuesData = []
  anomaliesData = []
  first = None
  last = None
  for dtStr, value, anomalyScore, _ in reversed(data):
    if not first:
      first = dtStr
    last = dtStr
    dt = datetime.datetime.strptime(dtStr, "%Y-%m-%d %H:%M:%S")
    ts = calendar.timegm(dt.utctimetuple())
    valuesData.append((ts, value))
    transformedAnomalyScore = _tranformAnomalyScore(anomalyScore)
    anomaliesData.append((ts, transformedAnomalyScore))
  print "First: %s and last: %s" % (first, last)
  return valuesData, anomaliesData



def sendDataToDatadog(datadogApiKey, YOMPServer, YOMPApiKey, numRecords,
                      metricId):
  """Get data from YOMP and send to Datadog.

  This gets metric data for the metric matching metricId and converts it into
  two datasets in the Datadog format: one for the values and one for the
  anomaly scores.
  """
  # Configure the Datadog library
  dog_http_api.api_key = datadogApiKey

  YOMP = YOMPSession(server=YOMPServer, apikey=YOMPApiKey)
  server, metricName = _getMetricServerAndName(YOMP, metricId)
  valuesData, anomaliesData = _getMetricData(YOMP, metricId, numRecords)

  # Hack to limit number of records for YOMP instances prior to version 1.3
  # that don't respect the limit parameter when getting metric data.
  valuesData = valuesData[-numRecords:]
  anomaliesData = anomaliesData[-numRecords:]

  print "Sending %i records for metric %s on server %s" % (
      len(valuesData), metricName, server)
  response = dog_http_api.metric(metricName + ".value", valuesData,
                                 host=server)
  if response["status"] != "ok":
    print "Datadog upload failed with response:\n\n%r" % response
  response = dog_http_api.metric(metricName + ".anomalyScore", anomaliesData,
                                 host=server)
  if response["status"] != "ok":
    print "Datadog upload failed with response:\n\n%r" % response



if __name__ == "__main__":
  usage = "usage: %prog [options] metricId"
  parser = optparse.OptionParser(usage=usage)
  parser.add_option("--datadogApiKey", help="the API key for Datadog")
  parser.add_option("--YOMPServer", help="the YOMP server URL")
  parser.add_option("--YOMPApiKey", help="the YOMP server API key")
  parser.add_option("--numRecords", type="int", default=6,
                    help="the number of records to fetch, or 0 to get all")

  options, extraArgs = parser.parse_args()

  if len(extraArgs) != 1:
    parser.error("incorrect number of arguments, expected 1 but got %i" %
                 len(extraArgs))

  if options.datadogApiKey is None:
    print "Must supply valid datadogApiKey"
    sys.exit(1)

  if options.YOMPServer is None:
    print "Must supply valid YOMPServer"
    sys.exit(1)

  if options.YOMPApiKey is None:
    print "Must supply valid YOMPApiKey"
    sys.exit(1)

  if options.numRecords is None:
    print "Must supply valid numRecords"
    sys.exit(1)

  sendDataToDatadog(options.datadogApiKey, options.YOMPServer,
                    options.YOMPApiKey, options.numRecords, extraArgs[0])
