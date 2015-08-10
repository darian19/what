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
Publish recent previously-collected non-metric twitter
data to the Taurus non-metric data RabbitMQ exchange
"""

from datetime import datetime, timedelta
import logging
from optparse import OptionParser


import sqlalchemy as sql

from nta.utils.message_bus_connector import MessageBusConnector

from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors.collectorsdb import schema
from taurus.metric_collectors import logging_support
from taurus.metric_collectors.twitterdirect.twitter_direct_agent import \
    TweetForwarder

# Will pubish previously-collected tweets that were created
_BACKLOG_DAYS = 14



g_log = logging.getLogger("migrate_tweets_to_dynamodb")



def _parseArgs():
  """ Display help, if requested, and validate that no unexpected args are
  passed
  """
  helpString = (
    "%%prog \n\n"
    "Publish the past %s days worth of previously-collected non-metric twitter "
    "data to the Taurus non-metric-data RabbitMQ exchange." % (_BACKLOG_DAYS,))

  parser = OptionParser(helpString)


  _options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))


def migrate(metrics=None):
  """ Migrate _BACKLOG_DAYS worth of previously-collected tweets to the Taurus
  non-metric-data RabbitMQ exchange.

  :param metrics: optional sequence of metric names; if specified (not None),
    the migration will be limited to tweets corresponding to the given metric
    names.
  """
  startingTimestamp = datetime.utcnow() - timedelta(days=_BACKLOG_DAYS)

  sqlEngine = collectorsdb.engineFactory()

  # Retrieve the first twitter samples sequence number in the desired range
  # select min(seq) from twitter_tweet_samples where agg_ts >= startingTimestamp

  @collectorsdb.retryOnTransientErrors
  def queryMigrationRange():
    sel = (sql.select(
            [sql.func.count(),
             sql.func.min(schema.twitterTweetSamples.c.seq),
             sql.func.max(schema.twitterTweetSamples.c.seq)])
           .where(schema.twitterTweetSamples.c.agg_ts >= startingTimestamp))
    if metrics is not None:
      sel = sel.where(schema.twitterTweetSamples.c.metric.in_(metrics))

    return sqlEngine.execute(sel).first()

  totalNumItems, minSeq, maxSeq = queryMigrationRange()
  if totalNumItems == 0:
    g_log.info("Nothing forwarded: no tweet samples found since %s UTC",
               startingTimestamp.isoformat())
    return

  if metrics is None:
    g_log.info("Starting migration of tweets from %s UTC; totalNumItems=%d; "
               "minSeq=%s, maxSeq=%s",
               startingTimestamp.isoformat(), totalNumItems, minSeq, maxSeq)
  else:
    g_log.info("Starting migration of tweets from %s UTC; totalNumItems=%d; "
               "minSeq=%s, maxSeq=%s; metrics=%s",
               startingTimestamp.isoformat(), totalNumItems, minSeq, maxSeq,
               metrics)

  # Retrieve and publish batches
  totalNumPublished = 0
  totalNumBatches = 0
  batchMinSeq = minSeq
  with MessageBusConnector() as messageBus:
    while True:
      batchEndSeq, batch = TweetForwarder.queryNonMetricTweetBatch(
        sqlEngine=sqlEngine,
        minSeq=batchMinSeq,
        maxItems=200,
        maxSeq=maxSeq,
        metrics=metrics)

      if batchEndSeq is None:
        break

      TweetForwarder.publishNonMetricTweetBatch(messageBus=messageBus,
                                                batch=batch)

      totalNumPublished += len(batch)
      totalNumBatches += 1

      g_log.debug("Published numItems=%d; batchMinSeq=%s; batchEndSeq=%s "
                  "(%d of %d: %s%%)",
                  len(batch), batchMinSeq, batchEndSeq,
                  totalNumPublished, totalNumItems,
                  int(float(totalNumPublished)/totalNumItems * 100))

      if (totalNumBatches % 250) == 0 or totalNumPublished == totalNumItems:
        # Progress report
        g_log.info(
          "Published %d of %d: %s%%",
          totalNumPublished, totalNumItems,
          int(float(totalNumPublished)/totalNumItems * 100))

      # Prepare for next query
      batchMinSeq = batchEndSeq + 1

  g_log.info("Done publishing! publishedBatches=%d, publishedItems=%d, "
             "expectedItems=%d; minSeq=%s, maxSeq=%s",
             totalNumBatches, totalNumPublished,
             totalNumItems, minSeq, maxSeq)


def main():
  """
  NOTE: main also serves as entry point for "console script" generated by setup
  """
  logging_support.LoggingSupport.initTool()

  _parseArgs()

  migrate()



if __name__ == "__main__":
  main()
