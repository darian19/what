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
"""
Sorted metrics webservice handlers.

============================ ===========================
Endpoint                     Handler
---------------------------- ---------------------------
/_anomalies                  :py:meth:`DefaultHandler`
/_anomalies/period/{period}  :py:meth:`AnomaliesHandler`
============================ ===========================

"""
import web

from htmengine import utils
from YOMP.app import repository
from YOMP.app.webservices import AuthenticatedBaseHandler
from YOMP.app.webservices.utils import (convertMetricRowToMetricDict,
                                        getMetricDisplayFields)
from YOMP import YOMP_logging

from collections import defaultdict


log = YOMP_logging.getExtendedLogger("webservices")


urls = (
  r"/period/(\d+)/*", "AnomaliesPeriodHandler",
  r"/name",           "AnomaliesNameHandler",
  "/*",               "DefaultHandler",
)


class DefaultHandler(AuthenticatedBaseHandler):
  def GET(self):
    """
    Get number of available periods

    Example request::

      GET /_anomalies

    Example response::

      [
        2,
        24,
        192
      ]
    """
    return utils.jsonEncode([2, 24, 192])


class AnomaliesPeriodHandler(AuthenticatedBaseHandler):
  def GET(self, period):
    """
    Get metrics, sorted by anomalies over specified period (hours)

    :param period: Period (hours) over which to consider anomalies for sort
      order
    :type period: int
    :returns: List of metrics
    :rtype: list

    Example request::

      GET /_anomalies/period/{period}

    Example response::

      [
        {
          "status": 1,
          "last_rowid": 4033,
          "display_name": "jenkins-master (us-west-2/AWS/EC2/i-12345678)",
          "description": "NetworkIn on EC2 instance i-12345678 in us-west-2",
          "name": "AWS/EC2/NetworkIn",
          "last_timestamp": "2014-04-14 20:29:00",
          "poll_interval": 300,
          "server": "us-west-2/AWS/EC2/i-12345678",
          "tag_name": "jenkins-master",
          "datasource": "cloudwatch",
          "location": "us-west-2",
          "message": null,
          "parameters": {
            "InstanceId": "i-12345678",
            "region": "us-west-2"
          },
          "uid": "0b6b97022fdb4134936aae92aa67393b"
        },
        ...
      ]

    """

    try:
      self.addStandardHeaders()

      engine = repository.engineFactory()

      with engine.connect() as conn:
        modelIterator = repository.getAllMetrics(conn, fields=getMetricDisplayFields(conn))
        displayValuesMap = repository.getMetricIdsSortedByDisplayValue(conn, period)

      # Keep track of the largest model display value for each server
      serverValues = defaultdict(float)

      modelsList = []

      for model in modelIterator:
        val = displayValuesMap.get(model.uid)
        if val is not None:
          serverValues[model.server] = max(float(val),
                                           serverValues[model.server])
        modelsList.append(convertMetricRowToMetricDict(model))

      # Sort by the primary key. The order within each server is preserved
      # from previous sort.
      def getModelRankByServer(model):
        return (-serverValues[model["server"]], model["server"], model["name"])
      modelsList = sorted(modelsList, key=getModelRankByServer)

      return utils.jsonEncode(modelsList)

    except (web.HTTPError) as ex:
      log.info(str(ex) or repr(ex))
      raise ex

    except Exception as ex:
      log.exception("GET Failed")
      raise web.internalerror(str(ex) or repr(ex))


class AnomaliesNameHandler(AuthenticatedBaseHandler):
  def GET(self):
    """
    Get metrics, sorted by AWS name tag / instance ID

    :returns: List of metrics
    :rtype: list

    Example request::

      GET /_anomalies/name

    Example response::

      [
        {
          "status": 1,
          "last_rowid": 4033,
          "display_name": "jenkins-master (us-west-2/AWS/EC2/i-12345678)",
          "description": "NetworkIn on EC2 instance i-12345678 in us-west-2",
          "name": "AWS/EC2/NetworkIn",
          "last_timestamp": "2014-04-14 20:29:00",
          "poll_interval": 300,
          "server": "us-west-2/AWS/EC2/i-12345678",
          "tag_name": "jenkins-master",
          "datasource": "cloudwatch",
          "location": "us-west-2",
          "message": null,
          "parameters": {
            "InstanceId": "i-12345678",
            "region": "us-west-2"
          },
          "uid": "0b6b97022fdb4134936aae92aa67393b"
        },
        ...
      ]

    """

    try:
      self.addStandardHeaders()

      engine = repository.engineFactory()

      with engine.connect() as conn:
        modelIterator = repository.getAllMetrics(conn, fields=getMetricDisplayFields(conn))
        modelsList = [convertMetricRowToMetricDict(model) for model in modelIterator]

      # Sort by tag_name, and then parameters=>InstanceID
      def cmpFn(model1, model2):
        name1 = model1["tag_name"]
        name2 = model2["tag_name"]
        id1 = model1["parameters"].get("InstanceID")
        id2 = model2["parameters"].get("InstanceID")

        if name1 and not name2:
          return -1
        elif name2 and not name1:
          return 1
        elif name1 != name2:
          return cmp(name1, name2)
        elif id1 and not id2:
          return -1
        elif id2 and not id1:
          return 1
        elif id1 != id2:
          return cmp(id1, id2)
        return 0

      modelsList.sort(cmpFn)

      return utils.jsonEncode(modelsList)

    except (web.HTTPError) as ex:
      log.info(str(ex) or repr(ex))
      raise ex

    except Exception as ex:
      log.exception("GET Failed")
      raise web.internalerror(str(ex) or repr(ex))


app = web.application(urls, globals())
