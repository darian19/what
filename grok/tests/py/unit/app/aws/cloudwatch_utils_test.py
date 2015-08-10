#!/usr/bin/env python
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
Unit tests for YOMP.app.aws.cloudwatch_utils
"""


import json
import logging

import unittest

from boto.exception import (AWSConnectionError, BotoServerError)

from mock import patch

from YOMP import logging_support
from YOMP.app.aws.cloudwatch_utils import retryOnCloudWatchTransientError



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



@patch.multiple("YOMP.app.aws.cloudwatch_utils",
                INITIAL_RETRY_BACKOFF_SEC=0.001)
class CloudWatchUtilsTestCase(unittest.TestCase):

  class ExitRetry(Exception):
    pass


  def testNoRetryOnUserError(self):
    # retryOnCloudWatchTransientError with no retry on user error
    accumulator = dict(value=0)

    @retryOnCloudWatchTransientError()
    def testMe():
      accumulator["value"] += 1
      raise BotoServerError(
        400,
        "",
        json.dumps(dict(Error=(dict(Code="InvalidAction")))))

    with self.assertRaises(BotoServerError):
      testMe()

    self.assertEqual(accumulator["value"], 1)


  def _testRetryCommon(self, ex):
    accumulator = dict(value=0)

    @retryOnCloudWatchTransientError(logger=logging.getLogger())
    def testMe():
      accumulator["value"] += 1

      if accumulator["value"] < 2:
        raise ex
      else:
        raise self.ExitRetry

    with self.assertRaises(self.ExitRetry):
      testMe()

    self.assertEqual(accumulator["value"], 2)


  def testRetryOnInternalFailure(self):
    # retryOnCloudWatchTransientError with retry on InternalFailure
    self._testRetryCommon(
      BotoServerError(
        500,
        "",
        json.dumps(dict(Error=(dict(Code="InternalFailure")))))
    )


  def testRetryOnRequestExpired(self):
    # retryOnCloudWatchTransientError with retry on RequestExpired
    self._testRetryCommon(
      BotoServerError(
        400,
        "",
        json.dumps(dict(Error=(dict(Code="RequestExpired")))))
    )


  def testRetryOnServiceUnavailable(self):
    # retryOnCloudWatchTransientError with retry on ServiceUnavailable
    self._testRetryCommon(
      BotoServerError(
        503,
        "",
        json.dumps(dict(Error=(dict(Code="ServiceUnavailable")))))
    )


  def testRetryOnThrottling(self):
    # retryOnCloudWatchTransientError with retry on Throttling
    self._testRetryCommon(
      BotoServerError(
        400,
        "",
        json.dumps(dict(Error=(dict(Code="Throttling")))))
    )


  def testRetryOnConnectionError(self):
    # retryOnCloudWatchTransientError with retry on AWSConnectionError
    self._testRetryCommon(AWSConnectionError("Error Message"))



if __name__ == '__main__':
  unittest.main()
