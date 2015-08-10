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
Helper methods for running commands remotely.

This is not in utilities.ec2 for two reasons:

1. It doesn't only work on ec2 instances

2. If you put it in utilities.ec2, when it gets imported from utilities.salt
(which is imported from utilities.ec2 because launchNumentaInstance needs
 requestKeySignature) that causes an import loop and raises an exception.
"""
from time import sleep

from fabric.api import hide, run, settings
from fabric.exceptions import NetworkError

from infrastructure.utilities.exceptions import (InstanceLaunchError,
                                                 InvalidParametersError)

# Globals
DEFAULT_USER = "ec2-user"



def runCommandBySSH(dnsName,
                    command,
                    logger,
                    maxRetries=120,
                    sleepDelay=1,
                    user=DEFAULT_USER,
                    silent=False,
                    sshKeyFile=None):
  """
  Run a command on an instance, retrying multiple times.

  :param dnsName: DNS name to run the command on. Required.

  :param command: command to run. Required.

  :param logger: An already initialized logger object. Required.

  :param maxRetries: Maximum retries before giving up on running salt

  :param sleepDelay: Time in seconds between retries

  :param user: User to run the command as.

  :param silent: If True, suppress command output to console.

  :param sshKeyFile: SSH private key to use. Use the user's keys from their
                     ssh-agent keyring if unset.

  :raises: InstanceLaunchError if the command fails to run or has a failure
           during the run.

  :returns: fabric run result of the command

  :rtype: fabric run result
  """
  if not command:
    raise InvalidParametersError("runCommandOnInstance requires a command")
  if not dnsName:
    raise InvalidParametersError("runCommandOnInstance requires a dnsName")
  if not logger:
    raise InvalidParametersError("runCommandOnInstance requires a logger")

  kwargs={ "host_string": dnsName,
           "user": user,
           "timeout": sleepDelay,
           "connection_attempts": maxRetries }
  # We only need to specify a key_filename to settings when sshKeyFile is
  # not None
  if sshKeyFile:
    kwargs["key_filename"] = sshKeyFile

  # Force fabric not to abort if the command fails or we won't be able
  # to retry
  kwargs["warn_only"] = True

  with settings(**kwargs):
    logger.debug("Running %s on %s as %s", command, dnsName, user)
    tries = 0
    while tries < maxRetries:
      tries = tries + 1
      try:
        if silent:
          with hide("output", "running"):
            result = run(command)
        else:
          result = run(command)
        if result.return_code == 0:
          logger.debug("%s completed successfully", command)
          return result
        if tries > maxRetries:
          raise InstanceLaunchError("%s failed to run", command)
        else:
          logger.debug("Try %s failed, retrying in %s seconds", tries,
                       sleepDelay)
          sleep(sleepDelay)
      except NetworkError:
        # If we can't connect to SSH, fabric raises NetworkError
        if tries > maxRetries:
          raise InstanceLaunchError("%s failed to run after %s tries",
                                    command, tries)
        logger.debug("Network error for try %s, retrying in %s seconds",
                     tries, sleepDelay)
        sleep(sleepDelay)

