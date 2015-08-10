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

# This script implements an extension of the unittest2.TestCase class to be
# used as a base class unit tests

import sys
import functools
import json
import socket
import time
import logging

import unittest

from htmengine import repository
from htmengine.adapters.datasource import createDatasourceAdapter
from htmengine.exceptions import MetricAlreadyMonitored
from htmengine.model_checkpoint_mgr import model_checkpoint_mgr
from htmengine.repository import schema
from htmengine.repository.queries import MetricStatus
import htmengine.exceptions as app_exceptions



LOGGER = logging.getLogger(__name__)



def retry(duration=15, delay=0.5, exceptionTypes=(AssertionError,)):
  """Decorator for assertion function may take some time to become true.

  This takes the total duration to wait and the delay to wait between attempts
  at running a function and returns a decorator that will run the function
  until duration has elapsed or it returns without an AssertionError. If the
  duration is reached, the most recent error is re-raised.
  """
  def retryDecorator(f):
    @functools.wraps(f)
    def newFunc(*args, **kwargs):
      deadline = time.time() + duration
      et, ei, tb = None, None, None
      i = 0
      while time.time() < deadline:
        i += 1
        try:
          firstLine = (f.__doc__ or "").strip().split("\n")[0]
          LOGGER.info("Attempt %i of %s: %s", i, f.__name__, firstLine)
          response = f(*args, **kwargs)
          return response
        except exceptionTypes:
          et, ei, tb = sys.exc_info()
          time.sleep(delay)
      # If we hit the deadline, re-raise the last error seen
      raise et, ei, tb
    return newFunc
  return retryDecorator



class TestCaseBase(unittest.TestCase):
  """
  This class adds additional methods useful for specific testing scenarios
  in htmengine test suites.
  """

  # NOTE: Derived class must override this with the valid config before
  # calling methods of this class that may need it.
  config = None


  def __init__(self, *args, **kwargs):

    # Construct the base-class instance
    super(TestCaseBase, self).__init__(*args, **kwargs)


  @property
  def __config(self):
    if self.config is None:
      raise ValueError("Did %r forget to set config member variable " % (
                       self,))
    return self.config


  def _deleteMetric(self, metricName):
    adapter = createDatasourceAdapter("custom")
    adapter.deleteMetricByName(metricName)


  def _deleteModel(self, metricId):
    adapter = createDatasourceAdapter("custom")
    adapter.unmonitorMetric(metricId)


  def _createModel(self, nativeMetric):
    adapter = createDatasourceAdapter("custom")
    try:
      metricId = adapter.monitorMetric(nativeMetric)
    except MetricAlreadyMonitored as e:
      metricId = e.uid

    engine = repository.engineFactory(config=self.config)

    with engine.begin() as conn:
      return repository.getMetric(conn, metricId)


  def fastCheckSequenceEqual(self, seq1, seq2):
    """ Check that two sequences (lists or tuples) are equal.

    NOTE: at the time of this writing, python 2.7 unittest's
    assertEqual and assertSequenceEqual took too long to compute the difference
    on even moderately long sequences (e.g., two lists of 4000 rows each with 1
    short string and 4 float/int elements per row took about an hour to complete
    on a recent model development MacBookPro). See
    http://bugs.python.org/review/19217/ "Calling assertEquals for moderately
    long list takes too long"
    """
    self.assertEqual(len(seq1), len(seq2))

    for i in xrange(len(seq1)):
      assert seq1[i] == seq2[i], (
        "seq1 != seq2; First difference at index=%s: %r != %r" %
        (i, seq1[i], seq2[i]))


  @retry(duration=45, delay=1)
  def checkModelIsActive(self, uid):
    engine = repository.engineFactory(config=self.__config)
    with engine.begin() as conn:
      metricObj = repository.getMetric(conn,
                                       uid,
                                       fields=[schema.metric.c.status])

    self.assertEqual(metricObj.status, MetricStatus.ACTIVE)


  @retry(duration=30, delay=1)
  def checkMetricUnmonitoredById(self, uid):
    engine = repository.engineFactory(config=self.__config)
    with engine.begin() as conn:
      metricObj = repository.getMetric(conn,
                                       uid,
                                       fields=[schema.metric.c.status,
                                               schema.metric.c.parameters])

    self.assertEqual(metricObj.status, MetricStatus.UNMONITORED)
    self.assertIsNone(metricObj.parameters)

    with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
      model_checkpoint_mgr.ModelCheckpointMgr().loadModelDefinition(uid)


  @retry()
  def checkStats(self, metricName, mn, mx):
    """Check that stats are computed correctly from the database"""
    engine = repository.engineFactory(config=self.__config)
    with engine.begin() as conn:
      metricObj = (
        repository.getCustomMetricByName(conn,
                                         metricName,
                                         fields=[schema.metric.c.uid,
                                                 schema.metric.c.parameters]))
      stats = repository.getMetricStats(conn, metricObj.uid)

    self.assertSetEqual(set(stats.keys()), set(("min", "max")))
    self.assertAlmostEqual(stats["min"], mn)
    self.assertAlmostEqual(stats["max"], mx)


  @retry()
  def checkEncoderResolution(self, uid, minVal, maxVal, minResolution=None):
    """Check that encoder resolution is computed correctly."""
    engine = repository.engineFactory(config=self.__config)
    with engine.begin() as conn:
      metricObj = repository.getMetric(conn,
                                       uid,
                                       fields=[schema.metric.c.name,
                                               schema.metric.c.model_params])

    modelParams = json.loads(metricObj.model_params)
    self.assertNotEqual(modelParams, None,
                        "No model exists for metric %s" % metricObj.name)
    sensorParams = modelParams["modelConfig"]["modelParams"]["sensorParams"]
    encoderParams = sensorParams["encoders"]["c1"]
    # Estimate and check the bounds for the resolution based on min and max
    lower = (maxVal - minVal) / 300.0
    upper = (maxVal - minVal) / 80.0

    if minResolution is not None:
      lower = max(minResolution, lower)
      upper = float("inf")

    resolution = encoderParams["resolution"]

    self.assertGreaterEqual(resolution, lower)
    self.assertLessEqual(resolution, upper)


  @retry(duration=25)
  def checkModelDeleted(self, uid):
    """Check that the model has been deleted"""

    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      try:
        metric = repository.getMetric(conn, uid)
        raise Exception("Metric not deleted as expected")
      except app_exceptions.ObjectNotFoundError:
        pass

      models = repository.getAllModels(conn)
      for model in models:
        self.assertNotEqual(model.uid, uid,
                            "Model showing up after deletion.")

    with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
      model_checkpoint_mgr.ModelCheckpointMgr().loadModelDefinition(uid)


  @retry(duration=100, delay=1)
  def checkModelResultsSize(self, uid, size, atLeast=False):
    """Check that the number of results for metric uid matches size.

    This is not compatible with ManagedTempRepository since it makes an HTTP
    request that may be outside the temp repository process tree.

    :param uid: the uid of the metric to check results for
    :param size: the expected number of results
    :param atLeast: if True, checks for at least that many results; if False,
      checks for exact match of the result count; defaults to False
    """
    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      result = repository.getMetricData(conn, metricId=uid)

    if atLeast:
      self.assertGreaterEqual(result.rowcount, size)
    else:
      self.assertEqual(result.rowcount, size)

    for row in result:
      self.assertIsNotNone(row)


  @retry(duration=30)
  def checkMetricCreated(self, metricName, numRecords=None):
    """Check that the new metrics show up in custom metrics list.

    :param metricName: metric name to check
    :param numRecords: optional number of records to wait for
    """
    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      metrics = repository.getCustomMetrics(conn)

    for metric in metrics:
      if metric.name == metricName:
        if numRecords:
          self.assertGreaterEqual(metric.last_rowid,numRecords)
        return metric.uid

    raise AssertionError("Metric not created!")


  @retry(duration=75, delay=1)
  def checkModelResults(self, uid, expectedResults):
    """Check that the results for metric uid match expectedResults.
    """
    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      result = (
        repository.getMetricData(conn,
                                 metricId=uid,
                                 sort=schema.metric_data.c.timestamp.desc()))

    self.assertEqual(result.rowcount, len(expectedResults))

    for result, expected in zip(result, expectedResults):
      self.assertSequenceEqual([result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                result.metric_value,
                                result.anomaly_score,
                                result.rowid],
                               expected)

  @retry(duration=600, delay=5)
  def getModelResults(self, uid, resultCount):
    """Queries MySQL db and returns rows with anomaly results

    :param uid: uid of metric
    :param resultCount: number of rows expected
    :return: List of tuples containing timestamp, metric_value,
     anomaly_score, and rowid
    """
    engine = repository.engineFactory(config=self.__config)
    fields = (schema.metric_data.c.timestamp,
              schema.metric_data.c.metric_value,
              schema.metric_data.c.anomaly_score,
              schema.metric_data.c.rowid)

    with engine.begin() as conn:
      result = (
        repository.getMetricData(conn,
                                 metricId=uid,
                                 fields=fields,
                                 sort=schema.metric_data.c.timestamp.desc(),
                                 score=0.0))

    self.assertEqual(result.rowcount, resultCount)
    return result.fetchall()


  @retry()
  def checkModelResultsDeleted(self, uid):
    """Check that the model results have been deleted"""
    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      result = (
        repository.getMetricData(conn,
                                 metricId=uid,
                                 sort=schema.metric_data.c.timestamp.desc()))

    for row in result:
      self.assertIsNone(row.raw_anomaly_score)
      self.assertIsNone(row.anomaly_score)
      self.assertIsNone(row.display_value)


  @retry(duration=25)
  def checkMetricDeleted(self, uid):

    engine = repository.engineFactory(config=self.__config)

    with engine.begin() as conn:
      with self.assertRaises(Exception) as e:
        metric = repository.getMetric(conn, uid)

      models = repository.getAllModels(conn)
      for model in models:
        self.assertNotEqual(model.uid, uid,
                            "Model showing up after deletion.")

    with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
      model_checkpoint_mgr.ModelCheckpointMgr().loadModelDefinition(uid)


  def gracefullyCloseSocket(self, sock):
    try:
      sock.shutdown(socket.SHUT_WR)
      response = sock.recv(4096)
      self.assertEqual(len(response), 0,
                       "Unexpected TCP response: %s" % response)
      sock.close()
    except socket.error:
      pass
