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

import os

from nta.utils.config import Config

from htmengine.repository import getUnaffiliatedEngine

from migrate import migrate



def reset():
  """
  Reset the htmengine database; upon successful completion, the necessary schema
  are created, but the tables are not populated
  """
  # Make sure we have the latest version of configuration
  config = Config("application.conf",
                  os.environ.get("APPLICATION_CONFIG_PATH"))
  dbName = config.get("repository", "db")

  resetDatabaseSQL = (
      "DROP DATABASE IF EXISTS %(database)s; "
      "CREATE DATABASE %(database)s;" % {"database": dbName})
  statements = resetDatabaseSQL.split(";")

  engine = getUnaffiliatedEngine(config)
  with engine.connect() as connection:
    for s in statements:
      if s.strip():
        connection.execute(s)

  migrate()



if __name__ == "__main__":
  reset()
