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
AMI unit tests for mysql support
"""
import agamotto
import unittest

from YOMP.app import repository



class TestMysqlInstallation(unittest.TestCase):

  def testMysqlUserExists(self):
    self.assertTrue(agamotto.user.exists('mysql'))


  def testMysqlInstalled(self):
    self.assertTrue(agamotto.package.installed('mysql-community-client'))
    self.assertTrue(agamotto.package.installed('mysql-community-common'))
    self.assertTrue(agamotto.package.installed('mysql-community-devel'))
    self.assertTrue(agamotto.package.installed('mysql-community-libs'))
    self.assertTrue(agamotto.package.installed('mysql-community-server'))


  def testMysqlConfigurationFilePresent(self):
    self.assertTrue(agamotto.file.exists('/etc/my.cnf'))

    # TODO: re-write after we decide how to deal with mysql customizations
    # on 5.6
    # self.assertTrue(agamotto.file.exists('/etc/mysql/conf.d/YOMP-my.cnf'))


  def testMysqlIsRunning(self):
    self.assertTrue(agamotto.process.running('/bin/sh /usr/bin/mysqld_safe'))


  def testMysqlInitScript(self):
    self.assertTrue(agamotto.file.exists('/etc/init.d/mysqld'))


  def testTablesCreatedWithInnoDBEngine(self):
    """
    Tests to make sure that all of the tables in the YOMP table_schema were
    created using the InnoDB engine to preserve referential integrity.

    At this time, it is checking all tables in the DB; in the future, if we do
    not require referential integrity, we can explicitly whitelist specific
    tables to allow those to use `MyISAM` or another engine.
    """
    engine = repository.engineFactory()
    result = engine.execute("SELECT table_name, engine "
                            "FROM information_schema.tables "
                            "WHERE table_schema = 'YOMP'")

    for row in result:
      self.assertEqual(row.engine, "InnoDB",
        ("Table %s was created with the wrong engine type" % row["table_name"]))



if __name__ == '__main__':
  unittest.main()
