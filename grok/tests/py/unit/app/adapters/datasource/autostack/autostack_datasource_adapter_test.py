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

""" Unit tests for AutostackDatasourceAdapter
"""

from mock import patch
import unittest

import YOMP.app.adapters.datasource as datasource_adapter_factory
from YOMP.app.exceptions import ObjectNotFoundError



@patch("htmengine.repository.engineFactory")
class AutostackDatasourceAdapterTest(unittest.TestCase):

  def testCreateAutostackNoName(self, _mockEngineFactory):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    stackSpec = {
      "aggSpec": {
        "datasource": "cloudwatch",
        "region": "us-west-2",
        "resourceType": "AWS::EC2::Instance",
        "filters": {
          "tag:Name":["*a*"]
        }
      }
    }
    self.assertRaises(ValueError, adapter.createAutostack, stackSpec)


  def testCreateAutostackEmptyName(self, _mockEngineFactory):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    stackSpec = {
      "name": "",
      "aggSpec": {
        "datasource": "cloudwatch",
        "region": "us-west-2",
        "resourceType": "AWS::EC2::Instance",
        "filters": {
          "tag:Name":["*a*"]
        }
      }
    }
    self.assertRaises(ValueError, adapter.createAutostack, stackSpec)


  @patch("YOMP.app.adapters.datasource.autostack.repository.getAutostack")
  def testMonitorMetricNoExistingAutostack(self, getAutostackMock,
                                           _mockEngineFactory):
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    modelSpec = {
      "datasource": "autostack",
      "metricSpec": {
        "autostackId": "9y2wn39y823nw9y8",
        "slaveDatasource": "cloudwatch",
        "slaveMetric": {
          "namespace": "AWS/EC2",
          "metric": "CPUUtilization",
          "dimensions": {
            "InstanceId": None
          },
          "period": 300
        }
      }
    }
    getAutostackMock.side_effect = ObjectNotFoundError()

    self.assertRaises(ObjectNotFoundError, adapter.monitorMetric, modelSpec)


if __name__ == "__main__":
  unittest.main()
