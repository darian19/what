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

""" Integration tests for Base methods of in CloudwatchDatasourceAdapter
"""

import json
import os
import yaml

from YOMP import logging_support
from YOMP.YOMP_logging import getExtendedLogger

import YOMP.app
import YOMP.app.adapters.datasource as datasource_adapter_factory
from YOMP.app.adapters.datasource.cloudwatch import aws_base
import YOMP.app.exceptions as app_exceptions
from YOMP.app import repository
from YOMP.app.repository import schema
from htmengine.repository.queries import MetricStatus
import htmengine.utils

from YOMP.test_utils.app.test_case_base import TestCaseBase, unittest
import YOMP.test_utils.aws_utils



_LOG = getExtendedLogger("cw_datasource_adapter_base_test")



class CloudwatchDatasourceAdapterBaseTest(TestCaseBase):

  # EC2 Region name of the test ec2 instance
  _testRegion = None
  _testId = None

  _modelSpecNoMinMax = None
  _modelSpecWithMinMax = None

  # What we expect to be supported so far
  _expectedResourceTypes = [
    aws_base.ResourceTypeNames.EC2_INSTANCE,
    aws_base.ResourceTypeNames.AUTOSCALING_GROUP,
    aws_base.ResourceTypeNames.DYNAMODB_TABLE,
    aws_base.ResourceTypeNames.ELB_LOAD_BALANCER,
    aws_base.ResourceTypeNames.EBS_VOLUME,
    aws_base.ResourceTypeNames.OPSWORKS_STACK,
    aws_base.ResourceTypeNames.RDS_DBINSTANCE,
    aws_base.ResourceTypeNames.REDSHIFT_CLUSTER,
    aws_base.ResourceTypeNames.SNS_TOPIC,
    aws_base.ResourceTypeNames.SQS_QUEUE
  ]


  @classmethod
  def setUpClass(cls):
    with open(os.path.join(
        YOMP.app.YOMP_HOME,
        "tests/py/integration/app/test_resources.yaml")) as fin:
      resources = yaml.load(fin)
    testCase = resources[aws_base.ResourceTypeNames.EC2_INSTANCE][0]

    cls._testRegion = testCase["region"]
    cls._testId = testCase["dimensions"]["InstanceId"]
    # Load YOMP API Key as required by TestCaseBase
    cls.apiKey = YOMP.app.config.get("security", "apikey")

    cls._modelSpecNoMinMax = {"datasource":testCase["datasource"],
                              "metricSpec":{
                                "region":testCase["region"],
                                "namespace":testCase["namespace"],
                                "metric":testCase["metric"],
                                "dimensions":testCase["dimensions"]}}

    cls.engine = repository.engineFactory()

  def setUp(self):
    _LOG.setLogPrefix("<%s> " % (self.id(),))  # pylint: disable=E1103

    self.connFactory = self.engine.connect


  @classmethod
  def tearDownClass(cls):
    cls.engine.dispose()


  def _monitorMetric(self, adapter, modelSpec):  # pylint: disable=R0201
    """ Start monitoring a metric and return its modelId

    :param adapter: CloudwatchDatasourceAdapter object

    :param modelSpec: modelSpec to use

    :returns: modelId of the monitored metric

    :raises: does not suppress any exceptions from monitorMetric
    """
    _LOG.info("Creating %s/%s metric on EC2 Instance=%s in %s",
               modelSpec["metricSpec"]["namespace"],
               modelSpec["metricSpec"]["metric"],
               modelSpec["metricSpec"]["dimensions"]["InstanceId"],
               modelSpec["metricSpec"]["region"])

    # Turn on monitoring
    return adapter.monitorMetric(modelSpec)


  def _runBasicChecksOnModel(self, modelId, _adapter, modelSpec):

    with self.connFactory() as conn:
      metricObj = repository.getMetric(conn,
                                       modelId,
                                       fields=[schema.metric.c.status,
                                               schema.metric.c.parameters])

    _LOG.info("Making sure metric is CREATE_PENDING or ACTIVE")
    self.assertIn(
      metricObj.status,
      [MetricStatus.CREATE_PENDING,
       MetricStatus.ACTIVE])

    _LOG.info("Checking modelSpec")
    self.assertEqual(json.loads(metricObj.parameters), modelSpec)

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


  def testMonitorMetricThatIsAlreadyMonitored(self):
    """ monitorMetric should raise if already monitored """
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    modelId = self._monitorMetric(adapter, self._modelSpecNoMinMax)

    with self.assertRaises(app_exceptions.MetricAlreadyMonitored) as cm:
      adapter.monitorMetric(self._modelSpecNoMinMax)

    self.assertEqual(cm.exception.uid, modelId)

    # Cleanup
    adapter.unmonitorMetric(modelId)


  def testActivateModel(self):
    """ Test activateModel """
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    modelId = self._monitorMetric(adapter, self._modelSpecNoMinMax)

    adapter.activateModel(modelId)

    self._runBasicChecksOnModel(modelId, adapter, self._modelSpecNoMinMax)

    # Cleanup
    adapter.unmonitorMetric(modelId)


  def _checkModelExportImport(self, modelSpec):

    def checkExportSpec(exportSpec):
      self.assertEqual(exportSpec, modelSpec)

    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    modelId = self._monitorMetric(adapter, modelSpec)
    try:
      # Export
      _LOG.info("Exporting model")
      exportSpec = adapter.exportModel(modelId)
      checkExportSpec(exportSpec)

      # Unmonitor
      _LOG.info("Unmonitoring")
      adapter.unmonitorMetric(modelId)
      self.checkModelDeleted(modelId)

      # Import
      _LOG.info("Importing")
      modelId = adapter.importModel(exportSpec)
      self._runBasicChecksOnModel(modelId, adapter, modelSpec)

      # Export again
      _LOG.info("Exporting again")
      exportSpec = adapter.exportModel(modelId)
      checkExportSpec(exportSpec)
    except:
      try:
        adapter.unmonitorMetric(modelId)
      except app_exceptions.ObjectNotFoundError:
        pass
    else:
      adapter.unmonitorMetric(modelId)


  def testExportImportNoMinMax(self):
    self._checkModelExportImport(self._modelSpecNoMinMax)


  @unittest.skip("TODO: Duplicate of testExportImportNoMinMax")
  def testExportImportWithMinMax(self):
    self._checkModelExportImport(self._modelSpecNoMinMax)


  def testDescribeRegions(self):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    regionSpecs = adapter.describeRegions()
    _LOG.info("got %d region descriptions", len(regionSpecs))

    self.assertIsInstance(regionSpecs, tuple)

    expectedRegionNames = (
      "ap-northeast-1",
      "ap-southeast-1",
      "ap-southeast-2",
      "eu-west-1",
      "sa-east-1",
      "us-east-1",
      "us-west-1",
      "us-west-2"
    )

    regionNames = tuple(name for name, description in regionSpecs)

    self.assertItemsEqual(regionNames, expectedRegionNames)

    for item in regionSpecs:
      self.assertIsInstance(item, tuple)
      self.assertEqual(len(item), 2)
      name, description = item
      self.assertIsInstance(name, basestring)
      self.assertIsInstance(description, basestring)


  def testListSupportedResourceTypes(self):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    supportedResourceTypes = adapter.listSupportedResourceTypes()
    _LOG.info("Got %d supported resource types", len(supportedResourceTypes))


    self.assertItemsEqual(supportedResourceTypes, self._expectedResourceTypes)


  def testDescribeSupportedMetrics(self):
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    supportedMetricDescriptions = adapter.describeSupportedMetrics()
    _LOG.info("Got %d supported metric description resource groups",
               len(supportedMetricDescriptions))

    self.assertIsInstance(supportedMetricDescriptions, dict)

    self.assertItemsEqual(
      supportedMetricDescriptions.keys(),
      self._expectedResourceTypes)

    for value in supportedMetricDescriptions.itervalues():
      self.assertIsInstance(value, dict)
      for metricName, metricInfo in value.iteritems():
        self.assertIsInstance(metricName, basestring)

        self.assertItemsEqual(metricInfo.keys(),
                              ["namespace", "dimensionGroups"])
        self.assertIsInstance(metricInfo["namespace"], basestring)
        self.assertIsInstance(metricInfo["dimensionGroups"], tuple)
        for dimensionGroup in metricInfo["dimensionGroups"]:
          self.assertIsInstance(dimensionGroup, tuple)
          for dimensionName in dimensionGroup:
            self.assertIsInstance(dimensionName, basestring)


if __name__ == "__main__":
  logging_support.LoggingSupport.initTestApp()
  unittest.main()
