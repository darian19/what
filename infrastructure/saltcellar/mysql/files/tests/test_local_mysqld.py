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
mysql.server tests for local MySQLd
"""

import unittest

import agamotto
from agamotto.file import isExecutable, isFile
from agamotto.process import running



class TestLocalMySQLdInstallation(unittest.TestCase):

  def testLocalMySQLdEnabled(self):
    """MySQLd service is enabled"""
    self.assertTrue(agamotto.service.enabled("mysqld"),
                    "mysqld is not configured to start at boot")


  def testLocalMySQLdInitScript(self):
    """mysqld server init script is present and executable"""
    self.assertTrue(isFile("/etc/init.d/mysqld"),
                    "mysqld init script is missing")
    self.assertTrue(isExecutable("/etc/init.d/mysqld"),
                    "mysqld init script is not executable")


  def testLocalMySQLdIsRunning(self):
    """MySQLd service is running"""
    self.assertTrue(running("mysqld --basedir=/usr --datadir=/var/lib/mysql"))



if __name__ == "__main__":
  unittest.main()
