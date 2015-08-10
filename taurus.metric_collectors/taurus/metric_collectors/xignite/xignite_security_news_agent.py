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
This agent fetches headlines and releases from xignite for securities in
taurus.metric_collectors/conf/metrics.json and stores the results in
taurus_collectors database.
"""

import abc
import copy
from collections import defaultdict
from collections import namedtuple
import itertools
import json
import logging
import operator
import os
import socket
import time
from collections import deque
from datetime import datetime, timedelta
from functools import partial
import multiprocessing
from optparse import OptionParser
from StringIO import StringIO

import requests
import sqlalchemy as sql

from nta.utils import date_time_utils
from nta.utils.error_handling import logExceptions
from nta.utils.error_handling import retry

from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors import logging_support
from taurus.metric_collectors.collectorsdb import schema
from taurus.metric_collectors import config
from taurus.metric_collectors import logging_support
from taurus.metric_collectors import metric_utils
from taurus.metric_collectors.metric_utils import getAllMetricSecurities
from taurus.metric_collectors.metric_utils import getMetricsConfiguration
from taurus.metric_collectors.xignite import xignite_agent_utils


DEFAULT_AGGREGATION_INTERVAL_SEC = 5 * 60
DEFAULT_MAX_BACKFILL_DAYS = 0


# Minimum number of workers in the news-retrieval worker pool
_MIN_POOL_CONCURRENCY = 10


# XIgnite API credentials
_DEFAULT_API_TOKEN = os.environ.get("XIGNITE_API_TOKEN")



# Our tracker key in the emitted_sample_tracker table
_EMITTED_NEWS_VOLUME_SAMPLE_TRACKER_KEY = "xignite-security-news-volume"



# News volume metrics provider key to match against properties in metrics.json
_NEWS_VOLUME_METRIC_PROVIDER = "xignite-security-news"



NewsVolumeMetricSpec = namedtuple(
  "NewsVolumeMetricSpec", "metric symbol")



class SecurityNewsUnavailable(Exception):
  """ No data available for the given security at this time """
  pass



class SecurityNewsFetchError(Exception):
  """ Error fetching headlines/releases for a given security """
  pass



class MarketNewsDetailsUnavailable(Exception):
  """ No market news details available for the given URL at this time """
  pass



class MarketNewsDetailsFetchError(Exception):
  """ Error fetching Market News Details for an article """
  pass



# Initialize logging
g_log = logging.getLogger("xignite_security_news_agent")


# Retry decorator for specific errors
_RETRY_ON_REQUESTS_ERROR = retry(
  timeoutSec=10, initialRetryDelaySec=0.05, maxRetryDelaySec=1,
  retryExceptions=(
    # requests retries on DNS errors, but not on connection errors
    requests.exceptions.ConnectionError,
  ),
  logger=g_log
)



g_poolWorkerHttpSession = requests.Session()



def _loadNewsVolumeMetricSpecs():
  """ Load metric specs for our securities news volume provider

  :returns: a sequence of NewsVolumeMetricSpec objects
  """
  return tuple(
    NewsVolumeMetricSpec(metric=metricName,
                         symbol=resVal["symbol"])
    for resVal in getMetricsConfiguration().itervalues()
    for metricName, metricVal in resVal["metrics"].iteritems()
    if metricVal["provider"] == _NEWS_VOLUME_METRIC_PROVIDER)



@_RETRY_ON_REQUESTS_ERROR
def _httpGetWithRetries(session, url, params):
  """ Wrap requests.Session.get in necessary retries

  :params session: requests.Session instance with auth configured
  :param url: URL string
  :param params: params dict to pass to requests.Session.get

  :returns: requests.models.Response instance. see requests.Session.get for
    details
  """
  return session.get(url, params=params)



class _HistoricalNewsTaskBase(object):
  """ Args for a headlines or releases poll operation """


  __metaclass__ = abc.ABCMeta

  # Base URL for retrieving historical news; to be overridden by subclasses
  _BASE_NEWS_URL = None

  # Destination table reference for storage of task-specific news; e.g.,
  # schema.xigniteSecurityHeadline; to be overridden by subclasses
  _NEWS_SCHEMA = None

  # Common URL prefix for xignite xGlobalNews.json APIs
  _X_GLOBAL_NEWS_JSON_URL_PREFIX = (
    "http://globalnews.xignite.com/xGlobalNews.json/")

  # URL args template for historical headlines/releases
  _NEWS_URL_ARGS_TEMPLATE = {
    "IdentifierType": "Symbol",
    "Identifier": None,
    "StartDate": None,
    "EndDate": None,
    "_Token": None
  }

  # Date format in xignite API SecurityHeadlines object
  _XIGNITE_DATE_FMT = "%m/%d/%Y"


  # Base URL for xignite GetMarketNewsDetails
  _BASE_MARKET_NEWS_DETAILS_URL = (_X_GLOBAL_NEWS_JSON_URL_PREFIX +
                                   "GetMarketNewsDetails")


  def __init__(self, security, startDate, endDate, dryRun):
    """
    :param security: tuple(<security symbol>, <exchangeName>)
    :param startDate: datetime.date object representing UTC start date for the
      operation; inclusive
    :param endDate: datetime.date object representing UTC end date for the
      operation; inclusive
    """
    self.security = security
    self.startDate = startDate
    self.endDate = endDate
    self.dryRun = dryRun


  def __repr__(self):
    return "%s<security=%s, from=%s, to=%s>" % (
      self.__class__.__name__, self.security, self.startDate, self.endDate)


  def process(self, apiToken):
    """ Fetch the task's historical news results and store newly-discovered news
    articles. May be invoked via multiprocessing.Pool

    :param apiToken: XIgnite API token

    :returns: The count of newly-discovered news rows that were saved; None if
      news retrieval resulted in failure
    """
    g_log.debug("%r.process()", self)

    # Reuse http session to facilitate faster execution via connection reuse
    session = g_poolWorkerHttpSession

    tickerSymbol = self.security[0]

    # Fetch the task's historical news
    try:
      allNews = self._fetchHistoricalSecurityNews(session=session,
                                                  apiToken=apiToken)
    except SecurityNewsUnavailable:
      return 0
    except SecurityNewsFetchError:
      g_log.exception("task._query failed:")
      return None

    headlines = allNews["Headlines"]
    if not headlines:
      return 0

    discoveredAt = datetime.utcnow()

    # Determine which of the headlines are new
    existingHeadlineSet = set(
      (row.local_pub_date, row.source, row.url)
      for row in self._queryExistingSecurityNewsRows(
        table=self._NEWS_SCHEMA,
        symbol=tickerSymbol,
        startDate=self.startDate,
        endDate=self.endDate))

    newHeadlineRows = []
    for story in headlines:
      localPubDate = datetime.strptime(story["Date"],
                                       self._XIGNITE_DATE_FMT).date()
      if not (self.startDate <= localPubDate <= self.endDate):
        # I saw there a lot at time of this writing. Reported to xignite
        # as case 00016736
        g_log.debug("%s: localPubDate=%r outside task's range; story=%s",
                    self, localPubDate, story)
        continue

      source = story["Source"]
      url = story["Url"].strip()

      headlineKey = (localPubDate, source, url,)
      if headlineKey in existingHeadlineSet:
        continue

      tags = story["Tags"]

      row = dict(
        symbol=tickerSymbol,
        title=story["Title"],
        local_pub_date=localPubDate,
        utc_offset=story["UTCOffset"],
        discovered_at=discoveredAt,
        source=source,
        url=url,
        image_urls=json.dumps(story["Images"]),
        tags=json.dumps(
          sorted([{tag["TagType"]: tag["TagValues"]} for tag in tags])
          if tags is not None else None),
        proc_dur=allNews["Delay"]
      )

      newHeadlineRows.append(row)


    if not newHeadlineRows:
      return 0

    g_log.info("%s: Detected %d new articles (out of %d)",
               self, len(newHeadlineRows), len(headlines))

    # Fetch additional details for each new headline and update newHeadlineRows
    self._fetchAdditionalNewsDetails(newHeadlineRows, session, apiToken)

    return self._saveSecurityNews(headlineRows=newHeadlineRows,
                                  xigniteSecurity=allNews["Security"])


  def _fetchHistoricalSecurityNews(self, session, apiToken):
    """ Fetch task-specific security news (releases or headlines) for the
    options supplied via the task's constructor

    :param requests.Session session: session object for REST API requests
    :param apiToken: XIgnite API token

    :returns: result object from xignite globalnews historical API
    :rtype: xignite globalnews SecurityHeadlines as dict

    :raises SecurityNewsFetchError:
    :raises SecurityNewsUnavailable:
    """
    params = copy.deepcopy(self._NEWS_URL_ARGS_TEMPLATE)
    params.update({"Identifier": self.security[0],
                  "StartDate": self.startDate.strftime(self._XIGNITE_DATE_FMT),
                  "EndDate": self.endDate.strftime(self._XIGNITE_DATE_FMT),
                  "_Token": apiToken})

    response = _httpGetWithRetries(session, self._BASE_NEWS_URL, params=params)

    g_log.debug("%s._fetchHistoricalSecurityNews: httpStatusCode=%s, data=%s",
                self, response.status_code, response.text)

    if response.status_code != 200:
      msg = ("%s._fetchHistoricalSecurityNews: httpStatusCode=%s, data=%s" %
             (self, response.status_code, response.text,))
      g_log.error(msg)
      raise SecurityNewsFetchError(msg)

    news = json.loads(response.text)

    outcome = news["Outcome"]

    if outcome == "RequestError":
      # e.g., "No data available for this Symbol (NEE)"
      msg = ("%s._fetchHistoricalSecurityNews: outcome=%s, message=%s" %
             (self, outcome, news["Message"],))
      g_log.debug(msg)
      # Assume no data available for the security at this moment; treat as
      # success (NOTE: based on observation; xignite documentation is lacking at
      # time of writing)
      raise SecurityNewsUnavailable(msg)
    elif outcome != "Success":
      msg = ("%s._fetchHistoricalSecurityNews: outcome=%s, data=%s" %
             (self, outcome, news,))
      g_log.error(msg)
      raise SecurityNewsFetchError(msg)

    return news


  @classmethod
  @collectorsdb.retryOnTransientErrors
  def _queryExistingSecurityNewsRows(cls, table, symbol, startDate, endDate):
    """ Query the given headline or release table for rows matching the given
    ticker symbol within the given date range

    :param sqlalchemy.Table table: table to query
    :param symbol: symbol of the security (e.g., stock ticker symbol)
    :param datetime.date startDate: UTC start date for the operation; inclusive
    :param datetime.date endDate: UTC end date for the operation; inclusive
    :returns: (possibly empty) sequence of matching sqlalchemy.engine.RowProxy
      objects with the following fields: local_pub_date, url, source
    """
    sel = sql.select([table.c.local_pub_date, table.c.url, table.c.source]
      ).where(
          (table.c.local_pub_date >= startDate) &
          (table.c.local_pub_date <= endDate))

    return collectorsdb.engineFactory().execute(sel).fetchall()


  @classmethod
  def _fetchAdditionalNewsDetails(cls, headlineRows, session, apiToken):
    """ Fetch additional details for each new headline and update headlineRows

    Add the following fields to each elements of headlineRows:
        summary
        orig_pub_time
        orig_source
        details_proc_dur

    :param headlineRows: rows of field values for target security news table
      prepopulated from xignite SecurityHeadline (see our `process` method)
    :type headlineRows: sequence of dicts
    """
    for row in headlineRows:
      summary = None
      originalPubTime = None
      originalPubSource = None
      detailsProcDuration = None
      try:
        newsDetails = cls._fetchMarketNewsDetails(session, row["url"], apiToken)
      except MarketNewsDetailsUnavailable:
        pass
      except MarketNewsDetailsFetchError:
        pass
      else:
        originalPubTime = datetime.strptime(newsDetails["Time"].strip(),
                                            "%m/%d/%Y %I:%M:%S %p")
        if originalPubTime.date() <= row["local_pub_date"]:
          summary = newsDetails["Summary"]
          summary = summary.strip() if summary is not None else None
          originalPubSource = newsDetails["Source"].strip()
          detailsProcDuration = newsDetails["Delay"]
        else:
          # This is likely the case whereby the article at the URL has been
          # updated and the details represent a newer headline
          originalPubTime = None

      row["summary"] = summary
      row["orig_pub_time"] = originalPubTime
      row["orig_source"] = originalPubSource
      row["details_proc_dur"] = detailsProcDuration


  @classmethod
  def _fetchMarketNewsDetails(cls, session, url, apiToken):
    """ Fetch market news details for the given market news URL via Xignite
    GetMarketNewsDetails API

    :param session: requests.Session instance with auth configured.
    :param url: URL of a securities headline or release
    :param apiToken: XIgnite API token

    :returns: result object from xignite GetMarketNewsDetails API; None if not
      found
    :rtype: dict

    :raises MarketNewsDetailsUnavailable:
    :raises MarketNewsDetailsFetchError:
    """
    # Reference=http://www.cnbc.com/id/101433706&_fields=Outcome,Message,Delay,Headline,Time,Source,Url,Summary
    params = {
      "Reference": url,
      "_fields": "Outcome,Message,Delay,Headline,Time,Source,Url,Summary",
      "_Token": apiToken
    }

    response = _httpGetWithRetries(session, cls._BASE_MARKET_NEWS_DETAILS_URL,
                                   params=params)

    g_log.debug(
      "%s._fetchMarketNewsDetails: httpStatusCode=%s, data=%s for url=%s",
      cls.__name__, response.status_code, response.text, url)

    if response.status_code != 200:
      msg = (
        "%s._fetchMarketNewsDetails: httpStatusCode=%s, data=%s for url=%s" %
        (cls.__name__, response.status_code, response.text, url,))
      g_log.error(msg)
      raise MarketNewsDetailsFetchError(msg)

    newsItem = json.loads(response.text)

    outcome = newsItem["Outcome"]

    if outcome == "RequestError":
      # e.g., "No data available for this Symbol (NEE)"
      msg = ("%s._fetchMarketNewsDetails: outcome=%s, message=%s for url=%s" %
             (cls.__name__, outcome, newsItem["Message"], url,))
      g_log.warning(msg)
      # Assume no details available for the URL; treat as success
      # NOTE: based on observation; xignite documentation is lacking at
      # time of writing
      raise MarketNewsDetailsUnavailable(msg)
    elif outcome != "Success":
      msg = ("%s._fetchMarketNewsDetails: outcome=%s, data=%s for url=%s" %
             (cls.__name__, outcome, newsItem, url,))
      g_log.error(msg)
      raise MarketNewsDetailsFetchError(msg)

    return newsItem



  def _saveSecurityNews(self, headlineRows, xigniteSecurity):
    """ Store security news in the destination schema specified via
    _NEWS_SCHEMA member variable.

    :param headlineRows: rows of field values for target security news table
    :type headlineRows: sequence of dicts
    :param dict xigniteSecurity: Security info from xignite API results (e.g.,
      global security news, security bars, etc.)

    :returns: The count of new news rows that were saved; 0 if the news object
      has no headlines.
    """
    destSchema = self._NEWS_SCHEMA

    if not headlineRows:
      return 0

    if self.dryRun:
      g_log.info("%r.process(dryRun=True): security=%s, news=%s", self,
                 xigniteSecurity, headlineRows)
      return 0

    engine = collectorsdb.engineFactory()

    @collectorsdb.retryOnTransientErrors
    def saveNews():
      with engine.begin() as conn:
        # Save headlines
        newsIns = destSchema.insert().prefix_with("IGNORE", dialect="mysql")
        return conn.execute(newsIns, headlineRows).rowcount

    try:
      return saveNews()
    except sql.exc.IntegrityError:
      # Most likely foreign key constraint violation against the
      # xignite_security table
      g_log.info("Inserting security row for symbol=%s",
                 xigniteSecurity["Symbol"])
      xignite_agent_utils.insertSecurity(engine, xigniteSecurity)

      # Re-insert news after resolving IntegrityError
      return saveNews()
      



class _HistoricalHeadlinesTask(_HistoricalNewsTaskBase):
  """ Task for retrieving and storing historical security headlines """

  _BASE_NEWS_URL = (_HistoricalNewsTaskBase._X_GLOBAL_NEWS_JSON_URL_PREFIX +
                    "GetHistoricalSecurityHeadlines")

  _NEWS_SCHEMA = schema.xigniteSecurityHeadline



class _HistoricalReleasesTask(_HistoricalNewsTaskBase):
  """ Task for retrieving and storing historical security releases """

  _BASE_NEWS_URL = (_HistoricalNewsTaskBase._X_GLOBAL_NEWS_JSON_URL_PREFIX +
                    "GetHistoricalReleasesBySecurity")

  _NEWS_SCHEMA = schema.xigniteSecurityRelease



def _generateTasks(securities, lastSecurityEndDates, backfillDays, taskClass,
                   dryRun):
  """ Generates retrieval task for security headlines or releases

  :param securities: a sequence of (<security symbol>, <exchangeName>)
    two-tuples
  :param lastSecurityEndDates: a dict that maps a security symbol to the
    datetime.date of the most recent successfully-retrieved/stored batch of
    headlines or releases. Any of the mappings could be empty, in which case
    backfillDays will be used to generate the startDate for the new task.
  :param backfillDays: Max number of days for backfilling headlines or releases
    in case the mapping for a security is absent from lastSecurityEndDates
  :param taskClass: _HistoricalNewsTaskBase-based class of the tasks to
    instantiate

  :returns: a sequence of _Task objects
  """
  endDate = datetime.utcnow().date()

  tasks = []
  for security in securities:
    startDate = lastSecurityEndDates.get(security[0])
    if startDate is None:
      startDate = endDate - timedelta(days=backfillDays)

    # NOTE: there appears to be a bug in xignite historical headlines and
    # releases APIs, such that a request with a range that spans multiple days
    # only returns results for the last day (xignite support Case 00016061); we
    # work around this bug by generating a task for each day in the range.
    daysInRange = (endDate - startDate).days + 1
    for i in xrange(daysInRange):
      date = startDate + timedelta(days=i)
      tasks.append(
        taskClass(security=security, startDate=date, endDate=date,
                  dryRun=dryRun))

  return tasks



@logExceptions(g_log)
def _executeTask(task, apiToken):
  """ Execute the task's process method; called via multiprocessing.Pool

  :param task: a task to executed; instance derived from _HistoricalNewsTaskBase
  :param apiToken: XIgnite API token

  :returns: two-tuple (<task>,
                       <count of newly-discovered articles, None on error>)
  """
  return task, task.process(apiToken=apiToken)



def _querySecurityNewsEndDates(srcSchema):
  """ Build a map of security symbols to the dates of the most recently saved
  news in the given schema

  :param srcSchema: Source sqlalchemy schema from which to retrieve the info (
    schema.xigniteSecurityHeadline or schema.xigniteSecurityRelease)

  :returns: a dict that maps security symbols to the datetime.date of most
    recently-stored news for those securities
  """
  @collectorsdb.retryOnTransientErrors
  def queryEndDates():
    sel = sql.select(
      [srcSchema.c.symbol,
       sql.func.max(srcSchema.c.local_pub_date)]
      ).group_by(srcSchema.c.symbol)

    resultProxy = collectorsdb.engineFactory().execute(sel)

    endDateMap = dict(
      (row[0], row[1]) for row in resultProxy
    )

    g_log.debug("%s endDateMap=%s", srcSchema, endDateMap)

    return endDateMap

  return queryEndDates()



@collectorsdb.retryOnTransientErrors
def _queryNewsVolumes(aggStartDatetime, aggStopDatetime):
  """ Query the database for the counts of security releases+headlines for each
  company that were detected during the specified time window.

  :param aggStartDatetime: inclusive start of aggregation interval as
    UTC datetime
  :param aggStopDatetime: non-inclusive upper bound of aggregation interval as
    UTC datetime
  :returns: a sparse sequence of two-tuples: (symbol, count); companies that
    have no detected news in the given aggregation period will be absent from
    the result.
  """
  headlineSel = sql.select(
    [schema.xigniteSecurityHeadline.c.symbol.label("symbol")]
    ).where(
      (schema.xigniteSecurityHeadline.c.discovered_at >= aggStartDatetime) &
      (schema.xigniteSecurityHeadline.c.discovered_at < aggStopDatetime))

  releaseSel = sql.select(
    [schema.xigniteSecurityRelease.c.symbol]
    ).where(
      (schema.xigniteSecurityRelease.c.discovered_at >= aggStartDatetime) &
      (schema.xigniteSecurityRelease.c.discovered_at < aggStopDatetime))

  allNewsUnion = sql.union_all(headlineSel, releaseSel)

  aggSel = sql.select(
    ["symbol", sql.func.count("symbol").label("sym_count")]
    ).select_from(allNewsUnion.alias("union_of_tables")
    ).group_by("symbol")

  return collectorsdb.engineFactory().execute(aggSel).fetchall()



def _forwardNewsVolumeMetrics(metricSpecs,
                              lastEmittedAggTime,
                              stopDatetime,
                              periodSec,
                              metricDestAddr):
  """ Query news volume metrics since the given last emitted timestamp through
  stopDatetime and forward them to htmengine's Metric Listener. Update the
  datetime of the last successfully-emitted news volume metric batch in the
  database.

  NOTE: forwarding will be aborted upon failure to connect to Metic Listener. In
    this case, an error will be logged, and the function will return the UTC
    timestamp of the last successfully-emitted sample aggregation interval. Once
    Metric Listener comes online, a subsequent call to this function will catch
    up by forwarding the stored samples since last successful emission.

  :param metrics: a sequence of NewsVolumeMetricSpec objects corresponding to
    the metrics to be emitted
  :param lastEmittedAggTime: UTC datetime of last successfully-emitted sample
    batch
  :param stopDatetime: non-inclusive upper bound UTC datetime for forwarding
  :param periodSec: aggregation period in seconds
  :param metricDestAddr: two-tuple (metricDestHost, metricDestPort)
  :returns: UTC timestamp of the last successfully-emitted sample batch.
  :rtype: datetime.datetime
  """
  periodTimedelta = timedelta(seconds=periodSec)
  aggStartDatetime = lastEmittedAggTime + periodTimedelta
  while aggStartDatetime < stopDatetime:
    # Get News Volume metrics for one aggregation interval
    aggStopDatetime = aggStartDatetime + periodTimedelta
    symbolToNewsVolumeMap = defaultdict(
      int,
      _queryNewsVolumes(aggStartDatetime, aggStopDatetime))

    # Generate metric samples
    epochTimestamp = date_time_utils.epochFromNaiveUTCDatetime(aggStartDatetime)
    samples = tuple(
      dict(
        metricName=spec.metric,
        value=symbolToNewsVolumeMap[spec.symbol],
        epochTimestamp=epochTimestamp)
      for spec in metricSpecs
    )

    # Emit samples to Metric Listener
    try:
      with metric_utils.metricDataBatchWrite(log=g_log) as putSample:
        for sample in samples:
          putSample(**sample)
    except Exception:
      g_log.exception("Failure while emitting metric data for agg=%s "
                      "containing numSamples=%d",
                      aggStartDatetime, len(samples))
      return lastEmittedAggTime
    else:
      g_log.info("Forwarded numSamples=%d for agg=%s",
                 len(samples), aggStartDatetime)

    # Update db with last successfully-emitted datetime
    metric_utils.updateLastEmittedSampleDatetime(
      key=_EMITTED_NEWS_VOLUME_SAMPLE_TRACKER_KEY,
      sampleDatetime=aggStartDatetime)

    # Set up for next iteration
    lastEmittedAggTime = aggStartDatetime
    aggStartDatetime = aggStopDatetime


  return lastEmittedAggTime



def _logSummaries(headlineTasksWithCounts,
                  headlineErrorTasks,
                  releaseTasksWithCounts,
                  releaseErrorTasks):
  """ Log summaries of task completions from a processing cycle
  :param headlineTasksWithCounts: a map of company symbol to sequence of
    two-tuples (<_HistoricalHeadlinesTask object>, <news story count>)
  :param headlineErrorTasks: a map of company symbol to sequence of failed
    _HistoricalHeadlinesTask objects
  :param releaseTasksWithCounts: a map of company symbol to sequence of
    two-tuples (<_HistoricalReleasesTask object>, <news story count>)
  :param releaseErrorTasks: a map of company symbol to sequence of failed
    _HistoricalReleasesTask objects
  """
  startDateGetter = lambda taskCountPair: taskCountPair[0].startDate

  if headlineTasksWithCounts:
    totalNewHeadlines = 0
    for tasksWithCounts in (
        headlineTasksWithCounts.itervalues()):
      for task, count in sorted(tasksWithCounts, key=startDateGetter):
        totalNewHeadlines += count
        g_log.info("%s newHeadlines=%d", task, count)

    g_log.info("totalNewHeadlines=%d", totalNewHeadlines)

  if headlineErrorTasks:
    totalHeadlineErrors = sum(len(tasks) for tasks in
                              headlineErrorTasks.itervalues())
    g_log.error("totalHeadlineErrors=%d", totalHeadlineErrors)

  if releaseTasksWithCounts:
    totalNewReleases = 0
    for tasksWithCounts in (
        releaseTasksWithCounts.itervalues()):
      for task, count in sorted(tasksWithCounts, key=startDateGetter):
        totalNewReleases += count
        g_log.info("%s newReleases=%d", task, count)

    g_log.info("totalNewReleases=%d", totalNewReleases)

  if releaseErrorTasks:
    totalReleaseErrors = sum(len(tasks) for tasks in
                              releaseErrorTasks.itervalues())
    g_log.error("totalReleaseErrors=%d", totalReleaseErrors)



def _processNewsCollectionTasks(pool,
                                tasksIter,
                                headlineEndDates,
                                releaseEndDates,
                                options):
  """ Process news collection tasks using multiprocessing pool

  :param pool: multiprocessing.Pool object
  :param tasksIter: an iterable that yields task objects (
    _HistoricalHeadlinesTask and _HistoricalReleasesTask) to be processed via
    pool workers
  :param headlineEndDates: a dict that maps security symbols to the
    datetime.date of most recently-stored headlines for those securities.
    NOTE: updatated by this function as news is retrieved
  :param releaseEndDates: a dict that maps security symbols to the
    datetime.date of most recently-stored releases for those securities.
    NOTE: updatated by this function as news is retrieved
  :param options: options from _parseArgs
  """
  executeTaskFn = partial(_executeTask, apiToken=options.apiToken)

  newSecurityHeadlineTasksWithCounts = defaultdict(list)
  securityHeadlineErrorTasks = defaultdict(list)
  newSecurityReleaseTasksWithCounts = defaultdict(list)
  securityReleaseErrorTasks = defaultdict(list)

  for task, newNewsCount in pool.imap_unordered(executeTaskFn, tasksIter):
    # Tally results
    g_log.debug("%s newNewsCount=%r", task, newNewsCount)

    if isinstance(task, _HistoricalHeadlinesTask):
      lastEndDates = headlineEndDates
      newSecurityNewsTasksWithCounts = newSecurityHeadlineTasksWithCounts
      securityErrorTasks = securityHeadlineErrorTasks
    elif isinstance(task, _HistoricalReleasesTask):
      lastEndDates = releaseEndDates
      newSecurityNewsTasksWithCounts = newSecurityReleaseTasksWithCounts
      securityErrorTasks = securityReleaseErrorTasks
    else:
      raise ValueError("Unexpected class of task=%r" % (task,))

    symbol = task.security[0]

    if newNewsCount is None:
      # Failed request
      securityErrorTasks[symbol].append(task)
      continue

    if newNewsCount != 0:
      newSecurityNewsTasksWithCounts[symbol].append((task, newNewsCount))

    if (lastEndDates.setdefault(symbol, task.endDate) <
        task.endDate):
      lastEndDates[symbol] = task.endDate

  # Log summaries
  _logSummaries(
    headlineTasksWithCounts=newSecurityHeadlineTasksWithCounts,
    headlineErrorTasks=securityHeadlineErrorTasks,
    releaseTasksWithCounts=newSecurityReleaseTasksWithCounts,
    releaseErrorTasks=securityReleaseErrorTasks)



def main():
  """
  NOTE: main also serves as entry point for "console script" generated by setup
  """
  logging_support.LoggingSupport.initService()

  options = _parseArgs()

  # See OP_MODE_ACTIVE, etc. in ApplicationConfig
  opMode = config.get("xignite_security_news_agent", "opmode")
  g_log.info("Starting: opMode=%s", opMode)

  aggSec = options.aggIntervalSec

  # Load metric specs from metric configuration
  metricSpecs = _loadNewsVolumeMetricSpecs()

  # Load securities from metric configuration
  securities = getAllMetricSecurities()
  g_log.info("Collecting headlines and releases for %s", securities)

  # Maps security symbols to the datetime.date of most recently-stored headlines
  lastSecurityHeadlineEndDates = _querySecurityNewsEndDates(
    schema.xigniteSecurityHeadline)

  # Map security symbols to the datetime.date of most recently-stored releases
  lastSecurityReleaseEndDates = _querySecurityNewsEndDates(
    schema.xigniteSecurityRelease)

  # Establish/retrieve datetime of last successfully-emitted metric data batch
  lastEmittedAggTime = metric_utils.establishLastEmittedSampleDatetime(
    key=_EMITTED_NEWS_VOLUME_SAMPLE_TRACKER_KEY,
    aggSec=aggSec)

  # Calculate next aggregation start time using lastEmittedAggTime as base
  lastAggStart = date_time_utils.epochFromNaiveUTCDatetime(lastEmittedAggTime)
  nextAggEnd= lastAggStart + (
    int((time.time() - lastAggStart + aggSec - 1) / aggSec) * aggSec) + aggSec

  # Poll, store and emit samples
  pollingIntervalSec = aggSec / 2.0
  numPoolWorkers = max(_MIN_POOL_CONCURRENCY, multiprocessing.cpu_count())
  g_log.info("Entering main loop: pollingIntervalSec=%s; numPoolWorkers=%d",
             pollingIntervalSec, numPoolWorkers)
  pool = multiprocessing.Pool(processes=numPoolWorkers)
  try:
    while True:
      pollingIntervalEnd = time.time() + pollingIntervalSec

      # Retrieve all headlines and releases of interest
      headlineTasks = _generateTasks(
        securities,
        lastSecurityHeadlineEndDates,
        options.backfillDays,
        taskClass=_HistoricalHeadlinesTask,
        dryRun=options.dryRun)

      releaseTasks = _generateTasks(
        securities,
        lastSecurityReleaseEndDates,
        options.backfillDays,
        taskClass=_HistoricalReleasesTask,
        dryRun=options.dryRun)

      allTasks = itertools.chain(headlineTasks, releaseTasks)

      _processNewsCollectionTasks(pool=pool,
                                  tasksIter=allTasks,
                                  headlineEndDates=lastSecurityHeadlineEndDates,
                                  releaseEndDates=lastSecurityReleaseEndDates,
                                  options=options)

      # Aggregate and forward metric samples to htmengine's Metric Listener
      if time.time() >= nextAggEnd:
        if opMode == config.OP_MODE_ACTIVE and not options.dryRun:
          lastEmittedAggTime = _forwardNewsVolumeMetrics(
            metricSpecs=metricSpecs,
            lastEmittedAggTime=lastEmittedAggTime,
            stopDatetime=datetime.utcfromtimestamp(nextAggEnd),
            periodSec=aggSec,
            metricDestAddr=options.metricDestAddr)

        nextAggEnd += aggSec

      sleepSec = pollingIntervalEnd - time.time()
      if sleepSec > 0:
        g_log.info("Sleeping for %f seconds. zzzzzzzz...", sleepSec)
        time.sleep(sleepSec)
      elif sleepSec < 0:
        g_log.warning("Processing exceeded pollingInterval=%ss by overage=%ss",
                      pollingIntervalSec, -sleepSec)
  except KeyboardInterrupt:
    # Log with exception info to help debug deadlocks
    g_log.info("Observed KeyboardInterrupt", exc_info=True)
    pass
  finally:
    g_log.info("Closing multiprocessing.Pool")
    pool.close()

    g_log.info("Terminating multiprocessing.Pool")
    pool.terminate()
    g_log.info("Multiprocessing.Pool terminated")



def _parseArgs():
  """
  :returns: OptionParser options object with the following options:
    apiToken: XIgnite API token (REQUIRED)
    dryRun: boolean; if true, do a dry run (retrieve data, but don't store it)
    aggIntervalSec: Metric aggregation interval in seconds
    backfillDays: Max number of days for backfilling headlines and releases
    metricDestAddr: two-tuple (metricDestHost, metricDestPort) or None if dryRun
  """
  helpString = (
    "./%prog  --apitoken=APITOKEN --metric-addr=METRICDESTADDR [options]\n\n"
    "This agent periodically queries XIgnite API for financial security "
    "headlines and releases, and stores the results in the taurus_collectors "
    "database.")

  parser = OptionParser(helpString)

  parser.add_option(
      "--api-token",
      action="store",
      type="string",
      default=_DEFAULT_API_TOKEN,
      dest="apiToken",
      help="XIgnite API Token [default: %default]")

  parser.add_option(
      "--agg-interval",
      action="store",
      type="int",
      dest="aggIntervalSec",
      default=DEFAULT_AGGREGATION_INTERVAL_SEC,
      help="Metric aggregation interval in seconds [default: %default]")

  parser.add_option(
      "--backfill-days",
      action="store",
      type="int",
      dest="backfillDays",
      default=DEFAULT_MAX_BACKFILL_DAYS,
      help=("Max number of days for backfilling headlines and releases; the "
            "underlying service lacks datetime granularity for backfilled data "
            "beyond the article's date [default: %default]"))

  parser.add_option(
      "--dryrun",
      action="store_true",
      default=False,
      dest="dryRun",
      help="Use this flag to do a dry run (retrieve data, but don't store it)")

  parser.add_option(
    "--metric-addr",
    action="store",
    type="string",
    dest="metricDestAddr",
    help=("Destination address for metrics as host:port; typically address of "
          "YOMP's custom metrics listener; YOMP's default metric listener port "
          "is 2003"))

  options, _ = parser.parse_args()

  if not options.apiToken:
    parser.error("Missing required XIgnite API Token")

  if options.dryRun:
    if options.metricDestAddr:
      msg = "--dryrun is mutually exclusive with --metric-addr"
      g_log.error(msg)
      parser.error(msg)

    options.metricDestAddr = None
  else:
    if not options.metricDestAddr:
      msg = "Missing address of metric destination server"
      g_log.error(msg)
      parser.error(msg)

    metricDestHost, _, metricDestPort = options.metricDestAddr.partition(":")
    if not metricDestHost:
      msg = "Missing hostname or IP address of metric destination server."
      g_log.error(msg)
      parser.error(msg)

    if not metricDestPort:
      msg = "Missing port number of metric destination server."
      g_log.error(msg)
      parser.error(msg)

    try:
      metricDestPort = int(metricDestPort)
    except ValueError:
      msg = "Metric destination port must be an integer, but got %r" % (
        metricDestPort,)
      g_log.exception(msg)
      parser.error(msg)

    options.metricDestAddr = (metricDestHost, metricDestPort)

  return options



if __name__ == "__main__":
  main()
