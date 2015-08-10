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

from .handlers import AuthenticatedBaseHandler
from .responses import UnauthorizedResponse

from YOMP.app import repository


__all__ = [
    "AuthenticatedBaseHandler",
    "UnauthorizedResponse"
  ]



def getWebLogPrefix():
  """
  Returns a prefix for logging containing the URL and user agent for a web
    request

  :returns: Prefix for logging
  """
  webURL = web.ctx.env.get("SCRIPT_NAME", "") + web.ctx.env.get("PATH_INFO",
                                                                "")
  if web.ctx.env.get("QUERY_STRING"):
    webURL = webURL + "?" + web.ctx.env.get("QUERY_STRING")

  return "METHOD=%s, URL=%r, UA=%r" %  (web.ctx.method,
                                        webURL,
                                        web.ctx.env.get("HTTP_USER_AGENT", ""))


class ManagedConnectionWebapp(object):
  """ Helper class for creating webapp that is confirgured (by means of web.py)
  loadhook/unloadhook application processors) to procure a sqlalchemy
  connectionFactory in the load phase, and release it in the unload phase.

  Web apps created in this fashion must use `web.ctx.connFactory()` in a context
  manager statement to ackquire and release connections.

  """
  def __new__(cls, *args, **kwargs):
    app = web.application(*args, **kwargs)

    app.add_processor(web.loadhook(cls._connect))
    app.add_processor(web.unloadhook(cls._disconnect))

    return app


  @staticmethod
  def _connect():
    """ Explicitly checks out a connection from the sqlalchemy engine for use
    inside web handler via web.ctx
    """
    web.ctx.connFactory = repository.engineFactory().connect


  @staticmethod
  def _disconnect():
    """ Explicitly close connection, releasing it back to the pool
    """
    web.ctx.connFactory = None
