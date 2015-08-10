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
Integration tests for the nta.utils.amqp.SynchronousAmqpClient module
"""

import logging
import requests
import unittest

from nta.utils.error_handling import retry
from nta.utils.amqp.connection import (
    getRabbitmqConnectionParameters,
    RabbitmqManagementConnectionParams,
)
from nta.utils.amqp.consumer import Consumer
from nta.utils.amqp.exceptions import (
    AmqpChannelError,
    UnroutableError
)
from nta.utils.amqp.messages import (
    BasicProperties,
    Message,
    MessageDeliveryInfo,
    MessageGetInfo,
    MessageReturnInfo,
    ReturnedMessage,
)
from nta.utils.amqp.queue import QueueDeclarationResult
from nta.utils.amqp.synchronous_amqp_client import SynchronousAmqpClient
from nta.utils.logging_support_raw import LoggingSupport
from nta.utils.test_utils import amqp_test_utils



_LOGGER = logging.getLogger(__name__)



def setUpModule():
  LoggingSupport.initTestApp()



_RETRY_ON_ASSERTION_ERROR = retry(timeoutSec=20, initialRetryDelaySec=0.5,
                                  maxRetryDelaySec=2,
                                  retryExceptions=(AssertionError,),
                                  logger=_LOGGER)



_NUM_TEST_MESSAGES = 3



@amqp_test_utils.RabbitmqVirtualHostPatch(
    clientLabel="testingAmqpClient",
    logger=_LOGGER)
class SynchronousAmqpClientTest(unittest.TestCase):
  """ Test for nta.utils.amqp.SynchronousAmqpClient """

  def __init__(self, *args, **kwargs):
    super(SynchronousAmqpClientTest, self).__init__(*args, **kwargs)
    self.connParams = None
    self.client = None


  def _connectToClient(self):
    """
    Setup method to run at beginning of test. Since tests are wrapped with the
    amqp_test_utils.RabbitmqVirtualHostPatch, connection parameters for the
    SynchronousAmqpClient MUST be checked during the test AND NOT during the
    usual setUp() method of unittest.TestCase, since the patch only applies to
    functions with the prefix specified in
    amqp_test_utils.RabbitmqVirtualHostPatch (test).
    """
    self.connParams = RabbitmqManagementConnectionParams()
    self.client = SynchronousAmqpClient(getRabbitmqConnectionParameters())
    self.assertTrue(self.client.isOpen())
    self.addCleanup(self.client.close)


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyExchange(self, testExchangeName, testExchangeType):
    """
    Verifies that a given exchange exists

    :param str testExchangeName: Exchange name
    :param str testExchangeType: Exchange type ("direct", "topic", "fanout")
    """
    exchange = requests.get(
        url="http://%s:%s/api/exchanges/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            testExchangeName),
        auth=(self.connParams.username,
              self.connParams.password)
    ).json()
    self.assertIn("name", exchange)
    self.assertIn("type", exchange)
    self.assertEqual(exchange["name"], testExchangeName)
    self.assertEqual(exchange["type"], testExchangeType)


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyDeletedExchange(self, exchangeName):
    """
    Verifies that a given exchange does not exist.

    :param str exchangeName: Exchange name
    """
    response = requests.get(
        url="http://%s:%s/api/exchanges/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            exchangeName),
        auth=(self.connParams.username,
              self.connParams.password))
    self.assertEqual(response.status_code, 404,
                     "Exchange didn't properly delete")


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyQueue(self, testQueueName, testConsumerCount=0,
                   testMessageCount=0):
    """
    Verifies that a given queue exists, with optional verification of message
    and consumer counts.

    :param str testQueueName: Queue name
    :param int testConsumerCount: (optional)
    :param int testMessageCount: (optional)
    """
    queue = requests.get(
        url="http://%s:%s/api/queues/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            testQueueName),
        auth=(self.connParams.username,
              self.connParams.password)
    ).json()
    self.assertIn("name", queue)
    self.assertIn("consumers", queue)
    self.assertIn("messages", queue)
    self.assertEqual(queue["name"], testQueueName)
    self.assertEqual(queue["consumers"], testConsumerCount)
    self.assertEqual(queue["messages"], testMessageCount)


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyDeletedQueue(self, queueName):
    """
    Verifies that a given queue does not exist.

    :param queueName: Queue name
    """
    response = requests.get(
        url="http://%s:%s/api/queues/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username,
              self.connParams.password))
    self.assertEqual(response.status_code, 404, "Queue didn't properly delete")


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyReadyMessages(self, queueName):
    queue = requests.get(
        url="http://%s:%s/api/queues/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    self.assertIn("messages_ready", queue)
    self.assertEqual(queue["messages_ready"], _NUM_TEST_MESSAGES)


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyUnacknowledgedMessages(self, queueName):
    queue = requests.get(
        url="http://%s:%s/api/queues/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    self.assertIn("messages_unacknowledged", queue)
    self.assertEqual(queue["messages_unacknowledged"], _NUM_TEST_MESSAGES)


  @_RETRY_ON_ASSERTION_ERROR
  def _verifyAcknowledgedMessages(self, queueName):
    """
    Verifies that messages are acked on server in nested function to
    use the _RETRY_ON_ASSERTION_ERROR decorator.
    """
    queue = requests.get(
        url="http://%s:%s/api/queues/%s/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    self.assertIn("messages", queue)
    self.assertIn("message_stats", queue)
    self.assertEqual(queue["messages"], 0)
    self.assertIn("ack", queue["message_stats"])
    self.assertEqual(queue["message_stats"]["ack"], _NUM_TEST_MESSAGES)


  @_RETRY_ON_ASSERTION_ERROR
  def _hasEvent(self):
    self.assertTrue(self.client.hasEvent())


  def testDeclareAndDeleteDirectExchange(self):
    """  Test creating and deleting a new exchange (type = direct) """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"

    with self.assertRaises(AmqpChannelError) as cm:
      self.client.declareExchange(exchangeName, exchangeType, passive=True)
    self.assertEqual(cm.exception.code, 404)

    self.client.declareExchange(exchangeName, exchangeType)
    self._verifyExchange(exchangeName, exchangeType)

    self.client.declareExchange(exchangeName, exchangeType, passive=True)

    self.client.deleteExchange(exchangeName)
    self._verifyDeletedExchange(exchangeName)


  def testDeclareAndDeleteFanoutExchange(self):
    """  Test creating and deleting a new exchange (type = fanout) """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "fanout"

    with self.assertRaises(AmqpChannelError) as cm:
      self.client.declareExchange(exchangeName, exchangeType, passive=True)
    self.assertEqual(cm.exception.code, 404)

    self.client.declareExchange(exchangeName, exchangeType)
    self._verifyExchange(exchangeName, exchangeType)

    self.client.declareExchange(exchangeName, exchangeType, passive=True)

    self.client.deleteExchange(exchangeName)
    self._verifyDeletedExchange(exchangeName)


  def testDeclareAndDeleteTopicExchange(self):
    """  Test creating and deleting a new exchange (type = topic) """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "topic"

    with self.assertRaises(AmqpChannelError) as cm:
      self.client.declareExchange(exchangeName, exchangeType, passive=True)
    self.assertEqual(cm.exception.code, 404)

    self.client.declareExchange(exchangeName, exchangeType)
    self._verifyExchange(exchangeName, exchangeType)

    self.client.declareExchange(exchangeName, exchangeType, passive=True)

    self.client.deleteExchange(exchangeName)
    self._verifyDeletedExchange(exchangeName)


  def testDeclareAndDeleteQueue(self):
    """ Test the declareQueue and deleteQueue methods """
    self._connectToClient()
    queueName = "testQueue"

    with self.assertRaises(AmqpChannelError) as cm:
      self.client.declareQueue(queueName, passive=True)
    self.assertEqual(cm.exception.code, 404)

    queueResult = self.client.declareQueue(queueName)
    self.assertIsInstance(queueResult, QueueDeclarationResult)
    self.assertEqual(queueResult.queue, queueName)
    self.assertEqual(queueResult.consumerCount, 0)
    self.assertEqual(queueResult.messageCount, 0)
    self._verifyQueue(queueName)

    queueResult = self.client.declareQueue(queueName, passive=True)
    self.assertIsInstance(queueResult, QueueDeclarationResult)
    self.assertEqual(queueResult.queue, queueName)
    self.assertEqual(queueResult.consumerCount, 0)
    self.assertEqual(queueResult.messageCount, 0)
    self._verifyQueue(queueName)

    self.client.deleteQueue(queueName)
    self._verifyDeletedQueue(queueName)


  def testBindUnbindQueue(self):
    """ Test binding and unbinding queues to exchanges """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)

    self.client.bindQueue(queueName, exchangeName, routingKey)
    queueBindings = requests.get(
        url="http://%s:%s/api/queues/%s/%s/bindings" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    queueBindingsList = [bind for bind in queueBindings
                         if bind["source"] == exchangeName]
    self.assertTrue(queueBindingsList)
    self.assertEqual(queueBindingsList[0]["routing_key"], routingKey)

    exchangeBindings = requests.get(
        url="http://%s:%s/api/exchanges/%s/%s/bindings/source" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            exchangeName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    exchangeBindingsList = [bind for bind in exchangeBindings
                            if bind["destination"] == queueName]
    self.assertTrue(exchangeBindingsList)
                    # Tests that the binding actually exists
    self.assertEqual(exchangeBindingsList[0]["routing_key"], routingKey)

    bindings = requests.get(
        url="http://%s:%s/api/bindings/%s/e/%s/q/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            exchangeName,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    bindingsList = [bind for bind in bindings
                    if bind["routing_key"] == routingKey]
    self.assertTrue(bindingsList)

    self.client.unbindQueue(queueName, exchangeName, routingKey)
    queueBindings = requests.get(
        url="http://%s:%s/api/queues/%s/%s/bindings" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    queueBindingsList = [bind for bind in queueBindings
                         if bind["source"] == exchangeName]
    self.assertFalse(queueBindingsList)
    exchangeBindings = requests.get(
        url="http://%s:%s/api/exchanges/%s/%s/bindings/source" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            exchangeName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    exchangeBindingsList = [bind for bind in exchangeBindings
                            if bind["destination"] == queueName]
    self.assertFalse(exchangeBindingsList)
    bindings = requests.get(
        url="http://%s:%s/api/bindings/%s/e/%s/q/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost,
            exchangeName,
            queueName),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    bindingsList = [bind for bind in bindings
                    if bind["routing_key"] == routingKey]
    self.assertFalse(bindingsList)


  def testPublishMessage(self):
    """ Test that published messages reach their specified queues"""
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    # Test message publishing
    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)

    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)


  def testPublishAndPurgeOnMultipleQueues(self):
    """ Test that queues are properly purged"""
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName1 = "testQueue1"
    queueName2 = "testQueue2"
    routingKey1 = "testKey1"
    routingKey2 = "testKey2"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName1)
    self.client.declareQueue(queueName2)
    self.client.bindQueue(queueName1, exchangeName, routingKey1)
    self.client.bindQueue(queueName2, exchangeName, routingKey2)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d-queue1" % (i)),
                          exchangeName,
                          routingKey1)
    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d-queue2" % (i)),
                          exchangeName,
                          routingKey2)

    self._verifyQueue(queueName1, testMessageCount=_NUM_TEST_MESSAGES)
    self._verifyQueue(queueName2, testMessageCount=_NUM_TEST_MESSAGES)
    self.client.purgeQueue(queueName1)
    self._verifyQueue(queueName1, testMessageCount=0)
    self._verifyQueue(queueName2, testMessageCount=_NUM_TEST_MESSAGES)
    self.client.purgeQueue(queueName2)
    self._verifyQueue(queueName2, testMessageCount=0)


  def testAckAllMessages(self):
    """ Tests acking all messages"""
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    self._verifyReadyMessages(queueName)

    self.client.createConsumer(queueName)
    self._verifyUnacknowledgedMessages(queueName)

    self.client.ackAll()
    self._verifyAcknowledgedMessages(queueName)


  def testNackAllMessages(self):
    """ Tests nacking all messages """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    self._verifyReadyMessages(queueName)

    self.client.createConsumer(queueName)
    self._verifyUnacknowledgedMessages(queueName)

    self.client.nackAll()
    @_RETRY_ON_ASSERTION_ERROR
    def _verifyNackedMessages():
      """
      Verifies that messages are gone from server in nested function to
      use the _RETRY_ON_ASSERTION_ERROR decorator.
      """
      queue = requests.get(
          url="http://%s:%s/api/queues/%s/%s" % (
              self.connParams.host,
              self.connParams.port,
              self.connParams.vhost,
              queueName),
          auth=(self.connParams.username, self.connParams.password)
      ).json()
      self.assertEqual(queue["messages"], 0)
      self.assertEqual(queue["messages_unacknowledged"], 0)
    _verifyNackedMessages()


  def testGetOneMessage(self):
    """ Tests getting messages using getOneMessage. """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    for i in range(0, _NUM_TEST_MESSAGES):
      message = self.client.getOneMessage(queueName)
      _LOGGER.info("getOneMessage() = %s", message.__repr__())
      self.assertEqual(message.body, "test-msg-%d" % (i))
      self.assertEqual(message.properties, BasicProperties())
      self.assertEqual(message.methodInfo,
                       MessageGetInfo(deliveryTag=(i+1),
                                      redelivered=False,
                                      exchange=exchangeName,
                                      routingKey=routingKey,
                                      messageCount=(_NUM_TEST_MESSAGES-1-i)))


  def testEnablePublisherAcksAfterUnroutableMessage(self):
    """
    Tests enabling publisher acknowledgements after an unroutable message has
    already been sent.
    """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    self.client.publish(Message("test-msg"), exchangeName, "fakeKey",
                        mandatory=True)

    with self.assertRaises(UnroutableError) as cm:
      self.client.enablePublisherAcks()

    self.assertEqual(cm.exception.messages[0],
                     ReturnedMessage(
                         body="test-msg",
                         properties=BasicProperties(),
                         methodInfo=MessageReturnInfo(
                             replyCode=312,
                             replyText="NO_ROUTE",
                             exchange=exchangeName,
                             routingKey="fakeKey")))


  def testPublishMandatoryMessage(self):
    """
    Tests sending an unroutable message after enabling publisher
    acknowledgements.
    """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    self.client.enablePublisherAcks()

    self.assertRaises(UnroutableError, self.client.publish,
                      Message("test-msg"), exchangeName, "fakeKey",
                      mandatory=True)

    self.client.publish(Message("test-msg"), exchangeName, routingKey,
                        mandatory=True)


  def testCreateCloseConsumer(self):
    """ Tests creation and close of a consumer. """
    self._connectToClient()
    queueName = "testQueue"

    self.client.declareQueue(queueName)

    # Test creation of consumer
    consumer = self.client.createConsumer(queueName)
    self.assertIsInstance(consumer, Consumer)
    self.assertNotEqual(consumer.tag, "")
    consumers = requests.get(
        url="http://%s:%s/api/consumers/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    consumersList = [c for c in consumers if c["queue"]["name"] == queueName]
    self.assertTrue(consumersList)
    self.assertEqual(consumersList[0]["consumer_tag"], consumer.tag)

    consumer.cancel()
    consumers = requests.get(
        url="http://%s:%s/api/consumers/%s" % (
            self.connParams.host,
            self.connParams.port,
            self.connParams.vhost),
        auth=(self.connParams.username, self.connParams.password)
    ).json()
    consumersList = [c for c in consumers if c["queue"]["name"] == queueName]
    self.assertFalse(consumersList)


  def testConsumerGetNextEvent(self):
    """ Tests getting messages using a consumer and getNextEvent(). """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    consumer = self.client.createConsumer(queueName)
    self._hasEvent()

    for i in range(0, _NUM_TEST_MESSAGES):
      message = self.client.getNextEvent()
      self.assertEqual(message.body, "test-msg-%d" % (i))
      self.assertEqual(message.properties, BasicProperties())
      self.assertEqual(message.methodInfo,
                       MessageDeliveryInfo(consumerTag=consumer.tag,
                                           deliveryTag=(i+1),
                                           redelivered=False,
                                           exchange=exchangeName,
                                           routingKey=routingKey))


  def testRecoverUnackedMessages(self):
    """ Tests the recover method to re-queue unacked messages. """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    consumer = self.client.createConsumer(queueName)
    self._hasEvent()

    for i in range(0, _NUM_TEST_MESSAGES):
      message = self.client.getNextEvent()
      self.assertEqual(message.body, "test-msg-%d" % (i))
      self.assertEqual(message.properties, BasicProperties())
      self.assertEqual(message.methodInfo,
                       MessageDeliveryInfo(consumerTag=consumer.tag,
                                           deliveryTag=(i+1),
                                           redelivered=False,
                                           exchange=exchangeName,
                                           routingKey=routingKey))

    self._verifyUnacknowledgedMessages(queueName)

    self.client.recover(requeue=True)

    @_RETRY_ON_ASSERTION_ERROR
    def _verifyRecoveredMessages():
      """
      Verifies that messages are unacknowledged on server in nested function to
      use the _RETRY_ON_ASSERTION_ERROR decorator.
      """
      queue = requests.get(
          url="http://%s:%s/api/queues/%s/%s" % (
              self.connParams.host,
              self.connParams.port,
              self.connParams.vhost,
              queueName),
          auth=(self.connParams.username, self.connParams.password)
      ).json()
      self.assertIn("redeliver", queue["message_stats"])
      self.assertEqual(queue["message_stats"]["redeliver"], _NUM_TEST_MESSAGES)
    _verifyRecoveredMessages()

    for i in range(0, _NUM_TEST_MESSAGES):
      message = self.client.getNextEvent()
      self.assertEqual(message.body, "test-msg-%d" % (i))
      self.assertEqual(message.properties, BasicProperties())
      self.assertEqual(message.methodInfo,
                       MessageDeliveryInfo(consumerTag=consumer.tag,
                                           deliveryTag=(_NUM_TEST_MESSAGES+i+1),
                                           redelivered=True,
                                           exchange=exchangeName,
                                           routingKey=routingKey))


  def testAckingMessages(self):
    """ Tests acking messages """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    self.client.createConsumer(queueName)
    self._hasEvent()

    for i in range(0, _NUM_TEST_MESSAGES):
      self.client.getNextEvent().ack()
    self._verifyAcknowledgedMessages(queueName)


  def testNackingMessages(self):
    """Tests nacking messages """
    self._connectToClient()
    exchangeName = "testExchange"
    exchangeType = "direct"
    queueName = "testQueue"
    routingKey = "testKey"

    self.client.declareExchange(exchangeName, exchangeType)
    self.client.declareQueue(queueName)
    self.client.bindQueue(queueName, exchangeName, routingKey)

    for i in range(0, _NUM_TEST_MESSAGES):
      # Test random numbers of messages sent to the queue
      self.client.publish(Message("test-msg-%d" % (i)),
                          exchangeName,
                          routingKey)
    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES)

    self.client.createConsumer(queueName)
    self._hasEvent()

    self._verifyQueue(queueName, testMessageCount=_NUM_TEST_MESSAGES,
                      testConsumerCount=1)

    for i in range(0, _NUM_TEST_MESSAGES):
      self.client.getNextEvent().nack()

    self._verifyQueue(queueName, testMessageCount=0, testConsumerCount=1)

    @_RETRY_ON_ASSERTION_ERROR
    def _verifyNackedMessages():
      """
      Verifies that messages are unacknowledged on server in nested function to
      use the _RETRY_ON_ASSERTION_ERROR decorator.
      """
      queue = requests.get(
          url="http://%s:%s/api/queues/%s/%s" % (
              self.connParams.host,
              self.connParams.port,
              self.connParams.vhost,
              queueName),
          auth=(self.connParams.username, self.connParams.password)
      ).json()
      self.assertEqual(queue["messages"], 0)
      self.assertEqual(queue["messages_unacknowledged"], 0)
    _verifyNackedMessages()



if __name__ == "__main__":
  unittest.main()
