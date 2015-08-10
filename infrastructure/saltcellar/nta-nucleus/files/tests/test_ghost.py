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
Test for GHOST: glibc vulnerability (CVE-2015-0235)
https://access.redhat.com/articles/1332213
"""
import agamotto
import subprocess
import unittest



class TestForGhostVulnerability(unittest.TestCase):

  def testGlibcVulnerableToGhost(self):
    """glibc not vulnerable to CVE-2015-0235 (GHOST)
    """
    # We run this test in an external helper script because if the vulnerability
    # exists, the test I found blows away the calling process and we don't want
    # to miss seeing other test failures.
    try:
      self.assertEquals(subprocess.check_call(
        "/etc/numenta/tests/helpers/ghost-test-helper.py"), 0,
        "glibc vulnerable to ghost!")
    except:
      self.fail("glibc vulnerable to ghost!")


if __name__ == "__main__":
  unittest.main()
