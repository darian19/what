#!/usr/bin/env python
#------------------------------------------------------------------------------
# Copyright 2013-2014 Numenta Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#------------------------------------------------------------------------------
import json
from optparse import OptionParser
import sys

from prettytable import PrettyTable

import YOMPcli
from YOMPcli.api import YOMPSession
from YOMPcli.exceptions import YOMPCLIError



# Subcommand CLI Options

if __name__ == "__main__":
  subCommand = "%prog"
else:
  subCommand = "%%prog %s" % __name__.rpartition('.')[2]

USAGE = """%s metrics (list|monitor|unmonitor) \
[YOMP_SERVER_URL YOMP_API_KEY] [options]

Manage custom metrics.
""".strip() % subCommand

parser = OptionParser(usage=USAGE)
parser.add_option(
  "--id",
  dest="id",
  metavar="ID",
  help="Metric ID (required for monitor)")
parser.add_option(
  "--name",
  dest="name",
  metavar="Name",
  help="Metric Name (required for unmonitor)")
parser.add_option(
  "--format",
  dest="format",
  default="text",
  help='Output format (text|json)')



def printHelpAndExit():
  parser.print_help(sys.stderr)
  sys.exit(1)


def handleListRequest(YOMP, fmt):
  metrics = YOMP.listMetrics("custom")

  if fmt == "json":
    print(json.dumps(metrics))
  else:
    table = PrettyTable()

    table.add_column("ID", [x['uid'] for x in metrics])
    table.add_column("Name", [x['name'] for x in metrics])
    table.add_column("Display Name", [x['display_name'] for x in metrics])
    table.add_column("Status", [x['status'] for x in metrics])

    table.align = "l"  # left align
    print(table)


def handleMonitorRequest(YOMP, metricID):
  nativeMetric = {
    "datasource": "custom",
    "uid": metricID
  }
  YOMP.createModel(nativeMetric)


def handleUnmonitorRequest(YOMP, metricName):
  models = YOMP.listModels()

  metrics = [m for m in models if (m["datasource"] == "custom" and
                                   m["name"] == metricName)]

  if not len(metrics):
    raise YOMPCLIError("Metric not found")

  YOMP.deleteModel(metrics[0]["uid"])


def handle(options, args):
  """ `YOMP custom` handler. """
  try:
    resource = args.pop(0)
    action = args.pop(0)
  except IndexError:
    printHelpAndExit()

  (server, apikey) = YOMPcli.getCommonArgs(parser, args)

  YOMP = YOMPSession(server=server, apikey=apikey)

  if resource == "metrics":

    if action == "list":
      handleListRequest(YOMP, options.format)

    elif action == "monitor":
      if not options.id:
        printHelpAndExit()

      handleMonitorRequest(YOMP, options.id)

    elif action == "unmonitor":
      if not options.name:
        printHelpAndExit()

      handleUnmonitorRequest(YOMP, options.name)

    else:
      printHelpAndExit()

  else:
    printHelpAndExit()


if __name__ == "__main__":
  handle(*parser.parse_args())
