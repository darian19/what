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

# Disable "Access to a protected member" warning
# pylint: disable=W0212

import os
import datetime
import json
import msgpack
import StringIO
import time
import web
import unittest
from collections import namedtuple
from paste.fixture import TestApp
from mock import ANY, create_autospec, MagicMock, Mock, patch

from YOMP import logging_support
import YOMP.app

from htmengine import utils as app_utils
from htmengine.model_swapper import utils as model_swapper_utils
from YOMP.app.adapters.datasource import createDatasourceAdapter
from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
  AWSResourceAdapterBase)
from YOMP.app.webservices import models_api
from YOMP.app.webservices.responses import InvalidRequestResponse
from YOMP.app.webservices.utils import getMetricDisplayFields
from htmengine.exceptions import ObjectNotFoundError
from YOMP.app import repository
from YOMP.app.repository.queries import MetricStatus
from htmengine.utils import jsonDecode, jsonEncode
from YOMP.test_utils.app.webservices import (
  getDefaultHTTPHeaders,
  getInvalidHTTPHeaders,
  webservices_assertions as assertions
)

from sqlalchemy.engine.base import Connection, Engine



def setUpModule():
  logging_support.LoggingSupport.initTestApp()


METRIC_DISPLAY_FIELDS = set(["uid",
                             "datasource",
                             "name",
                             "description",
                             "server",
                             "location",
                             "parameters",
                             "status",
                             "message",
                             "last_timestamp",
                             "poll_interval",
                             "tag_name",
                             "last_rowid"])


@patch.object(repository, "engineFactory", autospec=True)
class TestModelHandler(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.model_list = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/models_list.json")))


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(models_api.app.wsgifunc())
    metric = Mock(uid="cebe9fab-f416-4845-8dab-02d292244112",
                  datasource="cloudwatch",
                  description="The number of database connections in use by "
                              "Amazon RDS database",
                  server="YOMPdb2",
                  location="us-east-1",
                  parameters=app_utils.jsonEncode(
                    {"region":"us-east-1", "DBInstanceIdentifier":"YOMPdb2"}),
                  status=1,
                  message=None,
                  collector_error=None,
                  last_timestamp="2013-08-15 21:25:00",
                  poll_interval=60,
                  tag_name=None,
                  model_params=None,
                  last_rowid=20277)

    metric.name = "AWS/RDS/DatabaseConnections"
    self.metric = metric



  @patch.object(repository, 'getAllModels', autospec=True)
  def testModelHandlerListModelsEmptyResponse(self, getAllModelsMock,
                                              _engineMock, *args):
    getAllModelsMock.return_value = []
    response = self.app.get("", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual(result, [])


  @patch.object(repository, 'getAllModels', autospec=True)
  def testModelHandlerListModelsWithSlashEmptyResponse(self, getAllModelsMock,
                                              _engineMock, *args):
    getAllModelsMock.return_value = []
    response = self.app.get("/", headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual(result, [])


  @patch("YOMP.app.webservices.models_api.repository", autospec=True)
  @patch("YOMP.app.webservices.models_api.getMetricDisplayFields")
  def testModelHandlerListModelsWithSlashValidResponse(
      self, getMetricDisplayFieldsMock, repositoryMock, _engineMock, *args):

    cols = []
    for key in METRIC_DISPLAY_FIELDS:
      m = Mock()
      m.configure_mock(name=key)
      cols.append(m)

    getMetricDisplayFieldsMock.return_value=cols

    metric = Mock(**dict((col, getattr(self.metric, col))
                         for col in METRIC_DISPLAY_FIELDS))
    metric.keys.return_value = [col for col in METRIC_DISPLAY_FIELDS]
    metric.name = self.metric.name

    repositoryMock.getAllModels = Mock(return_value=[metric])

    response = self.app.get('/', headers=self.headers)
    assertions.assertSuccess(self, response)


    self.assertEqual(json.loads(response.body), self.model_list)


  @patch("YOMP.app.webservices.models_api.getMetricDisplayFields")
  @patch.object(models_api.ModelHandler, "createModel",
    spec_set=models_api.ModelHandler.createModel)
  def testModelHandlerPOSTModel(self, createModel, getMetricDisplayFieldsMock,
                                _engineMock):
    cols = []
    for key in METRIC_DISPLAY_FIELDS:
      m = Mock()
      m.configure_mock(name=key)
      cols.append(m)

    getMetricDisplayFieldsMock.return_value=cols

    metric = Mock(**dict((col, getattr(self.metric, col))
                         for col in METRIC_DISPLAY_FIELDS))
    metric.keys.return_value = [col for col in METRIC_DISPLAY_FIELDS]
    metric.name = self.metric.name

    createModel.return_value = metric

    params = {"type": "metric",
              "region": "us-east-1",
              "namespace": "AWS/EC2",
              "datasource": "cloudwatch",
              "metric": "CPUUtilization",
              "dimensions": {
                "InstanceId": "i-0c149c66"
              }}
    response = self.app.post("/", json.dumps(params), headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 201)
    assertions.assertResponseHeaders(self, response, "json")
    self.assertTrue(createModel.called)


  @patch("YOMP.app.webservices.models_api.getMetricDisplayFields")
  @patch.object(models_api.ModelHandler, "createModel",
     spec_set=models_api.ModelHandler.createModel)
  def testModelHandlerPUTModelCreate(self, createModel,
                                     getMetricDisplayFieldsMock, _engineMock):
    cols = []
    for key in METRIC_DISPLAY_FIELDS:
      m = Mock()
      m.configure_mock(name=key)
      cols.append(m)

    getMetricDisplayFieldsMock.return_value=cols

    metric = Mock(**dict((col, getattr(self.metric, col))
                         for col in METRIC_DISPLAY_FIELDS))
    metric.keys.return_value = [col for col in METRIC_DISPLAY_FIELDS]
    metric.name = self.metric.name

    createModel.return_value = metric

    params = {"type": "metric",
              "region": "us-east-1",
              "namespace": "AWS/EC2",
              "datasource": "cloudwatch",
              "metric": "CPUUtilization",
              "dimensions": {
                "InstanceId": "i-0c149c66"
              }}
    response = self.app.put("/", json.dumps(params), headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 201)
    assertions. assertResponseHeaders(self, response, "json")
    self.assertTrue(createModel.called)



  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.getMetricDisplayFields")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  @patch("YOMP.app.webservices.models_api.repository", autospec=True)
  def testModelHandlerPUTMonitorMetric(self,
                                       repositoryMock,
                                       createDatasourceAdapterMock,
                                       getMetricDisplayFieldsMock,
                                       quotaRepositoryMock,
                                       engineMock):

    cols = []
    for key in METRIC_DISPLAY_FIELDS:
      m = Mock()
      m.configure_mock(name=key)
      cols.append(m)

    getMetricDisplayFieldsMock.return_value=cols

    metric = Mock(**dict((col, getattr(self.metric, col))
                         for col in METRIC_DISPLAY_FIELDS))
    metric.keys.return_value = [col for col in METRIC_DISPLAY_FIELDS]
    metric.name = self.metric.name

    quotaRepositoryMock.getInstanceCount.return_value = 0
    repositoryMock.getMetric.return_value = metric

    params = {
        "region": "us-east-1",
        "namespace": "AWS/EC2",
        "datasource": "cloudwatch",
        "metric": "CPUUtilization",
        "dimensions": {
            "InstanceId": "i-0c149c66"
        }
    }

    response = self.app.put("/", json.dumps(params), headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 201)
    assertions.assertResponseHeaders(self, response, "json")
    repositoryMock.getMetric.assert_called_once_with(
      engineMock.return_value.connect.return_value.__enter__.return_value,
      createDatasourceAdapterMock.return_value.monitorMetric.return_value)


  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.getMetricDisplayFields")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  @patch("YOMP.app.webservices.models_api.repository", autospec=True)
  def testModelHandlerPUTImportModel(self,
                                     repositoryMock,
                                     createDatasourceAdapterMock,
                                     getMetricDisplayFieldsMock,
                                     quotaRepositoryMock,
                                     engineMock):
    cols = []
    for key in METRIC_DISPLAY_FIELDS:
      m = Mock()
      m.configure_mock(name=key)
      cols.append(m)

    getMetricDisplayFieldsMock.return_value=cols

    metric = Mock(**dict((col, getattr(self.metric, col))
                         for col in METRIC_DISPLAY_FIELDS))
    metric.keys.return_value = [col for col in METRIC_DISPLAY_FIELDS]
    metric.name = self.metric.name

    quotaRepositoryMock.getInstanceCount.return_value = 0
    repositoryMock.getMetric.return_value = metric

    params = {
        "type": "metric",
        "region": "us-east-1",
        "namespace": "AWS/EC2",
        "datasource": "cloudwatch",
        "metric": "CPUUtilization",
        "dimensions": {
            "InstanceId": "i-0c149c66"
        }
    }
    response = self.app.put("/", json.dumps(params), headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 201)
    assertions.assertResponseHeaders(self, response, "json")
    repositoryMock.getMetric.assert_called_once_with(
      engineMock.return_value.connect.return_value.__enter__.return_value,
      createDatasourceAdapterMock.return_value.importModel.return_value)


  @patch.object(models_api.ModelHandler, "deleteModel",
    spec_set=models_api.ModelHandler.deleteModel)
  def testModelHandlerDELETEModel(self, deleteModel, _engineMock):
    response = self.app.delete("/12232-jn939", headers=self.headers)
    self.assertTrue(deleteModel.called)
    assertions.assertResponseStatusCode(self, response, 200)
    assertions. assertResponseHeaders(self, response, "json")


  @patch.object(web, "data", return_value=None, autospec=True)
  def testCreateModelEmpty(self, data, _engineMock):
    response = self.app.post("/", {}, headers=self.headers, status="*")
    assertions.assertBadRequest(self, response)
    self.assertTrue(data.called)


  @patch.object(repository, "getMetric", autospec=True)
  def testDeleteModelInvalid(self, getMetricMock, _engineMock):
    getMetricMock.side_effect = ObjectNotFoundError("Test")
    response = self.app.delete("/12232-jn939", headers=self.headers,
      status="*")
    assertions.assertNotFound(self, response)
    self.assertEqual("ObjectNotFoundError Metric not found:"
                     " Metric ID: 12232-jn939", response.body)


  @patch.object(repository, "deleteModel", autospec=True)
  @patch.object(repository, "getMetric", autospec=True)
  @patch.object(model_swapper_utils, "deleteHTMModel",
    spec_set=model_swapper_utils.deleteHTMModel)
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         auto_spec=True)
  def testDeleteModelValid(self, _createDatasourceAdapterMock,
                           _deleteHTMModel, _getMetricMock, _deleteModelMock,
                           _engineMock):
    response = self.app.delete("/12232-jn939", headers=self.headers)
    result = jsonDecode(response.body)
    self.assertEqual(result, {"result": "success"})


  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.repository")
  @patch("web.ctx")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  def testCreateModelForMonitorMetric(self,
                                      createDatasourceAdapterMock,
                                      ctxMock,
                                      repositoryMock,
                                      quotaRepositoryMock,
                                      _engineMock): # pylint: disable=W0613
    nativeMetric = {
        "region": "us-west-2",
        "namespace": "AWS/EC2",
        "datasource": "cloudwatch",
        "metric": "CPUUtilization",
        "dimensions": {
          "InstanceId": "i-ab15a19d"
        }
      }

    metricSpec = {
        "region": nativeMetric["region"],
        "namespace": nativeMetric["namespace"],
        "metric": nativeMetric["metric"],
        "dimensions": nativeMetric["dimensions"]
      }

    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    (createDatasourceAdapterMock
     .return_value
     .getInstanceNameForModelSpec
     .return_value) = metricAdapter.getCanonicalResourceName()

    quotaRepositoryMock.getInstanceCount.return_value = 0

    result = models_api.ModelHandler.createModel(nativeMetric)

    self.assertIs(result, repositoryMock.getMetric.return_value)

    repositoryMock.getMetric.assert_called_once_with(
      ctxMock.connFactory.return_value.__enter__.return_value,
      createDatasourceAdapterMock.return_value.monitorMetric.return_value)


  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.repository")
  @patch("web.ctx")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  def testCreateModelForImportModel(self,
                                    createDatasourceAdapterMock,
                                    ctxMock,
                                    repositoryMock,
                                    quotaRepositoryMock,
                                    _engineMock):
    nativeMetric = {
        "type": "metric",
        "region": "us-west-2",
        "namespace": "AWS/EC2",
        "datasource": "cloudwatch",
        "metric": "CPUUtilization",
        "dimensions": {
          "InstanceId": "i-ab15a19d"
        }
      }

    metricSpec = {
        "region": nativeMetric["region"],
        "namespace": nativeMetric["namespace"],
        "metric": nativeMetric["metric"],
        "dimensions": nativeMetric["dimensions"]
      }

    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    (createDatasourceAdapterMock
     .return_value
     .getInstanceNameForModelSpec
     .return_value) = metricAdapter.getCanonicalResourceName()

    quotaRepositoryMock.getInstanceCount.return_value = 0

    result = models_api.ModelHandler.createModel(nativeMetric)

    self.assertIs(result, repositoryMock.getMetric.return_value)

    repositoryMock.getMetric.assert_called_once_with(
      ctxMock.connFactory.return_value.__enter__.return_value,
      createDatasourceAdapterMock.return_value.importModel.return_value)

  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.repository")
  @patch("web.ctx")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  def testImportModelAutostack(self, adapterMock, ctxMock, repositoryMock,
                               quotaRepositoryMock, _engineMock):
    nativeMetric = {
      "type": "autostack",
      "name": "test1",
      "region": "us-west-2",
      "datasource": "cloudwatch",
      "filters": {
        "tag:Name": [
          "*d*"
        ]
      },
      "metric": {
        "metric": "DiskWriteBytes",
        "namespace": "AWS/EC2"
      }
    }

    quotaRepositoryMock.getInstanceCount.return_value = 0

    adapter = createDatasourceAdapter("autostack")
    importModelMock = create_autospec(adapter.importModel)
    adapterMock.return_value.importModel = importModelMock

    result = models_api.ModelHandler.createModel(nativeMetric)
    self.assertIs(result, repositoryMock.getMetric.return_value)
    repositoryMock.getMetric.assert_called_once_with(
      ctxMock.connFactory.return_value.__enter__.return_value,
      adapterMock.return_value.importModel.return_value)


  @patch("web.webapi.ctx")
  @patch("YOMP.app.webservices.web.ctx")
  def testCreateModelRaisesBadRequestForEmptyRequest(self, webMock,
                                                     loggerWebMock,
                                                     _engineMock):
    webMock.badrequest = web.badrequest
    loggerWebMock.env = {'HTTP_HOST':'localhost',
                         'SCRIPT_NAME':'',
                         'PATH_INFO':'/_models/test',
                         'HTTP_USER_AGENT':'test'}
    with self.assertRaises(web.badrequest) as e:
      models_api.ModelHandler.createModel()
    self.assertIsInstance(e.exception, InvalidRequestResponse)
    self.assertIn("Metric data is missing", e.exception.data)


  @patch("YOMP.app.quota.repository")
  @patch("YOMP.app.webservices.models_api.repository")
  @patch("web.ctx")
  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  def testCreateModels(self, # pylint: disable=W0613
                       createDatasourceAdapterMock,
                       ctxMock,
                       repositoryMock,
                       quotaRepositoryMock,
                       _engineMock):
    nativeMetric = {
        "region": "us-west-2",
        "namespace": "AWS/EC2",
        "datasource": "cloudwatch",
        "metric": "CPUUtilization",
        "dimensions": {
          "InstanceId": "i-ab15a19d"
        }
      }

    metricSpec = {
        "region": nativeMetric["region"],
        "namespace": nativeMetric["namespace"],
        "metric": nativeMetric["metric"],
        "dimensions": nativeMetric["dimensions"]
      }

    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    (createDatasourceAdapterMock
     .return_value
     .getInstanceNameForModelSpec
     .return_value) = metricAdapter.getCanonicalResourceName()

    quotaRepositoryMock.getInstanceCount.return_value = 0

    result = models_api.ModelHandler.createModels([nativeMetric])
    self.assertIsInstance(result, list)
    self.assertIs(result[0], repositoryMock.getMetric.return_value)
    repositoryMock.getMetric.assert_called_once_with(
      ctxMock.connFactory.return_value.__enter__.return_value,
      createDatasourceAdapterMock.return_value.monitorMetric.return_value)


  @patch("web.webapi.ctx")
  @patch("YOMP.app.webservices.web.ctx")
  def testCreateModelsRaisesBadRequestForEmptyRequest(self, webMock,
                                                      loggerWebMock,
                                                      _engineMock):
    webMock.data.return_value = None
    webMock.badrequest = web.badrequest
    loggerWebMock.env = {'HTTP_HOST':'localhost',
                         'SCRIPT_NAME':'',
                         'PATH_INFO':'/_models/test',
                         'HTTP_USER_AGENT':'test'}
    with self.assertRaises(web.badrequest) as e:
      models_api.ModelHandler.createModels()
    self.assertEqual(e.exception.data, "Metric data is missing")


@patch.object(repository, "engineFactory", autospec=True)
class TestMetricDataHandler(unittest.TestCase):


  @classmethod
  def setUpClass(cls):
    cls.metric_data = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/models_data.json")))
    cls.rowTuple = namedtuple("rowTuple", "uid, timestamp, metric_value,"
                                          " anomaly_score, rowid")

  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(models_api.app.wsgifunc())

  def decodeRowTuples(self, dataRows):
    rowTuples = [self.rowTuple(
      row[0], # uid
      datetime.datetime(*time.strptime(row[1],
                                       "%Y-%m-%d %H:%M:%S")[0:6]), #timestamp
      row[2], #metric_value
      row[3], #anomaly_score
      row[4] #rowid
    ) for row in dataRows]
    return rowTuples

  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMetricData(self,
                                         getMetricDataMock,
                                         _engineMock):

    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data["datalist"])
    response = self.app.get("/be9fab-f416-4845-8dab-02d292244112/data",
     headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual([row[1:] for row in self.metric_data["datalist"]],
     result["data"])


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMultiMetricData(self,
                                              getMetricDataMock,
                                              _engineMock):
    getMetricDataMock.return_value = []
    response = self.app.get("/data", headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    getMetricDataMock.assert_called_once_with(
      _engineMock.return_value.connect.return_value.__enter__.return_value,
      metricId=None,
      fields=ANY,
      fromTimestamp=ANY,
      toTimestamp=ANY,
      score=ANY,
      sort=ANY)


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMetricDataWithFromTimestamp(self,
                                                          getMetricDataMock,
                                                          _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data['withfrom'])
    response = self.app.get(
      "/be9fab-f416-4845-8dab-02d292244112/data?to=2013-08-15 21:28:00",
       headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual([row[1:] for row in self.metric_data["withfrom"]],
     result["data"])


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMultiMetricDataWithFromTimestamp(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = []
    response = self.app.get("/data?from=2013-08-15 21:30:00",
     headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    getMetricDataMock.assert_called_once_with(
      _engineMock.return_value.connect.return_value.__enter__.return_value,
      metricId=None,
      fields=ANY,
      fromTimestamp="2013-08-15 21:30:00",
      toTimestamp=ANY,
      score=ANY,
      sort=ANY)


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMetricDataWithToTimestamp(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data["withto"])
    response = self.app.get(
      "/be9fab-f416-4845-8dab-02d292244112/data?to=2013-08-15 21:28:00",
       headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual([row[1:] for row in self.metric_data['withto']],
     result["data"])


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMultiMetricDataWithToTimestamp(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data["withto"])
    response = self.app.get("/data?to=2013-08-15 21:28:00",
     headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    getMetricDataMock.assert_called_once_with(
      _engineMock.return_value.connect.return_value.__enter__.return_value,
      metricId=None,
      fields=ANY,
      fromTimestamp=ANY,
      toTimestamp="2013-08-15 21:28:00",
      score=ANY,
      sort=ANY)


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMetricDataWIthAnomaly(self,
                                                    getMetricDataMock,
                                                    _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data['withanomaly'])
    response = self.app.get(
      "/be9fab-f416-4845-8dab-02d292244112/data?anomaly=0.01",
       headers=self.headers)
    assertions.assertSuccess(self, response)
    result = jsonDecode(response.body)
    self.assertEqual([row[1:] for row in self.metric_data['withanomaly']],
     result["data"])


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMultiMetricDataWithAnomaly(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = []
    response = self.app.get("/data?anomaly=0.01", headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    getMetricDataMock.assert_called_once_with(
      _engineMock.return_value.connect.return_value.__enter__.return_value,
      metricId=None,
      fields=ANY,
      fromTimestamp=ANY,
      toTimestamp=ANY,
      score=0.01,
      sort=ANY)


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMetricDataWithToFromAnomaly(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data['withanomaly'])
    response = self.app.get(
      "/be9fab-f416-4845-8dab-02d292244112/data?from=2013-08-15 21:34:00&" \
      "to=2013-08-15 21:24:00&anomaly=0.025", headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    result = json.loads(response.body)
    self.assertEqual([row[1:] for row in self.metric_data['withanomaly']],
     result["data"])


  @patch.object(repository, "getMetricData", autospec=True)
  def testMetricDataHandlerGetMultiMetricDataWithToFromAnomaly(self,
      getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = []
    response = self.app.get("/data?from=2013-08-15 21:34:00&"
                            "to=2013-08-15 21:24:00&anomaly=0.025",
                            headers=self.headers)
    assertions.assertResponseStatusCode(self, response, 200)
    getMetricDataMock.assert_called_once_with(
      _engineMock.return_value.connect.return_value.__enter__.return_value,
      metricId=None,
      fields=ANY,
      fromTimestamp="2013-08-15 21:34:00",
      toTimestamp="2013-08-15 21:24:00",
      score=0.025,
      sort=ANY)


  @patch("YOMP.app.webservices.models_api.repository.getMetricData")
  def testQuery(self, getMetricDataMock, _engineMock):
    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data["datalist"])

    response = self.app.get("/be9fab-f416-4845-8dab-02d292244112/data?\
      from=2013-08-15 21:34:00&to=2013-08-15 21:24:00&anomaly=0.025",
       headers=self.headers)
    assertions.assertSuccess(self, response)


  @patch("YOMP.app.webservices.models_api.repository.getMetricData")
  def testQueryMultiMetric(self, getMetricDataMock, _engineMock):
    response = self.app.get('/data?from=2013-08-15 21:34:00&' \
      'to=2013-08-15 21:24:00&anomaly=0.025', headers=self.headers)
    result = json.loads(response.body)
    self.assertIn("metrics", result)
    self.assertIn("names", result)


  @patch("YOMP.app.webservices.models_api.repository.getMetricData")
  def testQueryMultiMetricAsBinaryStream(self, getMetricDataMock, _engineMock):
    self.headers["Accept"] = "application/octet-stream"

    getMetricDataMock.return_value = self.decodeRowTuples(
      self.metric_data["datalist"])

    response = self.app.get("/data?from=2013-08-15 21:34:00&" \
      "to=2013-08-15 21:24:00&anomaly=0.025", headers=self.headers)

    unpacker = msgpack.Unpacker(StringIO.StringIO(response.body))

    names = next(unpacker)
    self.assertEqual(names, ["names", "uid", "timestamp", "value",
      "anomaly_score", "rowid"])



@patch.object(repository, "engineFactory", autospec=True)
class TestModelExportHandler(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.app = TestApp(models_api.app.wsgifunc())


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  @patch.object(repository, "getMetric", autospec=True)
  def testModelExportHandlerGETMetric(self, getMetricMock,
                                      createDatasourceAdapterMock,
                                      _engineMock):

    metric = Mock(
      uid=u'5f76ba824fe147c8a4bc1c59565d8499',
      description=(
        u'CPUUtilization on EC2 instance i-ab15a19d in us-west-2 region'),
      server=u'i-ab15a19d',
      location=u'us-west-2',
      parameters=jsonEncode({
        "datasource": "cloudwatch",

        "metricSpec": {
          "region": "us-west-2",
          "namespace": "AWS/EC2",
          "metric": "CPUUtilization",
          "dimensions": {
            "InstanceId": "i-12d67826"
          }
        },

        "modelParams": {
          "min": 0,
          "max": 100
        }
      }),
      last_timestamp=datetime.datetime(2013, 11, 23, 18, 36),
      poll_interval=300L,
      status=MetricStatus.ACTIVE,
      message=None,
      collector_error=None,
      tag_name=u'jenkins-master',
      last_rowid=1440L,
      datasource="cloudwatch")
    metric.name = u'AWS/EC2/CPUUtilization'


    getMetricMock.return_value = metric
    createDatasourceAdapterMock.return_value.exportModel.return_value = (
      metric.parameters)

    response = self.app.get("/5f76ba824fe147c8a4bc1c59565d8499/export",
      headers=self.headers)

    assertions.assertResponseStatusCode(self, response, 200)

    # Assert response matches expected behavior
    self.assertEqual(json.loads(response.body), [metric.parameters])


  @patch("YOMP.app.webservices.models_api.createDatasourceAdapter",
         autospec=True)
  @patch("YOMP.app.webservices.models_api.repository.getMetric")
  def testModelExportHandlerGETAutostack(self,
                                         getMetricMock,
                                         createDatasourceAdapterMock,
                                         _engineMock):
    metric = Mock(uid="1f76ba824fe147c8a4bc1c59565d8490",
                  datasource="cloudwatch",
                  description="CPUUtilization on EC2 instance i-ab15a19d in "
                              "us-west-2 region",
                  server="i-ab15a19d",
                  location="us-west-2",
                  parameters=app_utils.jsonEncode({"name": "test1",
                                                   "filters": {
                                                     "tag:Name": ["*d*"]
                                                   }}),
                  last_timestamp=datetime.datetime(2013, 11, 23, 18, 36),
                  poll_interval=300L,
                  status=1L,
                  message=None,
                  tag_name="jenkins-master",
                  model_params={},
                  last_rowid=1440L)
    metric.name = "AWS/EC2/CPUUtilization"

    getMetricMock.return_value = metric
    createDatasourceAdapterMock.return_value.exportModel.return_value = (
      metric.parameters)

    response = self.app.get("/1f76ba824fe147c8a4bc1c59565d8490/export",
      headers=self.headers)

    self.assertEqual(response.status, 200)

    self.assertEqual([metric.parameters],
                     json.loads(response.body))


class ModelsApiUnhappyTest(unittest.TestCase):
  """
  Unhappy tests for Cloudwatch API
  """


  def setUp(self):
    self.app = TestApp(models_api.app.wsgifunc())
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)


  @patch("YOMP.app.repository.engineFactory")
  def testNoAuthHeaders(self, engineFactoryMock): # pylint: disable=W0613
    """
    negative test for authentication guarded route.
    invoke get request without passing authentication headers
    response is validated for appropriate headers and body
    """
    response = self.app.get("", status="*")
    assertions.assertInvalidAuthenticationResponse(self, response)


  @patch("YOMP.app.repository.engineFactory")
  def testInvalidAuthHeaders(self, engineFactoryMock): # pylint: disable=W0613
    """
    negative test for authentication guarded route.
    invoke get request with invalid authentication headers
    response is validated for appropriate headers and body
    """
    invalidHeaders = getInvalidHTTPHeaders()
    response = self.app.get("", status="*", headers=invalidHeaders)
    assertions.assertInvalidAuthenticationResponse(self, response)



if __name__ == "__main__":
  unittest.main()
