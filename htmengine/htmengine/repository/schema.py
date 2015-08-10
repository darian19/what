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

"""SQLAlchemy table definitions."""

from sqlalchemy import (Column,
                        DATETIME,
                        ForeignKey,
                        Index,
                        INTEGER,
                        MetaData,
                        Table,
                        TEXT,
                        VARCHAR)
from sqlalchemy.dialects.mysql import DOUBLE



metadata = MetaData()



instance_status_history = Table(  # pylint: disable=C0103
                                "instance_status_history",
                                metadata,
                                Column("server",
                                       VARCHAR(length=100),
                                       primary_key=True,
                                       nullable=False,
                                       server_default=""),
                                Column("timestamp",
                                       DATETIME(),
                                       primary_key=True,
                                       nullable=False,
                                       server_default="0000-00-00 00:00:00"),
                                Column("status",
                                       VARCHAR(length=32),
                                       nullable=False,
                                       server_default=""),
                                schema=None)



metric = Table("metric",
               metadata,
               Column("uid",
                      VARCHAR(length=40),
                      primary_key=True,
                      nullable=False),
               Column("datasource",
                      VARCHAR(length=100)),
               Column("name",
                      VARCHAR(length=255)),
               Column("description",
                      VARCHAR(length=200)),
               Column("server",
                      VARCHAR(length=100)),
               Column("location",
                      VARCHAR(length=200)),
               Column("parameters",
                      TEXT()),
               Column("status",
                      INTEGER(),
                      autoincrement=False,
                      server_default="0"),
               Column("message",
                      TEXT()),
               Column("collector_error",
                      TEXT()),
               Column("last_timestamp",
                      DATETIME()),
               Column("poll_interval",
                      INTEGER(),
                      autoincrement=False,
                      server_default="60"),
               Column("tag_name",
                      VARCHAR(length=200)),
               Column("model_params",
                      TEXT()),
               Column("last_rowid",
                      INTEGER(),
                      autoincrement=False),
               schema=None)

Index("datasource_idx", metric.c.datasource)
Index("location_idx", metric.c.location)
Index("server_idx", metric.c.server)



metric_data = Table(  # pylint: disable=C0103
    "metric_data",
    metadata,
    Column("uid",
           VARCHAR(length=40),
           ForeignKey(metric.c.uid, name="metric_data_to_metric_fk",
                      onupdate="CASCADE", ondelete="CASCADE"),
           primary_key=True,
           nullable=False,
           server_default=""),
    Column("rowid",
           INTEGER(),
           primary_key=True,
           autoincrement=False,
           nullable=False,
           server_default="0"),
    Column("timestamp",
           DATETIME(),
           nullable=False),
    Column("metric_value",
           DOUBLE(asdecimal=False),
           nullable=False),
    Column("raw_anomaly_score",
           DOUBLE(asdecimal=False)),
    Column("anomaly_score",
           DOUBLE(asdecimal=False)),
    Column("display_value",
           INTEGER(),
           autoincrement=False),
    schema=None,
)

Index("timestamp_idx", metric_data.c.timestamp)
Index("anomaly_score_idx", metric_data.c.anomaly_score)



lock = Table("lock",
             metadata,
             Column("name",
                    VARCHAR(length=40),
                    primary_key=True,
                    nullable=False),
             schema=None)
