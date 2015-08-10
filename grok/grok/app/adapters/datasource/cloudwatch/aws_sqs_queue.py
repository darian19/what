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

# Note: we don't allow autostacks of SQS, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from boto import sqs

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class SQSAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.SQS_QUEUE

  NAMESPACE = "AWS/SQS"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("QueueName",),)


  @classmethod
  def describeResources(cls, region):
    """ Describe available resource-adapter-specific resources in the given
    region.

    NOTE: overrides method in base class

    :param region: AWS region

    :returns: description of available resource-adapter-specific resources in
      the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/instance/i-4be0d87f",
              "resID": "i-4be0d87f",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    conn = cls._connectToAWSService(sqs, region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    queueList = [{"grn": "aws://%s/%s/%s" % (region, instanceType, q.name),
                      "resID": q.name,
                      "name": ""}
                 for q in conn.get_all_queues()]
    return queueList


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s for Queue %s in %s" % (
      self.METRIC_NAME, self._dimensions["QueueName"], self._region)




@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SQSNumberOfEmptyReceivesMetricAdapter(SQSAdapter):

  METRIC_NAME = "NumberOfEmptyReceives"

  STATISTIC = "Sum"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SQSNumberOfMessagesDeletedMetricAdapter(SQSAdapter):

  METRIC_NAME = "NumberOfMessagesDeleted"

  STATISTIC = "Sum"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SQSNumberOfMessagesSentMetricAdapter(SQSAdapter):

  METRIC_NAME = "NumberOfMessagesSent"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Sum"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SQSNumberOfMessagesReceivedMetricAdapter(SQSAdapter):

  METRIC_NAME = "NumberOfMessagesReceived"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Sum"
  UNIT = "Count"

  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SQSSentMessageSizeMetricAdapter(SQSAdapter):

  METRIC_NAME = "SentMessageSize"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"
  UNIT = "Bytes"

  MIN = 0
  MAX = 10000
