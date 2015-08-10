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
try:
  import yaml
except ImportError:
  import json # yaml not available, fall back to json
import select
import sys

from functools import partial
from YOMPcli.api import YOMPSession
import YOMPcli
from optparse import OptionParser

# Subcommand CLI Options

if __name__ == "__main__":
  subCommand = "%prog"
else:
  subCommand = "%%prog %s" % __name__.rpartition('.')[2]

USAGE = """%s [YOMP_SERVER_URL YOMP_API_KEY] [FILE]

Import YOMP model definitions.
""".strip() % subCommand

parser = OptionParser(usage=USAGE)
parser.add_option(
  "-d",
  "--data",
  dest="data",
  metavar="FILE or -",
  help="Path to file containing YOMP model definitions, or - if you " \
       "want to read the data from stdin.")

# Implementation

def importMetricsFromFile(YOMP, fp, **kwargs):
  models = YOMPcli.load(fp.read())
  result = YOMP.createModels(models)


def handle(options, args):
  """ `YOMP import` handler. """
  (server, apikey) = YOMPcli.getCommonArgs(parser, args)

  if options.data:
    data = options.data
  else:
    # Pop data source off args
    try:
      data = args.pop(0)
    except IndexError:
      data = "-"

  YOMP = YOMPSession(server=server, apikey=apikey)

  if data.strip() == "-":
    if select.select([sys.stdin,],[],[],0.0)[0]:
      importMetricsFromFile(YOMP, sys.stdin, **vars(options))
    else:
      parser.print_help()
      sys.exit(1)
  elif data:
    with open(data, "r") as fp:
      importMetricsFromFile(YOMP, fp, **vars(options))




if __name__ == "__main__":
  handle(*parser.parse_args())
