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

"""Common SQLAlchemy table definitions for metric collectors."""

import sqlalchemy as sa
from sqlalchemy import (BOOLEAN,
                        Column,
                        DATE,
                        DATETIME,
                        FLOAT,
                        ForeignKey,
                        ForeignKeyConstraint,
                        func,
                        Index,
                        INTEGER,
                        MetaData,
                        PrimaryKeyConstraint,
                        Table,
                        TEXT,
                        TIME,
                        TIMESTAMP)

from sqlalchemy.dialects import mysql


# utf8mb4 is needed for successful handling of multi-byte unicode (e.g., some
# emoticons), but is only supported by mysql-v5.5.3+
# NOTE: CHARSET utf8mb4 together with COLLATE utf8mb4_unicode_ci appears to work
# fine with datasift and twitter interaction data. However, the metric collector
# server that we're using at this time is stuck at mysql-v5.1.x, so we can't
# make use of utf8mb4 yet!!!
#MYSQL_CHARSET = "utf8mb4"
MYSQL_CHARSET = "utf8"
MYSQL_COLLATE = MYSQL_CHARSET + "_unicode_ci"

# 190 facilitates utf8mb4 ("max key length is 767 bytes")
MAX_UTF8_KEY_LENGTH=190

METRIC_NAME_MAX_LEN=MAX_UTF8_KEY_LENGTH


metadata = MetaData()



_MAX_TWEET_MSG_ID_LEN = 40

_MAX_TWEET_USERID_LEN = 100

# A.K.A. "screen_name" or "twitter handle"
# NOTE: username (handle) is max 15 chars now, but per posts on the web
# attributed to Twitter: "Early users of Twitter may have a username or real
# name longer than user names we currently allow."
# https://support.twitter.com/articles/14609-changing-your-username
_MAX_TWEET_USERNAME_LEN = 100

# A.K.A. "name" or "real name"
# NOTE: real name is max 20 chars now, but per posts on the web attributed to
# Twitter: "Early users of Twitter may have a username or real name longer than
# user names we currently allow."
# https://support.twitter.com/articles/14609-changing-your-username
_MAX_TWEET_REAL_NAME_LEN = 100


# Twitter messages streamed via twitter_direct_agent
twitterTweets = Table(
  "twitter_tweets",
  metadata,

  # Message UID
  # Source: id_str
  Column("uid",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         primary_key=True,
         nullable=False),

  # Tweet's creation datetime
  # Source: created_at
  Column("created_at",
         DATETIME(),
         nullable=False),

  # True if retweet
  # Source: whether tweet contains retweeted_status
  Column("retweet",
         BOOLEAN(),
         nullable=False),

  # Language code (http://tools.ietf.org/html/bcp47)
  # Source: lang
  Column("lang",
         mysql.VARCHAR(length=10),
         nullable=False),

  # Text of the message
  # Source: text
  Column("text",
         mysql.MEDIUMTEXT(convert_unicode=True)),

  # NOTE: regarding user info: The twitter stream doesn't provide specific
  #  updates to user information. Embedded user objects may contain stale info
  #  per https://dev.twitter.com/faq. Users may change their screen and real
  #  names. In a normalized database design, the user info would belong in a
  #  separate table, referenced from here via userid. We might concider this
  #  approach, perhaps using the potentially-stale user info embedded in tweets
  #  to keep the user table somewhat up to date.

  # Author's user id
  # Source: user.id_str
  Column("userid",
         mysql.VARCHAR(length=_MAX_TWEET_USERID_LEN),
         nullable=True),

  # author's screen_name
  # Source: user.screen_name
  Column("username",
         mysql.VARCHAR(length=_MAX_TWEET_USERNAME_LEN),
         nullable=True),

  # The "real name" of the user who posted this tweet, as they've defined it;
  # NULL if not available or if the legacy row predates this column.
  # Source: user.name
  Column("real_name",
         mysql.VARCHAR(length=_MAX_TWEET_REAL_NAME_LEN),
         nullable=True),

  # Id of the original tweet that was retweeted. NULL if message is not a
  # retweet;
  # NOTE: will contain empty string in both tweet and retweet legacy rows that
  #  predate this column.
  # Source: retweeted_status.id_str
  Column("retweeted_status_id",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         nullable=True,
         server_default=""),

  # Retweet count represented in the given retweet; NULL if message is not a
  # retweet; NOTE: will contain -2 in both tweet and retweet legacy rows that
  # predate this column (Twitter uses retweet_count=-1 if the count is not
  # available at the moment)
  # Source: retweeted_status.retweet_count
  Column("retweet_count",
         INTEGER,
         autoincrement=False,
         nullable=True,
         server_default=sa.text("-2")),

  # NULL if message is not a retweet; id_str of original tweet's author if
  # message is a retweet
  # Source: retweeted_status.user.id_str
  Column("retweeted_userid",
         mysql.VARCHAR(length=_MAX_TWEET_USERID_LEN),
         nullable=True,
         server_default=""),

  # author's screen_name of the original tweet that was retweeted; NULL if
  # message is not a retweet;
  # NOTE: will contain empty string in both tweet and retweet legacy rows that
  #  predate this column.
  # Source: retweeted_status.user.screen_name
  Column("retweeted_username",
         mysql.VARCHAR(length=_MAX_TWEET_USERNAME_LEN),
         nullable=True,
         server_default=""),

  # The "real name" of the author of the original tweet that was retweeted, as
  # they've defined it; NULL if message is not a retweet;
  # NOTE: will contain empty string in both tweet and retweet legacy rows that
  #  predate this column.
  # Source: retweeted_status.user.name
  Column("retweeted_real_name",
         mysql.VARCHAR(length=_MAX_TWEET_REAL_NAME_LEN),
         nullable=True,
         server_default=""),

  # If the represented Tweet is a reply, this field will contain the string
  # representation of the original Tweet's ID; NULL otherwise;
  # NOTE: will contain empty string in all legacy rows that predate this column.
  # NOTE: in_reply_to_status_id_str appears to be unreliable or inconsistent
  #  with https://dev.twitter.com/overview/api/tweets in that a NULL or absent
  #  in_reply_to_status_id_str sometimes shows up along with non-NULL
  #  in_reply_to_user_id_str and in_reply_to_screen_name.
  # Source: in_reply_to_status_id_str
  Column("in_reply_to_status_id",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         nullable=True,
         server_default=""),

  # If the represented Tweet is a reply, this field will contain the string
  # representation of the original Tweet's author ID; NULL otherwise;
  # NOTE: will contain empty string in all legacy rows that predate this column.
  # Source: in_reply_to_user_id_str
  Column("in_reply_to_userid",
         mysql.VARCHAR(length=_MAX_TWEET_USERID_LEN),
         nullable=True,
         server_default=""),

  # If the represented Tweet is a reply, this field will contain the screen name
  # of the original Tweet's author; NULL otherwise;
  # NOTE: will contain empty string in all legacy rows that predate this column.
  # Source: in_reply_to_screen_name
  Column("in_reply_to_username",
         mysql.VARCHAR(length=_MAX_TWEET_USERNAME_LEN),
         nullable=True,
         server_default=""),

  # Tweet contributors JSON object, NULL if none; also, NULL in legacy rows that
  # predate this column.
  # Source: contributors
  Column("contributors",
         mysql.TEXT(convert_unicode=True),
         nullable=True),

  # Timestamp when this row was stored
  # NOTE: would have preferred DATETIME, but DATETIME with CURRENT_TIMESTAMP is
  # not possible there until MySQL 5.6.5
  Column("stored_at",
         TIMESTAMP,
         nullable=True,
         server_default=func.current_timestamp()),

  mysql_COLLATE=MYSQL_COLLATE,
  mysql_CHARSET=MYSQL_CHARSET,
)

Index("created_at_idx", twitterTweets.c.created_at)
Index("stored_at_idx", twitterTweets.c.stored_at)



# Twitter metric data samples from twitter_direct_agent
# NOTE: some messages may match multiple metrics
twitterTweetSamples = Table(
  "twitter_tweet_samples",
  metadata,

  # Sequence number; we save the sequence number of the most recently dispatched
  # non-metric data item in the "emitted_non_metric_tracker" table
  Column("seq",
         mysql.BIGINT(unsigned=True),
         autoincrement=True,
         nullable=False),

  PrimaryKeyConstraint("seq",
                       name="twitter_tweet_samples_pk"),

  # Metric name
  Column("metric",
         mysql.VARCHAR(length=METRIC_NAME_MAX_LEN),
         nullable=False),

  # UID of message in twitter_tweets table
  Column("msg_uid",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         ForeignKey(twitterTweets.c.uid,
                    name="twitter_tweet_samples_to_twitter_fk",
                    onupdate="CASCADE", ondelete="CASCADE"),
         nullable=False,
         server_default=""),

  # Aggregation timestamp
  Column("agg_ts",
         DATETIME(),
         nullable=False),

  # Timestamp when this row was stored
  # NOTE: would have preferred DATETIME, but DATETIME with CURRENT_TIMESTAMP is
  # not possible there until MySQL 5.6.5
  Column("stored_at",
         TIMESTAMP,
         nullable=True,
         server_default=func.current_timestamp()),

  mysql_COLLATE=MYSQL_COLLATE,
  mysql_CHARSET=MYSQL_CHARSET,
)

Index("agg_ts_idx", twitterTweetSamples.c.agg_ts)
Index("metric_and_msg_uid_idx",
      twitterTweetSamples.c.metric,
      twitterTweetSamples.c.msg_uid,
      unique=True)
Index("stored_at_idx", twitterTweetSamples.c.stored_at)



# Tweet IDs to be deleted from Status deletion notices; see
# https://dev.twitter.com/streaming/overview/messages-types
# NOTE: per twitter doc, deletion notices may arrive prior to the
# corresponding tweets
twitterDeletion = Table(
  "twitter_deletion",
  metadata,

  # Unique ID of tweet that was deleted
  Column("tweet_uid",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         primary_key=True,
         nullable=False),
  # User ID of the tweet's originator
  Column("userid",
         mysql.VARCHAR(length=_MAX_TWEET_USERID_LEN),
         nullable=False),
  # Timestamp when deletion record was created
  Column("created_at",
         TIMESTAMP,
         nullable=False,
         server_default=func.current_timestamp()),
  mysql_COLLATE=MYSQL_COLLATE,
  mysql_CHARSET=MYSQL_CHARSET,
)



# Twitter handle that have become invalid (say some Twitter handle changes)
twitterHandleFailures = Table(
  "twitter_handle_failures",
  metadata,

  # Twitter handle
  Column("handle",
         mysql.VARCHAR(length=_MAX_TWEET_MSG_ID_LEN),
         primary_key=True,
         nullable=False),
  # Timestamp when this row was created
  Column("created_at",
         TIMESTAMP,
         nullable=False,
         server_default=func.current_timestamp()),
  mysql_COLLATE=MYSQL_COLLATE,
  mysql_CHARSET=MYSQL_CHARSET,
)



# Max symbol length of a financial security (liberal guess)
_FIN_SECURITY_SYMBOL_MAX_LEN = 20

# Common settings for ASCII text columns. Using "latin1" and
# "latin1_swedish_ci" to match mysql defaults.
_ASCII_TEXT_KWARGS = dict(charset="latin1", collation="latin1_swedish_ci")

# Security(stock) descriptions from xIgnite
xigniteSecurity = Table(
  "xignite_securty",
  metadata,
  # Company market symbol (e.g., GOOG, GOOG.XMEX)
  Column("symbol",
         mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),
  # The Central Index Key (CIK) for this security (10 diYOMPs)
  Column("cik",
         mysql.VARCHAR(length=10, **_ASCII_TEXT_KWARGS),
         nullable=True),
  # CUSIP: a nine-character alphanumeric code that identifies a North American
  # financial security for the purposes of facilitating clearing and settlement
  # of trades. If you are not entitled to to receive CUSIP identifiers, then
  # this field will be NULL.
  Column("cusip",
         mysql.VARCHAR(length=9, **_ASCII_TEXT_KWARGS),
         nullable=True),
  # ISIN: a 12-character alpha-numerical code that does not contain information
  # characterizing financial instruments but serves for uniform identification
  # of a security at trading and settlement. If you are not entitled to receive
  # ISIN identifiers then this field will be empty.
  Column("isin",
         mysql.VARCHAR(length=12, **_ASCII_TEXT_KWARGS),
         nullable=True),
  # Valoren: An identification number assigned to financial instruments in
  # Switzerland. These numbers are similar to the CUSIP numbers that are used in
  # Canada and the U.S. A typical valoren number is between six to nine diYOMPs
  # in length.
  Column("valoren",
         mysql.VARCHAR(length=9, **_ASCII_TEXT_KWARGS),
         nullable=True),
  # The name of this security
  # e.g., "Google Inc"
  Column("name",
         mysql.VARCHAR(length=100),
         nullable=True),
  # The name of the market (exchange) that this security is listed on.
  # e.g., NASDAQ, NYSE, SANTIAGO
  Column("market",
         mysql.VARCHAR(length=20),
         nullable=True),
  # The Market Identification Code (MIC) of the market (exchange) that this
  # security is listed on. The MIC is a four alpha character code, and is
  # defined in ISO 10383
  Column("mic",
         mysql.VARCHAR(length=4, **_ASCII_TEXT_KWARGS),
         nullable=True),
  # A true/false flag denoting whether this exchange is the one where the
  # security is most frequently traded (and hence most liquid).
  Column("most_liquid_exg",
         BOOLEAN(),
         nullable=False),
  # Category or industry of this security
  # e.g., "InformationTechnologyServices"
  Column("industry",
         mysql.VARCHAR(length=100),
         nullable=True),
)



def _createXigniteGlobalnewsSchema(schemaName, metadata):
  schema = Table(
    schemaName,
    metadata,

    # Foreign key reference into xignite_securty.symbol column
    Column("symbol",
           mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                         **_ASCII_TEXT_KWARGS),
           ForeignKey(xigniteSecurity.c.symbol,
                      name=schemaName + "_to_security_fk",
                      onupdate="CASCADE", ondelete="CASCADE"),
           nullable=False,
           server_default=""),

    # The title for this headline
    Column("title",
           mysql.VARCHAR(length=500),
           nullable=True),

    # The date when this headline was published (or re-published by another
    # source)
    Column("local_pub_date",
           DATE,
           nullable=False),

    # The UTC offset for the local_pub_date field
    Column("utc_offset",
           FLOAT,
           autoincrement=False,
           nullable=False),

    # The UTC date/time when this press release was discovered by our agent
    Column("discovered_at",
           DATETIME,
           nullable=False),

    # The originating journal/website for this headline. NOTE: the same article
    # URL can originate from multiple sources (e.g., "Clusterstock" and
    # "Business Insider: Finance")
    Column("source",
           mysql.VARCHAR(length=MAX_UTF8_KEY_LENGTH),
           nullable=False),

    # The URL for the headline
    # NOTE: max key length in SQL is 767 bytes
    Column("url",
           mysql.VARCHAR(length=767, **_ASCII_TEXT_KWARGS),
           nullable=False),

    # JSON list that contains URLs of all images associated with this headline
    Column("image_urls",
           mysql.MEDIUMTEXT(convert_unicode=True),
           nullable=True),

    # JSON list that contains all tags associated with this headline, broken
    # down by tag groups; the original is flattened; example:
    #   [{"Companies": ["American Airlines Group Inc.", "S&P Capital IQ"]},
    #    {"Sectors": ["Finance", "Transportation"]},
    #    {"Symbols": ["DAL", "AAL"]}, {"Topics": ["Business_Finance"]}]
    # Source: xignite SecurityHeadline.Tags
    Column("tags",
           TEXT(convert_unicode=True),
           nullable=True),

    # The time taken (in seconds) to process the request on xignite servers.
    Column("proc_dur",
           FLOAT,
           nullable=False),

    # An abbreviated version(usually 2-3 paragraphs) of the full article; NULL
    # if unknown
    # Source: GetMarketNewsDetails MarketNewsItem.Summary
    Column("summary",
           mysql.TEXT(convert_unicode=True),
           nullable=True),

    # The UTC date/time when this news article was (originally) published; NULL
    # if unknown
    # Source: GetMarketNewsDetails MarketNewsItem.Time
    Column("orig_pub_time",
           DATETIME,
           nullable=True),

    # The originating journal/website for this headline; NULL if not known
    # Source: GetMarketNewsDetails MarketNewsItem.Source
    Column("orig_source",
           mysql.TEXT(convert_unicode=True),
           nullable=True),

    # The time taken (in seconds) to process the GetMarketNewsDetails request on
    # xignite servers.
    # Source: GetMarketNewsDetails MarketNewsItem.Delay
    Column("details_proc_dur",
           FLOAT,
           nullable=True),

    PrimaryKeyConstraint("symbol", "local_pub_date", "url", "source",
                         name=schemaName + "_pk"),

    Index("discovered_at_idx", "discovered_at", unique=False)
  )


  return schema



# Security (stock) Headlines from xIgnite
xigniteSecurityHeadline = _createXigniteGlobalnewsSchema(
  "xignite_security_headline", metadata)



# Security (stock) Press Releases from xIgnite
xigniteSecurityRelease = _createXigniteGlobalnewsSchema(
  "xignite_security_release", metadata)



# Company security symbols that have become invalid; used by
# check_company_symbols.py
companySymbolFailures = Table(
  "company_symbol_failures",
  metadata,

  # Twitter handle
  # Company market symbol (e.g., GOOG, GOOG.XMEX)
  Column("symbol",
         mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),
  # Timestamp when this row was created
  Column("created_at",
         TIMESTAMP,
         nullable=False,
         server_default=func.current_timestamp()),
)


# Table that tracks the timestamp of the last sample emitted to the taurus
# server
#
# This permits us to forward necessary stored data to Taurus server after Taurus
# service disruption
EMITTED_TRACKER_KEY_MAX_LEN = 50
emittedSampleTracker = Table(
  "emitted_sample_tracker",
  metadata,
  # Provider-specific key that uniquely identifies the corresponding sample
  # timestamp (e.g., "xignite-security-news-volume")
  Column("key",
         mysql.VARCHAR(length=EMITTED_TRACKER_KEY_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),
  # UTC timestamp of the last successfully-emitted aggregation
  Column("sample_ts",
         DATETIME,
         nullable=False),
)



# Table that tracks the sequence number of the last non-metric item dispatched
# to non-metric data consumer
#
# This permits us to track from where to resume forwarding when the consumer
# comes back online
emittedNonMetricTracker = Table(
  "emitted_non_metric_tracker",
  metadata,

  # Provider-specific key that uniquely identifies the corresponding sample
  # timestamp (e.g., "xignite-security-news-volume")
  Column("key",
         mysql.VARCHAR(length=EMITTED_TRACKER_KEY_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),

  # Sequence number of the last successfully dispatched non-metric data item
  Column("last_seq",
         mysql.BIGINT(unsigned=True),
         autoincrement=False,
         nullable=False),
)

# XIgnite stock data.  Partial results from XIgniteGlobalQuota GetBars API
xigniteSecurityBars = Table(
  "xignite_security_bars",
  metadata,
  Column("symbol",
         mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         ForeignKey(xigniteSecurity.c.symbol,
                    name="xignite_security_bars_to_security_fk",
                    onupdate="CASCADE",
                    ondelete="CASCADE"),
         primary_key=True,
         nullable=False),
  Column("StartDate", DATE(), primary_key=True, nullable=False),
  Column("StartTime", TIME(), primary_key=True, nullable=False),
  Column("EndDate", DATE(), primary_key=True, nullable=False),
  Column("EndTime", TIME(), primary_key=True, nullable=False),
  Column("UTCOffset", FLOAT(), primary_key=True, nullable=False),
  Column("Open", FLOAT(), nullable=False),
  Column("High", FLOAT(), nullable=False),
  Column("Low", FLOAT(), nullable=False),
  Column("Close", FLOAT(), nullable=False),
  Column("Volume", INTEGER(), nullable=False),
  Column("Trades", INTEGER(), nullable=False),
)

emittedStockPrice = Table(
  "emitted_stock_price",
  metadata,
  Column("symbol",
         mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),
  Column("StartDate", DATE(), primary_key=True, nullable=False),
  Column("StartTime", TIME(), primary_key=True, nullable=False),
  Column("EndDate", DATE(), primary_key=True, nullable=False),
  Column("EndTime", TIME(), primary_key=True, nullable=False),
  Column("UTCOffset", FLOAT(), primary_key=True, nullable=False),
  Column("sent", DATETIME(), nullable=True),
  ForeignKeyConstraint(
    [
      "symbol",
      "StartDate",
      "StartTime",
      "EndDate",
      "EndTime",
      "UTCOffset"
    ], [
      "xignite_security_bars.symbol",
      "xignite_security_bars.StartDate",
      "xignite_security_bars.StartTime",
      "xignite_security_bars.EndDate",
      "xignite_security_bars.EndTime",
      "xignite_security_bars.UTCOffset"
    ],
    onupdate="CASCADE",
    ondelete="CASCADE"
  )
)
Index("xignite_stock_price_sent_idx", emittedStockPrice.c.sent)

emittedStockVolume = Table(
  "emitted_stock_volume",
  metadata,
  Column("symbol",
         mysql.VARCHAR(length=_FIN_SECURITY_SYMBOL_MAX_LEN,
                       **_ASCII_TEXT_KWARGS),
         primary_key=True,
         nullable=False),
  Column("StartDate", DATE(), primary_key=True, nullable=False),
  Column("StartTime", TIME(), primary_key=True, nullable=False),
  Column("EndDate", DATE(), primary_key=True, nullable=False),
  Column("EndTime", TIME(), primary_key=True, nullable=False),
  Column(
    "UTCOffset",
    FLOAT(),
    primary_key=True,
    nullable=False),
  Column("sent", DATETIME(), nullable=True),
  ForeignKeyConstraint(
    [
      "symbol",
      "StartDate",
      "StartTime",
      "EndDate",
      "EndTime",
      "UTCOffset"
    ], [
      "xignite_security_bars.symbol",
      "xignite_security_bars.StartDate",
      "xignite_security_bars.StartTime",
      "xignite_security_bars.EndDate",
      "xignite_security_bars.EndTime",
      "xignite_security_bars.UTCOffset"
    ],
    onupdate="CASCADE",
    ondelete="CASCADE"
  )
)
Index("xignite_stock_volume_sent_idx", emittedStockVolume.c.sent)
