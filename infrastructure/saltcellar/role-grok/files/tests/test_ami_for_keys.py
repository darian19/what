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
Ensure no pem or pub files have crept into the AMI.
"""
import agamotto
import unittest
from agamotto.process import execute

class TestYOMPAMI(unittest.TestCase):

  def testNoNewPemFilesInSalt(self):
    """
    Pem files are forbidden in Marketplace AMIs.
    """
    saltRoot = "/srv/salt"
    # Make sure no pem files creep into AMIs either
    self.assertEquals(execute("sudo find %s -name '*.pem' -print 2>&1 | \
      grep -v 'No such file or directory' | \
      wc -l " % saltRoot).strip(), '0',
      "Found .pem file in %s directory tree!" % saltRoot)


  def testNoNewSSHPubkeysInSalt(self):
    """
    Make sure pubkeys don't slip in in new formulas we add to our salt
    configuration or we'll fail the marketplace acceptance tests.
    """
    saltRoot = "/srv/salt"
    # Make sure no new pubkeys creep into AMIs
    self.assertEquals(execute("""sudo find %s -name '*.pub' -print 2>&1 | \
                                 grep -v 'No such file or directory' | \
                                 wc -l""" % saltRoot).strip(), '0',
      "Found .pub file in %s directory tree!" % saltRoot
    )



if __name__ == '__main__':
  unittest.main()
