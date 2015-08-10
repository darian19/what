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

"""Integration tests for Autostacks"""

import collections
import datetime
import json
import logging
import time
import unittest

import boto.ec2.cloudwatch
import requests

from YOMP import logging_support
from YOMP.app import config
from YOMP.test_utils.app.test_case_base import TestCaseBase, retry



_LOGGER = logging.getLogger(__name__)

_REGION = "us-west-2"
_FILTERS = {"tag:aws:autoscaling:groupName": ["webserver-vpc-asg-numenta-abc"]}
_PERIOD = 300  # 5 minutes



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



class AutoStacksTest(TestCaseBase):
  """Integration tests for AutoStacks."""


  def setUp(self):
    self.apiKey = config.get("security", "apikey")


  def testCreateDelete(self):
    """Create and delete an AutoStack."""
    runIdentifier = str(time.time())
    stackName = "test.autostack.%s" % runIdentifier
    _LOGGER.info("Running test with Autostack name: %s", stackName)

    # Send autostack creation request
    payload = {"name": stackName, "region": _REGION,
               "filters": _FILTERS}
    response = requests.post("https://localhost/_autostacks",
                             auth=(self.apiKey, ""), verify=False,
                             data=json.dumps(payload))
    uid = response.json()["uid"]

    # Check that the Autostack was created
    self.checkAutostackCreated(uid)

    # Delete the AutoStack
    response = requests.delete("https://localhost/_autostacks/%s" % uid,
                               auth=(self.apiKey, ""), verify=False)
    self.assertEqual(response.status_code, 204)


  def testAttemptDuplicateCreation(self):
    """Create and delete an AutoStack."""
    runIdentifier = str(time.time())
    stackName = "test.autostack.%s" % runIdentifier
    _LOGGER.info("Running test with Autostack name: %s", stackName)

    # Send autostack creation request
    payload = {"name": stackName, "region": _REGION,
               "filters": _FILTERS}

    response = requests.post("https://localhost/_autostacks",
                             auth=(self.apiKey, ""), verify=False,
                             data=json.dumps(payload))
    uid = response.json()["uid"]

    # Check that the Autostack was created
    self.checkAutostackCreated(uid)

    # Attempt to create an autostack with the same payload
    badResponse = requests.post("https://localhost/_autostacks",
                             auth=(self.apiKey, ""), verify=False,
                             data=json.dumps(payload))

    # Delete the original AutoStack (cleanup)
    response = requests.delete("https://localhost/_autostacks/%s" % uid,
                               auth=(self.apiKey, ""), verify=False)

    self.assertEqual(badResponse.status_code, 500)
    self.assertIn("Please enter a unique Autostack name", badResponse.text)
    self.assertEqual(response.status_code, 204)


  def testMultipleInstances(self):
    """Create an AutoStack with multiple instances and validate results."""
    runIdentifier = str(time.time())
    stackName = "test.autostack.%s" % runIdentifier
    _LOGGER.info("Running test with Autostack name: %s", stackName)

    # Get and store the preview list of instances that will be included in
    # the AutoStack and validate that there are at least two instances.
    params = {"region": _REGION, "filters": json.dumps(_FILTERS)}
    response = requests.get("https://localhost/_autostacks/preview_instances",
                            params=params, auth=(self.apiKey, ""), verify=False)
    instanceIDs = [i["instanceID"] for i in response.json()]
    self.assertGreaterEqual(len(instanceIDs), 2,
                            "Make sure there are at least two AWS instances "
                            "in region %s matching the test filters: %r" %
                            (_REGION, _FILTERS))

    # Send autostack creation request
    payload = {"name": stackName, "region": _REGION,
               "filters": _FILTERS}
    response = requests.post("https://localhost/_autostacks",
                             auth=(self.apiKey, ""), verify=False,
                             data=json.dumps(payload))
    uid = response.json()["uid"]
    _LOGGER.info("Stack UID is %s", uid)

    self.addCleanup(requests.delete, "https://localhost/_autostacks/%s" % uid,
                    auth=(self.apiKey, ""), verify=False)

    # Check that the Autostack was created
    self.checkAutostackCreated(uid)

    # Add a metric to be monitored by the AutoStack
    payload = [{"namespace": "AWS/EC2", "metric": "CPUUtilization"}]
    response = requests.post("https://localhost/_autostacks/%s/metrics" % uid,
                             auth=(self.apiKey, ""), verify=False,
                             data=json.dumps(payload))
    self.assertEqual(response.json()["result"], "success")
    metricID = response.json()["metric"]["uid"]
    _LOGGER.info("AutoStack metric UID is %s", metricID)

    # Check the results are correct
    self._validateAutostackResults(metricID, instanceIDs, "CPUUtilization")


  @retry(duration=75, delay=1)
  def _validateAutostackResults(self, metricID, instanceIDs, metricName):
    """Validate that AutoStack data is correct based on the metrics data.

    This method ensures that there is at least twelve records and validates
    that the most recent five are computed correctly. By skipping at least the
    first few, we ensure that the data is still available in Cloudwatch. The
    number five is arbitrary, we just need some records to validate.

    @param metricID the ID of the AutoStack metric to check
    @param instanceIDs a sequence of the IDs for the metrics that make up the
        AutoStack
    @param metricName the metric name to validate
    """
    # Get the AutoStack data
    response = requests.get("https://localhost/_models/%s/data" % metricID,
                            auth=(self.apiKey, ""), verify=False)
    self.assertSetEqual(set(response.json().keys()), set(["names", "data"]))
    names = response.json()["names"]
    self.assertSetEqual(
        set(["timestamp", "value", "anomaly_score", "rowid"]), set(names))
    data = response.json()["data"]

    # Make sure that we have enough data to validate
    self.assertGreaterEqual(len(data), 12)
    recordsToValidate = dict((r[0], r[1]) for r in data[:12])

    # Get the start and end dates to pull Cloudwatch data for
    start = datetime.datetime.strptime(min(recordsToValidate.keys()),
                                       "%Y-%m-%d %H:%M:%S")
    end = datetime.datetime.strptime(max(recordsToValidate.keys()),
                                     "%Y-%m-%d %H:%M:%S")

    # Collect the Cloudwatch data for the timestamp range for all instances
    dataByTimestamp = collections.defaultdict(list)
    conn = boto.ec2.cloudwatch.connect_to_region(
            _REGION,
            aws_access_key_id=config.get("aws", "aws_access_key_id"),
            aws_secret_access_key=config.get("aws", "aws_secret_access_key"))
    for instanceID in instanceIDs:
      data = conn.get_metric_statistics(
          period=_PERIOD, start_time=start, end_time=end,
          metric_name=metricName, namespace="AWS/EC2", statistics=("Average",),
          dimensions={"InstanceId": instanceID})
      for record in data:
        dataByTimestamp[record["Timestamp"]].append(record["Average"])

    # Check that the manually averaged values match the AutoStack value
    numRecordsValidated = 0
    for timestamp, records in dataByTimestamp.iteritems():
      expectedAverage = sum(records) / len(records)
      actualAverage = recordsToValidate[timestamp.strftime("%Y-%m-%d %H:%M:%S")]
      self.assertAlmostEqual(
          expectedAverage, actualAverage, 4,
          "AutoStack value of %f differs from average from CloudWatch of %f "
          "at time %s" % (actualAverage, expectedAverage, timestamp))
      if len(records) >= 2:
        numRecordsValidated += 1
    # Make sure we checked enough records that had multiple instances
    self.assertGreaterEqual(numRecordsValidated, 5)



if __name__ == "__main__":
  unittest.main()
