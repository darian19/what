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

from taurus.engine import repository, taurus_logging
from taurus.engine.webservices import ManagedConnectionWebapp
from taurus.engine.webservices.handlers import AuthenticatedBaseHandler
from taurus.engine.webservices.models_api import ModelHandler
from taurus.engine.webservices.responses import InvalidRequestResponse



log = taurus_logging.getExtendedLogger("webservices")

urls = (
  "/?", "InstancesHandler",
)



class InstancesHandler(AuthenticatedBaseHandler):


  def DELETE(self):
    """
    Delete models for multiple instances

    ::

        DELETE /_instances

    DELETE data:

    ::

        [
            "{region}/{namespace}/{instanceId}",
            ...
        ]

    Returns:

    ::

        {
            "result": "success"
        }
    """
    try:
      instances = utils.jsonDecode(web.data())
    except:
      raise InvalidRequestResponse({"result": "Invalid request"})

    if not instances:
      raise InvalidRequestResponse({"result": ("Missing instances in DELETE"
                                               " request")})

    deleted = []
    if instances:
      for server in instances:
        with web.ctx.connFactory() as conn:
          modelIds = repository.listMetricIDsForInstance(conn, server)
        if modelIds:
          for modelId in modelIds:
            ModelHandler.deleteModel(modelId)
          deleted.append(server)

    if instances == deleted:
      self.addStandardHeaders()
      return utils.jsonEncode({"result": "success"})

    raise web.notfound("Not able to delete %s" %
                       utils.jsonEncode(list(set(instances)-set(deleted))))


  def GET(self):
    """
    Get all instances

    ::

        GET /_instances

    Sample Output:

    ::

        [
            {
                "location": "us-west-2",
                "message": null,
                "name": "jenkins-master",
                "namespace": "AWS/EC2",
                "server": "i-12345678",
                "status": 2
                "parameters": {
                    "region": "us-west-2",
                    "AutoScalingGroupName": "YOMPsolutions-com-ssl"
                },

            },
            ...
        ]
    """
    with web.ctx.connFactory() as conn:
      instances = repository.getInstances(conn)

    self.addStandardHeaders()
    return utils.jsonEncode(instances)



app = ManagedConnectionWebapp(urls, globals())
