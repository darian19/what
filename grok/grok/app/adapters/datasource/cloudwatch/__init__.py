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
AWS Cloudwatch Repository Adapter

TODO: MER-2949 decide our idempotency story of createMetric/monitorMetric calls
across *all* datasource adapters.
"""

import logging

import YOMP.app

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase, ResourceTypeNames)
from htmengine.adapters.datasource.datasource_adapter_iface import (
    DatasourceAdapterIface)

# Import all resource adapters to force registration
import YOMP.app.adapters.datasource.cloudwatch.aws_autoscaling_group
import YOMP.app.adapters.datasource.cloudwatch.aws_dynamodb_table
import YOMP.app.adapters.datasource.cloudwatch.aws_ebs_volume
import YOMP.app.adapters.datasource.cloudwatch.aws_ec2_instance
import YOMP.app.adapters.datasource.cloudwatch.aws_elb_load_balancer
import YOMP.app.adapters.datasource.cloudwatch.aws_opsworks_stack
import YOMP.app.adapters.datasource.cloudwatch.aws_rds_dbinstance
import YOMP.app.adapters.datasource.cloudwatch.aws_redshift_cluster
import YOMP.app.adapters.datasource.cloudwatch.aws_sns_topic
import YOMP.app.adapters.datasource.cloudwatch.aws_sqs_queue


import YOMP.app.exceptions
from YOMP.app import repository
from YOMP.app.repository import queries, schema
from htmengine.repository.queries import MetricStatus
from htmengine.runtime import scalar_metric_utils
import htmengine.utils
import htmengine.model_swapper.utils as model_swapper_utils
from YOMP.app.quota import Quota


# NOTE: we use an immutable data structure so that we may return it to callers
# without the risk of the contents being altered and without the need to copy it
_AWS_REGIONS = (
  ("ap-northeast-1", "Asia Pacific (Tokyo) Region"),
  ("ap-southeast-1", "Asia Pacific (Singapore) Region"),
  ("ap-southeast-2", "Asia Pacific (Sydney) Region"),
  ("eu-west-1", "EU (Ireland) Region"),
  ("sa-east-1", "South America (Sao Paulo) Region"),
  ("us-east-1", "US East (Northern Virginia) Region"),
  ("us-west-1", "US West (Northern California) Region"),
  ("us-west-2", "US West (Oregon) Region"),
)



# Mapping from namespace to resource type.
#
# This is a temporary mapping for the instance API that takes a namespace
# instead of a resource type.
NAMESPACE_TO_RESOURCE_TYPE = {
    "AWS/AutoScaling": ResourceTypeNames.AUTOSCALING_GROUP,
    "AWS/DynamoDB": ResourceTypeNames.DYNAMODB_TABLE,
    "AWS/EC2": ResourceTypeNames.EC2_INSTANCE,
    "AWS/EBS": ResourceTypeNames.EBS_VOLUME,
    "AWS/ELB": ResourceTypeNames.ELB_LOAD_BALANCER,
    "AWS/OpsWorks": ResourceTypeNames.OPSWORKS_STACK,
    "AWS/RDS": ResourceTypeNames.RDS_DBINSTANCE,
    "AWS/Redshift": ResourceTypeNames.REDSHIFT_CLUSTER,
    "AWS/SNS": ResourceTypeNames.SNS_TOPIC,
    "AWS/SQS": ResourceTypeNames.SQS_QUEUE,
}



@DatasourceAdapterIface.registerDatasourceAdapter
class _CloudwatchDatasourceAdapter(DatasourceAdapterIface):
  """ Datasource Adapter for Cloudwatch Metrics
  NOTE: DO NOT instantiate this class directly. Use Datasource Adapter factory
    instead: `YOMP.app.adapters.datasource.createDatasourceAdapter`; this is
    necessary for proper registration of all Datasource Adapters.

  IMPLEMENTATION NOTE: implementation shall retry on "throttle" and other
    transient errors for a reasonable amount of time, insulating callers from
    such details and hardship.
  """


  # Supported datasource (expected by
  # DatasourceAdapterIface.registerDatasourceAdapter)
  _DATASOURCE = "cloudwatch"


  def __init__(self, connectionFactory):
    """
    :param connectionFactory: connection factory for creating database
      connections.
    """
    super(_CloudwatchDatasourceAdapter, self).__init__()

    self._log = logging.getLogger("YOMP.cw_datasource_adapter")

    self.connectionFactory = connectionFactory


  @staticmethod
  def getDefaultModelSpecs(resourceType, region, instanceId,
                           dimension=None):
    """Gets model specs for the default metrics for the specified instance.

    :param resourceType: the resource type of the instance
    :param region: the region the instance is in
    :param instanceId: the resource-type-specific identifier for the instance
    :param dimension: the optional dimension name to use for the identifier to
        use instead of the defaults for the metrics
    :returns: a sequence of model spec dicts for each default metric
    """
    # Get the adapters for the resource types default metrics.
    defaultMetricAdapters = AWSResourceAdapterBase.getDefaultResourceMetrics(
        resourceType)

    # Build the model specs for the default metrics.
    modelSpecs = []
    for metricAdapter in defaultMetricAdapters:
      metricDimension = dimension or metricAdapter.DIMENSION_GROUPS[0][0]
      modelSpecs.append({
          "region": region,
          "namespace": metricAdapter.NAMESPACE,
          "datasource": "cloudwatch",
          "metric": metricAdapter.METRIC_NAME,
          # TODO: Is there a method for getting this or one we can make public?
          # TODO: Is this right?
          "dimensions": {metricDimension: instanceId},
      })

    return modelSpecs


  def monitorMetric(self, modelSpec):
    """ Start monitoring a metric; create a "cloudwatch model" DAO object for
    the given model specification.

    :param modelSpec: model specification for Cloudwatch-based model
    :type modelSpec: dict

    ::

        {
          "datasource": "cloudwatch",

          "metricSpec": {
            "region": "us-west-2",
            "namespace": "AWS/EC2",
            "metric": "CPUUtilization",
            "dimensions": {
              "InstanceId": "i-12d67826"
            }
          },

          # optional
          "modelParams": {
            "min": 0,  # optional
            "max": 100  # optional
          }
        }

    :returns: datasource-specific unique model identifier

    :raises YOMP.app.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist

    :raises YOMP.app.exceptions.MetricNotSupportedError: if requested metric
      isn't supported

    :raises YOMP.app.exceptions.MetricAlreadyMonitored: if the metric is already
      being monitored
    """
    metricSpec = modelSpec["metricSpec"]
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)

    # NOTE: getResourceName may be slow (AWS query)
    # TODO MER-3430: would be handy to use caching to speed things up a lot
    resourceName = metricAdapter.getResourceName()

    canonicalResourceName = self.getInstanceNameForModelSpec(modelSpec)
    resourceLocation = metricAdapter.getResourceLocation()
    metricName = metricAdapter.getMetricName()
    metricPeriod = metricAdapter.getMetricPeriod()
    metricDescription = metricAdapter.getMetricSummary()
    nameColumnValue = self._composeMetricNameColumnValue(
      metricName=metricName,
      metricNamespace=metricSpec["namespace"])

    # Determine if the model should be started. This will happen if the
    # nativeMetric input includes both "min" and "max" or we have default values
    # for both "min" and "max"
    defaultMin = metricAdapter.getMetricDefaultMin()
    defaultMax = metricAdapter.getMetricDefaultMax()
    if defaultMin is None or defaultMax is None:
      defaultMin = defaultMax = None

    # Get user-provided min/max, if any
    modelParams = modelSpec.get("modelParams", dict())
    explicitMin = modelParams.get("min")
    explicitMax = modelParams.get("max")
    if (explicitMin is None) != (explicitMax is None):
      raise ValueError(
        "min and max params must both be None or non-None; modelSpec=%r"
        % (modelSpec,))

    minVal = explicitMin if explicitMin is not None else defaultMin
    maxVal = explicitMax if explicitMax is not None else defaultMax
    stats = {"min": minVal, "max": maxVal}

    swarmParams = scalar_metric_utils.generateSwarmParams(stats)

    # Perform the start-monitoring operation atomically/reliably

    @repository.retryOnTransientErrors
    def startMonitoringWithRetries():
      """ :returns: metricId """
      with self.connectionFactory() as conn:
        with conn.begin():
          repository.lockOperationExclusive(conn,
                                            repository.OperationLock.METRICS)

          # Check if the metric is already monitored
          matchingMetrics = repository.getCloudwatchMetricsForNameAndServer(
            conn,
            nameColumnValue,
            canonicalResourceName,
            fields=[schema.metric.c.uid, schema.metric.c.parameters])

          for m in matchingMetrics:
            parameters = htmengine.utils.jsonDecode(m.parameters)
            if (parameters["metricSpec"]["dimensions"] ==
                metricSpec["dimensions"]):
              msg = ("monitorMetric: Cloudwatch modelId=%s is already "
                     "monitoring metric=%s on resource=%s; model=%r"
                     % (m.uid, nameColumnValue, canonicalResourceName, m))
              self._log.warning(msg)
              raise YOMP.app.exceptions.MetricAlreadyMonitored(msg, uid=m.uid)

          # Add a metric row for the requested metric
          metricDict = repository.addMetric(
            conn,
            name=nameColumnValue,
            description=metricDescription,
            server=canonicalResourceName,
            location=resourceLocation,
            poll_interval=metricPeriod,
            status=MetricStatus.UNMONITORED,
            datasource=self._DATASOURCE,
            parameters=htmengine.utils.jsonEncode(modelSpec),
            tag_name=resourceName)

          metricId = metricDict["uid"]

          self._log.info("monitorMetric: metric=%s, stats=%r", metricId, stats)

          # Start monitoring
          scalar_metric_utils.startMonitoring(
            conn=conn,
            metricId=metricId,
            swarmParams=swarmParams,
            logger=self._log)

          return metricId

    return startMonitoringWithRetries()


  def unmonitorMetric(self, metricId):
    """ Unmonitor a metric

    :param metricId: unique identifier of the metric row

    :raises YOMP.app.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist
    """
    # Delete the metric from the database
    with self.connectionFactory() as conn:
      repository.retryOnTransientErrors(repository.deleteMetric)(
        conn,
        metricId)

    # Send request to delete HTM model
    model_swapper_utils.deleteHTMModel(metricId)

    self._log.info("Cloudwatch Metric unmonitored: metric=%r", metricId)


  def activateModel(self, metricId):
    """ Start a model that is PENDING_DATA, creating the OPF/CLA model

    NOTE: used by MetricStreamer when model is in PENDING_DATA state and
      sufficient data samples are available to get statistics and complete model
      creation.

    :param metricId: unique identifier of the metric row

    :raises YOMP.app.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist

    :raises YOMP.app.exceptions.MetricStatisticsNotReadyError:
    """
    with self.connectionFactory() as conn:
      # TODO: This function is identical to custom metric activateModel()
      metricObj = repository.getMetric(conn,
                                       metricId,
                                       fields=[schema.metric.c.datasource,
                                               schema.metric.c.parameters])

    if metricObj.datasource != self._DATASOURCE:
      raise TypeError("activateModel: not a cloudwatch metric=%r"
                      % (metricObj,))


    if metricObj.parameters:
      parameters = htmengine.utils.jsonDecode(metricObj.parameters)
    else:
      parameters = {}

    stats = self._getMetricStatistics(parameters["metricSpec"])

    self._log.info("activateModel: metric=%s, stats=%r", metricId, stats)

    swarmParams = scalar_metric_utils.generateSwarmParams(stats)

    scalar_metric_utils.startModel(metricId,
                                   swarmParams=swarmParams,
                                   logger=self._log)



  def exportModel(self, metricId):
    """ Export the given model.

    :param metricId: datasource-specific unique metric identifier

    :returns: Model-export specification for Cloudwatch model
    :rtype: dict

    ::
        {
          "datasource": "cloudwatch",

          "metricSpec": {
            "region": "us-west-2",
            "namespace": "AWS/EC2",
            "metric": "CPUUtilization",
            "dimensions": {
              "InstanceId": "i-12d67826"
            }
          },

          # Same modelParams with which model was created, if any
          "modelParams": {
            "min": 0,  # optional
            "max": 100  # optional
          }
        }

    :raises YOMP.app.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist
    """
    with self.connectionFactory() as conn:
      metricObj = repository.retryOnTransientErrors(repository.getMetric)(
        conn, metricId, fields=[schema.metric.c.parameters])

    parameters = htmengine.utils.jsonDecode(metricObj.parameters)

    return parameters


  def importModel(self, spec):
    """ Import a model

    :param spec: datasource-specific value created by `exportModel`
    :type spec: dict

    :returns: datasource-specific unique metric identifier

    :raises YOMP.app.exceptions.MetricNotSupportedError: if requested metric
      isn't supported
    """
    try:
      return self.monitorMetric(spec)
    except YOMP.app.exceptions.MetricAlreadyMonitored as e:
      self._log.warning("importModel: metric already monitored; metricSpec=%s",
                        spec["metricSpec"])
      return e.uid


  def getMatchingResources(self, aggSpec):
    """ Get the resources that match an aggregation specification.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """
    resourceType = aggSpec["resourceType"]
    adapter = AWSResourceAdapterBase.getResourceAdapterClass(resourceType)
    return adapter.getMatchingResources(aggSpec)


  def getMetricResourceName(self, metricSpec):  # pylint: disable=R0201
    """ Query AWS for the NameTag of the metric's resource

    :returns: AWS/resource-specific status string if supported and available or
      None if not
    :rtype: string or NoneType
    """
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    return metricAdapter.getResourceName()


  def getMetricResourceStatus(self, metricSpec):  # pylint: disable=R0201
    """ Query AWS for the status of the metric's resource

    :returns: AWS/resource-specific status string if supported and available or
      None if not
    :rtype: string or NoneType
    """
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    return metricAdapter.getResourceStatus()


  def getMetricData(self, metricSpec, start, end):  # pylint: disable=R0201
    """ Retrieve metric data for the given time range

    :param metricSpec: metric specification for Cloudwatch-based model
    :type metricSpec: dict (see monitorMetric())

    :param start: UTC start time of the metric data range. The start value
      is inclusive: results include datapoints with the time stamp specified. If
      set to None, the implementation will choose the start time automatically
      based on Cloudwatch metric data expiration policy (14 days at the time of
      this writing)
    :type start: datetime.datetime

    :param end: UTC end time of the metric data range. The end value is
      exclusive; results will include datapoints predating the time stamp
      specified. If set to None, will use the current UTC time as end
    :type start: datetime.datetime

    :returns: A two-tuple (<data-sequence>, <next-start-time>).
      <data-sequence> is a possibly empty sequence of data points sorted by
      timestamp in ascending order. Each data point is a two-tuple of
      (<datetime timestamp>, <value>).
      <next-start-time> is a datetime.datetime object indicating the UTC start
      time to use in next call to this method.
    :rtype: tuple
    """
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    return metricAdapter.getMetricData(start, end)


  def describeRegions(self):  # pylint: disable=R0201
    """ Describe AWS regions

    :returns: region names and their descriptions
    :rtype: tuple of two-tuples

    ::

        (
          ("ap-northeast-1", "Asia Pacific (Tokyo) Region"),
          ("ap-southeast-1", "Asia Pacific (Singapore) Region"),
          ("ap-southeast-2", "Asia Pacific (Sydney) Region"),
          ...
        )
    """
    return _AWS_REGIONS


  def listSupportedResourceTypes(self):  # pylint: disable=R0201
    """ List supported resource types

    :returns: sequence of resource type names (per aws_base.ResourceTypeNames)

      ::

        ("AWS::AutoScaling::AutoScalingGroup", "AWS::EC2::Instance", ...)
    """
    return AWSResourceAdapterBase.listSupportedResourceTypes()


  def describeSupportedMetrics(self):  # pylint: disable=R0201
    """ Describe supported metrics, grouped by resource type (per
    aws_base.ResourceTypeNames)

    :returns: description of supported metrics, grouped by resource type.
    :rtype: dict

    ::

        {
            AWS::EC2::Instance: {
              "CPUUtilization": {
                "namespace": "AWS/EC2",
                "dimensionGroups": (("InstanceId",),)
                }
              },
              ...
            },
            ...
        }

    NOTE: this differs from the legacy getMetrics() primarily in that this new
      API is resource-oriented, while the legacy getMetrics() grouped results by
      Cloudwatch namespace. The new organization permits grouping of related
      metrics, such AWS/EC2 and AWS/AutoScale metrics on an Autoscaling region,
      by resource
    """
    return AWSResourceAdapterBase.describeSupportedMetrics()


  def describeResources(self, region, resourceType):  # pylint: disable=R0201
    """ Describe available AWS resources that are supported by YOMP within a
    given region and resources type.

    :param region: AWS region
    :param resourceType: type name of the resource (per
      aws_base.ResourceTypeNames)

    :returns: description of available AWS resources for a given resource type
      in the given region

      ::
        describeResources("us-west-2", ResourceTypeNames.AUTOSCALING_GROUP)
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
    return AWSResourceAdapterBase.describeResourcesByRegionAndType(region,
                                                                   resourceType)


  @classmethod
  def _composeMetricNameColumnValue(cls, metricName, metricNamespace):
    """ Compose the value to use in the name column of the metric row

    :param metricName: CloudWatch name of metric (e.g., "CPUUtilization")
    :param metricNamespace: the CloudWatch namespace in which the metric appears
    """
    return "%s/%s" % (metricNamespace, metricName)


  def _getMetricStatistics(self, metricSpec):  # pylint: disable=R0201
    """ Retrieve metric data statistics

    :param metricSpec: metric specification for Cloudwatch-based model
    :type metricSpec: dict (see monitorMetric())

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
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)

    return metricAdapter.getMetricStatistics(start=None, end=None)


  def getInstanceNameForModelSpec(self, spec):
    """ Get canonical instance name from a model spec

    :param modelSpec: Datasource-specific model specification
    :type modelSpec: JSONifiable dict

    :returns: Canonical instance name
    :rtype: str
    """
    metricSpec = spec["metricSpec"]
    metricAdapter = AWSResourceAdapterBase.createMetricAdapter(metricSpec)
    return metricAdapter.getCanonicalResourceName()

