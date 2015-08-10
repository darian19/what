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
"""
 Bunch of helper methods for handling various EC2 instances.
"""

import os

from time import sleep

import boto.ec2

from infrastructure.utilities import jenkins
from infrastructure.utilities.exceptions import (CommandFailedError,
                                                 InstanceLaunchError,
                                                 InstanceNotFoundError,
                                                 InvalidParametersError)
from infrastructure.utilities.ssh import runCommandBySSH


DEFAULT_REGION = "us-west-2"
MAX_RETRIES_FOR_INSTANCE_READY = 18
SLEEP_DELAY = 10



def getEC2Connection(config):
  """
    Connects to EC2 and returns the connection.

    :param config: A dict containing values for `AWS_ACCESS_KEY_ID`
      and `AWS_SECRET_ACCESS_KEY`

    :returns: An EC2Connection.
  """
  # TODO: TAUR-215 - Add retry decorator
  return boto.ec2.connect_to_region(config["REGION"],
    aws_access_key_id = config["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key = config["AWS_SECRET_ACCESS_KEY"])


def launchInstance(amiID, config, logger):
  """
    Launch an instance using the AMI-id and other options.
    Wait until the instance is up and return the instance-id
    and it"s public dns.

    :param instanceId: The Instance ID of the EC2 Instance that will be
      stopped.

    :param config: A dict containing values for `REGION`, `AWS_ACCESS_KEY_ID`,
      and `AWS_SECRET_ACCESS_KEY`. It also needs:
      - `KEY` = The SSH pub key to use for initialization (e.g.: chef_west)
      - `INSTANCE_TYPE` = The size of EC2 instance to use (e.g.: m3.medium)
      - `JOB_NAME` = used to tag the instance launched
      - `BUILD_NUMBER` = used to tag the instance launched

    :param logger: An initialized logger from the calling pipeline.

    :raises: infrastructure.utilities.exceptions.InstanceLaunchError
      If the instance fails to launch in a set amount of time.

    :returns: A tuple containing the public DNS entry for the server and the
      EC2 Instance ID, in that order.
  """

  # Make sure we have the right security groups setup for the instance. We use
  # `basic_server` to allow SSH access from our office and specified secure IPs.
  # `YOMP_server` allows access to the server from ports 80 & 443 universally,
  # but can be limited if necessary.
  if config["REGION"] == "us-west-2":
    securityGroups = ["basic_server", "YOMP_server"]
  if config["REGION"] == "us-east-1":
    securityGroups = ["basic_server", "YOMP_server_east"]

  conn = getEC2Connection(config)
  image = conn.get_image(amiID)

  logger.info("Launching instance from AMI: %s", amiID)
  reservation = image.run(key_name=config["KEY"],
                          security_groups=securityGroups,
                          instance_type=config["INSTANCE_TYPE"])

  instance = reservation.instances[0]
  instanceID = instance.id

  logger.debug("Waiting for instance %s to boot.", instanceID)
  for _ in xrange(MAX_RETRIES_FOR_INSTANCE_READY):
    logger.debug("Instance state: %s", instance.state)
    if instance.state == "pending":
      sleep(SLEEP_DELAY)
      instance.update()
    elif instance.state == "running":
      break
  else:
    terminateInstance(instanceID, config, logger)
    raise InstanceLaunchError("Instance took more than %d seconds to start" %
      MAX_RETRIES_FOR_INSTANCE_READY * SLEEP_DELAY)

  publicDnsName = instance.public_dns_name

  instanceTags = {}
  if os.environ.get("JENKINS_HOME"):
    instanceTags["Name"] = "%s-%s" % (os.environ["JOB_NAME"],
                                      jenkins.getBuildNumber())
  else:
    instanceTags["Name"] = "running-locally-by-user:%s" % os.getlogin()

  instanceTags["Description"] = "Testing AMI %s" % (amiID)

  if "BUILD_URL" in os.environ.keys():
    instanceTags["JENKINS_LINK"] = os.environ["BUILD_URL"]

  if "GIT_BRANCH" in os.environ.keys():
    instanceTags["GIT_BRANCH"] = os.environ["GIT_BRANCH"]

  if "GIT_COMMIT" in os.environ.keys():
    instanceTags["GIT_COMMIT"] = os.environ["GIT_COMMIT"]

  try:
    conn.create_tags([instanceID], instanceTags)
  except:
    terminateInstance(instanceID, config, logger)
    raise

  logger.info("Instance %s is running, public dns : %s", instanceID,
    publicDnsName)
  return publicDnsName, instanceID


def getInstances(region="us-west-2",
                 awsAccessKeyId=None,
                 awsSecretAccessKey=None,
                 logger=None):
  """
    List all the instances.

    :param region: AWS region
    :param awsAccessKeyId: AWS access key ID
    :param awsSecretAccessKey: AWS secret access key
    :param logger: An initialized logger from the calling pipeline.

    :returns: A list of instances
    :rtype: list
  """
  if not logger:
    raise InvalidParametersError("getInstances: Missing logger")
  if not awsAccessKeyId:
    raise InvalidParametersError("getInstances: Missing awsAccessKeyId")
  if not awsSecretAccessKey:
    raise InvalidParametersError("getInstances: Missing awsSecretAccessKey")

  config = {}
  config["REGION"] = region
  config["AWS_ACCESS_KEY_ID"] = awsAccessKeyId
  config["AWS_SECRET_ACCESS_KEY"] = awsSecretAccessKey
  conn = getEC2Connection(config)
  instances = []
  reservations = conn.get_all_reservations()
  for reservation in reservations:
    for instance in reservation.instances:
      instances.append(instance)
  if not instances:
    logger.debug("No instances available for the given credentials.")
  return instances


def loadInstanceTags(instanceId,
                     logger,
                     awsAccessKeyId,
                     awsSecretAccessKey,
                     region=DEFAULT_REGION):
  """
  Read the tags from a given instanceID

  :param instanceId: Instance ID to read

  :param logger: Initialized logger object

  :param awsAccessKey: AWS access key. Required.

  :param awsSecretAccessKey: AWS secret access key. Required.

  :param region: AWS region the instance is in

  :returns: tags for an instance ID

  :rtype: boto instance tags object

  :raises CommandFailedError if it can't find the instanceID
  :raises InstanceNotFoundError if instanceId is not found in region
  :raises InvalidParametersError if the arguments fail sanity check
  """
  # Sanity check arguments
  if not logger:
    raise InvalidParametersError("loadInstanceTags requires a logger")
  if not awsAccessKeyId:
    raise InvalidParametersError("loadInstanceTags:Missing awsAccessKeyId")
  if not awsSecretAccessKey:
    raise InvalidParametersError("loadInstanceTags:Missing awsSecretAccessKey")

  ec2Config = { "AWS_ACCESS_KEY_ID": awsAccessKeyId,
                "AWS_SECRET_ACCESS_KEY": awsSecretAccessKey,
                "REGION": region }

  conn = getEC2Connection(config=ec2Config)

  # Load info for the instance
  reservations = conn.get_all_reservations(filters={"instance-id": instanceId})

  try:
    instance = reservations[0].instances[0]
    return instance.tags
  except IndexError:
    raise InstanceNotFoundError("Could not find instance %s in %s",
                                instanceId, region)


def stopInstance(instanceId, config, logger):
  """
    Stops the given running EC2 instance.

    :param instanceId: The Instance ID of the EC2 Instance that will be
      stopped.

    :param config: A dict containing values for `REGION`, `AWS_ACCESS_KEY_ID`,
      and `AWS_SECRET_ACCESS_KEY`

    :param logger: An initialized logger from the calling pipeline.
  """
  # TODO: TAUR-215 - Add retry decorator
  logger.info("Stopping instance : %s", instanceId)
  conn = getEC2Connection(config)
  conn.stop_instances(instance_ids=[instanceId])


def terminateInstance(instanceId, config, logger):
  """
    Terminates the given running EC2 instance.

    :param instanceId: The Instance ID of the EC2 Instance that will be
      terminated.

    :param config: A dict containing values for `REGION`, `AWS_ACCESS_KEY_ID`,
      and `AWS_SECRET_ACCESS_KEY`

    :param logger: An initialized logger from the calling pipeline.
  """
  # TODO: TAUR-215 - Add retry decorator
  logger.info("Terminating instance : %s", instanceId)
  conn = getEC2Connection(config)
  conn.terminate_instances(instance_ids=[instanceId])
