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
""" This was once a service on its own.  It has since been broken up such that
the anomaly-scoring is handled by AnomalyService, and the MetricCollector and
AggregatorService instances send data to ModelSwapper directly, as opposed to
writing data to queue
"""
import itertools
import logging
import os
import time

from nta.utils.config import Config
from nta.utils.date_time_utils import epochFromNaiveUTCDatetime

from htmengine import htmengine_logging, repository
from htmengine.adapters.datasource import createDatasourceAdapter
from htmengine.exceptions import (MetricStatisticsNotReadyError,
                                  MetricStatusChangedError)
from htmengine.model_swapper.model_swapper_interface import ModelInputRow
from htmengine.repository import schema
from htmengine.repository.queries import MetricStatus
from htmengine.runtime import model_data_feeder
from htmengine.runtime.scalar_metric_utils import (
  MODEL_CREATION_RECORD_THRESHOLD)



config = Config("application.conf", os.environ.get("APPLICATION_CONFIG_PATH"))



class MetricStreamer(object):
  _TAIL_INPUT_TIMESTAMP_GC_INTERVAL_SEC = 7 * 24 * 60 * 60

  def __init__(self):
    super(MetricStreamer, self).__init__()

    # Make sure we have the latest version of configuration
    config.loadConfig()

    self._log = htmengine_logging.getExtendedLogger(self.__class__.__name__)

    self._profiling = (
      config.getboolean("debugging", "profiling") or
      self._log.isEnabledFor(logging.DEBUG))

    self._metricDataOutputChunkSize = config.getint(
      "metric_streamer", "chunk_size")

    # Cache of latest metric_data timestamps for each metric; used for filtering
    # out duplicate/re-delivered input metric data so it won't be saved again
    # in the metric_data table. Each key is a metric id and the corresponding
    # value is a datetime.datetime timestamp of the last metric_data stored by
    # us in metric_data table.
    self._tailInputMetricDataTimestamps = dict()
    # Last garbage-collection time; seconds since unix epoch (time.time())
    self._lastTailInputMetricDataTimestampsGCTime = 0


  def _scrubDataSamples(self, data, metricID, conn, lastDataRowID):
    """ Filter out metric data samples that are out of order or have duplicate
    timestamps.

    :param data: A sequence of data samples; each data sample is a pair:
                  (datetime.datetime, float)
    :param metricID: unique metric id
    :param sqlalchemy.engine.Connection conn: A sqlalchemy connection object
    :param lastDataRowID: last metric data row identifier for metric with given
      metric id

    :returns: a (possibly empty) sequence of metric data samples that passed
      the scrubbing.
    :rtype: sequence of pairs: (datetime.datetime, float)
    """
    passingSamples = []
    rejectedDataTimestamps = []
    prevSampleTimestamp = self._getTailMetricRowTimestamp(conn, metricID,
                                                          lastDataRowID)
    for sample in data:
      timestamp, metricValue = sample
      # Filter out those whose timestamp is not newer than previous sampale's
      if (prevSampleTimestamp is not None and timestamp < prevSampleTimestamp):
        # Reject it; this could be the result of an unordered sample feed or
        # concurrent feeds of samples for the same metric
        # TODO: unit-test
        rejectedDataTimestamps.append(timestamp)
        self._log.error(
          "Rejected input sample older than previous ts=%s (%s): "
          "metric=%s; rejectedTs=%s (%s); rejectedValue=%s",
          prevSampleTimestamp, epochFromNaiveUTCDatetime(prevSampleTimestamp),
          metricID, timestamp, epochFromNaiveUTCDatetime(timestamp),
          metricValue)
      elif timestamp == prevSampleTimestamp:
        # Reject it; this could be the result of guaranteed delivery via message
        # publish retry following transient connection loss with the message bus
        self._log.error(
          "Rejected input sample with duplicate ts=%s (%s): "
          "metric=%s; rejectedValue=%s",
          prevSampleTimestamp, epochFromNaiveUTCDatetime(prevSampleTimestamp),
          metricID, metricValue)
        rejectedDataTimestamps.append(timestamp)
      else:
        passingSamples.append(sample)
        prevSampleTimestamp = timestamp

    if rejectedDataTimestamps:
      # TODO: unit-test
      self._log.error("Rejected input rows: metric=%s; numRejected=%d; "
                      "rejectedRange=[%s..%s]",
                      metricID, len(rejectedDataTimestamps),
                      min(rejectedDataTimestamps), max(rejectedDataTimestamps))

    return passingSamples


  def _storeDataSamples(self, data, metricID, conn):
    """ Store the given metric data samples in metric_data table
    :param data: A sequence of data samples; each data sample is a pair:
                  (datetime.datetime, float)
    :param metricID: unique metric id
    :param sqlalchemy.engine.Connection conn: A sqlalchemy connection object

    :returns: a (possibly empty) tuple of ModelInputRow objects corresponding
        to the samples that were stored; ordered by rowid.
    :rtype: tuple of model_swapper_interface.ModelInputRow objects
    """

    if data:
      # repository.addMetricData expects samples as pairs of (value, timestamp)
      data = tuple((value, ts) for (ts, value) in data)

      # Save new metric data in metric table
      rows = repository.addMetricData(conn, metricID, data)

      # Update tail metric data timestamp cache for metrics stored by us
      self._tailInputMetricDataTimestamps[metricID] = rows[-1]["timestamp"]

      # Add newly-stored records to batch for sending to CLA model
      modelInputRows = tuple(
        ModelInputRow(rowID=row["rowid"], data=(timestamp, metricValue,))
        for (metricValue, timestamp), row
        in itertools.izip_longest(data, rows))
    else:
      modelInputRows = tuple()
      self._log.warning("_storeDataSamples called with empty data")

    return modelInputRows


  def _sendInputRowsToModel(self, inputRows, metricID, modelSwapper):
    """ Send input rows to CLA model for processing

    :param inputRows: sequence of model_swapper_interface.ModelInputRow objects
    """
    model_data_feeder.sendInputRowsToModel(
      modelId=metricID,
      inputRows=inputRows,
      batchSize=self._metricDataOutputChunkSize,
      modelSwapper=modelSwapper,
      logger=self._log,
      profiling=self._profiling)


  def _getTailMetricRowTimestamp(self, conn, metricID, lastDataRowID):
    """
    :param sqlalchemy.engine.Connection conn: A sqlalchemy connection object
    :param metricID: unique metric id
    :param lastDataRowID: last metric data row identifier for metric with given
      metric id

    :returns: timestamp of the last metric data row that *we* stored in
        metric_data table for the given metric id, or None if none have been
        stored
    :rtype: datetime.datetime or None

    TODO: unit-test
    """
    if (time.time() - self._lastTailInputMetricDataTimestampsGCTime >
        self._TAIL_INPUT_TIMESTAMP_GC_INTERVAL_SEC):
      # Garbage-collect our cache
      # TODO: unit-test
      self._tailInputMetricDataTimestamps.clear()
      self._lastTailInputMetricDataTimestampsGCTime = time.time()
      self._log.info("Garbage-collected tailInputMetricDataTimestamps cache")

    timestamp = None
    try:
      # First try to get it from cache
      timestamp = self._tailInputMetricDataTimestamps[metricID]
    except KeyError:
      # Not in cache, so try to load it from db
      rows = repository.getMetricData(conn,
                                      metricID,
                                      rowid=lastDataRowID)

      if rows.rowcount > 0 and rows.returns_rows:
        timestamp = next(iter(rows)).timestamp
        self._tailInputMetricDataTimestamps[metricID] = timestamp

    return timestamp


  def streamMetricData(self, data, metricID, modelSwapper):
    """ Store the data samples in metric_data table if needed, and stream the
    data samples to the model associated with the metric if the metric is
    monitored.

    If the metric is in PENDING_DATA state: if there are now enough data samples
    to start a model, start it and stream it the entire backlog of data samples;
    if there are still not enough data samples, suppress streaming of the data
    samples.

    :param data: A sequence of data samples; each data sample is a three-tuple:
                  (datetime.datetime, float, None)
                     OR
                  (datetime.datetime, float, rowid)
      The third item in each three-tuple is either None in all elements of the
      sequence or is a valid rowid in all elements of the sequence. If it's
      None, as is the case with metrics collected from AWS
      CloudWatch, the row is added to the metric_data table before sending it
      to the model. If rowid is not None, as is presently the case with HTM
      metrics, the data samples are assumed to be stored already.

    :param metricID: unique id of the HTM metric

    :param modelSwapper: ModelSwapper object for sending data to models
    :type modelSwapper: an instance of ModelSwapperInterface

    :raises: ObjectNotFoundError when the metric for the data doesn't exist
    """
    if not data:
      self._log.warn("Empty input metric data batch for metric=%s", metricID)
      return

    @repository.retryOnTransientErrors
    def storeDataWithRetries():
      """
      :returns: a three-tuple <modelInputRows, datasource, metricStatus>;
        modelInputRows: None if model was in state not suitable for streaming;
          otherwise a (possibly empty) tuple of ModelInputRow objects
          corresponding to the samples that were stored; ordered by rowid
      """
      with repository.engineFactory(config).connect() as conn:
        with conn.begin():
          # Syncrhonize with adapter's monitorMetric
          metricObj = repository.getMetricWithUpdateLock(
            conn,
            metricID,
            fields=[schema.metric.c.status,
                    schema.metric.c.last_rowid,
                    schema.metric.c.datasource])

          if (metricObj.status != MetricStatus.UNMONITORED and
              metricObj.status != MetricStatus.ACTIVE and
              metricObj.status != MetricStatus.PENDING_DATA and
              metricObj.status != MetricStatus.CREATE_PENDING):
            self._log.error("Can't stream: metric=%s has unexpected status=%s",
                            metricID, metricObj.status)
            modelInputRows = None
          else:
            # TODO: unit-test
            passingSamples = self._scrubDataSamples(data,
                                                    metricID,
                                                    conn,
                                                    metricObj.last_rowid)
            if passingSamples:
              modelInputRows = self._storeDataSamples(passingSamples, metricID,
                                                      conn)
            else:
              modelInputRows = tuple()

      return (modelInputRows, metricObj.datasource, metricObj.status)


    (modelInputRows,
     datasource,
     metricStatus) = storeDataWithRetries()

    if modelInputRows is None:
      # Metric was in state not suitable for streaming
      return

    if not modelInputRows:
      # TODO: unit-test
      # Nothing was added, so nothing further to do
      self._log.error("No records to stream to model=%s", metricID)
      return

    if metricStatus == MetricStatus.UNMONITORED:
      # Metric was not monitored during storage, so we're done
      #self._log.info("Status of metric=%s is UNMONITORED; not forwarding "
      #               "%d rows: rowids[%s..%s]; data=[%s..%s]",
      #               metricID, len(modelInputRows),
      #               modelInputRows[0].rowID, modelInputRows[-1].rowID,
      #               modelInputRows[0].data, modelInputRows[-1].data)
      return

    lastDataRowID = modelInputRows[-1].rowID

    # Check models that are waiting for activation upon sufficient data
    if metricStatus == MetricStatus.PENDING_DATA:
      if lastDataRowID >= MODEL_CREATION_RECORD_THRESHOLD:
        try:
          # Activate metric that is supported by Datasource Adapter
          createDatasourceAdapter(datasource).activateModel(metricID)
        except (MetricStatisticsNotReadyError,
                MetricStatusChangedError) as ex:
          # Perhaps the metric status changed in the meantime. We can just
          # ignore this and it will sort itself out if additional records come
          # in (e.g., HTM Metric).
          self._log.error("Couldn't start model=%s: %r", metricID, ex)
      return

    # Stream data if model is activated
    # TODO: unit-test
    if metricStatus in (MetricStatus.CREATE_PENDING, MetricStatus.ACTIVE):
      self._sendInputRowsToModel(
        inputRows=modelInputRows,
        metricID=metricID,
        modelSwapper=modelSwapper)

      self._log.debug("Streamed numRecords=%d to model=%s",
                      len(modelInputRows), metricID)
