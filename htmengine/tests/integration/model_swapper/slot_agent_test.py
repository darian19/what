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

"""Integration test for the Model Swapper's Slot Agent.


TODO: need more tests for model_swapper.slot_agent.ModelRunnerProxy
TODO: need tests for model_swapper.slot_agent.SlotAgent
"""

import logging


import unittest


from mock import patch

from htmengine.model_swapper import slot_agent
from htmengine.model_swapper.model_swapper_interface import (
  ModelSwapperInterface)
from nta.utils.message_bus_connector import MessageBusConnector

from nta.utils.test_utils import amqp_test_utils

from htmengine.model_swapper.model_swapper_test_utils import (
  ModelSwapperIsolationPatch)

from nta.utils.logging_support_raw import LoggingSupport



_LOGGER = logging.getLogger(__name__)



def setUpModule():
  LoggingSupport.initTestApp()



# Disable warning: Access to a protected member
# pylint: disable=W0212



@ModelSwapperIsolationPatch(clientLabel="ModelRunnerProxyTestCase",
                            logger=_LOGGER)
class ModelRunnerProxyTestCase(unittest.TestCase):
  """Tests slot_agent.ModelRunnerProxy"""


  def testStartModelRunnerAndStopIt(self):
    # Simple test that starts a ModelRunner and stops it gracefully
    # TODO send command to model and verify output

    modelID = "abcdef"

    with ModelSwapperInterface() as swapper:
      modelInputMQ = swapper._getModelInputQName(modelID=modelID)

    with amqp_test_utils.managedQueueDeleter(modelInputMQ):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(modelInputMQ, durable=True)

      runner = slot_agent.ModelRunnerProxy(
        modelID=modelID,
        onTermination=lambda: None,
        logger=_LOGGER)

      returnCode = runner.stopGracefully()

      self.assertEqual(returnCode, 0)


  @patch.object(slot_agent.ModelRunnerProxy, "_MAX_WAIT_FOR_GRACEFUL_STOP_SEC",
                new=5)
  def testStartMultipleModelRunnersAndStopThem(self):
    # Starts several ModelRunners and stops them gracefully
    # to confirm that they can all stop without conflicting with each other:
    # if ModelRunnerProxy doesn't configure subprocess.Popen with
    # `close_fds=True`, then graceful shutdown will fail because the stdin
    # of some child processes will be cloned into those that are started
    # after them and closing stding of an earlier ModelRunner child process
    # won't have the desired effect of terminating that process (since other
    # clones of that file descriptor will prevent it from fully closing)
    #
    # TODO send commands to models and verify output

    runners = []

    modelIDs = tuple("abcdef" + str(i) for i in xrange(5))

    with ModelSwapperInterface() as swapper:
      modelInputMQs = tuple(swapper._getModelInputQName(modelID=modelID)
                            for modelID in modelIDs)

    with amqp_test_utils.managedQueueDeleter(modelInputMQs):
      with MessageBusConnector() as bus:
        for mq in modelInputMQs:
          bus.createMessageQueue(mq, durable=True)

      for modelID in modelIDs:
        runners.append(
          slot_agent.ModelRunnerProxy(
            modelID=modelID,
            onTermination=lambda: None,
            logger=_LOGGER))

      returnCodes = [runner.stopGracefully() for runner in runners]

    self.assertEqual(returnCodes, [0] * len(runners))



if __name__ == '__main__':
  unittest.main()
