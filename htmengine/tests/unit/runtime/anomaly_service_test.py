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
Unit tests for htmengine.runtime.anomaly_service
"""

# Disable: Access to a protected member
# pylint: disable=W0212

# Disable: Method could be a function
# pylint: disable=R0201

from collections import namedtuple
import datetime
import json
import logging
import pkg_resources
import unittest

from mock import patch, MagicMock, Mock
import sqlalchemy
import validictory

from nta.utils.date_time_utils import epochFromNaiveUTCDatetime
from nta.utils.logging_support_raw import LoggingSupport

from htmengine import htmengineerrno
import htmengine.exceptions as app_exceptions
from htmengine.repository.queries import MetricStatus
from htmengine.runtime import anomaly_service
from htmengine.model_swapper import model_swapper_interface
from htmengine.model_swapper.model_swapper_interface import (
  ModelInferenceResult)


g_log = logging.getLogger(__name__)


MetricRowProxyMock = namedtuple(
  "MetricRowProxyMock",
  "uid datasource name description server location parameters")


def setUpModule():
  LoggingSupport.initTestApp()



@patch.object(anomaly_service, "repository", autospec=True)
class CommandResultTestCase(unittest.TestCase):
  """ Unit tests for handling command results """


  def testComposeModelCommandResultForDefine(self, repoMock, *_args):
    """ Make sure we can compose a model command result message for publishing
    "defineModel" on the AMQP exchange
    """
    class MetricRowSpec(object):
      status = MetricStatus.CREATE_PENDING
      name = "metric.name"
      server = "metric.server"
      parameters = json.dumps(dict(value1="one", value2=2))

    repoMock.getMetric.return_value = MetricRowSpec

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    msg = service._composeModelCommandResultMessage(modelID=modelID,
                                                    cmdResult=result)

    # Validate the message against its JSON schema
    schemaStream = pkg_resources.resource_stream(
      "htmengine.runtime.json_schema",
      "model_command_result_amqp_message.json")
    jsonSchema = json.load(schemaStream)

    validictory.validate(msg, jsonSchema)

    self.assertEqual(msg.pop("method"), result.method)
    self.assertEqual(msg.pop("modelId"), modelID)
    self.assertEqual(msg.pop("commandId"), result.commandID)
    self.assertEqual(msg.pop("status"), result.status)
    self.assertEqual(msg.pop("errorMessage"), result.errorMessage)

    modelInfo = msg.pop("modelInfo")
    self.assertEqual(modelInfo.pop("metricName"), MetricRowSpec.name)
    self.assertEqual(modelInfo.pop("resource"), MetricRowSpec.server)
    self.assertEqual(modelInfo.pop("modelSpec"),
                     json.loads(MetricRowSpec.parameters))
    self.assertFalse(modelInfo)

    self.assertFalse(msg)


  def testComposeModelCommandResultForDefineFail(self, repoMock, *_args):
    """ Make sure we can compose a model command result message for publishing
    a failed "defineModel" on the AMQP exchange
    """
    repoMock.getMetric.side_effect = Exception(
      "getMetric should not have been called here")

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=1,
      errorMessage="bad, bad, bad")

    msg = service._composeModelCommandResultMessage(modelID=modelID,
                                                    cmdResult=result)

    # Validate the message against its JSON schema
    schemaStream = pkg_resources.resource_stream(
      "htmengine.runtime.json_schema",
      "model_command_result_amqp_message.json")
    jsonSchema = json.load(schemaStream)

    validictory.validate(msg, jsonSchema)

    self.assertEqual(msg.pop("method"), result.method)
    self.assertEqual(msg.pop("modelId"), modelID)
    self.assertEqual(msg.pop("commandId"), result.commandID)
    self.assertEqual(msg.pop("status"), result.status)
    self.assertEqual(msg.pop("errorMessage"), result.errorMessage)

    self.assertFalse(msg)


  def testComposeModelCommandResultObjNotFound(self, repoMock, *_args):
    """ Make sure ObjectNotFoundError is raised when composing a model command
    result message for publishing "defineModel" and the metric is not found
    """
    repoMock.getMetric.side_effect = app_exceptions.ObjectNotFoundError(
      "getMetric should not have been called here")

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    with self.assertRaises(app_exceptions.ObjectNotFoundError):
      service._composeModelCommandResultMessage(modelID=modelID,
                                                cmdResult=result)


  def testComposeModelCommandResultNotMonitored(self, repoMock, *_args):
    """ Make sure MetricNotMonitoredError is raised when composing a model
    command result message for publishing "defineModel" and metric properties
    are not set
    """
    class MetricRowSpec(object):
      status = MetricStatus.UNMONITORED
      name = "metric.name"
      server = "metric.server"
      parameters = None

    repoMock.getMetric.return_value = MetricRowSpec

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    with self.assertRaises(app_exceptions.MetricNotMonitoredError):
      msg = service._composeModelCommandResultMessage(modelID=modelID,
                                                      cmdResult=result)



  def testComposeModelCommandResultForDelete(self, repoMock, *_args):
    """ Make sure we can compose a model command result message for publishing
    "deleteModel" on the AMQP exchange
    """
    repoMock.getMetric.side_effect = Exception(
      "getMetric should not have been called here")

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="deleteModel", status=0)

    msg = service._composeModelCommandResultMessage(modelID=modelID,
                                                    cmdResult=result)

    # Validate the message against its JSON schema
    schemaStream = pkg_resources.resource_stream(
      "htmengine.runtime.json_schema",
      "model_command_result_amqp_message.json")
    jsonSchema = json.load(schemaStream)

    validictory.validate(msg, jsonSchema)

    self.assertEqual(msg.pop("method"), result.method)
    self.assertEqual(msg.pop("modelId"), modelID)
    self.assertEqual(msg.pop("commandId"), result.commandID)
    self.assertEqual(msg.pop("status"), result.status)
    self.assertEqual(msg.pop("errorMessage"), result.errorMessage)

    self.assertFalse(msg)


  def testComposeModelCommandResultForDeleteFail(self, repoMock, *_args):
    """ Make sure we can compose a model command result message for publishing
    a failed "deleteModel" on the AMQP exchange
    """
    repoMock.getMetric.side_effect = Exception(
      "getMetric should not have been called here")

    service = anomaly_service.AnomalyService()

    modelID = "123456abcdef"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="deleteModel", status=1,
      errorMessage="bad, bad, bad")

    msg = service._composeModelCommandResultMessage(modelID=modelID,
                                                    cmdResult=result)

    # Validate the message against its JSON schema
    schemaStream = pkg_resources.resource_stream(
      "htmengine.runtime.json_schema",
      "model_command_result_amqp_message.json")
    jsonSchema = json.load(schemaStream)

    validictory.validate(msg, jsonSchema)

    self.assertEqual(msg.pop("method"), result.method)
    self.assertEqual(msg.pop("modelId"), modelID)
    self.assertEqual(msg.pop("commandId"), result.commandID)
    self.assertEqual(msg.pop("status"), result.status)
    self.assertEqual(msg.pop("errorMessage"), result.errorMessage)

    self.assertFalse(msg)


  def testProcessSuccessfulDefineModelCommandResultWhileInCreatePendingState(
      self, repoMock, *_args):
    """This is the normal processing path for "defineModel" result"""

    class MetricRowSpec(object):
      status = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.CREATE_PENDING)
    repoMock.getMetricWithSharedLock.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    metricID = "abc"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    runner._processModelCommandResult(metricID=metricID, result=result)

    repoMock.setMetricStatus.assert_called_with(
      (repoMock.engineFactory.return_value.connect.return_value.__enter__
       .return_value),
      metricID, MetricStatus.ACTIVE)


  def testProcessSuccessfulDefineModelCommandResultWhileInActiveState(
      self, repoMock, *_args):
    """This is the other normal processing path where "defineModel" result
    is re-delivered as the side-effect of at-least-once delivery guarantee
    """

    class MetricRowSpec(object):
      status = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ACTIVE)
    repoMock.getMetric.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    metricID = "abc"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    runner._processModelCommandResult(metricID=metricID, result=result)

    self.assertFalse(repoMock.setMetricStatus.called)


  def testProcessSuccessfulDefineModelCommandResultWhileInErrorState(
      self, repoMock, *_args):
    """Test the scenario where "defineModel" result is delivered after the
    Metric has already been placed in error state
    """

    class MetricRowSpec(object):
      status = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ERROR)
    repoMock.getMetric.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    metricID = "abc"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=0)

    runner._processModelCommandResult(metricID=metricID, result=result)

    self.assertFalse(repoMock.setMetricStatus.called)


  def testProcessFailedDefineModelCommandResultWhileInCreatePendingState(
      self, repoMock, *_args):
    """Test the scenario where a failed "defineModel" result is delivered while
    the Metric is in CREATE_PENDING state
    """

    class MetricRowSpec(object):
      status = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.CREATE_PENDING)
    repoMock.getMetric.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    metricID = "abc"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=htmengineerrno.ERR_INVALID_ARG,
      errorMessage="invalid arg")

    runner._processModelCommandResult(metricID=metricID, result=result)

    repoMock.setMetricStatus.assert_called_with(
      (repoMock.engineFactory.return_value.connect.return_value.__enter__
       .return_value),
      metricID, MetricStatus.ERROR,
      result.errorMessage)


  def testProcessFailedDefineModelCommandResultWhileInErrorState(
      self, repoMock, *_args):
    """Test the scenario where a failed "defineModel" result is delivered after
    the Metric has already been placed in ERROR state
    """

    class MetricRowSpec(object):
      status = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ERROR)
    repoMock.getMetricWithSharedLock.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    metricID = "abc"
    result = anomaly_service.ModelCommandResult(
      commandID="123", method="defineModel", status=htmengineerrno.ERR_INVALID_ARG,
      errorMessage="invalid arg")

    runner._processModelCommandResult(metricID=metricID, result=result)

    self.assertFalse(repoMock.setMetricStatus.called)


@patch("htmengine.runtime.anomaly_service.amqp", autospec=True)
@patch.object(anomaly_service, "MessageBusConnector", autospec=True)
@patch.object(anomaly_service, "ModelSwapperInterface", autospec=True)
@patch.object(anomaly_service, "repository", autospec=True)
class InferenceResultTestCase(unittest.TestCase):
  """ Unit tests for handling command results """

  def testRunWithModelInferenceResultBatch(self,
                                           _repositoryMock,
                                           ModelSwapperInterfaceMock,
                                           *_args):
    """ Test AnomalyService.run() cycle with a single model inference results
    batch
    """
    batch = model_swapper_interface._ConsumedResultBatch(
      modelID="abcdef",
      objects=[ModelInferenceResult(rowID=1, status=0, anomalyScore=0)],
      ack=Mock(spec_set=(lambda multiple: None))
    )

    consumeResultsReturnValueMock = MagicMock(
      __enter__=Mock(return_value=[batch])
    )

    (ModelSwapperInterfaceMock.return_value.__enter__.return_value
     .consumeResults.return_value) = consumeResultsReturnValueMock

    service = anomaly_service.AnomalyService()

    resource = "metric's resource"

    modelSpec = dict(
      datasource="custom",
      metricSpec=dict(
        metric="MY.METRIC.STOCK.VOLUME",
        resource=resource,
        userInfo=dict(
          displayName="Stock Volume"
        )
      )
    )

    metricRowProxyMock = MetricRowProxyMock(
      uid="abcdef",
      datasource="my-test-custom",
      name="MY.METRIC.STOCK.VOLUME",
      description="test metric",
      server=resource,
      location="metric's location",
      parameters=json.dumps(modelSpec)
    )

    tsDatetime1 = datetime.datetime(2015, 4, 17, 12, 3, 35)

    metricDataRow = anomaly_service.MutableMetricDataRow(
      uid="abcdef",
      rowid=1,
      metric_value=10.9,
      timestamp=tsDatetime1,
      raw_anomaly_score=0.1,
      anomaly_score=0,
      display_value=0
    )
    metricDataRows=[metricDataRow]
    with patch.object(service, "_processModelInferenceResults", autospec=True,
                      return_value=(metricRowProxyMock, metricDataRows)):
      service.run()
      service._processModelInferenceResults.assert_called_once_with(
        batch.objects,
        metricID=metricDataRow.uid)


  def testComposeModelInferenceResultsMessage(self, *_args):
    """ Validate AnomalyService._composeModelInferenceResultsMessage result
    """

    # Compose the message

    tsDatetime1 = datetime.datetime(2015, 4, 17, 12, 3, 35)

    inferenceResult1 = anomaly_service.MutableMetricDataRow(
      uid="abcdef",
      rowid=1,
      metric_value=10.9,
      timestamp=tsDatetime1,
      raw_anomaly_score=0.1,
      anomaly_score=0,
      display_value=0
    )

    tsDatetime2 = datetime.datetime(2015, 4, 17, 12, 8, 35)

    inferenceResult2 = anomaly_service.MutableMetricDataRow(
      uid="abcdef",
      rowid=2,
      metric_value=11.9,
      timestamp=tsDatetime2,
      raw_anomaly_score=0.5,
      anomaly_score=0.7,
      display_value=2
    )

    resource = "metric's resource"

    modelSpec = dict(
      datasource="custom",
      metricSpec=dict(
        metric="MY.METRIC.STOCK.VOLUME",
        resource=resource,
        userInfo=dict(
          displayName="Stock Volume"
        )
      )
    )

    metricRow = MetricRowProxyMock(
      uid="abcdef",
      datasource="my-test-custom",
      name="MY.METRIC.STOCK.VOLUME",
      description="test metric",
      server=resource,
      location="metric's location",
      parameters=json.dumps(modelSpec)
    )

    dataRows = [inferenceResult1, inferenceResult2]

    msg = anomaly_service.AnomalyService._composeModelInferenceResultsMessage(
      metricRow=metricRow,
      dataRows=dataRows)

    # Verify message against schema
    with pkg_resources.resource_stream(
        "htmengine.runtime.json_schema",
        "model_inference_results_msg_schema.json") as msgSchemaStream:
      validictory.validate(msg, json.load(msgSchemaStream))

    # Verify message properties

    metric = msg["metric"]
    self.assertEqual(metric["uid"], "abcdef")
    self.assertEqual(metric["datasource"], "my-test-custom")
    self.assertEqual(metric["name"], "MY.METRIC.STOCK.VOLUME")
    self.assertEqual(metric["description"], "test metric")
    self.assertEqual(metric["resource"], resource)
    self.assertEqual(metric["location"], metricRow.location)
    self.assertEqual(metric["spec"], modelSpec["metricSpec"])

    resultRows = msg["results"]
    self.assertEqual(len(resultRows), 2)

    def validateResultRow(resultRow, inputRow):
      self.assertEqual(resultRow["rowid"], inputRow.rowid)
      self.assertEqual(resultRow["ts"],
                       epochFromNaiveUTCDatetime(inputRow.timestamp))
      self.assertEqual(resultRow["value"], inputRow.metric_value)
      self.assertEqual(resultRow["rawAnomaly"], inputRow.raw_anomaly_score)
      self.assertEqual(resultRow["anomaly"], inputRow.anomaly_score)

    for resultRow, inputRow in zip(resultRows, dataRows):
      validateResultRow(resultRow, inputRow)

    # Make sure it can be serialized and deserialized
    serializedMsg = anomaly_service.AnomalyService._serializeModelResult(msg)
    print "json msg size:", len(json.dumps(msg)), "serialized msg size:", len(serializedMsg)
    print msg
    deserializedMsg = anomaly_service.AnomalyService.deserializeModelResult(
      serializedMsg)
    self.assertEqual(deserializedMsg, msg)


  def testRejectionOfInferenceResultsForInactiveMetric(
      self, repoMock, *_args):
    """Calling _processModelInferenceResults against a metric that is not in
    ACTIVE state should result in rejection of results
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.UNMONITORED,
        parameters=None)
    repoMock.getMetric.return_value = metricRowMock

    runner = anomaly_service.AnomalyService()

    self.assertIsNone(
      runner._processModelInferenceResults(inferenceResults=[metricRowMock],
                                           metricID="abc"))


  @patch("htmengine.anomaly_likelihood_helper.AnomalyLikelihoodHelper")
  def testProcessModelInferenceResultsHandlingOfRejectedInferenceResultBatch(
      self, AnomalyLikelihoodHelperMock, repoMock, *_args):
    """Make sure _processModelInferenceResults handles
    RejectedInferenceResultBatch from _scrubInferenceResultsAndInitMetricData
    without crashing
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ACTIVE,
        parameters=None)
    repoMock.getMetric.return_value = metricRowMock

    class MetricDataRowSpec(object):
      uid = None
      rowid = Mock()

    metricRowDataMock = Mock(
        spec_set=MetricDataRowSpec)
    repoMock.getMetricData.return_value = [metricRowDataMock]

    runner = anomaly_service.AnomalyService()
    ex = anomaly_service.RejectedInferenceResultBatch("blah")
    runner._scrubInferenceResultsAndInitMetricData = Mock(
      spec_set=runner._scrubInferenceResultsAndInitMetricData,
      side_effect=ex)

    runner._log.error = Mock(wraps=runner._log.error)
    self.assertIsNone(
      runner._processModelInferenceResults(
        inferenceResults=[Mock()], metricID=Mock()))

    self.assertTrue(runner._log.error.called)
    self.assertIn("Rejected inference result batch=",
                  runner._log.error.call_args[0][0])
    self.assertIs(runner._log.error.call_args[0][-1], ex)

    self.assertFalse(AnomalyLikelihoodHelperMock.called)


  def testProcessModelInferenceResultsWithMetricNotFoundOnEntry(
      self, repoMock, *_args):
    """Make sure _processModelInferenceResults handles
    ObjectNotFoundError from repository.getMetric() without crashing
    """
    repoMock.getMetric.side_effect = app_exceptions.ObjectNotFoundError(
      "Metric not found")

    runner = anomaly_service.AnomalyService()

    with patch.object(runner._log, "warning",
                      new=Mock(wraps=runner._log.warning)):
      self.assertIsNone(
        runner._processModelInferenceResults(inferenceResults=[Mock()],
                                             metricID="abc"))

      self.assertTrue(repoMock.getMetric.called)
      self.assertTrue(runner._log.warning.called)
      self.assertIn("Received inference results for unknown model=",
                    runner._log.warning.call_args[0][0])


  @patch("htmengine.runtime.anomaly_service.AnomalyService"
         "._updateAnomalyLikelihoodParams", autospec=True)
  def testMetricNotActiveErrorDuringAnomalyLikelihoodUpdate(
      self, updateAnomalyLikelihoodParamsMock, repoMock, *_args):
    """MetricNotActiveError raised during anomaly likelihood update
    should result in rejection of results
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.UNMONITORED,
        parameters=None)
    repoMock.getMetric.return_value = metricRowMock
    updateAnomalyLikelihoodParamsMock.side_effect = (
      app_exceptions.MetricNotActiveError("faking it"))

    runner = anomaly_service.AnomalyService()

    runner._scrubInferenceResultsAndInitMetricData = Mock(
      spec_set=runner._scrubInferenceResultsAndInitMetricData,
      return_value=None)

    runner.likelihoodHelper.updateModelAnomalyScores = Mock(
      spec_set=runner.likelihoodHelper.updateModelAnomalyScores,
      return_value=dict())

    self.assertIsNone(
      runner._processModelInferenceResults(inferenceResults=[metricRowMock],
                                           metricID="abc"))

    self.assertEqual(updateAnomalyLikelihoodParamsMock.call_count, 0)


  def testTruncatedInferenceResultsInScrubInferernceResults(
      self, *_args):
    """Calling _scrubInferenceResultsAndInitMetricData with fewer
    inferenceResults than metricDataRows should raise
    RejectedInferenceResultBatch
    """
    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.UNMONITORED,
        parameters=None)

    engineMock = Mock(spec_set=sqlalchemy.engine.Engine)

    runner = anomaly_service.AnomalyService()

    with self.assertRaises(anomaly_service.RejectedInferenceResultBatch) as cm:
      runner._scrubInferenceResultsAndInitMetricData(
          engine=engineMock, inferenceResults=[], metricDataRows=[Mock()],
          metricObj=metricRowMock)

    self.assertIn("Truncated inference result batch", cm.exception.args[0])


  def testTruncatedMetricDataRowsInScrubInferernceResults(
      self, *_args):
    """Calling _scrubInferenceResultsAndInitMetricData with fewer
    metricDataRows than inferenceResults should raise
    RejectedInferenceResultBatch
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.UNMONITORED,
        parameters=None)

    engineMock = Mock(spec_set=sqlalchemy.engine.Engine)

    runner = anomaly_service.AnomalyService()

    with self.assertRaises(anomaly_service.RejectedInferenceResultBatch) as cm:
      runner._scrubInferenceResultsAndInitMetricData(
          engine=engineMock, inferenceResults=[Mock()], metricDataRows=[],
          metricObj=metricRowMock)

    self.assertIn("No MetricData row for inference result",
                  cm.exception.args[0])


  def testRowIdMismatchInScrubInferernceResults(
      self, *_args):
    """Calling _scrubInferenceResultsAndInitMetricData with a rowID mismatch
    between an item in metricDataRows and inferenceResults should raise
    RejectedInferenceResultBatch
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ACTIVE,
        parameters=None)

    class MetricDataRowSpec(object):
      uid = None
      rowid = None
      metric_value = None
      timestamp = None

    metricRowDataMock = Mock(
        spec_set=MetricDataRowSpec,
        uid=0, rowid=0, timestamp=None, metric_value=0)

    engineMock = Mock(spec_set=sqlalchemy.engine.Engine)

    runner = anomaly_service.AnomalyService()

    with self.assertRaises(anomaly_service.RejectedInferenceResultBatch) as cm:
      runner._scrubInferenceResultsAndInitMetricData(
          engine=engineMock,
          inferenceResults=[ModelInferenceResult(rowID=1, status=0,
                                                 anomalyScore=0)],
          metricDataRows=[metricRowDataMock],
          metricObj=metricRowMock)

    self.assertIn("RowID mismatch between inference result",
                  cm.exception.args[0])


  def testErrorResultAndActiveModelInScrubInferernceResults(
      self, repoMock, *_args):
    """Calling _scrubInferenceResultsAndInitMetricData with a failed inference
    result and ACTIVE model should set the model to ERROR state and raise
    RejectedInferenceResultBatch.
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ACTIVE,
        parameters=None,
        uid=0)

    class MetricDataRowSpec(object):
      uid = None
      rowid = None
      metric_value = None
      timestamp = None
      raw_anomaly_score = None

    metricRowDataMock = Mock(
        spec_set=MetricDataRowSpec,
        uid=0, rowid=0, timestamp=None, metric_value=0, raw_anomaly_score=None)

    engineMock = Mock(spec_set=sqlalchemy.engine.Engine)

    cmMock = Mock()
    engineMock.connect.return_value = cmMock
    cmMock.__enter__ = cmMock
    cmMock.__exit__ = cmMock

    connMock = Mock(spec_set=sqlalchemy.engine.Connection)
    cmMock.return_value = connMock

    runner = anomaly_service.AnomalyService()

    with self.assertRaises(anomaly_service.RejectedInferenceResultBatch) as cm:
      runner._scrubInferenceResultsAndInitMetricData(
          engine=engineMock,
          inferenceResults=[ModelInferenceResult(rowID=0,
                                                 status=MetricStatus.ERROR,
                                                 errorMessage="bad inference")],
          metricDataRows=[metricRowDataMock],
          metricObj=metricRowMock)

    repoMock.setMetricStatus.assert_called_with(
        connMock, 0, MetricStatus.ERROR, "bad inference")
    self.assertIn("promoted to ERROR state", cm.exception.args[0])


  def testErrorResultAndErrorModelInScrubInferernceResults(
      self, *_args):
    """Calling _scrubInferenceResultsAndInitMetricData with a failed inference
    result and errored out model should raise RejectedInferenceResultBatch
    """

    class MetricRowSpec(object):
      uid = None
      status = None
      parameters = None
      server = None

    metricRowMock = Mock(
        spec_set=MetricRowSpec,
        status=MetricStatus.ERROR,
        parameters=None)

    class MetricDataRowSpec(object):
      uid = None
      rowid = None
      metric_value = None
      timestamp = None
      raw_anomaly_score = None

    metricRowDataMock = Mock(
        spec_set=MetricDataRowSpec,
        uid=0, rowid=0, timestamp=None, metric_value=0)

    runner = anomaly_service.AnomalyService()

    with self.assertRaises(anomaly_service.RejectedInferenceResultBatch) as cm:
      runner._scrubInferenceResultsAndInitMetricData(
        engine=Mock(),
        inferenceResults=[
          ModelInferenceResult(
            rowID=0, status=1, errorMessage="bad inference")],
        metricDataRows=[metricRowDataMock],
        metricObj=metricRowMock)

    self.assertIn("was in ERROR state", cm.exception.args[0])



class UpdateAnomalyLikelihoodParamsTestCase(unittest.TestCase):

  def testUpdateAnomalyLikelihoodParams(
      self, *_args):
    """ Test AnomalyService._updateAnomalyLikelihoodParams()
    """
    class MetricDataRowSpec(object):
      status = None

    repositoryWrap = Mock(wraps=anomaly_service.repository)

    conn = Mock(spec_set=sqlalchemy.engine.Connection)
    conn.execute.side_effect = [
      # for repository.getMetricWithUpdateLock:
      Mock(spec_set=sqlalchemy.engine.ResultProxy,
           first=Mock(
            spec_set=sqlalchemy.engine.ResultProxy.first,
            side_effect=[
              Mock(
                spec_set=MetricDataRowSpec,
                status=MetricStatus.ACTIVE)])),

      # for repository.updateMetricColumns:
      Mock(spec_set=sqlalchemy.engine.ResultProxy)
    ]

    with patch.object(anomaly_service, "repository", new=repositoryWrap):
      modelParams = json.dumps(dict())
      anomaly_service.AnomalyService._updateAnomalyLikelihoodParams(
        conn=conn,
        metricId="123abcde",
        modelParamsJson=modelParams,
        likelihoodParams="likelihood-state")

    self.assertTrue(repositoryWrap.getMetricWithUpdateLock.called)
    self.assertTrue(repositoryWrap.updateMetricColumns.called)

    _connArg, _metricIdArg, fieldsArg = (
      repositoryWrap.updateMetricColumns.call_args[0])
    self.assertEqual(
      fieldsArg,
      {"model_params":
        json.dumps({"anomalyLikelihoodParams": "likelihood-state"})})


if __name__ == '__main__':
  unittest.main()
