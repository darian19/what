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

""" Common SQLAlchemy table definitions for monitoring scripts. """

from sqlalchemy import (BOOLEAN,
                        Column,
                        DATETIME,
                        func,
                        INTEGER,
                        MetaData,
                        PrimaryKeyConstraint,
                        Table)

from sqlalchemy.dialects import mysql


_MAX_MONITOR_ISSUES_ID_LEN = 40
MYSQL_CHARSET = "utf8"
MYSQL_COLLATE = MYSQL_CHARSET + "_unicode_ci"



metadata = MetaData()



def _createMonitorErrorFlagsSchema(schemaName, metadata):
  schema = Table(
    schemaName,
    metadata,

    # Issue UID
    Column("uid",
           mysql.VARCHAR(length=_MAX_MONITOR_ISSUES_ID_LEN),
           primary_key=True,
           nullable=False),

    PrimaryKeyConstraint("uid",
                         name=schemaName + "_pk"),

    # Issue name
    Column("name",
           mysql.VARCHAR(length=_MAX_MONITOR_ISSUES_ID_LEN),
           nullable=False),

    # Should report issue flag
    Column("should_report",
           BOOLEAN(),
           nullable=False),

    # Datetime of last issue occurrence
    Column("last_occurrence",
           DATETIME(),
           nullable=False,
           server_default=func.current_timestamp()),

    # Count of issue occurrences
    Column("occurrence_count",
           INTEGER,
           nullable=True,
           autoincrement=True),

    mysql_CHARSET=MYSQL_CHARSET,
    mysql_COLLATE=MYSQL_COLLATE,
  )
  return schema



# Error flag schema for Taurus models monitor
modelsMonitorErrorFlags = _createMonitorErrorFlagsSchema(
  "models_monitor_error_flags", metadata)



# Error flag schema for Taurus metric-order monitor
metricOrderMonitorErrorFlags = _createMonitorErrorFlagsSchema(
  "metric_order_monitor_error_flags", metadata)
