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

# Note: we don't allow autostacks of ASGs, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from boto.ec2 import autoscale

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.aws.asg_utils import getAutoScalingGroups



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class AutoScalingGroupAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.AUTOSCALING_GROUP

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("AutoScalingGroupName",),)


  @classmethod
  def describeResources(cls, region):
    """ Describe available AutoScalingGroups in the given region.

    :param region: AWS region

    :returns: description of available AutoScalingGroups in the given region

    ::

        [
          {
            # NOTE: grn = "YOMP resource name"
            "grn": "aws://us-west-2/auto-scaling-group/webserver-asg-micros01",
            "resID": "webserver-asg-micros01",
            "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    autoscalingGroups = getAutoScalingGroups(region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    # TODO: TAUR-884 - If an autoscaling group does not have a 'Name' tag, then
    # the code below will fail with an 'IndexError: list index out of range' for
    # the 'name' field.
    autoscaleList = [{"grn": ("aws://%s/%s/%s" %
                              (region, instanceType, group.name)),
                      "resID": group.name,
                      "name": [tag.value for tag in group.tags
                               if tag.key == "Name"][0]
                              or ""}
                     for group in autoscalingGroups]
    return autoscaleList


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: str
    """
    return "%s on AutoScalingGroupName %s in %s" % (
      self.METRIC_NAME, self._dimensions["AutoScalingGroupName"], self._region)


  def getResourceName(self):
    """ Query AWS for the name tag value of the metric's resource

    NOTE: overrides method in base class

    :returns: name tag value if available or None if not
    :rtype: string or NoneType
    """
    conn = self._connectToAWSService(autoscale, self._region)
    filters = {
      "resource-type": "auto-scaling-group",
      "resource-id": self._dimensions["AutoScalingGroupName"],
      "key": "Name"
    }
    tags = conn.get_all_tags(filters=filters)

    # Boto doesn't currently support filters for get_all_tags in autoscaling
    # groups (not implemented yet). Manually implementing a filter
    # http://boto.readthedocs.org/en/2.6.0/ref/autoscale.html
    tags = [tag for tag in tags
            if tag.resource_type == "auto-scaling-group"
            and tag.resource_id == self._dimensions["AutoScalingGroupName"]
            and tag.key == "Name"]

    if tags:
      return tags[0].value

    return None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGGroupTotalInstancesMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "GroupTotalInstances"

  IS_INSTANCE_DEFAULT = True

  NAMESPACE = "AWS/AutoScaling"

  STATISTIC = "Sum"
  UNIT = "None"

  # The number of instances may grow a very substantial amount so estimating
  # based on a few hundred records may not be very accurate. We pick an
  # arbitrary number here instead that should work pretty well in all cases
  # (we want a bucket size close to one but any smaller isn't useful).
  MIN = 0
  MAX = 114



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGCPUUtilizationMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "CPUUtilization"

  NAMESPACE = "AWS/EC2"

  STATISTIC = "Average"
  UNIT = "Percent"

  MIN = 0
  MAX = 100



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGDiskReadBytesMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "DiskReadBytes"

  NAMESPACE = "AWS/EC2"

  STATISTIC = "Average"
  UNIT = "Bytes"

  MIN = 0
  MAX = 1000000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGDiskWriteBytesMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "DiskWriteBytes"

  NAMESPACE = "AWS/EC2"

  STATISTIC = "Average"
  UNIT = "Bytes"

  MIN = 0
  MAX = 1000000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGNetworkInMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "NetworkIn"

  NAMESPACE = "AWS/EC2"

  STATISTIC = "Average"
  UNIT = "Bytes"

  MIN = 0
  MAX = 10000000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class ASGNetworkOutMetricAdapter(AutoScalingGroupAdapter):

  METRIC_NAME = "NetworkOut"

  NAMESPACE = "AWS/EC2"

  STATISTIC = "Average"
  UNIT = "Bytes"

  MIN = 0
  MAX = 10000000
