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

import urlparse

import web

from htmengine import utils
import YOMP.app.adapters.datasource as datasource_adapter_factory
from YOMP.app.adapters.datasource.cloudwatch import NAMESPACE_TO_RESOURCE_TYPE
from YOMP.app.webservices import AuthenticatedBaseHandler



urls = (
  # /_metrics/cloudwatch
  "", "CWDefaultHandler",
  # /_metrics/cloudwatch/
  "/", "CWDefaultHandler",

  # /_metrics/cloudwatch/us-east-1/AWS/EC2/Tags
  "/([-\w]*)/AWS/Tags/*([-\w]*)/*([-\w]*)", "CWTagsHandler",

  # /_metrics/cloudwatch/namespaces
  "/namespaces", "CWNamespaceHandler",
  # /_metrics/cloudwatch/AWS/EC2
  "/(AWS/[-\w]*)", "CWNamespaceHandler",

  # /_metrics/cloudwatch/regions
  "/regions", "CWRegionsHandlerPublic",

  # /_metrics/cloudwatch/regions/us-west-2
  "/regions/([-\w]*)", "CWRegionsHandler",

  # /_metrics/cloudwatch/us-east-1/AWS/EC2
  "/([-\w]*)/(AWS/[-\w]*)", "CWInstanceHandler",
  # /_metrics/cloudwatch/us-east-1/AWS/EC2/instances/i-12345678
  "/([-\w]*)/(AWS/[-\w]*)/instances/([-\w]*)", "CWInstanceHandler",

  # /_metrics/cloudwatch/us-east-1/AWS/EC2/CPUUtilization
  "/([-\w]*)/(AWS/[-\w]*)/([-\w]*)", "CWMetricHandler",
)



def _translateResourcesIntoNamespaces(resources):
  # TODO: The new adapter interface organizes metrics by resource type rather
  # than namespace.  The web ui must be updated to follow this convention.
  # Until then, the API is remaining the same, requiring massaging data to
  # fit the expected response format
  namespaces = {}
  for _, metrics in resources.items():
    for (metricName, metric) in metrics.items():
      namespace = namespaces.setdefault(metric["namespace"], {})
      (namespace.setdefault("metrics", set())
                .add(metricName))
      (namespace.setdefault("dimensions", set())
                .update(metric["dimensionGroups"][0]))

  return namespaces


class CWDefaultHandler(AuthenticatedBaseHandler):
  def GET(self): # pylint: disable=R0201
    """
    Describe Cloudwatch datasource, listing all supported regions, namespaces
    and metrics

      ::

          GET /_metrics/cloudwatch

      Returns:

      ::

        {
            'regions': { 'region-name": 'region-description',...},
            'namespaces': {
                'namespace-name': {
                    'metrics': ['metric-name',...],
                    'dimensions': ['dimension-name',...]
                }, ....
            }
        }
    """
    web.header('Content-Type', 'application/json; charset=UTF-8', True)
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    resources = adapter.describeSupportedMetrics()

    return utils.jsonEncode(
      {"regions": dict(adapter.describeRegions()),
       "namespaces": _translateResourcesIntoNamespaces(resources)})



class CWRegionsHandlerPublic(object):
  def GET(self): # pylint: disable=R0201
    """
      Returns list of supported Clouwdwatch regions

      ::

          GET /_metrics/cloudwatch/regions

      Returns:

      ::

          { 'region-name': 'region-description',...}

      Sample output:

      ::

          {
            "ap-northeast-1": "Asia Pacific (Tokyo) Region",
            "ap-southeast-1": "Asia Pacific (Singapore) Region",
            "ap-southeast-2": "Asia Pacific (Sydney) Region",
            "eu-west-1": "EU (Ireland) Region",
            "sa-east-1": "South America (Sao Paulo) Region",
            "us-east-1": "US East (Northern Virginia) Region",
            "us-west-1": "US West (Northern California) Region",
            "us-west-2": "US West (Oregon) Region"
          }
    """
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    AuthenticatedBaseHandler.addStandardHeaders()
    return utils.jsonEncode(dict(adapter.describeRegions()))



class CWRegionsHandler(AuthenticatedBaseHandler):
  def GET(self, region):
    """
      List all existing Cloudwatch metrics for a given region

      ::

          GET /_metrics/cloudwatch/regions/{region}

      Returns:

      ::

          [
              {
                  'name': 'tag-or-empty-string',
                  'region': 'region-name',
                  'namespace': 'namespace-name',
                  'datasource': 'cloudwatch',
                  'identifier': 'id-from-dimension',
                  'metric': 'metric-name',
                  'dimensions': {
                      ...
                  }
              },...
          ]
    """

    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    resources = adapter.describeSupportedMetrics()

    def translateResourcesIntoMetrics():
      for resource, metrics in resources.items():
        for specificResource in adapter.describeResources(region, resource):
          for metric, cloudwatchParams in metrics.items():
            yield {"datasource": "cloudwatch",
                   "dimensions": {
                    cloudwatchParams["dimensionGroups"][0][0]:
                      specificResource["resID"]},
                   "identifier": specificResource["resID"],
                   "metric": metric,
                   "name": specificResource["name"],
                   "namespace": cloudwatchParams["namespace"],
                   "region": region}

    if region not in dict(adapter.describeRegions()):
      raise web.NotFound("Region '%s' was not found" % region)

    self.addStandardHeaders()
    return utils.jsonEncode(list(translateResourcesIntoMetrics()))



class CWNamespaceHandler(AuthenticatedBaseHandler):
  def GET(self, namespace=None):
    """
      List supported Cloudwatch namespaces

      ::

          GET /_metrics/cloudwatch/namespaces

      Returns:

      ::

          {'namespace-name1': {...},
           'namespace-name2': {...}
           ,...
        }


      OR

      List supported Cloudwatch metrics for a given namespace

      ::

          GET /_metrics/cloudwatch/{namespace-name}`

      Returns:

      ::

          {
              'namespace-name': {
                   'metrics': ['metric-name',...],
                   'dimensions': ['dimension-name',...]
              }
          }
    """
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    resources = adapter.describeSupportedMetrics()

    namespaces = _translateResourcesIntoNamespaces(resources)

    # Adding Autostacks namespaces to this list for now, to maintain API
    # backwards-compatibility during adapter refactor
    namespaces["Autostacks"] = {"metrics": ["InstanceCount"]}

    if namespace is None:
      self.addStandardHeaders()
      return utils.jsonEncode(namespaces)

    if not namespace in namespaces:
      raise web.NotFound("Namespace '%s' was not found" % namespace)

    self.addStandardHeaders()
    return utils.jsonEncode({str(namespace): namespaces[namespace]})


class CWMetricHandler(AuthenticatedBaseHandler):
  def GET(self, region, namespace, metric):
    """
      List all instances of the given metric for the given namespace in the
      region

      ::

          GET /_metrics/cloudwatch/{region-name}/{namespace-name}/{metric-name}

      Sample Output:

      ::

          [
            {
              "region":"regions-name",
              "namespace": "namespace-name",
              "datasource": "cloudwatch",
              "metric": "metric-name",
              "dimensions": {
                "dimension-name": "value-1",
                ...
              }
            },...
          ]
    """

    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    resources = adapter.describeSupportedMetrics()

    namespaces = _translateResourcesIntoNamespaces(resources)

    def translateResourcesIntoMetrics(namespace = None):
      for resource, metrics in resources.items():
        try:
          for specificResource in adapter.describeResources(region, resource):
            for metricName, cloudwatchParams in metrics.items():
              if (namespace and
                  cloudwatchParams["namespace"] == namespace and
                  metricName == metric):
                yield {"datasource": "cloudwatch",
                       "dimensions": {
                        cloudwatchParams["dimensionGroups"][0][0]:
                           specificResource["resID"]},
                       "metric": metricName,
                       "namespace": cloudwatchParams["namespace"],
                       "region": region}
        except NotImplementedError:
          # Metric exists but is otherwise not yet fully implemented.  When the
          # adapter no longer raises NotImplementedError, it will become
          # available.
          pass

    if region not in dict(adapter.describeRegions()):
      raise web.NotFound("Region '%s' was not found" % region)

    if not namespace in namespaces:
      raise web.NotFound("Namespace '%s' was not found" % namespace)

    if not metric in namespaces[namespace]["metrics"]:
      raise web.NotFound("Metric '%s' was not found" % metric)

    queryParams = dict(urlparse.parse_qsl(web.ctx.env['QUERY_STRING']))
    if not queryParams:
      self.addStandardHeaders()
      return utils.jsonEncode(list(translateResourcesIntoMetrics(namespace)))

    raise NotImplementedError("Unexpectedly received query params.")



class CWInstanceHandler(AuthenticatedBaseHandler):
  def GET(self, region, namespace, instance=None):
    """
    List metrics in the given namespace in the region [for a specific instance
    if specified]

    ::

        GET /_metrics/cloudwatch/{region}/{namespace}/instances/[{instance}]

    Sample Output:

    ::

        [
          {
            "dimensions": {
              "dimension-name": "value-1",
              ...
            }
            "region":"regions-name",
            "namespace": "namespace-name",
            "datasource": "cloudwatch",
            "identifier': "resource-id-from-dimension",
            "metric": "metric-name",
            "name": "name-tag-or-empty-string"
          },...
        ]

    Note:
    Expect a 200 OK even when attempting to GET from an invalid instance,
    this saves the overhead of asking AWS if we're dealing with a valid
    instance every GET.

    This fails silently. We expect the CLI user to know what Instance ID she is
    looking for.
    """

    data = web.input(tags=None)
    filters = None
    if data.tags:
      filters = {}
      kvpairs = [tag.strip() for tag in data.tags.split(",")]

      for kvpair in kvpairs:
        (key, _, value) = kvpair.partition(":")
        filters.setdefault("tag:" + key, []).append(value)

    if not namespace in NAMESPACE_TO_RESOURCE_TYPE:
      raise web.NotFound("Namespace '%s' was not found" % namespace)

    aggSpec = {"resourceType": NAMESPACE_TO_RESOURCE_TYPE[namespace],
               "region": region}

    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()

    resources = adapter.describeSupportedMetrics()

    namespaces = _translateResourcesIntoNamespaces(resources)

    if filters:
      aggSpec["filters"] = filters

      def translateResourcesIntoMetrics(namespace=None, instance=None):
        for metrics in resources.values():
          try:
            for specificInstance in adapter.getMatchingResources(aggSpec):
              for metricName, cloudwatchParams in metrics.items():
                if (namespace and
                    cloudwatchParams["namespace"] == namespace and
                    (instance is None or
                     instance == specificInstance.instanceID)):
                  yield {"datasource": "cloudwatch",
                       "dimensions": {
                        cloudwatchParams["dimensionGroups"][0][0]:
                           specificInstance.instanceID},
                       "identifier": specificInstance.instanceID,
                       "metric": metricName,
                       "name": specificInstance.tags["Name"],
                       "namespace": cloudwatchParams["namespace"],
                       "region": region}

          except NotImplementedError:
            # Metric exists but is otherwise not yet fully implemented.  When
            # the adapter no longer raises NotImplementedError, it will become
            # available.
            pass

    else:
      def translateResourcesIntoMetrics(namespace=None, instance=None):
        for resource, metrics in resources.items():
          try:
            for specificResource in adapter.describeResources(region,
                                                              resource):
              for metricName, cloudwatchParams in metrics.items():
                if (namespace and
                    cloudwatchParams["namespace"] == namespace and
                    (instance is None or
                     instance == specificResource["resID"])):
                  yield {"datasource": "cloudwatch",
                       "dimensions": {
                        cloudwatchParams["dimensionGroups"][0][0]:
                           specificResource["resID"]},
                       "identifier": specificResource["resID"],
                       "metric": metricName,
                       "name": specificResource["name"],
                       "namespace": cloudwatchParams["namespace"],
                       "region": region}

          except NotImplementedError:
            # Metric exists but is otherwise not yet fully implemented.  When
            # the adapter no longer raises NotImplementedError, it will become
            # available.
            pass

    if region not in dict(adapter.describeRegions()):
      raise web.NotFound("Region '%s' was not found" % region)

    self.addStandardHeaders()
    return utils.jsonEncode(list(translateResourcesIntoMetrics(namespace,
                                                               instance)))



app = web.application(urls, globals())

