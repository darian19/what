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

import os.path

import web

import YOMP.app

from htmengine import utils
from YOMP.app.webservices import AuthenticatedBaseHandler
from YOMP import YOMP_logging

log = YOMP_logging.getExtendedLogger("webservices")

urls = (
  '', "SupportHandler"
)

FLAG_DIR = '/tmp/'
FLAG_FILE = FLAG_DIR + 'enable_support_access'


class SupportHandler(AuthenticatedBaseHandler):

  # is support access allowed? does flag file exist?
  def GET(self):
    res = os.path.isfile(FLAG_FILE)
    web.header('Content-Type', 'application/json; charset=UTF-8', True)
    return utils.jsonEncode({'result': res})

  # revoke support access by remvoing flag file
  def DELETE(self):
    try:
      if os.path.isfile(FLAG_FILE):
        os.remove(FLAG_FILE)
    except:
      # raise the exception to the user and log
      log.exception("DELETE FAILED")
      raise web.badrequest('Failed to remove support access flag file: ' +
                            FLAG_FILE)

    return web.HTTPError(status="204", data="No Content")

  # allow support access by creating flag file
  def POST(self):
    try:
      open(FLAG_FILE, 'w').close()
    except IOError:
      raise web.badrequest('Failed to create support access flag file: ' +
                            FLAG_FILE)
    return web.HTTPError(status="204", data="No Content")


#===============================================================================
app = web.application(urls, globals())
