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


urls = (
  '', "UpdateHandler"
)

FLAG_DIR = '/tmp/'
FLAG_FILE_AVAILABLE = FLAG_DIR + 'YOMP-update-available'
FLAG_FILE_START =     FLAG_DIR + 'YOMP-update-start'


class UpdateHandler(AuthenticatedBaseHandler):

  def isFlagFileAvailable(self):
    return os.path.isfile(FLAG_FILE_AVAILABLE)

  # is there an update available?
  def GET(self):
    web.header('Content-Type', 'application/json; charset=UTF-8', True)
    res = self.isFlagFileAvailable()
    return utils.jsonEncode({ 'result': res })

  # trigger the update to start
  def POST(self):
    web.header('Content-Type', 'application/json; charset=UTF-8', True)
    res = self.isFlagFileAvailable()
    if res:
      try:
        open(FLAG_FILE_START, 'w').close()
      except IOError:
        raise web.badrequest('Failed to create update trigger file: ' +
                              FLAG_FILE_START)
      return web.HTTPError(status="204", data="No Content")
    raise web.badrequest('Tried to trigger update when no update available')


#===============================================================================
app = web.application(urls, globals())
