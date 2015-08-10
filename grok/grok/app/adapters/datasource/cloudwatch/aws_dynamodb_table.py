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

# Note: we don't allow autostacks of DynamoDB, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from boto import dynamodb

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class DynamoDBTableAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.DYNAMODB_TABLE

  NAMESPACE = "AWS/DynamoDB"


  @classmethod
  def describeResources(cls, region):
    """ Describe available DynamoDB tables in the given region.

    :param region: AWS region

    :returns: description of available DynamoDB tables in the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/dynamo-db-table/sample_table_for_dev",
              "resID": "sample_table_for_dev",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(':') + 1:]

    conn = cls._connectToAWSService(dynamodb, region)
    dbList = [{"grn": "aws://%s/%s/%s" %
                      (region, instanceType, db),
               "resID": db,
               "name": ""} for db in conn.list_tables()]
    return dbList

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: overrides method in base class

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s for DynamoDB Table %s in %s" % (
      self.METRIC_NAME, self._dimensions["TableName"], self._region)



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class DDBConsumedReadCapacityUnitsMetricAdapter(DynamoDBTableAdapter):

  METRIC_NAME = "ConsumedReadCapacityUnits"

  IS_INSTANCE_DEFAULT = True

  # Cloudwatch metric dimension combinations supported by this adapter;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("TableName",),)

  STATISTIC = "Average"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class DDBConsumedWriteCapacityUnitsMetricAdapter(DynamoDBTableAdapter):

  METRIC_NAME = "ConsumedWriteCapacityUnits"

  IS_INSTANCE_DEFAULT = True

  # Cloudwatch metric dimension combinations supported by this adapter;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("TableName",),)

  STATISTIC = "Average"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class DDBReturnedItemCountMetricAdapter(DynamoDBTableAdapter):

  METRIC_NAME = "ReturnedItemCount"

  IS_INSTANCE_DEFAULT = True

  # Cloudwatch metric dimension combinations supported by this adapter;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("TableName",),)

  STATISTIC = "Sum"
  UNIT = "Count"

  MIN = 0
  MAX = None



# TODO: MER-3802 Deprecated until cloudwatch API can properly handle multiple
# dimensions
#@AWSResourceAdapterBase.registerMetricAdapter
class DDBSuccessfulRequestLatencyAdapter(DynamoDBTableAdapter):

  METRIC_NAME = "SuccessfulRequestLatency"

  # Cloudwatch metric dimension combinations supported by this adapter;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("TableName", "Operation",),)

  STATISTIC = "Average"
  UNIT = "Milliseconds"

  MIN = 0
  MAX = 1000
