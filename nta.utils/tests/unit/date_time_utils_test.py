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

"""Unit tests for the date/time utilities"""

from datetime import datetime
import unittest

import pytz

from nta.utils import date_time_utils




class DateTimeUtilsTest(unittest.TestCase):
  """ Unit tests for the date/time utilities """

  def testEpochFromNaiveUTCDatetime(self):
    self.assertEqual(
      date_time_utils.epochFromNaiveUTCDatetime(datetime.utcfromtimestamp(0)),
      0)

    self.assertEqual(
      date_time_utils.epochFromNaiveUTCDatetime(
        datetime.utcfromtimestamp(1426880474.306222)),
      1426880474.306222)

    self.assertEqual(
      date_time_utils.epochFromNaiveUTCDatetime(
        datetime.utcfromtimestamp(1426880474)),
      1426880474)


  def testEpochFromLocalizedDatetime(self):
    localizedZero = (pytz.timezone("UTC")
                     .localize(datetime.utcfromtimestamp(0))
                     .astimezone(pytz.timezone("US/Eastern")))
    self.assertEqual(
      date_time_utils.epochFromLocalizedDatetime(localizedZero),
      0)

    localizedTime = (pytz.timezone("UTC")
                     .localize(datetime.utcfromtimestamp(1426880474.306222))
                     .astimezone(pytz.timezone("US/Eastern")))
    self.assertEqual(
      date_time_utils.epochFromLocalizedDatetime(localizedTime),
      1426880474.306222)

    localizedTime = (pytz.timezone("UTC")
                     .localize(datetime.utcfromtimestamp(1426880474))
                     .astimezone(pytz.timezone("Australia/Melbourne")))
    self.assertEqual(
      date_time_utils.epochFromLocalizedDatetime(localizedTime),
      1426880474)


if __name__ == '__main__':
  unittest.main()
