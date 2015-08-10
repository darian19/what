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

import json
from pkg_resources import resource_filename
import requests

from boto.exception import BotoServerError
import web
import YOMP.app

from YOMP.app import config
from htmengine import utils
from YOMP.app.aws import instance_utils
from YOMP.app.aws import ses_utils
from YOMP import YOMP_logging

log = YOMP_logging.getExtendedLogger("webservices")


urls = (
  '', "WufooHandler"
)



class WufooHandler(object):
  # save to wufoo form
  def POST(self):

    url = config.get("usertrack", "wufoo_url")
    user = config.get("usertrack", "wufoo_user")

    fields = {
      'name':               'Field6',
      'company':            'Field3',
      'email':              'Field4',
      'edition':            'Field8',
      'version':            'Field10',
      'build':              'Field12',
      'accountId':          'Field14',
      'uniqueServerId':     'Field16',
      'instanceId':         'Field18',
      'region':             'Field19',
      'instanceType':       'Field21'
    }
    payload = {}

    instanceData = instance_utils.getInstanceData() or {}
    for datum in instanceData:
      if datum in fields:
        payload[fields[datum]] = instanceData[datum]

    data = json.loads(web.data())

    if 'email' in data and len(data['email']):
      sendWelcomeEmail(data['email'])

    for datum in data:
      payload[fields[datum]] = data[datum]

    payload[fields["uniqueServerId"]] = config.get("usertrack",
                                                   "YOMP_id")


    if config.getboolean("usertrack", "send_to_wufoo"):
      requests.post(url=url, data=payload, auth=(user, ''))

    for (fieldName, field) in fields.iteritems():
      log.info("{TAG:WUFOO.CUST.REG} %s=%s" % (fieldName, payload.get(field)))

    return web.HTTPError(status="204", data="No Content")



def sendWelcomeEmail(toAddress):
  subject = config.get("registration", "subject")
  body = open(resource_filename(YOMP.__name__, os.path.join("../conf",
    config.get("registration", "body")))).read()
  body = body.replace("\n", "\r\n") # Ensure windows newlines

  serverUrl = web.ctx.env['HTTP_HOST']
  templated = dict(apiKey=config.get("security", "apikey"),
                   serverUrl=serverUrl)

  try:
    ses_utils.sendEmail(subject=subject.format(**templated),
                        body=body.format(**templated),
                        toAddresses=[toAddress])
  except BotoServerError:
    raise web.badrequest("Invalid email address.")



app = web.application(urls, globals())
