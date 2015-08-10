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

import abc
import os

from nta.utils.config import Config

from htmengine import repository



class DatasourceAdapterIface(object):
  """ Baseline interface definition for datasource adapters; also acts as
  factory for derived adapters.

  NOTE: Derived Datasource Adapter classes must register themselves via our
    class decorator DatasourceAdapterIface.registerDatasourceAdapter

  """

  __metaclass__ = abc.ABCMeta


  # Registry of datasource adapters populated by our registerDatasourceAdapter
  # decorator
  # key: datasource name (e.g., "cloudwatch")
  # value: datasource adapter class
  _adapterRegistry = dict()


  @classmethod
  def createDatasourceAdapter(cls, datasource):
    """ Factory for Datasource adapters

    :param datasource: datasource (e.g., "cloudwatch")

    :returns: DatasourceAdapterIface-based adapter object corresponding to the
      given datasource value
    """
    config = Config("application.conf",
                    os.environ.get("APPLICATION_CONFIG_PATH"))
    return cls._adapterRegistry[datasource](
      repository.engineFactory(config).connect)


  @classmethod
  def listDatasourceNames(cls):
    """ Returns a sequence of supported datasource names

    :returns: sequence of supported datasource names;
      e.g., ("cloudwatch", "autostack", "custom",)
    """
    return tuple(cls._adapterRegistry.iterkeys())


  @abc.abstractmethod
  def monitorMetric(self, modelSpec):
    """ Start monitoring a metric

    :param modelSpec: Datasource-specific model specification
    :type modelSpec: JSONifiable dict

    :returns: datasource-specific unique model identifier

    :raises htmengine.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist

    :raises htmengine.exceptions.MetricNotSupportedError: if requested metric
      isn't supported

    :raises htmengine.exceptions.MetricAlreadyMonitored: if the metric is already
      being monitored
    """


  @abc.abstractmethod
  def activateModel(self, metricId):
    """ Start a model that is PENDING_DATA, creating the OPF/CLA model.

    NOTE: used by MetricStreamer when model is in PENDING_DATA state and
      sufficient data samples are available to get statistics and complete model
      creation.

    :param metricId: unique identifier of the metric row

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist

    :raises htmengine.exceptions.MetricStatisticsNotReadyError:
    """


  @abc.abstractmethod
  def unmonitorMetric(self, metricId):
    """ Unmonitor a metric

    :param metricId: unique identifier of the metric row

    :raises htmengine.exceptions.ObjectNotFoundError: if metric with the
      referenced metric uid doesn't exist
    """


  @abc.abstractmethod
  def exportModel(self, metricId):
    """ Export the given model.

    :param metricId: datasource-specific unique metric identifier

    :returns: Datasource-specific model-export specification
    :rtype: dict

    :raises htmengine.exceptions.ObjectNotFoundError: if referenced metric
      doesn't exist
    """


  @abc.abstractmethod
  def importModel(self, spec):
    """ Import a model

    :param spec: datasource-specific value created by `exportModel`
    :type spec: dict

    :returns: datasource-specific unique metric identifier

    :raises htmengine.exceptions.MetricNotSupportedError: if requested metric
      isn't supported
    """


  @abc.abstractmethod
  def getMatchingResources(self, aggSpec):
    """ Get the resources that match an aggregation specification.

    :param aggSpec: Autostack aggregation specification
    :type aggSpec: dict (see _AutostackDatasourceAdapter.createAutostack)

    :returns: sequence of matching resources
    """


  @abc.abstractmethod
  def getInstanceNameForModelSpec(self, spec):
    """ Get canonical instance name from a model spec

    :param modelSpec: Datasource-specific model specification
    :type modelSpec: JSONifiable dict

    :returns: Canonical instance name
    :rtype: str or None
    """


  @classmethod
  def registerDatasourceAdapter(cls, clientCls):
    """ Decorator for registering derived Datasource Adapter classes with the
    factory.

    NOTE: The derived Datasource Adapter classes must have a class-level
      variable named _DATASOURCE that is initialized with the adapter's unique
      datasource name (e.g., "cloudwatch", "autostack", "custom")
    """
    key = clientCls._DATASOURCE  #pylint: disable=W0212
    assert key not in cls._adapterRegistry, (
      clientCls, key, cls._adapterRegistry[key])

    cls._adapterRegistry[key] = clientCls

    return clientCls
