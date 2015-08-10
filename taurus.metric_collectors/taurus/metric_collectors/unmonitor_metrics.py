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

""" Unmonitor models on the given destination HTM server """

import json
import logging
from optparse import OptionParser
import os
import sys

from taurus.metric_collectors import logging_support, metric_utils



DEFAULT_HTM_SERVER = os.environ.get("TAURUS_HTM_SERVER")



g_log = logging.getLogger("metric_collectors.unmonitor_metrics")



def _parseArgs():
  """
  :returns: dict of arg names and values:
    htmServer
    apiKey
    unmonitorAll (boolean)
    modelIds (mutually-exclusive with unmonitorAll)
    modelsFilePath
  """
  helpString = (
    "%prog [options] [modelId1 modelId2 ...]\n\n"
    "Unmonitors specific or all models on an HTM server.")

  parser = OptionParser(helpString)

  parser.add_option(
      "--all",
      action="store_true",
      default=False,
      dest="unmonitorAll",
      help="If set, all monitored models will be unmonitored")

  parser.add_option(
    "--modelsout",
    action="store",
    type="string",
    dest="modelsFilePath",
    help=("Required output file path for model objects that is needed for "
          "remonitoring by monitor_metrics. All directory components of the "
          "path must already exist and be writeable"))

  parser.add_option(
    "--server",
    action="store",
    type="string",
    dest="htmServer",
    default=DEFAULT_HTM_SERVER,
    help="Hostname or IP address of server running HTM Engine API to create "
    "models [default: %default]")

  parser.add_option(
    "--apikey",
    action="store",
    type="string",
    dest="apiKey",
    help="API Key of HTM Engine")

  options, modelIds = parser.parse_args()

  if options.unmonitorAll and modelIds:
    msg = "--all is mutually-exclusive with specific modelIds: %r" % (modelIds,)
    g_log.error(msg)
    parser.error(msg)

  if not (options.unmonitorAll or modelIds):
    msg = "Either --all or specific modelIds must be specified"
    g_log.error(msg)
    parser.error(msg)

  if not options.modelsFilePath:
    msg = ("Missing or empty models output file path")
    g_log.error(msg)
    parser.error(msg)


  if not options.htmServer:
    msg = ("Missing or empty Hostname or IP address of server running HTM "
           "Engine API")
    g_log.error(msg)
    parser.error(msg)

  if not options.apiKey:
    msg = "Missing or empty API Key of HTM Engine"
    g_log.error(msg)
    parser.error(msg)


  return dict(
    htmServer=options.htmServer,
    apiKey=options.apiKey,
    unmonitorAll=options.unmonitorAll,
    modelIds = modelIds,
    modelsFilePath=options.modelsFilePath
  )



def main():
  logging_support.LoggingSupport.initTool()

  try:
    options = _parseArgs()
    g_log.info("Running %s with options=%r", sys.argv[0], options)

    if options["unmonitorAll"]:
      models = metric_utils.getAllModels(
        host=options["htmServer"],
        apiKey=options["apiKey"])
    else:
      models = tuple(
        metric_utils.getOneModel(
          host=options["htmServer"],
          apiKey=options["apiKey"],
          modelId=modelId)
        for modelId in options["modelIds"]
      )

    # Save model objects to file for use by monitor_metrics
    with open(options["modelsFilePath"], "w") as outFile:
      json.dump(models, outFile, indent=4)

    if not models:
      g_log.info("No models to unmonitor")
      return

    g_log.info("Unmonitoring %d models", len(models))

    for i, model in enumerate(models, 1):
      modelId = model["uid"]
      metric_utils.unmonitorMetric(
        host=options["htmServer"],
        apiKey=options["apiKey"],
        modelId=modelId)
      g_log.info("Unmonitored metric=%s (%d of %d)",
                 modelId, i, len(models))

    g_log.info("Unmonitored %d models", len(models))
  except SystemExit as e:
    if e.code != 0:
      g_log.exception("unmonitor_metrics failed")
    raise
  except Exception:
    g_log.exception("unmonitor_metrics failed")
    raise



if __name__ == "__main__":
  main()
