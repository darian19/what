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

""" Integration tests for AutostackDatasourceAdapter
"""

import json

from YOMP import logging_support
from YOMP.YOMP_logging import getExtendedLogger

import YOMP.app
import YOMP.app.adapters.datasource as datasource_adapter_factory
import YOMP.app.exceptions
from YOMP.app import repository
from YOMP.app.repository import schema
from htmengine.repository.queries import MetricStatus
import htmengine.utils
from YOMP.test_utils.app.test_case_base import TestCaseBase, unittest



g_log = None



def setUpModule():
  logging_support.LoggingSupport.initTestApp()

  global g_log  # pylint: disable=W0603
  g_log = getExtendedLogger("autostack_datasource_adapter_test")



class AutostackDatasourceAdapterTest(TestCaseBase):

  stackSpec = {
    "name": "test_stack",
    "aggSpec": {
      "datasource": "cloudwatch",
      "region": "us-west-2",
      "resourceType": "AWS::EC2::Instance",
      "filters": {"tag:Name":["*a*"]}
    }
  }

  modelSpecTemplates = {
    "cloudwatch": {
      "datasource": "autostack",
      "metricSpec": {
        "autostackId": None,  # to be filled by getModelSpec
        "slaveDatasource": "cloudwatch",
        "slaveMetric": {
          "namespace": "AWS/EC2",
          "metric": None  # to be filled by getModelSpec
        }
      }
    },
    "autostack": {
      "datasource": "autostack",
      "metricSpec": {
        "autostackId": None,  # to be filled by getModelSpec
        "slaveDatasource": "autostack",
        "slaveMetric": {
          "namespace": "Autostacks",
          "metric": None  # to be filled by getModelSpec
        }
      }
    }
  }


  @classmethod
  def getModelSpec(cls, datasource, metricName, autostack):
    modelSpec = dict(cls.modelSpecTemplates[datasource])
    modelSpec["metricSpec"]["slaveMetric"]["metric"] = metricName
    modelSpec["metricSpec"]["autostackId"] = autostack.uid
    return modelSpec


  @classmethod
  def setUpClass(cls):
    # Load YOMP API Key as required by TestCaseBase
    cls.apiKey = YOMP.app.config.get("security", "apikey")
    cls.engine = repository.engineFactory()


  def setUp(self):
    g_log.setLogPrefix("<%s> " % (self.id(),))  # pylint: disable=E1103


  @classmethod
  def tearDownClass(cls):
    cls.engine.dispose()


  def _deleteAutostack(self, autostackId):
    with self.engine.connect() as conn:
      repository.deleteAutostack(conn, autostackId)


  def testCreateAutostack(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    autostack = adapter.createAutostack(self.stackSpec)
    self.addCleanup(self._deleteAutostack, autostack.uid)

    self.assertIsNotNone(autostack)
    self.assertEqual(autostack.name, self.stackSpec["name"])
    self.assertEqual(autostack.region, self.stackSpec["aggSpec"]["region"])
    self.assertEqual(htmengine.utils.jsonDecode(autostack.filters),
                     self.stackSpec["aggSpec"]["filters"])


  def testMonitorMetric(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    autostack = adapter.createAutostack(self.stackSpec)
    self.addCleanup(self._deleteAutostack, autostack.uid)

    modelSpec = self.getModelSpec("cloudwatch", "CPUUtilization", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    modelSpec = self.getModelSpec("cloudwatch", "DiskReadBytes", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    modelSpec = self.getModelSpec("cloudwatch", "DiskWriteBytes", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    modelSpec = self.getModelSpec("cloudwatch", "NetworkIn", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    modelSpec = self.getModelSpec("cloudwatch", "NetworkOut", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    modelSpec = self.getModelSpec("autostack", "InstanceCount", autostack)
    modelId = adapter.monitorMetric(modelSpec)
    self.validateModel(modelId, modelSpec, autostack)

    with self.engine.connect() as conn:
      metrics = repository.getAutostackMetrics(conn, autostack.uid)
    self.assertEqual(len([metricObj for metricObj in metrics]), 6)


  def testMonitorMetricThatIsAlreadyMonitored(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    autostack = adapter.createAutostack(self.stackSpec)
    self.addCleanup(self._deleteAutostack, autostack.uid)

    modelSpec = self.getModelSpec("cloudwatch", "CPUUtilization", autostack)
    modelId = adapter.monitorMetric(modelSpec)

    with self.assertRaises(YOMP.app.exceptions.MetricAlreadyMonitored) as cm:
      adapter.monitorMetric(modelSpec)

    self.assertEqual(cm.exception.uid, modelId)


  def testUnmonitorMetric(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    autostack = adapter.createAutostack(self.stackSpec)
    self.addCleanup(self._deleteAutostack, autostack.uid)

    modelSpec = self.getModelSpec("cloudwatch", "CPUUtilization", autostack)
    modelId = adapter.monitorMetric(modelSpec)

    adapter.unmonitorMetric(modelId)
    self.checkModelDeleted(modelId)


  def testExportModel(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    autostack = adapter.createAutostack(self.stackSpec)
    self.addCleanup(self._deleteAutostack, autostack.uid)

    modelSpec = self.getModelSpec("cloudwatch", "CPUUtilization", autostack)
    modelId = adapter.monitorMetric(modelSpec)

    expectedSpec = {
      "datasource": "autostack",
      "stackSpec": self.stackSpec,
      "modelSpec": modelSpec
    }
    del expectedSpec["modelSpec"]["metricSpec"]["autostackId"]
    spec = adapter.exportModel(modelId)

    self.assertEqual(spec, expectedSpec)


  def testImportModel(self):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()

    autostack = adapter.createAutostack(self.stackSpec)

    modelSpec = self.getModelSpec("cloudwatch", "CPUUtilization", autostack)
    modelId = adapter.monitorMetric(modelSpec)

    spec = adapter.exportModel(modelId)
    adapter.unmonitorMetric(modelId)

    modelId = adapter.importModel(spec)
    self.validateModel(modelId, modelSpec, autostack)
    with self.engine.connect() as conn:
      metrics = repository.getAutostackMetrics(conn, autostack.uid)
      self.assertEqual(len([metricObj for metricObj in metrics]), 1)

      # Ensure that import can create an autostack if it doesn't exist
      repository.deleteAutostack(conn, autostack.uid)

    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()

    modelId = adapter.importModel(spec)
    newModelSpec = dict(modelSpec)

    with self.engine.connect() as conn:
      repository.getMetric(conn, modelId)
      autostack = repository.getAutostackFromMetric(conn, modelId)
    self.addCleanup(self._deleteAutostack, autostack.uid)
    newModelSpec["metricSpec"]["autostackId"] = autostack.uid

    self.validateModel(modelId, modelSpec, autostack)



  def validateModel(self, modelId, modelSpec, autostack):
    self.assertIsNotNone(modelId)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn,
                                       modelId,
                                       fields=[schema.metric.c.status,
                                               schema.metric.c.parameters])

      self.assertIn(metricObj.status, [MetricStatus.CREATE_PENDING,
                                       MetricStatus.ACTIVE])
      self.assertEqual(json.loads(metricObj.parameters), modelSpec)
      self.assertEqual(repository.getAutostackFromMetric(conn, modelId).uid,
                       autostack.uid)



if __name__ == "__main__":
  unittest.main()
