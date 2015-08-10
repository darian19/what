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

import itertools
import json
import logging
from collections import namedtuple
import math
from optparse import OptionParser
import os
import sys
import time
import zlib

from nta.utils import amqp
from nta.utils.date_time_utils import epochFromNaiveUTCDatetime
from nta.utils.message_bus_connector import MessageBusConnector
from nta.utils.message_bus_connector import MessageProperties

from htmengine.anomaly_likelihood_helper import AnomalyLikelihoodHelper
from htmengine import htmengineerrno
from htmengine.exceptions import (ObjectNotFoundError,
                                  MetricNotActiveError,
                                  MetricNotMonitoredError)
from htmengine import (raiseExceptionOnMissingRequiredApplicationConfigPath,
                       repository)
from htmengine.repository import retryOnTransientErrors, schema
from htmengine.repository.queries import MetricStatus
from htmengine.model_swapper.model_swapper_interface import (
  ModelCommandResult,
  ModelInferenceResult,
  ModelSwapperInterface)
from htmengine.htmengine_logging import (getExtendedLogger,
                                         getStandardLogPrefix,
                                         getMetricLogPrefix)

from nta.utils.logging_support_raw import LoggingSupport
from nta.utils.config import Config




config = raiseExceptionOnMissingRequiredApplicationConfigPath(Config)(
  "application.conf", os.environ["APPLICATION_CONFIG_PATH"])



_MODULE_NAME = "htmengine.anomaly"


# Sort order code ported from Android app
GREEN_BAR_FLOOR = 1000
YELLOW_BAR_FLOOR = GREEN_BAR_FLOOR * 1000
RED_BAR_FLOOR = YELLOW_BAR_FLOOR * 1000
PROBATION_FACTOR = 1.0 / RED_BAR_FLOOR
INACTIVE_BAR_FLOOR = -10000
LOG_1_MINUS_0_9999999999 = math.log(1.0 - 0.9999999999)



def _getLogger():
  return getExtendedLogger(_MODULE_NAME)



g_log = _getLogger()



class MutableMetricDataRow(object):
  __slots__ = ("anomaly_score", "display_value", "metric_value",
               "raw_anomaly_score", "rowid", "timestamp", "uid")

  def __init__(self, anomaly_score, display_value, metric_value,
               raw_anomaly_score, rowid, timestamp, uid):
    # Disable "Invalid attribute name" warnings here; these attrs need to match
    #  metric_data table column names
    # pylint: disable=C0103
    self.anomaly_score = anomaly_score
    self.display_value = display_value
    self.metric_value = metric_value
    self.raw_anomaly_score = raw_anomaly_score
    self.rowid = rowid
    self.timestamp = timestamp
    self.uid = uid


  def __repr__(self):
    return ("%s<uid=%s, rowid=%s, ts=%s, value=%s, raw=%s, anomlik=%s, "
            "display=%s>") % (
      self.__class__.__name__, self.uid, self.rowid, self.timestamp,
      self.metric_value, self.raw_anomaly_score, self.anomaly_score,
      self.display_value)



def _logScale(value):
  if value > 0.99999:
    return 1

  return math.log(1.0000000001 - value) / LOG_1_MINUS_0_9999999999



def rescaleForDisplay(value, active):
  """ Rescale data point for display.  When ranking instances by anomaly, we'll
  consider the sum of these rescaled values over multiple time periods (hour,
  day, week) to compute a rank for the metric.

  :param value: Data value
  :param active: Active status
  :returns: rescaled data point
  """
  if value == 0:
    return 0

  calculated = _logScale(abs(value))

  if calculated >= 0.50:
    calculated += RED_BAR_FLOOR
  elif calculated >= 0.40:
    calculated += YELLOW_BAR_FLOOR
  else:
    calculated += GREEN_BAR_FLOOR

  if not active:
    calculated *= PROBATION_FACTOR

  return calculated



class RejectedInferenceResultBatch(Exception):
  """ The given batch of inference results are rejected """
  pass



class AnomalyService(object):
  """ Anomaly Service for processing CLA model results, calculating Anomaly
  Likelihood scores, and updating the associated metric data records

  Records are processed in batches from
  ``ModelSwapperInterface().consumeResults()`` and the associated
  ``MetricData`` rows are updated with the results of applying
  ``AnomalyLikelihoodHelper().updateModelAnomalyScores()`` and finally the
  results are packaged up as as objects complient with
  ``model_inference_results_msg_schema.json`` and published to the model
  results exchange, as identified by the ``results_exchange_name``
  configuration directive from the ``metric_streamer`` section of
  ``config``.

  Other services may be subscribed to the model results fanout exchange for
  subsequent (and parallel) processing.  For example,
  ``htmengine.runtime.notification_service.NotificationService`` is one example
  of a use-case for that exchange.  Consumers must deserialize inbound messages
  with ``AnomalyService.deserializeModelResult()``.

  """

  def __init__(self):
    self._log = _getLogger()

    self._profiling = (
      config.getboolean("debugging", "profiling") or
      self._log.isEnabledFor(logging.DEBUG))

    self._modelResultsExchange = (
      config.get("metric_streamer", "results_exchange_name"))

    self._statisticsSampleSize = (
      config.getint("anomaly_likelihood", "statistics_sample_size"))

    self.likelihoodHelper = AnomalyLikelihoodHelper(self._log, config)


  def _processModelCommandResult(self, metricID, result):
    """
    Process a single model command result
    """
    engine = repository.engineFactory(config)

    # Check if deleting model
    if result.method == "deleteModel":
      self._log.info("Model=%s was deleted", metricID)
      return

    # Validate model ID
    try:
      # NOTE: use shared lock to prevent race condition with adapter's
      # monitorMetric, whereby adapter creates and/or activates a metric inside
      # a transaction, and we might get the defineModel command before the
      # metric row updates are committed
      with engine.connect() as conn:
        metricObj = repository.getMetricWithSharedLock(conn, metricID)
    except ObjectNotFoundError:
      # This may occur if the user deletes the model before the result was
      # delivered while there are result messages still on the message bus.
      self._log.warn("Received command result=%r for unknown model=%s "
                     "(model deleted?)", result, metricID)
      return

    if result.status != 0:
      self._log.error(result.errorMessage)
      if metricObj.status != MetricStatus.ERROR:
        self._log.error("Placing model=<%s> in ERROR state due to "
                        "commandResult=%s",
                        getMetricLogPrefix(metricObj),
                        result)
        with engine.connect() as conn:
          repository.setMetricStatus(conn, metricID, MetricStatus.ERROR,
                                     result.errorMessage)



      else:
        # NOTE: could be a race condition between app-layer and Model Swapper
        #   or a side-effect of the at-least-once delivery guarantee
        self._log.warn("Received command result=%r for metricID=%s of "
                       "metric=<%s> that was already in ERROR state",
                       result, metricID, getMetricLogPrefix(metricObj))
      return

    # Create Model
    if result.method == "defineModel":
      self._log.info("Model was created for <%s>" % (
                      getMetricLogPrefix(metricObj)))

      if metricObj.status == MetricStatus.CREATE_PENDING:
        with engine.connect() as conn:
          repository.setMetricStatus(conn, metricID, MetricStatus.ACTIVE)
      else:
        # NOTE: could be a race condition between app-layer and Model Swapper
        #   or a side-effect of the at-least-once delivery guarantee
        self._log.warn("Received command result=%r for model=%s of metric=<%s> "
                       "that was not in CREATE_PENDING state",
                       result, metricID, getMetricLogPrefix(metricObj))
      return

    self._log.error("Unexpected model result=%r", result)


  def _processModelInferenceResults(self, inferenceResults, metricID):
    """
    Process a batch of model inference results

    Store the updated MetricData and anomaly likelihood parameters in the
    database.

    A row's anomaly_score value will be set to and remain at 0 in the
    first self._statisticsMinSampleSize rows; once we get enough inference
    results to create an anomaly likelyhood model, anomaly_score will be
    computed on the subsequent rows.

    :param inferenceResults: a sequence of ModelInferenceResult instances in the
      processed order (ascending by timestamp)

    :param metricID: metric/model ID of the model that emitted the results

    :returns: None if the batch was rejected; otherwise a pair:
      (metric, metricDataRows)
        metric: Metric RowProxy instance corresponding to the given metricID
        metricDataRows: a sequence of MutableMetricDataRow instances
          corresponding to the updated metric_data rows.
      TODO: unit-test return value
    :rtype: None or tuple

    *NOTE:*
      the processing must be idempotent due to the "at least once" delivery
      semantics of the message bus

    *NOTE:*
      the performance goal is to minimize costly database access and avoid
      falling behind while processing model results, especially during the
      model's initial "catch-up" phase when large inference result batches are
      prevalent.
    """
    engine = repository.engineFactory(config)

    # Validate model ID
    try:
      with engine.connect() as conn:
        metricObj = repository.getMetric(conn, metricID)
    except ObjectNotFoundError:
      # Ignore inferences for unkonwn models. Typically, this is is the result
      # of a deleted model. Another scenario where this might occur is when a
      # developer resets db while there are result messages still on the
      # message bus. It would be an error if this were to occur in production
      # environment.
      self._log.warning("Received inference results for unknown model=%s; "
                        "(model deleted?)", metricID, exc_info=True)
      return None

    # Reject the results if model is in non-ACTIVE state (e.g., if HTM Metric
    # was unmonitored after the results were generated)
    if metricObj.status != MetricStatus.ACTIVE:
      self._log.warning("Received inference results for a non-ACTIVE "
                        "model=%s; metric=<%s>; (metric unmonitored?)",
                        metricID, getMetricLogPrefix(metricObj))
      return None

    # Load the MetricData instances corresponding to the results
    with engine.connect() as conn:
      metricDataRows = repository.getMetricData(conn,
                                                metricID,
                                                start=inferenceResults[0].rowID,
                                                stop=inferenceResults[-1].rowID)

    # metricDataRows must be mutable, as the data is massaged in
    # _scrubInferenceResultsAndInitMetricData()
    metricDataRows = list(metricDataRows)

    if not metricDataRows:
      self._log.error("Rejected inference result batch=[%s..%s] of model=%s "
                      "due to no matching metric_data rows",
                      inferenceResults[0].rowID, inferenceResults[-1].rowID,
                      metricID)
      return None

    try:
      self._scrubInferenceResultsAndInitMetricData(
        engine=engine,
        inferenceResults=inferenceResults,
        metricDataRows=metricDataRows,
        metricObj=metricObj)
    except RejectedInferenceResultBatch as e:
      # TODO: unit-test
      self._log.error(
        "Rejected inference result batch=[%s..%s] corresponding to "
        "rows=[%s..%s] of model=%s due to error=%r",
        inferenceResults[0].rowID, inferenceResults[-1].rowID,
        metricDataRows[0].rowid, metricDataRows[-1].rowid, metricID, e)
      return None

    # Update anomaly scores based on the new results
    anomalyLikelihoodParams = (
      self.likelihoodHelper.updateModelAnomalyScores(
                                                engine=engine,
                                                metricObj=metricObj,
                                                metricDataRows=metricDataRows))

    # Update metric data rows with rescaled display values
    # NOTE: doing this outside the updateColumns loop to avoid holding row locks
    #  any longer than necessary
    for metricData in metricDataRows:
      metricData.display_value = rescaleForDisplay(
        metricData.anomaly_score,
        active=(metricObj.status == MetricStatus.ACTIVE))

    # Update database once via transaction!
    startTime = time.time()
    try:
      @retryOnTransientErrors
      def runSQL(engine):
        with engine.begin() as conn:
          for metricData in metricDataRows:
            fields = {"raw_anomaly_score": metricData.raw_anomaly_score,
                      "anomaly_score": metricData.anomaly_score,
                      "display_value": metricData.display_value}
            repository.updateMetricDataColumns(conn, metricData, fields)

          self._updateAnomalyLikelihoodParams(
            conn,
            metricObj.uid,
            metricObj.model_params,
            anomalyLikelihoodParams)

      runSQL(engine)
    except (ObjectNotFoundError, MetricNotActiveError):
      self._log.warning("Rejected inference result batch=[%s..%s] of model=%s",
                        inferenceResults[0].rowID, inferenceResults[-1].rowID,
                        metricID, exc_info=True)
      return None

    self._log.debug("Updated HTM metric_data rows=[%s..%s] "
                    "of model=%s: duration=%ss",
                    metricDataRows[0].rowid, metricDataRows[-1].rowid,
                    metricID, time.time() - startTime)

    return (metricObj, metricDataRows,)


  @classmethod
  def _updateAnomalyLikelihoodParams(cls, conn, metricId, modelParamsJson,
                                     likelihoodParams):
    """Update and save anomaly_params with the given likelyhoodParams if the
       metric is ACTIVE.

    :param conn: Transactional SQLAlchemy connection object
    :type conn: sqlalchemy.engine.base.Connection
    :param metricId: Metric uid
    :param modelParamsJson: Model params JSON object (from model_params metric
      column)
    :param likelihoodParams: anomaly likelihood params dict

    :raises: htmengine.exceptions.MetricNotActiveError if metric's status is not
      MetricStatus.ACTIVE
    """
    lockedRow = repository.getMetricWithUpdateLock(
      conn,
      metricId,
      fields=[schema.metric.c.status])

    if lockedRow.status != MetricStatus.ACTIVE:
      raise MetricNotActiveError(
        "_updateAnomalyLikelihoodParams failed because metric=%s is not "
        "ACTIVE; status=%s" % (metricId, lockedRow.status,))

    modelParams = json.loads(modelParamsJson)
    modelParams["anomalyLikelihoodParams"] = likelihoodParams

    repository.updateMetricColumns(conn,
                                   metricId,
                                   {"model_params": json.dumps(modelParams)})


  @classmethod
  def _composeModelInferenceResultsMessage(cls, metricRow, dataRows):
    """ Create a message body for publishing from the result of
    _processModelInferenceResults

    :param metricRow: Metric instance corresponding to the given metricID
    :param dataRows: a sequence of MutableMetricDataRow instances
      corresponding to the updated metric_data rows.
    :returns: JSON-ifiable dict conforming to
      model_inference_results_msg_schema.json
    :rtype: dict
    """
    return dict(
      metric=dict(
        uid=metricRow.uid,
        name=metricRow.name,
        description=metricRow.description,
        resource=metricRow.server,
        location=metricRow.location,
        datasource=metricRow.datasource,
        spec=json.loads(metricRow.parameters)["metricSpec"]
      ),

      results=[
        dict(
          rowid=row.rowid,
          ts=epochFromNaiveUTCDatetime(row.timestamp),
          value=row.metric_value,
          rawAnomaly=row.raw_anomaly_score,
          anomaly=row.anomaly_score
        )
        for row in dataRows
      ]
    )


  @classmethod
  def _composeModelCommandResultMessage(cls, modelID, cmdResult):
    """ Compose message corresponding to the completion of a model command
    for publishing to downstream services.

    :param modelID: model identifier
    :param model_swapper_interface.ModelCommandResult cmdResult: model command
      result
    :returns: JSON-ifiable message contents object per
      model_command_result_amqp_message.json
    :rtype: dict
    :raises ObjectNotFoundError: when attempted to request additional info about
      a model that is not in the repository
    :raises MetricNotMonitoredError: when required info about a model is not
      available, because it's no longer monitored
    """
    commandResultMessage = dict(
      method=cmdResult.method,
      modelId=modelID,
      commandId=cmdResult.commandID,
      status=cmdResult.status,
      errorMessage=cmdResult.errorMessage,
    )

    if (cmdResult.method == "defineModel" and
        cmdResult.status == htmengineerrno.SUCCESS):
      # Add modelInfo for successfully-completed "defineModel" commands
      engine = repository.engineFactory(config)
      fields = [
        schema.metric.c.name,
        schema.metric.c.server,
        schema.metric.c.parameters
      ]
      try:
        with engine.connect() as conn:
          metricObj = repository.getMetric(
            conn,
            modelID,
            fields=fields)
      except ObjectNotFoundError:
        g_log.warning("_composeModelCommandResultMessage: method=%s; "
                      "model=%s not found", cmdResult.method, modelID)
        raise

      if not metricObj.parameters:
        g_log.warning("_composeModelCommandResultMessage: method=%s; "
                      "model=%s not monitored", cmdResult.method, modelID)
        raise MetricNotMonitoredError

      commandResultMessage["modelInfo"] = dict(
        metricName=metricObj.name,
        resource=metricObj.server,
        modelSpec=json.loads(metricObj.parameters))

    return commandResultMessage


  def _scrubInferenceResultsAndInitMetricData(self, engine, inferenceResults,
                                              metricDataRows, metricObj):
    """ Validate the given inferenceResults against metricDataRows, update
    corresponding MetricData instances by initializing their
    `raw_anomaly_score` property from results and the `anomaly_score` property
    with 0. Replace elements in metricDataRows with MutableMetricDataRow
    objects.

    *NOTE:* does NOT update the MetricData instances to the database (we do that
    once after we process the batch for efficiency)

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param inferenceResults: a sequence of ModelInferenceResult instances
      representing the inference result batch ordered by row id

    :param metricDataRows: a mutable list of MetricData instances with row ids
      in the range of inferenceResults[0].rowID to inferenceResults[-1].rowID

    :param metricObj: a Metric instance associated with the given
      inferenceResults

    :raises RejectedInferenceResultBatch: if the given result batch is rejected
    """

    for result, enumeratedMetricData in itertools.izip_longest(
                                          inferenceResults,
                                          enumerate(metricDataRows)):

      if enumeratedMetricData is None:
        raise RejectedInferenceResultBatch(
            "No MetricData row for inference result=%r of model=<%r>" % (
                result, metricObj))
      index, metricData = enumeratedMetricData

      if result is None:
        raise RejectedInferenceResultBatch(
          "Truncated inference result batch; no result for metric data row=%r "
          "of model=<%r>" % (metricData, metricObj))

      if metricData is None:
        raise RejectedInferenceResultBatch(
          "No MetricData row for inference result=%r of model=<%r>" %
          (result, metricObj))

      if result.rowID != metricData.rowid:
        raise RejectedInferenceResultBatch(
          "RowID mismatch between inference result=%r and ModelData row=%r of "
          "model=<%r>" % (result, metricData, metricObj))

      if metricData.raw_anomaly_score is not None:
        # Side-effect of at-least-once delivery guarantee?
        self._log.error(
          "Anomaly was already processed on data row=%s; new result=%r",
          metricData, result)

      # Validate the result
      if result.status != 0:
        self._log.error(result.errorMessage)
        if metricObj.status == MetricStatus.ERROR:
          raise RejectedInferenceResultBatch(
            "inferenceResult=%r failed and model=<%s> was in ERROR state" %
            (result, getMetricLogPrefix(metricObj)))
        else:
          self._log.error("Placing model=<%r> in ERROR state due to "
                          "inferenceResult=%r", metricObj, result)
          with engine.connect() as conn:
            repository.setMetricStatus(conn,
                                       metricObj.uid,
                                       MetricStatus.ERROR,
                                       result.errorMessage)
          raise RejectedInferenceResultBatch(
            "inferenceResult=%r failed and model=<%s> promoted to ERROR state" %
            (result, getMetricLogPrefix(metricObj)))

      #self._log.info("{TAG:ANOM.METRIC} metric=%s:%s:%s",
      #               metricObj.name,
      #               calendar.timegm(metricData.timestamp.timetuple()),
      #               metricData.metric_value)

      mutableMetricData = MutableMetricDataRow(**dict(metricData.items()))
      mutableMetricData.raw_anomaly_score = result.anomalyScore
      mutableMetricData.anomaly_score = 0
      metricDataRows[index] = mutableMetricData


  @staticmethod
  def _serializeModelResult(modelResults):
    """ Serializes a model result into a message suitable for delivery
        to RabbitMQ/AMQP model result exchange
    :param modelResults: a JSON-ifiable object
    """
    return zlib.compress(json.dumps(modelResults))


  @staticmethod
  def deserializeModelResult(payload):
    """ Deserialize model result batch """
    return json.loads(zlib.decompress(payload))


  def run(self):
    """
    Consumes pending results.  Once result batch arrives, it will be dispatched
    to the correct model command result handler.

    :see: `_processModelCommandResult` and `_processModelInferenceResults`
    """
    # Properties for publishing model command results on RabbitMQ exchange
    modelCommandResultProperties = MessageProperties(
        deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE,
        headers=dict(dataType="model-cmd-result"))

    # Properties for publishing model inference results on RabbitMQ exchange
    modelInferenceResultProperties = MessageProperties(
        deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE)

    # Declare an exchange for forwarding our results
    with amqp.synchronous_amqp_client.SynchronousAmqpClient(
        amqp.connection.getRabbitmqConnectionParameters()) as amqpClient:
      amqpClient.declareExchange(self._modelResultsExchange,
                                 exchangeType="fanout",
                                 durable=True)

    with ModelSwapperInterface() as modelSwapper, MessageBusConnector() as bus:
      with modelSwapper.consumeResults() as consumer:
        for batch in consumer:
          if self._profiling:
            batchStartTime = time.time()

          inferenceResults = []
          for result in batch.objects:
            try:
              if isinstance(result, ModelCommandResult):
                self._processModelCommandResult(batch.modelID, result)
                # Construct model command result message for consumption by
                # downstream processes
                try:
                  cmdResultMessage = self._composeModelCommandResultMessage(
                    modelID=batch.modelID,
                    cmdResult=result)
                except (ObjectNotFoundError, MetricNotMonitoredError):
                  pass
                else:
                  bus.publishExg(
                    exchange=self._modelResultsExchange,
                    routingKey="",
                    body=self._serializeModelResult(cmdResultMessage),
                    properties=modelCommandResultProperties)
              elif isinstance(result, ModelInferenceResult):
                inferenceResults.append(result)
              else:
                self._log.error("Unsupported ModelResult=%r", result)
            except ObjectNotFoundError:
              self._log.exception("Error processing result=%r "
                                  "from model=%s", result, batch.modelID)

          if inferenceResults:
            result = self._processModelInferenceResults(
              inferenceResults,
              metricID=batch.modelID)

            if result is not None:
              # Construct model results payload for consumption by
              # downstream processes
              metricRow, dataRows = result
              resultsMessage = self._composeModelInferenceResultsMessage(
                metricRow,
                dataRows)

              payload = self._serializeModelResult(resultsMessage)

              bus.publishExg(
                exchange=self._modelResultsExchange,
                routingKey="",
                body=payload,
                properties=modelInferenceResultProperties)

          batch.ack()

          if self._profiling:
            if inferenceResults:
              if result is not None:
                # pylint: disable=W0633
                metricRow, rows = result
                rowIdRange = (
                  "%s..%s" % (rows[0].rowid, rows[-1].rowid)
                  if len(rows) > 1
                  else str(rows[0].rowid))
                self._log.info(
                  "{TAG:ANOM.BATCH.INF.DONE} model=%s; "
                  "numItems=%d; rows=[%s]; tailRowTS=%s; duration=%.4fs; "
                  "ds=%s; name=%s",
                  batch.modelID, len(batch.objects),
                  rowIdRange, rows[-1].timestamp.isoformat() + "Z",
                  time.time() - batchStartTime, metricRow.datasource,
                  metricRow.name)
            else:
              self._log.info(
                "{TAG:ANOM.BATCH.CMD.DONE} model=%s; "
                "numItems=%d; duration=%.4fs", batch.modelID,
                len(batch.objects), time.time() - batchStartTime)

    self._log.info("Stopped processing model results")



def main(args):
  # Parse command line options
  helpString = (
    "Usage: %prog\n"
    "This script runs the HTM Anomaly service.")

  parser = OptionParser(helpString)

  (_options, args) = parser.parse_args(args)

  if len(args) > 0:
    parser.error("Didn't expect any positional args (%r)." % (args,))

  try:
    AnomalyService().run()
  except Exception:
    _getLogger().exception("Error in Anomaly Service run()")
    raise



if __name__ == "__main__":
  LoggingSupport.initService()

  logger = _getLogger()
  logger.setLogPrefix("%s, SERVICE=ANOMALY" % getStandardLogPrefix())


  try:
    logger.info("{TAG:ANOM.START} argv=%r", sys.argv)
    main(sys.argv[1:])
  except KeyboardInterrupt as e:
    logger.info("Terminated via %r", e, exc_info=True)
  except:
    logger.exception("{TAG:ANOM.STOP.ABORT}")
    raise

  logger.info("{TAG:ANOM.STOP.OK}")
