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

from time import sleep

from fabric.api import run, settings
from YOMPcli.api import YOMPSession

from infrastructure.utilities.exceptions import (
  YOMPConfigError,
  InstanceLaunchError,
  InstanceNotReadyError)

YOMP_AWS_CREDENTIALS_SETUP_TRIES = 30
MAX_RETRIES_FOR_INSTANCE_READY = 18
SLEEP_DELAY = 10



def checkYOMPServicesStatus(logger):
  """
    Checks to see if all YOMP Services are running. Returns True if all Services
    are running and False if any are not running.  This should be wrapped in
    retry logic with error handling.

    :param logger: Initialized logger

    :raises: infrastructure.utilities.exceptions.InstanceLaunchError
      If a YOMP service fails to startup.

    :returns: True if YOMPServices are running properly.
    :rtype: boolean
  """
  cmd = ("source /etc/YOMP/supervisord.vars && "
         "supervisorctl -c /opt/numenta/YOMP/conf/supervisord.conf status")
  YOMPServicesState = run(cmd)

  for service in YOMPServicesState.split("\r\n"):
    if set(["FATAL", "EXITED"]) & set(service.split(" ")):
      raise InstanceLaunchError("Some YOMP services failed to start:\r\n%s" %
                                YOMPServicesState.stdout)
    elif set(["STOPPED", "STARTING", "UNKNOWN"]) & set(service.split(" ")):
      logger.debug("Some YOMP services are not yet ready: \r\n %s" %
                   YOMPServicesState.stdout)
      break
  else:
    return True
  return False


def checkNginxStatus(logger):
  """
    Checks to see if Nginx is running for YOMP. Returns True if it is and False
    otherwise. This should be wrapped in retry logic with error handling.

    :param logger: Initialized logger

    :raises: infrastructure.utilities.exceptions.InstanceLaunchError
      If Nginx starts up using the error configuration.

    :returns: True if Nginx is running using the correct conf file for YOMP.
    :rtype: boolean
  """
  output = run("ps aux | grep -e nginx -e YOMP-api.conf | grep -v grep")

  # If nginx launches with our error config, raise an exception
  if "YOMP-error.conf" in output.stdout:
    raise InstanceLaunchError("Nginx launched in Error state: \r\n %s" %
                              output.stdout)
  # Else if we're still stopped or currently loading YOMP, just log a debug msg
  elif ("YOMP-loading.conf" in output.stdout or
        "YOMP-stopped.conf" in output.stdout):
    logger.debug("Nginx has not yet finished loading: \r\n %s" % output.stdout)


  return "YOMP-api.conf" in output.stdout


def waitForYOMPServerToBeReady(publicDnsName, serverKey, user, logger):
  """
    Wait for a pre-determined amount of time for the YOMP server to be ready.

    :param publicDnsName: Reachable DNS entry of a YOMP server

    :param serverKey: SSH Key to use to connect to the instance

    :param user: Username to use when connecting via SSH (e.g.: ec2-user)

    :param logger: Initialized logger

    :raises:
      infrastructure.utilities.exceptions.InstanceNotReadyError
      If either YOMP or Nginx fails to come up properly in the prescribed time.

    :raises infrastructure.utilities.exceptions.InstanceLaunchError:
      If a YOMP service fails to startup.
  """
  nginx = YOMPServices = False
  with settings(host_string = publicDnsName,
                key_filename = serverKey, user = user,
                connection_attempts = 30, warn_only = True):
    for _ in xrange(MAX_RETRIES_FOR_INSTANCE_READY):
      logger.info("Checking to see if nginx and YOMP Services are running")
      try:
        nginx = checkNginxStatus(logger)
        YOMPServices = checkYOMPServicesStatus(logger)
      except EOFError:
        # If SSH hasn't started completely on the remote system, we may get an
        # EOFError trying to provide a password for the user. Instead, just log
        # a warning and continue to retry
        logger.warning("SSH hasn't started completely on the remote machine")
      if nginx and YOMPServices:
        break
      sleep(SLEEP_DELAY)
    else:
      raise InstanceNotReadyError("YOMP services not ready on server %s after "
                                  "%d seconds." % (publicDnsName,
                                                MAX_RETRIES_FOR_INSTANCE_READY *
                                                SLEEP_DELAY))


def setupYOMPAWSCredentials(publicDnsName, config):
  """
    Using the YOMP CLI, connect to YOMP to obtain the API Key for the instance.

    :param publicDnsName: A reachable DNS entry for the YOMP server that needs
      to be configured

    :param config: A dict containing values for `AWS_ACCESS_KEY_ID`
      and `AWS_SECRET_ACCESS_KEY`

    :raises: infrastructure.utilities.exceptions.YOMPConfigError if
      it is unable to obtain the API Key

    :returns: The API Key of the YOMP server
  """
  credentials = {
    "aws_access_key_id": config["AWS_ACCESS_KEY_ID"],
    "aws_secret_access_key": config["AWS_SECRET_ACCESS_KEY"]
  }
  server = "https://%s" % publicDnsName
  YOMP = YOMPSession(server=server)
  YOMP.apikey = YOMP.verifyCredentials(**credentials)
  if YOMP.apikey:
    YOMP.updateSettings(settings=credentials, section="aws")
    return YOMP.apikey
  else:
    raise YOMPConfigError("Unable to obtain YOMP API Key")


def getApiKey(instanceId, publicDnsName, config, logger):
  """
    When the API Key is unknown, get the API Key from the server. This should be
    used for newly instantiated YOMP servers.

    :param instanceId: The EC2 instance ID of the new server

    :param publicDnsName: The reachable DNS entry for the instance under test

    :param logger: An initialized logger.

    :raises infrastructure.utilities.exceptions.YOMPConfigError: If
      the API Key doesn't get set properly on a new instance.

    :returns: A string value representing the API Key of the new instance.
  """
  for _ in xrange(YOMP_AWS_CREDENTIALS_SETUP_TRIES):
    logger.debug("Trying to setup YOMP AWS Credentials.")
    try:
      YOMPApiKey = setupYOMPAWSCredentials(publicDnsName, config)
    except (YOMPConfigError, AttributeError):
      # We want to retry this, so just keep going on a YOMPConfigError or
      # AttributeError (which probably indicates that the response was empty)
      pass
    if YOMPApiKey:
      logger.info("YOMP API Key: %s" % YOMPApiKey)
      break
    sleep(SLEEP_DELAY)
  else:
    raise YOMPConfigError("Failed to get API Key for instance %s" %
                          instanceId)
  return YOMPApiKey
