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

"""Integration test to test instance quota"""

import json
from paste.fixture import TestApp, AppError
import socket
import unittest

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

import YOMP
from YOMP import logging_support
from YOMP.app.webservices import (autostacks_api,
                                  cloudwatch_api,
                                  custom_api,
                                  instances_api,
                                  models_api)
from YOMP.test_utils.app.test_case_base import TestCaseBase
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  webservices_assertions as assertions)

from YOMP.app.quota import QuotaConfig
from YOMP.app import config


def setUpModule():
  logging_support.LoggingSupport.initTestApp()



quotaConfig = QuotaConfig()



class QuotaTest(TestCaseBase):

  @classmethod
  def setUpClass(cls):
    cls.autostacksApp = TestApp(autostacks_api.app.wsgifunc())
    cls.cloudwatchApp = TestApp(cloudwatch_api.app.wsgifunc())
    cls.customApp = TestApp(custom_api.app.wsgifunc())
    cls.instancesApp = TestApp(instances_api.app.wsgifunc())
    cls.modelApp = TestApp(models_api.app.wsgifunc())
    cls.headers = getDefaultHTTPHeaders(YOMP.app.config)

    cls.plaintextPort = config.getint("metric_listener", "plaintext_port")
    cls.apiKey = config.get("security", "apikey")


  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                        (("actual", "instance_quota", "2"),))
  def testCustomQuota(self):
    metricNames = ["testCustomMetricsQuota-1",
                   "testCustomMetricsQuota-2",
                   "testCustomMetricsQuota-3"]

    # Make sure to attempt metric deletion
    for metricName in metricNames:
      self.addCleanup(self.customApp.delete,
                      "/%s" % metricName,
                      headers=self.headers)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for metricName in metricNames:
      sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    # Store metric uids
    metricUIDs = []
    for metricName in metricNames:
      metricUIDs.append(self.checkMetricCreated(metricName))

    # Send model creation request
    for uid in metricUIDs[:-1]:
      payload = {"uid": uid, "datasource": "custom", "min": 0.0, "max": 100.0}
      self.modelApp.post("/", json.dumps(payload), headers=self.headers)

    # Send the 3rd metric. This should result in an error
    with self.assertRaises(AppError) as e:
      payload = {"uid": metricUIDs[-1],
                 "datasource": "custom",
                 "min": 0.0,
                 "max": 100.0}
      self.modelApp.post("/", json.dumps(payload), headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)


  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                        (("actual", "instance_quota", "2"),))
  def testCloudwatchQuota(self):
    result = self.cloudwatchApp.get("/us-west-2/AWS/EC2",
                                    headers=self.headers)
    instances = json.loads(result.body)

    for i in range(0, 10, 5):
      instance = instances[i]
      instanceId = "us-west-2/AWS/EC2/%s" % (
        instance["dimensions"]["InstanceId"])
      postResponse = self.instancesApp.post("/%s" % instanceId,
                                            headers=self.headers)
      assertions.assertSuccess(self, postResponse)
      self.addCleanup(self.instancesApp.delete, "/", headers=self.headers,
                      params=json.dumps([instanceId]))

    with self.assertRaises(AppError) as e:
      instanceId = ("us-west-2/AWS/EC2/%s" %
                    (instances[10]["dimensions"]["InstanceId"]))
      postResponse = self.instancesApp.post("/%s" % instanceId,
                                            headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)


  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                      (("actual", "instance_quota", "2"),))
  def testAutostackQuota(self):
    autostackNames = ["testAutostackQuota-1",
                      "testAutostackQuota-2",
                      "testAutostackQuota-3"]
    filters = {"tag:aws:autoscaling:groupName": ["webserver-asg-micros01"]}

    # Send autostack creation request
    autostackUIDs = []
    for autostackName in autostackNames[:-1]:
      payload = {"name": autostackName, "region": "us-west-2",
                 "filters": filters}
      response = self.autostacksApp.post(
        "/", json.dumps(payload), headers=self.headers)

      autostackUIDs.append(json.loads(response.body)["uid"])

    # Check that the Autostack was created
    for uid in autostackUIDs:
      self.checkAutostackCreated(uid)

    # Quota should kick in even without monitored metrics
    with self.assertRaises(AppError) as e:
      payload = {"name": autostackNames[-1], "region": "us-west-2",
                 "filters": filters}
      self.autostacksApp.post(
        "/", json.dumps(payload), headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)

    # Enable a metric on each autostack so they are treated as active instances
    payload = [{"namespace": "AWS/EC2", "metric": "CPUUtilization"}]
    for uid in autostackUIDs:
      self.autostacksApp.post("/%s/metrics" % uid,
                              json.dumps(payload),
                              headers=self.headers)

    # Ensure cleanup
    for uid in autostackUIDs:
      self.addCleanup(self.autostacksApp.delete, "/%s" % uid,
                      headers=self.headers)

    # Check quota is enforced now that there are metrics added
    with self.assertRaises(AppError) as e:
      payload = {"name": autostackNames[-1], "region": "us-west-2",
                 "filters": filters}
      self.autostacksApp.post(
        "/", json.dumps(payload), headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)



  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                        (("actual", "instance_quota", "2"),))
  def testCombinationQuota1(self):
    result = self.cloudwatchApp.get("/us-west-2/AWS/EC2",
                                    headers=self.headers)
    instances = json.loads(result.body)


    for i in range(0, 10, 5):
      instance = instances[i]
      instanceId = "us-west-2/AWS/EC2/%s" % (
        instance["dimensions"]["InstanceId"])
      postResponse = self.instancesApp.post("/%s" % instanceId,
                                            headers=self.headers)
      assertions.assertSuccess(self, postResponse)
      self.addCleanup(self.instancesApp.delete, "/", headers=self.headers,
                      params=json.dumps([instanceId]))

    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    sock.sendall("CustomMetric1 5.0 1386201600\n")
    self.gracefullyCloseSocket(sock)
    self.addCleanup(self.customApp.delete,
                    "/CustomMetric1",
                    headers=self.headers)
    uid = self.checkMetricCreated("CustomMetric1")

    with self.assertRaises(AppError) as e:
      payload = {"uid": uid,
                 "datasource": "custom",
                 "min": 0.0,
                 "max": 100.0}
      self.modelApp.post("/", json.dumps(payload), headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)


  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                        (("actual", "instance_quota", "2"),))
  def testCombinationQuota2(self):
    metricNames = ["testCustomMetricsQuota-1",
                   "testCustomMetricsQuota-2"]

    # Make sure to attempt metric deletion
    for metricName in metricNames:
      self.addCleanup(self.customApp.delete,
                      "/%s" % metricName,
                      headers=self.headers)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for metricName in metricNames:
      sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    # Store metric uids
    metricUIDs = []
    for metricName in metricNames:
      metricUIDs.append(self.checkMetricCreated(metricName))

    # Send model creation request
    for uid in metricUIDs:
      payload = {"uid": uid, "datasource": "custom", "min": 0.0, "max": 100.0}
      self.modelApp.post("/", json.dumps(payload), headers=self.headers)

    # Monitor an additional instance. This should return an error
    result = self.cloudwatchApp.get("/us-west-2/AWS/EC2",
                                      headers=self.headers)
    instances = json.loads(result.body)

    with self.assertRaises(AppError) as e:
      instanceId = ("us-west-2/AWS/EC2/%s" %
                    (instances[0]["dimensions"]["InstanceId"]))
      self.instancesApp.post("/%s" % instanceId, headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)


  @ConfigAttributePatch(quotaConfig.CONFIG_NAME,
                        quotaConfig.baseConfigDir,
                        (("actual", "instance_quota", "2"),))
  def testCombinationQuota3(self):
    metricNames = ["testCustomMetricsQuota-1",
                   "testCustomMetricsQuota-2"]

    # Make sure to attempt metric deletion
    for metricName in metricNames:
      self.addCleanup(self.customApp.delete,
                      "/%s" % metricName,
                      headers=self.headers)

    # Add custom metric data
    sock = socket.socket()
    sock.connect(("localhost", self.plaintextPort))
    for metricName in metricNames:
      sock.sendall("%s 5.0 1386201600\n" % metricName)
    self.gracefullyCloseSocket(sock)

    # Store metric uids
    metricUIDs = []
    for metricName in metricNames:
      metricUIDs.append(self.checkMetricCreated(metricName))

    # Send model creation request
    for uid in metricUIDs:
      payload = {"uid": uid, "datasource": "custom", "min": 0.0, "max": 100.0}
      self.modelApp.post("/", json.dumps(payload), headers=self.headers)

    with self.assertRaises(AppError) as e:
      filters = {"tag:aws:autoscaling:groupName": ["webserver-asg-micros01"]}
      payload = {"name": "autostackQuotaTest", "region": "us-west-2",
                 "filters": filters}
      self.autostacksApp.post(
        "/", json.dumps(payload), headers=self.headers)

    self.assertIn("Server limit exceeded", e.exception.message)



if __name__ == "__main__":
  unittest.main()
