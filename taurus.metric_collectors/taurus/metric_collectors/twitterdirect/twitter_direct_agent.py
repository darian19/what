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

from collections import namedtuple
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import islice
import json
import logging
import multiprocessing
from optparse import OptionParser
import os
import pprint
import Queue
import sys
import threading
import time

import sqlalchemy as sql
import tweepy

from nta.utils import amqp
from nta.utils import date_time_utils
from nta.utils.error_handling import abortProgramOnAnyException
from nta.utils.error_handling import logExceptions
from nta.utils.message_bus_connector import MessageBusConnector
from nta.utils.message_bus_connector import MessageProperties

from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors.collectorsdb import schema
from taurus.metric_collectors import config
from taurus.metric_collectors import logging_support
from taurus.metric_collectors import metric_utils
from taurus.metric_collectors.metric_utils import getMetricsConfiguration
from taurus.metric_collectors.text_utils import sanitize4ByteUnicode



# NOTE: default Twitter credentials obtained from "numentastream" account
DEFAULT_CONSUMER_KEY = os.environ.get(
  "TAURUS_TWITTER_CONSUMER_KEY")

DEFAULT_CONSUMER_SECRET = os.environ.get(
  "TAURUS_TWITTER_CONSUMER_SECRET")

DEFAULT_ACCESS_TOKEN = os.environ.get(
  "TAURUS_TWITTER_ACCESS_TOKEN")

DEFAULT_ACCESS_TOKEN_SECRET = os.environ.get(
  "TAURUS_TWITTER_ACCESS_TOKEN_SECRET")


# Our tracker key in the emitted_sample_tracker table
_EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY = "twitter-tweets-volume"



# Initialize logging
g_log = logging.getLogger("twitter_direct_agent")



TwitterMetricSpec = namedtuple(
  "TwitterMetricSpec",
  "resource metric screenNames symbol")


def _percentage(n, d):
  """ Compute percentage of n over d, guarding against d=0

  :returns: percentage; if d is 0, returns `float("inf")`
  :rtype: float
  """
  return (float(n) / d * 100) if d else float("inf")



def loadMetricSpecs():
  """ Load metric specs for the "twitter" provider

  :returns: a sequence of TwitterMetricSpec objects
  """
  return tuple(
    TwitterMetricSpec(resource=resName,
                      metric=metricName,
                      screenNames=metricVal["screenNames"],
                      symbol=resVal["symbol"].lower())
    for resName, resVal in getMetricsConfiguration().iteritems()
    for metricName, metricVal in resVal["metrics"].iteritems()
    if metricVal["provider"] == "twitter")



def buildTaggingMapAndStreamFilterParams(metricSpecs, authHandler):
  """ Build tweet tag processing map and the corresponding twitter stream filter
  params

  :param metricSpecs: sequence of TwitterMetricSpec objects

  :returns: a two-tuple (<taggingMap>, <streamFilterParams>)
    <taggingMap>: a dict of callables to corresponding mapping dictionaries;
      each mapping dictionary key is a target value of interest (e.g., stock
      ticker) and the corresponding value is the name(s) of the metric(s)
      corresonding to that value; the callable is passed each message and
      the mapping dictionary corresponding to the callable, and is responsible
      for adding metric names to the metricTagSet of the message for any hits
      that it finds. This example demonstrates the structure of the
      <taggingMap>:
        {
          tagOnSymbols: {
            "ACN": "TWITTER.TWEET.HANDLE.ACN.VOLUME",
            "IRBT": "TWITTER.TWEET.HANDLE.IRBT.VOLUME",
            . . .
          },
          tagOnSourceUsers: {
            "10194682": set(["TWITTER.TWEET.HANDLE.ACN.VOLUME"]),  # @Accenture
            "20536157": set(["TWITTER.TWEET.HANDLE.GOOGL.VOLUME",
                             "TWITTER.TWEET.HANDLE.GOOG.VOLUME"]), # @google
            "111682122": set(["TWITTER.TWEET.HANDLE.IRBT.VOLUME"]) # @RoombaLove
            . . .
          },
          tagOnMentions: {
            "10194682": set(["TWITTER.TWEET.HANDLE.ACN.VOLUME"]),  # @Accenture
            "20536157": set(["TWITTER.TWEET.HANDLE.GOOGL.VOLUME",
                             "TWITTER.TWEET.HANDLE.GOOG.VOLUME"]), # @google
            "111682122": set(["TWITTER.TWEET.HANDLE.IRBT.VOLUME"]) # @RoombaLove
            . . .
          }
        }
    <streamFilterParams>: a dictionary of parameters to pass to
      tweepy.Stream.filter(); for examle:
        {
          "track": ["@Accenture", "@iRobot", "@RoombaLove", "$ACN", "$IRBT",],
          "follow": ["10194682", "62515374", "111682122",]
        }
  """
  g_log.info("Building Metric Tagging Map and Stream Filter Params")

  def tagOnSymbols(msg, mappings):
    """ Adds metric names to msg["metricTagSet"] for each cashtag in msg with a
    matching key in mappings
    """
    entities = msg.get("entities")
    if not entities:
      return
    symbols = entities.get("symbols")
    if not symbols:
      return

    for sym in symbols:
      ticker = sym.get("text")
      if not ticker:
        continue
      metricName = mappings.get(ticker.lower())
      if metricName:
        msg["metricTagSet"].add(metricName)

  def tagOnSourceUsers(msg, mappings):
    """ Adds metric name(s) to msg["metricTagSet"] corresponding to the matching
    source twitter user id in mappings, if any

    :param mappings: userId-to-metricNames map
    """
    userObj = msg.get("user")
    if not userObj:
      return
    idStr = userObj.get("id_str")
    metricNames = mappings.get(idStr)
    if metricNames:
      msg["metricTagSet"].update(metricNames)

  def tagOnMentions(msg, mappings):
    """ Adds metric names to msg["metricTagSet"] corresponding to the matching
    twitter mention user ids in mappings, if any

    :param mappings: userId-to-metricNames map
    """
    entities = msg.get("entities")
    if not entities:
      return
    userMentions = entities.get("user_mentions")
    if not userMentions:
      return

    for mention in userMentions:
      idStr = mention.get("id_str")
      metricNames = mappings.get(idStr)
      if metricNames:
        msg["metricTagSet"].update(metricNames)


  symbolToMetricMap = dict()
  userIdToMetricsMap = dict()

  taggingMap = {
    tagOnSymbols: symbolToMetricMap,
    tagOnSourceUsers: userIdToMetricsMap,
    tagOnMentions: userIdToMetricsMap
  }

  screenNameToMetricsMap = dict()

  tweepyApi = tweepy.API(authHandler)

  for spec in metricSpecs:
    symbolToMetricMap[spec.symbol] = spec.metric

    for screenName in spec.screenNames:
      screenNameToMetricsMap.setdefault(screenName.lower(), set()).add(
        spec.metric)

  # Get twitter Ids corresponding to screen names and build a userId-to-metric
  # map
  maxLookupItems = 100  # twitter's users/lookup limit
  screenNames = screenNameToMetricsMap.keys()
  lookupSlices = [screenNames[n:n + maxLookupItems]
                  for n in xrange(0, len(screenNames), maxLookupItems)]
  mappedScreenNames = []
  for names in lookupSlices:
    try:
      users = tweepyApi.lookup_users(screen_names=names)
    except Exception:
      g_log.exception("tweepyApi.lookup_users failed for names=%s", names)
      raise

    # NOTE: Users that weren't found will be missing from results
    for user in users:
      screenName = user.screen_name.lower()
      userId = user.id_str
      g_log.info("screenName=%s mapped to userId=%s", screenName, userId)
      userIdToMetricsMap.setdefault(userId, set()).update(
        screenNameToMetricsMap[screenName])

      mappedScreenNames.append(screenName)

  unmappedScreenNames = set(screenNames).difference(mappedScreenNames)
  if unmappedScreenNames:
    g_log.error("No mappings for screenNames=%s", unmappedScreenNames)

  # Generate stream filter parameters
  streamFilterParams = dict(
    track=[("@" + screen) for screen in screenNameToMetricsMap] +
      [("$" + ticker) for ticker in symbolToMetricMap],
    follow=userIdToMetricsMap.keys(),
    stall_warnings=True
  )


  return taggingMap, streamFilterParams



class TwitterStreamListener(tweepy.StreamListener):
  """ Wrapper around tweepy.Stream client. Process incoming messages from
  Twitter stream: tag, save, aggregate and emit metrics, forward non-metric
  tweet data via RabbitMQ.
  """

  class ConnectionMarker(object):
    """ We enqueue this class to notify our tweet storage thread about the new
    connection
    """
    pass


  def __init__(self, metricSpecs, aggPeriod, consumerKey, consumerSecret,
               accessToken, accessTokenSecret, echoData):
    """
    :param metricSpecs: The metrics for which this Twitter Stream Listener
      instance is responsible.
    :type metricSpecs: a sequence of TwitterMetricSpec objects
    :param period: aggregation period in seconds
    :param consumerKey: Twitter consumer key
    :param consumerSecret: Twitter consumer secret
    :param accessToken: Twitter access token
    :param accessTokenSecret: Twitter access token secret
    :param echoData: Echo processed Twitter messages to stdout for debugging
    """
    super(TwitterStreamListener, self).__init__()

    self._metricSpecs = metricSpecs
    self._aggregationPeriod = aggPeriod
    self._consumerKey=consumerKey
    self._consumerSecret=consumerSecret
    self._accessToken=accessToken
    self._accessTokenSecret=accessTokenSecret
    self._echoData = echoData

    # See OP_MODE_ACTIVE, etc. in ApplicationConfig
    self._opMode = config.get("twitter_direct_agent", "opmode")

    self._authHandler = tweepy.OAuthHandler(self._consumerKey,
                                            self._consumerSecret)
    self._authHandler.set_access_token(self._accessToken,
                                       self._accessTokenSecret)

    self._storageThread = None
    self._messageHoldingQ = Queue.Queue()
    self._streamFilterParams = None

    # tweepy.Stream object
    self._stream = None


  def on_connect(self):
    """Called once connected to streaming server.

    This will be invoked once a successful response
    is received from the server. Allows the listener
    to perform some work prior to entering the read loop.
    """
    g_log.info("tweepy.Streamer connected to streaming server")
    self._checkHealth()
    self._messageHoldingQ.put(self.ConnectionMarker)


  def on_error(self, status):
    """ tweepy.StreamListener error sink; Called when a non-200 status code is
    returned

    :returns: False to stop stream and close
    """
    g_log.error("tweepy.Streamer httpError=%s", status)
    self._checkHealth()


  def on_timeout(self):
    """Called when stream connection times out

    :returns: False to stop stream and close
    """
    g_log.error("tweepy.Streamer connection timeout")
    self._checkHealth()


  def on_data(self, data):
    """ tweepy.StreamListener data sink; Called when raw data is received from
    connection

    :returns: False to stop stream and close
    """
    self._checkHealth()
    #print json.dumps(json.loads(data), indent=4)
    self._messageHoldingQ.put(data)
    return True


  def _checkHealth(self):
    if os.getppid() == 1:
      # Our parent process has gone away without shutting us down
      g_log.critical("Exiting streaming process, because our parent "
                     "process has gone away without shutting us down first")
      sys.exit(1)

    if not self._storageThread.is_alive():
      g_log.critical("Exiting streaming process, because our storage thread "
                     "has stopped")
      sys.exit(1)


  def run(self):
    """ Run the Twitter stream listener. """
    g_log.info("%s is running: opMode=%s", self.__class__.__name__,
               self._opMode)

    taggingMap, self._streamFilterParams = (
      buildTaggingMapAndStreamFilterParams(self._metricSpecs,
                                           self._authHandler))

    # Start tweet storage thread
    storageThreadKwargs=dict(
      aggSec=self._aggregationPeriod,
      msgQ=self._messageHoldingQ,
      echoData=self._echoData,
      taggingMap=taggingMap)

    self._storageThread = threading.Thread(
      target=TweetStorer.runInThread,
      kwargs=storageThreadKwargs)
    self._storageThread.setDaemon(True)
    self._storageThread.start()

    # Stream
    self._stream = tweepy.Stream(self._authHandler, self)

    g_log.info("Filtering via params=%s", self._streamFilterParams)

    # See https://dev.twitter.com/streaming/reference/post/statuses/filter
    self._stream.filter(**self._streamFilterParams)

    msg = "%s exited unexpectedly" % (self._stream.__class__.__name__)
    g_log.error(msg)
    raise RuntimeError(msg)



class TweetStorer(object):
  """ This class is responsible to dequeueing messages from
  TwitterStreamListener and saving them in the database
  """

  _MAX_SAVED_TEXT_LEN = 2000


  class _StreamingStatsBase(object):
    def __init__(self):
      # Count of tweets recevied from API
      self.numTweets = 0

      # Count of tweets from current stream that didn't match our tagging logic
      self.numUntaggedTweets = 0

      # Count of "delete" statuses
      self.numDeleteStatuses = 0

      # Count of "limit" statuses
      self.numLimitStatuses = 0

      # Count of rate-limited tweets as reaped from  "limit" statuses
      self.numLimitedTweets = 0

      # Count of "disconnect" statuses
      self.numDisconnectStatuses = 0

      # Count of "warning" statuses
      self.numWarningStatuses = 0

      # Count of other statuses
      self.numOtherStatuses = 0


    def __str__(self):
      return (
        "rxTweets=%(rxTweets)d; untagged=%(untagged)d (%(untaggedPct).1f%%); "
        "delete=%(delete)d; limit=%(limit)d; "
        "limitedTweets=%(limitedTweets)d (%(limitedTweetsPct).1f%%); "
        "disconnect=%(disconnect)d; warning=%(warning)d; other=%(other)d"
        % dict(
          rxTweets=self.numTweets,
          untagged=self.numUntaggedTweets,
          untaggedPct=_percentage(self.numUntaggedTweets, self.numTweets),
          delete=self.numDeleteStatuses,
          limit=self.numLimitStatuses,
          limitedTweets = self.numLimitedTweets,
          limitedTweetsPct = _percentage(
            self.numLimitedTweets,
            self.numTweets + self.numLimitedTweets),
          disconnect=self.numDisconnectStatuses,
          warning=self.numWarningStatuses,
          other=self.numOtherStatuses)
        )


  class _CurrentStreamStats(_StreamingStatsBase):
    def __init__(self):
      super(TweetStorer._CurrentStreamStats, self).__init__()

      # Starting datetime of the current stream
      self.startingDatetime = None

    def __str__(self):
      return "%s; started=%s" % (
        super(TweetStorer._CurrentStreamStats, self).__str__(),
        (self.startingDatetime.replace(microsecond=0).isoformat()
         if self.startingDatetime else None),)


  class _RuntimeStreamingStats(_StreamingStatsBase):
    def __init__(self):
      super(TweetStorer._RuntimeStreamingStats, self).__init__()

      # 1-based number of the current stream
      self.streamNumber = None

    def __str__(self):
      return "%s; streamNumber=%s" % (
        super(TweetStorer._RuntimeStreamingStats, self).__str__(),
        self.streamNumber,)


  def __init__(self, taggingMap, aggSec, msgQ, echoData):
    """
    :param taggingMap: tweet tagging map as returned by
      `buildTaggingMapAndStreamFilterParams()`
    :param int aggSec: metric aggregation period in seconds
    :param Queue.Queue msgQ: input messages queue receiving messages from our
      TwitterStreamListener
    :param bool echoData: wheter we should log incoming messages
    """
    self._taggingMap = taggingMap
    self._aggSec = aggSec
    self._msgQ = msgQ
    self._echoData = echoData

    self._sqlEngine = collectorsdb.engineFactory()

    # Streaming stats of current stream
    self._currentStreamStats = None

    # Overall runtime streaming stats
    self._runtimeStreamingStats = self._RuntimeStreamingStats()


  @classmethod
  @logExceptions(g_log)
  def runInThread(cls, taggingMap, aggSec, msgQ, echoData):
    """ The thread target function; instantiates and runs TweetStorer

    :param taggingMap: tweet tagging map as returned by
      `buildTaggingMapAndStreamFilterParams()`
    :param int aggSec: metric aggregation period in seconds
    :param Queue.Queue msgQ: input messages queue receiving messages from our
      TwitterStreamListener
    :param bool echoData: wheter we should log incoming messages
    """
    g_log.info("%s thread is running", cls.__name__)
    tweetStorer = cls(taggingMap=taggingMap,
                      aggSec=aggSec,
                      msgQ=msgQ,
                      echoData=echoData)
    tweetStorer._run()


  def _run(self):
    """ Thread function; preprocess and store incoming tweets deposited by
    twitter streamer into self._msgQ
    """
    # Get time reference for calculating aggregation timestamps
    aggRefDatetime = metric_utils.establishLastEmittedSampleDatetime(
      key=_EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY,
      aggSec=self._aggSec)

    statsIntervalSec = 600
    nextStatsUpdateEpoch = time.time()

    maxBatchSize = 100
    while True:
      # Accumulate batch of incoming messages for SQL insert performance
      messages = []
      while len(messages) < maxBatchSize:
        # Get the next incoming message
        timeout = 0.5 if messages else None
        try:
          msg = self._msgQ.get(timeout=timeout)
        except Queue.Empty:
          break
        else:
          g_log.debug("%s: got msg=%s", self.__class__.__name__, msg)
          messages.append(msg)

      # Process the batch
      tweets = deletes = None
      try:
        tweets, deletes = self._reapMessages(messages)
      except Exception:
        g_log.exception("_reapMessages failed")
        pass

      # Save (re)tweets
      if tweets:
        try:
          self._saveTweets(messages=tweets, aggRefDatetime=aggRefDatetime)
        except Exception:
          g_log.exception("Failed to save numTweets=%d", len(tweets))
          pass

      # Save deletion requests
      if deletes:
        try:
          self._saveTweetDeletionRequests(messages=deletes)
        except Exception:
          g_log.exception("Failed to save deletion numRequests=%d",
                          len(deletes))
          for msg in deletes:
            g_log.error("Failed to save deletion msg=%s", msg)
          pass

      # Echo messages to stdout if requested
      if self._echoData:
        for msg in messages:
          print pprint.pformat(msg)
        sys.stdout.flush()

      # Print stats
      now = time.time()
      if now >= nextStatsUpdateEpoch:
        nextStatsUpdateEpoch = now + statsIntervalSec
        self._logStreamStats()


  def _logStreamStats(self):
    g_log.info("Current stream stats: %s", self._currentStreamStats)

    g_log.info("Runtime streaming stats: %s", self._runtimeStreamingStats)


  def _reapMessages(self, messages):
    """ Process the messages from TwitterStreamListener and update stats; they
    could be (re)tweets or notifications, such as "limit", "delete", "warning",
    etc., or other meta information, such as ConnectionMarker that indicates a
    newly-created Streaming API connection.

    See https://dev.twitter.com/streaming/overview/messages-types

    Tweets that match one or more metrics and delete notifications are returned
    to caller. Other notifications of interest are logged.

    :param messages: messages received from our TwitterStreamListener
    :type messages: sequence of JSON strings representing twitter statuses
      and/or TwitterStreamListener.ConnectionMarker

    :returns: a pair (tweets, deletes), where `tweets` is a possibly empty
      sequence of tweet status dicts each matching at least one metric and
      tagged via `TweetStorer._tagMessage()`; and `deletes` is a possibly empty
      sequence of "delete" notification dicts representing tweet statuses to be
      deleted.

    Additional candidate status types that may be of interest:
      user_withheld
      status_withheld
    """
    streamStats = self._currentStreamStats
    runtimeStats = self._runtimeStreamingStats

    tweets = []
    deletes = []
    for msg in messages:
      if isinstance(msg, basestring):
        # Got Twitter Status
        try:
          msg = json.loads(msg)
        except ValueError:
          # Sometimes we get an incomplete message when Twitter stream closes
          g_log.exception("Decoding failure of twitter message=%r", msg)
          continue

        if "in_reply_to_status_id" in msg:
          # Got a tweet of some sort
          streamStats.numTweets += 1
          runtimeStats.numTweets += 1

          # Tag tweet with metric names that match it, if any
          self._tagMessage(msg)

          if msg["metricTagSet"]:
            # Matched one or more metrics
            tweets.append(msg)
          else:
            # It didn't match any metrics
            streamStats.numUntaggedTweets += 1
            runtimeStats.numUntaggedTweets += 1

        elif "delete" in msg:
          deletes.append(msg)
          streamStats.numDeleteStatuses += 1
          runtimeStats.numDeleteStatuses += 1

        elif "limit" in msg:
          g_log.warning("Received Twitter LIMIT message=%s", msg)
          streamStats.numLimitStatuses += 1
          runtimeStats.numLimitStatuses += 1
          limit = msg["limit"]
          track = limit.get("track")
          if track is None:
            g_log.error("Twitter LIMIT message missing track value: %s", msg)
          elif track > streamStats.numLimitedTweets:
            # NOTE: we frequently see these arriving out of order, hence the
            # check
            runtimeStats.numLimitedTweets += (track -
                                              streamStats.numLimitedTweets)
            streamStats.numLimitedTweets = track

        elif "disconnect" in msg:
          g_log.error("Received Twitter DISCONNECT message=%s", msg)
          streamStats.numDisconnectStatuses += 1
          runtimeStats.numDisconnectStatuses += 1

        elif "warning" in msg:
          g_log.warning("Received Twitter WARNING message=%s", msg)
          streamStats.numWarningStatuses += 1
          runtimeStats.numWarningStatuses += 1

        else:
          g_log.warning("Streamed unexpected message=%s",
                        str(msg)[:100])
          streamStats.numOtherStatuses += 1
          runtimeStats.numOtherStatuses += 1

      elif msg is TwitterStreamListener.ConnectionMarker:
        # Got connection establishment notification
        if self._runtimeStreamingStats.streamNumber is not None:
          self._logStreamStats()

        g_log.info("%s: got connection marker", self.__class__.__name__)

        self._currentStreamStats = self._CurrentStreamStats()
        self._currentStreamStats.startingDatetime = datetime.utcnow()
        streamStats = self._currentStreamStats

        if self._runtimeStreamingStats.streamNumber is None:
          self._runtimeStreamingStats.streamNumber = 1
        else:
          self._runtimeStreamingStats.streamNumber += 1
      else:
        errorMsg = "Unexpected message from listener: %r" % (msg,)
        g_log.error(errorMsg)
        raise RuntimeError(errorMsg)

    return tweets, deletes


  def _tagMessage(self, msg):
    """ Tag message: add "metricTagSet" attribute to the message; the value
    of "metricTagSet" is a possibly-empty set containing metric name(s) that
    match the containing message.

    :param dict msg: Twitter status object
    """
    msg["metricTagSet"] = set()
    for tagger, mappings in self._taggingMap.iteritems():
      try:
        tagger(msg, mappings)
      except Exception:
        g_log.exception("Tagging failed on msg=%s", pprint.pformat(msg))
        raise


  @classmethod
  def _truncateText(cls, text):
    """ Truncate given text string to _MAX_SAVED_TEXT_LEN
    """
    if text is not None and len(text) > cls._MAX_SAVED_TEXT_LEN:
      text = text[:cls._MAX_SAVED_TEXT_LEN]

    return text


  @classmethod
  def _sanitizeTextForDb(cls, text):
    """ Truncate and sanitize text to make it suitable for storing in mysql """
    if text is None:
      return text

    text = cls._truncateText(text)

    # NOTE: this is necessiated by lack of support for 4-byte code points
    # in mysql < v5.5.3 that is deployed on our initial
    # tauruspoc.collectors.numenta.com
    text = sanitize4ByteUnicode(text)

    return text


  def _createTweetAndReferenceRows(self, msg, aggRefDatetime):
    """ Generate a tweet row and corresponding reference rows from a tagged
    tweet for saving to the database (some tweets may match multiple metrics)

    :param msg: a tweet dict received from twitter with an additional
      "metricTagSet" attribute; the value of "metricTagSet" is a set containing
      metric name(s) that match the containing message
    :param datetime aggRefDatetime: aggregation reference time for determining
      aggregation timestamp of the given messages

    :returns: a two-tuple (<tweet_row>, <reference_rows>)
      tweet_row: a dict representing the tweet row for inserting into
        schema.twitterTweets
      reference_rows: a sequence of dicts representing tweet reference rows for
        inserting into schema.twitterTweetSamples

    Additional candidate fields:
      coordinates
        If saving coordinates, then must also honor "Location deletion notices
        (scrub_geo)" per
        https://dev.twitter.com/streaming/overview/messages-types
      favorite_count (most likely not useful in this context, since subsequent
        (un)favoriting would not be udpated in the db so the value will often be
        way off.
      retweet_count (same concern as with favorite_count)
      retweeted_status (original tweet inside retweet; perhaps this may be used
        to update retweet_count in the original, and even save it as original in
        case we didn't already have it; *not helpful for updating
        favorite_count, since something may be (un)favorited without being
        retweted)
      truncated
      withheld_copyright, withheld_in_countries, withheld_scope: it turns out
        that content may be withheld due to DMCA complaint in certain countries
        or everywhere. *We also need to figure out whether we need to abide by
        this in Taurus Client; if we do, then we need to start handling
        "withheld content notices" described in
        https://dev.twitter.com/streaming/overview/messages-types; also, the doc
        doesn't shed light whether/how "unwithholding" is communicated (empty
        country list?)
    """
    msgId = msg["id_str"]
    retweetedStatus = msg.get("retweeted_status")
    isRetweet = (retweetedStatus is not None)
    createdAt = datetime.strptime(msg["created_at"],
                                  "%a %b %d %H:%M:%S +0000 %Y")
    contributors = msg.get("contributors")

    tweetRow = dict(
      uid=msgId,
      created_at=createdAt,
      retweet=isRetweet,
      lang=msg.get("lang"),
      text=self._sanitizeTextForDb(msg.get("text")),
      userid=msg["user"]["id_str"],
      username=msg["user"]["screen_name"],
      real_name=msg["user"]["name"],
      retweeted_status_id=(
        retweetedStatus["id_str"] if isRetweet else None),
      retweet_count=(
        retweetedStatus["retweet_count"] if isRetweet else None),
      retweeted_userid=(
        retweetedStatus["user"]["id_str"] if isRetweet else None),
      retweeted_username=(
        retweetedStatus["user"]["screen_name"] if isRetweet else None),
      retweeted_real_name=(
        retweetedStatus["user"]["name"] if isRetweet else None),
      in_reply_to_status_id=msg.get("in_reply_to_status_id_str"),
      in_reply_to_userid=msg.get("in_reply_to_user_id_str"),
      in_reply_to_username=msg.get("in_reply_to_screen_name"),
      contributors=(
        json.dumps(contributors) if contributors is not None else None)
    )

    # Compute aggregation timestamp as the lower aggregation boundary relative
    # to the given reference (required by Taurus-Mobile)
    aggDatetime = metric_utils.aggTimestampFromSampleTimestamp(
      sampleDatetime=createdAt,
      aggRefDatetime=aggRefDatetime,
      aggSec=self._aggSec)

    referenceRows = [
      dict(metric=metric, msg_uid=msgId, agg_ts=aggDatetime)
      for metric in msg["metricTagSet"]
    ]

    return (tweetRow, referenceRows)


  def _saveTweets(self, messages, aggRefDatetime):
    """ Save tweets and references in database

    See https://dev.twitter.com/overview/api/tweets

    :param messages: sequence of tweet dict received from twitter with an
      additional "metricTagSet" attribute; the value of "metricTagSet" is a set
      containing metric name(s) that match the containing message
    :param datetime aggRefDatetime: aggregation reference time for determining
      aggregation timestamp of the given messages
    """
    tweetRows = []
    referenceRows = []
    for msg in messages:
      try:
        tweet, references = self._createTweetAndReferenceRows(msg,
                                                              aggRefDatetime)
      except Exception:
        g_log.exception("Failed to reap tweet=%s", msg)
      else:
        tweetRows.append(tweet)
        referenceRows.extend(references)

    g_log.debug("tweetRows=%s, referenceRows=%s", tweetRows, referenceRows)

    @collectorsdb.retryOnTransientErrors
    def saveWithRetries():
      # NOTE: we use "IGNORE" to avoid errors due to occasional duplicate tweets
      # from twitter stream
      with self._sqlEngine.begin() as conn:
        # Save twitter message
        conn.execute(
          schema.twitterTweets.insert(  # pylint: disable=E1120
            ).prefix_with("IGNORE", dialect="mysql"),
          tweetRows)

        # Save corresponding references
        # NOTE: some tweets may match multiple metrics
        conn.execute(
          schema.twitterTweetSamples.insert(  # pylint: disable=E1120
            ).prefix_with("IGNORE", dialect="mysql"),
          referenceRows)

    saveWithRetries()


  def _saveTweetDeletionRequests(self, messages):
    """ Save tweet deletion request in database

    :param messages: sequence of Twitter "delete" status dicts
      https://dev.twitter.com/streaming/overview/messages-types
    """
    # Compose rows for schema.twitterDeletion
    deletionRows = []
    for msg in messages:
      deletionStatus = msg["delete"].get("status")
      if deletionStatus:
        deletionRows.append(
          dict(tweet_uid=deletionStatus["id_str"],
               userid=deletionStatus["user_id_str"]))
      else:
        g_log.error("Missing status in delete msg=%s", msg)


    # Save the rows

    @collectorsdb.retryOnTransientErrors
    def saveWithRetries():
      with self._sqlEngine.begin() as conn:
        ins = schema.twitterDeletion.insert(  # pylint: disable=E1120
          ).prefix_with('IGNORE', dialect="mysql")

        conn.execute(ins, deletionRows)

    saveWithRetries()

    for row in deletionRows:
      g_log.info("Saved tweet deletion request=%s", row)


class TweetForwarder(object):
  """ This class is responsible for forwarding tweets """

  # RabbitMQ Topic Exchange for publishing non-metric (e.g., tweets)
  _NON_METRIC_EXCHANGE = "taurus.data.non-metric"

  # Routing Key for publishing tweets to the non-metric exchange
  _TWEET_NON_METRIC_ROUTING_KEY = "taurus.data.non-metric.twitter"

  # AMQP Basic Properties for publishing tweets on message bus
  _TWEET_BASIC_AMQP_PROPERTIES = MessageProperties(
    deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE)

  # Sleep duration between forwarding cycles
  _SLEEP_SEC = 5


  def __init__(self):
    self._sqlEngine = collectorsdb.engineFactory()


  @classmethod
  @abortProgramOnAnyException(exitCode=1, logger=g_log)
  def runInThread(cls):
    """ The thread target function; instantiates and runs MetricDataForwarder

    :param metricSpecs: sequence of TwitterMetricSpec
    :param int aggSec: metric aggregation period in seconds
    """
    g_log.info("%s thread is running", cls.__name__)
    cls()._run()


  def _run(self):
    """ Run the main loop responsible for forwarding tweets
    """
    # Bootstrap non-metric forwarding state
    lastForwardedSeq = metric_utils.queryLastEmittedNonMetricSequence(
      _EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY)
    if lastForwardedSeq is not None:
      g_log.info("On startup: existing non-metric lastForwardedSeq=%d",
                 lastForwardedSeq)
    else:
      # The non-metric forwarding feature is deployed for the first time, so
      # configure non-metric forwarding to start with new data;
      #
      # NOTE: we rely on the migrate_tweets_to_dynamodb.py tool for the initial
      # forwarding of the backlog, so we don't bother with that here
      @collectorsdb.retryOnTransientErrors
      def queryMaxSeq():
        sel = sql.select([sql.func.max(schema.twitterTweetSamples.c.seq)])
        return self._sqlEngine.execute(sel).scalar()

      maxSeq = queryMaxSeq()
      if maxSeq is None:
        # Table is empty
        maxSeq = 0 # the real sequence begins at 1

      # Save it as the last emitted non-metric sequence
      metric_utils.updateLastEmittedNonMetricSequence(
        _EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY,
        maxSeq)

      g_log.info("On startup: established new non-metric lastForwardedSeq=%d",
                 maxSeq)


    # Run the forwarding loop
    with MessageBusConnector() as messageBus:
      while True:
        self._forwardTweetsViaRabbitmq(messageBus)

        time.sleep(self._SLEEP_SEC)


  def _forwardTweetsViaRabbitmq(self, messageBus):
    """ Forward all unforwarded tweets to non-metric data exchange
    :param messageBus: message bus connection
    :type messageBus: nta.utils.message_bus_connector.MessageBusConnector
    """
    batchSizeLimit = 100

    # Find out where to resume forwarding
    lastForwardedSeq = metric_utils.queryLastEmittedNonMetricSequence(
      _EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY)
    if lastForwardedSeq is None:
      # This should have been bootstrapped already
      raise Exception("Last emitted non-metric sequence not bootstrapped!")

    while True:
      # Load and build a batch of tweet items conforming to the interface
      # defined by Taurus's dynamodb_service
      lastForwardedSeq, batch = self.queryNonMetricTweetBatch(
        sqlEngine=self._sqlEngine,
        minSeq=lastForwardedSeq + 1,
        maxItems=batchSizeLimit)

      if not batch:
        # No more rows - done!
        break

      # Forward the batch
      self.publishNonMetricTweetBatch(messageBus, batch)

      # Update the last-forwarded sequence number
      metric_utils.updateLastEmittedNonMetricSequence(
        _EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY,
        lastForwardedSeq)

      g_log.info("Forwarded numTweets=%d ending with seq=%d",
                 len(batch), lastForwardedSeq)


  @classmethod
  def queryNonMetricTweetBatch(cls, sqlEngine, minSeq, maxItems=None,
                               maxSeq=None, metrics=None):
    """ Query a batch of non-metric twitter items for forwarding

    NOTE: Also used by migrate_tweets_to_dynamodb.py script

    :param sqlalchemy.engine.Engine sqlEngine:
    :param int minSeq: Minimum schema.twitterTweetSamples sequence number for
      filtering results
    :param int maxItems: OPTIONAL Upper bound on number of items to return;
      unbound if None
    :param int maxSeq: OPTIONAL Maximum schema.twitterTweetSamples sequence
      number for filtering results; unbound if None
    :param metrics: optional sequence of metric names; if specified (not None),
      the query will be further limited to tweets corresponding to the given
      metric names.

    :returns: a two-tuple (<last seq>, <items>); (None, None) if there are no
      rows in the requested range; otherwise <last seq> is the sequence number
      corresponding to the last item in <items> or None if the returned sequence
      of items is empty; and <items> is a sequence of dicts conforming to the
      schema required by Taurus's dynamodb_service consumer per
      taurus/metric_collectors/twitterdirect/tweet_export_schema.json
    """
    tweetsSchema = schema.twitterTweets
    samplesSchema = schema.twitterTweetSamples
    fields = [
      samplesSchema.c.metric,
      samplesSchema.c.agg_ts,
      samplesSchema.c.seq,
      tweetsSchema.c.uid,
      tweetsSchema.c.created_at,
      tweetsSchema.c.text,
      tweetsSchema.c.username,
      tweetsSchema.c.userid,
      tweetsSchema.c.retweet_count
    ]

    join = samplesSchema.join(
      tweetsSchema,
      samplesSchema.c.msg_uid == tweetsSchema.c.uid)

    sel = sql.select(fields
      ).select_from(join
      ).where(samplesSchema.c.seq >= minSeq
      ).order_by(samplesSchema.c.seq.asc())

    if metrics is not None:
      sel = sel.where(schema.twitterTweetSamples.c.metric.in_(metrics))

    if maxSeq is not None:
      sel = sel.where(samplesSchema.c.seq <= maxSeq)

    if maxItems is not None:
      sel = sel.limit(maxItems)

    @collectorsdb.retryOnTransientErrors
    def queryWithRetries():
      return sqlEngine.execute(sel).fetchall()

    rows = queryWithRetries()
    if not rows:
      # No rows in requested range
      return (None, None)

    # Build a batch of tweet items conforming to the interface defined by
    # Taurus's dynamodb_service
    items = [
      {
        "metric_name": row.metric,
        "tweet_uid": row.uid,
        "created_at": row.created_at.isoformat(),
        "agg_ts": row.agg_ts.isoformat(),
        "text": row.text,
        "userid": row.userid,
        "username": row.username,
        "retweet_count": row.retweet_count
      }
      for row in rows
      if row.created_at and row.agg_ts
    ]

    return (rows[-1].seq, items)


  @classmethod
  def publishNonMetricTweetBatch(cls, messageBus, batch):
    """ Publish non-metric tweet batch via RabbitMQ

    :param messageBus: message bus connection
    :type messageBus: nta.utils.message_bus_connector.MessageBusConnector
    :param batch: sequence of dicts as returned by cls.queryNonMetricTweetBatch
    """
    delivered = messageBus.publishExg(
      exchange=cls._NON_METRIC_EXCHANGE,
      routingKey=cls._TWEET_NON_METRIC_ROUTING_KEY,
      body=json.dumps(batch),
      properties=cls._TWEET_BASIC_AMQP_PROPERTIES)
    if not delivered:
      g_log.error("Failed to deliver message to exchange=%s; routing_key=%s",
                  cls._NON_METRIC_EXCHANGE, cls._TWEET_NON_METRIC_ROUTING_KEY)



class MetricDataForwarder(object):
  """ This class is responsible for aggregating and forwarding metric data """

  def __init__(self, metricSpecs, aggSec):
    self._metricSpecs = metricSpecs
    self._aggSec = aggSec

    self._sqlEngine = collectorsdb.engineFactory()


  @classmethod
  @abortProgramOnAnyException(exitCode=1, logger=g_log)
  def runInThread(cls, metricSpecs, aggSec):
    """ The thread target function; instantiates and runs MetricDataForwarder

    :param metricSpecs: sequence of TwitterMetricSpec
    :param int aggSec: metric aggregation period in seconds
    """
    g_log.info("%s thread is running", cls.__name__)
    cls(metricSpecs, aggSec)._run()


  def _run(self):
    """ Run the main loop responsible for aggregation and forwarding
    """
    aggSec = self._aggSec

    # Bootstrap metric data forwarding state
    lastEmittedAggTime = metric_utils.establishLastEmittedSampleDatetime(
      key=_EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY,
      aggSec=aggSec)

    # Calculate next aggregation end time using lastEmittedAggTime as base
    #
    # NOTE: an aggregation timestamp is the time of the beginning of the
    # aggregation window
    nextAggEndEpoch = (
      date_time_utils.epochFromNaiveUTCDatetime(lastEmittedAggTime) +
      aggSec + aggSec)

    # Fudge factor to account for streaming and processing latencies upstream
    latencyAllowanceSec = aggSec

    while True:
      # Sleep until it's time to aggregate metric data
      aggHarvestEpoch = nextAggEndEpoch + latencyAllowanceSec
      now = time.time()
      while now < aggHarvestEpoch:
        time.sleep(aggHarvestEpoch - now)
        now = time.time()

      # Aggregate and forward metric samples to htmengine's Metric Listener
      lastEmittedAggTime = self._forwardTweetVolumeMetrics(
        lastEmittedAggTime=lastEmittedAggTime,
        stopDatetime=datetime.utcfromtimestamp(nextAggEndEpoch))

      nextAggEndEpoch += aggSec


  def aggregateAndForward(self, aggStartDatetime, stopDatetime, metrics=None):
    """ Aggregate tweet volume metrics in the given datetime range and forward
    them to Taurus Engine.

    NOTE: this may be called by tooling, such as `resymbol_metrics.py`

    NOTE: does not updateLastEmittedSampleDatetime

    :param datetime aggStartDatetime: UTC datetime of first aggregation to be
      performed and emitted
    :param datetime stopDatetime: non-inclusive upper bound UTC datetime for
      forwarding
    :param metrics: optional sequence of metric names; if specified (non-None),
      the operation will be limited to the given metric names
    """
    def getSamples(aggStartDatetime):
      """Retrieve and yield metric data samples of interest"""
      periodTimedelta = timedelta(seconds=self._aggSec)

      while aggStartDatetime < stopDatetime:
        # Query Tweet Volume metrics for one aggregation interval
        metricToVolumeMap = defaultdict(
          int,
          self._queryTweetVolumes(aggStartDatetime, metrics))

        # Generate metric samples
        epochTimestamp = date_time_utils.epochFromNaiveUTCDatetime(
          aggStartDatetime)

        samples = tuple(
          dict(
            metricName=spec.metric,
            value=metricToVolumeMap[spec.metric],
            epochTimestamp=epochTimestamp)
          for spec in self._metricSpecs
          if metrics is None or spec.metric in metrics
        )

        if g_log.isEnabledFor(logging.DEBUG):
          g_log.debug("samples=%s", pprint.pformat(samples))

        for sample in samples:
          yield sample

        g_log.info("Yielded numSamples=%d for agg=%s",
                   len(samples), aggStartDatetime)

        # Set up for next iteration
        aggStartDatetime += periodTimedelta


    # Emit samples to Taurus Engine
    with metric_utils.metricDataBatchWrite(log=g_log) as putSample:
      for sample in getSamples(aggStartDatetime):
        try:
          putSample(**sample)
        except Exception:
          g_log.exception("Failure while emitting metric data sample=%s",
                          sample)
          raise


  def _forwardTweetVolumeMetrics(self, lastEmittedAggTime, stopDatetime):
    """ Query tweet volume metrics since the given last emitted aggregation time
    through stopDatetime and forward them to Taurus. Update
    the datetime of the last successfully-emitted tweet volume metric batch in
    the database.

    NOTE: Upon failure during forwarding, an error will be logged, and the
      function will return the UTC timestamp of the last successfully-emitted
      sample aggregation interval. Once destination comes online, a subsequent
      call to this function will catch up by forwarding the stored samples since
      last successful emission.

    :param datetime lastEmittedAggTime: UTC datetime of most recent
      successfully-emitted sample aggregation batch
    :param datetime stopDatetime: non-inclusive upper bound UTC datetime for
      forwarding

    :returns: UTC timestamp of the latest successfully-emitted aggregation
      batch.
    :rtype: datetime.datetime
    """
    periodTimedelta = timedelta(seconds=self._aggSec)
    aggStartDatetime = lastEmittedAggTime + periodTimedelta

    while aggStartDatetime < stopDatetime:
      # Aggregate and forward Tweet Volume metrics for one aggregation interval
      try:
        self.aggregateAndForward(
          aggStartDatetime=aggStartDatetime,
          stopDatetime=aggStartDatetime + periodTimedelta)
      except Exception:
        return lastEmittedAggTime

      # Update db with last successfully-emitted datetime
      metric_utils.updateLastEmittedSampleDatetime(
        key=_EMITTED_TWEET_VOLUME_SAMPLE_TRACKER_KEY,
        sampleDatetime=aggStartDatetime)

      # Set up for next iteration
      lastEmittedAggTime = aggStartDatetime
      aggStartDatetime += periodTimedelta


    return lastEmittedAggTime


  @collectorsdb.retryOnTransientErrors
  def _queryTweetVolumes(self, aggDatetime, metrics):
    """ Query the database for the counts of tweet metric volumes for the
    specified aggregation.

    :param datetime aggDatetime: aggregation timestamp
    :param metrics: optional sequence of metric names; if specified (non-None),
      the operation will be limited to the given metric names
    :returns: a sparse sequence of two-tuples: (metric_name, count); metrics
      that have no tweets in the given aggregation period will be absent from
      the result.
    """
    sel = sql.select(
        [schema.twitterTweetSamples.c.metric, sql.func.count()]
      ).where(schema.twitterTweetSamples.c.agg_ts == aggDatetime
      ).group_by(schema.twitterTweetSamples.c.metric)

    if metrics is not None:
      sel = sel.where(schema.twitterTweetSamples.c.metric.in_(metrics))

    return self._sqlEngine.execute(sel).fetchall()



def _parseArgs():
  """
  :returns: dict of arg names and values:
    numPartitions
    aggPeriod
    consumerKey
    consumerSecret
    accessToken
    accessTokenSecret
    forwardNonMetric
    echoData
  """
  helpString = (
    "%prog [options]"
    "This fetches twitter messages directly from twitter and sends message "
    "volume to YOMP server as custom metrics. Metric configuration is in "
    "conf/metrics.json.")

  parser = OptionParser(helpString)

  parser.add_option(
      "--partitions",
      action="store",
      type="int",
      dest="numPartitions",
      default=1,
      help=("The list of companies will be partitioned into this many parts. "
            "Each partition will be serviced by an individual stream listener. "
            "At this time, it appears that Twitter allows MAX of TWO listeners "
            "PER ACCOUNT. NOTE: if you start seeing 'ERROR: 420' in the log, "
            "it's a sure sign that there are too many streamers on the same "
            "account. [default: %default]"))

  parser.add_option(
      "--period",
      action="store",
      type="int",
      dest="aggPeriod",
      default=300,
      help="Volume aggregation period in seconds [default: %default]")

  parser.add_option(
      "--ckey",
      action="store",
      type="string",
      dest="consumerKey",
      default=DEFAULT_CONSUMER_KEY,
      help=("Twitter consumer key; overrides environment variable "
            "TAURUS_TWITTER_CONSUMER_KEY [default: %default]"))

  parser.add_option(
      "--csecret",
      action="store",
      type="string",
      dest="consumerSecret",
      default=DEFAULT_CONSUMER_SECRET,
      help=("Twitter consumer secret; overrides environment variable "
            "TAURUS_TWITTER_CONSUMER_SECRET [default: %default]"))

  parser.add_option(
      "--atoken",
      action="store",
      type="string",
      dest="accessToken",
      default=DEFAULT_ACCESS_TOKEN,
      help=("Twitter access token; overrides environment variable "
            "TAURUS_TWITTER_ACCESS_TOKEN [default: %default]"))

  parser.add_option(
      "--atokensecret",
      action="store",
      type="string",
      dest="accessTokenSecret",
      default=DEFAULT_ACCESS_TOKEN_SECRET,
      help=("Twitter access token secret; overrides environment variable "
            "TAURUS_TWITTER_ACCESS_TOKEN_SECRET [default: %default]"))

  parser.add_option(
      "--forward-non-metric",
      action="store_true",
      default=False,
      dest="forwardNonMetric",
      help=("Forward non-metric data; applies only in active op-mode "
            "[default: %default]"))

  parser.add_option(
      "--echodata",
      action="store_true",
      default=False,
      dest="echoData",
      help=("Echo processed Twitter messages to stdout for debugging "
            "[default: %default]"))

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if not 0 < options.numPartitions <= 2:
    parser.error("Number of partitions must be either 1 or 2, but got %s" %
                 options.numPartitions)

  return dict(
    numPartitions=options.numPartitions,
    aggPeriod=options.aggPeriod,
    consumerKey=options.consumerKey,
    consumerSecret=options.consumerSecret,
    accessToken=options.accessToken,
    accessTokenSecret=options.accessTokenSecret,
    forwardNonMetric=options.forwardNonMetric,
    echoData=options.echoData)


def _partition(l, numParts):
  """ Partition a sequence into the given number of parts. The last
  partition will get any of the leftovers.

  :param sequence l:
  :param int numParts:
  :returns: tuple of sequences
  """
  size = len(l) / numParts
  partitions = tuple(
    list(islice(l, i * size, (i + 1) * size)) for i in xrange(numParts))

  partitions[-1].extend(l[size * numParts:])

  return partitions



@logExceptions(g_log)
def _runStreamWorker(task):
  """ Run the pool worker; called in a multiprocessing pool process"""
  try:
    g_log.info("TwitterStreamListener pool worker started; numMetrics=%d",
               len(task["metricSpecs"]))
    TwitterStreamListener(**task).run()
  except KeyboardInterrupt:
    # Normal exit in response to SIGINT
    g_log.info("KeyboardInterrupt detected, exiting", exc_info=True)
    raise
  except:
    g_log.exception("Something bad happened")
    raise Exception("ERROR in stream worker with pid=%s" % os.getpid())



@abortProgramOnAnyException(exitCode=1, logger=g_log)
def _runPoolThread(pool, tasks):
  # Stream data
  g_log.info("Submitting numTasks=%d to multiprocessing pool", len(tasks))

  for result in pool.imap_unordered(_runStreamWorker, tasks, 1):
    # NOTE: We should never get here - the workers should work tirelessly
    # forever. If a worker exits with an exception, that exception will be
    # carried over into the main process by imap_unordered.
    raise RuntimeError("Unexpected termination of pool worker; result=%r"
                       % result)


def main():
  """
  NOTE: main also serves as the entry point for the "console script" generated
  by setup
  """
  logging_support.LoggingSupport.initService()

  try:
    try:
      options = _parseArgs()
    except SystemExit as e:
      if e.code == 0:
        # Suppress exception logging when exiting due to --help
        return

      raise

    opMode = config.get("twitter_direct_agent", "opmode")

    g_log.info("Starting TwitterStreamListener(s) with options=%r", options)

    metricSpecs = loadMetricSpecs()

    # Start forwarders
    metricDataForwarderThread = None
    tweetForwarderThread = None
    if opMode == config.OP_MODE_ACTIVE:
      # Start Metric Data Forwarder
      metricDataForwarderThread = threading.Thread(
        target=MetricDataForwarder.runInThread,
        kwargs=dict(metricSpecs=metricSpecs,
                    aggSec=options["aggPeriod"]))
      metricDataForwarderThread.setDaemon(True)
      metricDataForwarderThread.start()
      g_log.info("Started MetricDataForwarder thread")

      # Start Tweet Forwarder
      if options["forwardNonMetric"]:
        tweetForwarderThread = threading.Thread(
          target=TweetForwarder.runInThread)
        tweetForwarderThread.setDaemon(True)
        tweetForwarderThread.start()
        g_log.info("Started TweetForwarder thread")


    numPartitions = options["numPartitions"]
    metricPartitions = _partition(metricSpecs, numPartitions)

    assert len(metricPartitions) == numPartitions, (
      len(metricPartitions), numPartitions)
    assert len(metricSpecs) == sum(len(part) for part in metricPartitions)

    # Create a process pool with number of processes equal to the number of
    # partitions
    taskOptions = dict(options.iteritems())
    taskOptions.pop("numPartitions")
    taskOptions.pop("forwardNonMetric")

    tasks = [
      dict(
        [["metricSpecs", part]] + taskOptions.items())
      for part in metricPartitions
    ]

    g_log.info("Creating multiprocessing pool with numWorkers=%d", len(tasks))
    workerPool = multiprocessing.Pool(processes=len(tasks))
    try:
      # NOTE: we run workerPool.imap_unordered from a thread because the Pool
      # is otherwise somehow interfering with the processing of SIGINT and our
      # process just hangs when supervisord tries to shut it down.
      poolRunnerThread = threading.Thread(
        target=_runPoolThread,
        kwargs=dict(pool=workerPool, tasks=tasks))
      poolRunnerThread.setDaemon(True)
      poolRunnerThread.start()
      g_log.info("Started Pool Runner thread")

      # Wait for it to exit, which it never should
      while True:
        # Passing a timeout value allows the join call to be interrupted by
        # SIGINT, which results in KeyboardInterrupt exception.
        poolRunnerThread.join(60)
        assert poolRunnerThread.is_alive()

        if metricDataForwarderThread is not None:
          metricDataForwarderThread.join(60)
          assert metricDataForwarderThread.is_alive()

        if tweetForwarderThread is not None:
          tweetForwarderThread.join(60)
          assert tweetForwarderThread.is_alive()
    finally:
      # Terminate worker pool. There is no point in trying to close it because
      # our tasks never complete
      g_log.info("Terminating multiprocessing.Pool")
      workerPool.terminate()
      g_log.info("Multiprocessing.Pool terminated")
  except KeyboardInterrupt:
    # Log with exception info to help debug deadlocks
    g_log.info("Observed KeyboardInterrupt", exc_info=True)
    pass
  except:
    g_log.exception("Failed")
    raise



if __name__ == "__main__":
  main()
