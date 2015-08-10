import json
import os.path

from taurus.engine import TAURUS_HOME
from htmengine.utils import jsonDecode
from htmengine import repository
from htmengine.repository import schema

def encodeJson(obj):
  """Serializes a Python dictionary into a JSON string."""
  return json.dumps(obj, ensure_ascii=False, indent=2)



def loadSchema(schemaFile):
  """
  Load JSON Schema
  Will throw IOError if given an invalid path

  :param schemaFile: "examplefilename.json", function will look in
      TAURUS_HOME/taurus/webservices/schemas/ for the file.
  :returns: Loaded json schema object from taurus/webservices/schemas
  """


  schemaPath = os.path.join(TAURUS_HOME,
                            "taurus/engine/webservices/schemas/",
                            schemaFile)
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
