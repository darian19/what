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
# pylint: disable=C0103,W1401

import web
from htmengine import utils
from YOMP.app.adapters.datasource import listDatasourceNames
from YOMP.app.webservices import (AuthenticatedBaseHandler,
                                  cloudwatch_api,
                                  custom_api)



urls = (
  "/datasources", "MetricsHandler",
  "/cloudwatch", cloudwatch_api.app,
  "/custom", custom_api.app,
  "/?", "MetricsHandler"
)


class MetricsHandler(AuthenticatedBaseHandler):
  """
    List supported datasources

    ::

        GET /_metrics/datasources

    Returns:

    ::

        ["autostack", "cloudwatch", "custom"]
  """
  def GET(self):
    self.addStandardHeaders()
    return utils.jsonEncode(self.getDatasources())

  @staticmethod
  def getDatasources():
    return listDatasourceNames()


app = web.application(urls, globals())
