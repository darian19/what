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

"""Tests for ELB utility functions."""

import types
import unittest

from mock import Mock, patch

from YOMP.app.aws import elb_utils



class ELBUtilsTest(unittest.TestCase):


  @patch("YOMP.app.aws.elb_utils.getELBInstances")
  def testGetSuggestedInstancesNone(self, getELBInstancesMock):
    getELBInstancesMock.return_value = []

    suggestions = elb_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getELBInstancesMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.elb_utils.getELBInstances")
  def testGetSuggestedInstancesTwoDifferentSize(self, getELBInstancesMock):
    region = "us-west-2"
    # Instance 1
    instanceMock1 = Mock(spec="boto.ec2.elb.load_balancer.LoadBalancer")
    instanceMock1.name = "testName1"
    instanceMock1.instances = ["a", "b"]
    # Instance 2
    instanceMock2 = Mock(spec="boto.ec2.elb.load_balancer.LoadBalancer")
    instanceMock2.name = "testName2"
    instanceMock2.instances = ["c", "d", "e"]

    getELBInstancesMock.return_value = [
        instanceMock1,
        instanceMock2,
    ]

    suggestions = elb_utils.getSuggestedInstances(region)
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [
        {"id": "testName2", "name": "testName2", "namespace": "AWS/ELB",
         "region": region},
        {"id": "testName1", "name": "testName1", "namespace": "AWS/ELB",
         "region": region},
    ])
    getELBInstancesMock.assert_call_once_with(region)



if __name__ == "__main__":
  unittest.main()
