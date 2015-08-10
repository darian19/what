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

from boto import ec2
from boto.ec2 import autoscale
from dateutil.tz import tzutc
from datetime import datetime
import dateutil.parser

def getLongRunningEC2Instances(region, awsAccessKeyId, awsSecretAccessKey,
                               instanceAge):
  """
  Returns the list of long running ec2 instances
  region : AWS region to query
  awsAccessKeyId : aws_access_key_id
  awsSecretAccessKey : aws_secret_access_key
  instanceAge : Accepted in number of days

  e.g.
  getLongRunningEC2Instances("us-west-2", os.environ["AWS_ACCESS_KEY_ID"],
      os.environ["AWS_SECRET_ACCESS_KEY"], 15)
  """
  ec2Conn = ec2.connect_to_region(
                  region_name=region,
                  aws_access_key_id=awsAccessKeyId,
                  aws_secret_access_key=awsSecretAccessKey)

  instances = ec2Conn.get_only_instances()
  runningInstances = filter(lambda instance: instance.state == "running",
                            instances)
  longRunningInstances = []
  for instance in runningInstances:
    nowutc = datetime.now(tzutc())
    launchTime = dateutil.parser.parse(instance.launch_time)
    activeTime = nowutc - launchTime
    if activeTime.days > instanceAge:
      longRunningInstances.append(instance)
  return longRunningInstances



def getLongRunningAutoscalingGroup(region, awsAccessKeyId, awsSecretAccessKey,
                                   groupAge):
  """
  Returns the list of long running autoscaling groups

  :param region : AWS region to query
  :param awsAccessKeyId : aws_access_key_id
  :param awsSecretAccessKey : aws_secret_access_key
  :param groupAge : Accepted in number of days
  :returns: A list of long-running autoscaling groups.

  e.g.
  getLongRunningEC2Instances(
      "us-west-2",
      os.environ["AWS_ACCESS_KEY_ID"],
      os.environ["AWS_SECRET_ACCESS_KEY"],
      15)
  """
  autoscalingConn = autoscale.connect_to_region(
    region_name=region,
    aws_access_key_id=awsAccessKeyId,
    aws_secret_access_key=awsSecretAccessKey)

  groups = autoscalingConn.get_all_groups()
  monitoredGroups = [group for group in groups if group.enabled_metrics]
  longRunningGroups = []
  for group in monitoredGroups:
    nowutc = datetime.now(tzutc())
    createdTime = dateutil.parser.parse(group.created_time)
    activeTime = nowutc - createdTime
    if activeTime.days > groupAge:
      longRunningGroups.append(group)
  return longRunningGroups
