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

# Note: we don't allow autostacks of ELBs, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase, ResourceTypeNames)
from YOMP.app.aws.elb_utils import getELBInstances



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class ELBAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.ELB_LOAD_BALANCER

  NAMESPACE = "AWS/ELB"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("LoadBalancerName",),)


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: overrides method in base class

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s on ELB Load Balancer %s in %s region" % (
      self.METRIC_NAME, self._dimensions["LoadBalancerName"], self._region)


  @classmethod
  def describeResources(cls, region):
    """ Describe available ELB Instances in the given region.

    :param region: AWS region

    :returns: description of available ELB Instances in the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/AWS/ELB/LoadBalancer/prod-elb",
              "resID": "prod-elb",
              "name": ""
          },

          ...
        ]
    """
    elbs = getELBInstances(region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    elbList = [{"grn": ("aws://%s/%s/%s" %
                        (region, instanceType, elb.name)),
                      "resID": elb.name,
                      "name": ""}
                     for elb in elbs]
    return elbList



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ELBLatencyMetricAdapter(ELBAdapter):

  METRIC_NAME = "Latency"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "Seconds"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 3



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ELBRequestCountMetricAdapter(ELBAdapter):

  METRIC_NAME = "RequestCount"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Sum"

  UNIT = "Count"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 1000
