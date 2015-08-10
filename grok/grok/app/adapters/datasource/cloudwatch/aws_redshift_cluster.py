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

# Note: we don't allow autostacks of Redshift, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

import boto.redshift

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.exceptions import InvalidAWSRegionName



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class RedshiftClusterAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.REDSHIFT_CLUSTER

  # Cloudwatch metric dimension combinations supported by all metric adapters
  # on this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("ClusterIdentifier",),)


  @classmethod
  def describeResources(cls, region):
    """ Describe available Redshift Clusters in the given region.

    :param region: AWS region

    :returns: description of available Redshift Clusters in the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/auto-scaling-group/webserver-asg",
              "resID": "webserver-asg",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    try:
      redshiftConn = cls._connectToAWSService(boto.redshift, region)
    except InvalidAWSRegionName:
      # Redshift isn't implemented yet in several regions so an exception
      # is sometimes returned. This breaks parts of the web api, so instead of
      # raising the exception, an empty list is returned.
      return []

    clustersDescription = redshiftConn.describe_clusters()
    clusters = clustersDescription["DescribeClustersResponse"]\
      ["DescribeClustersResult"]["Clusters"]
    clusterNames = [cluster["Endpoint"]["Address"].split(".")[0]
                    for cluster in clusters]

    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]
    redshiftList = [{"grn": ("aws://%s/%s/%s" %
                             (region, instanceType, clusterName)),
                      "resID": clusterName,
                      "name": ""}
                     for clusterName in clusterNames]
    return redshiftList


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: str
    """
    return "%s for %s in %s" % (
      self.METRIC_NAME, self._dimensions["ClusterIdentifier"], self._region)



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class RSCDatabaseConnectionsMetricAdapter(RedshiftClusterAdapter):

  METRIC_NAME = "DatabaseConnections"

  IS_INSTANCE_DEFAULT = True

  NAMESPACE = "AWS/Redshift"

  STATISTIC = "Sum"
  UNIT = "Count"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 500
