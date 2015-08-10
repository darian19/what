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
import shutil

from subprocess import check_call

from infrastructure.utilities.env import prepareEnv
from infrastructure.utilities.exceptions import CommandFailedError
from infrastructure.utilities.jenkins import getBuildNumber, getWorkspace
from infrastructure.utilities.logger import initPipelineLogger, printEnv
from infrastructure.utilities.path import changeToWorkingDir
from infrastructure.utilities.cli import runWithOutput



g_logger = None


def prepareResultsDir():
  """
    Make sure that a results directory exists in the right place. Return the
    path of the results directory.

    :returns: The full path of the results directory
    :rtype: String
  """
  resultsDir = os.path.join(getWorkspace(), "results")
  if not os.path.exists(resultsDir):
    os.makedirs(resultsDir)
  return resultsDir



def runTestCommand(testCommand, env, outputFile=None):
  """
    Runs given test command with provided environment

    :param testCommand: Test command that is suppose to be run
    :param env: Current environ set for YOMP_HOME, etc
    :param outputFile: Optional, Path for output file where stdout should be
      redirected. It is passed only if the test are nonXunitTest, as the
      results are not generated as xml we need redirect them to a text file.
    :returns: return True if tests are successful, False otherwise
    :rtype: bool

  """
  try:
    if outputFile:
      check_call(testCommand, shell=True, env=env,
                 stdout=open(outputFile, "w"))
      # Updating console
      runWithOutput("cat %s" % outputFile, env=env, logger=g_logger)
    else:
      runWithOutput(testCommand, env=env, logger=g_logger)
    return True
  except CommandFailedError:
    if outputFile:
      runWithOutput("cat %s" % outputFile)
    g_logger.error("Error executing %s\n*Most likely cause is a test FAILURE*",
                   testCommand)
    return False



def runUnitTests(env):
  """
    Runs tests listed in files present at {YOMP_HOME}/tests/ci/

    :param env: Current environ set for YOMP_HOME, etc
    :param pipeline: name of repository which has triggered this build
    :param YOMPSha: YOMP SHA used current run
    :returns: return True if tests are successful
    :rtype: bool

  """
  # Print environment for debug purposes
  printEnv(env, g_logger)
  buildWorkspace = os.environ["BUILD_WORKSPACE"]

  xunitSuccess = True
  with open(os.path.join(env["YOMP_HOME"],
                         "tests/ci/test_commands_xunit.txt"), "r") as tests:
    xunitTests = [test.strip() % dict(globals().items() + \
                  locals().items()) for test in tests]

  with changeToWorkingDir(os.path.join(buildWorkspace, "products")):
    g_logger.debug(os.getcwd())
    for xunitTest in xunitTests:
      g_logger.info("-------Running %s -------", xunitTest)
      xunitSuccess = runTestCommand(xunitTest, env)
      g_logger.info("\n\n###### COMPLETED %s tests ######\n\n", xunitTest)
      if not xunitSuccess:
        g_logger.error("-------Failed %s -------", xunitTest)
        break

  if "WORKSPACE" in os.environ:
    # `WORKSPACE` should only be set by Jenkins and we only want to record
    # the test results if we're on Jenkins
    recordXunitTestsResults()

  return xunitSuccess



def recordXunitTestsResults():
  """
    This updates result generated for tests which does report formatted test
    result.
    Results are updated to a directory name masterResults where jenkins can find
    it. Results are archived by jenkins for each build.
  """
  jobResultsDir = os.path.join(os.environ["BUILD_WORKSPACE"], "products")
  masterResults = prepareResultsDir()
  jobNumber = getBuildNumber()

  def attemptResultUpdate(task):
    originalResultsFile = "%s_unit_test_results.xml" % task
    newResultsFile = "%s_unit_test_results_%s.xml" % (task, jobNumber)
    if os.path.exists(os.path.join(jobResultsDir, originalResultsFile)):
      shutil.move(os.path.join(jobResultsDir, originalResultsFile),
                  os.path.join(masterResults, newResultsFile))

  attemptResultUpdate("YOMP")
  attemptResultUpdate("htmengine")
  attemptResultUpdate("nta.utils")



def addAndParseArgs(jsonArgs):
  """
    Parse the command line arguments.

    :returns : pipeline, buildWorkspace, YOMPSha, pipelineParams.
  """
  parser = argparse.ArgumentParser(description="test tool to run Test for "
                                   "YOMP. Provide parameters either "
                                   "via path for JSON file or commandline. "
                                   "Provinding both JSON parameter and as a "
                                   "commandline is prohibited. "
                                   "Use help for detailed information for "
                                   "parameters")
  parser.add_argument("--build-workspace", dest="buildWorkspace", type=str,
                      help="Common dir prefix for YOMP")
  parser.add_argument("--pipeline-json", dest="pipelineJson", type=str,
                      help="Path locator for build json file. This file should "
                      "have all parameters required by this script. Provide "
                      "parameters either as a command line parameters or as "
                      "individial parameters")
  parser.add_argument("--log", dest="logLevel", type=str, default="warning",
                      help="Logging level, optional parameter and defaulted to "
                      "level warning")

  args = {}
  if jsonArgs:
    args = jsonArgs
  else:
    args = vars(parser.parse_args())

  global g_logger
  g_logger = initPipelineLogger("run_tests", logLevel=args["logLevel"])

  g_logger.debug(args)
  saneParams = {k:v for k, v in args.items() if v is not None}

  del saneParams["logLevel"]

  if "pipelineJson" in saneParams and len(saneParams) > 1:
    parser.error("Please provide parameters via JSON file or commandline,"
                   "but not both")

  if "pipelineJson" in saneParams:
    with open(args["pipelineJson"]) as paramFile:
      pipelineParams = json.load(paramFile)
  else:
    pipelineParams = saneParams

  buildWorkspace = os.environ.get("BUILD_WORKSPACE",
                     pipelineParams.get("buildWorkspace",
                     pipelineParams.get("manifest", {}).get("buildWorkspace")))

  if buildWorkspace and pipelineParams:
    return (buildWorkspace, pipelineParams, args["pipelineJson"])
  else:
    parser.error("Please provide all parameters, "
                 "use --help for further details")



def main(jsonArgs=None):
  """
    Main function.

    :param jsonArgs: dict of pipeline-json and logLevel, defaults to empty
      dict to make the script work independently and via driver scripts.
      e.g. {"pipelineJson" : <PIPELINE_JSON_PATH>,
            "logLevel" : <LOG_LEVEL>}

  """
  jsonArgs = jsonArgs or {}
  testResult = False
  try:
    (buildWorkspace, pipelineParams, pipelineJson) = addAndParseArgs(jsonArgs)

    os.environ["BUILD_WORKSPACE"] = buildWorkspace
    env = prepareEnv(buildWorkspace, None, os.environ)

    testResult = runUnitTests(env=env)
    # Write testResult to JSON file if JSON file driven run
    if pipelineJson:
      pipelineParams["test"] = {"testStatus" : testResult}
      with open(pipelineJson, 'w') as fp:
        fp.write(json.dumps(pipelineParams, ensure_ascii=False))
      runWithOutput("cat %s" % pipelineJson)
    # In any case log success/failure to console and exit accordingly
    exitStatus = int(not testResult)
    if exitStatus:
      g_logger.error("Test Failure!!!")
    else:
      g_logger.debug("All tests passed")
    return exitStatus
  except:
    g_logger.exception("Unknown error occurred while running unit tests")
    raise



if __name__ == "__main__":
  main()
