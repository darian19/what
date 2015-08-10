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

import unittest2 as unittest

from mock import DEFAULT, Mock, patch
import MySQLdb
import sqlalchemy
from sqlalchemy.engine import Engine
import sqlalchemy.exc

from nta.utils.sqlalchemy_utils import _ALL_RETRIABLE_ERROR_CODES

from taurus.metric_collectors import collectorsdb, logging_support
from taurus.metric_collectors.collectorsdb import retryOnTransientErrors



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



@patch("taurus.metric_collectors.collectorsdb.sqlalchemy", autospec=True)
class CollectorsdbTestCase(unittest.TestCase):
  def testEngineFactorySingletonPattern(self, sqlalchemyMock):

    # Explicitly spec out sqlalchemy.create_engine()
    firstCall = Mock(spec_set=sqlalchemy.engine.base.Engine)
    secondCall = Mock(spec_set=sqlalchemy.engine.base.Engine)
    sqlalchemyMock.create_engine.side_effect = iter([firstCall, secondCall])

    # Call collectorsdb.engineFactory()
    engine = collectorsdb.engineFactory()
    self.assertIs(engine, firstCall)

    # Call collectorsdb.engineFactory() again and assert singleton
    engine2 = collectorsdb.engineFactory()
    self.assertIs(engine2, firstCall)
    self.assertEqual(sqlalchemyMock.create_engine.call_count, 1)

    # Call collectorsdb.engineFactory() in different process, assert new
    # instance
    with patch("taurus.metric_collectors.collectorsdb.os",
               autospec=True) as osMock:
      osMock.getpid.return_value = collectorsdb._EngineSingleton._pid + 1
      engine3 = collectorsdb.engineFactory()
      self.assertTrue(engine.dispose.called)
      self.assertIs(engine3, secondCall)



if __name__ == "__main__":
  unittest.main()
