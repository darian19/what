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

from boto.dynamodb2.fields import HashKey, RangeKey, GlobalAllIndex

import taurus.engine
from taurus.engine.runtime.dynamodb.definitions.dynamodbdefinition import (
  DynamoDBDefinition)



class MetricTweetsDynamoDBDefinition(DynamoDBDefinition):
  """ taurus.metric_tweets DynamoDB item definition
  """


  @property
  def tableName(self):
    return ("taurus.metric_tweets%s" % (
            taurus.engine.config.get("dynamodb", "table_name_suffix")))


  @property
  def tableCreateKwargs(self):
    return dict(
      schema=[
        HashKey("metric_name_tweet_uid"),
        RangeKey("agg_ts")
      ],
      throughput={
        "read": 1,
        "write": taurus.engine.config.getint("dynamodb",
                                             "metric_tweets_throughput_write")
      },
      global_indexes=[
        GlobalAllIndex(
          "taurus.metric_data-metric_name_index",
          parts=[
            HashKey("metric_name"),
            RangeKey("agg_ts")
          ],
          throughput={
            "read": (
              taurus.engine.config.getint("dynamodb",
                                          "metric_tweets_throughput_read")),
            "write": (
              taurus.engine.config.getint("dynamodb",
                                          "metric_tweets_throughput_write"))
          }
        )
      ]
    )


  @property
  def Item(self):
    return namedtuple(
      "MetricTweetsItem",
      field_names=(
        "metric_name_tweet_uid",
        "metric_name",
        "tweet_uid",
        "created_at",
        "agg_ts",
        "text",
        "userid",
        "username",
        "retweet_count"
      )
    )
