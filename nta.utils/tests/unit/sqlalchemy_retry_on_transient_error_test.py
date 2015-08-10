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
Unit tests for sqlalchemy transient error handling
"""

import logging
import unittest
from mock import DEFAULT, patch, Mock

import MySQLdb
import sqlalchemy.engine
from sqlalchemy.engine import Engine
import sqlalchemy.exc

from nta.utils.logging_support_raw import LoggingSupport
from nta.utils.sqlalchemy_utils import _ALL_RETRIABLE_ERROR_CODES
from nta.utils.sqlalchemy_utils import retryOnTransientErrors



_LOGGER = logging.getLogger(
  "unit.sqlalchemy_retry_on_transient_error_test")



def setUpModule():
  LoggingSupport.initTestApp()



class TestTransientErrorHandling(unittest.TestCase):

  def _runTransientErrorRetryTest(self, numErrors):

    for errorCode in _ALL_RETRIABLE_ERROR_CODES:
      clientSideEffects = [sqlalchemy.exc.OperationalError(
                            orig=MySQLdb.OperationalError(errorCode),
                            statement="err", params=None)] \
                            * numErrors + [DEFAULT]
      serverSideEffects = [sqlalchemy.exc.InternalError(
                            orig=MySQLdb.InternalError(errorCode),
                            statement="err", params=None)] \
                            * numErrors + [DEFAULT]

      if 3000 > errorCode >= 2000:
        # The error is client side. Return one operationalError, then pass
        with patch.object(Engine,
                          "execute",
                          spec_set=Engine.execute,
                          side_effect=clientSideEffects) \
            as mockExecute:
          retryOnTransientErrors(mockExecute)(Mock())
          self.assertEqual(mockExecute.call_count, numErrors + 1)

      elif errorCode >= 1000:
        # The error is server side. Return one internalError, then pass
        with patch.object(Engine,
                          "execute",
                          spec_set=Engine.execute,
                          side_effect=serverSideEffects) \
            as mockExecute:
          retryOnTransientErrors(mockExecute)(Mock())
          self.assertEqual(mockExecute.call_count, numErrors + 1)

      else:
        self.fail("Error code is neither client nor server: %s" % errorCode)


  def testTransientSingleErrorRetry(self):
    self._runTransientErrorRetryTest(numErrors=1)


  def testTransientMultipleErrorRetry(self):
    self._runTransientErrorRetryTest(numErrors=3)


  def testNonTransientError(self):
    # Pass MySQLdb error constant for CANT_CREATE_TABLE
    errorCode = 1005
    #The error is client side. Return an operationalError
    with patch.object(Engine,
                      "execute",
                      spec_set=Engine.execute,
                      side_effect=[sqlalchemy.exc.OperationalError(
                        orig=MySQLdb.OperationalError(errorCode),
                        statement="err", params=None)])\
        as mockExecute:

      self.assertRaises(sqlalchemy.exc.OperationalError,
                        retryOnTransientErrors(mockExecute))


if __name__ == "__main__":
  unittest.main()
