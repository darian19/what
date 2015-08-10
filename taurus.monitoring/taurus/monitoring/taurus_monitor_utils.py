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
import logging

from taurus.monitoring import monitorsdb
from taurus.monitoring.monitorsdb import schema



g_logger = logging.getLogger("taurus_monitor_utils")



@monitorsdb.retryOnTransientErrors
def containsErrorFlag(table, uid):
  """
  Checks whether issue(s) with specified uid is(are) present in
  specified table.

  :param table: A database table
  :type table: sqlalchemy.schema.Table
  :param uid: a unique issue id
  :type uid: string
  :returns: True is there exist any row(s) in the table having specified uid,
            False otherwise
  :rtype: Boolean
  """
  sel = table.select().where(table.c.uid == uid)
  issues = monitorsdb.engineFactory().execute(sel).fetchall()
  return len(issues) > 0



@monitorsdb.retryOnTransientErrors
def addErrorFlag(table, uid, name):
  """
  Adds issue to table.

  :param table: A database table
  :type table: sqlalchemy.schema.Table
  :param uid: a unique issue id
  :type uid: string
  :param name: name of issue
  :type name: string
  """
  ins = table.insert().prefix_with("IGNORE", dialect="mysql").values(
    uid=uid,
    name=name,
    should_report=False)
  monitorsdb.engineFactory().execute(ins)
  g_logger.debug("Added new issue flag for %s", name)



@monitorsdb.retryOnTransientErrors
def removeErrorFlag(table, uid):
  """
  Removes issue with uid from table.

  :param table: A database table
  :type table: sqlalchemy.schema.Table
  :param uid: a unique issue id
  :type uid: string
  """
  cmd = table.delete().where(table.c.uid == uid)
  result = monitorsdb.engineFactory().execute(cmd)
  if result.rowcount > 0:
    g_logger.debug("Removed issue flag: %s", uid)
