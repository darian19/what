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

"""Utility functions for AWS EC2."""

import calendar
import datetime
import logging
import time

import boto
import boto.ec2

from nupic.support import decorators

from YOMP.app import config
import YOMP.app.exceptions

# Instances sizes as of May 1, 2014 for us-east-1
INSTANCE_SIZES = {
    # Current Generation
    # General Purpose
    "m3.medium":   0.070,
    "m3.large":    0.140,
    "m3.xlarge":   0.280,
    "m3.2xlarge":  0.560,
    # Compute Optimized
    "c3.large":    0.105,
    "c3.xlarge":   0.210,
    "c3.2large":   0.420,
    "c3.4large":   0.840,
    "c3.8large":   1.680,
    # GPU Instances
    "g2.2xlarge":  0.650,
    # Memory Optimized
    "r3.large":    0.175,
    "r3.xlarge":   0.350,
    "r3.2xlarge":  0.700,
    "r3.4xlarge":  1.400,
    "r3.8xlarge":  2.800,
    # Storage Optimized
    "i2.xlarge":   0.853,
    "i2.2xlarge":  1.705,
    "i2.4xlarge":  3.410,
    "i2.8xlarge":  6.820,
    "hs1.8xlarge": 4.600,
    # Micro and Small
    "t1.micro":    0.020,
    "m1.small":    0.044,

    # Previous Generation
    # General Purpose
    #"m1.small":    0.044,  # redundant
    "m1.medium":   0.087,
    "m1.large":    0.175,
    "m1.xlarge":   0.350,
    # Compute Optimized
    "c1.medium":   0.130,
    "c1.xlarge":   0.520,
    "cc2.8xlarge": 2.000,
    # GPU Instances
    "cg1.4xlarge": 2.100,
    # Memory Optimized
    "m2.xlarge":   0.245,
    "m2.2xlarge":  0.490,
    "m2.4xlarge":  0.980,
    "cr1.8xlarge": 3.500,
    # Storage Optimized
    "hi1.4xlarge": 3.100,
}



class EC2ClientErrorCodes(object):
  """EC2 client error codes of interest.

  These all use 400-series HTTP status codes

  NOTE: these MUST be the error codes as defined by AWS EC2!

  See http://docs.aws.amazon.com/AWSEC2/latest/APIReference/api-error-codes.html
  for error list
  """

  # The difference between the request timestamp and the AWS server time is
  # greater than 5 minutes. Ensure that your system clock is accurate and
  # configured to use the correct time zone.
  REQUEST_HAS_EXPIRED = "InvalidSecurity.RequestHasExpired"

  # You've reached the limit on your IOPS usage for that region. If you need to
  # increase your volume limit, complete the Amazon EC2 EBS Volume Limit Form.
  MAX_IOPS_LIMIT_EXCEEDED = "MaxIOPSLimitExceeded"

  # The maximum request rate permitted by the Amazon EC2 APIs has been exceeded
  # for your account. For best results, use an increasing or variable sleep
  # interval between requests. For more information, see Query API Request Rate.
  REQUEST_LIMIT_EXCEEDED = "RequestLimitExceeded"



class EC2ServerErrorCodes(object):
  """EC2 server error codes of interest.

  These all use 500-series HTTP status codes

  NOTE: these MUST be the error codes as defined by AWS EC2!

  See http://docs.aws.amazon.com/AWSEC2/latest/APIReference/api-error-codes.html
  for error list
  """

  # An internal error has occurred. Retry your request, but if the problem
  # persists, contact us with details by posting a message on the AWS forums.
  INTERNAL_ERROR = "InternalError"

  # The server is overloaded and can't handle the request.
  UNAVAILABLE = "Unavailable"



# Excceptions that are subject to transient-error retries
RETRY_EXCEPTIONS = (
  boto.exception.AWSConnectionError,
  boto.exception.BotoServerError,
)



# BotoServerError error codes that are subject to transient-error retries
RETRIABLE_ERROR_CODES = (
  EC2ClientErrorCodes.REQUEST_HAS_EXPIRED,
  EC2ClientErrorCodes.MAX_IOPS_LIMIT_EXCEEDED,
  EC2ClientErrorCodes.REQUEST_LIMIT_EXCEEDED,

  EC2ServerErrorCodes.INTERNAL_ERROR,
  EC2ServerErrorCodes.UNAVAILABLE,
)

# Default timeout for EC2 retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1



def retryOnEC2TransientError(logger=logging.root,
                             timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """Create a decorator for retrying a function upon EC2 transient error.

  :param logger: a python logger object for logging failures; defaults to the
      builtin root logger

  :param timeoutSec: How many seconds from time of initial call to stop retrying
  :type timeoutSec: floating point

  :returns: a decorator
  """

  def retryFilter(e, *_args, **_kwargs):
    """Return True to permit a retry, false to re-raise the exception."""
    if isinstance(e, boto.exception.BotoServerError):
      if getattr(e, "error_code", "") in RETRIABLE_ERROR_CODES:
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
    clientLabel="retryOnEC2TransientError")



def getEC2Instances(region, filters=None):
  """Simple generator for getting EC2 instances.

  :param region: the region to get instances for
  :param filters: Dictionary of filters
    See http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Filtering.html
  :returns: a generator of :class:`boto.ec2.instance.Instance` instances
  """
  awsAccessKeyId = config.get("aws", "aws_access_key_id")
  awsSecretAccessKey = config.get("aws", "aws_secret_access_key")
  conn = boto.ec2.connect_to_region(region_name=region,
                                    aws_access_key_id=awsAccessKeyId,
                                    aws_secret_access_key=awsSecretAccessKey)
  for reservation in conn.get_all_reservations(filters=filters):
    for instance in reservation.instances:
      yield instance



@retryOnEC2TransientError()
def getSuggestedInstances(region, queue=None, timeout=None):
  """Gets a sequence of suggested instances with highest value first.

  This returns the running EC2 instances in decreasing order first by instance
  cost and then by time since launch.

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
  for instance in getEC2Instances(region):
    if instance.state != "running":
      if timeout is not None and time.time() - start > timeout:
        break
      continue
    instanceSize = INSTANCE_SIZES.get(instance.instance_type, 0.0)
    launchDT = datetime.datetime.strptime(
        instance.launch_time.rstrip("Z"), "%Y-%m-%dT%H:%M:%S.%f")
    launchTimestamp = calendar.timegm(launchDT.utctimetuple())
    uptime = time.time() - launchTimestamp
    instances.append((instanceSize, uptime, instance))
    if timeout is not None and time.time() - start > timeout:
      break
  instances = (formatInstance(instance)
               for _, _, instance in sorted(instances, reverse=True))
  if queue:
    for instance in instances:
      queue.put(instance)
  return instances



def formatInstance(instance):
  """Convert a boto EC2 instance into the format to return to clients.

  :param instance: instance of boto.ec2.instance.Instance
  :returns: a dict with "region", "namespace", "name", and "id" keys
  """
  return {
      "region": instance.region.name,
      "namespace": "AWS/EC2",
      "id": instance.id,
      "name": instance.tags.get("Name", instance.id),
  }



def checkEC2Authorization(awsAccessKeyID, awsSecretAccessKey):
  """ Perform EC2 authorization check

  :param awsAccessKeyID: AWS key id
  :param awsSecretAccessKey: AWS secret key

  :raises YOMP.app.exceptions.AuthFailure:
  :raises YOMP.app.exceptions.AWSPermissionsError:
  """
  # NOTE: this function was salvaged from legacy cloudwatch adapter
  conn = boto.ec2.connection.EC2Connection(awsAccessKeyID, awsSecretAccessKey)
  try:
    conn.get_all_regions()
    return True
  except boto.exception.EC2ResponseError as e:
    if (e.error_code == "AuthFailure" or
        e.error_code == "SignatureDoesNotMatch"):
      raise YOMP.app.exceptions.AuthFailure(e.message)
    raise YOMP.app.exceptions.AWSPermissionsError(
        "IAM credentials don't have correct permissions. Please use read-only "
        "permissions as described here: "
        "http://www.numenta.com/assets/pdf/YOMP/resources/1.3/"
        "Generate-Restrictive-Credentials.pdf")
