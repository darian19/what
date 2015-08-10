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

""" Unit tests for aggregator_metric_collection.py """

import datetime
import logging
import unittest

from mock import Mock

from YOMP.app.runtime.aggregator_metric_collection import (
  _MetricCollectionIterator,
  _MetricCollectionTaskResult,
  _MetricCollectionAccumulator,
  MetricCollection)

from YOMP.app.runtime import aggregator_utils



class AggregatorMetricCollectionTestCase(unittest.TestCase):


  def testEmptyDataOnFailedTask(self):
    # Test processing of failed task in _MetricCollectionIterator.next. In this
    # case, we expect the returned InstanceMetricData.records to be an empty
    # sequence

    refID = 246
    instanceID = "i-12345"

    taskResult = _MetricCollectionTaskResult(
      refID=refID,
      metricID="abc_metric_id",
      instanceID=instanceID)


    taskResult.exception = Exception("Expected: things happen!")
    taskResult.data = None


    taskResults = [taskResult]

    timeRange = aggregator_utils.TimeRange(
      datetime.datetime.utcnow(),
      datetime.datetime.utcnow())

    collectionAccumulatorMap = {
      refID: _MetricCollectionAccumulator(
        expectedNumSlices=1,
        collection=MetricCollection(
          refID=refID, slices=[], timeRange=timeRange,
          nextMetricTime=timeRange.end))
    }

    it = _MetricCollectionIterator(
      taskResultsIter=iter(taskResults),
      collectionAccumulatorMap=collectionAccumulatorMap,
      numTasks=len(taskResults),
      log=Mock(spec_set=logging.root))

    collection = it.next()

    self.assertEqual(collection.refID, refID)
    self.assertEqual(len(collection.slices), 1)
    self.assertEqual(collection.slices[0].instanceID, instanceID)
    self.assertEqual(len(collection.slices[0].records), 0)
    self.assertIsInstance(collection.slices[0].records, (tuple, list))



if __name__ == "__main__":
  unittest.main()
