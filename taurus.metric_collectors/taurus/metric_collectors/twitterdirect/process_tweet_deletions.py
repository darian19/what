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
Service the current tweet deletion requests that are recorded in the
twitter_deletion table and exit. This script is intended to be called
periodically via crontab or equivalent.

Our twitter_direct_agent service saves tweet deletion requests that are
delivered via our twitter stream. These deletion requests need to be processed
as described in https://dev.twitter.com/streaming/overview/messages-types

NOTE: Per twitter doc, it's possible that the deletion request could be streamed
prior to the referenced tweet.
"""

import logging
from optparse import OptionParser
import sys

import sqlalchemy

from taurus.metric_collectors import collectorsdb, logging_support



g_log = logging.getLogger("process_tweet_deletions")



# Age, in days, when schema.twitterDeletion rows expire
_DELETION_ROW_EXPIRY_DAYS = 1



def _parseArgs():
  """ Parse arguments, emit help message when requested
  """
  helpString = (
    "%prog\n\n"
    "Service the current tweet deletion requests that are recorded in the "
    "twitter_deletion table and exit. This script is intended to be called "
    "periodically via crontab or equivalent.")

  parser = OptionParser(helpString)

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))


@collectorsdb.retryOnTransientErrors
def _purgeTweetsSlatedForDeletion(limit):
  """ Purge tweets that are slated for deletion as indicated by entries in the
  schema.twitterDeletion table

  :param limit: max records to purge per call
  :returns: a sequence of id's of deleted tweets
  """
  twitterTweetsSchema = collectorsdb.schema.twitterTweets
  twitterDeletionSchema = collectorsdb.schema.twitterDeletion


  # NOTE: we first query the row id's to delete, so we can return them for
  # accountability and debugging
  rowsToDeleteSel = sqlalchemy.select([twitterTweetsSchema.c.uid]).where(
    twitterTweetsSchema.c.uid.in_(
      sqlalchemy.select([twitterDeletionSchema.c.tweet_uid]))).limit(limit)

  numDeleted = 0
  with collectorsdb.engineFactory().begin() as conn:
    rowIdsToDelete = tuple(
      str(row[0]) for row in conn.execute(rowsToDeleteSel).fetchall()
    )

    if rowIdsToDelete:
      tweetDeletion = twitterTweetsSchema.delete().where(
        twitterTweetsSchema.c.uid.in_(rowIdsToDelete))

      numDeleted = conn.execute(tweetDeletion).rowcount

  if len(rowIdsToDelete) != numDeleted:
    g_log.error("Expected to delete %d tweets, but actually deleted %d tweets",
                len(rowIdsToDelete), numDeleted)

  return rowIdsToDelete



@collectorsdb.retryOnTransientErrors
def _purgeStaleDeletionRecords(limit):
  """ Delete stale rows in schema.twitterDeletion table

  :param limit: max records to purge per call
  :returns: a sequence of tweet_uid's of deleted schema.twitterDeletion rows
  """
  twitterDeletionSchema = collectorsdb.schema.twitterDeletion

  # NOTE: we first query the row id's to delete, so we can return them for
  # accountability and debugging
  rowsToDeleteSel = sqlalchemy.select(
    [twitterDeletionSchema.c.tweet_uid]).where(
      twitterDeletionSchema.c.created_at <
      sqlalchemy.func.date_sub(
        sqlalchemy.func.current_timestamp(),
        sqlalchemy.text("INTERVAL %i DAY" % (_DELETION_ROW_EXPIRY_DAYS,)))
      ).limit(limit)

  numDeleted = 0
  with collectorsdb.engineFactory().begin() as conn:
    rowIdsToDelete = tuple(
      str(row[0]) for row in conn.execute(rowsToDeleteSel).fetchall()
    )

    if rowIdsToDelete:
      deletion = twitterDeletionSchema.delete().where(
        twitterDeletionSchema.c.tweet_uid.in_(rowIdsToDelete))

      numDeleted = conn.execute(deletion).rowcount

  if len(rowIdsToDelete) != numDeleted:
    g_log.error("Expected to delete %d tweet delition request rows, but "
                "actually deleted %d rows", len(rowIdsToDelete), numDeleted)

  return rowIdsToDelete


def main():
  """
  NOTE: main also serves as entry point for "console script" generated by setup
  """
  logging_support.LoggingSupport().initTool()

  try:
    _parseArgs()

    # Process tweet deletions
    g_log.info("Processing tweet deletions")
    totalDeletedTweets = 0
    tweetDeletionLimit = 100
    while True:
      deletedTweetIds = _purgeTweetsSlatedForDeletion(limit=tweetDeletionLimit)
      numDeletedTweets = len(deletedTweetIds)
      if numDeletedTweets:
        totalDeletedTweets += numDeletedTweets
        g_log.info("Purged numTweets=%d: %s", numDeletedTweets, deletedTweetIds)

      if numDeletedTweets < tweetDeletionLimit:
        break

    g_log.info("Purged totalDeletedTweets=%d", totalDeletedTweets)


    # Purge stale tweet deletion request rows
    g_log.info("Purging stale tweet deletion request rows")
    totalPurgedTweetDeletionRows = 0
    deletionRowPurgeLimit = 100
    while True:
      purgedDeletionIds = _purgeStaleDeletionRecords(
        limit=deletionRowPurgeLimit)
      numPurgedTweetDeletionRows = len(purgedDeletionIds)
      if numPurgedTweetDeletionRows:
        totalPurgedTweetDeletionRows += numPurgedTweetDeletionRows
        g_log.info("Purged numPurgedTweetDeletionRows=%d: %s",
                   numPurgedTweetDeletionRows, purgedDeletionIds)

      if numPurgedTweetDeletionRows < deletionRowPurgeLimit:
        break

    g_log.info("Purged totalPurgedTweetDeletionRows=%d",
               totalPurgedTweetDeletionRows)

  except SystemExit as e:
    if e.code != 0:
      g_log.exception("Failed!")
    raise
  except Exception:
    g_log.exception("Failed!")
    raise



if __name__ == "__main__":
  main()
