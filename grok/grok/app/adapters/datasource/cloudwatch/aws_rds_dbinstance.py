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

# Note: we don't allow autostacks of RDS, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

import boto.rds
import boto.exception

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.aws.rds_utils import getRDSInstances, retryOnRDSTransientError


@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class RDSAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.RDS_DBINSTANCE

  NAMESPACE = "AWS/RDS"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("DBInstanceIdentifier",),)


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
              "grn": "aws://us-west-2/AWS/RDS/i-4be0d87f",
              "resID": "i-4be0d87f",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    dbinstances = getRDSInstances(region)
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    dbList = [{"grn": ("aws://%s/%s/%s" % (region, instanceType, db.id)),
                      "resID": db.id,
                      "name": ""} for db in dbinstances]
    return dbList


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return "%s on Database %s in %s" % (
      self.METRIC_NAME, self._dimensions["DBInstanceIdentifier"], self._region)


  def getResourceStatus(self):
    """ Query AWS for the status of the metric's resource

    NOTE: overrides method in base class

    :returns: AWS/resource-specific status string if available or None if not
    :rtype: string or NoneType
    """
    @retryOnRDSTransientError()
    def getStatus():
      conn = self._connectToAWSService(boto.rds, self._region)

      dbinstances = conn.get_all_dbinstances(
        self._dimensions["DBInstanceIdentifier"])

      if dbinstances:
        dbinstance = next(iter(dbinstances))
        return dbinstance.status

      return None

    try:
      return getStatus()
    except boto.exception.BotoServerError as e:
      # Catch-all.  If status is not available, return None
      self._log.warn("getInstanceStatus: get_all_dbinstances failed (%r)", e)
      return None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSCPUUtilizationMetricAdapter(RDSAdapter):

  METRIC_NAME = "CPUUtilization"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"
  UNIT = "Percent"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSDatabaseConnectionsMetricAdapter(RDSAdapter):

  METRIC_NAME = "DatabaseConnections"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"
  UNIT = "Count"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 1000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSDiskQueueDepthMetricAdapter(RDSAdapter):

  METRIC_NAME = "DiskQueueDepth"

  STATISTIC = "Average"
  UNIT = "Count"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 10000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSFreeableMemoryMetricAdapter(RDSAdapter):

  METRIC_NAME = "FreeableMemory"

  STATISTIC = "Average"
  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 300000000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSReadIOPSMetricAdapter(RDSAdapter):

  METRIC_NAME = "ReadIOPS"

  STATISTIC = "Average"
  UNIT = "Count/Second"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSReadLatencyMetricAdapter(RDSAdapter):

  METRIC_NAME = "ReadLatency"

  STATISTIC = "Average"
  UNIT = "Seconds"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 2.0



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSReadThroughputMetricAdapter(RDSAdapter):

  METRIC_NAME = "ReadThroughput"

  STATISTIC = "Average"
  UNIT = "Bytes/Second"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 1000000



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSSwapUsageMetricAdapter(RDSAdapter):

  METRIC_NAME = "SwapUsage"

  STATISTIC = "Average"
  UNIT = "Bytes"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSWriteIOPSMetricAdapter(RDSAdapter):

  METRIC_NAME = "WriteIOPS"

  STATISTIC = "Average"
  UNIT = "Count/Second"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSWriteLatencyMetricAdapter(RDSAdapter):

  METRIC_NAME = "WriteLatency"

  STATISTIC = "Average"
  UNIT = "Seconds"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 2.0



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RDSWWriteThroughputMetricAdapter(RDSAdapter):

  METRIC_NAME = "WriteThroughput"

  STATISTIC = "Average"
  UNIT = "Bytes/Second"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None
