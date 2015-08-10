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

from boto.dynamodb2.fields import HashKey, RangeKey, AllIndex, GlobalAllIndex

import taurus.engine
from taurus.engine.runtime.dynamodb.definitions.dynamodbdefinition import (
  DynamoDBDefinition)



class InstanceDataHourlyDynamoDBDefinition(DynamoDBDefinition):
  """ taurus.metric_data DynamoDB item definition
  """


  @property
  def tableName(self):
    return ("taurus.instance_data_hourly%s" %
            taurus.engine.config.get("dynamodb", "table_name_suffix"))


  @property
  def tableCreateKwargs(self):
    return dict(
      schema=[
        HashKey("instance_id"),
        RangeKey("date_hour"),
      ],
      throughput={
        "read": (
          taurus.engine.config.getint("dynamodb",
                                      "instance_data_hourly_throughput_read")),
        "write": (
          taurus.engine.config.getint("dynamodb",
                                      "instance_data_hourly_throughput_write"))
      },
      global_indexes=[
        GlobalAllIndex(
          "taurus.instance_data_hourly-date_hour_index",
          parts=[
            HashKey("date"),
            RangeKey("hour")
          ],
          throughput={
            "read": taurus.engine.config.getint(
                "dynamodb",
                "instance_data_hourly_throughput_read"),
            "write": taurus.engine.config.getint(
                "dynamodb",
                "instance_data_hourly_throughput_write")
          }
        )
      ]
    )


  @property
  def Item(self):
    return namedtuple(
      "InstanceDataHourlyItem",
      field_names=(
        "instance_id",
        "date_hour",
        "date",
        "hour",
        "anomaly_score",
      )
    )
