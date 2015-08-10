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
HTM Engine Metric Datasource Adapter
"""

import copy
import datetime

from htmengine.adapters.datasource.datasource_adapter_iface import (
    DatasourceAdapterIface)

import htmengine.exceptions as app_exceptions
from htmengine import htmengine_logging

from htmengine import repository
from htmengine.repository import schema
from htmengine.repository.queries import MetricStatus
from htmengine.runtime import scalar_metric_utils
import htmengine.utils
import htmengine.model_swapper.utils as model_swapper_utils



@DatasourceAdapterIface.registerDatasourceAdapter
class _CustomDatasourceAdapter(DatasourceAdapterIface):
  """ Datasource Adapter for HTM Metrics.

  NOTE: DO NOT instantiate this class directly. Use Datasource Adapter factory
    instead: `htmengine.adapters.datasource.createDatasourceAdapter`; this is
    necessary for proper registration of all Datasource Adapters.
  """

  # Supported datasource (expected by
  # DatasourceAdapterIface.registerDatasourceAdapter)
  _DATASOURCE = "custom"

  # Default metric period value to use when it's unknown
  # TODO: Should we use 0 since it's unknown "unknown" or default to 5 min?
  #   Consider potential impact on web charts, YOMP-mobile
  _DEFAULT_METRIC_PERIOD = 300  # 300 sec = 5 min


  def __init__(self, connectionFactory):
    """
    :param connectionFactory: connection factory for creating database
      connections.
    """
    super(_CustomDatasourceAdapter, self).__init__()

    self._log = htmengine_logging.getExtendedLogger(
      "htmengine.custom_datasource_adapter")

    self.connectionFactory = connectionFactory


  @repository.retryOnTransientErrors
  def createMetric(self, metricName):
    """Create scalar HTM metric if it doesn't exist

    NOTE: this method is specific to HTM Metrics, where metric creation
      happens separately from model creation.

    :param metricName: name of the HTM metric
    :type metricName: string

    :rtype: unique metric identifier

    :raises htmengine.exceptions.MetricAlreadyExists: if a metric with same
      name already exists
    """
    with self.connectionFactory() as conn:
      return self._createMetric(conn, metricName)


  def _createMetric(self, conn, metricName):
    """ Create scalar HTM metric if it doesn't exist

    :param conn: SQLAlchemy;
    :type conn: sqlalchemy.engine.Connection

    :param metricName: name of the HTM metric
    :type metricName: string

    :rtype: unique HTM metric identifier

    :raises htmengine.exceptions.MetricAlreadyExists: if a metric with same
      name already exists
    """
    resource = self._makeDefaultResourceName(metricName)

    # First, try to get it without locking (faster in typical case)
    try:
      with self.connectionFactory() as conn:
        metricObj = repository.getCustomMetricByName(
          conn,
          metricName,
          fields=[schema.metric.c.uid])
    except app_exceptions.ObjectNotFoundError:
      pass
    else:
      raise app_exceptions.MetricAlreadyExists(
        "Custom metric with matching name already exists: "
        "metric=%s, name=%s" % (metricObj.uid, metricName,),
        uid=metricObj.uid)

    with self.connectionFactory() as conn:
      with conn.begin():
        repository.lockOperationExclusive(conn,
                                          repository.OperationLock.METRICS)

        try:
          # Check again under lock, to avoid race condition with another process
          metricObj = repository.getCustomMetricByName(
            conn,
            metricName,
            fields=[schema.metric.c.uid])
        except app_exceptions.ObjectNotFoundError:
          pass
        else:
          return metricObj.uid

        metricDict = repository.addMetric(
          conn,
          name=metricName,
          description="Custom metric %s" % (metricName,),
          server=resource,
          location="",
          poll_interval=self._DEFAULT_METRIC_PERIOD,
          status=MetricStatus.UNMONITORED,
          datasource=self._DATASOURCE)

        return metricDict["uid"]


  def deleteMetricByName(self, metricName):
    """ Delete both metric and corresponding model (if any)

    NOTE: this method is specific to HTM Metrics

    :param metricName: name of the HTM metric
    :type metricName: string

    :raises htmengine.exceptions.ObjectNotFoundError: if the requested metric
      doesn't exist
    """

    with self.connectionFactory() as conn:
      metricObj = repository.retryOnTransientErrors(
        repository.getCustomMetricByName)(conn,
                                          metricName,
                                          fields=[schema.metric.c.uid,
                                                  schema.metric.c.status])

    if metricObj.status != MetricStatus.UNMONITORED:
      self.unmonitorMetric(metricObj.uid)

    # Delete the metric from the database
    with self.connectionFactory() as conn:
      repository.retryOnTransientErrors(repository.deleteMetric)(
        conn,
        metricObj.uid)

    self._log.info("HTM Metric deleted: metric=%s; name=%s",
                   metricObj.uid, metricName)


  def monitorMetric(self, modelSpec):
    """ Start monitoring a metric; perform model creation logic specific to
    custom metrics.

    Start the model if possible: this will happen if modelParams includes both
    "min" and "max" or there is enough data to estimate them.

    :param modelSpec: model specification for HTM model; per
        ``model_spec_schema.json`` with the ``metricSpec`` property per
        ``custom_metric_spec_schema.json``
    :type modelSpec: dict

    ::
      1st variant: `uid` is the unique id of an existing metric;
        # TODO: it would be preferable to punt on this variant, and refer
        #  to custom metric by name in modelSpec for consistency with
        # import/export. Web GUI uses metric name; some tests use this variant,
        # though.
        {
          "datasource": "custom",

          "metricSpec": {
            "uid": "4a833e2294494b4fbc5004e03bad45b6",
            "unit": "Count",  # optional
            "resource": "prod.web1",  # optional
            "userInfo": {"symbol": "<TICKER_SYMBOL>"} # optional
          },

          # Optional model params
          "modelParams": {
            "min": min-value,  # optional
            "max": max-value  # optional
          }
        }

    ::

      2nd variant: `metric` is the unique name of the metric; a new custom
      metric row will be created with this name, if it doesn't exit
        {
          "datasource": "custom",

          "metricSpec": {
            "metric": "prod.web.14.memory",
            "unit": "Count",  # optional
            "resource": "prod.web1",  # optional
            "userInfo": {"symbol": "<TICKER_SYMBOL>"} # optional
          },

          # Optional model params
          "modelParams": {
            "min": min-value,  # optional
            "max": max-value  # optional
          }
        }

    :returns: datasource-specific unique model identifier

    :raises ValueError: if finds something invalid in arg

    :raises TypeError: if metric with the referenced uid is not a custom metric

    :raises htmengine.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist

    :raises htmengine.exceptions.MetricNotSupportedError: if requested metric
      isn't supported

    :raises htmengine.exceptions.MetricAlreadyMonitored: if the metric is already
      being monitored
    """
    metricSpec = modelSpec["metricSpec"]

    with self.connectionFactory() as conn:
      if "uid" in metricSpec:
        # Via metric ID
        metricId = metricSpec["uid"]
        # Convert modelSpec to canonical form
        modelSpec = copy.deepcopy(modelSpec)
        modelSpec["metricSpec"].pop("uid")
        modelSpec["metricSpec"]["metric"] = (
          repository.retryOnTransientErrors(repository.getMetric)(
            conn, metricId).name)
      elif "metric" in metricSpec:
        # Via metric name
        try:
          # Crete the metric, if needed
          metricId = repository.retryOnTransientErrors(self._createMetric)(
            conn, metricSpec["metric"])
        except app_exceptions.MetricAlreadyExists as e:
          # It already existed
          metricId = e.uid
      else:
        raise ValueError(
          "Neither uid nor metric name present in metricSpec; modelSpec=%r"
          % (modelSpec,))

      modelParams = modelSpec.get("modelParams", dict())
      minVal = modelParams.get("min")
      maxVal = modelParams.get("max")
      minResolution = modelParams.get("minResolution")
      if (minVal is None) != (maxVal is None):
        raise ValueError(
          "min and max params must both be None or non-None; metric=%s; "
          "modelSpec=%r" % (metricId, modelSpec,))

    # Start monitoring
    if minVal is None or maxVal is None:
      minVal = maxVal = None

      with self.connectionFactory() as conn:
        numDataRows = repository.retryOnTransientErrors(
          repository.getMetricDataCount)(conn, metricId)

      if numDataRows >= scalar_metric_utils.MODEL_CREATION_RECORD_THRESHOLD:
        try:
          stats = self._getMetricStatistics(metricId)
          self._log.info("monitorMetric: trigger numDataRows=%d, stats=%s",
                         numDataRows, stats)
          minVal = stats["min"]
          maxVal = stats["max"]
        except app_exceptions.MetricStatisticsNotReadyError:
          pass

    stats = {"min": minVal, "max": maxVal, "minResolution": minResolution}
    self._log.debug("monitorMetric: metric=%s, stats=%r", metricId, stats)

    swarmParams = scalar_metric_utils.generateSwarmParams(stats)

    self._startMonitoringWithRetries(metricId, modelSpec, swarmParams)

    return metricId


  @repository.retryOnTransientErrors
  def _startMonitoringWithRetries(self, metricId, modelSpec, swarmParams):
    """ Perform the start-monitoring operation atomically/reliably

    :param metricId: unique identifier of the metric row

    :param modelSpec: same as `modelSpec`` from `monitorMetric`

    :param swarmParams: object returned by
      scalar_metric_utils.generateSwarmParams()

    :raises htmengine.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist

    :raises htmengine.exceptions.MetricNotSupportedError: if requested metric
      isn't supported

    :raises htmengine.exceptions.MetricAlreadyMonitored: if the metric is
      already being monitored
    """
    with self.connectionFactory() as conn:
      with conn.begin():
        # Lock the metric to synchronize with metric streamer; must be first
        # call at start of transaction
        metricObj = repository.getMetricWithUpdateLock(conn, metricId)

        if metricObj.datasource != self._DATASOURCE:
          raise TypeError("Not an HTM metric=%r; modelSpec=%r"
                          % (metricObj, modelSpec))

        if metricObj.status != MetricStatus.UNMONITORED:
          self._log.info("monitorMetric: already monitored; metric=%r",
                         metricObj)
          raise app_exceptions.MetricAlreadyMonitored(
            ("Custom metric=%s is already monitored by model=%r"
             % (metricObj.name, metricObj,)),
            uid=metricId)

        # Save model specification in metric row
        update = {"parameters": htmengine.utils.jsonEncode(modelSpec)}
        instanceName = self.getInstanceNameForModelSpec(modelSpec)
        if instanceName is not None:
          update["server"] = instanceName
        repository.updateMetricColumns(conn, metricId, update)

        modelStarted = scalar_metric_utils.startMonitoring(
          conn=conn,
          metricId=metricId,
          swarmParams=swarmParams,
          logger=self._log)

        if modelStarted:
          scalar_metric_utils.sendBacklogDataToModel(
            conn=conn,
            metricId=metricId,
            logger=self._log)


  def activateModel(self, metricId):
    """ Start a model that is PENDING_DATA, creating the OPF/CLA model

    NOTE: used by MetricStreamer when model is in PENDING_DATA state and
      sufficient data samples are available to get statistics and complete model
      creation.

    :param metricId: unique identifier of the metric row

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist

    :raises htmengine.exceptions.MetricStatisticsNotReadyError:
    """
    # Load the existing metric
    with self.connectionFactory() as conn:
      metricObj = repository.getMetric(conn,
                                       metricId,
                                       fields=[schema.metric.c.datasource])

    if metricObj.datasource != self._DATASOURCE:
      raise TypeError(
        "activateModel: not an HTM metric=%s; datasource=%s" %
        (metricId, metricObj.datasource))

    stats = self._getMetricStatistics(metricId)

    swarmParams = scalar_metric_utils.generateSwarmParams(stats)

    scalar_metric_utils.startModel(metricId,
                                   swarmParams=swarmParams,
                                   logger=self._log)


  def unmonitorMetric(self, metricId):
    """ Unmonitor a metric

    :param metricId: unique identifier of the metric row

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist
    """
    @repository.retryOnTransientErrors
    def updateMetric():
      with self.connectionFactory() as conn:
        repository.deleteModel(conn, metricId)

    updateMetric()

    model_swapper_utils.deleteHTMModel(metricId)

    self._log.info("HTM Metric unmonitored: metric=%r", metricId)


  def exportModel(self, metricId):
    """ Export the given model

    :param metricId: datasource-specific unique metric identifier

    :returns: model-export specification for HTM model
    :rtype: dict

    ::

        {
          "datasource": "custom",

          "metricSpec": {
            "metric": "prod.web.14.memory",
            "unit": "Count" # optional
          },

          # Optional model params
          "modelParams": {
            "min": min-value,  # optional
            "max": max-value  # optional
          },

          "data": [[value, datetime.datetime], ...]  # optional
        }

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist
    """
    with self.connectionFactory() as conn:
      metricObj = repository.retryOnTransientErrors(repository.getMetric)(
        conn, metricId)

      if metricObj.datasource != self._DATASOURCE:
        raise TypeError("exportModel: not an HTM metric=%r"
                        % (metricObj,))
      data = repository.getMetricData(
        conn,
        metricId,
        fields=[schema.metric_data.c.metric_value,
                schema.metric_data.c.timestamp],
        fromTimestamp=datetime.datetime.utcnow() - datetime.timedelta(days=14))

    modelSpec = htmengine.utils.jsonDecode(metricObj.parameters)
    modelSpec["data"] = list(data)

    return modelSpec


  def importModel(self, spec):
    """ Import a model

    :param spec: datasource-specific value created by `exportModel`
    :type spec: dict

    ::

        {
          "datasource": "custom",

          "metricSpec": {
            "metric": "prod.web.14.memory",
            "unit": "Count" # optional
          },

          # Optional model params
          "modelParams": {
            "min": min-value,  # optional
            "max": max-value  # optional
          },

          "data": [[value, "2014-07-17 01:36:48"], ...]  # optional
        }

    :returns: datasource-specific unique metric identifier
    """

    try:
      metricId = self.createMetric(spec["metricSpec"]["metric"])
    except app_exceptions.MetricAlreadyExists as e:
      metricId = e.uid

    with self.connectionFactory() as conn:
      metricObj = repository.retryOnTransientErrors(repository.getMetric)(
        conn, metricId)
      if metricObj.status != MetricStatus.UNMONITORED:
        self._log.info("importModel: metric is already monitored: %r",
                       metricObj)
        return metricId

      # Add data
      data = spec.get("data")
      if data:
        if repository.getMetricDataCount(conn, metricId) == 0:
          repository.retryOnTransientErrors(repository.addMetricData)(conn,
                                                                      metricId,
                                                                      data)

    # Start monitoring
    modelSpec = spec.copy()
    modelSpec.pop("data", None)
    return self.monitorMetric(modelSpec)


  def getMatchingResources(self, aggSpec):
    """ Get the resources that match an aggregation specification.

    Note: Not currently supported by custom metrics.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """
    raise NotImplementedError("not-supported")


  def _getMetricStatistics(self, metricId):
    """ Get metric data statistics

    :param metricId: unique identifier of the metric row

    :returns: a dictionary with the metric's statistics
    :rtype: dict; {"min": <min-value>, "max": <max-value>}

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist

    :raises htmengine.exceptions.MetricStatisticsNotReadyError:
    """
    with self.connectionFactory() as conn:
      stats = repository.retryOnTransientErrors(repository.getMetricStats)(
        conn, metricId)

    minVal = stats["min"]
    maxVal = stats["max"]

    # Handle an edge case which should almost never happen
    # (borrowed from legacy custom adapter logic)
    if maxVal <= minVal:
      self._log.warn("Max encoder value (%g) is not greater than min (%g).",
                     maxVal if maxVal is not None else float("nan"),
                     minVal if minVal is not None else float("nan"))
      maxVal = minVal + 1

    # Add a 20% buffer on both ends of the range
    # (borrowed from legacy custom adapter)
    buff = (maxVal - minVal) * 0.2
    minVal -= buff
    maxVal += buff

    self._log.debug("getMetricStatistics for metric=%s: minVal=%g, "
                    "maxVal=%g.", metricId, minVal, maxVal)

    return {"max": maxVal,
            "min": minVal}


  @classmethod
  def _makeDefaultResourceName(cls, metricName):
    """ Construct the default resource name for a given metric

    :param metricName: unique name of the metric
    """
    return metricName


  def getInstanceNameForModelSpec(self, spec):
    """ Get canonical instance name from a model spec

    :param modelSpec: Datasource-specific model specification
    :type modelSpec: JSONifiable dict

    :returns: Canonical instance name
    :rtype: str or None
    """
    if "resource" in spec["metricSpec"]:
      return spec["metricSpec"]["resource"]
