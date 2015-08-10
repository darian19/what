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

"""Utility functions for AWS Opsworks."""

import logging

from boto.exception import (AWSConnectionError, BotoServerError)
from nupic.support import decorators


class OpsWorksClientErrorCodes(object):
  """OpsWorks client error codes of interest.

  These all use 400-series HTTP status codes

  NOTE: these MUST be the error codes as defined by AWS OpsWorks!

  See http://docs.aws.amazon.com/opsworks/latest/APIReference/CommonErrors.html
  for error list
  """

  # The request reached the service more than 15 minutes after the date stamp
  # on the request or more than 15 minutes after the request expiration date
  # (such as for pre-signed URLs), or the date stamp on the request is more
  # than 15 minutes in the future.
  REQUEST_EXPIRED = "RequestExpired"

  # The request was denied due to request throttling.
  THROTTLING = "Throttling"

class OpsWorksServerErrorCodes(object):
  """OpsWorks server error codes of interest.

  These all use 500-series HTTP status codes

  NOTE: these MUST be the error codes as defined by AWS OpsWorks!

  See http://docs.aws.amazon.com/opsworks/latest/APIReference/CommonErrors.html
  for error list
  """

  # The request processing has failed because of an unknown error, exception
  # or failure.
  INTERNAL_FAILURE = "InternalFailure"

  # The request has failed due to a temporary failure of the server.
  SERVICE_UNAVAILABLE = "ServiceUnavailable"


# Excceptions that are subject to transient-error retries
RETRY_EXCEPTIONS = (
  AWSConnectionError,
  BotoServerError,
)

# BotoServerError error codes that are subject to transient-error retries
RETRIABLE_ERROR_CODES = (
  OpsWorksClientErrorCodes.REQUEST_EXPIRED,
  OpsWorksClientErrorCodes.THROTTLING,

  OpsWorksServerErrorCodes.INTERNAL_FAILURE,
  OpsWorksServerErrorCodes.SERVICE_UNAVAILABLE
)

# Default timeout for EC2 retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1

def retryOnOpsworksTransientError(logger=logging.root,
                             timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """Create a decorator for retrying a function upon OpsWorks transient error.

  :param logger: a python logger object for logging failures; defaults to the
      builtin root logger

  :param timeoutSec: How many seconds from time of initial call to stop
    retrying
  :type timeoutSec: floating point

  :returns: a decorator
  """

  def retryFilter(e, *_args, **_kwargs):
    """Return True to permit a retry, false to re-raise the exception."""
    if isinstance(e, BotoServerError):
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
    clientLabel="retryOnOpsWorksTransientError")
