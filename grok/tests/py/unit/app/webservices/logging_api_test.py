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

"""Unit tests for the logging API."""

# pylint: disable=W0212

import unittest

from mock import patch, mock_open, call, Mock
import datetime
import fcntl
import web
import os.path

from htmengine import utils
from YOMP.app import repository
from YOMP.app.repository.queries import MetricStatus
from YOMP.app.webservices import logging_api



class AndroidHandlerTest(unittest.TestCase):


  @patch.object(os.path, "isfile")
  @patch.object(web, "data")
  def testPOST(self, dataMock, isfileMock):
    # Set up mocking

    isfileMock.return_value = True

    # Mock the request POST data
    dataMock.return_value = ('[{"timestamp":"1393310538",'
      '"deviceID":"DEVICE_ID=6cdb56113bc772e9","eventType":"INFO",'
      '"message":"APP_VERSION=1.1.1-dev OS_VERSION=4.3 SDK_VERSION=18 '
      'OS_BUILD=JSS15J DEVICE=Android SDK built for x86-unknown(generic_x86) '
      'SERIAL=unknown Service started","tag":"YOMPService"}]')

    openMock = mock_open()

    timestamp = datetime.datetime.fromtimestamp(1393310538).isoformat()

    # Call the POST function
    with patch.object(logging_api, 'open', openMock, create=True):
      openMock.name = logging_api._LOG_FORMAT_ANDROID
      with patch.object(fcntl, 'flock') as fcntlMock:
        response = logging_api.AndroidHandler.POST()

    # Verify results
    dataMock.assert_called_once()
    openMock.assert_called_with(logging_api._LOG_FORMAT_ANDROID, "a")
    handle = openMock()
    handle.write.assert_called_once_with("%s [INFO] "
      "[YOMPService] MOBILE.ANDROID.DEVICE_ID=6cdb56113bc772e9 "
      "APP_VERSION=1.1.1-dev OS_VERSION=4.3 SDK_VERSION=18 OS_BUILD=JSS15J "
      "DEVICE=Android SDK built for x86-unknown(generic_x86) SERIAL=unknown "
      "Service started\n" % timestamp)
    fcntlMock.assert_has_calls([call(handle, fcntl.LOCK_EX),
      call(handle, fcntl.LOCK_UN)])
    self.assertEqual(response, None)



class FeedbackHandlerTest(unittest.TestCase):

  @patch.object(repository, "engineFactory")
  @patch.object(repository, "getMetricData")
  @patch.object(repository, "getMetric")
  @patch.object(logging_api.FeedbackHandler, "_uploadTarfile")
  @patch.object(web, "data")
  def testPOST(self, dataMock, uploadTarfileMock, getMetricMock,
               getMetricDataMock, _engineFactoryMock):
    # Set up mocking

    uploadTarfileMock.return_value = "s3_key"

    metricId = utils.createGuid()

    metric = Mock(uid=metricId,
                  description="My Metric Description",
                  server="My Server",
                  location="My Location",
                  datasource="My Datasource",
                  poll_interval=60,
                  parameters="{}",
                  last_timestamp=None,
                  status=MetricStatus.ACTIVE,
                  message=None,
                  collector_error=None,
                  tag_name=None,
                  model_params=None,
                  last_rowid=0)
    metric.name = "My Metric Name"

    # Mock the request POST data
    dataMock.return_value = '{"uid": "%s"}' % metricId

    # Return metric from mocked repository.getMetric()
    getMetricMock.return_value = metric

    getMetricDataMock.return_value = []

    # Call the POST function
    response = logging_api.FeedbackHandler.POST()

    # Verify results
    dataMock.assert_called_once()
    uploadTarfileMock.assert_called_once()
    self.assertEqual(response, "s3_key")



if __name__ == "__main__":
  unittest.main()
