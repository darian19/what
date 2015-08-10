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
Test YOMP AMI. Ensure OpenSSL hack is installed, and that our private
yum repository is not.
"""
import os
import unittest

import agamotto


class TestYOMPAMI(unittest.TestCase):

  def testMySQLCommunityRepoMustBePresent(self):
    """Confirm that the mysql community repo files are on the YOMP AMI."""
    # Check for the GPG key
    self.assertTrue(os.path.exists("/etc/pki/rpm-gpg/RPM-GPG-KEY-mysql"),
                     "mysql community repo must be on YOMP marketplace AMIs")
    # Check for the actual repo file
    self.assertTrue(os.path.exists("/etc/yum.repos.d/mysql-community.repo"),
                     "mysql community repo must be on YOMP marketplace AMIs")

  # TODO: TAUR-759: Re-enable this test after we get the OpenSSL
  # situation sorted out.
  # def testOpenSSLVersion(self):
  #   """Ensure OpenSSL is at 1.0.1h"""
  #   self.assertTrue(agamotto.process.stdoutContains("openssl version",
  #                   "OpenSSL 1.0.1h"),
  #                   "Bad OpenSSL version - should be 1.0.1h")


  def testSecretsauceRepoMustBeAbsent(self):
    """Confirm that the secretsauce repo file is not on the YOMP AMI."""
    self.assertFalse(os.path.exists('/etc/yum.repos.d/secretsauce.repo'),
                     "secretsauce repo must never be on marketplace AMIs")


if __name__ == '__main__':
  unittest.main()
