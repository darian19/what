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
from collections import defaultdict
import itertools
import json
import math
import msgpack
import re
import urlparse
from validictory import validate, ValidationError
import web

from htmengine import utils
from htmengine.adapters.datasource import createDatasourceAdapter
import htmengine.exceptions as app_exceptions

from taurus.engine import config, repository, taurus_logging
from taurus.engine.repository import schema
from taurus.engine.webservices import ManagedConnectionWebapp
from taurus.engine.webservices.handlers import AuthenticatedBaseHandler
from taurus.engine.webservices.responses import (InvalidRequestResponse,
                                                 NotAllowedResponse)
from taurus.engine.webservices.utils import getMetricDisplayFields, loadSchema



_PROCESSING_TIME_PER_RECORD = 0.05  # seconds per record

log = taurus_logging.getExtendedLogger("webservices")

urls = (
      '', 'ModelHandler',
      '/', 'ModelHandler',
      '/data', 'MetricDataHandler',
      '/data/stats', 'MetricDataStatsHandler',
      '/export', 'ModelExportHandler',
      '/([-\w]*)', 'ModelHandler',
      '/([-\w]*)/data', 'MetricDataHandler',
      '/([-\w]*)/export', 'ModelExportHandler',
)



# Schema for validating custom metrics model creation
_CUSTOM_MODEL_CREATION_SCHEMA = loadSchema("custom_model_creation_schema.json")



def formatMetricRowProxy(metricObj):
  if metricObj.tag_name is not None and len(metricObj.tag_name) > 0:
    displayName = "%s (%s)" % (metricObj.tag_name, metricObj.server)
  else:
    displayName = metricObj.server

  if (hasattr(metricObj, "parameters") and
      isinstance(metricObj.parameters, basestring)):
    parameters = json.loads(metricObj.parameters)
  else:
    parameters = metricObj.parameters

  engine = repository.engineFactory()

  allowedKeys = set([col.name for col in getMetricDisplayFields(engine)])

  metricDict = dict((col, getattr(metricObj, col))
                    for col in metricObj.keys()
                    if col in allowedKeys)

  metricDict["display_name"] = displayName
  metricDict["parameters"] = parameters

  return metricDict



class ModelHandler(AuthenticatedBaseHandler):


  @classmethod
  def scrubModelParamsFromLegacyModelSpec(cls, modelSpec):
    """ Create modelParams from legacy modelSpec

    :param modelSpec: legacy modelSpec
    ::
        {
          ...

          "min": 0.0,  # optional
          "max": 5000.0  # optional
        }

    :returns: modelParams dict if there were model params in legacy modelSpec;
      None otherwise
    ::
        {
          "min": 0.0,  # optional
          "max": 5000.0  # optional
        }
    """
    # min/max
    modelParams = dict()
    if "min" in modelSpec:
      modelParams["min"] = modelSpec["min"]
    if "max" in modelSpec:
      modelParams["max"] = modelSpec["max"]
    if modelParams:
      return modelParams
    else:
      return None


  @classmethod
  def createModel(cls, modelSpec=None):
    """
    NOTE MER-3479: this code path is presently incorrectly used for two
      purposes:
        * Importing of all types of metrics (not desirable; there should be a
          separate endpoint or an import-specific flag in this endpoint for
          importing that facilitates slightly different behavior, such as
          suppressing certain errors to allow for re-import in case of tranisent
          error part way through the prior import)
    """

    if not modelSpec:
      # Metric data is missing
      log.error("Data is missing in request, raising BadRequest exception")
      raise InvalidRequestResponse({"result": "Metric data is missing"})

    # TODO MER-3479: import using import-specific endpoint
    # NOTE: pending MER-3479, this is presently a hack for exercising
    #   the adapter import API
    importing = False

    if modelSpec.get("datasource") == "custom":
      if "data" in modelSpec:
        importing = True

    try:
      adapter = createDatasourceAdapter(modelSpec["datasource"])
      try:
        # TODO: Maybe initialize transaction and commit here
        if importing:
          # TODO MER-3479: import using import-specific endpoint
          # NOTE: pending MER-3479, this is presently a hack for exercising
          #   the adapter import API
          metricId = adapter.importModel(modelSpec)
        else:
          metricId = adapter.monitorMetric(modelSpec)
      except app_exceptions.MetricAlreadyMonitored as e:
        metricId = e.uid

      with web.ctx.connFactory() as conn:
        return repository.getMetric(conn, metricId)
    except (ValueError, app_exceptions.MetricNotSupportedError) as e:
      raise InvalidRequestResponse({"result": repr(e)})


  @staticmethod
  def createModels(data=None):
    if data:
      if isinstance(data, basestring):
        request = utils.jsonDecode(data)
      else:
        request = data

      if not isinstance(request, list):
        request = [request]

      response = []
      for nativeMetric in request:
        try:
          response.append(ModelHandler.createModel(nativeMetric))
        except app_exceptions.ObjectNotFoundError:
          # This happens when there is a race condition between creating the
          # model and another thread/process deleting the metric or metric data.
          # TODO: it does't make sense that this error is suppressed and that
          #   it's reported this way inside the response list among dao.Metric
          #   objects.
          response.append("Model failed during creation. Please try again.")
      return response

    # Metric data is missing
    log.error("Data is missing in request, raising BadRequest exception")
    raise web.badrequest("Metric data is missing")


  @staticmethod
  def getAllModels():
    with web.ctx.connFactory() as conn:
      return repository.getAllModels(conn, getMetricDisplayFields(conn))


  @staticmethod
  def getModel(metricId):
    try:
      with web.ctx.connFactory() as conn:
        metric = repository.getMetric(conn,
                                      metricId,
                                      getMetricDisplayFields(conn))
      return metric
    except app_exceptions.ObjectNotFoundError:
      raise web.notfound("ObjectNotFoundError Metric not found: Metric ID: %s"
                         % metricId)


  @staticmethod
  def deleteModel(metricId):
    try:
      with web.ctx.connFactory() as conn:
        metricRow = repository.getMetric(conn, metricId)
    except app_exceptions.ObjectNotFoundError:
      raise web.notfound("ObjectNotFoundError Metric not found: Metric ID: %s"
                         % metricId)

    log.debug("Deleting model for %s metric=%s", metricRow.datasource,
              metricId)
    # NOTE: this is the new way using datasource adapters
    try:
      createDatasourceAdapter(metricRow.datasource).unmonitorMetric(metricId)
    except app_exceptions.ObjectNotFoundError:
      raise web.notfound(
        "ObjectNotFoundError Metric not found: Metric ID: %s" % (metricId,))

    return utils.jsonEncode({'result': 'success'})


  #=============================================================================
  def GET(self, modelId=None):
    """
    List all models or a specific model if one is given

    ::

        GET /_models/{model-id}

    Returns:

    ::

        [{
            "description":
              "DiskWriteBytes on EC2 instance i-12345678 in us-west-2 region",
            "display_name": "YOMP-docs (i-12345678)",
            "last_rowid": 4053,
            "last_timestamp": "2013-12-12 00:00:00",
            "location": "us-west-2",
            "message": null,
            "name": "AWS/EC2/DiskWriteBytes",
            "parameters": "{"InstanceId": "i-12345678", "region": "us-west-2"}",
            "poll_interval": 300,
            "server": "i-12345678",
            "status": 1,
            "tag_name": "YOMP-docs",
            "uid": "2a123bb1dd4d46e7a806d62efc29cbb9"
          }, ...
        ]
    """
    try:
      if modelId is None:
        modelRows = self.getAllModels()
      else:
        modelRows = [self.getModel(modelId)]

      self.addStandardHeaders()

      return utils.jsonEncode([formatMetricRowProxy(modelRow)
                               for modelRow in modelRows])

    except web.HTTPError as ex:
      log.info(str(ex) or repr(ex))
      raise ex

    except Exception as ex:
      log.exception("GET Failed")
      raise web.internalerror(str(ex) or repr(ex))

  def DELETE(self, modelId):
    try:
      self.addStandardHeaders()
      return self.deleteModel(modelId)
    except web.HTTPError as ex:
      log.info(str(ex) or repr(ex))
      raise ex
    except Exception as ex:
      log.exception("DELETE Failed")
      raise web.internalerror(str(ex) or repr(ex))

  def POST(self, modelId=None):
    """
    Create Model (Same as PUT command)

    ::

        POST /_models

    Data: Use the metric as returned by the datasource metric list.

    For example, create a custom model, include the following data in the
    POST request (uid is the same for the metric and model):

    ::

        {
            "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
            "datasource": "custom",
            "min": 0.0,
            "max": 5000.0
        }

    The "min" and "max" options are optional.
    """
    return self.PUT(modelId)

  def PUT(self, modelId=None):
    """
    Create Model

    ::

        POST /_models

    Data: Use the metric as returned by the datasource metric list.

    For example, create a custom model, include the following data in the
    POST request (uid is the same for the metric and model):

    ::

        {
            "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
            "datasource": "custom",
            "min": 0.0,
            "max": 5000.0
        }

    The "min" and "max" options are optional.
    """
    if modelId:
      # ModelHandler is overloaded to handle both single-model requests, and
      # multiple-model requests.  As a result, if a user makes a POST, or PUT
      # request, it's possible that the request can be routed to this handler
      # if the url pattern matches.  This specific POST handler is not meant
      # to operate on a known model, therefore, raise an exception, and return
      # a `405 Method Not Allowed` response.
      raise NotAllowedResponse({"result": "Not supported"})

    data = web.data()
    if data:
      try:
        if isinstance(data, basestring):
          request = utils.jsonDecode(data)
        else:
          request = data
      except ValueError as e:
        response = "InvalidArgumentsError(): " + repr(e)
        raise InvalidRequestResponse({"result": response})

      if not isinstance(request, list):
        request = [request]

      response = []
      for nativeMetric in request:
        try:
          validate(nativeMetric, _CUSTOM_MODEL_CREATION_SCHEMA)

        except ValidationError as e:
          # Catch ValidationError if validation fails
          # InvalidRequestResponse produces an HTTP 400 error code
          response = "InvalidArgumentsError(): " + repr(e)
          raise InvalidRequestResponse({"result": response})
    else:
      # Metric data is missing
      log.error("Data is missing in request, raising BadRequest exception")
      raise web.badrequest("Metric data is missing")

    try:
      self.addStandardHeaders()
      metricRowList = self.createModels(data)

      metricDictList = [formatMetricRowProxy(metricRow)
                        for metricRow in metricRowList]
      response = utils.jsonEncode(metricDictList)

      raise web.created(response)

    except web.HTTPError as ex:
      if bool(re.match("([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      log.exception("PUT Failed")
      raise web.internalerror(str(ex) or repr(ex))


class MetricDataHandler(AuthenticatedBaseHandler):

  def GET(self, metricId=None):
    """
    Get Model Data

    ::

        GET /_models/{model-id}/data?from={fromTimestamp}&to={toTimestamp}&anomaly={anomalyScore}&limit={numOfRows}

    Parameters:

      :param limit: (optional) max number of records to return
      :type limit: int
      :param from: (optional) return records from this timestamp
      :type from: timestamp
      :param to: (optional) return records up to this timestamp
      :type to: timestamp
      :param anomaly: anomaly score to filter
      :type anomaly: float

    Returns:

    ::

        {
            "data": [
                ["2013-08-15 21:34:00", 222, 0.025, 125],
                ["2013-08-15 21:32:00", 202, 0, 124],
                ["2013-08-15 21:30:00", 202, 0, 123],
                ...
            ],
            "names": [
                "timestamp",
                "value",
                "anomaly_score",
                "rowid
            ]
        }
    """
    queryParams = dict(urlparse.parse_qsl(web.ctx.env['QUERY_STRING']))
    fromTimestamp = queryParams.get("from")
    toTimestamp = queryParams.get("to")
    anomaly = float(queryParams.get("anomaly") or 0.0)
    limit = int(queryParams.get("limit") or 0)

    with web.ctx.connFactory() as conn:
      fields = (schema.metric_data.c.uid,
                schema.metric_data.c.timestamp,
                schema.metric_data.c.metric_value,
                schema.metric_data.c.anomaly_score,
                schema.metric_data.c.rowid)
      names = ("names",) + tuple(["value" if col.name == "metric_value"
                                  else col.name
                                  for col in fields])
      if fromTimestamp:
        sort = schema.metric_data.c.timestamp.asc()
      else:
        sort = schema.metric_data.c.timestamp.desc()

      result = repository.getMetricData(conn,
                                        metricId=metricId,
                                        fields=fields,
                                        fromTimestamp=fromTimestamp,
                                        toTimestamp=toTimestamp,
                                        score=anomaly,
                                        sort=sort)

    if "application/octet-stream" in web.ctx.env.get('HTTP_ACCEPT', ""):
      results_per_uid = defaultdict(int)
      packer = msgpack.Packer()
      self.addStandardHeaders(content_type='application/octet-stream')
      web.header('X-Accel-Buffering', 'no')

      yield packer.pack(names)
      for row in result:
        if not limit or (limit and len(results_per_uid[row.uid]) < limit):
          resultTuple = (
              row.uid,
              calendar.timegm(row.timestamp.timetuple()),
              row.metric_value,
              row.anomaly_score,
              row.rowid,
            )
          yield packer.pack(resultTuple)
          results_per_uid[row.uid] += 1
    else:

      if metricId is None:
        output = {}
        for row in result:
          uid = row.uid
          default = {"uid": uid, "data": []}
          recordTuple = (
            row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            row.metric_value,
            row.anomaly_score,
            row.rowid
          )
          metricDataRecord = output.setdefault(uid, default)
          if not limit or (limit and len(metricDataRecord["data"]) < limit):
            metricDataRecord["data"].append(recordTuple)

        results = {
          "metrics":  output.values(),
          "names": names[2:]
        }

      else:
        if limit:
          results = {"names": names[2:],
                     "data": [(row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                               row.metric_value,
                               row.anomaly_score,
                               row.rowid)
                              for row in itertools.islice(result, 0, limit)]}
        else:
          results = {"names": names[2:],
                     "data": [(row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                               row.metric_value,
                               row.anomaly_score,
                               row.rowid) for row in result]}
      self.addStandardHeaders()
      yield utils.jsonEncode(results)



class MetricDataStatsHandler(AuthenticatedBaseHandler):


  def GET(self):
    """
    Get model data stats

    ::

        GET /_models/data/stats

    Returns:

    ::

        {
            "processing_time_remaining": 37
        }
    """
    with repository.engineFactory().connect() as conn:
      unprocessedDataCount = repository.getUnprocessedModelDataCount(conn)
    processingTimeRemaining = int(math.ceil(
        unprocessedDataCount * _PROCESSING_TIME_PER_RECORD))

    self.addStandardHeaders()
    return utils.jsonEncode({
        "processing_time_remaining": processingTimeRemaining,
    })



class ModelExportHandler(AuthenticatedBaseHandler):
  @staticmethod
  def _exportNativeMetric(metric):
    return createDatasourceAdapter(metric.datasource).exportModel(metric.uid)

  def GET(self, metricId=None):
    """ Returns a dict sufficient for importing a new model from scratch """
    try:
      if metricId is not None:
        try:
          with web.ctx.connFactory() as conn:
            metricRow = (
              repository.getMetric(conn,
                                   metricId,
                                   fields=[schema.metric.c.uid,
                                           schema.metric.c.datasource]))
          nativeMetrics = [self._exportNativeMetric(metricRow)]
        except app_exceptions.ObjectNotFoundError:
          raise web.notfound("ObjectNotFoundError Metric not found: "
                             "Metric ID: %s" % metricId)
      else:
        with web.ctx.connFactory() as conn:
          metricRowList = repository.getAllModels(conn)
        if metricRowList:
          nativeMetrics = [self._exportNativeMetric(metricRow)
                           for metricRow in metricRowList]
        else:
          nativeMetrics = []

      self.addStandardHeaders()

      web.header("Content-Description", "Taurus Export")
      web.header("Expires", "0")
      web.header("Cache-Control", "must-revalidate, post-check=0, pre-check=0")

      data = web.input(filename=None)

      if data.filename:
        web.header("Content-Disposition", "attachment;filename=%s" % (
          data.filename))

      returned = utils.jsonEncode(nativeMetrics)

      web.header("Content-length", len(returned))
      return returned
    except web.HTTPError as ex:
      log.info(str(ex) or repr(ex))
      raise ex
    except Exception as ex:
      log.exception("GET Failed")
      raise web.internalerror(str(ex) or repr(ex))


app = ManagedConnectionWebapp(urls, globals())
