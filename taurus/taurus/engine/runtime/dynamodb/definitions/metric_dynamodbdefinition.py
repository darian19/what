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

from boto.dynamodb2.fields import HashKey

import taurus.engine
from taurus.engine.runtime.dynamodb.definitions.dynamodbdefinition import (
  DynamoDBDefinition)



class MetricDynamoDBDefinition(DynamoDBDefinition):
  """ taurus.metric DynamoDB item definition
  """


  @property
  def tableName(self):
    return ("taurus.metric%s" % taurus.engine.config.get("dynamodb",
                                                         "table_name_suffix"))


  @property
  def tableCreateKwargs(self):
    return dict(
      schema=[HashKey("uid")],
      throughput={
        "read": taurus.engine.config.getint("dynamodb",
                                            "metric_throughput_read"),
        "write": taurus.engine.config.getint("dynamodb",
                                             "metric_throughput_write")
      }
    )


  @property
  def Item(self):
    return namedtuple(
      "MetricItem",
      field_names=(
        "display_name",
        "name",
        "server",
        "uid",
        "metricType",
        "metricTypeName",
        "symbol"
      )
    )
