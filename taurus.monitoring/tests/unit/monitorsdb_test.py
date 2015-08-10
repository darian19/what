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

from taurus.monitoring import monitorsdb, logging_support
from taurus.monitoring.monitorsdb import retryOnTransientErrors



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



@patch("taurus.monitors.monitorsdb.sqlalchemy", autospec=True)
class MonitorsdbTestCase(unittest.TestCase):
  def testEngineFactorySingletonPattern(self, sqlalchemyMock):

    # Explicitly spec out sqlalchemy.create_engine()
    firstCall = Mock(spec_set=sqlalchemy.engine.base.Engine)
    secondCall = Mock(spec_set=sqlalchemy.engine.base.Engine)
    sqlalchemyMock.create_engine.side_effect = iter([firstCall, secondCall])

    # Call monitorsdb.engineFactory()
    engine = monitorsdb.engineFactory()
    self.assertIs(engine, firstCall)

    # Call monitorsdb.engineFactory() again and assert singleton
    engine2 = monitorsdb.engineFactory()
    self.assertIs(engine2, firstCall)
    self.assertEqual(sqlalchemyMock.create_engine.call_count, 1)

    # Call monitorsdb.engineFactory() in different process, assert new
    # instance
    with patch("taurus.monitors.monitorsdb.os", autospec=True) as osMock:
      osMock.getpid.return_value = monitorsdb._EngineSingleton._pid + 1
      engine3 = monitorsdb.engineFactory()
      self.assertTrue(engine.dispose.called)
      self.assertIs(engine3, secondCall)



if __name__ == "__main__":
  unittest.main()
