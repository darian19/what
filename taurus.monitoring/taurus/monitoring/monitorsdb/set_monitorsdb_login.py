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
Applies the given mysql login information as overrides for
taurus-monitors-sqldb.conf.

NOTE: this script may be configured as "console script" by the package
installer.
"""

import logging
from optparse import OptionParser

from nta.utils.config import Config

from taurus.monitoring import monitorsdb, logging_support



g_log = logging.getLogger("set_monitorsdb_login")



def _parseArgs():
  """
  :returns: dict of arg names and values:
    host - mysql hostname or IP address (required, non-empty)
    user - mysql user name (required, non-empty)
    password - mysql password (may be empty string)
  """
  helpString = (
    "%%prog OPTIONS\n"
    "Applies the given mysql login information as overrides for %s.") % (
    monitorsdb.MonitorsDbConfig.CONFIG_NAME,)

  parser = OptionParser(helpString)

  parser.add_option(
      "--host",
      action="store",
      type="string",
      dest="host",
      help="mysql hostname or IP address [REQUIRED]")

  parser.add_option(
      "--user",
      action="store",
      type="string",
      dest="user",
      help="mysql user name [REQUIRED]")

  parser.add_option(
      "--password",
      action="store",
      type="string",
      dest="password",
      default="",
      help="mysql password [OPTIONAL]")

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if not options.host:
    parser.error("Required \"--host\" value was empty string or not specified")

  if not options.user:
    parser.error("Required \"--user\" value was empty string or not specified")

  return dict(
    host=options.host,
    user=options.user,
    password=options.password)



def main():
  logging_support.LoggingSupport().initTool()

  try:
    options = _parseArgs()

    host = options["host"]
    user = options["user"]
    password = options["password"]

    config = monitorsdb.MonitorsDbConfig()

    configWriter = monitorsdb.MonitorsDbConfig(mode=Config.MODE_OVERRIDE_ONLY)

    if not configWriter.has_section("repository"):
      configWriter.add_section("repository")

    def override(option, value):
      assert config.has_option("repository", option), option
      configWriter.set("repository", option, value)

    override("host", host)
    override("user", user)
    override("password", password)

    configWriter.save()

    g_log.info("Override of mysql settings for %s completed successfully",
               monitorsdb.MonitorsDbConfig.CONFIG_NAME)

  except SystemExit as e:
    if e.code != 0:
      g_log.exception("Failed!")
    raise
  except Exception:
    g_log.exception("Failed!")
    raise



if __name__ == "__main__":
  main()
