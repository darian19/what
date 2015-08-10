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
import signal
import yaml

from pkg_resources import resource_stream

from fabric.api import settings, run, get
import xml.etree.ElementTree as ET

from infrastructure.utilities.ec2 import (
  launchInstance,
  stopInstance,
  terminateInstance)
from infrastructure.utilities.exceptions import (
  MissingAWSKeysInEnvironment,
  TestsFailed
)
from infrastructure.utilities.YOMP_server import (
  getApiKey, waitForYOMPServerToBeReady)
from infrastructure.utilities.jenkins import getBuildNumber, getWorkspace
from infrastructure.utilities.logger import initPipelineLogger



# Prepare configuration
g_config = yaml.load(resource_stream(__name__, "../conf/config.yaml"))
g_config["JOB_NAME"] = os.environ.get("JOB_NAME", "Local Run")

g_dirname = os.path.abspath(os.path.dirname(__file__))
g_remotePath = "/opt/numenta/YOMP/tests/results/py2/xunit/jenkins/results.xml"
g_rpmBuilder = "rpmbuild.YOMPsolutions.com"
g_s3RepoPath = "/opt/numenta/s3repo/s3/x86_64"
s3Bucket = "public.numenta.com"

g_logger = None

FIRST_BOOT_RUN_TRIES = 18
YOMP_SERVICES_TRIES = 6
YOMP_AWS_CREDENTIALS_SETUP_TRIES = 30
SLEEP_DELAY = 10


def analyzeResults(resultsPath):
  """
    Reads results.xml and accordingly gives the status of test.

    :returns: returns True is all tests have passed else false.
    :rtype: Bool
  """
  successStatus = True
  results = ET.parse(resultsPath)
  failures = int(results.getroot().get("failures"))
  errors = int(results.getroot().get("errors"))
  if failures or errors:
    successStatus = False
  return successStatus


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


def postTestRunAction(instanceId, terminate=True, **config):
  """
    Terminate or stop the instance. If the tests fail then
    just stop the instance or terminate it.

    :param instanceID: InstanceID of instance launched.
    :terminate: if True terminate the instance else stop instance.
    :config: dict of config values
  """
  if terminate:
    g_logger.info("Terminating instance %s", instanceId)
    terminateInstance(instanceId, config, g_logger)
  else:
    g_logger.info("Stopping instance %s", instanceId)
    stopInstance(instanceId, config, g_logger)


def parseArgs():
  """
    Parses commandline Arguments

    :returns: parsed arguments
  """
  parser = argparse.ArgumentParser(description="Run integration tests on an "
                                   "instance launched from given AMI")
  parser.add_argument("--ami", dest="ami", type=str,
                      help="The AMI which is to be tested")
  parser.add_argument("--pipeline-json", dest="pipelineJson", type=str,
                      help="The AMI which is to be tested")
  parser.add_argument("--log", dest="logLevel", type=str, default="debug",
                      help="Logging level, optional parameter and defaulted to"
                      "level debug")

  args = parser.parse_args()
  if not args.ami:
    parser.error("Please provide the AMI to bring up the instance.")

  return args


def main():
  """
    This is the main class.
  """
  args = parseArgs()

  global g_logger
  g_logger = initPipelineLogger("run-integration-tests", logLevel=args.logLevel)

  if not (os.environ.get("AWS_ACCESS_KEY_ID") and
          os.environ.get("AWS_SECRET_ACCESS_KEY")):
    g_logger.error("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    raise MissingAWSKeysInEnvironment("AWS keys are not set")
  else:
    g_config["AWS_ACCESS_KEY_ID"] = os.environ["AWS_ACCESS_KEY_ID"]
    g_config["AWS_SECRET_ACCESS_KEY"] = os.environ["AWS_SECRET_ACCESS_KEY"]

  #launching instance with the give AMI
  publicDnsName, instanceId = launchInstance(args.ami, g_config, g_logger)

  resultsDir = prepareResultsDir()
  serverKey = os.path.join("~", ".ssh", g_config["KEY"] + ".pem")

  # The calls in this function are not signal-safe. However, the expectation is
  # that making them signal safe would be overly burdensome at this time. If
  # issues arise later, then we'll figure out what the right approach is at that
  # time.
  def handleSignalInterrupt(signal, _frame):
    g_logger.error("Received interrupt signal %s", signal)
    if instanceId:
      g_logger.error("Terminating instance %s", instanceId)
      terminateInstance(instanceId, g_config, g_logger)

  signal.signal(signal.SIGINT, handleSignalInterrupt)
  signal.signal(signal.SIGTERM, handleSignalInterrupt)

  with settings(host_string=publicDnsName,
                key_filename=serverKey,
                user=g_config["USER"], connection_attempts=30, warn_only=True):
    g_logger.info("Connected to %s using %s.pem", publicDnsName, serverKey)
    # Run Integration tests
    try:
      waitForYOMPServerToBeReady(publicDnsName, serverKey, g_config["USER"],
                                 g_logger)
      getApiKey(instanceId, publicDnsName, g_config, g_logger)
      # TODO remove the exports; keeping them intact for now because some of the
      # integration tests use the ConfigAttributePatch which reads these values
      # from environment.
      runTestCommand = ("export AWS_ACCESS_KEY_ID=%s"
                        % os.environ["AWS_ACCESS_KEY_ID"] +
                        " && export AWS_SECRET_ACCESS_KEY=%s"
                        % os.environ["AWS_SECRET_ACCESS_KEY"] +
                        " && source /etc/YOMP/supervisord.vars" +
                        " && cd $YOMP_HOME" +
                        " && ./run_tests.sh --integration --language py" +
                        " --results xunit jenkins")
      run(runTestCommand)
      g_logger.debug("Retreiving results")
      get("%s" % (g_remotePath), resultsDir)
    except Exception:
      g_logger.exception("Caught exception in run_tests")
      stopInstance(instanceId, g_config, g_logger)
      raise
    else:
      g_logger.info("Tests have finished.")

      # Rename the results file to be job specific
      newResultsFile = "YOMP_integration_test_results_%s.xml" % getBuildNumber()
      if os.path.exists(os.path.join(resultsDir, "results.xml")):
        shutil.move(os.path.join(resultsDir, "results.xml"),
                    os.path.join(resultsDir, newResultsFile))
      if os.path.exists(os.path.join(resultsDir, newResultsFile)):
        successStatus = analyzeResults("%s/%s" % (resultsDir, newResultsFile))
      else:
        g_logger.error("Could not find results file: %s", newResultsFile)
        successStatus = False

      if args.pipelineJson:
        with open(args.pipelineJson) as jsonFile:
          pipelineParams = json.load(jsonFile)

        pipelineParams["integration_test"] = {"testStatus": successStatus}
        with open(args.pipelineJson, "w") as jsonFile:
          jsonFile.write(json.dumps(pipelineParams, ensure_ascii=False))

      if successStatus:
        postTestRunAction(instanceId, terminate=True, **g_config)
      else:
        postTestRunAction(instanceId, terminate=False, **g_config)
        raise TestsFailed("Integration test failed")



if __name__ == "__main__":
  main()
