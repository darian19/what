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
import base64
import web

from ConfigParser import ConfigParser

import taurus.engine
from taurus.engine.webservices.responses import UnauthorizedResponse
from taurus.engine import __version__



class AuthenticatedBaseHandler(object):
  """ Base class for any handler that should require api-key authentication """


  @staticmethod
  def compareAuthorization(userAPIKey):
    """ Returns bool, or None if not applicable.  Therefore, not suitable for
    blind bool evaluation... """
    if taurus.engine.config.has_section("security"):
      try:
        validAPIKey = taurus.engine.config.get("security", "apikey")
      except ConfigParser.NoOptionError:
        raise Exception("Internal error, could not get config apikey...")

      return userAPIKey == validAPIKey

    return None


  @staticmethod
  def extractAuthHeader():
    if hasattr(web.ctx, "env"):
      (_, _, auth) = web.ctx.env.get("HTTP_AUTHORIZATION", "").partition("Basic ")

      (userAPIKey, _, _) = base64.decodestring(auth).partition(":")
      return userAPIKey

    return ""


  @staticmethod
  def raiseAuthFailure(message = "Invalid API Key"):
    raise UnauthorizedResponse({"result": message})


  def __new__(cls, *args, **kwargs):
    apikey = cls.extractAuthHeader()
    authResult = cls.compareAuthorization(apikey)

    if authResult is False:
      cls.raiseAuthFailure()

    return super(AuthenticatedBaseHandler, cls).__new__(cls, *args, **kwargs)


  @staticmethod
  def addServerHeader():
    """
    Adds standard 'HTTP Server' header identifying this server and the current
    version.

      Sample Server Header::

        Server: Taurus x.y.z
    """
    web.header("Server", "Taurus %s" % __version__, True)


  @staticmethod
  def addStandardHeaders(content_type="application/json; charset=UTF-8"):
    """
    Add Standard HTTP Headers ("Content-Type", "Server") to the response.

    Here is an example of the headers added by this method using the default
    values::

      Content-Type: application/json; charset=UTF-8
      Server: Taurus x.y.z

    :param content_type: The value for the "Content-Type" header.
                         (default "application/json; charset=UTF-8")
    """
    AuthenticatedBaseHandler.addServerHeader()
    web.header("Content-Type", content_type, True)

