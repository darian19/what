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
import unittest
from paste.fixture import TestApp


import taurus.engine
from taurus.engine import logging_support
from taurus.engine.webservices import models_api



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



class TaurusModelsAPITestCase(unittest.TestCase):
  def setUp(self):
    apikey = taurus.engine.config.get("security", "apikey")
    self.headers = {
      "Authorization": "Basic %s" % base64.b64encode(apikey + ":")
    }

    self.app = TestApp(models_api.app.wsgifunc())


  def testCreateModels(self):
    """ Taurus Models API properly passes incoming model parameters to
    datasource adapter.  This mirrors the path taken by
    `taurus.metric_collectors.metric_utils.createAllModels()` and tests the
    expected API.
    """

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

        response = self.app.put("/", json.dumps(params), headers=self.headers)

        response = json.loads(response.body)
        responseModel = response[0]
        self.addCleanup(self.app.delete, "/" + responseModel["uid"],
                        headers=self.headers)
        self.assertEqual(responseModel["name"], metricName)
        self.assertEqual(responseModel["server"], resName)
        self.assertIn("modelParams", responseModel["parameters"])
        self.assertIn("minResolution",
                      responseModel["parameters"]["modelParams"])
        self.assertEqual(
          responseModel["parameters"]["modelParams"]["minResolution"],
          metricVal["modelParams"]["minResolution"])
        self.assertIn("metricSpec", responseModel["parameters"])
        self.assertIn("metric", responseModel["parameters"]["metricSpec"])
        self.assertEqual(responseModel["parameters"]["metricSpec"]["metric"],
                         metricName)
        self.assertIn("resource", responseModel["parameters"]["metricSpec"])
        self.assertEqual(responseModel["parameters"]["metricSpec"]["resource"],
                         resName)
        self.assertIn("userInfo", responseModel["parameters"]["metricSpec"])
        self.assertIn("symbol",
                      responseModel["parameters"]["metricSpec"]["userInfo"])
        self.assertEqual(
          responseModel["parameters"]["metricSpec"]["userInfo"]["symbol"],
          resVal["symbol"])
        self.assertIn(
          "metricType",
          responseModel["parameters"]["metricSpec"]["userInfo"])
        self.assertEqual(
          responseModel["parameters"]["metricSpec"]["userInfo"]["metricType"],
          metricVal["metricType"])
        self.assertIn(
          "metricTypeName",
          responseModel["parameters"]["metricSpec"]["userInfo"])
        self.assertEqual(
          responseModel["parameters"]["metricSpec"]["userInfo"]["metricTypeName"],
          metricVal["metricTypeName"])



if __name__ == "__main__":
  unittest.main()
