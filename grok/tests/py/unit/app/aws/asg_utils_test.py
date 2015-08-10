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

"""Tests for ASG utility functions."""

import types
import unittest

from mock import Mock, patch

from YOMP.app.aws import asg_utils



class ASGUtilsTest(unittest.TestCase):


  @patch("YOMP.app.aws.asg_utils.getAutoScalingGroups")
  def testGetSuggestedInstancesNone(self, getAutoScalingGroupsMock):
    getAutoScalingGroupsMock.return_value = []

    suggestions = asg_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getAutoScalingGroupsMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.asg_utils.getAutoScalingGroups")
  def testGetSuggestedInstancesTwoDifferentSize(self, getAutoScalingGroupsMock):
    region = "us-west-2"
    # Instance 1
    instanceMock1 = Mock(spec="boto.ec2.auto_scale.group.AutoScalingGroup")
    instanceMock1.name = "testName1"
    instanceMock1.desired_capacity = 64
    # Instance 2
    instanceMock2 = Mock(spec="boto.ec2.auto_scale.group.AutoScalingGroup")
    instanceMock2.name = "testName2"
    instanceMock2.desired_capacity = 65

    getAutoScalingGroupsMock.return_value = [
        instanceMock1,
        instanceMock2,
    ]

    suggestions = asg_utils.getSuggestedInstances(region)
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [
        {"id": "testName2", "name": "testName2", "namespace": "AWS/AutoScaling",
         "region": region},
        {"id": "testName1", "name": "testName1", "namespace": "AWS/AutoScaling",
         "region": region},
    ])
    getAutoScalingGroupsMock.assert_call_once_with(region)



if __name__ == "__main__":
  unittest.main()
