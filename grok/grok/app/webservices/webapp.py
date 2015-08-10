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
import hashlib
import os
import random
import socket
import string  # pylint: disable=W0402
import web

from datetime import datetime
from subprocess import check_output, CalledProcessError
from urlparse import urlparse

from YOMP import __version__, logging_support

from YOMP.YOMP_logging import getExtendedLogger

import YOMP.app

from YOMP.app.aws import instance_utils
from YOMP.app.aws.ec2_utils import checkEC2Authorization
from YOMP.app.exceptions import AuthFailure, AWSPermissionsError
from YOMP.app.webservices import (annotations_api,
                                  anomalies_api,
                                  autostacks_api,
                                  instances_api,
                                  getWebLogPrefix,
                                  logging_api,
                                  messagemanager,
                                  metrics_api,
                                  models_api,
                                  notifications_api,
                                  settings_api,
                                  support_api,
                                  update_api,
                                  wufoo_api,
                                  UnauthorizedResponse)
from YOMP.app.webservices.utils import encodeJson
from htmengine.utils import jsonDecode



logging_support.LoggingSupport.initService()

log = getExtendedLogger("webapp-logger")



urls = (
  # Web UI
  "", "DefaultHandler",
  "/", "DefaultHandler",
  "/YOMP", "YOMPHandler",
  r"/YOMP/([-\/\w]*)", "YOMPHandler",

  # i18n strings
  "/_msgs", "MessagesHandler",

  # REST API Endpoints
  "/_annotations", annotations_api.app,
  "/_anomalies", anomalies_api.app,
  "/_auth", "AWSAuthHandler",
  "/_autostacks", autostacks_api.app,
  "/_instances", instances_api.app,
  "/_logging", logging_api.app,
  "/_metrics", metrics_api.app,
  "/_models", models_api.app,
  "/_notifications", notifications_api.app,
  "/_settings", settings_api.app,
  "/_support", support_api.app,
  "/_update", update_api.app,
  "/_wufoo", wufoo_api.app,
)

messageManager = messagemanager.MessageManager(
  open(os.path.join(YOMP.app.YOMP_HOME,
                    "resources/messages/us/messages.json")).read()
)

# Get the build sha to display in web ui for easy debugging
try:
  buildSha = open(os.path.join(YOMP.app.YOMP_HOME, "static/YOMP.sha")).read()
except IOError:
  try:
    buildSha = check_output(["YOMP", "rev-parse", "--verify", "HEAD"])
  except CalledProcessError:
    buildSha = "0"


def _getInstanceMetadata():
  """ Get and cache metadata about the instance this YOMP server is running on

  NOTE: This used to be retrieved directly into a global variable, which added
    significant delays when running unit test on a dev laptop while on a
    different network (e.g., from home) and there was no way to patch. Caching
    also helps when debugging in that environment; without it, many of the
    Web GUI requests take a very long time to complete.

  :returns: metadata (see instance_utils.getInstanceData) or empty dict if none
  """
  try:
    return _getInstanceMetadata.instanceMetadata
  except AttributeError:
    _getInstanceMetadata.instanceMetadata = (
      instance_utils.getInstanceData() or {})
    return _getInstanceMetadata.instanceMetadata


class DefaultHandler(object):
  def GET(self):  # pylint: disable=R0201,C0103
    raise web.seeother("/static/index.html")


class YOMPHandler(object):
  def GET(self, path=None):  # pylint: disable=R0201,W0613,C0103
    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()
    YOMP.app.product.loadConfig()

    # prep data
    apiKey = YOMP.app.config.get("security", "apikey")
    hostname = socket.gethostname()
    isEmbed = path and ("embed/" in path)
    params = web.input(hash="", width=720, height=480)
    paramHash = params.hash
    paramHeight = params.height
    paramWidth = params.width
    refererUri = web.ctx.env.get("HTTP_REFERER", "")
    referer = urlparse(refererUri).hostname or ""
    sha1 = hashlib.sha1()
    render = web.template.render(os.path.join(YOMP.app.YOMP_HOME,
                                              "resources/templates"))

    instanceData = _getInstanceMetadata()

    data = {"baseUrl": YOMP.app.config.get("web", "base_url"),
            "embed": {"height":   paramHeight,
                      "width":    paramWidth},
            "endpoint": YOMP.app.config.get("web", "base_url"),
            "hostname": hostname,
            "product": {"build": buildSha[:7],
                        "edition": YOMP.app.product.get("edition",
                                                        "type").title(),
                        "version": __version__.__version__},
            "site": messageManager.getMessagesByKey("site"),
            "year": datetime.utcnow().year,
            "instanceData": {"region": instanceData.get("region") or ""}}

    web.header("Content-Type", "text/html; charset=UTF-8")

    # if an embed, and not an internal web ui visit, and hash was sent...
    if isEmbed and referer != hostname and len(paramHash):
      # check hash
      sha1.update(apiKey + referer)
      newHash = sha1.hexdigest()

      # embed not authorized
      if paramHash != newHash:
        raise web.badrequest("Hashes did not match.")

      # embed authorized - render simple embed template
      data["apiKey"] = apiKey
      return render.embed(data)

    # not embed - render web ui page
    return render.main(data)



class MessagesHandler(object):
  def POST(self): # pylint: disable=R0201,C0103
    """
    Handles calls from clients for messages. Expects to received batched
    requests, keyed by the name of the template used to identify responses.
    """
    global messageManager # pylint: disable=W0603
    data = web.input()
    messagesOut = {}

    if YOMP.app.DEBUG_LEVEL > 0:
      # When debugging, read the file and create new MessageManager on
      # every request so we can change messages.json on the fly.
      with open(os.path.join(YOMP.app.YOMP_HOME,
                             "resources/messages/us/messages.json")) as f:
        messageManager = messagemanager.MessageManager(f.read())

    # Make sure we have the latest version of configuration
    YOMP.app.config.loadConfig()
    for templateKey in data:
      templateLocation = data[templateKey]

      if templateKey == "explicit":
        # The templateKey is either an id or the string "explicit", which means
        # that the client wants to identify the key directly, not by template,
        # which is easy enough.
        for templateId in templateLocation.split(","):
          messagesOut[templateId] = messageManager.getMessagesByKey(templateId)
      else:
        # To get the right relative lookup path for messages.json, we"ll
        # remove known template paths.
        baseUrl = YOMP.app.config.get("web", "base_url")
        path = templateLocation\
              .replace(baseUrl + "/static/js/program/templates/", "")
        msgs = messageManager.getMessagesForTemplate(path)
        messagesOut[templateKey] = msgs

    web.header("Content-Type", "application/json; charset=UTF-8", True)
    return encodeJson(messagesOut)



class AWSAuthHandler(object):
  """ AWS Authorization verification handler """

  @staticmethod
  def generateAPIKey(
      size=5,
      chars="".join(set(string.letters + string.diYOMPs) - set("1iLl0Oo"))):
    return "".join(random.choice(chars) for _ in xrange(size))


  def POST(self):  # pylint: disable=C0103
    data = jsonDecode(web.data())
    YOMP.app.config.loadConfig()
    # if they already authed, new aws creds must match the originals
    if YOMP.app.config.has_section("aws"):
      if YOMP.app.config.has_option("aws", "aws_access_key_id"):
        awsAccessKeyId = YOMP.app.config.get("aws", "aws_access_key_id")
        if awsAccessKeyId and awsAccessKeyId != data["aws_access_key_id"]:
          raise UnauthorizedResponse({
              "result": ("Please use the same AWS Credentials that you "
                         "initially authenticated with.")
          })

    try:
      checkEC2Authorization(data["aws_access_key_id"],
                            data["aws_secret_access_key"])
    except (AuthFailure, AWSPermissionsError) as e:
      raise UnauthorizedResponse({"result": str(e)})

    result = {"result": "success"}

    apikey = None

    if YOMP.app.config.has_section("security"):
      if YOMP.app.config.has_option("security", "apikey"):
        apikey = YOMP.app.config.get("security", "apikey")

    if not apikey:
      apikey = self.generateAPIKey()
      YOMP.app.config.set("security", "apikey", apikey)
      YOMP.app.config.save()

    result["apikey"] = apikey

    web.header("Content-Type", "application/json; charset=UTF-8", True)
    return encodeJson(result)



web.config.debug = False
app = web.application(urls, globals())


def webLogger(handler):
  log.info(getWebLogPrefix())
  return handler()

app.add_processor(webLogger)


if __name__ == "__main__":
  app.run()


application = app.wsgifunc()
