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
Applies the given dynamodb information as overrides for application.conf.

NOTE: this script may be configured as "console script" by the package
installer.
"""

import logging
from optparse import OptionParser

from nta.utils.config import Config

from taurus.engine import config, logging_support
from taurus.engine.exceptions import InsufficientConfigurationError


g_log = logging.getLogger("set_dynamodb_credentials")



def _parseArgs():
  """
  :returns: dict of arg names and values:
    host - DynamoDB hostname or IP address (required, empty for live AWS api)
    port - DynamoDB port (required, empty for live AWS api)
    isSecure - True to use a secure networking protocol for DynamoDB API
    suffix - DynamoDB table name suffix (required)
  """
  helpString = (
    "%%prog options\n"
    "Applies the given dynamodb information as overrides for Taurus config "
    "object %s.") % (config.CONFIG_NAME,)

  parser = OptionParser(helpString)

  parser.add_option(
      "--host",
      action="store",
      type="string",
      dest="host",
      help=("DynamoDB hostname or IP address [REQUIRED] -- empty string for "
            "live AWS api; typically '127.0.0.1' for DynamoDB Local Emulation "
            "Tool"))

  parser.add_option(
      "--port",
      action="store",
      type="string",
      dest="port",
      help=("DynamoDB port [REQUIRED] -- empty string for live AWS api; "
            "typically 8300 for DynamoDB Local Emulation Tool"))

  parser.add_option(
      "--security-off",
      action="store_true",
      default=False,
      dest="securityOff",
      help=("Disable secure communication with DynamoDB API. NOTE: DynamoDB "
            "Local Emulation Tool requires secure communication to be disabled "
            "at this time; defaults to secure communication "))

  parser.add_option(
      "--table-suffix",
      action="store",
      type="string",
      dest="suffix",
      help=("DynamoDB table name suffix [REQUIRED]. By convention, suffixes "
            "begin with '.'. For example '.staging' or '.production'"))

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if options.host is None:
    parser.error(
      "Host (--host) is a required option.")

  if options.port is None:
    parser.error(
      "Port (--port) is a required option.")

  if not options.suffix:
    parser.error(
      "Table name suffix (--table-suffix) is required to have a value.")

  if ((options.host and not options.port) or
      (options.port and not options.host)):
    parser.error("host and port are biconditional. You must provide values "
                 "for both (for local emulation tool), or neither (for live "
                 "API).")

  if options.port:
    try:
      int(options.port)
    except (TypeError, ValueError):
      parser.error("--port must be an integer, but got %r" % (options.port,))
    except:
      raise Exception("Unable to convert port to integer")

    if not options.securityOff:
      # Warn the user: the user is probably cofigurig for the dynamodb emulation
      # tool, but forgot to pass --security-off
      g_log.warning("If configuring to use dynamodb emulation tool, you need "
                    "to disable secure communication via the --security-off "
                    "option")

  if options.securityOff:
    g_log.warning("Disabling secure communication with DynamoDB")

  return dict(host=options.host, port=options.port,
              isSecure=(not options.securityOff),
              suffix=options.suffix)



def main():
  logging_support.LoggingSupport().initTool()

  try:
    options = _parseArgs()

    host = options["host"]
    port = options["port"]
    isSecure = options["isSecure"]
    suffix = options["suffix"]

    configWriter =  Config(config.CONFIG_NAME, config.baseConfigDir,
                             mode=Config.MODE_OVERRIDE_ONLY)

    if not configWriter.has_section("dynamodb"):
      configWriter.add_section("dynamodb")

    def override(option, value):
      assert config.has_option("dynamodb", option), option
      configWriter.set("dynamodb", option, value)

    override("host", host)
    override("port", port)
    override("is_secure", isSecure)
    override("table_name_suffix", suffix)

    configWriter.save()

    g_log.info("Override of dynamodb settings for %s completed successfully",
               configWriter.CONFIG_NAME)

  except SystemExit as e:
    if e.code != 0:
      g_log.exception("Failed!")
    raise
  except Exception:
    g_log.exception("Failed!")
    raise


if __name__ == "__main__":
  main()
