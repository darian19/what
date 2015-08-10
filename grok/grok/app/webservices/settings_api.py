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
import YOMP.app

from htmengine import utils
from YOMP.app import YOMPAppConfig
from YOMP.app.webservices import AuthenticatedBaseHandler



urls = (
  '', "SettingsHandler",
  '/([-\w]*)', "SettingsHandler",
)

CONFIGURABLE_SETTINGS = ("aws", "notifications")
HIDDEN_SETTINGS = {
  "aws": set(["aws_secret_access_key"]),
  "notifications": set(["subject", "body"])} # May want to consider unhiding
                                             # these options to allow user to
                                             # define subject/body templates


class SettingsHandler(object):
  def validSections(self):
    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()
    if YOMP.app.config.has_option("admin", "configurable_sections"):
      return YOMP.app.config.get("admin", "configurable_sections").split(",")
    else:
      return []

  def getAllSettings(self):
    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()

    apikey = AuthenticatedBaseHandler.extractAuthHeader()
    authResult = AuthenticatedBaseHandler.compareAuthorization(apikey)

    if authResult is False:
      AuthenticatedBaseHandler.raiseAuthFailure()

    res = {}
    for section in self.validSections():
      res[section] = {}
      for key, value in YOMP.app.config.items(section):
        if key not in HIDDEN_SETTINGS.get(section, set()):
          res[section][key] = value
    return res

  def getSectionSettings(self, section):
    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()
    res = {}

    if section != "usertrack":
      # Everything but usertrack requires authentication...
      apikey = AuthenticatedBaseHandler.extractAuthHeader()
      authResult = AuthenticatedBaseHandler.compareAuthorization(apikey)

      if authResult is False:
        AuthenticatedBaseHandler.raiseAuthFailure()

    if section in self.validSections():
      for key, value in YOMP.app.config.items(section):
        if key not in HIDDEN_SETTINGS.get(section, set()):
          res[key] = value
    return res

  def updateSettings(self, section=None):
    if section != "usertrack":
      # Everything but usertrack requires authentication...
      apikey = AuthenticatedBaseHandler.extractAuthHeader()
      authResult = AuthenticatedBaseHandler.compareAuthorization(apikey)

      if authResult is False:
        AuthenticatedBaseHandler.raiseAuthFailure()

    dirty = False
    data = web.data()
    if data:
      sections = {}
      if section:
        sections = {section: utils.jsonDecode(data)}
      else:
        sections = utils.jsonDecode(data)

      config = YOMPAppConfig(mode=YOMPAppConfig.MODE_OVERRIDE_ONLY)

      for s in sections:
        if s in self.validSections():
          for key in sections[s]:
            if not config.has_section(s):
              config.add_section(s)
            config.set(s, key, sections[s][key])
            dirty = True
        else:
          return False
      if dirty:
        config.save()

      return dirty

  def GET(self, section=None):
    """
    List All Settings

    ::

        GET /_settings

    Returns:

    ::

        {
          "section": {
              "option": "value", ...
          }, ...
        }

    OR

    List Some Settings

    ::

        GET /_settings/section

    ::

        {
          "option": "value", ...
        }
    """
    res = {}
    if section is None:
      res = self.getAllSettings()
    else:
      res = self.getSectionSettings(section)

    AuthenticatedBaseHandler.addStandardHeaders()
    return utils.jsonEncode(res)

  def POST(self, section=None):
    if self.updateSettings(section):
      return web.HTTPError(status="204", data="No Content")

    raise web.badrequest("Failed to update configuration settings")



#===============================================================================
app = web.application(urls, globals())
