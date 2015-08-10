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

import os

from infrastructure.utilities.path import changeToWorkingDir
from infrastructure.utilities.exceptions import CommandFailedError
from infrastructure.utilities.cli import runWithOutput


def uploadToSauceLab(apkPath, apkName, uploadName, logger):
  """
    Uploads the APK to saucelab

    :param apkPath: Path to the APK
    :param apkName: Name of the APK in the artifacts directory
    :param uploadName: Name of the apk to upload to saucelab
    :param logger: An initialized logger.

    :raises: CommandFailedError when the `curl` command fails.
  """

  user = os.environ["SAUCE_USER_NAME"]
  key = os.environ["SAUCE_KEY"]
  sauceUrl = "https://saucelabs.com/rest/v1/storage"
  command = ("curl -u %s:%s -X POST"
             " %s/%s/%s?overwrite=true"
             " -H Content-Type:application/octet-stream --data-binary @%s" %
             (user, key, sauceUrl, user, uploadName, apkName))

  with changeToWorkingDir(apkPath):
    try:
      logger.info("---------------- Uploading to saucelabs ----------------")
      runWithOutput(command, logger=logger)
    except CommandFailedError:
      logger.exception("Failed to upload APK to saucelab.")
      raise
