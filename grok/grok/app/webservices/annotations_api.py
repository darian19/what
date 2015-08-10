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
# pylint: disable=C0103,R0201
# C0103: Invalid method name "GET", "POST", "DELETE" (invalid-name)
# R0201: Method "GET", "POST", "DELETE" could be a function (no-self-use)
"""
Annotation webservice handlers.

==================== =================================
Endpoint             Handler
-------------------- ---------------------------------
/_annotations/{uid}  :py:class:`AnnotationHandler`
/_annotations        :py:class:`AnnotationHandler`
==================== =================================

"""
import datetime
from sqlalchemy.exc import IntegrityError
import web
import urlparse
import YOMP.app.exceptions as app_exceptions

from YOMP.app import repository
from htmengine import utils
from YOMP.app.webservices import (AuthenticatedBaseHandler,
                                  ManagedConnectionWebapp)
from YOMP import YOMP_logging

log = YOMP_logging.getExtendedLogger("webservices")

urls = (
    r"/([-\w]*)", "AnnotationHandler",
    "/", "AnnotationHandler",
    "", "AnnotationHandler",
)



class AnnotationHandler(AuthenticatedBaseHandler):
  def GET(self, uid=None):
    # pylint: disable=C0301
    # C0301: Line too long (docstring GET URL)
    """
    Get annotations

    Requests::

      GET /_annotations/{uid}

    :param uid: Annotation ID

    OR

    ::

      GET /_annotations?device={device}&user={user}&server={server}&from={from}&to={to}

    :param device: Device ID if the annotation was created by the mobile app
                   or Service UID if the annotation was created by a service
    :param user: User name who created the annotation if the annotation was
                 created by the mobile app or service name if the annotation was
                 created by a service
    :param server: Instance ID associated with the annotation

    :param from: annotations with "timestamp" greater or equals to "from"
    :param to:  annotations with "timestamp" lower or equal to "to"

    Response::

      [
        {
           "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
           "device", "1231AC32FE",
           "created":"2013-08-27 16:46:51",
           "timestamp":"2013-08-27 16:45:00",
           "user":"Demo User",
           "server":" AWS/EC2/i-12345678",
           "message":" The CPU Utilization was high ...",
           "data": { Optional JSON Object }
         },
        ...
      ]
    """
    # pylint: enable=C0301
    self.addStandardHeaders()
    if uid:
      try:
        with web.ctx.connFactory() as conn:
          row = repository.getAnnotationById(conn, uid)
        return utils.jsonEncode([dict(row)])
      except app_exceptions.ObjectNotFoundError:
        raise web.notfound("ObjectNotFoundError Annotation not found: ID: %s"
                           % uid)
    else:
      try:
        queryParams = dict(urlparse.parse_qsl(web.ctx.env['QUERY_STRING']))
        device = queryParams.get("device")
        user = queryParams.get("user")
        server = queryParams.get("server")
        fromDate = queryParams.get("from")
        toDate = queryParams.get("to")

        with web.ctx.connFactory() as conn:
          results = repository.getAnnotations(conn, device, user, server,
                                              fromDate, toDate)
        annotations = [dict(row) for row in results]

        return utils.jsonEncode(annotations)
      except web.HTTPError as ex:
        log.info(str(ex) or repr(ex))
        raise ex

      except Exception as ex:
        raise web.internalerror(str(ex) or repr(ex))


  def DELETE(self, uid):
    """
    Delete Annotation

    Request::

      DELETE /_annotations/{uid}

    :param uid: Annotation ID

    Response::

      HTTP 204 No Content

    """
    try:
      if uid:
        with web.ctx.connFactory() as conn:
          repository.deleteAnnotationById(conn, uid)
        self.addServerHeader()
        raise web.HTTPError(status="204 No Content")
    except app_exceptions.ObjectNotFoundError:
      self.addStandardHeaders()
      raise web.notfound("ObjectNotFoundError Annotation not found: ID: %s"
                         % uid)


  def POST(self):
    """
    Create new Annotation

    Request::

      POST /_annotations

      {
         "device", "1231AC32FE",
         "timestamp":"2013-08-27 16:45:00",
         "user":"Demo User",
         "server":" AWS/EC2/i-12345678",
         "message": "The CPU Utilization was high ...",
         "data": { JSON Object }
      }

    :param device: Device ID if the annotation was created by the mobile app
                   or Service UID if the annotation was created by a service
    :param timestamp: The date and time to be annotated
    :param user: User name who created the annotation if the annotation was
                 created by the mobile app or service name if the annotation was
                 created by a service
    :param server: Instance ID associated with the annotation
    :param message: Annotation message (Optional if data is provided)
    :param data: Service specific data associated with this annotation
                 (Optional if message is provided)

    Response::

      HTTP Status 201 Created

      {
         "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
         "device", "1231AC32FE",
         "created":"2013-08-27 16:46:51",
         "timestamp":"2013-08-27 16:45:00",
         "user":"Demo User",
         "server":" AWS/EC2/i-12345678",
         "message": "The CPU Utilization was high ...",
         "data": {JSON Object }
      }
    """
    self.addStandardHeaders()
    webdata = web.data()
    if webdata:
      try:
        if isinstance(webdata, basestring):
          webdata = utils.jsonDecode(webdata)
      except ValueError as e:
        raise web.badrequest("Invalid JSON in request: " + repr(e))

      if "device" in webdata:
        device = webdata["device"]
      else:
        raise web.badrequest("Missing 'device' in request")

      if "timestamp" in webdata:
        timestamp = webdata["timestamp"]
      else:
        raise web.badrequest("Missing 'timestamp' in request")

      if "user" in webdata:
        user = webdata["user"]
      else:
        raise web.badrequest("Missing 'user' in request")

      if "server" in webdata:
        server = webdata["server"]
      else:
        raise web.badrequest("Missing 'server' in request")

      if "message" in webdata:
        message = webdata["message"]
      else:
        message = None

      if "data" in webdata:
        data = webdata["data"]
      else:
        data = None

      if data is None and message is None:
        raise web.badrequest(
            "Annotation must contain either 'message' or 'data'")

      # lower timestamp resolution to seconds because the database rounds up
      # microsecond to the nearest second
      created = datetime.datetime.utcnow().replace(microsecond=0)
      uid = utils.createGuid()

      try:
        with web.ctx.connFactory() as conn:
          repository.addAnnotation(conn=conn, timestamp=timestamp,
                                   device=device, user=user, server=server,
                                   message=message, data=data, created=created,
                                   uid=uid)

        # Prepare response with generated "uid" and "created" fields filled
        response = utils.jsonEncode({
            "uid": uid,
            "created": created,
            "device": device,
            "timestamp": timestamp,
            "user": user,
            "server": server,
            "message": message,
            "data": data,
        })
        raise web.created(response)
      except app_exceptions.ObjectNotFoundError as ex:
        raise web.badrequest(str(ex) or repr(ex))


app = ManagedConnectionWebapp(urls, globals())
