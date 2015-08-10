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

"""Utility functions for AWS AutoScaling."""

import logging
import time

import boto.ec2.autoscale
from boto.exception import (AWSConnectionError, BotoServerError)
from nupic.support import decorators

from YOMP.app import config



class AutoScaleServerErrorCodes(object):
  """AutoScale server error codes of interest.

  NOTE: these MUST be the error codes as defined by AWS AutoScaling!

  See docs.aws.amazon.com/AutoScaling/latest/APIReference/CommonErrors.html
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
  AutoScaleServerErrorCodes.INTERNAL_FAILURE,
  AutoScaleServerErrorCodes.REQUEST_EXPIRED,
  AutoScaleServerErrorCodes.SERVICE_UNAVAILABLE,
  AutoScaleServerErrorCodes.THROTTLING,
)

# Default timeout for CloudWatch retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1



def retryOnAutoScalingTransientError(logger=logging.root,
                                     timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """Create a decorator for retrying a function upon AutoScale transient error.

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
    clientLabel="retryOnAutoScalingTransientError")



def getAutoScalingGroups(region, filters=None):
  """Simple generator for getting AutoScaling groups.

  :param region: the region to get groups for
  :param filters: Dictionary of filters
    See http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Filtering.html
  :returns: a generator of :class:`boto.ec2.autoscale.group.AutoScalingGroup`
      instances
  """
  awsAccessKeyId = config.get("aws", "aws_access_key_id")
  awsSecretAccessKey = config.get("aws", "aws_secret_access_key")
  conn = boto.ec2.autoscale.connect_to_region(
      region_name=region,
      aws_access_key_id=awsAccessKeyId,
      aws_secret_access_key=awsSecretAccessKey)
  names = None
  if filters:
    names = filters.get("tag:Name", None)
  for group in conn.get_all_groups(names=names):
    yield group



@retryOnAutoScalingTransientError()
def getSuggestedInstances(region, queue=None, timeout=None):
  """Gets a sequence of suggested instances with highest value first.

  This returns the ASGs in decreasing order of `desired_capacity`.

  :param region: the region to get instances for
  :param queue: an optional Queue.Queue for putting results
  :param timeout: when this time has elapsed, the function will stop fetching
      instances and format and return the results
  :returns: a list of instance dicts as formatted by :func:`formatInstance`
  """
  start = time.time()
  groups = []
  for group in getAutoScalingGroups(region):
    groups.append((group.desired_capacity, group))
    if timeout is not None and time.time() - start > timeout:
      break
  instances = (formatInstance(group, region)
               for _, group in sorted(groups, reverse=True))
  if queue:
    for instance in instances:
      queue.put(instance)
  return instances



def formatInstance(group, region):
  """Convert a boto ASG into the format to return to clients.

  :param group: instance of boto.ec2.autoscale.group.AutoScalingGroup
  :param region: the region the group is in
  :returns: a dict with "region", "namespace", "name", and "id" keys
  """
  return {
      "region": region,
      "namespace": "AWS/AutoScaling",
      "id": group.name,
      "name": group.name,
  }
