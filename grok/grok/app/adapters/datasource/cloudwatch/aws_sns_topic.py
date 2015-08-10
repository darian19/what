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

# Note: we don't allow autostacks of SNS, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from boto import sns

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
  AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames


@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class SNSAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.SNS_TOPIC

  NAMESPACE = "AWS/SNS"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("Topic",),)


  @classmethod
  def describeResources(cls, region):
    """ Describe available SNS Topics in the given region.

    :param region: AWS region

    :returns: description of available EC2 Instances in the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/Topic/i-4be0d87f",
              "resID": "i-4be0d87f",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    conn = cls._connectToAWSService(sns, region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(':') + 1:]

    result = conn.get_all_topics()["ListTopicsResponse"]["ListTopicsResult"]
    topics = result["Topics"]

    queueList = []
    for topic in topics:
      topicName = topic["TopicArn"][topic["TopicArn"].rfind(":")+1:]
      queueList.append({"grn":"aws://%s/%s/%s" %
                              (region ,instanceType, topicName),
                        "resID":topicName,
                        "name":""})
    return queueList

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: overrides method in base class

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s for Topic %s in %s" % (
      self.METRIC_NAME, self._dimensions["Topic"], self._region)



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class SNSNumberOfMessagesPublishedMetricAdapter(SNSAdapter):

  METRIC_NAME = "NumberOfMessagesPublished"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Sum"

  UNIT = "Count"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None
