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

import web

from htmengine import repository
from htmengine.adapters.datasource import createDatasourceAdapter

from taurus.engine import exceptions as app_exceptions
from taurus.engine.webservices.handlers import AuthenticatedBaseHandler
from taurus.engine.webservices import ManagedConnectionWebapp
from taurus.engine.webservices.utils import (getMetricDisplayFields,
                                             convertMetricRowToMetricDict)



urls = (
  # /_metrics/custom
  '', "CustomDefaultHandler",
  # /_metrics/custom/
  '/', "CustomDefaultHandler",
  # /_metrics/custom/<metricName>
  '/([\w\.\-]+)', "CustomDefaultHandler",
)



class CustomDefaultHandler(AuthenticatedBaseHandler):


  def GET(self):
    with web.ctx.connFactory() as conn:
      metrics = repository.getCustomMetrics(conn, getMetricDisplayFields(conn))
    convertedMetrics = [convertMetricRowToMetricDict(metric)
                        for metric in metrics]
    self.addStandardHeaders()
    return json.dumps(convertedMetrics)


  def DELETE(self, metricName):
    adapter = createDatasourceAdapter("custom")
    try:
      adapter.deleteMetricByName(metricName)
    except app_exceptions.ObjectNotFoundError:
      raise web.notfound("Metric not found. Metric name=%s" % (metricName,))

    self.addStandardHeaders()
    return json.dumps({'result': 'success'})



app = ManagedConnectionWebapp(urls, globals())
