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
Integration tests for YOMP.app.runtime.aggregator_metric_collection
"""

# Suppress "access to protected member" warning
# pylint: disable=W0212

from collections import defaultdict
from datetime import datetime
import json
import logging
import math
import unittest
import uuid

import YOMP.app
import htmengine.utils

from YOMP.app import repository
from YOMP.app.repository import schema
from htmengine.repository.queries import MetricStatus

from YOMP.app.runtime.aggregator_metric_collection import \
    EC2InstanceMetricGetter, AutostackMetricRequest

from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository

from YOMP import logging_support



gLogger = logging.getLogger(__name__)


def setUpModule():
  logging_support.LoggingSupport.initTestApp()


class AggregatorMetricCollectionTestCase(unittest.TestCase):


  @classmethod
  def _createAutostackMetric(cls, autostack, name="AWS/EC2/CPUUtilization"):
    raise NotImplementedError("Boom")


  def testConstructAndClose(self):
    collector = EC2InstanceMetricGetter()
    self.assertIsNotNone(collector._processPool)

    collector.close()
    self.assertIsNone(collector._processPool)


  def testFetchInstanceCacheItemsMultipleRegions(self):
    collector = EC2InstanceMetricGetter()
    self.addCleanup(collector.close)

    filters1 = {"tag:Name": ["*"]}

    filters2 = {"tag:Name": ["?*"]}

    filters3 = {"tag:Name": ["*"], "tag:Description": ["*", "NOSUCHTHING_ZZZ"]}

    filters4 = {"tag:Name": ["*"], "tag:Description": ["NOSUCHTHING_ZZZ"]}

    autostackDescriptions = [
      ("abcdef1", "us-east-1", filters1),

      ("abcdef2", "us-west-2", filters2),

      ("abcdef3", "us-west-2", filters3),

      ("abcdef4", "us-west-2", filters4),
    ]

    result = collector._fetchInstanceCacheItems(autostackDescriptions)
    self.assertEqual(len(result), len(autostackDescriptions))

    resultMap = dict(result)

    self.assertIn("abcdef1", resultMap)
    cacheItem = resultMap.pop("abcdef1")
    self.assertEqual(cacheItem.region, "us-east-1")
    self.assertEqual(cacheItem.filters, filters1)
    self.assertGreater(len(cacheItem.instances), 0)

    self.assertIn("abcdef2", resultMap)
    cacheItem = resultMap.pop("abcdef2")
    self.assertEqual(cacheItem.region, "us-west-2")
    self.assertEqual(cacheItem.filters, filters2)
    self.assertGreater(len(cacheItem.instances), 0)

    self.assertIn("abcdef3", resultMap)
    cacheItem = resultMap.pop("abcdef3")
    self.assertEqual(cacheItem.region, "us-west-2")
    self.assertEqual(cacheItem.filters, filters3)
    self.assertGreater(len(cacheItem.instances), 0)

    self.assertIn("abcdef4", resultMap)
    cacheItem = resultMap.pop("abcdef4")
    self.assertEqual(cacheItem.region, "us-west-2")
    self.assertEqual(cacheItem.filters, filters4)
    self.assertEqual(len(cacheItem.instances), 0)


  def _addAutostack(self, **kwargs):
    details = dict(uid=str(uuid.uuid4()),
                   name=" ".join(["Generic",
                                  self.__class__.__name__,
                                  str(id(self))]),
                   region="N/A")

    details.update(kwargs)

    insert = schema.autostack.insert().values(details) # pylint: disable=E1120
    self.engine.execute(insert)
    result = self.engine.execute(
      schema.autostack.select()
                      .where(schema.autostack.c.uid == details["uid"]))


    autostackObj = type("MutableAutostack", (object,), dict(result.first().items()))()
    autostackObj.filters = json.loads(autostackObj.filters)

    return autostackObj




  def _addAutostackMetric(self, conn, autostackObj, name=None, **kwargs):
    name = name or "AWS/EC2/CPUUtilization"

    modelSpec = {"modelParams": {},
                 "datasource": "autostack",
                 "metricSpec": {"slaveDatasource": "cloudwatch" if name.startswith("AWS/EC2") else "autostack",
                                "slaveMetric": {"metric": name,
                                                "namespace": "AWS/EC2"},
                                "autostackId": autostackObj.uid}}

    metricDict = repository.addMetric(
      conn,
      datasource="autostack",
      name=name,
      description=("{0} on YOMP Autostack {1} in {2} "
                   "region").format(name, autostackObj.name, autostackObj.region),
      server="Autostacks/{0}".format(autostackObj.uid),
      location=autostackObj.region,
      tag_name=name,
      parameters=htmengine.utils.jsonEncode(modelSpec),
      poll_interval=300,
      status=MetricStatus.UNMONITORED)

    metricObj = repository.getMetric(conn, metricDict["uid"])

    repository.addMetricToAutostack(conn, autostackObj.uid, metricObj.uid)

    metricObj = type("MutableMetric", (object,), dict(metricObj.items()))()

    return metricObj


  @ManagedTempRepository(clientLabel="AggMetricCollectionTest")
  def testCollectMetricData(self):
    self.engine = repository.engineFactory(reset=True)

    with self.engine.connect() as conn:
      autostack1 = self._addAutostack(name="testCollectMetricData1",
                                      region="us-east-1",
                                      filters='{"tag:Name": ["*"]}')

      m1a = self._addAutostackMetric(conn, autostack1)
      m1b = self._addAutostackMetric(conn,
                                     autostack1,
                                     name="Autostacks/InstanceCount")

      autostack2 = self._addAutostack(name="testCollectMetricData2",
                                      region="us-west-2",
                                      filters='{"tag:Name": ["*?*"]}')

      m2 = self._addAutostackMetric(conn, autostack2)

      autostack3 = self._addAutostack(
        name="testCollectMetricData3",
        region="us-west-2",
        filters='{"tag:Name": ["NothingShouldMatchThis"]}')

      m3 = self._addAutostackMetric(conn, autostack3)

    # Collection data for both autostack/metric combinations
    collector = EC2InstanceMetricGetter()
    self.addCleanup(collector.close)

    requests = [
      AutostackMetricRequest(refID=1, autostack=autostack1, metric=m1a),
      AutostackMetricRequest(refID=2, autostack=autostack1, metric=m1b),
      AutostackMetricRequest(refID=3, autostack=autostack2, metric=m2),
      AutostackMetricRequest(refID=4, autostack=autostack3, metric=m3)
    ]

    metricCollections = dict(
      (collection.refID, collection)
      for collection in collector.collectMetricData(requests=requests))

    self.assertEqual(len(metricCollections), len(requests))


    def checkSliceSorted(records):
      sortedRecords = sorted(records, key=lambda record: record.timestamp)
      self.assertSequenceEqual(records, sortedRecords)

    def checkSliceUniqueTimestamps(records):
      timestamps = tuple(record.timestamp for record in records)
      for timestamp in timestamps:
        self.assertIsInstance(timestamp, datetime)
      self.assertItemsEqual(set(timestamps), timestamps)


    collection1 = metricCollections[1]
    collection2 = metricCollections[2]
    collection3 = metricCollections[3]
    collection4 = metricCollections[4]


    # COLLECTION-1:
    self.assertEqual(collection1.nextMetricTime, collection1.timeRange.end)
    metricGroups = defaultdict(list)
    for metricSlice in collection1.slices:
      checkSliceSorted(metricSlice.records)
      checkSliceUniqueTimestamps(metricSlice.records)
      for record in metricSlice.records:
        metricGroups[record.timestamp].append(
          (metricSlice.instanceID, record.value))

    foundValues = False
    for _timestamp, values in metricGroups.iteritems():
      if len(values) >= 0:
        #print timestamp, values[:5]
        foundValues = True
        break

    self.assertTrue(foundValues)


    # COLLECTION-2:
    self.assertEqual(collection2.nextMetricTime, collection2.timeRange.end)
    metricGroups = defaultdict(list)
    for metricSlice in collection2.slices:
      checkSliceSorted(metricSlice.records)
      checkSliceUniqueTimestamps(metricSlice.records)
      for record in metricSlice.records:
        metricGroups[record.timestamp].append(
          (metricSlice.instanceID, record.value))

    foundValues = False
    for _timestamp, values in metricGroups.iteritems():
      if len(values) >= 0:
        #print timestamp, values[:5]
        foundValues = True
        break

    self.assertTrue(foundValues)


    # COLLECTION-3:
    self.assertEqual(collection3.nextMetricTime, collection3.timeRange.end)
    metricGroups = defaultdict(list)
    metricTimestampInstanceHits = defaultdict(list)
    for metricSlice in collection3.slices:
      checkSliceSorted(metricSlice.records)
      checkSliceUniqueTimestamps(metricSlice.records)
      for record in metricSlice.records:
        metricGroups[record.timestamp].append((metricSlice.instanceID,
                                               record.value))
        metricTimestampInstanceHits[record.timestamp].append(
          metricSlice.instanceID)

    foundAlignedItems = False
    for _timestamp, values in metricGroups.iteritems():
      if len(values) > 1:
        #print timestamp, values[:5]
        foundAlignedItems = True
        break

    self.assertTrue(foundAlignedItems)

    # Make sure there were no duplicate timestamps in any one slice
    for _timestamp, instances in metricTimestampInstanceHits.iteritems():
      self.assertItemsEqual(instances, set(instances))


    # COLLECTION-4 (there should be no matching instances for it):
    self.assertEqual(len(collection4.slices), 0)
    self.assertEqual(collection4.nextMetricTime, collection4.timeRange.end)


  @ManagedTempRepository(clientLabel="AggMetricCollectionTest")
  def testCollectMetricStatistics(self):

    expectedStatisticNames = ["min", "max"]

    def validateStats(stats):
      self.assertIsInstance(stats, (list, tuple))

      timestamps = []
      for instanceMetrics in stats:
        self.assertEqual(len(instanceMetrics.records), 1)
        record = instanceMetrics.records[0]
        self.assertIsInstance(record.value, dict)
        self.assertGreater(len(record.value), 0)
        self.assertTrue(
          set(record.value.iterkeys()).issubset(expectedStatisticNames),
          msg=record.value)

        for metricValue in record.value.itervalues():
          self.assertIsInstance(metricValue, float, msg=instanceMetrics)
          self.assertFalse(math.isnan(metricValue))

        timestamps.append(record.timestamp)


      # Verify that all the stats timestamps are the same
      if timestamps:
        self.assertSequenceEqual(timestamps, [timestamps[0]] * len(timestamps))



    # Collection data for both autostack/metric combinations
    collector = EC2InstanceMetricGetter()
    self.addCleanup(collector.close)

    def _createAutostackMetric(conn, name, region, filters):
      autostackDict = repository.addAutostack(conn,
                                              name=name,
                                              region=region,
                                              filters=json.dumps(filters))

      modelSpec = {"modelParams": {},
                   "datasource": "autostack",
                   "metricSpec": {"slaveDatasource": "cloudwatch",
                                  "slaveMetric": {"metric": "CPUUtilization",
                                                  "namespace": "AWS/EC2"},
                                  "autostackId": autostackDict["uid"]}}

      metricDict = repository.addMetric(
          conn,
          datasource="autostack",
          name="CPUUtilization",
          description=("CPUUtilization on YOMP Autostack {0} in us-west-2 "
                       "region").format(name),
          server="Autostacks/{0}".format(autostackDict["uid"]),
          location=region,
          tag_name=name,
          parameters=htmengine.utils.jsonEncode(modelSpec),
          poll_interval=300,
          status=MetricStatus.UNMONITORED)

      repository.addMetricToAutostack(conn,
                                      autostackDict["uid"],
                                      metricDict["uid"])

      autostackObj = type("MutableAutostack", (object,), autostackDict)()
      autostackObj.filters = json.loads(autostackObj.filters)

      metricObj = type("MutableMetric", (object,), metricDict)()

      return autostackObj, metricObj

    # All instances in us-east-1
    engine = repository.engineFactory()
    with engine.begin() as conn:
      autostack1, m1 = (
        _createAutostackMetric(conn,
                               name="testCollectMetricStats1",
                               region="us-east-1",
                               filters={"tag:Name": ["*"]}))

      stats1 = collector.collectMetricStatistics(
        autostack=autostack1,
        metric=m1)
      print "STATS1:", stats1

      validateStats(stats1)
      self.assertGreaterEqual(len(stats1), 1)


      # All instances in us-west-2
      autostack2, m2 = _createAutostackMetric(conn,
                                              name="testCollectMetricStats2",
                                              region="us-west-2",
                                              filters={"tag:Name": ["*"]})

      stats2 = collector.collectMetricStatistics(
        autostack=autostack2,
        metric=m2)
      print "STATS2:", stats2
      validateStats(stats2)
      self.assertGreater(len(stats2), 1)


      # No matching instances in us-west-2
      autostack3, m3 = (
        _createAutostackMetric(
          conn,
          name="testCollectMetricStatistics3",
          region="us-west-2",
          filters={"tag:Name": ["NothingShouldMatchThis"]}))

      stats3 = collector.collectMetricStatistics(
        autostack=autostack3,
        metric=m3)
      print "STATS3:", stats3
      validateStats(stats3)
      self.assertEqual(len(stats3), 0)



if __name__ == '__main__':
  unittest.main()
