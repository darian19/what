#!/usr/bin/env python
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
import web

from taurus.engine import logging_support
from taurus.engine.taurus_logging import getExtendedLogger
from taurus.engine.webservices import (instances_api,
                                       metrics_api,
                                       models_api,
                                       tweets_api)



logging_support.LoggingSupport.initService()

log = getExtendedLogger("webapp-logger")



urls = (
  # Web UI
  "", "DefaultHandler",
  "/", "DefaultHandler",
  "/_instances", instances_api.app,
  "/_metrics", metrics_api.app,
  "/_models", models_api.app,
  "/_tweets", tweets_api.app
)



class DefaultHandler(object):
  def GET(self):  # pylint: disable=R0201,C0103
    return "Hi there!  Move along.  Nothing to see here."


web.config.debug = False
app = web.application(urls, globals())


if __name__ == "__main__":
  app.run()


application = app.wsgifunc()
