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

"""Create initial tables.

Revision ID: 3a7e06671df4
Revises: None
Create Date: 2014-09-25 12:18:06.364214
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# Revision identifiers, used by Alembic. Do not change.
revision = "3a7e06671df4"
down_revision = None



def upgrade():
  """Create initial tables from scratch."""
  op.create_table(
      "notification_settings",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("windowsize", sa.INTEGER(), server_default="1",
                autoincrement=False, nullable=True),
      sa.Column("sensitivity", sa.FLOAT(), server_default="0.99999",
                nullable=True),
      sa.Column("email_addr", sa.VARCHAR(length=255), nullable=False),
      sa.Column("last_timestamp", sa.TIMESTAMP(), nullable=True),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_table(
      "metric_template",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("name", sa.VARCHAR(length=255), nullable=True),
      sa.Column("description", sa.VARCHAR(length=200), nullable=True),
      sa.Column("server", sa.VARCHAR(length=100), nullable=True),
      sa.Column("location", sa.VARCHAR(length=200), nullable=True),
      sa.Column("datasource", sa.VARCHAR(length=100), nullable=True),
      sa.Column("query", sa.TEXT(), nullable=True),
      sa.Column("parameters", sa.TEXT(), nullable=True),
      sa.Column("period", sa.INTEGER(), server_default="60", nullable=True),
      sa.Column("notificationUnit", sa.VARCHAR(length=100), nullable=True),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_table(
      "instance_status_history",
      sa.Column("server", sa.VARCHAR(length=100), server_default="",
                nullable=False),
      sa.Column("timestamp", sa.TIMESTAMP(),
                server_default="0000-00-00 00:00:00", nullable=False),
      sa.Column("status", sa.VARCHAR(length=32), server_default="",
                nullable=False),
      sa.PrimaryKeyConstraint("server", "timestamp")
  )
  op.create_table(
      "autostack",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("name", sa.VARCHAR(length=255), nullable=False),
      sa.Column("region", sa.VARCHAR(length=14), nullable=False),
      sa.Column("filters", sa.BLOB(), nullable=True),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_index("name_region", "autostack", ["name", "region"], unique=True)
  op.create_table(
      "annotation",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("timestamp", sa.TIMESTAMP(), nullable=False),
      sa.Column("created", sa.TIMESTAMP(), nullable=False),
      sa.Column("device", sa.VARCHAR(length=40), nullable=True),
      sa.Column("user", sa.VARCHAR(length=100), nullable=True),
      sa.Column("server", sa.VARCHAR(length=100), nullable=True),
      sa.Column("message", sa.TEXT(), nullable=True),
      sa.Column("data", sa.TEXT(), nullable=True),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_index("device_idx", "annotation", ["device"], unique=False)
  op.create_index("server_idx", "annotation", ["server"], unique=False)
  op.create_index("timestamp_idx", "annotation", ["timestamp"], unique=False)
  op.create_index("user_idx", "annotation", ["user"], unique=False)
  op.create_table(
      "metric",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("datasource", sa.VARCHAR(length=100), nullable=True),
      sa.Column("name", sa.VARCHAR(length=255), nullable=True),
      sa.Column("description", sa.VARCHAR(length=200), nullable=True),
      sa.Column("server", sa.VARCHAR(length=100), nullable=True),
      sa.Column("location", sa.VARCHAR(length=200), nullable=True),
      sa.Column("parameters", sa.TEXT(), nullable=True),
      sa.Column("status", sa.INTEGER(), server_default="0", autoincrement=False,
                nullable=True),
      sa.Column("message", sa.TEXT(), nullable=True),
      sa.Column("collector_error", sa.TEXT(), nullable=True),
      sa.Column("last_timestamp", sa.TIMESTAMP(), nullable=True),
      sa.Column("poll_interval", sa.INTEGER(), server_default="60",
                autoincrement=False, nullable=True),
      sa.Column("metric_template", sa.VARCHAR(length=40), nullable=True),
      sa.Column("tag_name", sa.VARCHAR(length=200), nullable=True),
      sa.Column("model_params", sa.TEXT(), nullable=True),
      sa.Column("last_rowid", sa.INTEGER(), autoincrement=False, nullable=True),
      sa.Column("kind", mysql.ENUM("standalone", "autostack"), nullable=False),
      sa.ForeignKeyConstraint(["metric_template"], [u"metric_template.uid"],
                              name="metric_to_metric_template_fk",
                              onupdate="CASCADE", ondelete="CASCADE"),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_index("datasource_idx", "metric", ["datasource"], unique=False)
  op.create_index("location_idx", "metric", ["location"], unique=False)
  op.create_index("metric_template_idx", "metric", ["metric_template"],
                  unique=False)
  op.create_index("server_idx", "metric", ["server"], unique=False)
  op.create_table(
      "notification",
      sa.Column("uid", sa.VARCHAR(length=40), nullable=False),
      sa.Column("metric", sa.VARCHAR(length=40), nullable=True),
      sa.Column("rowid", sa.INTEGER(), autoincrement=False, nullable=False),
      sa.Column("device", sa.VARCHAR(length=40), nullable=True),
      sa.Column("windowsize", sa.INTEGER(), server_default="1",
                autoincrement=False, nullable=True),
      sa.Column("timestamp", sa.TIMESTAMP(), nullable=True),
      sa.Column("acknowledged", mysql.TINYINT(), nullable=True),
      sa.Column("seen", mysql.TINYINT(), nullable=True),
      sa.Column("ses_message_id", sa.VARCHAR(length=100), nullable=True),
      sa.ForeignKeyConstraint(["device"], [u"notification_settings.uid"],
                              name="notification_to_notification_settings_fk",
                              onupdate="CASCADE", ondelete="CASCADE"),
      sa.ForeignKeyConstraint(["metric"], [u"metric.uid"],
                              name="notification_to_metric_fk",
                              onupdate="CASCADE", ondelete="CASCADE"),
      sa.PrimaryKeyConstraint("uid")
  )
  op.create_index("metric_rowid", "notification", ["metric", "rowid", "device"],
                  unique=True)
  op.create_table(
      "metric_set",
      sa.Column("metric", sa.VARCHAR(length=40), nullable=False),
      sa.Column("autostack", sa.VARCHAR(length=40), nullable=False),
      sa.ForeignKeyConstraint(["autostack"], [u"autostack.uid"],
                              name="metric_set_to_autostack_fk",
                              onupdate="CASCADE", ondelete="CASCADE"),
      sa.ForeignKeyConstraint(["metric"], [u"metric.uid"],
                              name="metric_set_to_metric_fk",
                              onupdate="CASCADE", ondelete="CASCADE")
  )
  op.create_table(
      "metric_data",
      sa.Column("uid", sa.VARCHAR(length=40), server_default="",
                nullable=False),
      sa.Column("rowid", sa.INTEGER(), server_default="0", autoincrement=False,
                nullable=False),
      sa.Column("timestamp", sa.TIMESTAMP(),
                server_default=sa.func.current_timestamp(), nullable=False),
      sa.Column("metric_value", mysql.DOUBLE(), nullable=False),
      sa.Column("raw_anomaly_score", mysql.DOUBLE(), nullable=True),
      sa.Column("anomaly_score", mysql.DOUBLE(), nullable=True),
      sa.Column("display_value", sa.INTEGER(), autoincrement=False,
                nullable=True),
      sa.ForeignKeyConstraint(["uid"], [u"metric.uid"],
                              name="metric_data_to_metric_fk",
                              onupdate="CASCADE", ondelete="CASCADE"),
      sa.PrimaryKeyConstraint("uid", "rowid")
  )
  op.create_index("anomaly_score_idx", "metric_data", ["anomaly_score"],
                  unique=False)
  op.create_index("timestamp_idx", "metric_data", ["timestamp"], unique=False)



def downgrade():
  """Revert back to empty database."""
  op.drop_index("timestamp_idx", table_name="metric_data")
  op.drop_index("anomaly_score_idx", table_name="metric_data")
  op.drop_table("metric_data")
  op.drop_table("metric_set")
  op.drop_index("metric_rowid", table_name="notification")
  op.drop_table("notification")
  op.drop_index("server_idx", table_name="metric")
  op.drop_index("metric_template_idx", table_name="metric")
  op.drop_index("location_idx", table_name="metric")
  op.drop_index("datasource_idx", table_name="metric")
  op.drop_table("metric")
  op.drop_index("user_idx", table_name="annotation")
  op.drop_index("timestamp_idx", table_name="annotation")
  op.drop_index("server_idx", table_name="annotation")
  op.drop_index("device_idx", table_name="annotation")
  op.drop_table("annotation")
  op.drop_index("name_region", table_name="autostack")
  op.drop_table("autostack")
  op.drop_table("instance_status_history")
  op.drop_table("metric_template")
  op.drop_table("notification_settings")
