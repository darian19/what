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

from htmengine.adapters.datasource.datasource_adapter_iface import (
    DatasourceAdapterIface)

import YOMP.app.adapters.datasource.autostack
import YOMP.app.adapters.datasource.cloudwatch
import htmengine.adapters.datasource.custom



from htmengine.adapters.datasource import (createCustomDatasourceAdapter,
                                           createDatasourceAdapter,
                                           listDatasourceNames)



def createAutostackDatasourceAdapter():
  """ Convenience function for creating a datasource adapter for YOMP Autostack
  Metrics

  :returns: datasource adapter for YOMP Autostack Metrics
  :rtype: YOMP.app.adapters.datasource.cloudwatch._AutostackDatasourceAdapter
  """
  return createDatasourceAdapter("autostack")



def createCloudwatchDatasourceAdapter():
  """ Convenience function for creating a datasource adapter for Cloudwatch
  Metrics

  :returns: datasource adapter for Cloudwatch Metrics
  :rtype: YOMP.app.adapters.datasource.cloudwatch._CloudwatchDatasourceAdapter
  """
  return createDatasourceAdapter("cloudwatch")



