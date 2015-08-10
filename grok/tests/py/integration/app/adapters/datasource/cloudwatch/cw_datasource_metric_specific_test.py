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

""" Integration tests for metric-specific methods """

import datetime
import os
import yaml

from YOMP import logging_support
from YOMP.YOMP_logging import getExtendedLogger

import YOMP.app
import YOMP.app.adapters.datasource as datasource_adapter_factory
from YOMP.app.adapters.datasource.cloudwatch import aws_base
from YOMP.app import repository
from YOMP.app.repository.queries import MetricStatus
import htmengine.utils
from htmengine.utils import jsonDecode

from YOMP.test_utils.app.test_case_base import TestCaseBase, unittest
import YOMP.test_utils.aws_utils



_LOG = getExtendedLogger("cw_datasource_adapter_metrics_test")



def setUpModule():
  logging_support.LoggingSupport.initTestApp()




class CloudwatchDatasourceAdapterMetricsTest(TestCaseBase):

  _supportedResourceTypes = [
    aws_base.ResourceTypeNames.EC2_INSTANCE,
    aws_base.ResourceTypeNames.AUTOSCALING_GROUP,
    #aws_base.ResourceTypeNames.DYNAMODB_TABLE, (NO DATA)
    aws_base.ResourceTypeNames.ELB_LOAD_BALANCER,
    #aws_base.ResourceTypeNames.EBS_VOLUME, (NO DATA)
    aws_base.ResourceTypeNames.OPSWORKS_STACK,
    aws_base.ResourceTypeNames.RDS_DBINSTANCE,
    aws_base.ResourceTypeNames.REDSHIFT_CLUSTER,
    #aws_base.ResourceTypeNames.SNS_TOPIC, (NO DATA)
    #aws_base.ResourceTypeNames.SQS_QUEUE (NO DATA)


  ]

  _validStateNames = {
    aws_base.ResourceTypeNames.EC2_INSTANCE:
      ("pending", "running", "shutting-down", "terminated", "stopping",
       "stopped"),
    aws_base.ResourceTypeNames.RDS_DBINSTANCE:
      ("available", "backing-up", "creating", "deleted", "deleting", "failed",
       "incompatible-restore", "incompatible-parameters", "modifying",
       "rebooting", "resetting-master-credentials", "storage-full")
  }

  @classmethod
  def setUpClass(cls):

    with open(os.path.join(
        YOMP.app.YOMP_HOME,
        "tests/py/integration/app/test_resources.yaml")) as fin:
      resources = yaml.load(fin)

    # Load YOMP API Key as required by TestCaseBase
    cls.apiKey = YOMP.app.config.get("security", "apikey")

    cls._testCases = {}
    cls._tagNames = {}

    for key in cls._supportedResourceTypes:
      testSpecs = resources[key]
      cls._testCases[key] = {}

      cls._testCases[key]["noMinMax"] = [
        {"datasource":testSpec["datasource"],
         "metricSpec":{
           "region":testSpec["region"],
           "namespace":testSpec["namespace"],
           "metric":testSpec["metric"],
           "dimensions":testSpec["dimensions"]
         }} for testSpec in testSpecs]

      cls._testCases[key]["withMinMax"] = [
        {"datasource":testSpec["datasource"],
         "metricSpec":{
           "region":testSpec["region"],
           "namespace":testSpec["namespace"],
           "metric":testSpec["metric"],
           "dimensions":testSpec["dimensions"]
         },
         "modelParams":testSpec["modelParams"]
        } for testSpec in testSpecs]


      if "tag_name" in testSpecs[0]:
        cls._tagNames[key] = testSpecs[0]["tag_name"]


  def setUp(self):
    _LOG.setLogPrefix("<%s> " % (self.id(),))  # pylint: disable=E1103


  def _monitorMetric(self, adapter, modelSpec):  # pylint: disable=R0201
    """ Start monitoring a metric and return its modelId

    :param adapter: CloudwatchDatasourceAdapter object

    :param modelSpec: modelSpec to use

    :returns: modelId of the monitored metric

    :raises: does not suppress any exceptions from monitorMetric
    """
    _LOG.info("Creating %s/%s metric on %r in %s",
              modelSpec["metricSpec"]["namespace"],
              modelSpec["metricSpec"]["metric"],
              modelSpec["metricSpec"]["dimensions"],
              modelSpec["metricSpec"]["region"])

    # Turn on monitoring
    return adapter.monitorMetric(modelSpec)


  def _runBasicChecksOnModel(self, modelId, _adapter, modelSpec):
    with repository.engineFactory().connect() as conn:
      metricObj = repository.getMetric(conn, modelId)
    _LOG.info("Making sure metric is CREATE_PENDING or ACTIVE or PENDING_DATA")

    self.assertIn(
      metricObj.status,
      [MetricStatus.CREATE_PENDING,
       MetricStatus.ACTIVE,
       MetricStatus.PENDING_DATA])

    _LOG.info("Checking modelSpec")
    self.assertEqual(jsonDecode(metricObj.parameters), modelSpec)

    _LOG.info("Waiting for model to become active")
    self.checkModelIsActive(modelId)

    _LOG.info("Waiting at least one model result")
    self.checkModelResultsSize(modelId, 1, atLeast=True)


  def _monitorMetricAndTest(self, adapter, modelSpec):
    """ Start monitoring a metric and perform basic validation

    :param adapter: CloudwatchDatasourceAdapter object

    :param modelSpec: modelSpec to use

    :returns: modelId of the monitored metric

    :raises: does not suppress any exceptions from monitorMetric
    """

    # Turn on monitoring
    modelId = self._monitorMetric(adapter, modelSpec)
    try:
      self._runBasicChecksOnModel(modelId, adapter, modelSpec)
    except:
      adapter.unmonitorMetric(modelId)
      raise

    return modelId


  def testMonitorAndUnmonitorMetric(self):
    """ Test monitorMetric then unmonitorMetric """
    for key in self._supportedResourceTypes:
      for modelSpec in self._testCases[key]["noMinMax"]:
        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())

        modelId = self._monitorMetricAndTest(
          adapter, modelSpec)

        adapter.unmonitorMetric(modelId)
        self.checkModelDeleted(modelId)


  def testMonitorMetricWithoutModelParams(self):
    """ Test monitorMetric of Group Total Instances without optional
    modelParams
    """
    for key in self._supportedResourceTypes:
      for modelSpec in self._testCases[key]["noMinMax"]:
        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())

        modelId = self._monitorMetricAndTest(
          adapter,
          modelSpec)

        # Cleanup
        adapter.unmonitorMetric(modelId)


  def testMonitorMetricWithModelParams(self):
    """ Test monitorMetric of Group Total Instances with optional
    modelParams
    """
    for key in self._supportedResourceTypes:
      for modelSpec in self._testCases[key]["withMinMax"]:
        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())

        modelId = self._monitorMetricAndTest(
          adapter,
          modelSpec)

        # Cleanup
        adapter.unmonitorMetric(modelId)


  def testGetMetricData(self):

    def check(start, end):
      _LOG.info("Getting metric data; start=%s; end=%s; metricSpec=%r",
                start, end, metricSpec)
      samples, nextStartTime = adapter.getMetricData(
        metricSpec=metricSpec,
        start=start,
        end=end)

      _LOG.info("Got %d data samples; head=%s; tail=%s; nextStartTime=%s",
                len(samples), samples[0] if samples else None,
                samples[-1] if samples else None, nextStartTime)

      self.assertIsInstance(samples, (list, tuple))
      self.assertGreaterEqual(len(samples), 1)

      self.assertIsInstance(nextStartTime, datetime.datetime)

      previousTimestamp = None
      for sample in samples:
        self.assertIsInstance(sample, tuple)
        self.assertEqual(len(sample), 2)

        timestamp, value = sample

        self.assertIsInstance(timestamp, datetime.datetime)

        self.assertLess(timestamp, nextStartTime)

        if start is not None:
          self.assertGreaterEqual(timestamp, start)

        if end is not None:
          self.assertLess(timestamp, end)

        self.assertIsInstance(value, (float, int))

        if previousTimestamp is not None:
          self.assertGreater(timestamp, previousTimestamp)

        previousTimestamp = timestamp

    for key in self._supportedResourceTypes:
      for modelSpec in self._testCases[key]["noMinMax"]:
        metricSpec = modelSpec["metricSpec"]

        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())

        check(start=None, end=None)

        check(
          start=(datetime.datetime.utcnow().replace(microsecond=0, second=0) -
                 datetime.timedelta(days=1)),
          end=None
        )


  def testGetMetricResourceStatus(self):
    for key in self._supportedResourceTypes:
      for modelSpec in self._testCases[key]["noMinMax"]:
        metricSpec = modelSpec["metricSpec"]

        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())

        stateName = adapter.getMetricResourceStatus(metricSpec)

        _LOG.info("got resource stateName=%r", stateName)

        validStateNames = (self._validStateNames[key]
                           if key in self._validStateNames
                           else (None, ))

        self.assertIn(stateName, validStateNames)


  def testGetResourceName(self):
    for key in self._supportedResourceTypes:
      if key in self._tagNames:
        metricSpec = self._testCases[key]["noMinMax"][0]["metricSpec"]

        adapter = (datasource_adapter_factory
                   .createCloudwatchDatasourceAdapter())
        nametag = adapter.getMetricResourceName(metricSpec)

        _LOG.info("got resource nametag=%r", nametag)

        self.assertEqual(nametag, self._tagNames[key])



if __name__ == "__main__":
  unittest.main()
