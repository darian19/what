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
Runtime utilities for scalar metrics.

NOTE: this module is imported by metric_streamer_util and by datasource
  adapters, so it's best to avoid importing either from here in the interest of
  steering clear of circular import dependencies. metric_streamer_util and this
  module avoid circular dependencies by relying on the model_data_feeder module
  for sending input rows to models.
"""

import logging
import os
import sys
import time


from nupic.data import fieldmeta

from htmengine import repository
from htmengine.algorithms.modelSelection.clusterParams import (
    getScalarMetricWithTimeOfDayParams)
import htmengine.exceptions as app_exceptions
from htmengine.model_swapper import model_swapper_interface
import htmengine.model_swapper.utils as model_swapper_utils
from htmengine.repository import schema
from htmengine.repository.queries import MetricStatus
from htmengine.runtime import model_data_feeder
import htmengine.utils

from nta.utils.config import Config



config = Config("application.conf", os.environ.get("APPLICATION_CONFIG_PATH"))

# Minimum records needed before creating a model; assumes 24 hours worth of
# 5-minute data samples
MODEL_CREATION_RECORD_THRESHOLD = (60 / 5) * 24



def generateSwarmParams(stats):
  """ Generate parameters for creating a model

  :param stats: dict with "min" and "max"; values must be integer,float or None.

  :returns: if either minVal or maxVal is None, returns None; otherwise returns
    swarmParams object that is suitable for passing to startMonitoring and
    startModel
  """
  minVal = stats.get("min")
  maxVal = stats.get("max")
  minResolution = stats.get("minResolution")
  if minVal is None or maxVal is None:
    return None

  # Create possible swarm parameters based on metric data
  possibleModels = getScalarMetricWithTimeOfDayParams(
    metricData=[0],
    minVal=minVal,
    maxVal=maxVal,
    minResolution=minResolution)

  swarmParams = possibleModels[0]

  swarmParams["inputRecordSchema"] = (
    fieldmeta.FieldMetaInfo("c0", fieldmeta.FieldMetaType.datetime,
                            fieldmeta.FieldMetaSpecial.timestamp),
    fieldmeta.FieldMetaInfo("c1", fieldmeta.FieldMetaType.float,
                            fieldmeta.FieldMetaSpecial.none),
  )

  return swarmParams


def startMonitoring(conn, metricId, swarmParams, logger):
  """ Start monitoring an UNMONITORED metric.

  NOTE: typically called either inside a transaction and/or with locked tables

  Starts the CLA model if provided non-None swarmParams; otherwise defers model
  creation to a later time and places the metric in MetricStatus.PENDING_DATA
  state.

  :param conn: SQLAlchemy Connection object for executing SQL
  :type conn: sqlalchemy.engine.Connection

  :param metricId: unique identifier of the metric row

  :param swarmParams: swarmParams generated via
    scalar_metric_utils.generateSwarmParams() or None.

  :param logger: logger object

  :returns: True if model was started; False if not

  :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
    referenced metric uid doesn't exist

  :raises htmengine.exceptions.MetricStatusChangedError: if Metric status was
      changed by someone else (most likely another process) before this
      operation could complete
  """
  modelStarted = False

  startTime = time.time()

  metricObj = repository.getMetric(conn, metricId)

  assert metricObj.status == MetricStatus.UNMONITORED, (
    "startMonitoring: metric=%s is already monitored; status=%s" % (
      metricId, metricObj.status,))

  if swarmParams is not None:
    # We have swarmParams, so start the model
    modelStarted = _startModelHelper(conn=conn,
                                     metricObj=metricObj,
                                     swarmParams=swarmParams,
                                     logger=logger)
  else:
    # Put the metric into the PENDING_DATA state until enough data arrives for
    # stats
    refStatus = metricObj.status

    repository.setMetricStatus(conn,
                               metricId,
                               MetricStatus.PENDING_DATA,
                               refStatus=refStatus)
    # refresh
    metricStatus = repository.getMetric(conn,
                                        metricId,
                                        fields=[schema.metric.c.status]).status

    if metricStatus == MetricStatus.PENDING_DATA:
      logger.info("startMonitoring: promoted metric to model in PENDING_DATA; "
                  "metric=%s; duration=%.4fs",
                  metricId, time.time() - startTime)
    else:
      raise app_exceptions.MetricStatusChangedError(
        "startMonitoring: unable to promote metric=%s to model as "
        "PENDING_DATA; metric status morphed from %s to %s"
        % (metricId, refStatus, metricStatus,))

  return modelStarted


def startModel(metricId, swarmParams, logger):
  """ Start the model atomically/reliably and send data backlog, if any

  :param metricId: unique identifier of the metric row

  :param swarmParams: non-None swarmParams generated via
    scalar_metric_utils.generateSwarmParams().

  :param logger: logger object

  :returns: True if model was started; False if not

  :raises htmengine.exceptions.ObjectNotFoundError: if the metric doesn't exist;
      this may happen if it got deleted by another process in the meantime.

  :raises htmengine.exceptions.MetricStatusChangedError: if Metric status was
      changed by someone else (most likely another process) before this
      operation could complete
  """
  # Perform the start-model operation atomically/reliably

  @repository.retryOnTransientErrors
  def start():
    with repository.engineFactory(config).begin() as conn:
      metricObj = repository.getMetric(conn, metricId)
      modelStarted = (
        _startModelHelper(conn=conn,
                          metricObj=metricObj,
                          swarmParams=swarmParams,
                          logger=logger))
      if modelStarted:
        sendBacklogDataToModel(conn=conn,
                               metricId=metricId,
                               logger=logger)

      return modelStarted

  return start()



def sendBacklogDataToModel(conn, metricId, logger):
  """ Send backlog data to OPF/CLA model. Do not call this before starting the
  model.

  :param conn: SQLAlchemy Connection object for executing SQL
  :type conn: sqlalchemy.engine.Connection

  :param metricId: unique identifier of the metric row

  :param logger: logger object

  """
  backlogData = tuple(
    model_swapper_interface.ModelInputRow(
      rowID=md.rowid, data=(md.timestamp, md.metric_value,))
    for md in repository.getMetricData(
                conn,
                metricId,
                fields=[schema.metric_data.c.rowid,
                        schema.metric_data.c.timestamp,
                        schema.metric_data.c.metric_value]))

  if backlogData:
    with model_swapper_interface.ModelSwapperInterface() as modelSwapper:
      model_data_feeder.sendInputRowsToModel(
        modelId=metricId,
        inputRows=backlogData,
        batchSize=config.getint("metric_streamer", "chunk_size"),
        modelSwapper=modelSwapper,
        logger=logger,
        profiling=(config.getboolean("debugging", "profiling") or
                   logger.isEnabledFor(logging.DEBUG)))

  logger.info("sendBacklogDataToModel: sent %d backlog data rows to model=%s",
              len(backlogData), metricId)



def _startModelHelper(conn, metricObj, swarmParams, logger):
  """ Start the model

  :param conn: SQLAlchemy Connection object for executing SQL
  :type conn: sqlalchemy.engine.Connection

  :param metricObj: metric, freshly-loaded
  :type metricObj: sqlalchemy.engine.RowProxy (see repository.getMetric())

  :param swarmParams: non-None swarmParams generated via
    scalar_metric_utils.generateSwarmParams().

  :param logger: logger object

  :returns: True if model was started; False if not

  :raises htmengine.exceptions.ObjectNotFoundError: if the metric doesn't exist;
      this may happen if it got deleted by another process in the meantime.

  :raises htmengine.exceptions.MetricStatusChangedError: if Metric status was
      changed by someone else (most likely another process) before this
      operation could complete
  """
  if swarmParams is None:
    raise ValueError(
      "startModel: 'swarmParams' must be non-None: metric=%s"
      % (metricObj.uid,))

  if metricObj.status not in (MetricStatus.UNMONITORED,
                           MetricStatus.PENDING_DATA):
    if metricObj.status in (MetricStatus.CREATE_PENDING, MetricStatus.ACTIVE):
      return False

    logger.error("Unexpected metric status; metric=%r", metricObj)
    raise ValueError("startModel: unexpected metric status; metric=%r"
                     % (metricObj,))

  startTime = time.time()

  # Save swarm parameters and update metric status
  refStatus = metricObj.status
  repository.updateMetricColumnsForRefStatus(
    conn,
    metricObj.uid,
    refStatus,
    {"status": MetricStatus.CREATE_PENDING,
     "model_params": htmengine.utils.jsonEncode(swarmParams)})

  metricObj = repository.getMetric(conn,
                                   metricObj.uid,
                                   fields=[schema.metric.c.uid,
                                           schema.metric.c.status]) # refresh

  if metricObj.status != MetricStatus.CREATE_PENDING:
    raise app_exceptions.MetricStatusChangedError(
      "startModel: unable to start model=%s; "
      "metric status morphed from %s to %s"
      % (metricObj.uid, refStatus, metricObj.status,))

  # Request to create the CLA model
  try:
    model_swapper_utils.createHTMModel(metricObj.uid, swarmParams)
  except Exception:
    logger.exception("startModel: createHTMModel failed.")
    repository.setMetricStatus(conn,
                               metricObj.uid,
                               status=MetricStatus.ERROR,
                               message=repr(sys.exc_info()[1]))
    raise

  logger.info("startModel: started model=%r; duration=%.4fs",
              metricObj, time.time() - startTime)

  return True
