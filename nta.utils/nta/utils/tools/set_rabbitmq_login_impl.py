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
Applies the given rabbitmq login information as overrides for
rabbitmq.conf.

NOTE: this script may be configured as "console script" by the package
installer.
"""

import logging
from optparse import OptionParser

from nta.utils import amqp
from nta.utils.config import Config



g_log = logging.getLogger("set_rabbitmq_login")



def setRabbitmqLoginScriptImpl():
  """ Implementation for product-specific scripts that need to set RabbitMQ
  connectiona and authentication information. It parses options from
  command-line args (see _parseArgs function) and applies the overrides to the
  rabbitmq.conf configuration object.

  The calling script needs to initialize logging via logging_support prior to
  invoking this function.
  """
  try:
    options = _parseArgs()

    host = options["host"]
    user = options["user"]
    password = options["password"]

    config = amqp.connection.RabbitmqConfig()

    configWriter = amqp.connection.RabbitmqConfig(mode=(
        amqp.connection.RabbitmqConfig.MODE_OVERRIDE_ONLY))

    if not configWriter.has_section("connection"):
      configWriter.add_section("connection")

    if not configWriter.has_section("credentials"):
      configWriter.add_section("credentials")

    def overrideConnection(option, value):
      assert config.has_option("connection", option), option
      configWriter.set("connection", option, value)

    def overrideCredentials(option, value):
      assert config.has_option("credentials", option), option
      configWriter.set("credentials", option, value)

    overrideConnection("host", host)
    overrideCredentials("user", user)
    overrideCredentials("password", password)

    configWriter.save()

    g_log.info("Override of rabbitmq settings for %s completed successfully",
               amqp.connection.RabbitmqConfig.CONFIG_NAME)

  except SystemExit as e:
    if e.code != 0:
      g_log.exception("Failed!")
    raise
  except Exception:
    g_log.exception("Failed!")
    raise



def _parseArgs():
  """
  :returns: dict of arg names and values:
    host - rabbitmq hostname or IP address (required, non-empty)
    user - rabbitmq user name (required, non-empty)
    password - rabbitmq password (required, non-empty)
  """
  helpString = (
    "%%prog OPTIONS\n"
    "Applies the given rabbitmq login information as overrides for %s.") % (
    amqp.connection.RabbitmqConfig.CONFIG_NAME,)

  parser = OptionParser(helpString)

  parser.add_option(
      "--host",
      action="store",
      type="string",
      dest="host",
      help="rabbitmq hostname or IP address [REQUIRED]")

  parser.add_option(
      "--user",
      action="store",
      type="string",
      dest="user",
      help="rabbitmq user name [REQUIRED]")

  parser.add_option(
      "--password",
      action="store",
      type="string",
      dest="password",
      default="",
      help="rabbitmq password [REQUIRED]")

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if not options.host:
    parser.error("Required \"--host\" value was empty string or not specified")

  if not options.user:
    parser.error("Required \"--user\" value was empty string or not specified")

  if not options.password:
    parser.error(
      "Required \"--password\" value was empty string or not specified")

  return dict(
    host=options.host,
    user=options.user,
    password=options.password)
