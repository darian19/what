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

"""Utility functions for AWS RDS."""

import logging
import time

import boto.ec2
from boto.exception import (AWSConnectionError, BotoServerError)
from nupic.support import decorators

from YOMP.app import config



class RDSServerErrorCodes(object):
  """RDS Server error codes of interest.

  NOTE: these MUST be the error codes as defined by AWS RDS!

  See docs.aws.amazon.com/AmazonRDS/latest/APIReference/CommonErrors.html
  for error list
  """

  # The request processing has failed because of an unknown error, exception or
  # failure
  INTERNAL_FAILURE = "InternalFailure"  # HTTP Status Code: 500

  # The request reached the service more than 15 minutes after the date stamp on
  # the request or more than 15 minutes after the request expiration date (such
  # as for pre-signed URLs), or the date stamp on the request is more than 15
  # minutes in the future.
  REQUEST_EXPIRED = "RequestExpired"  # HTTP Status Code: 400

  # The request has failed due to a temporary failure of the server
  SERVICE_UNAVAILABLE = "ServiceUnavailable"  # HTTP Status Code: 503

  # The request was denied due to request throttling
  THROTTLING = "Throttling"  # HTTP Status Code: 400



# Excceptions that are subject to transient-error retries
RETRY_EXCEPTIONS = (
  AWSConnectionError,
  BotoServerError,
)



# BotoServerError error codes that are subject to transient-error retries
RETRIABLE_SERVER_ERROR_CODES = (
  RDSServerErrorCodes.INTERNAL_FAILURE,
  RDSServerErrorCodes.REQUEST_EXPIRED,
  RDSServerErrorCodes.SERVICE_UNAVAILABLE,
  RDSServerErrorCodes.THROTTLING,
)

# Default timeout for RDS retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1



def retryOnRDSTransientError(logger=logging.root,
                             timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """Create a decorator for retrying a function upon RDS transient error.

  :param logger: a python logger object for logging failures; defaults to the
      builtin root logger

  :param timeoutSec: How many seconds from time of initial call to stop retrying
  :type timeoutSec: floating point

  :returns: a decorator
  """

  def retryFilter(e, *_args, **_kwargs):
    """Return True to permit a retry, false to re-raise the exception."""
    if isinstance(e, BotoServerError):
      if getattr(e, "error_code", "") in RETRIABLE_SERVER_ERROR_CODES:
        return True
      else:
        return False

    return True

  return decorators.retry(
    timeoutSec=timeoutSec,
    initialRetryDelaySec=INITIAL_RETRY_BACKOFF_SEC,
    maxRetryDelaySec=MAX_RETRY_BACKOFF_SEC,
    retryExceptions=RETRY_EXCEPTIONS,
    retryFilter=retryFilter,
    getLoggerCallback=lambda: logger,
    clientLabel="retryOnCloudWatchTransientError")



def getRDSInstances(region):
  """Simple generator for getting RDS instances.

  :param region: the region to get instances for
  :returns: a generator of :class:`boto.rds.dbinstance.DBInstance` instances
  """
  awsAccessKeyId = config.get("aws", "aws_access_key_id")
  awsSecretAccessKey = config.get("aws", "aws_secret_access_key")
  conn = boto.rds.connect_to_region(region_name=region,
                                    aws_access_key_id=awsAccessKeyId,
                                    aws_secret_access_key=awsSecretAccessKey)
  for instance in conn.get_all_dbinstances():
    yield instance



@retryOnRDSTransientError()
def getSuggestedInstances(region, queue=None, timeout=None):
  """Gets a sequence of suggested instances with highest value first.

  This returns available RDS instances in decreasing order of allocated storage.

  You can optionally pass a queue to put results in. This is useful when running
  this function in a thread. Additionally, a timeout can be passed to limit how
  long the thread executes.

  :param region: the region to get instances for
  :param queue: an optional Queue.Queue for putting results
  :param timeout: when this time has elapsed, the function will stop fetching
      instances and format and return the results
  :returns: a list of instance dicts as formatted by :func:`formatInstance`
  """
  start = time.time()
  instances = []
  for instance in getRDSInstances(region):
    if instance.status != "available":
      if timeout is not None and time.time() - start > timeout:
        break
      continue
    storage = instance.allocated_storage
    instances.append((storage, instance))
    if timeout is not None and time.time() - start > timeout:
      break
  instances = (formatInstance(instance, region)
               for _, instance in sorted(instances, reverse=True))
  if queue:
    for instance in instances:
      queue.put(instance)
  return instances



def formatInstance(instance, region):
  """Convert a boto RDS instance into the format to return to clients.

  :param instance: instance of boto.rds.dbinstance.DBInstance
  :param region: the region the load balancer is in
  :returns: a dict with "region", "namespace", "name", and "id" keys
  """
  return {
      "region": region,
      "namespace": "AWS/RDS",
      "id": instance.id,
      "name": instance.id,
  }
