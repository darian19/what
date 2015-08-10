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

"""Drop metric_template table and add lock table with metric value.

Revision ID: 2f1ee984f978
Revises: 3a7e06671df4
Create Date: 2014-09-25 12:35:09.985034
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# Revision identifiers, used by Alembic. Do not change.
revision = "2f1ee984f978"
down_revision = "3a7e06671df4"



def upgrade():
  """Perform the upgrade."""
  op.create_table(
      "lock",
      sa.Column("name", sa.VARCHAR(length=40), nullable=False),
      sa.PrimaryKeyConstraint("name")
  )
  op.execute("INSERT INTO `lock` (`name`) VALUES('metrics')")
  op.drop_column("metric", "kind")
  op.drop_constraint("metric_to_metric_template_fk", table_name="metric",
                     type_="foreignkey")
  op.drop_index("metric_template_idx", table_name="metric")
  op.drop_column("metric", "metric_template")
  op.drop_table("metric_template")

  # Change tables to use DATETIME column types instead of TIMESTAMP
  op.alter_column("annotation", "timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=False,
                  existing_server_default=sa.text(
                    "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

  op.alter_column("annotation", "created",
                  type_=sa.DATETIME,
                  existing_nullable=False,
                  existing_server_default=sa.text("'0000-00-00 00:00:00'"))

  op.alter_column("instance_status_history", "timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=False,
                  existing_server_default=sa.text("'0000-00-00 00:00:00'"))

  op.alter_column("metric", "last_timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=True,
                  existing_server_default=sa.text("NULL"))

  op.alter_column("metric_data", "timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=False)

  op.alter_column("notification_settings", "last_timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=True,
                  existing_server_default=sa.text("NULL"))

  op.alter_column("notification", "timestamp",
                  type_=sa.DATETIME,
                  existing_nullable=True,
                  existing_server_default=sa.text("NULL"))




def downgrade():
  """Perform the downgrade."""
  raise NotImplementedError("Rollback is not supported.")
