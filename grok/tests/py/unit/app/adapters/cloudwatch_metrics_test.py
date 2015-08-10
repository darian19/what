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

"""
Tests to ensure that only approved metrics have a max setting and
that all metrics have a correct min value. All metrics also need to have
a period of '300' seconds.
"""

import unittest
from nupic.support.unittesthelpers.testcasebase import TestCaseBase
from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
  AWSResourceAdapterBase)

class CloudwatchMetricsTest(TestCaseBase):



  def testMinCorrect(self):
    """
    Currently the YOMP algorithm code assumes that all metrics have a min that
    is >= 0. Let's ensure that.
    """

    for adapter in AWSResourceAdapterBase._metricRegistry.values():
      self.assertTrue(hasattr(adapter["adapter"], "MIN"))
      self.assertGreaterEqual(adapter["adapter"].MIN, 0)



  def testPeriodCorrect(self):
    """
    Test that all metrics have a period of 300 seconds. Currently we are
    enforcing this in YOMP.
    """
    for adapter in AWSResourceAdapterBase._metricRegistry.values():
      self.assertTrue(hasattr(adapter["adapter"], "METRIC_PERIOD"))
      self.assertEqual(adapter["adapter"].METRIC_PERIOD, 300)



if __name__ == '__main__':
  unittest.main()

