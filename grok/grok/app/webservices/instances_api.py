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
import json
import Queue
import threading

from validictory import validate, ValidationError
import web

from YOMP import YOMP_logging
from YOMP.app import config, repository
from YOMP.app.adapters import datasource
from YOMP.app.adapters.datasource import cloudwatch
from YOMP.app.aws import asg_utils, ec2_utils, elb_utils, rds_utils
from YOMP.app.webservices import (AuthenticatedBaseHandler,
                                  ManagedConnectionWebapp)
from YOMP.app.webservices.models_api import ModelHandler
from YOMP.app.webservices.responses import (
    quotaErrorResponseWrapper,
    InvalidRequestResponse)
from YOMP.app.webservices.utils import encodeJson, loadSchema

# Number of instances to suggest (pre-checked)
_NUM_SUGGESTED_INSTANCES = 8
# Max number of instances to suggest including alternates (unchecked)
_MAX_SUGGESTED_INSTANCES_TOTAL = 28
# Time limit for fetching AWS instances
_AWS_INSTANCE_FETCHING_TIME_LIMIT = 5.0

log = YOMP_logging.getExtendedLogger("webservices")

urls = (
  "/(.+?)/(.+?\/.+?)/(.+\/*.+)", "InstanceDefaultsHandler",
  "/(.+)/(.+\/.+)", "InstanceDefaultsHandler",
  "/?", "InstancesHandler",
  # /_instances/suggestions
  "/suggestions", "InstanceSuggestionsHandler",
  # /_instances/suggestions/us-west-2
  "/suggestions/(.+?)", "InstanceSuggestionsHandler",
)

# Validation schema to ensure we are getting an array of strings.
# Does not validate valid region or namespace, those are handled elsewhere.
_INSTANCES_MODEL_CREATION_SCHEMA = loadSchema(
  "instances_model_creation_schema.json")



class InstanceDefaultsHandler(AuthenticatedBaseHandler):


  @quotaErrorResponseWrapper
  def POST(self, region, namespace, instanceId=None):
    """
    Monitor a set of default metrics for a specific instance

    ::

        POST /_instances/{region}/{namespace}/{instanceId}

    Returns:

    ::

        {
            "result": "success"
        }

    OR

    Monitor a set of default metrics for multiple specific instances

    ::

        POST /_instances/{region}/{namespace}

    POST data:

    ::

        [
            {instanceId},
            ...
        ]

    Returns:

    ::

        {
            "result": "success"
        }

    Note:
    We expect a 200 OK even when attempting to POST to an instanece in the wrong
    namespace or the wrong region, this saves the overhead of asking AWS if
    we're dealing with a valid instance in the given namespace or region
    with every POST request.
    We expect the CLI user to know the correct instance ID.
    """
    if instanceId is None:
      try:
        dimension = None
        instances = json.loads(web.data())
      except:
        raise InvalidRequestResponse({"result": "Invalid request"})

    else:
      (dimension, _, identifier) = instanceId.rpartition("/")
      instances = [identifier]

    # Check for invalid region or namespace
    cwAdapter = datasource.createDatasourceAdapter("cloudwatch")

    supportedRegions = set(region for region, _desc in
                           cwAdapter.describeRegions())
    if region not in supportedRegions:
      raise InvalidRequestResponse({"result": ("Not supported. Region '%s' was"
                                               " not found.") % region})

    supportedNamespaces = set()
    for resourceInfo in cwAdapter.describeSupportedMetrics().values():
      for metricInfo in resourceInfo.values():
        supportedNamespaces.add(metricInfo["namespace"])
    if namespace not in supportedNamespaces:
      raise InvalidRequestResponse({"result": ("Not supported. Namespace '%s' "
                                               "was not found.") % namespace})

    try:
      # Attempt to validate instances list using validictory
      validate(instances, _INSTANCES_MODEL_CREATION_SCHEMA)
    except ValidationError as e:
      response = "InvalidArgumentsError: " + str(e)
      raise InvalidRequestResponse({"result": response})

    if instances:
      for instanceId in instances:
        server = "/".join([region, namespace, instanceId])
        with web.ctx.connFactory() as conn:
          numMetrics = repository.getMetricCountForServer(conn, server)
        if numMetrics > 0:
          # Metrics exist for instance id.
          pass

        else:
          try:
            resourceType = cloudwatch.NAMESPACE_TO_RESOURCE_TYPE[namespace]
          except KeyError:
            raise InvalidRequestResponse({"result": "Not supported."})

          modelSpecs = cwAdapter.getDefaultModelSpecs(
              resourceType, region, instanceId, dimension)

          for modelSpec in modelSpecs:
            ModelHandler.createModel(modelSpec)

    self.addStandardHeaders()
    return encodeJson({"result": "success"})



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
      instances = json.loads(web.data())
    except:
      raise InvalidRequestResponse({"result": "Invalid request"})

    if not instances:
      raise InvalidRequestResponse({"result": ("Missing instances in DELETE"
                                               " request")})

    deleted = []
    if instances:
      for server in instances:
        if server.count("/") == 4:
          (lhs, _, identifier) = server.rpartition("/")
          (regionAndNamespace, _, _) = lhs.rpartition("/")
          serverSansDimension = regionAndNamespace + "/" + identifier
        else:
          serverSansDimension = server
        with web.ctx.connFactory() as conn:
          modelIds = repository.listMetricIDsForInstance(conn,
                                                         serverSansDimension)
        if modelIds:
          for modelId in modelIds:
            ModelHandler.deleteModel(modelId)
          deleted.append(server)

    if instances == deleted:
      self.addStandardHeaders()
      return encodeJson({'result': 'success'})

    raise web.notfound("Not able to delete %s" %
                       encodeJson(list(set(instances)-set(deleted))))


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
    # To support idempotency requirements of the web ui, ensure that server
    # parameter matches the same pattern as is required for POST, and DELETE.
    # This means inserting the dimension between the namespace and identifier
    # for AWS-only.  Autostacks are ignored here.
    for instance in instances:
      if "/AWS/" in instance["server"]:
        dimensions = instance["parameters"]["metricSpec"]["dimensions"]

        for (dimension, value) in dimensions.iteritems():
          if instance["server"].endswith("/" + value):
            # We're looking for the identifying dimension in the instance
            # parameters
            (lhs, _, identifier) = (instance["server"].rpartition("/"))
            instance["server"] = "/".join([lhs, dimension, identifier])
          if instance["message"] is "":
            instance["message"] = None

    self.addStandardHeaders()
    return encodeJson(instances)



class InstanceSuggestionsHandler(AuthenticatedBaseHandler):


  def GET(self, region=None): # pylint: disable=R0201
    """
    Get quick selection instance suggestions to monitor

    ::

        GET /_instances/suggestions

    Sample Output:

    ::

        {
            "suggested": [
              {
                  "region": "us-west-2",
                  "namespace": "AWS/EC2",
                  "id": "i-12345678"
              },
              ... (up to 8 total suggested) ...
          ],
          "alternates": [
              {
                  "region": "us-west-2",
                  "namespace": "AWS/ELB",
                  "id": "YOMP-docs-elb"
              },
              ... (up to 22 total alternatives) ...
          ]
      }
      """
    if region is None:
      region = config.get("aws", "default_region")

    ec2Queue = Queue.Queue()
    ec2Thread = threading.Thread(
        target=ec2_utils.getSuggestedInstances,
        args=(region, ec2Queue, _AWS_INSTANCE_FETCHING_TIME_LIMIT))
    ec2Thread.start()

    rdsQueue = Queue.Queue()
    rdsThread = threading.Thread(
        target=rds_utils.getSuggestedInstances,
        args=(region, rdsQueue, _AWS_INSTANCE_FETCHING_TIME_LIMIT))
    rdsThread.start()

    elbQueue = Queue.Queue()
    elbThread = threading.Thread(
        target=elb_utils.getSuggestedInstances,
        args=(region, elbQueue, _AWS_INSTANCE_FETCHING_TIME_LIMIT))
    elbThread.start()

    asgQueue = Queue.Queue()
    asgThread = threading.Thread(
        target=asg_utils.getSuggestedInstances,
        args=(region, asgQueue, _AWS_INSTANCE_FETCHING_TIME_LIMIT))
    asgThread.start()

    response = {
        "suggested": [],
        "alternates": [],
    }

    # Wait for the threads to finish
    ec2Thread.join()
    rdsThread.join()
    elbThread.join()
    asgThread.join()

    n = 0
    done = False
    while n < _MAX_SUGGESTED_INSTANCES_TOTAL and not done:
      done = True

      # EC2 Instances
      try:
        instance = ec2Queue.get(block=False)
        if n < _NUM_SUGGESTED_INSTANCES:
          response["suggested"].append(instance)
        else:
          response["alternates"].append(instance)
        done = False
        n += 1
        if n >= _MAX_SUGGESTED_INSTANCES_TOTAL:
          break
      except Queue.Empty:
        pass

      # RDS Instances
      try:
        instance = rdsQueue.get(block=False)
        if n < _NUM_SUGGESTED_INSTANCES:
          response["suggested"].append(instance)
        else:
          response["alternates"].append(instance)
        done = False
        n += 1
        if n >= _MAX_SUGGESTED_INSTANCES_TOTAL:
          break
      except Queue.Empty:
        pass

      # Load Balancers
      try:
        instance = elbQueue.get(block=False)
        if n < _NUM_SUGGESTED_INSTANCES:
          response["suggested"].append(instance)
        else:
          response["alternates"].append(instance)
        done = False
        n += 1
        if n >= _MAX_SUGGESTED_INSTANCES_TOTAL:
          break
      except Queue.Empty:
        pass

      # AutoScaling groups
      try:
        instance = asgQueue.get(block=False)
        if n < _NUM_SUGGESTED_INSTANCES:
          response["suggested"].append(instance)
        else:
          response["alternates"].append(instance)
        done = False
        n += 1
        if n >= _MAX_SUGGESTED_INSTANCES_TOTAL:
          break
      except Queue.Empty:
        pass

    return encodeJson(response)



app = ManagedConnectionWebapp(urls, globals())
