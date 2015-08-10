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
This module implements the YOMP Aggregator service that is responsible for
retrieving and aggregating metric data for autostacks.

NOTE: The first phase supports only AWS/EC2 Instances.
"""

from optparse import OptionParser
import sys
import time

from YOMP.app import repository
from YOMP.app.adapters.datasource.autostack.autostack_metric_adapter import (
  AutostackMetricAdapterBase)
from YOMP.app.exceptions import ObjectNotFoundError
from YOMP.app.runtime.aggregation import aggregate
from YOMP.app.runtime.aggregator_metric_collection import (
    EC2InstanceMetricGetter,
    AutostackMetricRequest)
from htmengine.runtime.metric_streamer_util import MetricStreamer

from htmengine.model_swapper.model_swapper_interface import (
  ModelSwapperInterface)

from YOMP import logging_support
from YOMP.YOMP_logging import (getExtendedLogger,
                               getStandardLogPrefix,
                               getMetricLogPrefix)




_MODULE_NAME = "YOMP.aggregator"



def _getLogger():
  return getExtendedLogger(_MODULE_NAME)



class AggregatorService(object):

  _NOTHING_READY_SLEEP_TIME_SEC = 0.5

  def __init__(self):
    # NOTE: the EC2InstanceMetricGetter instance and its process pool must be
    # created BEFORE this main (parent) process creates any global or
    # class-level shared resources that are also used by the pool workers (e.g.,
    # boto connections) that would have undersirable consequences when
    # replicated into and used by forked child processes (e.g., the same
    # connection socket file descriptor used by multiple processes).

    self._metricGetter = EC2InstanceMetricGetter()

    self._log = _getLogger()


    self.metricStreamer = MetricStreamer()

  def close(self):
    self._metricGetter.close()


  def run(self):
    with ModelSwapperInterface() as modelSwapper:
      engine = repository.engineFactory()
      while True:
        with engine.connect() as conn:
          pendingStacks = repository.retryOnTransientErrors(
            repository.getAutostackMetricsPendingDataCollection)(conn)

        if not pendingStacks:
          time.sleep(self._NOTHING_READY_SLEEP_TIME_SEC)
          continue

        # Build a sequence of autostack metric requests
        requests = []
        for autostack, metrics in pendingStacks:
          refBase = len(requests)
          requests.extend(
            AutostackMetricRequest(refID=refBase + i,
                                   autostack=autostack,
                                   metric=metric)
            for i, metric in enumerate(metrics))

        # Collect, aggregate, and stream metric data
        self._processAutostackMetricRequests(engine, requests, modelSwapper)


  def _processAutostackMetricRequests(self, engine, requests, modelSwapper):
    """ Execute autostack metric requests, aggregate and stream
    collected metric data

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine
    :param requests: sequence of AutostackMetricRequest objects
    :param modelSwapper: Model Swapper
    """
    # Start collecting requested metric data
    collectionIter = self._metricGetter.collectMetricData(requests)

    # Aggregate each collection and dispatch to app MetricStreamer
    for metricCollection in collectionIter:
      request = requests[metricCollection.refID]

      metricObj = request.metric
      data = None

      if metricCollection.slices:
        aggregationFn = getAggregationFn(metricObj)
        if aggregationFn:
          data = aggregate(metricCollection.slices,
                           aggregationFn=aggregationFn)
        else:
          data = aggregate(metricCollection.slices)

      try:
        with engine.connect() as conn:
          repository.retryOnTransientErrors(repository.setMetricLastTimestamp)(
            conn, metricObj.uid, metricCollection.nextMetricTime)
      except ObjectNotFoundError:
        self._log.warning("Processing autostack data collection results for "
                          "unknown model=%s (model deleted?)", metricObj.uid)
        continue

      if data:
        try:
          self.metricStreamer.streamMetricData(data,
                                               metricID=metricObj.uid,
                                               modelSwapper=modelSwapper)
        except ObjectNotFoundError:
          # We expect that the model exists but in the odd case that it has
          # already been deleted we don't want to crash the process.
          self._log.info("Metric not found when adding data. metric=%s" %
                         metricObj.uid)

        self._log.debug(
          "{TAG:APP.AGG.DATA.PUB} Published numItems=%d for metric=%s;"
          "timeRange=[%sZ-%sZ]; headTS=%sZ; tailTS=%sZ",
          len(data), getMetricLogPrefix(metricObj),
          metricCollection.timeRange.start.isoformat(),
          metricCollection.timeRange.end.isoformat(),
          data[0][0].isoformat(), data[-1][0].isoformat())

      else:
        self._log.info(
          "{TAG:APP.AGG.DATA.NONE} No data for metric=%s;"
          "timeRange=[%sZ-%sZ]", getMetricLogPrefix(metricObj),
          metricCollection.timeRange.start.isoformat(),
          metricCollection.timeRange.end.isoformat())


def getAggregationFn(metric):
  fn = None

  slaveDatasource = AutostackMetricAdapterBase.getMetricDatasource(metric)
  metricAdapter = AutostackMetricAdapterBase.getMetricAdapter(slaveDatasource)
  query = metricAdapter.getQueryParams(metric.name)

  if "statistics" in query and query["statistics"] == "Sum":
    fn = sum

  return fn


def main(args):
  # Parse command line options
  helpString = (
    "Usage: %prog\n"
    "This script runs the YOMP Aggregator service.")

  parser = OptionParser(helpString)

  (_options, args) = parser.parse_args(args)

  if len(args) > 0:
    parser.error("Didn't expect any positional args (%r)." % (args,))

  service = AggregatorService()
  try:
    service.run()
  finally:
    service.close()



if __name__ == "__main__":
  logging_support.LoggingSupport.initService()

  logger = _getLogger()
  logger.setLogPrefix('%s, SERVICE=AGGR' % getStandardLogPrefix())

  try:
    logger.info("{TAG:AGGR.START} argv=%r", sys.argv)
    main(sys.argv[1:])
  except KeyboardInterrupt as e:
    logger.info("Terminated via %r", e)
  except:
    logger.exception("{TAG:AGGR.STOP.ABORT}")
    raise

  logger.info("{TAG:AGGR.STOP.OK}")
