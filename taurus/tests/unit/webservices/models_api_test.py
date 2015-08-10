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

import base64
import json
from mock import ANY, Mock, patch
import unittest
from paste.fixture import TestApp

from  htmengine.adapters.datasource.datasource_adapter_iface import (
  DatasourceAdapterIface
)

import taurus.engine
from taurus.engine import logging_support, repository
from taurus.engine.webservices import models_api



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



@patch.object(repository, "engineFactory", autospec=True)
class TaurusModelsAPITestCase(unittest.TestCase):
  def setUp(self):
    apikey = taurus.engine.config.get("security", "apikey")
    self.headers = {
      "Authorization": "Basic %s" % base64.b64encode(apikey + ":")
    }

    self.app = TestApp(models_api.app.wsgifunc())


  @patch("taurus.engine.webservices.models_api.createDatasourceAdapter")
  def testCreateModels(self, datasourceMock, _engineMock):
    """ Taurus Models API properly passes incoming model parameters to
    datasource adapter.  This mirrors the path taken by
    `taurus.engine.metric_collectors.metric_utils.createAllModels()` and tests
    the expected API.
    """

    datasourceMock.return_value = Mock(spec_set=DatasourceAdapterIface)

    # Snippet from taurus.metric_collectors models.json file
    metricsConfiguration = {
      "3M": {
        "metrics": {
          "TWITTER.TWEET.HANDLE.MMM.VOLUME": {
            "metricType": "TwitterVolume",
            "metricTypeName": "Twitter Volume",
            "modelParams": {
              "minResolution": 0.6
            },
            "provider": "twitter",
            "screenNames": [
              "3M"
            ]
          },
          "XIGNITE.MMM.CLOSINGPRICE": {
            "metricType": "StockPrice",
            "metricTypeName": "Stock Price",
            "modelParams": {
              "minResolution": 0.2
            },
            "provider": "xignite",
            "sampleKey": "Close"
          },
          "XIGNITE.MMM.VOLUME": {
            "metricType": "StockVolume",
            "metricTypeName": "Stock Volume",
            "modelParams": {
              "minResolution": 0.2
            },
            "provider": "xignite",
            "sampleKey": "Volume"
          }
        },
        "stockExchange": "NYSE",
        "symbol": "MMM"
      }
    }

    for resName, resVal in metricsConfiguration.iteritems():
      for metricName, metricVal in resVal["metrics"].iteritems():
        params = {
          "datasource": "custom",
          "metricSpec": {
            "metric": metricName,
            "resource": resName,
            "userInfo": {
              "metricType": metricVal["metricType"],
              "metricTypeName": metricVal["metricTypeName"],
              "symbol": resVal["symbol"]
            }
          },
          "modelParams": metricVal["modelParams"]
        }

        self.app.put("/", json.dumps(params), headers=self.headers)

        self.assertTrue(datasourceMock.called)
        self.assertTrue(datasourceMock.return_value.monitorMetric.called)
        datasourceMock.return_value.monitorMetric.assert_called_once_with({
          "datasource": "custom",
          "metricSpec": {
            "metric": metricName,
            "resource": resName,
            "userInfo": {
              "metricType": metricVal["metricType"],
              "metricTypeName": metricVal["metricTypeName"],
              "symbol": resVal["symbol"]}
          },
          "modelParams": {
            "minResolution": metricVal["modelParams"]["minResolution"]
          }
        })

        datasourceMock.reset_mock()


  @patch("taurus.engine.webservices.models_api.createDatasourceAdapter")
  @patch("taurus.engine.webservices.models_api.repository", autospec=True)
  def testDelete(self, repositoryMock, datasourceMock, _engineMock):
    """ Test that a model is deleted at /_models/<model id>
    """
    datasourceMock.return_value = Mock(spec_set=DatasourceAdapterIface)

    self.app.delete("/foo", headers=self.headers)

    self.assertTrue(repositoryMock.getMetric.called)
    repositoryMock.getMetric.assert_called_once_with(ANY, "foo")
    self.assertTrue(datasourceMock.called)
    self.assertTrue(datasourceMock.return_value.unmonitorMetric.called)
    datasourceMock.return_value.unmonitorMetric.assert_called_once_with("foo")


  @patch("taurus.engine.webservices.models_api.repository", autospec=True)
  def testGetModel(self, repositoryMock, _engineMock):
    """ Test that a model is available at /_models/<model id>
    """
    self.app.get("/foo", headers=self.headers)

    self.assertTrue(repositoryMock.getMetric.called)
    repositoryMock.getMetric.assert_called_once_with(ANY, "foo", ANY)


  @patch("taurus.engine.webservices.models_api.repository", autospec=True)
  def testGetAllModels(self, repositoryMock, _engineMock):
    """ Test that all models available at /_models/
    """
    self.app.get("/", headers=self.headers)

    self.assertTrue(repositoryMock.getAllModels.called)



if __name__ == "__main__":
  unittest.main()


