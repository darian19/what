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

import argparse
import json
import os
import sys
import yaml

from fabric.api import settings, run

from infrastructure.utilities import logger


"""
1) While running using command-line expected parameters are
  repoName : Name of repository which is supposed to be synced e.g x86_64
  logLevel : Logger level for current run
  This will make force execution of sync operation for given repository

2) While running using json file.
  When ran using json file it checks value for packageRpm.syncRpm
   - When set to True this will make force execution of sync operation for given
     repositor provided in packageRpm.repository.
   - When set to False. Sync operation would be skipped.
"""


g_confPath = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                          "..", "conf")
g_config = yaml.load(open(os.path.join(g_confPath, "config.yaml"), "r"))



def writePipelineJson(pipelineJson, pipelineParams, syncStatus, message):
  """
  Writes phase details for uploading rpm

  :param pipelineJson: Path locator for pipeline Json file
  :param pipelineParams: Paramters for current run
  :param syncStatus: boolean, whether this phase was executed
  :param message: message for syncStatus in phase details
  """
  pipelineParams["syncRepo"] = {"syncStatus": syncStatus, "message": message}
  g_logger.info(message)
  with open(pipelineJson, 'w') as fp:
    fp.write(json.dumps(pipelineParams, ensure_ascii=False))
  g_logger.debug(pipelineParams)


def syncRepoWithS3(pipelineJson, pipelineParams, repoName):
  """
  This is wrapper which in turn invokes functions for syncing /uploading rpms
  on S3 and updating pipeline json if provided

  :param pipelineParams: Paramters for current run
  :return status for call for syncing / uploading rpms on S3
  """
  serverKey = os.path.join(os.path.expanduser("~"), ".ssh",
                           g_config["KEY"] + ".pem")
  with settings(host_string=os.environ["RPMBUILDBOX"],
                key_filename=serverKey, user=g_config["USER"],
                connection_attempts=10, warn_only=True):
    g_logger.info("Updating repo to sync S3 repo")
    result = run("update-individual-repo %s" % repoName)

  message = ""
  if result.return_code:
    message = "Failed to sync repo %s" % repoName
  else:
    message = "%s is up to date with S3" % repoName
  if pipelineJson:
    syncStatus = False if result.return_code else True
    writePipelineJson(pipelineJson, pipelineParams, syncStatus , message)
  return result.return_code


def addAndParseArgs(jsonArgs):
  """
    Parse the command line arguments

    :returns Parsed object for the command-line arguments from sys.argv
    :rtype argparse.Namespace
  """
  parser = argparse.ArgumentParser(description="Tool to sync yum repository"
                                   "with S3")
  parser.add_argument("--repo-name", dest="repoName", type=str,
                      help="Name of the repository to be updated")
  parser.add_argument("--pipeline-json", dest="pipelineJson", type=str,
                      help="Path locator for build json file")
  parser.add_argument("--log", dest="logLevel", type=str, default="warning",
                      help="Logging level")
  args = {}
  if jsonArgs:
    args = jsonArgs
  else:
    args = vars(parser.parse_args())

  global g_logger
  g_logger = logger.initPipelineLogger("sync_yum_repo_s3",
                                       logLevel=args["logLevel"])

  saneParams = {k:v for k, v in args.items() if v is not None}
  del saneParams["logLevel"]

  if "pipelineJson" in saneParams and len(saneParams) > 1:
    errorMessage = "Please provide parameters via JSON file or commandline"
    g_logger.error(errorMessage)
    parser.error(errorMessage)
  else:
    pipelineParams = {}
    if "pipelineJson" in saneParams:
      with open(args["pipelineJson"]) as paramFile:
        pipelineParams = json.load(paramFile)
    else:
      pipelineParams = saneParams
  repoName = pipelineParams.get("repoName", pipelineParams.get("packageRpm",
                                {}).get("repoName"))
  syncRpm = pipelineParams.get("syncRpm", pipelineParams.get("packageRpm",
                                {}).get("syncRpm"))
  if repoName:
    return (repoName, syncRpm, pipelineParams, args["pipelineJson"])
  else:
    parser.error("Please provide all parameters, "
                 "use --help for further details")


def main(jsonArgs={}):
  """
    Main function for the pipeline. Executes all sub-tasks

    :param jsonArgs: dict of pipeline-json and logLevel, defaults to empty
      dict to make the script work independently and via driver scripts.
      e.g. {"pipelineJson" : <PIPELINE_JSON_PATH>,
            "logLevel" : <LOG_LEVEL>}

    :raises: raises generic Exception if anything else goes wrong.
  """
  try:
    (repoName, syncRpm, pipelineParams,
     pipelineJson) = addAndParseArgs(jsonArgs)
    if pipelineJson and not syncRpm:
      if not syncRpm:
        message = "%s is up to date with S3" % repoName
        g_logger.info(message)
        writePipelineJson(pipelineJson, pipelineParams , True,
                          message)
        return 0

    result = syncRepoWithS3(pipelineJson, pipelineParams, repoName)
    syncStatus = False if result else True

    if pipelineJson:
      message = ""
      if result:
        message = "Failed to sync repo %s" % repoName
      else:
        message = "%s is up to date with S3" % repoName

      writePipelineJson(pipelineJson, pipelineParams, syncStatus,
                        message)
    return syncStatus
  except Exception:
    g_logger.exception("Unknown error occurred while syncing yum repo to S3")
    raise



if __name__ == "__main__":
  main()
