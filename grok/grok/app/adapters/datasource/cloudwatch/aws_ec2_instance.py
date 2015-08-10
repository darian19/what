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


import boto.ec2
import boto.exception

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.aws.ec2_utils import getEC2Instances, retryOnEC2TransientError
from YOMP.app.runtime.aggregator_instances import getAutostackInstances



@AWSResourceAdapterBase.registerResourceAdapter
class InstanceAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.EC2_INSTANCE

  NAMESPACE = "AWS/EC2"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("InstanceId",),)


  def getResourceName(self):
    """ Query AWS for the name tag value of the metric's resource

    NOTE: overrides method in base class

    :returns: name tag value if available or None if not
    :rtype: string or NoneType
    """
    return self._queryResourceNameTagValue(
      region=self._region,
      resourceTagType="instance",
      resourceId=self._dimensions["InstanceId"])


  def getResourceStatus(self):
    """ Query AWS for the status of the metric's resource

    NOTE: overrides method in base class

    :returns: AWS/resource-specific status string if available or None if not
    :rtype: string or NoneType
    """
    @retryOnEC2TransientError()
    def getStatus():
      conn = self._connectToAWSService(boto.ec2, self._region)

      reservations = conn.get_all_instances(self._dimensions["InstanceId"])

      if reservations:
        reservation = next(iter(reservations))
        if reservation.instances:
          instance = next(iter(reservation.instances))
          return instance.state

      return None

    try:
      return getStatus()
    except boto.exception.EC2ResponseError as e:
      # Catch-all.  If status is not available, return None
      self._log.warn("getInstanceStatus failed (%r)", e)
      return None


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: overrides method in base class

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s on EC2 instance %s in %s region" % (
      self.METRIC_NAME, self._dimensions["InstanceId"], self._region)


  @classmethod
  def describeResources(cls, region):
    """ Describe available EC2 Instances in the given region.

    :param region: AWS region

    :returns: description of available EC2 Instances in the given region

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
    ec2Instances = getEC2Instances(region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    instanceList = [{"grn": ("aws://%s/%s/%s" %
                             (region, instanceType, instance.id)),
                      "resID": instance.id,
                      "name": instance.tags.get("Name", "")}
                     for instance in ec2Instances]
    return instanceList


  @classmethod
  def getMatchingResources(cls, aggSpec):
    """ Get the resources that match an aggregation specification.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """
    return getAutostackInstances(regionName=aggSpec["region"],
                                 filters=aggSpec["filters"])



@AWSResourceAdapterBase.registerMetricAdapter
class EC2CPUUtilizationMetricAdapter(InstanceAdapter):

  METRIC_NAME = "CPUUtilization"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "Percent"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100



@AWSResourceAdapterBase.registerMetricAdapter
class EC2DiskReadBytesMetricAdapter(InstanceAdapter):

  METRIC_NAME = "DiskReadBytes"

  STATISTIC = "Average"

  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 1000000



@AWSResourceAdapterBase.registerMetricAdapter
class EC2DiskWriteBytesMetricAdapter(InstanceAdapter):

  METRIC_NAME = "DiskWriteBytes"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 1000000



@AWSResourceAdapterBase.registerMetricAdapter
class EC2NetworkInMetricAdapter(InstanceAdapter):

  METRIC_NAME = "NetworkIn"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 10000000



@AWSResourceAdapterBase.registerMetricAdapter
class EC2NetworkOutMetricAdapter(InstanceAdapter):

  METRIC_NAME = "NetworkOut"

  STATISTIC = "Average"

  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 10000000
