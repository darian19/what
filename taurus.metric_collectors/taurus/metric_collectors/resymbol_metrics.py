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
Purges old records from taurus_collectors.twitter_tweets table.

NOTE: this script may be configured as "console" app by the package
installer.
"""

from collections import namedtuple
from datetime import datetime, timedelta
import logging
from optparse import OptionParser
import os

from sqlalchemy import sql

from taurus.metric_collectors import (
    collectorsdb,
    config,
    logging_support,
    metric_utils)
from taurus.metric_collectors.collectorsdb import schema
from taurus.metric_collectors import gen_metrics_config
from taurus.metric_collectors.twitterdirect import migrate_tweets_to_dynamodb

from taurus.metric_collectors.twitterdirect import twitter_direct_agent
from taurus.metric_collectors.xignite import xignite_stock_agent

from taurus.metric_collectors.twitterdirect.twitter_direct_agent import (
    _EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY
)



DEFAULT_HTM_SERVER = os.environ.get("TAURUS_HTM_SERVER")


# Maximum window for forwarded metric data samples
MAX_METRIC_SAMPLE_BACKLOG_DAYS = 90


g_log = logging.getLogger(__name__)



def _parseArgs():
  """
  :returns: dict of arg names and values:
    old_symbol - the orignal ticker symbol
    new_symbol - the new ticker symbol
    migrate_price - boolean specifying whether to keep historical price data
    migrate_tweets - boolean specifying whether to keep historical twitter data
  """
  helpString = (
      "%%prog [options]"
      "Tool to rename a metric's symbol and migrate the historical data to the "
      "new metric.")

  parser = OptionParser(helpString)

  parser.add_option(
      "--server",
      action="store",
      type="string",
      dest="htmServer",
      default=DEFAULT_HTM_SERVER,
      help="Hostname or IP address of server running HTM Engine API to create "
      "models [default: %default]")

  parser.add_option(
      "--apikey",
      action="store",
      type="string",
      dest="apikey",
      default="taurus",
      help="API Key of HTM Engine to create models [default: %default]")

  parser.add_option(
      "--period",
      action="store",
      type="int",
      dest="aggPeriod",
      default=300,
      help="Volume aggregation period in seconds [default: %default]")

  parser.add_option(
      "--oldsymbol",
      action="store",
      type="string",
      dest="oldSymbol",
      help="Original ticker symbol currently used by metric_collector")

  parser.add_option(
      "--newsymbol",
      action="store",
      type="string",
      dest="newSymbol",
      help="New ticker symbol to be used")

  parser.add_option(
      "-t", "--twitteronly",
      action="store_false",
      dest="stocks",
      default=True,
      help="Only migrate twitter metric data"
  )

  parser.add_option(
      "-x", "--stocksonly",
      action="store_false",
      dest="twitter",
      default=True,
      help="Only migrate xignite stock metric data"
  )


  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if options.oldSymbol is None:
    parser.error("Required \"--oldsymbol\" option was not specified")
  if options.newSymbol is None:
    parser.error("Required \"--newsymbol\" option was not specified")


  if (not options.twitter) and (not options.stocks):
    parser.error("Flags specifying a single type of metric to migrate can "
                 "only be used exclusively. Forwarding all metrics is already "
                 "the default behavior of this tool.")

  optionsTuple = namedtuple("optionsTuple", "htmServer "
                                            "apikey "
                                            "aggPeriod "
                                            "oldSymbol "
                                            "newSymbol "
                                            "twitter "
                                            "stocks")

  return optionsTuple(htmServer=options.htmServer,
                      apikey=options.apikey,
                      aggPeriod=options.aggPeriod,
                      oldSymbol=options.oldSymbol.upper(),
                      newSymbol=options.newSymbol.upper(),
                      twitter=options.twitter,
                      stocks=options.stocks)



def _resymbolTweetVolumeMetric(oldSymbol, newSymbol, aggPeriod):
  """ Perform the workflow of resymboling a tweet volume metric that consists of
  the following steps:
    1. Reassign bufferred tweet samples in collectorsdb to the new metric.
    2. Forward the new metric data samples to HTM Engine
    3. Forward the tweet media to dynamodb

  :param str oldSymbol: old stock symbol, upper case
  :param str newSymbol: new stock symbol, upper case
  :param int aggPeriod: metric aggregation period in seconds
  """
  g_log.info(
    "Renaming tweet sample metric: oldSymbol=%s, newSymbol=%s, aggPeriod=%s",
    oldSymbol, newSymbol, aggPeriod)

  oldMetricName = gen_metrics_config.getTweetVolumeMetricName(oldSymbol)
  newMetricName = gen_metrics_config.getTweetVolumeMetricName(newSymbol)

  sqlEngine = collectorsdb.engineFactory()

  # Rename the metric in tweet sample rows

  with sqlEngine.begin() as conn:
    # Verify that metric samples with new symbol don't overlap with with samples
    # corresponding to the old symbol
    g_log.info("Verifying that newMetric=%s in table=%s doesn't overlap with "
               "the oldMetric=%s.",
               newMetricName, schema.twitterTweetSamples, oldMetricName)

    maxOldMetricAggTimestamp = conn.execute(
      sql.select([sql.func.max(schema.twitterTweetSamples.c.agg_ts)])
    ).scalar()

    if maxOldMetricAggTimestamp is not None:
      overlappingRow = conn.execute(
        sql.select([schema.twitterTweetSamples.c.metric])
        .where(schema.twitterTweetSamples.c.metric == newMetricName)
        .where(schema.twitterTweetSamples.c.agg_ts <= maxOldMetricAggTimestamp)
        .order_by(schema.twitterTweetSamples.c.agg_ts.asc())
        .limit(1)).first()
      assert overlappingRow is None, overlappingRow

    # Re-symbol the tweet sample metric rows
    g_log.info("Renaming tweet sample metric %s with %s",
               oldMetricName, newMetricName)
    conn.execute(
      schema.twitterTweetSamples  # pylint: disable=E1120
      .update()
      .where(schema.twitterTweetSamples.c.metric == oldMetricName)
      .values(metric=newMetricName))


  # Forward tweet metric samples to Taurus Engine

  g_log.info("Forwarding new tweet metric=%s samples to Taurus engine...",
             newMetricName)

  # Get the aggregation timestamp of the starting tweet sample to forward
  #
  # NOTE: prior to March 2015, tweet samples didn't have a consistent reference
  # between twitter agent's restarts. This issue was address with the
  # introduction of emitted_sample_tracker table.
  #
  timestampScanLowerBound = (datetime.utcnow() -
                             timedelta(days=MAX_METRIC_SAMPLE_BACKLOG_DAYS))

  aggStartDatetime = sqlEngine.execute(
    sql.select([schema.twitterTweetSamples.c.agg_ts],
      order_by=schema.twitterTweetSamples.c.agg_ts.asc())
    .where(schema.twitterTweetSamples.c.metric == newMetricName)
    .where(schema.twitterTweetSamples.c.agg_ts > timestampScanLowerBound)
    .limit(1)).scalar()

  # Get the timestamp of the most recent sample batch emitted to Taurus engine
  lastEmittedAggTime = metric_utils.queryLastEmittedSampleDatetime(
    key=_EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY)

  if lastEmittedAggTime is None:
    # Last emitted sample datetime has not been established yet; we'll rely
    # on the twitter agent to forward all metric samples to HTM engine
    g_log.info("Last emitted sample datetime has not been established yet; "
               "deferring metric sample forwarding to Twitter Agent.")
    return

  metricDataForwarder = twitter_direct_agent.MetricDataForwarder(
    metricSpecs=twitter_direct_agent.loadMetricSpecs(),
    aggSec=aggPeriod)

  metricDataForwarder.aggregateAndForward(
      aggStartDatetime=aggStartDatetime,
      stopDatetime=lastEmittedAggTime + timedelta(seconds=aggPeriod),
      metrics=[newMetricName])


  # Forward tweet media to dynamodb
  g_log.info("Forwarding twitter tweets to dynamodb using new symbol...")
  migrate_tweets_to_dynamodb.migrate(metrics=[newMetricName])



def _resymbolStockMetrics(oldSymbol, newSymbol):
  """ Resymbol stock metrics

  :param str oldSymbol: old stock symbol, upper case
  :param str newSymbol: new stock symbol, upper case
  """
  g_log.info("Renaming stock metrics: oldSymbol=%s, newSymbol=%s",
             oldSymbol, newSymbol)

  sqlEngine = collectorsdb.engineFactory()


  with sqlEngine.begin() as conn:
    # NOTE: the foreign key cascade-on-update relationship between
    # emitted_stock_price/emitted_stock_volume tables and the
    # xignite_security_bars table causes the symbol to be automatically updated
    # in the xignite_security_* tables

    # Delete emitted stock price rows for old symbol
    conn.execute(
      schema.emittedStockPrice  # pylint: disable=E1120
      .delete()
      .where(schema.emittedStockPrice.c.symbol == oldSymbol)
    )

    # Delete emitted stock volume rows for old symbol
    conn.execute(
      schema.emittedStockVolume  # pylint: disable=E1120
      .delete()
      .where(schema.emittedStockVolume.c.symbol == oldSymbol)
    )

    # Re-symbol xignite security row associated with the old symbol
    #
    # TODO TAUR-1327: when we rename this symbol in the xignite_security table,
    # we leave other columns of the affected xignite_security row likely
    # inconsitent with the new symbol, which is bad. Once TAUR-1327 is complete,
    # this problem will go away along with this operation on xignite_security
    # table.
    #
    # NOTE: we use IGNORE to ignore integrity errors (most likely duplicate),
    # because stock agent might insert a security row for the new symbol before
    # we do.
    conn.execute(
      schema.xigniteSecurity  # pylint: disable=E1120
      .update().prefix_with('IGNORE', dialect="mysql")
      .where(schema.xigniteSecurity.c.symbol == oldSymbol)
      .values(symbol=newSymbol)
    )
    # Delete old xignite security row just in case the rename aborted due to
    # integrity error
    conn.execute(
      schema.xigniteSecurity  # pylint: disable=E1120
      .delete()
      .where(schema.xigniteSecurity.c.symbol == oldSymbol)
    )

    # Update stock bars
    # NOTE: This becomes necessary once TAUR-1327 is implemented
    conn.execute(
      schema.xigniteSecurityBars  # pylint: disable=E1120
      .update()
      .where(schema.xigniteSecurityBars.c.symbol == oldSymbol)
      .values(symbol=newSymbol))

  # Forward stock metric data samples to Taurus Engine
  g_log.info("Forwarding new stock metric data samples for symbol=%s to Taurus "
             "engine...", newSymbol)
  xignite_stock_agent.transmitMetricData(
    metricSpecs=[spec for spec
                 in xignite_stock_agent.loadMetricSpecs()
                 if spec.symbol == newSymbol],
      symbol=newSymbol,
      engine=sqlEngine
  )


def _deleteSymbolMetricsFromEngine(host, apiKey, symbol):
  """Delete metrics corresponding to the given stock symbol from Taurus Engine

  :param host: API server's hostname or IP address
  :param apiKey: API server's API Key
  :param symbol: Stock symbol
  """
  g_log.info("Unmonitoring and deleting existing metrics linked to stock "
             "symbol=%s", symbol)

  # Get matching metrics
  allMetrics = metric_utils.getAllCustomMetrics(host=host, apiKey=apiKey)

  metricsToDelete = tuple(obj["name"]
                          for obj in allMetrics
                          if ".{symbol}.".format(symbol=symbol) in obj["name"])

  g_log.info("Deleteing metrics=%s", metricsToDelete)
  for metricName in metricsToDelete:
    g_log.info("Deleting metric=%s", metricName)
    metric_utils.deleteMetric(host, apiKey, metricName)



def main():
  """
  NOTE: main also serves as entry point for "console script" generated by setup
  """
  logging_support.LoggingSupport().initTool()

  try:
    options = _parseArgs()
    allSymbols = set(stockData["symbol"] for stockData in
                     metric_utils.getMetricsConfiguration().itervalues() )

    g_log.info("Verifying that agents are in hot_standby mode")
    for section in config.sections():
      assert config.get(section, "opmode") == config.OP_MODE_HOT_STANDBY

    g_log.info("Verifying that the old symbol has been removed from the "
               "metrics configuration")
    assert options.oldSymbol not in allSymbols

    g_log.info("Verifying that the new symbol is present in the metrics "
               "configuration")
    assert options.newSymbol in allSymbols

    if options.twitter and not options.stocks:
      g_log.info("Migrating ONLY twitter data from old-symbol=%s "
                 "to new-symbol=%s",
                 options.oldSymbol, options.newSymbol)
    elif options.stocks and not options.twitter:
      g_log.info("Migrating ONLY xignite stock data from old-symbol=%s "
                 "to new-symbol=%s",
                 options.oldSymbol, options.newSymbol)
    else:
      g_log.info("Migrating BOTH twitter and xignite stock data from "
                 "old-symbol=%s to new-symbol=%s",
                 options.oldSymbol, options.newSymbol)

    # Rename the metrics in collectorsdb and forward new metric samples to HTM
    # Engine
    g_log.info("Modifying old metrics with new symbol")

    if options.twitter:
      _resymbolTweetVolumeMetric(oldSymbol=options.oldSymbol,
                                 newSymbol=options.newSymbol,
                                 aggPeriod=options.aggPeriod)

    if options.stocks:
      _resymbolStockMetrics(oldSymbol=options.oldSymbol,
                            newSymbol=options.newSymbol)


    # Delete metrics linked to old stock symbol from Taurus Engine
    _deleteSymbolMetricsFromEngine(host=options.htmServer,
                                   apiKey=options.apikey,
                                   symbol=options.oldSymbol)


  except SystemExit as e:
    if e.code != 0:
      g_log.exception("Failed!")
    raise
  except Exception:
    g_log.exception("Failed!")
    raise



if __name__ == "__main__":
  main()
