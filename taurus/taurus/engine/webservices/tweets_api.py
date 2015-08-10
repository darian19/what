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
import calendar
import msgpack
import web
import urlparse
from sqlalchemy import asc, desc, select

from htmengine import utils

from taurus.engine import taurus_logging
from taurus.engine.webservices import ManagedConnectionWebapp
from taurus.engine.webservices.handlers import AuthenticatedBaseHandler
from taurus.engine.webservices.responses import InvalidRequestResponse

from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors.collectorsdb.schema import (
  twitterTweets as tweets,
  twitterTweetSamples as samples
)

log = taurus_logging.getExtendedLogger("webservices")

urls = ("/(.+)", "TweetsHandler")



def _raiseNotImplementedError():
  raise NotImplementedError("Managed connection factory not implemented")


g_connFactory = _raiseNotImplementedError


def _connect():
  """ Explicitly checks out a connection from the sqlalchemy engine for use
  inside web handler via web.ctx
  """
  global g_connFactory
  g_connFactory = collectorsdb.engineFactory().connect


def _disconnect():
  """ Explicitly close connection, releasing it back to the pool
  """
  global g_connFactory
  g_connFactory = _raiseNotImplementedError



class TweetsHandler(AuthenticatedBaseHandler):
  def GET(self, metricName):
    """
    Get Tweet Data

    ::

        GET /_tweets/{metric}?from={fromTimestamp}&to={toTimestamp}

    Parameters:

      :param from: (required) return records from this timestamp
      :type from: timestamp
      :param to: (required) return records up to this timestamp
      :type to: timestamp
      :param sortOrder: Sort order ("asc" or "desc")
      :type sortOrder: str
      :param sortBy: "sort by" field ("agg_ts" or "created_at")
      :type sortBy: str

    Returns:

    ::

        {
            "data": [...],
            "names": ["uid", "created_at", "text", "username", "userid"]
        }
    """
    queryParams = dict(urlparse.parse_qsl(web.ctx.env["QUERY_STRING"]))

    fromTimestamp = queryParams.get("from")
    if not fromTimestamp:
      raise InvalidRequestResponse({"result": "Invalid `from` value"})

    toTimestamp = queryParams.get("to")
    if not toTimestamp:
      raise InvalidRequestResponse({"result": "Invalid `to` value"})

    orderByDirection = queryParams.get("sortOrder", "desc").lower()
    if orderByDirection == "asc":
      direction = asc
    elif orderByDirection == "desc":
      direction = desc
    else:
      raise InvalidRequestResponse({"result": "Invalid `sortOrder` value"})

    fields = [tweets.c.uid,
              tweets.c.created_at,
              samples.c.agg_ts,
              tweets.c.text,
              tweets.c.username,
              tweets.c.userid]

    orderByField = queryParams.get("sortBy", "created_at")
    if orderByField not in ("agg_ts", "created_at"):
      raise InvalidRequestResponse({"result": "Invalid `sortBy` value"})

    names = ("names",) + tuple([col.name for col in fields])

    with g_connFactory() as conn:
      sel = (select(fields)
             .select_from(samples.join(tweets,
                                       samples.c.msg_uid == tweets.c.uid))
             .where(samples.c.metric == metricName)
             .where(fromTimestamp <= samples.c.agg_ts)
             .where(samples.c.agg_ts <= toTimestamp))

      result = conn.execute(sel.order_by(direction(orderByField)))

    if "application/octet-stream" in web.ctx.env.get("HTTP_ACCEPT", ""):
      packer = msgpack.Packer()
      self.addStandardHeaders(content_type="application/octet-stream")
      web.header("X-Accel-Buffering", "no")

      yield packer.pack(names)
      for row in result:
        resultTuple = (
            row.uid,
            calendar.timegm(row.created_at.timetuple()),
            calendar.timegm(row.agg_ts.timetuple()),
            row.text,
            row.username,
            row.userid
          )
        yield packer.pack(resultTuple)
    else:
      results = {"names": ["uid", "created_at", "agg_ts", "text", "username",
                           "userid"],
                 "data": [(row.uid,
                           row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                           row.agg_ts.strftime("%Y-%m-%d %H:%M:%S"),
                           row.text,
                           row.username,
                           row.userid) for row in result]}
      self.addStandardHeaders()
      yield utils.jsonEncode(results)



app = ManagedConnectionWebapp(urls, globals())
app.add_processor(web.loadhook(_connect))
app.add_processor(web.unloadhook(_disconnect))

