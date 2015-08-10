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

import json



class AutostackMetricAdapterBase(object):
  """ Base class for Autostack Metric Adapter """

  _adapterRegistry = {}

  # To be overridden by derived classes
  _QUERY_PARAMS = {}


  @classmethod
  def getMetricAdapter(cls, datasource):
    """
    :param datasource: Datasource (eg. cloudwatch)
    :type datasource: string

    :returns: AutostackMetricAdapterBase instance
    """
    if not datasource in cls._adapterRegistry:
      raise ValueError("Unregistered datasource: ".format(datasource))

    return cls._adapterRegistry[datasource]


  @classmethod
  def getMetricDatasource(cls, metric):
    """
    :param metric: Metric object
    :type metric: Metric

    :returns: Datasource for metric
    :rtype: string
    """
    params = json.loads(metric.parameters)
    return params["metricSpec"]["slaveDatasource"]


  @classmethod
  def getQueryParams(cls, metricName):
    """ Get query params for a type of metric

    :param metricName: Metric name
    :type metricName: string

    :returns: query params
    :rtype: dict
    """
    if not metricName in cls._QUERY_PARAMS:
      raise ValueError("Metric not supported: {0}".format(metricName))

    return cls._QUERY_PARAMS[metricName]


  @classmethod
  def registerMetricAdapter(cls, clientCls):
    """
    Decorator for registering derived Autostack Metric Adapter classes
    with the base
    """
    key = clientCls._DATASOURCE #pylint: disable=W0212
    assert key not in cls._adapterRegistry, (
      clientCls, key, cls._adapterRegistry[key])

    cls._adapterRegistry[key] = clientCls

    return clientCls


  @classmethod
  def getMetricName(cls, slaveMetric):
    """ Get the metric name given a slave metric

    NOTE: derived classes must override this method

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :returns: metric name
    :rtype: string
    """
    raise NotImplementedError


  @classmethod
  def getMetricDescription(cls, slaveMetric, autostack):
    """ Get the metric name given a slave metric

    NOTE: derived classes must override this method

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :param autostack: Autostack that metric belongs to
    :type autostack: Autostack

    :returns: metric name
    :rtype: string
    """
    raise NotImplementedError



@AutostackMetricAdapterBase.registerMetricAdapter
class CloudwatchAutostackMetricAdapter(AutostackMetricAdapterBase):
  """ Autostack Metric Adapter for Cloudwatch """

  _DATASOURCE = "cloudwatch"

  _QUERY_PARAMS = {
    "AWS/EC2/CPUUtilization": {
      "statistics": "Average",
      "unit": "Percent",
      "min": 0,
      "max": 100,
      "period": 300,
    },
    "AWS/EC2/DiskReadBytes": {
      "statistics": "Average",
      "unit": "Bytes",
      "min":0,
      "max":1000000,
      "period": 300,
    },
    "AWS/EC2/DiskWriteBytes": {
      "statistics": "Average",
      "unit": "Bytes",
      "min":0,
      "max":1000000,
      "period": 300,
    },
    "AWS/EC2/NetworkIn": {
      "statistics": "Average",
      "unit": "Bytes",
      "min":0,
      "max":10000000,
      "period": 300,
    },
    "AWS/EC2/NetworkOut": {
      "statistics": "Average",
      "unit": "Bytes",
      "min":0,
      "max":10000000,
      "period": 300,
      }
  }

  @classmethod
  def getMetricName(cls, slaveMetric):
    """ Get the metric name given a slave metric

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :returns: metric name
    :rtype: string
    """
    return "{0}/{1}".format(slaveMetric["namespace"],
                            slaveMetric["metric"])


  @classmethod
  def getMetricDescription(cls, slaveMetric, autostack):
    """ Get the metric name given a slave metric

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :param autostack: Autostack that metric belongs to
    :type autostack: Autostack

    :returns: metric name
    :rtype: string
    """
    return "{0} on YOMP Autostack {1} in {2} region".format(
      slaveMetric["metric"], autostack.name, autostack.region
    )



@AutostackMetricAdapterBase.registerMetricAdapter
class DerivedAutostackMetricAdapter(AutostackMetricAdapterBase):
  """ Autostack Metric Adapter for derived autostack metrics """

  _DATASOURCE = "autostack"

  _QUERY_PARAMS = {
    "Autostacks/InstanceCount": {
      "statistics": "Sum",
      "unit": "Count",
      "min": 0,
      "max": 500,
      "period": 300,
    }
  }

  @classmethod
  def getMetricName(cls, slaveMetric):
    """ Get the metric name given a slave metric

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :returns: metric name
    :rtype: string
    """
    return "{0}/{1}".format(slaveMetric["namespace"],
                            slaveMetric["metric"])


  @classmethod
  def getMetricDescription(cls, slaveMetric, autostack):
    """ Get the metric name given a slave metric

    :param slaveMetric: See _AutostackDatasourceAdapter.monitorMetric
    :type slaveMetric: dict

    :param autostack: Autostack that metric belongs to
    :type autostack: Autostack

    :returns: metric name
    :rtype: string
    """
    return "{0} on YOMP Autostack {1} in {2} region".format(
      slaveMetric["metric"], autostack.name, autostack.region
    )
