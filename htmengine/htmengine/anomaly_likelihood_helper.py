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

from nupic.algorithms import anomaly_likelihood as algorithms
from htmengine import repository
from htmengine.exceptions import MetricNotActiveError
from htmengine.htmengine_logging import getMetricLogPrefix
from htmengine.repository.queries import MetricStatus
from htmengine.utils import jsonDecode



NUM_SKIP_RECORDS = 288 # One day of records
                       # TODO: Maybe define NUM_SKIP_RECORDS in configuration
                       # instead?



class AnomalyLikelihoodHelper(object):
  """ Helper class for running AnomalyLikelihood calculations in
  htmengine.runtime.anomaly_service.AnomalyService.

  Usage::

    likelihoodHelper = AnomalyLikelihoodHelper(log, config)
    likelihoodHelper.updateModelAnomalyScores(engine=engine,
                                              metric=metric,
                                              metricDataRows=metricDataRows)
  """
  def __init__(self, log, config):
    """
    :param log: htmengine log
    :type log: logging.Logger
    :param config: htmengine config
    :type config: nta.utils.config.Config
    """
    # Make sure we have the latest version of configuration
    config.loadConfig()

    self._log = log

    self._minStatisticsRefreshInterval = (
      config.getint("anomaly_likelihood", "statistics_refresh_rate"))
    self._statisticsMinSampleSize = (
      config.getint("anomaly_likelihood", "statistics_min_sample_size"))
    self._statisticsSampleSize = (
      config.getint("anomaly_likelihood", "statistics_sample_size"))


  def _generateAnomalyParams(self, metricID, statsSampleCache,
                             defaultAnomalyParams):
    """
    Generate the model's anomaly likelihood parameters from the given sample
    cache.

    :param metricID: the metric ID
    :param statsSampleCache: a sequence of MetricData instances that
      comprise the cache of samples for the current inference result batch with
      valid raw_anomaly_score in the processed order (by rowid/timestamp). At
      least self._statisticsMinSampleSize samples are needed.
    :param defaultAnomalyParams: the default anomaly params value; if can't
      generate new ones (not enough samples in cache), this value will be
      returned verbatim

    :returns: new anomaly likelihood parameters; defaultAnomalyParams, if there
      are not enough samples in statsSampleCache.
    """
    if len(statsSampleCache) < self._statisticsMinSampleSize:
      # Not enough samples in cache
      # TODO: unit-test this
      self._log.error(
        "Not enough samples in cache to update anomaly params for model=%s: "
        "have=%d, which is less than min=%d; firstRowID=%s; lastRowID=%s.",
        metricID, len(statsSampleCache), self._statisticsMinSampleSize,
        statsSampleCache[0].rowid if statsSampleCache else None,
        statsSampleCache[-1].rowid if statsSampleCache else None)

      return defaultAnomalyParams

    # We have enough samples to generate anomaly params
    lastRowID = statsSampleCache[-1].rowid

    numSamples = min(len(statsSampleCache), self._statisticsSampleSize)

    # Create input sequence for algorithms
    samplesIter = itertools.islice(
      statsSampleCache,
      len(statsSampleCache) - numSamples,
      len(statsSampleCache))

    scores = tuple(
      (row.timestamp, row.metric_value, row.raw_anomaly_score,)
      for row in samplesIter)

    assert len(scores) >= self._statisticsMinSampleSize, (
      "_generateAnomalyParams: samples count=%d is smaller than min=%d; "
      "model=%s; lastRowID=%s") % (len(scores), self._statisticsMinSampleSize,
                                  metricID, lastRowID,)

    assert len(scores) <= self._statisticsSampleSize, (
      "_generateAnomalyParams: samples count=%d is larger than max=%d; "
      "model=%s; lastRowID=%s") % (len(scores), self._statisticsSampleSize,
                                   metricID, lastRowID,)

    # Calculate estimator parameters
    # We ignore statistics from the first day of data (288 records) since the
    # CLA is still learning. For simplicity, this logic continues to ignore the
    # first day of data even once the window starts sliding.
    _, _, params = algorithms.estimateAnomalyLikelihoods(
                      anomalyScores=scores,
                      skipRecords=NUM_SKIP_RECORDS)

    anomalyParams = {}
    anomalyParams["last_rowid_for_stats"] = lastRowID
    anomalyParams["params"] = params

    self._log.debug("Generated anomaly params for model=%s using "
                    "numRows=%d with rows=[%s..%s]",
                    metricID, numSamples,
                    statsSampleCache[-numSamples].rowid,
                    statsSampleCache[-1].rowid)

    return anomalyParams


  def _getStatisticsRefreshInterval(self, batchSize):
    """ Determine the interval for refreshing anomaly likelihood parameters.

    The strategy is to use larger refresh intervals in large batches, which are
    presumably older catch-up data, in order to speed up our processing.
    Config-based self._minStatisticsRefreshInterval serves as the baseline.

    :param batchSize: number of elements in the inference result batch being
      processed.

    :returns: an integer that indicates how many samples should be
      processed until the next refresh of anomaly likelihood parameters
    """
    return int(max(self._minStatisticsRefreshInterval, batchSize * 0.1))


  def _initAnomalyLikelihoodModel(self, engine, metricObj, metricDataRows):
    """ Create the anomaly likelihood model for the given Metric instance.
    Assumes that the metric doesn't have anomaly params yet.

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param metricObj: Metric instance with no anomaly likelihood params
    :param metricDataRows: a sequence of MetricData instances
      corresponding to the inference results batch in the processed order
      (ascending by rowid and timestamp) with updated raw_anomaly_score and
      zeroed out anomaly_score corresponding to the new model inference results,
      but not yet updated in the database. Will not alter this sequence.

    :returns: the tuple (anomalyParams, statsSampleCache, startRowIndex)
      anomalyParams: None, if there are too few samples; otherwise, the anomaly
        likelyhood objects as returned by algorithms.estimateAnomalyLikelihoods
      statsSampleCache: None, if there are too few samples; otherwise, a list of
        MetricData instances comprising of a concatenation of rows sourced
        from metric_data tail and topped off with necessary items from the
        given metricDataRows for a minimum of self._statisticsMinSampleSize and
        a maximum of self._statisticsSampleSize total items.
      startRowIndex: Index into the given metricDataRows where processing of
        anomaly scores is to start; if there are too few samples to generate
        the anomaly likelihood params, then startRowIndex will reference past
        the last item in the given metricDataRows sequence.
    """
    if metricObj.status != MetricStatus.ACTIVE:
      raise MetricNotActiveError(
        "getAnomalyLikelihoodParams failed because metric=%s is not ACTIVE; "
        "status=%s; resource=%s" % (metricObj.uid,
                                    metricObj.status,
                                    metricObj.server,))

    modelParams = jsonDecode(metricObj.model_params)
    anomalyParams = modelParams.get("anomalyLikelihoodParams", None)

    assert not anomalyParams, anomalyParams

    statsSampleCache = None

    # Index into metricDataRows where processing of anomaly scores is to start
    startRowIndex = 0

    with engine.connect() as conn:
      numProcessedRows = repository.getProcessedMetricDataCount(conn,
                                                                metricObj.uid)

    if numProcessedRows + len(metricDataRows) >= self._statisticsMinSampleSize:
      # We have enough samples to initialize the anomaly likelihood model
      # TODO: unit-test

      # Determine how many samples will be used from metricDataRows
      numToConsume = max(0, self._statisticsMinSampleSize - numProcessedRows)
      consumedSamples = metricDataRows[:numToConsume]
      startRowIndex += numToConsume

      # Create the anomaly likelihood model
      anomalyParams, statsSampleCache = self._refreshAnomalyParams(
        engine=engine,
        metricID=metricObj.uid,
        statsSampleCache=None,
        consumedSamples=consumedSamples,
        defaultAnomalyParams=anomalyParams)

      # If this assertion fails, it implies that the count retrieved by our
      # call to MetricData.count above is no longer correct
      assert anomalyParams

      self._log.info("Generated initial anomaly params for model=%s: "
                     "numSamples=%d; firstRowID=%s; lastRowID=%s; ",
                     metricObj.uid, len(statsSampleCache),
                     statsSampleCache[0].rowid,
                     statsSampleCache[-1].rowid)
    else:
      # Not enough raw scores yet to begin anomaly likelyhoods processing
      # TODO: unit-test
      startRowIndex = len(metricDataRows)

    return anomalyParams, statsSampleCache, startRowIndex


  def _refreshAnomalyParams(self, engine, metricID, statsSampleCache,
                            consumedSamples, defaultAnomalyParams):
    """ Refresh anomaly likelihood parameters from the tail of
    statsSampleCache and consumedSamples up to self._statisticsSampleSize.

    Update statsSampleCache, including initializing from metric_data table, if
    needed, and appending of consumedSamples content.

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine

    :param metricID: the metric ID
    :param statsSampleCache: A list of MetricData instances. None, if the
      cache hasn't been initialized yet as is the case when the anomaly
      likelihood model is being built for the first time for the model or are
      being refreshed for the first time within a given result batch, in which
      case it will be initialized as follows: up to the balance of
      self._statisticsSampleSize in excess of consumedSamples will be loaded
      from the metric_data table.
    :param consumedSamples: A sequence of samples that have been consumed by
      anomaly processing, but are not yet in statsSampleCache. They will be
      appended to statsSampleCache
    :param defaultAnomalyParams: the default anomaly params value; if can't
      generate new ones, this value will be returned in the result tuple

    :returns: the tuple (anomalyParams, statsSampleCache,)

      If statsSampleCache was None on entry, it will be initialized as follows:
      up to the balance of self._statisticsSampleSize in excess of
      consumedSamples metric data rows with non-null raw anomaly scores will be
      loaded from the metric_data table and consumedSamples will be appended to
      it. If statsSampleCache was not None on entry, then elements from
      consumedSamples will be appended to it. The returned statsSampleCache will
      be a list NOTE: it may be an empty list, if there was nothing to fill it
      with.

      If there are not enough total samples to satisfy
      self._statisticsMinSampleSize, then the given defaultAnomalyParams will be
      returned in the tuple.
    """
    # Update the samples cache

    if statsSampleCache is None:
      # The samples cache hasn't been initialized yet, so build it now;
      # this happens when the model is being built for the first time or when
      # anomaly params are being refreshed for the first time within an
      # inference result batch.
      # TODO: unit-test this
      tail = self._tailMetricDataWithRawAnomalyScoresIter(
        engine,
        metricID,
        max(0, self._statisticsSampleSize - len(consumedSamples)))

      statsSampleCache = list(itertools.chain(tail, consumedSamples))
    else:
      # TODO: unit-test this
      statsSampleCache.extend(consumedSamples)

    anomalyParams = self._generateAnomalyParams(
      metricID=metricID,
      statsSampleCache=statsSampleCache,
      defaultAnomalyParams=defaultAnomalyParams)

    return (anomalyParams, statsSampleCache,)


  @classmethod
  def _tailMetricDataWithRawAnomalyScoresIter(cls, engine, metricID, limit):
    """
    Fetch the tail of metric_data rows with non-null raw_anomaly_score
    for the given metric ID

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine
    :param metricID: the metric ID
    :param limit: max number of tail rows to fetch

    :returns: an iterable that yields up to `limit` MetricData tail
      instances with non-null raw_anomaly_score ordered by metric data timestamp
      in ascending order

    """
    if limit == 0:
      return tuple()

    with engine.connect() as conn:
      rows = repository.getMetricDataWithRawAnomalyScoresTail(conn,
                                                              metricID,
                                                              limit=limit)

    return reversed(rows)


  def updateModelAnomalyScores(self, engine, metricObj, metricDataRows):
    """
    Calculate the anomaly scores based on the anomaly likelihoods. Update
    anomaly scores in the given metricDataRows MetricData instances, and
    calculate new anomaly likelihood params for the model.

    :param engine: SQLAlchemy engine object
    :type engine: sqlalchemy.engine.Engine
    :param metricObj: the model's Metric instance
    :param metricDataRows: a sequence of MetricData instances in the
      processed order (ascending by timestamp) with updated raw_anomaly_score
      and zeroed out anomaly_score corresponding to the new model inference
      results, but not yet updated in the database. Will update their
      anomaly_score properties, as needed.

    :returns: new anomaly likelihood params for the model

    *NOTE:*
      the processing must be idempotent due to the "at least once" delivery
      semantics of the message bus

    *NOTE:*
      the performance goal is to minimize costly database access and avoid
      falling behind while processing model results, especially during the
      model's initial "catch-up" phase when large inference result batches are
      prevalent.
    """
    # When populated, a cached list of MetricData instances for updating
    # anomaly likelyhood params
    statsSampleCache = None

    # Index into metricDataRows where processing is to resume
    startRowIndex = 0

    statisticsRefreshInterval = self._getStatisticsRefreshInterval(
      batchSize=len(metricDataRows))

    if metricObj.status != MetricStatus.ACTIVE:
      raise MetricNotActiveError(
        "getAnomalyLikelihoodParams failed because metric=%s is not ACTIVE; "
        "status=%s; resource=%s" % (metricObj.uid,
                                    metricObj.status,
                                    metricObj.server,))

    modelParams = jsonDecode(metricObj.model_params)
    anomalyParams = modelParams.get("anomalyLikelihoodParams", None)
    if not anomalyParams:
      # We don't have a likelihood model yet. Create one if we have sufficient
      # records with raw anomaly scores
      (anomalyParams, statsSampleCache, startRowIndex) = (
        self._initAnomalyLikelihoodModel(engine=engine,
                                         metricObj=metricObj,
                                         metricDataRows=metricDataRows))

    # Do anomaly likelihood processing on the rest of the new samples
    # NOTE: this loop will be skipped if there are still not enough samples for
    #  creating the anomaly likelihood params
    while startRowIndex < len(metricDataRows):
      # Determine where to stop processing rows prior to next statistics refresh

      if (statsSampleCache is None or
          len(statsSampleCache) >= self._statisticsMinSampleSize):
        # We're here if:
        #   a. We haven't tried updating anomaly likelihood stats yet
        #                 OR
        #   b. We already updated anomaly likelyhood stats (we had sufficient
        #      samples for it)
        # TODO: unit-test
        endRowID = (anomalyParams["last_rowid_for_stats"] +
                    statisticsRefreshInterval)

        if endRowID < metricDataRows[startRowIndex].rowid:
          # We're here if:
          #   a. Statistics refresh interval is smaller than during last stats
          #      update; this is the typical/normal case when backlog catch-up
          #      is tapering off, and refresh interval is reduced for smaller
          #      batches. OR
          #   b. There is a gap of anomaly scores preceeding the start of the
          #      current chunk. OR
          #   c. Statistics config changed.
          # TODO: unit-test

          self._log.warning(
            "Anomaly run cutoff precedes samples (smaller stats "
            "refreshInterval or gap in anomaly scores or statistics config "
            "changed) : model=%s; rows=[%s..%s]",
            metricObj.uid, metricDataRows[startRowIndex].rowid, endRowID)

          if statsSampleCache is not None:
            # We already attempted to update anomaly likelihood params, so fix
            # up endRowID to make sure we make progress and don't get stuck in
            # an infinite loop
            endRowID = metricDataRows[startRowIndex].rowid
            self._log.warning(
              "Advanced anomaly run cutoff to make progress: "
              "model=%s; rows=[%s..%s]",
              metricObj.uid, metricDataRows[startRowIndex].rowid, endRowID)
      else:
        # During prior iteration, there were not enough samples in cache for
        # updating anomaly params

        # We extend the end row so that there will be enough samples
        # to avoid getting stuck in this rut in the current and following
        # iterations
        # TODO: unit-test this
        endRowID = metricDataRows[startRowIndex].rowid + (
          self._statisticsMinSampleSize - len(statsSampleCache) - 1)

      # Translate endRowID into metricDataRows limitIndex for current run
      if endRowID < metricDataRows[startRowIndex].rowid:
        # Cut-off precedes the remaining samples
        # Normally shouldn't be here (unless statistics config changed or there
        # is a gap in anomaly scores in metric_data table)
        # TODO: unit-test this

        # Set limit to bypass processing of samples for immediate refresh of
        # anomaly likelihood params
        limitIndex = startRowIndex
        self._log.warning(
          "Anomaly run cutoff precedes samples, so forcing refresh of anomaly "
          "likelihood params: modelInfo=<%s>; rows=[%s..%s]",
          getMetricLogPrefix(metricObj),
          metricDataRows[startRowIndex].rowid, endRowID)
      else:
        # Cutoff is either inside or after the remaining samples
        # TODO: unit-test this
        limitIndex = startRowIndex + min(
          len(metricDataRows) - startRowIndex,
          endRowID + 1 - metricDataRows[startRowIndex].rowid)

      # Process the next new sample run
      self._log.debug(
        "Starting anomaly run: model=%s; "
        "startRowIndex=%s; limitIndex=%s; rows=[%s..%s]; "
        "last_rowid_for_stats=%s; refreshInterval=%s; batchSize=%s",
        metricObj.uid,
        startRowIndex, limitIndex, metricDataRows[startRowIndex].rowid,
        endRowID, anomalyParams["last_rowid_for_stats"],
        statisticsRefreshInterval, len(metricDataRows))

      consumedSamples = []
      for md in itertools.islice(metricDataRows, startRowIndex, limitIndex):
        consumedSamples.append(md)

        (likelihood,), _, anomalyParams["params"] = (
          algorithms.updateAnomalyLikelihoods(
            ((md.timestamp, md.metric_value, md.raw_anomaly_score),),
            anomalyParams["params"]))

        # TODO: the float "cast" here seems redundant
        md.anomaly_score = float(1.0 - likelihood)

        # If anomaly score > 0.99 then we greedily update the statistics. 0.99
        # should not repeat too often, but to be safe we wait a few more
        # records before updating again, in order to avoid overloading the DB.
        #
        # TODO: the magic 0.99 and the magic 3 value below should either
        #  be constants or config settings. Where should they be defined?
        if (md.anomaly_score > 0.99 and
            (anomalyParams["last_rowid_for_stats"] + 3) < md.rowid):
          if statsSampleCache is None or (
              len(statsSampleCache) + len(consumedSamples) >=
              self._statisticsMinSampleSize):
            # TODO: unit-test this
            self._log.info("Forcing refresh of anomaly params for model=%s due "
                           "to exceeded anomaly_score threshold in sample=%r",
                           metricObj.uid, md)
            break

      if startRowIndex + len(consumedSamples) < len(metricDataRows) or (
          consumedSamples[-1].rowid >= endRowID):
        # We stopped before the end of new samples, including a bypass-run,
        # or stopped after processing the last item and need one final refresh
        # of anomaly params
        anomalyParams, statsSampleCache = self._refreshAnomalyParams(
          engine=engine,
          metricID=metricObj.uid,
          statsSampleCache=statsSampleCache,
          consumedSamples=consumedSamples,
          defaultAnomalyParams=anomalyParams)


      startRowIndex += len(consumedSamples)
    # <--- while

    return anomalyParams
