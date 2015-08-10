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

"""
Base class for AWS Resource Adapters
"""

import collections
import datetime
import logging
import math

import boto.ec2
import boto.ec2.cloudwatch
import boto.exception


import YOMP.app
from YOMP.app.aws import cloudwatch_utils
import YOMP.app.exceptions



class ResourceTypeNames(object):
  """ AWS Resource types supported by the Datasource adapters. The type names
  are per AWSCloudFormation documentation, which defines a comprehensive list of
  AWS resource types. See
  http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/
    aws-template-resource-type-ref.html
  """

  AUTOSCALING_GROUP = "AWS::AutoScaling::AutoScalingGroup"

  DYNAMODB_TABLE = "AWS::DynamoDB::Table"

  EC2_INSTANCE = "AWS::EC2::Instance"

  EBS_VOLUME = "AWS::EC2::Volume"

  ELB_LOAD_BALANCER = "AWS::ElasticLoadBalancing::LoadBalancer"

  OPSWORKS_STACK = "AWS::OpsWorks::Stack"

  RDS_DBINSTANCE = "AWS::RDS::DBInstance"

  REDSHIFT_CLUSTER = "AWS::Redshift::Cluster"

  SNS_TOPIC = "AWS::SNS::Topic"

  SQS_QUEUE = "AWS::SQS::Queue"



class AWSResourceAdapterBase(object):
  """ Base class for AWS Resource Adapters

  IMPLEMENTATION NOTE: implementation shall retry on "throttle" and other
    transient errors for a reasonable amount of time, insulating callers from
    such details and hardship.
  """

  # Default granularity of metric datapoints in seconds; period must be at least
  # 60 seconds and must be a multiple of 60.
  METRIC_PERIOD = 300

  #
  # Class attributes required in Resource Adapters
  #

  # Resource type supported by the Resource Adapter; use constant from
  # .aws_base.ResourceTypeNames
  RESOURCE_TYPE = None

  #
  # Class attributes required in Metric Adapters
  #
  METRIC_NAME = None
  # True if the metric should be included by default for monitored instances.
  IS_INSTANCE_DEFAULT = False
  NAMESPACE = None
  # Cloudwatch metric dimension combinations supported by this adapter;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = None
  STATISTIC = None
  UNIT = None
  MIN = None
  MAX = None

  ###

  # Registry of resource adapters populated by our registerResourceAdapter
  # decorator
  # key: resource-type
  # value: resource adapter class
  _resourceRegistry = dict()

  # Registry of metric adapters populated by our registerMetricAdapter decorator
  # key: (namespace, metric-name, resource-dimension)
  # value: {"adapter": metric-adapter-class,
  #         "sortedDimensionGroups" : (sorted-group-list, ...)
  _metricRegistry = dict()

  # Registry of adapters per resource type for each metric that should be
  # monitored by default when monitoring an instance of that resource type.
  # This is populated by the metric adapter decorator.
  _defaultMetricRegistry = collections.defaultdict(list)


  def __init__(self, region, dimensions):
    """
    :param region: AWS region
    :param dimensions: dict of Cloudwatch dimensions for the metric
    """
    self._log = logging.getLogger("YOMP." + self.__class__.__name__)
    self._region = region
    self._dimensions = dimensions


  def __repr__(self):
    return "%s<ns=%s, name=%s, region=%s, dim=%s>" % (
      self.__class__.__name__,
      self.NAMESPACE,
      self.METRIC_NAME,
      self._region,
      self._dimensions)


  @classmethod
  def getResourceAdapterClass(cls, resourceType):
    return cls._resourceRegistry[resourceType]


  @classmethod
  def getDefaultResourceMetrics(cls, resourceType):
    return cls._defaultMetricRegistry[resourceType]


  def getResourceLocation(self):
    """ Get resource location value

    :returns: AWS Region
    :rtype: string
    """
    return self._region


  def getResourceName(self):  #pylint: disable=R0201
    """ Query AWS for the name value of the metric's resource

    NOTE: this method must be overridden by derived classes whose resource
      supports name tags; default behavior returns None.

    :returns: name value if available or None if not
    :rtype: string or NoneType
    """
    return None


  def getResourceStatus(self):  #pylint: disable=R0201
    """ Query AWS for the status of the metric's resource

    NOTE: this method must be overridden by derived classes whose resource
      supports status checks; default behavior returns None.

    :returns: AWS/resource-specific status string if supported and available or
      None if not
    :rtype: string or NoneType
    """
    return None


  def getMetricName(self):
    """ Get AWS Metric Name

    :returns: AWS Metric Name
    :rtype: string
    """
    return self.METRIC_NAME


  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    raise NotImplementedError


  def getMetricPeriod(self):
    """ Get metric period

    :returns: metric period in seconds
    :rtype: integer
    """
    return self.METRIC_PERIOD


  def getMetricDefaultMin(self):
    """ Get default min value for the metric's data

    :return: default min value for the metric's data or None if default is not
      defined
    :rtype: number (integer or float) or NoneType
    """
    return self.MIN


  def getMetricDefaultMax(self):
    """ Get default max value for the metric's data

    :return: default max value for the metric's data or None if default is not
      defined
    :rtype: number (integer or float) or NoneType
    """
    return self.MAX


  def getMetricData(self, start, end):
    """ Retrieve metric data for the given time range

    :param start: UTC start time of the metric data range. The start value
      is inclusive: results include datapoints with the time stamp specified. If
      set to None, the implementation will choose the start time automatically
      based on Cloudwatch metric data expiration policy (14 days at the time of
      this writing)
    :type start: datetime.datetime

    :param end: UTC end time of the metric data range. The end value is
      exclusive; results will include datapoints predating the time stamp
      specified. If set to None, will use the current UTC time as end
    :type end: datetime.datetime

    :returns: A two-tuple (<data-sequence>, <next-start-time>).
      <data-sequence> is a possibly empty sequence of data points sorted by
      timestamp in ascending order. Each data point is a two-tuple of
      (<datetime timestamp>, <value>).
      <next-start-time> is a datetime.datetime object indicating the UTC start
      time to use in next call to this method.
    :rtype: tuple
    """
    period = self.METRIC_PERIOD
    stats = [self.STATISTIC]

    samples = []

    start, end = cloudwatch_utils.getMetricCollectionTimeRange(
      startTime=start,
      endTime=end,
      period=period)

    nextCallStartTime = start

    # Calculate the number of records returned by this query
    remainingSampleSlots = (end - start).total_seconds() // period

    if remainingSampleSlots <= 0:
      self._log.warning("The requested date range=[%s..%s] is less than "
                        "period=%ss; adapter=%r", start, end, period, self)
    else:
      # AWS limits data access to 1440 records
      requestLimit = min(remainingSampleSlots, 1440)
      fromDate = start
      toDate = fromDate + datetime.timedelta(seconds=period * requestLimit)

      # Load data in blocks of up to 1440 records
      while not samples and toDate <= end and fromDate < toDate:
        nextCallStartTime = fromDate
        try:
          rawdata = self._queryCloudWatchMetricStats(
            period=period,
            start=fromDate,
            end=toDate,
            stats=stats)
        except boto.exception.BotoServerError as ex:
          if ex.status == 400 and ex.error_code == "Throttling":
            # TODO: unit-test
            raise YOMP.app.exceptions.MetricThrottleError(repr(ex))
          else:
            raise

        # AWS limits data access to 1440 records
        remainingSampleSlots = remainingSampleSlots - requestLimit
        fromDate = toDate
        requestLimit = min(remainingSampleSlots, 1440)
        toDate = fromDate + datetime.timedelta(seconds=period * requestLimit)

        if not rawdata:
          continue

        # Sort by "Timestamp"
        rawdata.sort(key=lambda row: row["Timestamp"])

        # Format raw data into data points and append to results
        samples.extend((e["Timestamp"], e[self.STATISTIC]) for e in rawdata)


    if samples:
      nextCallStartTime = samples[-1][0] + datetime.timedelta(seconds=period)

    return (samples, nextCallStartTime)


  def getMetricStatistics(self, start, end):
    """ Retrieve metric data statistics for the given time range

    :param start: UTC start time of the metric data range. The start value
      is inclusive: results include datapoints with the time stamp specified. If
      set to None, the implementation will choose the start time automatically
      based on Cloudwatch metric data expiration policy (14 days at the time of
      this writing)
    :type start: datetime.datetime

    :param end: UTC end time of the metric data range. The end value is
      exclusive; results will include datapoints predating the time stamp
      specified. If set to None, will use the current UTC time
    :type start: datetime.datetime

    :returns: a dictionary with the metric's statistics
    :rtype: dict; {"min": <min-value>, "max": <max-value>}
    """
    defaultMinVal = self.MIN
    defaultMaxVal = self.MAX

    start, end = cloudwatch_utils.getMetricCollectionTimeRange(
      startTime=start,
      endTime=end,
      period=self.METRIC_PERIOD)

    period = end - start
    totalSeconds = int(period.total_seconds())

    cloudStats = self._queryCloudWatchMetricStats(period=totalSeconds,
                                                  start=start,
                                                  end=end,
                                                  stats=("Maximum", "Minimum"))
    cloudStats = cloudStats[0] if cloudStats else None
    minVal, maxVal = self._normalizeMinMax(defaultMinVal, defaultMaxVal,
                                           cloudStats)

    self._log.debug("getMetricStatistics for metric %s: minVal=%g, maxVal=%g.",
                    self.METRIC_NAME, minVal, maxVal)

    return {"min": minVal, "max": maxVal}


  @classmethod
  def _normalizeMinMax(cls, defaultMinVal, defaultMaxVal, metricStats):
    """ Updates min and max based on values in CloudWatch stats default values,
    handling edge cases.

    NOTE: This is a class method because it is an entry point for GEF

    :param defaultMinVal:  The default minimum value
    :type defaultMinVal: float

    :param defaultMaxVal: The default maximum value
    :type defaultMaxVal: float

    :param metricStats: CloudWatch metric stats; None if not available
    :type metricStats: dict with properties: "Minimum" and "Maximum", whose
      values are floating point numbers; or None if metric stats are not
      available

    :rtype: tuple (minVal, maxVal)
    """
    minVal = defaultMinVal
    maxVal = defaultMaxVal

    # NOTE: implementation borrowed from legacy CloudwatchDataAdapter

    if metricStats:
      dataMin = metricStats["Minimum"]
      dataMax = metricStats["Maximum"]
      if minVal is None:
        minVal = dataMin
      # Override the max value using the data if necessary. For some of the
      # metrics, the max value in the JSON is not the theoretical max (it would
      # be incorrect to use the theoretical max since it is often way too high).
      # To handle these cases we check whether the observed max value is greater
      # than the max value specified in the JSON. If we do override from the
      # data we add an additional slop of 20%. Note: we don't have an issue with
      # the min value, which is almost always correctly 0.
      if (maxVal is None) or (maxVal < (1.2 * dataMax)):
        maxVal = 1.2 * dataMax

    # Handle edge cases which can happen with Cloudwatch.
    if (isinstance(minVal, float) and math.isnan(minVal)) or minVal is None:
      minVal = 0.0

    if (isinstance(maxVal, float) and math.isnan(maxVal)) or maxVal is None:
      maxVal = 1.0

    if maxVal <= minVal:
      maxVal = minVal + 1

    return minVal, maxVal


  @classmethod
  def listSupportedResourceTypes(cls):
    """ List supported resource types

    :returns: sequence of supported resource type names (per ResourceTypeNames)
    """
    return tuple(cls._resourceRegistry.iterkeys())


  @classmethod
  def describeSupportedMetrics(cls):
    """ Describe supported metrics

    :returns: description of supported metrics
    :rtype: dict

    ::

        {
            resource-type: {
              metric-name: {
                "namespace": "cw-namespace",
                "dimensionGroups": (dimension-tuple, ...)
                }
              },
              ...
            },
            ...
        }
    """
    description = dict()

    # key: (namespace, metric-name, resource-dimension)
    # value: {"adapter": metric-adapter-class,
    #         "sortedDimensionGroups" : (sorted-group-list, ...)

    for entry in cls._metricRegistry.itervalues():

      adapterClass = entry["adapter"]

      description.setdefault(
        adapterClass.RESOURCE_TYPE, dict())[adapterClass.METRIC_NAME] = dict(
        namespace=adapterClass.NAMESPACE,
        dimensionGroups=adapterClass.DIMENSION_GROUPS)

    return description


  @classmethod
  def describeResources(cls, region):
    """ Describe available resource-adapter-specific resources in the given
    region.

    NOTE: derived resource-adapter classes must override this method

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
    raise NotImplementedError


  @classmethod
  def describeResourcesByRegionAndType(cls, region, resourceType):
    """ Describe available AWS resources that are supported by YOMP within a
    given region and resources type.

    :param region: AWS region
    :param resourceType: type name of the resource (per ResourceTypeNames)

    :returns: description of available AWS resources for a given resource type
      in the given region

      ::
        describeResourcesByRegionAndType("us-west-2",
                                         ResourceTypeName.AUTOSCALING_GROUP)
        -->

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/auto-scaling-group/webserver-asg",
              "resID": "webserver-asg-micros01",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    return cls._resourceRegistry[resourceType].describeResources(region)


  @classmethod
  def getMatchingResources(cls, aggSpec):
    """ Get the resources that match an aggregation specification.

    To be overridden by each InstanceAdapter.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """
    raise NotImplementedError


  def getCanonicalResourceName(self):
    """
    :returns: a canonical resource identifier
    :rtype: string
    """

    # TODO MER-3316: This is an example, as the format is not finalized; the
    #   value needs to be encoded to account for spaces and other special
    #   characters in resource identifiers (some identifiers are named by user,
    #   such as AutoScalingGroupName)
    resourceID = self._dimensions[self._getResourceDimension()]
    return "%s/%s/%s" % (
      self._region,
      self.NAMESPACE,
      resourceID)


  @classmethod
  def _getResourceDimension(cls):
    """
    :returns: the dimension name that identifies the resource monitored by the
      cloudwatch metric
    """
    return cls.DIMENSION_GROUPS[0][0]


  @classmethod
  def createMetricAdapter(cls, metricSpec):
    """ Factory for metric adapters

    :param metricSpec: metric specification for Cloudwatch-based model
    :type metricSpec: dict

    ::

        {
          "region": "us-west-2",
          "namespace": "AWS/EC2",
          "metric": "CPUUtilization",
          "dimensions": {
            "InstanceId": "i-12d67826"
          }
        }

    :returns: metric adapter object that supports the given metricSpec
    :rtype: derived from AWSResourceAdapterBase class

    :raises YOMP.app.exceptions.MetricNotSupportedError: if requested metric
      isn't supported
    """
    metricClass = cls._findMetricAdapter(
      metricSpec["namespace"],
      metricSpec["metric"],
      metricSpec["dimensions"])

    return metricClass(region=metricSpec["region"],
                       dimensions=metricSpec["dimensions"])


  @classmethod
  def registerResourceAdapter(cls, clientCls):
    """ Decorator for registering derived Resource Adapter classes with the
    factory
    """
    key = clientCls.RESOURCE_TYPE
    assert key not in cls._resourceRegistry, (
      clientCls, key, cls._resourceRegistry[key])

    cls._resourceRegistry[key] = clientCls

    return clientCls


  @classmethod
  def registerMetricAdapter(cls, clientCls):
    """ Decorator for registering derived metric adapter classes with the
    factory
    """
    # Build default metrics map
    if clientCls.IS_INSTANCE_DEFAULT:
      cls._defaultMetricRegistry[clientCls.RESOURCE_TYPE].append(clientCls)

    resourceDimension = clientCls._getResourceDimension() #pylint: disable=W0212

    # Make sure resource dimension is same in all dimension groups
    for dimGroup in clientCls.DIMENSION_GROUPS:
      assert dimGroup[0] == resourceDimension, (
        clientCls, dimGroup, resourceDimension)

    key = cls._makeMetricAdapterKey(
      clientCls.NAMESPACE, clientCls.METRIC_NAME, resourceDimension)
    assert key not in cls._metricRegistry, (
      clientCls, key, cls._metricRegistry[key])

    cls._metricRegistry[key] = dict(
      adapter=clientCls,
      sortedDimensionGroups=tuple(sorted(group)
                                  for group in clientCls.DIMENSION_GROUPS)
    )

    return clientCls


  @classmethod
  def _makeMetricAdapterKey(cls, namespace, metricName, resourceDimension):
    """
    :param namespace: Cloudwatch namesapce
    :param metricName: Cloudwatch metric name
    :param resourceDimension: name of Cloudwatch dimension that identifies the
      resource that the metric is associated with
    """
    return (namespace, metricName, resourceDimension)


  @classmethod
  def _findMetricAdapter(cls, namespace, metricName, dimensions):
    """ Look up the metric adapter class

    :param namespace: Cloudwatch namesapce
    :param metricName: Cloudwatch metric name
    :param dimensions: sequence of Cloudwatch dimension names associated with
      the given metric

    :returns: metric adapter class

    :raises YOMP.app.exceptions.MetricNotSupportedError: if requested metric
      isn't supported
    """
    for dim in dimensions:
      entry = cls._metricRegistry.get(
        cls._makeMetricAdapterKey(namespace, metricName, dim))
      if entry is not None:
        break
    else:
      raise YOMP.app.exceptions.MetricNotSupportedError(
        "No matching metric adapter for namespace=%r, metric=%r, dimensions=%r"
        % (namespace, metricName, dimensions))

    adapterClass = entry["adapter"]

    # Verify that the dimensions match one of the dimension groups in the
    # metric adapter
    if sorted(dimensions) not in entry["sortedDimensionGroups"]:
      raise YOMP.app.exceptions.MetricNotSupportedError(
        "No matching dimension group in metric adapter=%r for dimensions=%r" %
        (adapterClass, dimensions))

    return adapterClass


  @classmethod
  def _queryResourceNameTagValue(cls, region, resourceTagType, resourceId):
    """ Get name tag value for the given resource

    :param region: AWS region name (e.g., "us-west-2")
    :type region: string

    :param resourceTagType: tag-resource-type filter value; valid values:
      customer-gateway, dhcp-options, image, instance, internet-gateway,
      network-acl, network-interface, reserved-instances, route-table,
      security-group, snapshot, spot-instances-request, subnet, volume, vpc,
      vpn-connection, vpn-gateway (see AWS API Reference for DescribeTags for
      the latest supported tag types)

    :param resourceId: id of the AWS resource

    :returns: name tag value if available or None if not
    :rtype: string or NoneType

    :raises YOMP.app.exceptions.InvalidAWSRegionName:
    """
    filters = {
      "resource-type": resourceTagType,
      "resource-id": resourceId,
      "key": "Name"
    }
    conn = cls._connectToAWSService(boto.ec2, region)
    tags = conn.get_all_tags(filters=filters)
    if tags:
      return tags[0].value

    return None


  @cloudwatch_utils.retryOnCloudWatchTransientError()
  def _queryCloudWatchMetricStats(self, period, start, end, stats, region=None):
    """ Retrieve the  time-series data for requested statistics of a given
    metric.

    NOTE: There is typically a latency in the availability of recent
      data points.

    NOTE: Also consider that the calling CPU's clock might not be exactly in
      sync with CloudWatch

    :param period: The granularity, in seconds, of the requested datapoints.
      Period must be at least 60 seconds and must be a multiple of 60.
    :type period: integer

    :param start: UTC start time of the metric data range. The start value
      is inclusive: results include datapoints with the time stamp specified.
    :type start: datetime.datetime

    :param end: UTC end time of the metric data range. The end value is
      exclusive; results will include datapoints predating the time stamp
      specified.
    :type start: datetime.datetime

    :param stats: a sequence of Cloudwatch metric statistic selectors,
      indicating which info to return
    ::
        ["Maximum", "Minimum"]
    ::
        ["Average"]

    :param region: Optional region override.

    :returns: an unordered sequence of map objects (dicts?) (per boto
      get_metric_statistics()). Each element corresponds to an available data
      point within the requested time range and correpsonding period. There may
      be gaps in the data (e.g., a service might have been idle and not reported
      metrics). Each element contains the requested stats as properties as well
      as a "Timestamp" property. The "Timestamp" property is a datatime.datetime
      object.
    """
    connection = self._connectToAWSService(boto.ec2.cloudwatch,
                                           region or self._region)
    data = connection.get_metric_statistics(
        period=period,
        start_time=start,
        end_time=end,
        metric_name=self.METRIC_NAME,
        namespace=self.NAMESPACE,
        statistics=stats,
        dimensions=self._dimensions,
        unit=self.UNIT)
    return data

  @classmethod
  def _connectToAWSService(cls, serviceModule, region):
    """ Connect to AWS service

    :param serviceModule: boto module for connecting; e.g., boto.ec2.cloudwatch

    :param region: The name of AWS Region to connect to (e.g., "us-west-2")
      applicable

    :returns: boto connection object

    :raises YOMP.app.exceptions.InvalidAWSRegionName:
    """
    conn = serviceModule.connect_to_region(
                region_name=region,
                **cls._getFreshAWSAuthenticationArgs())
    if conn is None:
      raise YOMP.app.exceptions.InvalidAWSRegionName(region)

    return conn


  @classmethod
  def _getFreshAWSAuthenticationArgs(cls):
    """
    :returns: dictionary with AWS connection authentication args;
    ::
      {
        "aws_access_key_id": <key-id-string>,
        "aws_secret_access_key": <secret-access-key-string>
      }
    """
    # Make sure we have the latest version of configuration
    # TODO: probably don't need to do this here. Instead, get them on demand in
    #   AWSResourceAdapterBase
    YOMP.app.config.loadConfig()

    return {
      "aws_access_key_id":
        YOMP.app.config.get("aws", "aws_access_key_id"),
      "aws_secret_access_key":
        YOMP.app.config.get("aws", "aws_secret_access_key")
    }

