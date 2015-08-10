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
 Plumbing methods for Jenkins.
"""

import os
import shutil

import xml.etree.ElementTree as ET

from infrastructure.utilities.YOMP import (
  getCurrentSha,
  getGitRootFolder)


XUNIT_TEST_RESULTS_FILE_PATH = (
  "/opt/numenta/YOMP/tests/results/py2/xunit/jenkins/results.xml")

def getTestResult(filename):
  """
    Get output by reading filename

    :param filename: Name of .xml to be parsed

    :returns True in case of success else False

    :rtype bool
  """
  tree = ET.parse(filename)
  result = tree.getroot().items()[2][1]
  return True if int(result) is 0 else False


def getResultsDir():
  """
    :return Returns path to given keyFileName
  """
  return os.path.join(getWorkspace(), "results")


def getWorkspace():
  """
    :raises:
      infrastructure.utilities.exceptions.CommandFailedError if
        the workspace env variable isn't set and you are running from outside of
        a YOMP repo or the YOMP command to find your current root folder fails.

    :returns: The value of the `WORKSPACE` environment variable, or the root
    folder of the products repo. This assumes you are executing from any folder
    within the Products repo.
  """
  workspace = None
  if "WORKSPACE" in os.environ:
    workspace = os.environ["WORKSPACE"]
  else:
    workspace = getGitRootFolder()
  return workspace


def createOrReplaceDir(dirname):
  """
    Creates a dirname dir in workspace. As a initial cleanup also
    deletes dirname if already present

    :param dirname: Directory name that should be created inside workspace

    :returns path to created dirname
  """
  workspace = getWorkspace()
  if os.path.exists(os.path.join(workspace, dirname)):
    shutil.rmtree("%s/%s" % (workspace, dirname))
  os.makedirs("%s/%s" % (workspace, dirname))
  return os.path.join(workspace, dirname)


def createOrReplaceResultsDir():
  """
    Creates a "results" dir in workspace. As a initial cleanup also
    deletes "results" if already present

    :returns path to created "results"
  """
  return createOrReplaceDir("results")


def getBuildNumber():
  """
    :raises:
      infrastructure.utilities.exceptions.CommandFailedError if
        the workspace env variable isn't set and you are running from outside of
        a YOMP repo or the YOMP command to find your current root folder fails.

    :returns: The value of the `BUILD_NUMBER` environment variable if set, or
    the current commit SHA of the YOMP repo if it's not set.
  """
  buildNumber = None
  if "BUILD_NUMBER" in os.environ:
    buildNumber = os.environ["BUILD_NUMBER"]
  else:
    buildNumber = getCurrentSha()
  return buildNumber


def getKeyPath(keyFileName="chef_west.pem"):
  """
    Returns path to given keyFileName

    :param keyFileName: Name of authorization key

    :return Returns path to given keyFileName
  """
  return os.path.join(os.environ.get("HOME"), ".ssh", keyFileName)


def createOrReplaceArtifactsDir():
  """
    Creates a "artifacts" dir in workspace. As a initial cleanup also
    deletes "artifacts" if already present

    :returns path to created "artifacts"
  """
  return createOrReplaceDir("artifacts")
