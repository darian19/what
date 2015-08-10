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

"""Utility functions for AWS ELB."""

import logging
import time

import boto.ec2.elb
from boto.exception import (AWSConnectionError, BotoServerError)
from nupic.support import decorators

from YOMP.app import config



class ELBServerErrorCodes(object):
  """ELB server error codes of interest.

  NOTE: these MUST be the error codes as defined by AWS ELB!

  See http://docs.aws.amazon.com/ElasticLoadBalancing/latest/DeveloperGuide/
                                 ts-elb-http-errors.html
  for error list
  """

  # Indicates that the client cancelled the request or failed to send a full
  # request.
  REQUEST_TIMEOUT = "HTTPCode_ELB_408"  # HTTP Status Code: 408

  # Indicates that either the load balancer or the registered instances are
  # causing error.
  SERVICE_UNAVAILABLE = "HTTPCode_ELB_503"  # HTTP Status Code: 503

  # Indicates that either the load balancer or the registered instances are
  # causing error.
  GATEWAY_TIMEOUT = "HTTPCode_ELB_504"  # HTTP Status Code: 504



# Excceptions that are subject to transient-error retries
RETRY_EXCEPTIONS = (
  AWSConnectionError,
  BotoServerError,
)



# BotoServerError error codes that are subject to transient-error retries
RETRIABLE_SERVER_ERROR_CODES = (
  ELBServerErrorCodes.REQUEST_TIMEOUT,
  ELBServerErrorCodes.SERVICE_UNAVAILABLE,
  ELBServerErrorCodes.GATEWAY_TIMEOUT,
)

# Default timeout for CloudWatch retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1



def retryOnELBTransientError(logger=logging.root,
                             timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """ Create a decorator for retrying a function upon ELB transient error.

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
    clientLabel="retryOnELBTransientError")



def getELBInstances(region):
  """Simple generator for getting ELB instances.

  :param region: the region to get instances for
  :returns: a generator of :class:`boto.ec2.elb.load_balancer.LoadBalancer`
      instances
  """
  awsAccessKeyId = config.get("aws", "aws_access_key_id")
  awsSecretAccessKey = config.get("aws", "aws_secret_access_key")
  conn = boto.ec2.elb.connect_to_region(
      region_name=region,
      aws_access_key_id=awsAccessKeyId,
      aws_secret_access_key=awsSecretAccessKey)
  for loadBalancer in conn.get_all_load_balancers():
    yield loadBalancer



@retryOnELBTransientError()
def getSuggestedInstances(region, queue=None, timeout=None):
  """Gets a sequence of suggested instances with highest value first.

  This returns the ELBs in decreasing order of number of member EC2 instances.

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
  loadBalancers = []
  for loadBalancer in getELBInstances(region):
    numInstances = len(loadBalancer.instances)
    loadBalancers.append((numInstances, loadBalancer))
    if timeout is not None and time.time() - start > timeout:
      break
  instances = (formatInstance(loadBalancer, region)
               for _, loadBalancer in sorted(loadBalancers, reverse=True))
  if queue:
    for instance in instances:
      queue.put(instance)
  return instances



def formatInstance(loadBalancer, region):
  """Convert a boto load balancer into the format to return to clients.

  :param loadBalancer: instance of boto.ec2.elb.loadbalancer.LoadBalancer
  :param region: the region the load balancer is in
  :returns: a dict with "region", "namespace", "name", and "id" keys
  """
  return {
      "region": region,
      "namespace": "AWS/ELB",
      "id": loadBalancer.name,
      "name": loadBalancer.name,
  }
