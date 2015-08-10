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

import re
import web

import boto.exception

from htmengine import utils
import htmengine.model_swapper.utils as model_swapper_utils
from YOMP.app.adapters.datasource import (createAutostackDatasourceAdapter,
                                          createCloudwatchDatasourceAdapter)
from YOMP.app.exceptions import DuplicateRecordError, ObjectNotFoundError
from YOMP.app.webservices import (AuthenticatedBaseHandler,
                                  ManagedConnectionWebapp)
from YOMP.app.webservices.responses import (InvalidRequestResponse,
                                            quotaErrorResponseWrapper)
from YOMP.app.webservices.utils import (getMetricDisplayFields,
                                        convertMetricRowToMetricDict)
from YOMP.app.exceptions import QuotaError
from YOMP import YOMP_logging
from YOMP.app import repository
from YOMP.app.quota import checkQuotaForInstanceAndRaise

log = YOMP_logging.getExtendedLogger("webservices")

urls = (
  r"/preview_instances/?", "AutostackInstancesHandler",
  r"/([-\w]+)/?", "AutostackHandler",
  r"/([-\w]+)/metrics/?([-\w]*)", "AutostackMetricsHandler",
  r"/([-\w]+)/instances/?", "AutostackInstancesHandler",
  r"/?", "AutostacksHandler",
 )



class AutostacksHandler(AuthenticatedBaseHandler):

  def GET(self): # pylint: disable=C0103
    """
      Get list of autostacks

      Example request::

        GET /_autostacks

      Example response::

        [
          {
            "name": {name}
            "region": {region}
            "filters": {
              "tag:{Name}": ["{value}", "{value}", ...],
              "tag:{Description}": ["{value}", "{value}", ...],
              "tag:{etc}": ["{value}", "{value}", ...]
            },
            "uid": {uid}
          }
          ...
        ]

    """
    self.addStandardHeaders()
    with web.ctx.connFactory() as conn:
      autostackRows = repository.getAutostackList(conn)
    autostackList = [{"uid":autostack.uid,
                      "name":autostack.name,
                      "region":autostack.region,
                      "filters":utils.jsonDecode(autostack.filters)}
                     for autostack in autostackRows]

    return utils.jsonEncode(autostackList)


  @quotaErrorResponseWrapper
  def POST(self): # pylint: disable=C0103
    r"""
      Create an Autostack

      ::

          POST /_autostacks

          {
            "name": {name},
            "region": {region},
            "filters": {
              "tag:{Name}": ["{value}", "{value}", ...],
              "tag:{Description}": ["{value}", "{value}", ...],
              "tag:{etc}": ["{value}", "{value}", ...]
            }
          }

      Request body must be a dictionary that includes:

      :param name: Unique autostack name
      :type name: str
      :param region: AWS region
      :type region: str
      :param filters: AWS Tag value pattern
      :type filters: dict

      The creation request will be rejected if the filters match more than
      MAX_INSTANCES_PER_AUTOSTACK.

      From http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Filtering.html:

      ::

        You can also use wildcards with the filter values. An asterisk (*)
        matches zero or more characters, and a question mark (?) matches
        exactly one character. For example, you can use *database* as a filter
        value to get all EBS snapshots that include database in the
        description. If you were to specify database as the filter value, then
        only snapshots whose description equals database would be returned.
        Filter values are case sensitive. We support only exact string
        matching, or substring matching (with wildcards).

        Tip

          Your search can include the literal values of the wildcard
          characters; you just need to escape them with a backslash before the
          character. For example, a value of \*numenta\?\\ searches for the
          literal string *numenta?\.
    """
    try:
      self.addStandardHeaders()
      data = web.data()
      if not data:
        raise web.badrequest("Metric data is missing")
      nativeMetric = utils.jsonDecode(data)
      try:
        stackSpec = {
          "name": nativeMetric["name"],
          "aggSpec": {
            "datasource": "cloudwatch",  # only support cloudwatch for now
            "region": nativeMetric["region"],
            "resourceType": "AWS::EC2::Instance",  # only support EC2 for now
            "filters": nativeMetric["filters"]
          }
        }
        adapter = createAutostackDatasourceAdapter()

        with web.ctx.connFactory() as conn:
          checkQuotaForInstanceAndRaise(conn, None)

        autostack = adapter.createAutostack(stackSpec)
        result = dict(autostack.items())
      except DuplicateRecordError:
        # TODO [MER-3543]: Make sure this actually gets hit
        raise web.internalerror(
            "The name you are trying to use, '%s', is already in use in AWS "
            "region '%s'. Please enter a unique Autostack name." % (
                nativeMetric.get("name", "None"),
                nativeMetric.get("region", "None")))
      raise web.created(utils.jsonEncode(result))
    except (web.HTTPError, QuotaError) as ex:
      if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      log.exception("POST Failed")
      raise web.internalerror(str(ex) or repr(ex))



class AutostackInstancesHandler(AuthenticatedBaseHandler):

  @staticmethod
  def formatInstance(instance, keys=("instanceID", "state", "instanceType",
                                     "launchTime", "tags", "regionName")):
    """ Format InstanceInfo namedtuple to dict for API consumption

        :param instance: InstanceInfo object
        :type instance: YOMP.app.runtime.aggregator_instances.InstanceInfo
        :param keys: Keys to be included in resulting dict
        :type keys: tuple
        :return: Formatted InstanceInfo dict containing keys defined by keys
                 kwarg, and corresponding values from original InstanceInfo
                 object.  `lanchTime` is converted explicitly to ISO format.
        :rtype: dict
    """
    # convert to dict (for mutability)
    instance = instance._asdict()

    # Strip +00:00 timezone suffix (if present)
    (timestamp, _, _) = instance["launchTime"].isoformat().partition("+")
    # Strip franctional seconds (if present)
    (timestamp, _, _) = timestamp.partition(".")
    # Add "Zulu" timezone abbreviation for UTC
    instance["launchTime"] = timestamp + "Z"

    # Return only the keys we want
    return dict((key, instance[key]) for key in keys)



  def GET(self, autostackId=None): # pylint: disable=C0103
    """
      Get instances for known Autostack:

      ::

          GET /_autostacks/{autostackId}/instances

      Preview Autostack instances:

      ::

          GET /_autostacks/preview_instances?region={region}&filters={filters}

      :param region: AWS Region Name
      :type region: str
      :param filters: AWS Tag value pattern
      :type value: str (JSON object)

      Example query params:

      ::

          region=us-west-2&filters={"tag:Name":["jenkins-master"]}

      :return: List of instance details.  See
               AutostackInstancesHandler.formatInstance() for implementation.

      Example return value:

      ::

          [
            {
              "instanceID": "i-12345678",
              "state": "stopped",
              "regionName": "us-west-2",
              "instanceType": "m1.medium",
              "launchTime": "2013-09-24T02:02:48Z",
              "tags": {
                "Type": "Jenkins",
                "Description": "Jenkins Master",
                "Name": "jenkins-master"
              }
            },
            {
              "instanceID": "i-12345678",
              "state": "running",
              "regionName": "us-west-2",
              "instanceType": "m1.large",
              "launchTime": "2013-12-19T12:02:31Z",
              "tags": {
                "Type": "Jenkins",
                "Name": "jenkins-master",
                "Description": "Jenkin Master(Python 2.7)"
              }
            }
          ]
    """
    self.addStandardHeaders()
    aggSpec = {
      "datasource": "cloudwatch",  # only support EC2 for now
      "region": None,  # to be filled below
      "resourceType": "AWS::EC2::Instance",  # only support EC2 for now
      "filters": None  # to be filled below
    }
    adapter = createCloudwatchDatasourceAdapter()
    if autostackId is not None:
      try:
        with web.ctx.connFactory() as conn:
          autostackRow = repository.getAutostack(conn, autostackId)
      except ObjectNotFoundError:
        raise web.notfound("Autostack not found: Autostack ID: %s"
                           % autostackId)
      except web.HTTPError as ex:
        if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
          # Log 400-599 status codes as errors, ignoring 200-399
          log.error(str(ex) or repr(ex))
        raise
      except Exception as ex:
        raise web.internalerror(str(ex) or repr(ex))
      aggSpec["region"] = autostackRow.region
      aggSpec["filters"] = autostackRow.filters
      result = adapter.getMatchingResources(aggSpec)
    else:
      data = web.input(region=None, filters=None)
      if not data.region:
        raise InvalidRequestResponse({"result":"Invalid region"})
      if not data.filters:
        raise InvalidRequestResponse({"result":"Invalid filters"})

      try:
        aggSpec["region"] = data.region
        aggSpec["filters"] = utils.jsonDecode(data.filters)
        result = adapter.getMatchingResources(aggSpec)
      except boto.exception.EC2ResponseError as responseError:
        raise InvalidRequestResponse({"result": responseError.message})

    if result:
      return utils.jsonEncode([self.formatInstance(instance)
                               for instance in result])

    return utils.jsonEncode([])



class AutostackHandler(AuthenticatedBaseHandler):
  def DELETE(self, autostackId): # pylint: disable=C0103,R0201
    """
      Delete an Autostack

      ::

          DELETE /_autostacks/{autostackId}
    """
    try:
      with web.ctx.connFactory() as conn:
        modelIDs = tuple(m.uid for m in
                         repository.
                           getAutostackMetrics(conn,
                                               autostackId))

      with web.ctx.connFactory() as conn:
        repository.deleteAutostack(conn, autostackId)

      # Delete the corresponding Engine models, if any
      for modelID in modelIDs:
        model_swapper_utils.deleteHTMModel(modelID)
      raise web.HTTPError(status="204 No Content")
    except ObjectNotFoundError:
      raise web.notfound("Autostack not found: Autostack ID: %s" % autostackId)
    except web.HTTPError as ex:
      if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      log.exception("DELETE Failed")
      raise web.internalerror(str(ex) or repr(ex))


class AutostackMetricsHandler(AuthenticatedBaseHandler):

  def GET(self, autostackId, *args): # pylint: disable=C0103,W0613
    """
      Get Metrics associated with autostack

      ::

          GET /_autostacks/{autostackId}/metrics

      NOTE: args is ignored.  Function signature for all method handlers must
      be compatible with the regexp pattern that matches.  POST optionally
      takes a second argument, DELETE requires it.
    """
    try:
      self.addStandardHeaders()
      engine = repository.engineFactory()
      metricRows = repository.getAutostackMetrics(engine,
                                                  autostackId,
                                                  getMetricDisplayFields(engine))
      metricsList = [convertMetricRowToMetricDict(metricRow)
                     for metricRow in metricRows]

      return utils.jsonEncode(metricsList)

    except ObjectNotFoundError:
      raise web.notfound("Autostack not found: Autostack ID: %s" % autostackId)
    except web.HTTPError as ex:
      if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      raise web.internalerror(str(ex) or repr(ex))


  def POST(self, autostackId, data=None): # pylint: disable=C0103,R0201
    """
      Create one or more Autostack Metric(s)

      ::

          POST /_autostacks/{autostackId}/metrics

          [
            {
              "namespace": "AWS/EC2",
              "metric": "CPUUtilization"
            },
            ...
          ]

      Request body is a list of items, each of which are a subset of the
      standard cloudwatch native metric, specifying only:

      :param namespace: AWS Namespace
      :type namespace: str
      :param metric: AWS Metric name
      :type str:

      `datasource`, `region`, and `dimensions` normally required when creating
      models are not necessary.
    """
    try:
      self.addStandardHeaders()
      with web.ctx.connFactory() as conn:
        autostackRow = repository.getAutostack(conn,
                                               autostackId)
      data = data or utils.jsonDecode(web.data())

      for nativeMetric in data:
        try:
          if nativeMetric["namespace"] == "Autostacks":
            slaveDatasource = "autostack"
          else:
            slaveDatasource = "cloudwatch"  # only support cloudwatch for now

          modelParams = {}
          if "min" and "max" in nativeMetric:
            modelParams["min"] = nativeMetric["min"]
            modelParams["max"] = nativeMetric["max"]

          modelSpec = {
            "datasource": "autostack",
            "metricSpec": {
              "autostackId": autostackRow.uid,
              "slaveDatasource": slaveDatasource,
              "slaveMetric": nativeMetric
            },
            "modelParams": modelParams
          }

          metricId = (createAutostackDatasourceAdapter()
                      .monitorMetric(modelSpec))
          with web.ctx.connFactory() as conn:
            metricRow = repository.getMetric(conn, metricId)
          metricDict = convertMetricRowToMetricDict(metricRow)

        except KeyError:
          raise web.badrequest("Missing details in request")

        except ValueError:
          response = {"result": "failure"}
          raise web.badrequest(utils.jsonEncode(response))

      response = {"result": "success", "metric": metricDict}
      raise web.created(utils.jsonEncode(response))

    except ObjectNotFoundError:
      raise web.notfound("Autostack not found: Autostack ID: %s" % autostackId)
    except (web.HTTPError) as ex:
      if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      log.exception("POST Failed")
      raise web.internalerror(str(ex) or repr(ex))


  def DELETE(self, autostackId, metricId): # pylint: disable=C0103,R0201
    """
      Remove a specific metric from autostack

      ::

          DELETE /_autostacks/{autostackId}/metrics/{metricId}
    """
    try:
      # The if statement makes sure that the metric belongs to the autostack
      with web.ctx.connFactory() as conn:
        autostackObj = repository.getAutostackFromMetric(conn, metricId)

      if autostackId != autostackObj.uid:
        raise InvalidRequestResponse(
          {"result": "Metric=%s does not belong to autostack=%s"
           % (metricId, autostackId)})

      with web.ctx.connFactory() as conn:
        repository.deleteMetric(conn, metricId)

      model_swapper_utils.deleteHTMModel(metricId)
      raise web.HTTPError(status="204 No Content")
    except ObjectNotFoundError:
      raise web.notfound(("Autostack or metric not found: autostack=%s, "
                          "metric=%s") % (autostackId, metricId))
    except web.HTTPError as ex:
      if bool(re.match(r"([45][0-9][0-9])\s?", web.ctx.status)):
        # Log 400-599 status codes as errors, ignoring 200-399
        log.error(str(ex) or repr(ex))
      raise
    except Exception as ex:
      log.exception("DELETE Failed")
      raise web.internalerror(str(ex) or repr(ex))



app = ManagedConnectionWebapp(urls, globals())
