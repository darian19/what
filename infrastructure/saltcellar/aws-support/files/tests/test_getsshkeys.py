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
Ensure the AMI has getsshkeys enabled so that it can write the key passed
to the instance by EC2 into the appropriate authorized_keys files.

If getsshkeys is missing, users won't be able to ssh into instances created
from the AMI.
"""
import agamotto
import unittest
from agamotto.process import execute


class TestGetSSHKeys(unittest.TestCase):

  def testGetSSHKeysEnabled(self):
    """
    getsshkeys loads the ssh key specified during instance launch in AWS.
    Ensure it is enabled or sshing into the instance will be impossible
    """
    self.assertTrue(agamotto.service.enabled("getsshkeys"))



if __name__ == "__main__":
  unittest.main()
