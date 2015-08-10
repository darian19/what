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
# TODO: TAUR-1363 - Clean up the logger=None throughout this file.

import os
import time

from subprocess import CalledProcessError, check_call, check_output

from infrastructure.utilities import logger as diagnostics
from infrastructure.utilities.exceptions import CommandFailedError



def executeCommand(command, env=None, logger=None):
  """
  Execute a command and return the raw output

  @param command: String or list containing the exact command to execute.

  @param env: The environment required to execute the command which is passed.
              By default use os.environ

  @param printEnv: whether or not to print the environment passed to command

  @param logger: logger for additional debug info if desired

  @raises
    infrastructure.utilities.exceptions.CommandFailedError if
    the command fails

  @returns: A str representing the raw output of the command

  @rtype: string
  """
  try:
    if env is None:
      env = os.environ
    if logger is not None:
      diagnostics.printEnv(env, logger)
      logger.debug("**********> %s", command)
    if isinstance(command, basestring):
      command = command.strip().split(" ")
    return check_output(command, env=env).strip()
  except CalledProcessError as e:
    errMessage = "Failed to execute: %s; original=%r" % (command, e,)
    raise CommandFailedError(errMessage)


def runWithRetries(command, retries=1, delay=1, logger=None):
  """
  Run a command up to retries times until it succeeds.

  @param command: Command line to run

  @param retries: maximum number of retries

  @param delay: delay in seconds between retries

  @param printEnv: whether or not to print the environment passed to command

  @param logger: logger for additional debug info if desired

  @raises infrastructure.utilities.exceptions.CommandFailedError
  if the command doesn't succeed after trying retries times
  """
  attempts = 0
  while attempts < retries:
    attempts = attempts + 1
    try:
      runWithOutput(command, printEnv=printEnv, logger=logger)
      return
    except CommandFailedError:
      if logger is not None:
        logger.debug("Attempt %s to '%s' failed, retrying in %s seconds...",
                     attempts, command, delay)
      time.sleep(delay)

  errMessage = "%s failed after %s attempts" % (command, retries)
  raise CommandFailedError(errMessage)


def runWithOutput(command, env=None, logger=None):
  """
  Run a command, printing as the command executes.

  @param command: Command to run. Can be str or list

  @param env: environment variables to use while running command

  @param printEnv: Whether or not to print the environment passed to command

  @param logger: optional logger for additional debug info if desired
  """
  try:
    if env is None:
      env = os.environ
    if logger is not None:
      diagnostics.printEnv(env, logger)
      logger.debug("**********> %s", command)
    if isinstance(command, basestring):
      command = command.strip().split(" ")
    check_call(command, env=env)
  except CalledProcessError:
    errMessage = "Failed to execute: %s" % (command,)
    raise CommandFailedError(errMessage)
  # Catch other exceptions, add info about what command triggered them
  except Exception as e:
    errMessage = "Failed to execute: %s; original=%r" % (command, e,)
    if logger is not None:
      logger.exception(errMessage)
    raise
