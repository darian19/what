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

from sqlalchemy import (BLOB,
                        Column,
                        DATETIME,
                        FLOAT,
                        ForeignKey,
                        Index,
                        INTEGER,
                        Table,
                        TEXT,
                        VARCHAR)
from sqlalchemy.dialects.mysql import TINYINT

# We use several of these in downstream functions, so disable W0611
#pylint: disable=W0611
from htmengine.repository.schema import (instance_status_history,
                                         lock,
                                         metadata,
                                         metric,
                                         metric_data)
#pylint: enable=W0611


annotation = Table("annotation",
                   metadata,
                   Column("uid",
                          VARCHAR(length=40),
                          primary_key=True,
                          nullable=False),
                   Column("timestamp",
                          DATETIME(),
                          nullable=False),
                   Column("created",
                          DATETIME(),
                          nullable=False),
                   Column("device",
                          VARCHAR(length=40),
                          nullable=True),
                   Column("user",
                          VARCHAR(length=100),
                         nullable=True),
                   Column("server",
                          VARCHAR(length=100),
                          nullable=True),
                   Column("message",
                          TEXT()),
                   Column("data",
                          TEXT()),
                   schema=None)

Index("timestamp_idx", annotation.c.timestamp)
Index("device_idx", annotation.c.device)
Index("server_idx", annotation.c.server)
Index("user_idx", annotation.c.user)



autostack = Table("autostack",
                  metadata,
                  Column("uid",
                         VARCHAR(length=40),
                         primary_key=True,
                         nullable=False),
                  Column("name",
                         VARCHAR(length=255),
                         nullable=False),
                  Column("region",
                         VARCHAR(length=14),
                         nullable=False),
                  Column("filters",
                         BLOB()),
                  schema=None)

Index("name_region", autostack.c.name, autostack.c.region, unique=True)




metric_set = Table(  # pylint: disable=C0103
                   "metric_set",
                   metadata,
                   Column("metric",
                          VARCHAR(length=40),
                          ForeignKey(metric.c.uid,
                                     name="metric_set_to_metric_fk",
                                     onupdate="CASCADE", ondelete="CASCADE"),
                          nullable=False),
                   Column("autostack",
                          VARCHAR(length=40),
                          ForeignKey(autostack.c.uid,
                                     name="metric_set_to_autostack_fk",
                                     onupdate="CASCADE", ondelete="CASCADE"),
                          nullable=False),
                   schema=None)



notification_settings = Table(  # pylint: disable=C0103
                              "notification_settings",
                              metadata,
                              Column("uid",
                                     VARCHAR(length=40),
                                     primary_key=True,
                                     nullable=False),
                              Column("windowsize",
                                     INTEGER(),
                                     autoincrement=False,
                                     server_default="1"),
                              Column("sensitivity",
                                     FLOAT(),
                                     server_default="0.99999"),
                              Column("email_addr",
                                     VARCHAR(length=255),
                                     nullable=False),
                              Column("last_timestamp",
                                     DATETIME()),
                              schema=None)



notification = Table(
    "notification",
    metadata,
    Column("uid",
           VARCHAR(length=40),
           primary_key=True,
           nullable=False),
    Column("metric",
           VARCHAR(length=40),
           ForeignKey(metric.c.uid, name="notification_to_metric_fk",
                      onupdate="CASCADE", ondelete="CASCADE")),
    Column("rowid",
           INTEGER(),
           nullable=False,
           autoincrement=False),
    Column("device",
           VARCHAR(length=40),
           ForeignKey(notification_settings.c.uid,
                      name="notification_to_notification_settings_fk",
                      onupdate="CASCADE", ondelete="CASCADE")),
    Column("windowsize",
           INTEGER(),
           autoincrement=False,
           server_default="1"),
    Column("timestamp",
           DATETIME()),
    Column("acknowledged",
           TINYINT()),
    Column("seen",
           TINYINT()),
    Column("ses_message_id",
           VARCHAR(length=100)),
    schema=None)

Index("metric_rowid", notification.c.metric, notification.c.rowid,
      notification.c.device, unique=True)
