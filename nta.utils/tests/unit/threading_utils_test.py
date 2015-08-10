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

"""Unit tests for the threading utilities"""


import unittest


from nta.utils import threading_utils



class ThreadingUtilsTest(unittest.TestCase):
  """ Unit tests for the threading utilities """

  def testThreadsafeCounterConstructor(self):
    """ Test ThreadsafeCounter constructor """

    # Test with default args
    counter = threading_utils.ThreadsafeCounter()
    self.assertEqual(counter.value, 0)

    # Test with explicit initial value
    counter = threading_utils.ThreadsafeCounter(999)
    self.assertEqual(counter.value, 999)


  def testThreadsafeCounterContextManager(self):
    """ Test ThreadsafeCounter context manager """

    counter = threading_utils.ThreadsafeCounter(10)
    with counter as currentValue1:
      self.assertEqual(currentValue1, 11)
      # We get away with it because in this test there is no true concurrency
      self.assertEqual(counter.value, 11)

      # Test reentrancy
      with counter as currentValue2:
        self.assertEqual(currentValue2, 12)
        self.assertEqual(counter.value, 12)

      self.assertEqual(counter.value, 11)

    self.assertEqual(counter.value, 10)


  def testThreadsafeCounterAdjust(self):
    """ test ThreadsafeCounter.adjust() """

    counter = threading_utils.ThreadsafeCounter(1)

    self.assertEqual(counter.value, 1)

    self.assertEqual(counter.adjust(7), 8)
    self.assertEqual(counter.value, 8)

    self.assertEqual(counter.adjust(-3), 5)
    self.assertEqual(counter.value, 5)

    # Test combination of context manager and adjust
    with counter as currentValue:
      self.assertEqual(currentValue, 6)
      self.assertEqual(counter.value, 6)

      self.assertEqual(counter.adjust(-6), 0)
      self.assertEqual(counter.value, 0)

    self.assertEqual(counter.value, -1)



if __name__ == '__main__':
  unittest.main()
