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
Unit tests for htmengine.runtime.metric_streamer_util
"""

# Disable pylint warning "Access to a protected member"
# pylint: disable=W0212


from datetime import datetime, timedelta
import unittest

from mock import Mock, patch

from htmengine.runtime import metric_streamer_util
from htmengine.model_swapper import model_swapper_interface


class MetricStreamerTestCase(unittest.TestCase):


  @patch.object(metric_streamer_util, "repository", autospec=True)
  def testScrubDataSamplesOutOfOrder(self, _repositoryMock):
    streamer = metric_streamer_util.MetricStreamer()

    now = datetime.utcnow()

    getTailMetricRowTimestampPatch = patch.object(
      streamer, "_getTailMetricRowTimestamp", autospec=True,
      return_value=now)

    oneInterval = timedelta(seconds=300)

    taintedSamples = [
      (now - oneInterval, -1.0),
      (now + oneInterval * 1, 2.0),
      (now, -3.0),
      (now, -3.0),
      (now + oneInterval * 2, 4.0),
      (now + oneInterval * 2, -4.0),
      (now + oneInterval * 3, 5.0),
    ]

    expectedPassingSamples = [
      (now + oneInterval * 1, 2.0),
      (now + oneInterval * 2, 4.0),
      (now + oneInterval * 3, 5.0)
    ]

    with getTailMetricRowTimestampPatch:
      passingData = streamer._scrubDataSamples(
        data=taintedSamples,
        metricID=Mock(name="MetricID"),
        conn=Mock(name="SqlalchemyConnection"),
        lastDataRowID=Mock(name="lastDataRowID")
      )

    self.assertSequenceEqual(passingData, expectedPassingSamples)


  def testSendInputRowsToModel(self):
    """ Test MetricStreamer._sendInputRowsToModel """
    metricDataOutputChunkSize = metric_streamer_util.config.getint(
        "metric_streamer", "chunk_size")


    now = datetime.utcnow()

    expectedBatch1 = [
      model_swapper_interface.ModelInputRow(
        rowID=1+i,
        data=(now + timedelta(seconds=60*i), i,))
      for i in xrange(metricDataOutputChunkSize)
    ]

    expectedBatch2 = [
      model_swapper_interface.ModelInputRow(
        rowID=1+i,
        data=(now + timedelta(seconds=60 * i), i,))
      for i in xrange(i + 1, metricDataOutputChunkSize + i + 1)
    ]

    expectedBatch3 = [
      model_swapper_interface.ModelInputRow(
        rowID=1+i,
        data=(now + timedelta(seconds=60 * i), i,))
      for i in xrange(i + 1, metricDataOutputChunkSize // 2 + i + 1)
    ]

    inputRows = expectedBatch1 + expectedBatch2 + expectedBatch3

    modelSwapper = Mock(
      spec_set=model_swapper_interface.ModelSwapperInterface)

    metricID = "abcdef"

    streamer = metric_streamer_util.MetricStreamer()

    streamer._sendInputRowsToModel(
      inputRows=inputRows,
      metricID=metricID,
      modelSwapper=modelSwapper)

    self.assertEqual(modelSwapper.submitRequests.call_count, 3)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[0][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[0][0][1],
      expectedBatch1)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[1][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[1][0][1],
      expectedBatch2)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[2][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[2][0][1],
      expectedBatch3)

    # And one more time with just one input row
    modelSwapper = Mock(
      spec_set=model_swapper_interface.ModelSwapperInterface)

    streamer._sendInputRowsToModel(
      inputRows=inputRows[:1],
      metricID=metricID,
      modelSwapper=modelSwapper)

    self.assertEqual(modelSwapper.submitRequests.call_count, 1)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[0][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[0][0][1],
      inputRows[:1])


  def testSendInputRowsToModelModelNotFoundError(self):
    """ Test MetricStreamer._sendInputRowsToModel with ModelNotFound error
    from ModelSwapperInterface.submitRequests
    """
    metricDataOutputChunkSize = metric_streamer_util.config.getint(
        "metric_streamer", "chunk_size")

    now = datetime.utcnow()

    inputRows = [
      model_swapper_interface.ModelInputRow(
        rowID=1+i,
        data=(now + timedelta(seconds=60*i), i,))
      for i in xrange(metricDataOutputChunkSize * 3)
    ]

    modelSwapper = Mock(
      spec_set=model_swapper_interface.ModelSwapperInterface)

    modelSwapper.submitRequests.side_effect = (
      model_swapper_interface.ModelNotFound)

    metricID = "abcdef"

    streamer = metric_streamer_util.MetricStreamer()

    streamer._sendInputRowsToModel(
      inputRows=inputRows,
      metricID=metricID,
      modelSwapper=modelSwapper)

    self.assertEqual(modelSwapper.submitRequests.call_count, 1)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[0][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[0][0][1],
      inputRows[:metricDataOutputChunkSize])


  def testSendInputRowsToModelSubmitRequestsOtherError(self):
    """ Test MetricStreamer._sendInputRowsToModel with error other than
    ModelNotFound from ModelSwapperInterface.submitRequests
    """
    metricDataOutputChunkSize = metric_streamer_util.config.getint(
        "metric_streamer", "chunk_size")

    now = datetime.utcnow()

    inputRows = [
      model_swapper_interface.ModelInputRow(
        rowID=1+i,
        data=(now + timedelta(seconds=60*i), i,))
      for i in xrange(metricDataOutputChunkSize * 3)
    ]

    class OtherError(Exception):
      pass

    modelSwapper = Mock(
      spec_set=model_swapper_interface.ModelSwapperInterface)

    modelSwapper.submitRequests.side_effect = OtherError

    metricID = "abcdef"

    streamer = metric_streamer_util.MetricStreamer()

    with self.assertRaises(OtherError):
      streamer._sendInputRowsToModel(
        inputRows=inputRows,
        metricID=metricID,
        modelSwapper=modelSwapper)

    self.assertEqual(modelSwapper.submitRequests.call_count, 1)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[0][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[0][0][1],
      inputRows[:metricDataOutputChunkSize])

    # And one more with just one row
    modelSwapper = Mock(
      spec_set=model_swapper_interface.ModelSwapperInterface)

    modelSwapper.submitRequests.side_effect = OtherError

    with self.assertRaises(OtherError):
      streamer._sendInputRowsToModel(
        inputRows=inputRows[:1],
        metricID=metricID,
        modelSwapper=modelSwapper)

    self.assertEqual(modelSwapper.submitRequests.call_count, 1)

    self.assertEqual(modelSwapper.submitRequests.call_args_list[0][0][0],
                     metricID)
    self.assertSequenceEqual(
      modelSwapper.submitRequests.call_args_list[0][0][1],
      inputRows[:1])



if __name__ == '__main__':
  unittest.main()
