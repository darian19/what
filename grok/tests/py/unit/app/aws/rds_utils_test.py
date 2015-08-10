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

"""Tests for RDS utility functions."""

import types
import unittest

from mock import Mock, patch

from YOMP.app.aws import rds_utils



class RDSUtilsTest(unittest.TestCase):


  @patch("YOMP.app.aws.rds_utils.getRDSInstances")
  def testGetSuggestedInstancesNone(self, getRDSInstancesMock):
    getRDSInstancesMock.return_value = []

    suggestions = rds_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getRDSInstancesMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.rds_utils.getRDSInstances")
  def testGetSuggestedInstancesNoAvailable(self, getRDSInstancesMock):
    instanceMock1 = Mock(spec="boto.rds.dbinstance.DBInstance")
    instanceMock1.status = "not-available"
    getRDSInstancesMock.return_value = [
        instanceMock1,
    ]

    suggestions = rds_utils.getSuggestedInstances("dummy-region")
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [])
    getRDSInstancesMock.assert_call_once_with("dummy-region")


  @patch("YOMP.app.aws.rds_utils.getRDSInstances")
  def testGetSuggestedInstancesTwoDifferentSize(self, getRDSInstancesMock):
    region = "us-west-2"
    # Instance 1
    instanceMock1 = Mock(spec="boto.rds.dbinstance.DBInstance")
    instanceMock1.status = "available"
    instanceMock1.allocated_storage = 64.0
    instanceMock1.id = "testId1"
    # Instance 2
    instanceMock2 = Mock(spec="boto.rds.dbinstance.DBInstance")
    instanceMock2.status = "available"
    instanceMock2.allocated_storage = 65.0
    instanceMock2.id = "testId2"

    getRDSInstancesMock.return_value = [
        instanceMock1,
        instanceMock2,
    ]

    suggestions = rds_utils.getSuggestedInstances(region)
    self.assertIsInstance(suggestions, types.GeneratorType)
    suggestions = list(suggestions)

    self.assertSequenceEqual(suggestions, [
        {"id": "testId2", "name": "testId2", "namespace": "AWS/RDS",
         "region": region},
        {"id": "testId1", "name": "testId1", "namespace": "AWS/RDS",
         "region": region},
    ])
    getRDSInstancesMock.assert_call_once_with(region)



if __name__ == "__main__":
  unittest.main()
