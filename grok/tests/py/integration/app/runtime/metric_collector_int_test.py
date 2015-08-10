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
Integration tests for YOMP.app.runtime.metric_collector

TODO Need to test unhappy paths, too
"""

import logging
import os
import Queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from YOMP.app.quota import Quota


from nupic.support.decorators import retry

from nta.utils.message_bus_connector import MessageBusConnector
from nta.utils.test_utils import ManagedSubprocessTerminator
from nta.utils.test_utils.amqp_test_utils import RabbitmqVirtualHostPatch
from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository

import YOMP.app
from YOMP.app import repository
from YOMP.app.adapters.datasource import createCloudwatchDatasourceAdapter
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.repository.queries import MetricStatus

from htmengine.model_swapper.model_swapper_interface import (
  ModelSwapperInterface)

from YOMP import logging_support



_LOGGER = logging.getLogger(__name__)


def setUpModule():
  logging_support.LoggingSupport.initTestApp()


def _waitForServiceReady(outputFilePath):
  time.sleep(0.5)

  @retry(timeoutSec=10, initialRetryDelaySec=0.5, maxRetryDelaySec=0.5)
  def waitWithRetries(outputFilePath):
    # Check for presence of the metric_data queue that metric_collector
    # creates once it starts processing. This will raise an exception if
    # the queue doesn't exist yet
    if os.stat(outputFilePath).st_size <= 0:
      raise Exception("Service not ready: %s is empty" % (outputFilePath,))

  waitWithRetries(outputFilePath)



# NOTE: The aws credentials in application.conf initially have empty
#  string values, expecting to be set via the /YOMP/welcome screen. Since this
#  test doesn't involve YOMP-api, we will get the credentials from environment
#  variables as that the test environments are expected to set and apply them
#  as config overrides.
@RabbitmqVirtualHostPatch(clientLabel="MetricCollectorTestCase")
@ConfigAttributePatch(
  YOMP.app.config.CONFIG_NAME,
  YOMP.app.config.baseConfigDir,
  (
    ("metric_collector", "poll_interval", "1.0"),
  )
)
class MetricCollectorTestCase(unittest.TestCase):
  """
  Fast facts about Metric Collector:
    Metric polling interval is controlled by:
      YOMP.app.config.getfloat("metric_collector", "poll_interval")

    Publishes data points via ModelSwapperInterface.submitRequests

    Output data point batch size is controlled by:
      YOMP.app.config.getint("metric_streamer", "chunk_size")

  """


  def _startMetricCollectorSubprocess(self):
    """
    Returns: the subprocess.Popen instance wrapped in
    ManagedSubprocessTerminator
    """
    # Override CWD for the metric collector subprocess so that it won't write
    # files in our source tree
    tempCWD = tempfile.mkdtemp(
      self.__class__.__name__ + '_startMetricCollectorSubprocess')
    self.addCleanup(shutil.rmtree, tempCWD)
    cwd = os.getcwd()
    os.chdir(tempCWD)

    stdout = open(os.path.join(tempCWD, "metric_collector.stdout"), "a")
    stderr = open(os.path.join(tempCWD, "metric_collector.stderr"), "a")

    try:
      p = subprocess.Popen(args=[sys.executable, "-m",
                                 "YOMP.app.runtime.metric_collector"],
                           stdin=subprocess.PIPE,
                           stdout=stdout,
                           stderr=stderr)

      _LOGGER.info("Started metric_collector subprocess=%s", p)

      # Give it a little time to get initialized; NOTE: if we don't wait, then
      # Python runtime doesn't get enough time to register its SIGINT handler
      # for KeyboardInterrupt, resulting in `-2` return code from the subprocess
      # instead of the 0 return code that we expect from normal termination
      _LOGGER.info("Waiting for metric_collector subprocess to init")
      _waitForServiceReady(stderr.name)

      return ManagedSubprocessTerminator(p)
    finally:
      # Restore current working directory
      os.chdir(cwd)


  def _startModelSchedulerSubprocess(self):
    """
    Returns: the subprocess.Popen instance wrapped in
    ManagedSubprocessTerminator
    """
    # Override CWD for the metric collector subprocess so that it won't write
    # files in our source tree
    tempCWD = tempfile.mkdtemp(
      self.__class__.__name__ + '_startModelSchedulerSubprocess')
    self.addCleanup(shutil.rmtree, tempCWD)
    cwd = os.getcwd()
    os.chdir(tempCWD)

    stdout = open(os.path.join(tempCWD, "model_scheduler.stdout"), "a")
    stderr = open(os.path.join(tempCWD, "model_scheduler.stderr"), "a")

    try:
      p = subprocess.Popen(
        args=[sys.executable, "-m",
              "htmengine.model_swapper.model_scheduler_service"],
        stdin=subprocess.PIPE,
        stdout=stdout,
        stderr=stderr)

      _LOGGER.info("Started model_scheduler subprocess=%s", p)

      # Give it a little time to get initialized; NOTE: if we don't wait, then
      # Python runtime doesn't get enough time to register its SIGINT handler
      # for KeyboardInterrupt, resulting in `-2` return code from the subprocess
      # instead of the 0 return code that we expect from normal termination
      _LOGGER.info("Waiting for model_scheduler subprocess to init")
      _waitForServiceReady(stderr.name)

      return ManagedSubprocessTerminator(p)
    finally:
      # Restore current working directory
      os.chdir(cwd)


  @ManagedTempRepository(clientLabel="MetricCollectorTestCase")
  def testStartAndStopMetricCollector(self):
    # Simply start Metric Collector as a subprocess and then stop it and verify
    # that it stopped gracefully (i.e., process returncode=0)

    # Start metric collector as a subprocess
    with self._startMetricCollectorSubprocess() as p:
      # Verify that it's still running
      self.assertIsNone(p.poll(),
                        msg="subprocess %s stopped prematurely" % (p.pid,))

      def waitForSubprocessToStop(p, resultQ):
        try:
          r = p.wait()
          _LOGGER.info("metric collector subprocess returncode=%s", r)
          resultQ.put(r)
        except Exception:
          _LOGGER.exception("Error waiting for metric collector subprocess")
          resultQ.put(sys.exc_info()[1])
          raise

      # Give subprocess time to initialize before potentially killing it 
      # prematurely
      time.sleep(5)

      # Stop it using the signal that it expects from supervisord; this should
      # trigger its handler for KeyboardInterrupt
      p.send_signal(signal.SIGINT)

      # Wait for metric collector to exit. NOTE: we do this in a thread to avoid
      # deadlocking the test in case metric collector fails to stop
      resultQ = Queue.Queue()
      waitThread = threading.Thread(target=waitForSubprocessToStop,
                                    args=(p, resultQ,))
      waitThread.setDaemon(True)
      waitThread.start()

      waitThread.join(timeout=5)
      self.assertFalse(waitThread.isAlive())

      self.assertEqual(resultQ.get_nowait(), 0)


  @ManagedTempRepository(clientLabel="MetricCollectorTestCase")
  def testCollectAndPublishMetrics(self):
    # Start Metric Collector, create a set of Metrics, wait for it to collect
    # some metrics and to publish them to the metric_exchange, then validate
    # attributes of the published metrics.
    #
    # TODO Add more metric types
    # TODO Deeper validation of the published metrics

    # Start our own instance of metric collector and wait for data points
    with self._startModelSchedulerSubprocess() as modelSchedulerSubprocess, \
        self._startMetricCollectorSubprocess() as metricCollectorSubprocess:
      # Create some models for metric collector to harvest
      region = "us-west-2"
      namespace = "AWS/EC2"
      resourceType = ResourceTypeNames.EC2_INSTANCE

      engine = repository.engineFactory()
      adapter = createCloudwatchDatasourceAdapter()


      ec2Instances = adapter.describeResources(region=region,
                                               resourceType=resourceType)

      self.assertGreater(len(ec2Instances), 0)

      maxModels = 10

      ec2Instances = ec2Instances[:min(maxModels, Quota.getInstanceQuota())]

      metricInstances = []

      _LOGGER.info("Starting %d models", len(ec2Instances))
      self.assertGreater(len(ec2Instances), 0)
      for ec2Instance in ec2Instances:

        metricSpec = {"region": region,
                      "namespace": namespace,
                      "metric": "CPUUtilization",
                      "dimensions": {"InstanceId": ec2Instance["resID"]}}

        modelSpec = {"datasource": "cloudwatch",
                     "metricSpec": metricSpec}

        metricId = adapter.monitorMetric(modelSpec)

        with engine.connect() as conn:
          repository.setMetricStatus(conn, metricId, MetricStatus.ACTIVE)

        metricInstances.append(metricId)

      _LOGGER.info("Waiting for results from models...")

      seenMetricIDs = set()
      allMetricIDs = set(metricInstances)

      # Register a timeout so we won't deadlock the test
      def onTimeout(resultsQueueName):
        _LOGGER.error(
          "Timed out waiting to get results from models; numResults=%d; "
          "expected=%d", len(seenMetricIDs), len(allMetricIDs))

        # HACK delete model swapper results queue to abort the consumer
        try:
          with MessageBusConnector() as bus:
            bus.deleteMessageQueue(resultsQueueName)
        except Exception:
          _LOGGER.exception("Failed to delete results mq=%s", resultsQueueName)
          raise

      with ModelSwapperInterface() as modelSwapper:
        with modelSwapper.consumeResults() as consumer:
          timer = threading.Timer(120, onTimeout,
                                  args=[modelSwapper._resultsQueueName])
          timer.start()
          try:
            for batch in consumer:
              seenMetricIDs.add(batch.modelID)
              batch.ack()
              if seenMetricIDs == allMetricIDs:
                break
            else:
              self.fail(
                "Expected %d results, but got only %d: %s"
                % (len(allMetricIDs), len(seenMetricIDs), seenMetricIDs,))
            _LOGGER.info("Got %d results from models", len(seenMetricIDs))
          finally:
            timer.cancel()

      # Terminate metric_collector subprocess gracefully to avoid too much
      # error logging junk on the terminal
      metricCollectorSubprocess.send_signal(signal.SIGINT)

      # Terminate metric_collector subprocess gracefully to avoid too much
      # error logging junk on the terminal
      modelSchedulerSubprocess.send_signal(signal.SIGINT)


if __name__ == '__main__':
  unittest.main()
