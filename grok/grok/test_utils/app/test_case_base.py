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
This script implements an extension of the unittest2.TestCase class to be
used as a base class unit tests
"""

import sys
import functools
import json
import socket
import time
import logging

import unittest

import requests

from YOMP.app import repository
from YOMP.app.repository import schema
from htmengine.repository.queries import MetricStatus


from htmengine.model_checkpoint_mgr import model_checkpoint_mgr

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
  in YOMP App test suites.
  """

  # NOTE: Derived class must override this with the valid YOMPAPI key before
  # calling methods of this class that may need it.
  apiKey = None


  def __init__(self, *args, **kwargs):

    # Construct the base-class instance
    super(TestCaseBase, self).__init__(*args, **kwargs)


  @property
  def __apiKey(self):
    if self.apiKey is None:
      raise ValueError("Did %r forget to set apiKey member variable "
                       "to non-None YOMP API Key?" % (self,))
    return self.apiKey


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


  @retry(duration=600, delay=5)
  def getModelResults(self, uid, resultCount):
    urlString = "https://localhost/_models/%s/data" % uid
    response = requests.get(urlString,
                            auth=(self.__apiKey, ""), verify=False)
    data = response.json()["data"]
    currentResultCount = len(data)
    LOGGER.info("Got %d results, expected %d", currentResultCount, resultCount)
    self.assertEqual(len(data), resultCount)
    return data


  @retry(duration=45, delay=1)
  def checkModelIsActive(self, uid):
    engine = repository.engineFactory()
    with engine.begin() as conn:
      metricObj = repository.getMetric(conn,
                                       uid,
                                       fields=[schema.metric.c.status])

    self.assertEqual(metricObj.status, MetricStatus.ACTIVE)


  @retry(duration=30, delay=1)
  def checkMetricUnmonitoredById(self, uid):
    engine = repository.engineFactory()
    with engine.begin() as conn:
      metricObj = repository.getMetric(conn,
                                       uid,
                                       fields=[schema.metric.c.status,
                                               schema.metric.c.parameters])

    self.assertEqual(metricObj.status, MetricStatus.UNMONITORED)
    self.assertIsNone(metricObj.parameters)

    with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
      model_checkpoint_mgr.ModelCheckpointMgr().loadModelDefinition(uid)


  @retry(duration=30)
  def checkMetricCreated(self, metricName, numRecords=None):
    """Check that the new metrics show up in custom metrics list.

    TODO: since this is specific to YOMP Custom metrics, rename to
      checkYOMPCustomMetricCreated

    :param metricName: metric name to check
    :param numRecords: optional number of records to wait for
    """
    response = requests.get("https://localhost/_metrics/custom",
                            auth=(self.__apiKey, ""), verify=False)
    nameToMetric = dict((m["name"], m) for m in response.json())
    metricNameSet = set(nameToMetric.keys())
    self.assertIn(metricName, metricNameSet)
    if numRecords:
      self.assertGreaterEqual(nameToMetric[metricName]["last_rowid"],
                              numRecords)
    return nameToMetric[metricName]["uid"]


  @retry()
  def checkAutostackCreated(self, uid):
    """Check that the new Autostack shows up in Autostacks list.

    :param uid: the uid of the autostack
    """
    response = requests.get("https://localhost/_autostacks",
                            auth=(self.__apiKey, ""), verify=False)
    uidSet = set(autostack["uid"] for autostack in response.json())
    self.assertIn(uid, uidSet)


  @retry(duration=60)
  def checkModelDeleted(self, uid):
    """Check that the model has been deleted"""

    response = requests.get("https://localhost/_models",
                            auth=(self.__apiKey, ""), verify=False)
    for model in response.json():
      self.assertNotEqual(model["uid"], uid,
                          "Model showing up after deletion.")
    with self.assertRaises(model_checkpoint_mgr.ModelNotFound):
      model_checkpoint_mgr.ModelCheckpointMgr().loadModelDefinition(uid)


  @retry()
  def checkAutostackDeleted(self, uid):
    """Check that the Autostack has been deleted"""
    response = requests.get("https://localhost/_autostacks",
                            auth=(self.__apiKey, ""), verify=False)
    for autostack in response.json():
      self.assertNotEqual(autostack["uid"], uid,
                          "Autostack showing up after deletion.")


  @retry()
  def checkModelResultsDeleted(self, uid):
    """Check that the model results have been deleted"""
    response = requests.get("https://localhost/_models/%s/data" % uid,
                            auth=(self.__apiKey, ""), verify=False)
    self.assertEqual(len(response.json()["data"]), 0)


  @retry()
  def checkMetricDeleted(self, metricName):
    """Make sure the metric no longer shows up in the custom metric list
    TODO: since this is specific to YOMP Custom metrics, rename to
      checkYOMPCustomMetricDeleted
    """
    response = requests.get("https://localhost/_metrics/custom",
                            auth=(self.__apiKey, ""), verify=False)
    self.assertNotIn(metricName,
                     set(m["name"] for m in response.json()))


  @retry()
  def checkStats(self, metricName, mn, mx):
    """Check that stats are computed correctly from the database"""
    engine = repository.engineFactory()
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
  def checkEncoderResolution(self, uid, minVal, maxVal):
    """Check that encoder resolution is computed correctly."""
    engine = repository.engineFactory()
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
    self.assertGreater(encoderParams["resolution"], lower)
    self.assertLess(encoderParams["resolution"], upper)


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
    response = requests.get("https://localhost/_models/%s/data" % uid,
                            auth=(self.__apiKey, ""), verify=False)
    self.assertSetEqual(set(response.json().keys()), set(["names", "data"]))
    names = response.json()["names"]
    data = response.json()["data"]
    self.assertSetEqual(
        set(["timestamp", "value", "anomaly_score", "rowid"]), set(names))

    LOGGER.debug("Checking for %i model results atLeast=%s, currently see: %i",
                 size, atLeast, len(data))
    if atLeast:
      self.assertGreaterEqual(len(data), size)
    else:
      # Check for exact count match
      self.assertEqual(len(data), size)
    for result in data:
      self.assertIsNotNone(result)


  @retry(duration=75, delay=1)
  def checkModelResults(self, uid, expectedResults):
    """Check that the results for metric uid match expectedResults.

    This is not compatible with ManagedTempRepository since it makes an HTTP
    request that may be outside the temp repository process tree.
    """
    response = requests.get("https://localhost/_models/%s/data" % uid,
                            auth=(self.__apiKey, ""), verify=False)
    self.assertSetEqual(set(response.json().keys()), set(["names", "data"]))
    LOGGER.debug("Checking for data output: %r", response.json()["data"])
    names = response.json()["names"]
    self.assertSetEqual(
        set(["timestamp", "value", "anomaly_score", "rowid"]), set(names))
    data = response.json()["data"]
    self.assertEqual(len(data), len(expectedResults))
    for result, expected in zip(data, expectedResults):
      self.assertSequenceEqual(result, expected)


  def gracefullyCloseSocket(self, sock):
    try:
      sock.shutdown(socket.SHUT_WR)
      response = sock.recv(4096)
      self.assertEqual(len(response), 0,
                       "Unexpected TCP response: %s" % response)
      sock.close()
    except socket.error:
      pass
