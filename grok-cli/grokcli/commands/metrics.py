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


if __name__ == "__main__":
  subCommand = "%prog"
else:
  subCommand = "%%prog %s" % __name__.rpartition('.')[2]

USAGE = """%s (list|unmonitor) [YOMP_SERVER_URL YOMP_API_KEY] [options]

Manage monitored metrics.
""".strip() % subCommand


parser = OptionParser(usage=USAGE)
parser.add_option(
  "--id",
  dest="id",
  metavar="ID",
  help="Metric ID (required for unmonitor)")
parser.add_option(
  "--instance",
  dest="instance",
  metavar="INSTANCE_ID",
  help="Instance ID (cloudwatch only)")
parser.add_option(
  "--namespace",
  dest="namespace",
  metavar="NAMESPACE",
  help="Metric namespace (cloudwatch only)")
parser.add_option(
  "--region",
  dest="region",
  metavar="REGION",
  help="AWS Region (cloudwatch only)")
parser.add_option(
  "--format",
  dest="format",
  default="text",
  help='Output format (text|json)')



def printHelpAndExit():
  parser.print_help(sys.stderr)
  sys.exit(1)


def handleListRequest(YOMP, fmt, region=None, namespace=None, instance=None):
  models = YOMP.listModels()

  if region and namespace and instance:
    server = "{0}/{1}/{2}".format(region, namespace, instance)
    models = [m for m in models if (m["datasource"] == "cloudwatch" and
                                    m["server"] == server)]

  if fmt == "json":
    print(json.dumps(models))
  else:
    table = PrettyTable()

    table.add_column("ID", [x['uid'] for x in models])
    table.add_column("Display Name", [x['display_name'] for x in models])
    table.add_column("Name", [x['name'] for x in models])
    table.add_column("Status", [x['status'] for x in models])

    table.align = "l"  # left align
    print(table)


def handleUnmonitorRequest(YOMP, metricID):
  YOMP.deleteModel(metricID)


def handle(options, args):
  """ `YOMP metrics` handler. """
  try:
    action = args.pop(0)
  except IndexError:
    printHelpAndExit()

  (server, apikey) = YOMPcli.getCommonArgs(parser, args)

  YOMP = YOMPSession(server=server, apikey=apikey)

  if action == "list":
    handleListRequest(YOMP, options.format,
                      region=options.region, namespace=options.namespace,
                      instance=options.instance)
  elif action == "unmonitor":
    if not options.id:
      printHelpAndExit()

    handleUnmonitorRequest(YOMP, options.id)
  else:
    printHelpAndExit()


if __name__ == "__main__":
  handle(*parser.parse_args())
