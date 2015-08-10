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
unit tests for taurus.metric_collectors.twitterdirect.twitter_direct_agent
"""

from datetime import datetime
import json
import unittest

from mock import Mock

from taurus.metric_collectors.twitterdirect import twitter_direct_agent



class TweetStorerTestCase(unittest.TestCase):


  def testCurentStreamStatsRudimentary(self):
    """ Very rudimentary tests of TweetStorer._CurrentStreamStats
    """
    stats = twitter_direct_agent.TweetStorer._CurrentStreamStats()

    # Make sure that str doesn't crash on stats with default attributes
    str(stats)

    # Change stats and make sure that str doesn't crash
    stats.numTweets = 5
    stats.numUntaggedTweets = 1
    stats.numDeleteStatuses = 2
    stats.numLimitStatuses = 3
    stats.numLimitedTweets = 100
    stats.numDisconnectStatuses = 4
    stats.numWarningStatuses = 5
    stats.numOtherStatuses = 6
    stats.startingDatetime = datetime.utcnow()
    str(stats)


  def testRuntimeStreamingStatsRudimentary(self):
    """ Very rudimentary tests of TweetStorer._RuntimeStreamingStats
    """
    stats = twitter_direct_agent.TweetStorer._RuntimeStreamingStats()

    # Make sure that str doesn't crash on stats with default attributes
    str(stats)

    # Change stats and make sure that str doesn't crash
    stats.numTweets = 5
    stats.numUntaggedTweets = 1
    stats.numDeleteStatuses = 2
    stats.numLimitStatuses = 3
    stats.numLimitedTweets = 100
    stats.numDisconnectStatuses = 4
    stats.numWarningStatuses = 5
    stats.numOtherStatuses = 6
    stats.streamNumber = 7
    str(stats)


  def testReapMessagesEmptySequence(self):
    """ Test handling of empty message sequence by TweetStorer._reapMessages
    """
    storer = twitter_direct_agent.TweetStorer(
      taggingMap=Mock(),
      aggSec=300,
      msgQ=Mock(),
      echoData=False)

    # Test passing empty sequence of messages
    tweets, deletes = storer._reapMessages([])
    self.assertSequenceEqual(tweets, [])
    self.assertSequenceEqual(deletes, [])


  def testReapMessagesWithLimitNotifications(self):
    """ Test handling of "limit" notifications in TweetStorer._reapMessages
    """
    storer = twitter_direct_agent.TweetStorer(
      taggingMap=Mock(),
      aggSec=300,
      msgQ=Mock(),
      echoData=False)

    # Test first connection marker and limit
    tweets, deletes = storer._reapMessages(
      [
        twitter_direct_agent.TwitterStreamListener.ConnectionMarker,
        json.dumps(dict(limit=dict(track=5)))
      ])

    self.assertSequenceEqual(tweets, [])
    self.assertSequenceEqual(deletes, [])

    self.assertEqual(storer._currentStreamStats.numLimitStatuses, 1)
    self.assertEqual(storer._currentStreamStats.numLimitedTweets, 5)
    self.assertEqual(storer._runtimeStreamingStats.numLimitStatuses, 1)
    self.assertEqual(storer._runtimeStreamingStats.numLimitedTweets, 5)
    self.assertEqual(storer._runtimeStreamingStats.streamNumber, 1)

    # Test out-of-order limit: should be counted in numLimitStatuses, but
    # ignored in numLimitedTweets
    tweets, deletes = storer._reapMessages(
      [json.dumps(dict(limit=dict(track=1)))])

    self.assertSequenceEqual(tweets, [])
    self.assertSequenceEqual(deletes, [])

    self.assertEqual(storer._currentStreamStats.numLimitStatuses, 2)
    self.assertEqual(storer._currentStreamStats.numLimitedTweets, 5)
    self.assertEqual(storer._runtimeStreamingStats.numLimitStatuses, 2)
    self.assertEqual(storer._runtimeStreamingStats.numLimitedTweets, 5)

    # Test two more in-order limits
    tweets, deletes = storer._reapMessages(
      [
        json.dumps(dict(limit=dict(track=9))),
        json.dumps(dict(limit=dict(track=12))),
      ])

    self.assertSequenceEqual(tweets, [])
    self.assertSequenceEqual(deletes, [])

    self.assertEqual(storer._currentStreamStats.numLimitStatuses, 4)
    self.assertEqual(storer._currentStreamStats.numLimitedTweets, 12)
    self.assertEqual(storer._runtimeStreamingStats.numLimitStatuses, 4)
    self.assertEqual(storer._runtimeStreamingStats.numLimitedTweets, 12)

    # Test reconnect and one limit notification on the new connection
    tweets, deletes = storer._reapMessages(
      [
        twitter_direct_agent.TwitterStreamListener.ConnectionMarker,
        json.dumps(dict(limit=dict(track=1000))),
      ])

    self.assertSequenceEqual(tweets, [])
    self.assertSequenceEqual(deletes, [])

    self.assertEqual(storer._currentStreamStats.numLimitStatuses, 1)
    self.assertEqual(storer._currentStreamStats.numLimitedTweets, 1000)
    self.assertEqual(storer._runtimeStreamingStats.numLimitStatuses, 5)
    self.assertEqual(storer._runtimeStreamingStats.numLimitedTweets, 1012)
    self.assertEqual(storer._runtimeStreamingStats.streamNumber, 2)


  def testCreateTweetAndReferenceRowsWithMissingLangKey(self):
    """ Test case for TAUR-1370 wherein a missing `lang` key resulted in a
    failure to reap tweet, but also resulted in a faulty entry in
    `twitter_tweets` table with null values, causing the agent to crash later
    in the pipeline """
    storer = twitter_direct_agent.TweetStorer(
      taggingMap=Mock(),
      aggSec=300,
      msgQ=Mock(),
      echoData=False)

    aggRefDatetime = datetime(2015, 8, 5, 14, 44, 33)

    msg = {
      u'contributors': None,
      u'coordinates': None,
      u'created_at': u'Wed Aug 05 14:44:32 +0000 2015',
      u'entities': {u'hashtags': [],
                    u'symbols': [{u'indices': [90, 95], u'text': u'LAMR'},
                                 {u'indices': [96, 100], u'text': u'IBM'},
                                 {u'indices': [101, 104], u'text': u'WY'}],
                    u'trends': [],
                    u'urls': [{u'display_url': u'ow.ly/QrGNn',
                               u'expanded_url': u'http://ow.ly/QrGNn',
                               u'indices': [67, 89],
                               u'url': u'http://t.co/bBikX3EmVd'}],
                    u'user_mentions': []},
      u'favorite_count': 0,
      u'favorited': False,
      u'filter_level': u'low',
      u'geo': None,
      u'id': 628939652129538049,
      u'id_str': u'628939652129538049',
      u'in_reply_to_screen_name': None,
      u'in_reply_to_status_id': None,
      u'in_reply_to_status_id_str': None,
      u'in_reply_to_user_id': None,
      u'in_reply_to_user_id_str': None,
      'metricTagSet': set([u'TWITTER.TWEET.HANDLE.IBM.VOLUME']),
      u'place': None,
      u'possibly_sensitive': False,
      u'retweet_count': 0,
      u'retweeted': False,
      u'source': u'<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
      u'text': u'Huge Moves On Our Penny Stock Picks Lately! Big New Pick Tomorrow: http://t.co/bBikX3EmVd $LAMR $IBM $WY',
      u'timestamp_ms': u'1438785872858',
      u'truncated': False,
      u'user': {u'contributors_enabled': False,
                u'created_at': u'Wed Apr 16 20:03:52 +0000 2014',
                u'default_profile': True,
                u'default_profile_image': False,
                u'description': u'ATTENTION: Read full disclaimer before looking at any of our tweets! Link To Full Disclaimer: http://www.pennystockdream.com/disclaimer',
                u'favourites_count': 0,
                u'follow_request_sent': None,
                u'followers_count': 5037,
                u'following': None,
                u'friends_count': 0,
                u'geo_enabled': False,
                u'id': 2447928920,
                u'id_str': u'2447928920',
                u'is_translator': False,
                u'lang': u'en',
                u'listed_count': 43,
                u'location': u'',
                u'name': u'StockenheimerSchmidt',
                u'notifications': None,
                u'profile_background_color': u'C0DEED',
                u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png',
                u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png',
                u'profile_background_tile': False,
                u'profile_image_url': u'http://pbs.twimg.com/profile_images/456523892308201472/sBGAsJTn_normal.png',
                u'profile_image_url_https': u'https://pbs.twimg.com/profile_images/456523892308201472/sBGAsJTn_normal.png',
                u'profile_link_color': u'0084B4',
                u'profile_sidebar_border_color': u'C0DEED',
                u'profile_sidebar_fill_color': u'DDEEF6',
                u'profile_text_color': u'333333',
                u'profile_use_background_image': True,
                u'protected': False,
                u'screen_name': u'Stockenheimer1',
                u'statuses_count': 151832,
                u'time_zone': None,
                u'url': None,
                u'utc_offset': None,
                u'verified': False}}

    tweetRow, referenceRows = (
      storer._createTweetAndReferenceRows(msg, aggRefDatetime))

    self.assertIn("lang", tweetRow)
    self.assertEqual(tweetRow["lang"], None)
    self.assertIn("username", tweetRow)
    self.assertEqual(tweetRow["username"], u"Stockenheimer1")
    self.assertIn("uid", tweetRow)
    self.assertEqual(tweetRow["uid"], u"628939652129538049")
    self.assertIn("created_at", tweetRow)
    self.assertEqual(tweetRow["created_at"], datetime(2015, 8, 5, 14, 44, 32))


if __name__ == "__main__":
  unittest.main()
