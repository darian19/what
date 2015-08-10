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
import sys
from functools import partial
from optparse import OptionParser
from YOMPcli.api import YOMPSession
import YOMPcli

# Subcommand CLI Options

if __name__ == "__main__":
  subCommand = "%prog"
else:
  subCommand = "%%prog %s" % __name__.rpartition('.')[2]

USAGE = """%s [YOMP_SERVER_URL YOMP_API_KEY]

Export YOMP model definitions.
""".strip() % subCommand

parser = OptionParser(usage=USAGE)
parser.add_option(
  "-o",
  "--output",
  dest="output",
  metavar="FILE",
  help="Write output to FILE instead of stdout")
try:
  import yaml
  parser.add_option(
    "-y",
    "--yaml",
    dest="useYaml",
    default=False,
    action="store_true",
    help="Display results in YAML format")
except ImportError:
  pass # yaml not available, hide from user

# Implementation


def handle(options, args):
  """ `YOMP export` handler. """
  (server, apikey) = YOMPcli.getCommonArgs(parser, args)

  dump = partial(json.dumps, indent=2)

  if hasattr(options, "useYaml"):
    if options.useYaml:
      dump = partial(yaml.safe_dump, default_flow_style=False)

  YOMP = YOMPSession(server=server, apikey=apikey)

  if options.output is not None:
    outp = open(options.output, "w")
  else:
    outp = sys.stdout

  models = YOMP.exportModels()

  if models:
    try:
      print >> outp, dump(models)
    finally:
      outp.flush()
      if outp != sys.stdout:
        outp.close()


if __name__ == "__main__":
  handle(*parser.parse_args())
