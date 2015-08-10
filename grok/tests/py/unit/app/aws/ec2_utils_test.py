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

"""Tests for EC2 utility functions."""

import types
import unittest

from mock import Mock, patch

from YOMP.app.aws import ec2_utils



class EC2UtilsTest(unittest.TestCase):


  @patch("YOMP.app.aws.ec2_utils.getEC2Instances")
  def testGetSuggestedInstancesNone(self, getEC2InstancesMock):
    getEC2InstancesMock.return_value = []

    suggestions = ec2_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getEC2InstancesMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.ec2_utils.getEC2Instances")
  def testGetSuggestedInstancesNoRunning(self, getEC2InstancesMock):
    instanceMock1 = Mock(spec="boto.ec2.instance.Instance")
    instanceMock1.state = "stopped"
    getEC2InstancesMock.return_value = [
        instanceMock1,
    ]

    suggestions = ec2_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getEC2InstancesMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.ec2_utils.getEC2Instances")
  def testGetSuggestedInstancesTwoDifferentSize(self, getEC2InstancesMock):
    regionMock = Mock(spec="boto.ec2.region.Region")
    regionMock.name = "us-west-2"
    # Instance 1
    instanceMock1 = Mock(spec="boto.ec2.instance.Instance")
    instanceMock1.state = "running"
    instanceMock1.instance_type = "m3.large"
    instanceMock1.launch_time = "2014-05-06T15:17:33.324Z"
    instanceMock1.region = regionMock
    instanceMock1.id = "testId1"
    instanceMock1.tags = {"Name": "testName1"}
    # Instance 2
    instanceMock2 = Mock(spec="boto.ec2.instance.Instance")
    instanceMock2.state = "running"
    instanceMock2.instance_type = "m3.xlarge"
    instanceMock2.launch_time = "2014-05-06T15:18:33.324Z"
    instanceMock2.region = regionMock
    instanceMock2.id = "testId2"
    instanceMock2.tags = {"Name": "testName2"}
    getEC2InstancesMock.return_value = [
        instanceMock1,
        instanceMock2,
    ]

    suggestions = ec2_utils.getSuggestedInstances(regionMock.name)
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [
        {"id": "testId2", "name": "testName2", "namespace": "AWS/EC2",
         "region": regionMock.name},
        {"id": "testId1", "name": "testName1", "namespace": "AWS/EC2",
         "region": regionMock.name},
    ])
    getEC2InstancesMock.assert_call_once_with(regionMock.name)


  @patch("YOMP.app.aws.ec2_utils.getEC2Instances")
  def testGetSuggestedInstancesTwoSameSize(self, getEC2InstancesMock):
    regionMock = Mock(spec="boto.ec2.region.Region")
    regionMock.name = "us-west-2"
    # Instance 1
    instanceMock1 = Mock(spec="boto.ec2.instance.Instance")
    instanceMock1.state = "running"
    instanceMock1.instance_type = "m3.xlarge"
    instanceMock1.launch_time = "2014-05-06T15:17:33.324Z"
    instanceMock1.region = regionMock
    instanceMock1.id = "testId1"
    instanceMock1.tags = {"Name": "testName1"}
    # Instance 2
    instanceMock2 = Mock(spec="boto.ec2.instance.Instance")
    instanceMock2.state = "running"
    instanceMock2.instance_type = "m3.xlarge"
    instanceMock2.launch_time = "2014-05-06T15:18:33.324Z"
    instanceMock2.region = regionMock
    instanceMock2.id = "testId2"
    instanceMock2.tags = {"Name": "testName2"}
    getEC2InstancesMock.return_value = [
        instanceMock1,
        instanceMock2,
    ]

    suggestions = ec2_utils.getSuggestedInstances(regionMock.name)
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [
        {"id": "testId1", "name": "testName1", "namespace": "AWS/EC2",
         "region": regionMock.name},
        {"id": "testId2", "name": "testName2", "namespace": "AWS/EC2",
         "region": regionMock.name},
    ])
    getEC2InstancesMock.assert_call_once_with(regionMock.name)



if __name__ == "__main__":
  unittest.main()
