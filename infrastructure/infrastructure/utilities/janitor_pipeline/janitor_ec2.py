#!/usr/bin/env python
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

import argparse
import os

from datetime import datetime

from infrastructure.utilities.ec2 import getInstances, terminateInstance
from infrastructure.utilities.exceptions import MissingAWSKeysInEnvironment
from infrastructure.utilities.logger import initPipelineLogger, LOG_LEVELS


HOUR_IN_SECS = 3600


def parseArgs():
  """
    Parse the command line arguments

    :returns: The Parsed arguments from the command line
    :rtype: argparse.Namespace
  """

  parser = argparse.ArgumentParser(description="This script terminates "
                                               "stale EC2 instances.")
  parser.add_argument("--log-level",
                      dest="logLevel",
                      type=str,
                      default="info",
                      choices=LOG_LEVELS,
                      help="Logging level, optional parameter. Default: info")
  parser.add_argument("--region", dest="region", type=str, nargs="+",
                      help="EC2 regions in which stale instances are running. "
                           "Refer to "
                           "'http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html'"
                           " for valid options.",
                      required=True)


  args = parser.parse_args()
  return args


def toBeTerminated(instance, logger):
  """
  Returns whether instance should be terminated.

  :param instance: boto.ec2.instance.Instance object
  :returns: True if instance should be terminated. Otherwise False.
  :rtype: Bool
  """

  # Terminate instances which are more than three hours old and do not
  # have 'Name'
  currentTimeStamp = datetime.now()
  instanceTimeStamp = datetime.strptime(instance.launch_time.split(".")[0],
                                        "%Y-%m-%dT%H:%M:%S")
  instanceUptime = currentTimeStamp - instanceTimeStamp
  if (("Name" not in instance.tags or not instance.tags["Name"]) and
      instanceUptime.total_seconds() > HOUR_IN_SECS * 3):
    return True
  if (instance.tags["Name"].startswith("vertis_") and
      not instance.tags["Name"].startswith("vertis_donotremove_")):
    return True
  return False


def main(args):
  """
  This function will terminate the stale instances running the regions
  passed as parameter to the script.
  Instances which satisfy following conditions will be terminated.
  - Name of the instance starts with 'vertis_'. Instances starting with
    'vertis_donotremove_' will not be terminated.
  - Instances which are running for more than three hours, and have blank
    'Name' tag.
  """

  logger = initPipelineLogger("janitor_ec2", logLevel=args.logLevel)

  awsAccessKeyId = os.environ.get("AWS_ACCESS_KEY_ID")
  awsScrectAccessKey = os.environ.get("AWS_SECRET_ACCESS_KEY")

  if not (awsAccessKeyId and awsScrectAccessKey):
    logger.error("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    raise MissingAWSKeysInEnvironment("AWS keys are not set")

  # required for terminateInstance function
  config = {}
  config["AWS_ACCESS_KEY_ID"] = awsAccessKeyId
  config["AWS_SECRET_ACCESS_KEY"] = awsScrectAccessKey
  for region in args.region:
    instances = [i.id for i in getInstances(region, awsAccessKeyId,
                                            awsScrectAccessKey, logger)
                 if toBeTerminated(i, logger)]
    if instances:
      config["REGION"] = region
      logger.info("Deleting {}".format(", ".join(instances)))
      for instance in instances:
        terminateInstance(instance, config, logger)
    else:
      logger.info("None of the instances are stale.")


if __name__ == "__main__":
  main(parseArgs())
