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

"""Utilities for AWS CloudWatch."""

import datetime
import logging

from boto.exception import (AWSConnectionError, BotoServerError)

from nupic.support import decorators

from htmengine.utils import roundUpDatetime



# AWS CloudWatch returns error if number of returned data records would
# exceed 1,440
_CLOUDWATCH_MAX_DATA_RECORDS = 1440

# AWS CloudWatch only keeps 2 weeks worth of data. Limit range to 14 days
_CLOUDWATCH_DATA_MAX_STORAGE_TIMEDELTA = datetime.timedelta(days=14)



class CloudWatchServerErrorCodes(object):
  """ CloudWatch Server error codes of interest

  NOTE: these MUST be the error codes as defined by AWS CloudWatch!

  See docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/CommonErrors.html
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
  CloudWatchServerErrorCodes.INTERNAL_FAILURE,
  CloudWatchServerErrorCodes.REQUEST_EXPIRED,
  CloudWatchServerErrorCodes.SERVICE_UNAVAILABLE,
  CloudWatchServerErrorCodes.THROTTLING,
)

# Default timeout for CloudWatch retries
DEFAULT_RETRY_TIMEOUT_SEC = 10

INITIAL_RETRY_BACKOFF_SEC = 0.75

MAX_RETRY_BACKOFF_SEC = 1



def retryOnCloudWatchTransientError(logger=logging.root,
                                    timeoutSec=DEFAULT_RETRY_TIMEOUT_SEC):
  """ Create a decorator for retrying a function upon CloudWatch transient
  error.

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



def getMetricCollectionBackoffSeconds(period):
  """ Return the number of seconds to subtract from current time in order to
  determine the end of metric retrieval period.

  :param period: Metric period in seconds; must be multiple of 60
  :type period: integer
  """
  # NOTE: this must be coordinated with
  # repository._getCloudwatchMetricReadinessPredicate()

  # Metrics in CloudWatch don't appear to be aligned on any specific time
  # boundary and there is presently no API to introspect their alignment.
  # Also, metric data for 5-minute metrics appears to become readable 5
  # minutes after the end of the given time "bucket".

  # This corresponds to the number of seconds from the end time of the metric
  # value's time bucket for the metric value to become available and stabilize
  return period + 60



def getMetricCollectionTimeRange(startTime, endTime, period):
  """
  :param startTime: UTC start time of planned metric data collection; may be
    None when called for the first time, in which case a start time will be
    calculated and returned in the result (even if there is not enough time for
    at least one period of metric data collection)
  :type startTime: datetime.datetime

  :param endTime: UTC end time of the metric data range. The end value is
    exclusive; results will include datapoints predating the end time. If set to
    None, will base the resulting end time on the current UTC time
  :type endTime: datetime.datetime

  :param period: Metric aggregation period in seconds; must be multiple of 60
  :type period: integer

  :returns: time range for collecting metrics adjusted for integral number of
    periods. If there is not enough time for at least one period, then end-time
    will be set equal to start-time
  :rtype: two-tuple of datetime.datetime values, where the first element is the
    start time and the second element is the end time of the range
  """
  now = datetime.datetime.utcnow()

  if startTime is None:
    # AWS CloudWatch only keeps 2 weeks worth of data. Limit range to 14 days
    startTime = now - _CLOUDWATCH_DATA_MAX_STORAGE_TIMEDELTA
    # Round up start time to the nearest period to align time buckets between
    # different metrics
    startTime = roundUpDatetime(startTime, period)

  # Metrics in CloudWatch don't appear to be aligned on any specific time
  # boundary and there is presently no API to introspect their alignment.
  if endTime is None:
    endTime = (
      now -
      datetime.timedelta(seconds=getMetricCollectionBackoffSeconds(period)))

  numPeriods = min(
    (endTime - startTime).total_seconds() // period,
    _CLOUDWATCH_MAX_DATA_RECORDS)

  if numPeriods > 0:
    # Truncate end-time by the number of expected periods
    endTime = startTime + datetime.timedelta(seconds=numPeriods * period)
  else:
    endTime = startTime

  return startTime, endTime
