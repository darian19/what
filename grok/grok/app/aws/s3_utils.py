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

"""Utilities for AWS S3."""

import logging
import socket

from boto.exception import (AWSConnectionError, BotoServerError,
                            S3CreateError, S3DataError, S3ResponseError)

from nupic.support import decorators

DEFAULT_RETRY_TIMEOUT_SEC = 20.0



class S3ServerErrorCodes(object):
  """ S3 Server error codes of interest.

  NOTE: these MUST be the error codes as defined by S3!

  See http://docs.amazonwebservices.com/AmazonS3/latest/API/ for error list (
  under Error Respones at the time of this writing)
  """

  # We encountered an internal error. Please try again.
  INTERNAL_ERROR = "InternalError"

  # The specified bucket does not exist
  NO_SUCH_BUCKET = "NoSuchBucket"

  # S3ResponseError: The bucket you tried to delete is not empty
  BUCKET_NOT_EMPTY = "BucketNotEmpty"

  # The specified key does not exist
  NO_SUCH_KEY = "NoSuchKey"

  # Invalid Argument
  INVALID_ARG = "InvalidArgument"

  # Your previous request to create the named bucket succeeded and you
  # already own it
  BUCKET_ALREADY_OWNED_BY_YOU = "BucketAlreadyOwnedByYou"

  # A conflicting conditional operation is currently in progress against this
  # resource. Please try again.
  OPERATION_ABORTED = "OperationAborted"

  # Please reduce your request rate
  SERVICE_UNAVAILABE = "ServiceUnavailable"

  # Please reduce your request rate
  SLOW_DOWN = "SlowDown"


# TODO: add throttling to retriable support (SLOW_DOWN and SERVICE_UNAVAILABE)

RETRIABLE_SERVER_ERROR_CODES = [
    S3ServerErrorCodes.OPERATION_ABORTED,
    S3ServerErrorCodes.INTERNAL_ERROR,
]




def retryOnBotoS3TransientError(getLoggerCallback=logging.getLogger,
                                timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """Return a decorator for retrying a boto S3 function on transient failures.

  NOTE: please ensure that the operation being retried is idempotent.

  getLoggerCallback:
                    user-supplied callback function that takes no args and
                     returns the logger instance to use for logging.
  timeoutSec:       How many seconds from time of initial call to stop retrying
                     (floating point)
  """

  def retryFilter(e, args, kwargs):
    """Return True to permit a retry, false to re-raise the exception."""
    if isinstance(e, BotoServerError):
      if (getattr(e, "error_code", "") in RETRIABLE_SERVER_ERROR_CODES):
        return True
      else:
        return False

    return True


  retryExceptions = tuple([
    socket.error,
    AWSConnectionError,
    S3DataError,
    S3CreateError,
    S3ResponseError,
  ])

  return decorators.retry(
    timeoutSec=timeoutSec, initialRetryDelaySec=0.1, maxRetryDelaySec=10,
    retryExceptions=retryExceptions, retryFilter=retryFilter,
    getLoggerCallback=getLoggerCallback,
    clientLabel="retryOnBotoS3TransientError")
