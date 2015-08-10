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
import json
import os.path

from YOMP.app import YOMP_HOME
from htmengine.utils import jsonDecode
from YOMP.app.repository import schema



def encodeJson(obj):
  """Serializes a Python dictionary into a JSON string."""
  return json.dumps(obj, ensure_ascii=False, indent=2)



def loadSchema(schemaFile):
  """
  Load JSON Schema
  Will throw IOError if given an invalid path

  :param schemaFile: "examplefilename.json", function will look in
      YOMP_HOME/static/schemas/ for the file.
  :returns: Loaded json schema object from static/schemas
  """
  schemaPath = os.path.join(YOMP_HOME, "static/schemas/", schemaFile)
  with open(schemaPath) as schema:
    return json.load(schema)


def getMetricDisplayFields(conn):
  return set([schema.metric.c.uid,
              schema.metric.c.datasource,
              schema.metric.c.name,
              schema.metric.c.description,
              schema.metric.c.server,
              schema.metric.c.location,
              schema.metric.c.parameters,
              schema.metric.c.status,
              schema.metric.c.message,
              schema.metric.c.last_timestamp,
              schema.metric.c.poll_interval,
              schema.metric.c.tag_name,
              schema.metric.c.last_rowid])



def convertMetricRowToMetricDict(metricRow):
  metric = {"uid":metricRow.uid,
            "datasource":metricRow.datasource,
            "name":metricRow.name,
            "description":metricRow.description,
            "server":metricRow.server,
            "location":metricRow.location,
            "parameters":jsonDecode(metricRow.parameters) if metricRow.parameters != None else None,
            "status":metricRow.status,
            "message":metricRow.message,
            "last_timestamp":metricRow.last_timestamp,
            "poll_interval":metricRow.poll_interval,
            "tag_name":metricRow.tag_name,
            "last_rowid":metricRow.last_rowid,
            "display_name":("%s (%s)" % (metricRow.tag_name, metricRow.server)
                            if metricRow.tag_name
                            else metricRow.server)}
  return metric
