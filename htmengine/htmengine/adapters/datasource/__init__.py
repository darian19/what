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

import htmengine.adapters.datasource.custom

from htmengine.adapters.datasource.datasource_adapter_iface import (
    DatasourceAdapterIface)



def listDatasourceNames():
  """ Returns a sequence of supported datasource names

  :returns: sequence of supported datasource names;
    e.g., ("cloudwatch", "autostack", "custom",)
  """
  return DatasourceAdapterIface.listDatasourceNames()



def createDatasourceAdapter(datasource):
  """ Factory for Datasource adapters

  :param datasource: datasource (e.g., "cloudwatch")

  :returns: DatasourceAdapterIface-based adapter object corresponding to the
    given datasource value
  """
  return DatasourceAdapterIface.createDatasourceAdapter(datasource)



def createCustomDatasourceAdapter():
  """ Convenience function for creating a datasource adapter for htmengine
  Custom Metrics

  :returns: datasource adapter for htmengine Custom Metrics
  :rtype: htmengine.adapters.datasource.custom._CustomDatasourceAdapter
  """
  return createDatasourceAdapter("custom")

