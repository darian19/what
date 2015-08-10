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
Autostack metrics Adapter
"""

import logging

import YOMP.app
from YOMP.app import repository
import YOMP.app.adapters.datasource
from htmengine.adapters.datasource.datasource_adapter_iface import (
  DatasourceAdapterIface)
from YOMP.app.adapters.datasource.autostack.autostack_metric_adapter import (
  AutostackMetricAdapterBase)
import YOMP.app.exceptions

import htmengine.utils
from htmengine.runtime import scalar_metric_utils
import htmengine.model_swapper.utils as model_swapper_utils
from htmengine.repository.queries import MetricStatus
from YOMP.app.quota import Quota
from YOMP.app.repository import schema




MAX_INSTANCES_PER_AUTOSTACK = 500



@DatasourceAdapterIface.registerDatasourceAdapter
class _AutostackDatasourceAdapter(DatasourceAdapterIface):
  """ Datasource Adapter for YOMP Autostack Metrics

  NOTE: DO NOT instantiate this class directly. Use Datasource Adapter factory
    instead: `YOMP.app.adapters.datasource.createDatasourceAdapter`; this is
    necessary for proper registration of all Datasource Adapters.
  """

  # Supported datasource (expected by
  # DatasourceAdapterIface.registerDatasourceAdapter)
  _DATASOURCE = "autostack"


  def __init__(self, connectionFactory):
    """
    :param connectionFactory: connection factory for creating database
      connections.
    """
    super(_AutostackDatasourceAdapter, self).__init__()

    self._log = logging.getLogger("YOMP.autostack_datasource_adapter")

    self.connectionFactory = connectionFactory


  @staticmethod
  def _validateFilters(filters):
    """ Validate filters, raises an exception if check fails

    :param filters: Dictionary of filters; e.g.,
        {"tag:Name":["*test*", "*YOMP*"], "tag:Description":["Blah", "foo"]}
    :type filters: dict
    """
    try:
      assert isinstance(filters, dict)
      assert all(
        isinstance(key, basestring) and isinstance(value, list) and
        all(isinstance(filterValue, basestring) for filterValue in value)
        for key, value in filters.iteritems())
    except AssertionError:
      raise TypeError("filters argument must be a non-empty dict of filters; "
                      "each key is a filter name and corresponding value is a "
                      "list of filter strings. Got %r" % (filters,))


  def createAutostack(self, stackSpec):
    """ Create an "autostack"

    :param stackSpec: specification for an Autostack
    :type stackSpec: dict

    ::

        {
          "name": "all_web_servers",  # Autostack name
          "aggSpec": {  # aggregation spec
            "datasource": "cloudwatch",
            "region": "us-west-2",
            "resourceType": "AWS::EC2::Instance"
            "filters": {  # resourceType-specific filter
              "tag:Name":["*test*", "*YOMP*"], "tag:Description":["Blah", "foo"]
            },
          }
        }

    :returns: "autostack"
    """
    if "name" not in stackSpec or stackSpec["name"].strip() == "":
      raise ValueError("Must provide a valid name for the Autostack.")

    aggSpec = stackSpec["aggSpec"]
    filters = aggSpec["filters"]
    self._validateFilters(filters)

    region = aggSpec["region"]

    # Enforce the instances per AutoStack limit
    adapter = YOMP.app.adapters.datasource.createDatasourceAdapter(
      aggSpec["datasource"])
    instances = adapter.getMatchingResources(aggSpec)
    if len(instances) > MAX_INSTANCES_PER_AUTOSTACK:
      raise YOMP.app.exceptions.TooManyInstancesError(
        "The filters specified match %i instances but the limit per "
        "AutoStack is %i." % (len(instances), MAX_INSTANCES_PER_AUTOSTACK))

    name = stackSpec["name"]

    with self.connectionFactory() as conn:
      autostackDict = repository.addAutostack(
                        conn,
                        name=name,
                        region=region,
                        filters=htmengine.utils.jsonEncode(filters))
      autostackObj = repository.getAutostack(conn, autostackDict["uid"])

    return autostackObj


  def monitorMetric(self, modelSpec):
    """ Start monitoring a metric; create a model linked to an existing
    Autostack

    :param modelSpec: model specification for an Autostack-based model
    :type modelSpec: dict

    ::

        {
          "datasource": "autostack",

          "metricSpec": {
            # TODO [MER-3533]: This should be autostack name instead
            "autostackId": "a858c6990a444cd8a07466ec7f3cae16",

            "slaveDatasource": "cloudwatch",

            "slaveMetric": {
              # specific to slaveDatasource
              "namespace": "AWS/EC2",
              "metric": "CPUUtilization"
            },

            "period": 300  # aggregation period; seconds
          },

          "modelParams": { # optional; specific to slave metric
            "min": 0,  # optional
            "max": 100  # optional
          }
        }

    :returns: datasource-specific unique model identifier

    :raises YOMP.app.exceptions.ObjectNotFoundError: if referenced autostack
      doesn't exist

    :raises YOMP.app.exceptions.MetricNotSupportedError: if requested metric
      isn't supported

    :raises YOMP.app.exceptions.MetricAlreadyMonitored: if the metric is already
      being monitored
    """
    metricSpec = modelSpec["metricSpec"]
    autostackId = metricSpec["autostackId"]
    with self.connectionFactory() as conn:
      autostack = repository.getAutostack(conn, autostackId)

    slaveDatasource = metricSpec["slaveDatasource"]
    slaveMetric = metricSpec["slaveMetric"]

    canonicalResourceName = self.getInstanceNameForModelSpec(modelSpec)

    metricAdapter = AutostackMetricAdapterBase.getMetricAdapter(slaveDatasource)
    nameColumnValue = metricAdapter.getMetricName(slaveMetric)
    metricDescription = metricAdapter.getMetricDescription(slaveMetric,
                                                           autostack)
    queryParams = metricAdapter.getQueryParams(nameColumnValue)

    defaultMin = queryParams["min"]
    defaultMax = queryParams["max"]
    defaultPeriod = queryParams["period"]

    modelParams = modelSpec.get("modelParams", dict())
    explicitMin = modelParams.get("min")
    explicitMax = modelParams.get("max")
    explicitPeriod = metricSpec.get("period")
    if (explicitMin is None) != (explicitMax is None):
      raise ValueError(
        "min and max params must both be None or non-None; modelSpec=%r"
        % (modelSpec,))

    minVal = explicitMin if explicitMin is not None else defaultMin
    maxVal = explicitMax if explicitMax is not None else defaultMax
    period = explicitPeriod if explicitPeriod is not None else defaultPeriod
    stats = {"min": minVal, "max": maxVal}

    if minVal is None or maxVal is None:
      raise ValueError("Expected min and max to be set")

    swarmParams = scalar_metric_utils.generateSwarmParams(stats)

    @repository.retryOnTransientErrors
    def startMonitoringWithRetries():
      """
      :returns: metricId
      """
      with self.connectionFactory() as conn:
        with conn.begin():
          repository.lockOperationExclusive(conn,
                                            repository.OperationLock.METRICS)

          # Check if the metric is already monitored
          matchingMetrics = repository.getAutostackMetricsWithMetricName(
            conn,
            autostackId,
            nameColumnValue,
            fields=[schema.metric.c.uid])

          matchingMetric = next(iter(matchingMetrics), None)

          if matchingMetric:
            msg = ("monitorMetric: Autostack modelId=%s is already "
                   "monitoring metric=%s on resource=%s; model=%r"
                   % (matchingMetric.uid, nameColumnValue,
                      canonicalResourceName, matchingMetric))
            self._log.warning(msg)
            raise YOMP.app.exceptions.MetricAlreadyMonitored(
                    msg,
                    uid=matchingMetric.uid)

          # Add a metric row for the requested metric
          metricDict = repository.addMetric(
            conn,
            datasource=self._DATASOURCE,
            name=nameColumnValue,
            description=metricDescription,
            server=canonicalResourceName,
            location=autostack.region,
            tag_name=autostack.name,
            parameters=htmengine.utils.jsonEncode(modelSpec),
            poll_interval=period,
            status=MetricStatus.UNMONITORED)

          metricId = metricDict["uid"]

          repository.addMetricToAutostack(conn, autostackId, metricId)

          # Start monitoring
          scalar_metric_utils.startMonitoring(
            conn=conn,
            metricId=metricId,
            swarmParams=swarmParams,
            logger=self._log)

      self._log.info("monitorMetric: monitoring metric=%s, stats=%r",
                     metricId, stats)

      return metricId

    return startMonitoringWithRetries()


  def activateModel(self, _metricId):
    """ Start a model that is PENDING_DATA, creating the OPF/CLA model

    NOTE: used by MetricStreamer when model is in PENDING_DATA state and
      sufficient data samples are available to get statistics and complete model
      creation.

    NOTE: Currently, all Autostack metrics have min/max values, so this function
    should never be called. (N/A)

    :param metricId: unique identifier of the metric row

    :raises YOMP.app.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist

    :raises YOMP.app.exceptions.MetricStatisticsNotReadyError:
    """
    raise NotImplementedError("not-applicable")


  def unmonitorMetric(self, metricId):
    """ Unmonitor a metric

    :param metricId: unique identifier of the metric row

    :raises YOMP.app.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist
    """
    with self.connectionFactory() as conn:
      metricObj = repository.getMetric(conn, metricId)

      # Delete the metric from the database
      repository.retryOnTransientErrors(repository.deleteMetric)(conn,
                                                                 metricId)

    # Send request to delete CLA model
    model_swapper_utils.deleteHTMModel(metricId)

    self._log.info("Autostack Metric unmonitored: metric=%r", metricObj)


  def exportModel(self, metricId):
    """ Export the given model.

    :param metricId: datasource-specific unique metric identifier

    :returns: Model-export specification for the Autostack model
    :rtype: dict

    ::
        {
          "datasource": "autostack",

          "stackSpec": {
            "name": "all_web_servers",  # Autostack name
            "aggSpec": {  # aggregation spec
              "datasource": "cloudwatch",
              "region": "us-west-2",
              "resourceType": "AWS::EC2::Instance"
              "filters": {  # resourceType-specific filter
                "tag:Name":["*test*", "*YOMP*"],
                "tag:Description":["Blah", "foo"]
              },
            }
          },

          "modelSpec": {
            "datasource": "autostack",

            "metricSpec": {
              "slaveDatasource": "cloudwatch",

              "slaveMetric": {
                # specific to slaveDatasource
                "namespace": "AWS/EC2",
                "metric": "CPUUtilization"
              },

              "period": 300  # aggregation period; seconds
            },

            "modelParams": { # optional; specific to slave metric
              "min": 0,  # optional
              "max": 100  # optional
            }
          }
        }

    """
    with self.connectionFactory() as conn:
      spec = {}
      spec["datasource"] = self._DATASOURCE

      metricObj = repository.getMetric(conn,
                                       metricId,
                                       fields=[schema.metric.c.parameters])
      autostackObj = repository.getAutostackFromMetric(conn, metricId)

    parameters = htmengine.utils.jsonDecode(metricObj.parameters)
    spec["modelSpec"] = parameters
    modelSpec = spec["modelSpec"]
    metricSpec = modelSpec["metricSpec"]
    del metricSpec["autostackId"]

    spec["stackSpec"] = {}
    stackSpec = spec["stackSpec"]
    stackSpec["name"] = autostackObj.name

    # Only supporting cloudwatch / EC2 for now
    stackSpec["aggSpec"] = {}
    aggSpec = stackSpec["aggSpec"]
    aggSpec["datasource"] = "cloudwatch"
    aggSpec["region"] = autostackObj.region
    aggSpec["resourceType"] = "AWS::EC2::Instance"
    aggSpec["filters"] = htmengine.utils.jsonDecode(autostackObj.filters)

    return spec


  def importModel(self, spec):
    """ Import a model

    :param spec: datasource-specific value created by `exportModel`
    :type spec: dict

    :returns: datasource-specific unique metric identifier
    """
    stackSpec = spec["stackSpec"]
    aggSpec = stackSpec["aggSpec"]

    try:
      with self.connectionFactory() as conn:
        autostackObj = repository.getAutostackForNameAndRegion(
          conn,
          stackSpec["name"],
          aggSpec["region"])
    except YOMP.app.exceptions.ObjectNotFoundError:
      autostackObj = self.createAutostack(stackSpec)

    modelSpec = spec["modelSpec"]
    metricSpec = modelSpec["metricSpec"]
    metricSpec["autostackId"] = autostackObj.uid

    try:
      return self.monitorMetric(modelSpec)
    except YOMP.app.exceptions.MetricAlreadyMonitored as e:
      self._log.warning("importModel: Autostack metric already monitored; "
                        "metricSpec=%s", metricSpec)
      return e.uid


  def getMatchingResources(self, aggSpec):
    """ Get the resources that match an aggregation specification.

    NOTE: Since we don't support autostacks of autostacks, this function is N/A.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """
    raise NotImplementedError("not-applicable")


  def _getMetricStatistics(self, aggSpec, metricSpec):
    """ Retrieve metric data statistics

    NOTE: Since activateModel is N/A, this function should never be called.
    (N/A)

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see createAutostack)

    :param metricSpec: Autostack metric specification
    :type metricSpec: dict (see monitorMetric)

    :returns: a dictionary with the metric's statistics
    :rtype: dict; {"min": <min-value>, "max": <max-value>}
    """
    raise NotImplementedError("not-applicable")


  def _getCanonicalResourceName(self, autostackUid):  # pylint: disable=R0201
    return "Autostacks/{0}".format(autostackUid)


  def getInstanceNameForModelSpec(self, spec):
    """ Get canonical instance name from a model spec

    :param modelSpec: Model specification or import model specification
    :type modelSpec: JSONifiable dict

    :returns: Canonical instance name; None if autostack doesn't exist
    :rtype: str or None
    """
    if "metricSpec" in spec:
      autostackId = spec["metricSpec"]["autostackId"]
    else:
      # Proceed as if for an import-model-spec
      stackSpec = spec["stackSpec"]
      aggSpec = stackSpec["aggSpec"]

      try:
        with self.connectionFactory() as conn:
          autostackObj = repository.getAutostackForNameAndRegion(
            conn,
            stackSpec["name"],
            aggSpec["region"])
      except YOMP.app.exceptions.ObjectNotFoundError:
        return None
      else:
        autostackId = autostackObj.uid

    return self._getCanonicalResourceName(autostackId)

