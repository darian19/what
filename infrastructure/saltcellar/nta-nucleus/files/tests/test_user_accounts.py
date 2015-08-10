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
Test for insecure user accounts
"""
import agamotto
import unittest



class TestUserAccounts(unittest.TestCase):

  def testNoAccountsHaveEmptyPasswords(self):
    """No blank passwords in /etc/shadow

       /etc/shadow has : separated fields. Check the password field ($2) and
       make sure no accounts have a blank password.
    """
    self.assertEquals(agamotto.process.execute(
      'sudo awk -F: \'($2 == "") {print}\' /etc/shadow | wc -l').strip(), '0',
      "found accounts with blank password")


  def testRootIsTheOnlyUidZeroAccount(self):
    """root is only UID 0 account in /etc/passwd

       /etc/passwd stores the UID in field 3. Make sure only one account entry
       has uid 0.
    """
    self.assertEquals(agamotto.process.execute(
                      'awk -F: \'($3 == "0") {print}\' /etc/passwd').strip(),
                      'root:x:0:0:root:/root:/bin/bash')



if __name__ == '__main__':
  unittest.main()
