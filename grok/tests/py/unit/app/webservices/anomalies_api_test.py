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
Unit tests for Sorted Metrics API
"""
import json

import unittest
from mock import patch, Mock
from paste.fixture import TestApp

import YOMP.app
from YOMP.app.webservices import anomalies_api
from htmengine.utils import jsonEncode
from YOMP.test_utils.app.webservices import getDefaultHTTPHeaders


class TestAnomaliesHandler(unittest.TestCase):
  """
  Unit tests for AnomaliesHandler
  """


  @classmethod
  def setUpClass(cls):
    metric1 = Mock(uid="cebe9fab-f416-4845-8dab-02d292244112",
                   datasource="cloudwatch",
                   description=
                     "DatabaseConnections for YOMPdb2 "
                     "in us-east-1",
                   server="us-east-1/AWS/RDS/YOMPdb2",
                   location="us-east-1",
                   parameters=jsonEncode(
                     {"region":"us-east-1", "DBInstanceIdentifier":"YOMPdb2"}),
                   status=1,
                   message=None,
                   collector_error=False,
                   last_timestamp="2013-08-15 21:25:00",
                   poll_interval=60,
                   tag_name=None,
                   model_params=None,
                   last_rowid=0)
    metric1.name = "AWS/RDS/Metric2"

    metric2 = Mock(uid="cebe9fab-f416-4845-8dab-02d292244111",
                   datasource="cloudwatch",
                   description=
                     "DatabaseConnections for YOMPdb2 "
                     "in us-east-1",
                   server="us-east-1/AWS/RDS/YOMPdb2",
                   location="us-east-1",
                   parameters=jsonEncode(
                     {"region":"us-east-1", "DBInstanceIdentifier":"YOMPdb2"}),
                   status=1,
                   message=None,
                   collector_error=False,
                   last_timestamp="2013-08-15 21:25:00",
                   poll_interval=60,
                   tag_name="Test 1",
                   model_params=None,
                   last_rowid=0)
    metric2.name = "AWS/RDS/Metric1"

    metric3 = Mock(uid="cebe9fab-f416-4845-8dab-02d292244113",
                   datasource="cloudwatch",
                   description=
                     "DatabaseConnections for YOMPdb2 "
                     "in us-east-1",
                   server="us-east-1/AWS/RDS/YOMPdb2",
                   location="us-east-1",
                   parameters=jsonEncode(
                     {"region":"us-east-1", "DBInstanceIdentifier":"YOMPdb2",
                      "InstanceID":"i-733"}),
                   status=1,
                   message=None,
                   collector_error=False,
                   last_timestamp="2013-08-15 21:25:00",
                   poll_interval=60,
                   tag_name="Test 2",
                   model_params=None,
                   last_rowid=0)
    metric3.name = "AWS/RDS/Metric3"

    metric4 = Mock(uid="cebe9fab-f416-4845-8dab-02d292244114",
                   datasource="cloudwatch",
                   description=
                     "DatabaseConnections for YOMPdb3 "
                     "in us-east-1",
                   server="us-east-1/AWS/RDS/YOMPdb3",
                   location="us-east-1",
                   parameters=jsonEncode(
                     {"region":"us-east-1", "DBInstanceIdentifier":"YOMPdb3",
                      "InstanceID":"i-442"}),
                   status=1,
                   message=None,
                   collector_error=False,
                   last_timestamp="2013-08-15 21:25:00",
                   poll_interval=60,
                   tag_name="Test 2",
                   model_params=None,
                   last_rowid=0)
    metric4.name = "AWS/RDS/Metric4"

    cls.metrics = [metric1, metric2, metric3, metric4]


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(anomalies_api.app.wsgifunc())

  @patch("YOMP.app.repository.engineFactory", autospec=True)
  @patch("YOMP.app.repository.getMetricIdsSortedByDisplayValue", autospec=True)
  @patch("YOMP.app.repository.getAllMetrics", autospec=True)
  def testGETMetricsByPeriod(self, getAllMetricsMock,
                     getMetricIdsSortedByDisplayValueMock,
                     _getEngineMock,
                     *args):
    getMetricIdsSortedByDisplayValueMock.return_value = {
      'cebe9fab-f416-4845-8dab-02d292244111': 3,
      'cebe9fab-f416-4845-8dab-02d292244112': 2,
      'cebe9fab-f416-4845-8dab-02d292244113': 1,
      'cebe9fab-f416-4845-8dab-02d292244114': 4,
    }
    getAllMetricsMock.return_value = self.metrics
    response = self.app.get("/period/2", headers=self.headers)

    self.assertEqual(response.status, 200)
    result = json.loads(response.body)
    # Ensure that the order of the response matches the descending order of the
    # values defined in repository.getMetricIdsSortedByDisplayValue()
    self.assertEqual(result[0]['uid'], 'cebe9fab-f416-4845-8dab-02d292244114')
    self.assertEqual(result[1]['uid'], 'cebe9fab-f416-4845-8dab-02d292244111')
    self.assertEqual(result[2]['uid'], 'cebe9fab-f416-4845-8dab-02d292244112')
    self.assertEqual(result[3]['uid'], 'cebe9fab-f416-4845-8dab-02d292244113')


  @patch("YOMP.app.repository.engineFactory", autospec=True)
  @patch("YOMP.app.repository.getAllMetrics", autospec=True)
  def testGETMetricsByName(self, getAllMetricsMock, _getEngineMock, *args):
    getAllMetricsMock.return_value = self.metrics

    response = self.app.get("/name", headers=self.headers)
    self.assertEqual(response.status, 200)
    result = json.loads(response.body)
    # Ensure that the order of the response matches descending order by name
    self.assertEqual(result[0]['uid'], 'cebe9fab-f416-4845-8dab-02d292244111')
    self.assertEqual(result[1]['uid'], 'cebe9fab-f416-4845-8dab-02d292244114')
    self.assertEqual(result[2]['uid'], 'cebe9fab-f416-4845-8dab-02d292244113')
    self.assertEqual(result[3]['uid'], 'cebe9fab-f416-4845-8dab-02d292244112')



if __name__ == "__main__":
  unittest.main()
