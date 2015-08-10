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
Integration tests for the durable message queue abstraction

TODO: test durability/persistence (how? stop/re-start rabbitmq broker?)
"""

import copy
import logging
import Queue
import sys
import threading
import time
import unittest
import uuid

from mock import patch

from nta.utils import amqp
from nta.utils.logging_support_raw import LoggingSupport
from nta.utils import message_bus_connector
from nta.utils.message_bus_connector import \
    MessageBusConnector, \
    MessageQueueNotFound, \
    MessageProperties
from nta.utils.test_utils import amqp_test_utils



# Disable "Access to a protected member of a client class"
# pylint: disable=W0212


_LOGGER = logging.getLogger(
  "integration.message_bus_connector_test")



def setUpModule():
  LoggingSupport.initTestApp()



def _getQueueMessageCount(mqName):
  connParams = amqp.connection.getRabbitmqConnectionParameters()
  with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
        amqpClient):
    r = amqpClient.declareQueue(mqName, passive=True)
    return r.messageCount



class _TestCaseBase(unittest.TestCase):

  @classmethod
  def _getUniqueMessageQueueName(cls):
    return "%s.%s" % (cls.__name__, uuid.uuid1().hex)



class MessageQueueManagementTestCase(_TestCaseBase):
  """ Tests queue management support of
  message_bus_connector.MessageBusConnector.

  This includes:
    createMessageQueue
    deleteMessageQueue
    purge
    isEmpty
  """

  def testCreateDurableMessageQueue(self):
    # Create a durable message queue and verify that it exists
    # TODO Test that it's a Durable queue and auto-delete=false

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=True)

      # Check that MessageBusConnector's context manager cleaned up
      self.assertIsNone(bus._channelMgr)

      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testCreateDurableMessageQueueSecondTime(self):
    # Create a durable message queue and verify that repeating the create call
    # succeeds

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=True)

      self.assertEqual(_getQueueMessageCount(mqName), 0)

      # And one more time...
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=True)

      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testCreateNonDurableMessageQueue(self):
    # Create a non-durable message queue and verify that it exists
    # TODO Test that it's a non-Durable queue and auto-delete=false

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=False)

      # Check that MessageBusConnector's context manager cleaned up
      self.assertIsNone(bus._channelMgr)

      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testCreateNonDurableMessageQueueSecondTime(self):
    # Create a non-durable message queue and verify that repeating the create
    # call succeeds

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=False)

        self.assertEqual(_getQueueMessageCount(mqName), 0)

        # And one more time...
        bus.createMessageQueue(mqName=mqName, durable=False)

        self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testDeleteMessageQueue(self):
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        bus.createMessageQueue(mqName=mqName, durable=True)

        self.assertEqual(_getQueueMessageCount(mqName), 0)

        bus.deleteMessageQueue(mqName=mqName)

        connParams = amqp.connection.getRabbitmqConnectionParameters()

        with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
          with self.assertRaises(amqp.exceptions.AmqpChannelError) as excContext:
            r = amqpClient.declareQueue(mqName, passive=True)

          self.assertEqual(excContext.exception.code,
                           amqp.constants.AMQPErrorCodes.NOT_FOUND)


  def testDeleteMessageQueueThatDoesNotExist(self):
    # Verify that deleting a non-existent message queue doesn't raise an
    # exception
    mqName = self._getUniqueMessageQueueName()

    # NOTE: deleting an entity that doesn't exist used to result in
    # NOT_FOUND=404 channel error from RabbitMQ. However, more recent versions
    # of RabbitMQ changed that behavior such that it now completes with success.
    # Per https://www.rabbitmq.com/specification.html: "We have made
    # queue.delete into an idempotent assertion that the queue must not exist,
    # in the same way that queue.declare asserts that it must."

    with MessageBusConnector() as bus:
      bus.deleteMessageQueue(mqName=mqName)


  def testPurge(self):
    # Create a message queue, add some messages to it, then purge the data and
    # verify that it's empty

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add some messages
        bus.publish(mqName, "abc", persistent=True)
        bus.publish(mqName, "def", persistent=True)

        # Verify that the messages were added
        self.assertEqual(_getQueueMessageCount(mqName), 2)

        self.assertFalse(bus.isEmpty(mqName))

        # Purge the queue
        bus.purge(mqName=mqName)

        # Verify that the message queue is now empty
        self.assertEqual(_getQueueMessageCount(mqName), 0)

        self.assertTrue(bus.isEmpty(mqName))


  def testPurgeWithEmptyQueue(self):
    # Verify that puring an empty queue doesn't raise an exception
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Purge the empty queue
        bus.purge(mqName=mqName)

        # Verify that the message queue exists and indeed has no messages
        self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testPurgeWithQueueNotFound(self):
    # Verify that purging a non-existent message queue raises the expected
    # exception
    mqName = self._getUniqueMessageQueueName()

    with MessageBusConnector() as bus:
      with self.assertRaises(MessageQueueNotFound):
        bus.purge(mqName=mqName)


  def testIsEmptyWithEmptyQueue(self):
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        self.assertTrue(bus.isEmpty(mqName))


  def testIsEmptyWithNonEmptyQueue(self):
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add some messages
        bus.publish(mqName, "abc", persistent=True)
        bus.publish(mqName, "def", persistent=True)

        # Verify that the messages were added
        self.assertEqual(_getQueueMessageCount(mqName), 2)

        self.assertFalse(bus.isEmpty(mqName))


  def testIsEmptyWithQueueNotFound(self):
    # Verify that isEmpty on a non-existent message queue raises the expected
    # exception
    mqName = self._getUniqueMessageQueueName()

    with MessageBusConnector() as bus:
      with self.assertRaises(MessageQueueNotFound):
        bus.isEmpty(mqName=mqName)


  def testGetAllMessageQueues(self):
    durableMQ = self._getUniqueMessageQueueName()
    nonDurableMQ = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter((durableMQ, nonDurableMQ)):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=durableMQ, durable=True)
        bus.createMessageQueue(mqName=nonDurableMQ, durable=False)

        allQueues = bus.getAllMessageQueues()

        self.assertIn(durableMQ, allQueues)
        self.assertIn(nonDurableMQ, allQueues)



class MessagePublisherTestCase(_TestCaseBase):
  """ Tests the message queue publishing functionality of
  message_bus_connector.MessageBusConnector """


  def _busMsgPropsVsAmqpClientMsgProps(self, busProps, clientProps):
    """ Test properties for equality

    :param message_bus_connector.MessageProperties busProps:
    :param nta.utils.amqp.messages.BasicProperties
    """
    # NOTE: they happen to have matching attribute names of interest
    attributeNames = (
      "contentType",
      "contentEncoding",
      "headers",
      "deliveryMode",
      "priority",
      "correlationId",
      "replyTo",
      "expiration",
      "messageId",
      "timestamp",
      "messageType",
      "userId",
      "appId"
    )

    def toDict(props):
      return dict((name, getattr(props, name)) for name in attributeNames)

    self.assertDictEqual(toDict(busProps), toDict(clientProps))


  def testPublish(self):
    # Publish messages and verify that they were published
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add some messages - a small and a large one
        msg1 = "a" * 100
        msg2 = "b" * 100000

        bus.publish(mqName, msg1, persistent=True)
        bus.publish(mqName, msg2, persistent=True)

        # Verify that the messages were added
        self.assertEqual(_getQueueMessageCount(mqName), 2)

        connParams = amqp.connection.getRabbitmqConnectionParameters()

        with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
          msg = amqpClient.getOneMessage(mqName, noAck=False)
          self.assertEqual(msg.body, msg1)
          msg.ack()

          msg = amqpClient.getOneMessage(mqName, noAck=False)
          self.assertEqual(msg.body, msg2)
          msg.ack()

        self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testPublishManyMessages(self):
    numMessagesToPublish = 50

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add a bunch of messages
        expectedContent = [str(i) for i in xrange(numMessagesToPublish)]

        _LOGGER.info("testPublishManyMessages: publishing %s tiny messages",
                     numMessagesToPublish)
        for body in expectedContent:
          bus.publish(mqName, body, persistent=True)

        _LOGGER.info("testPublishManyMessages: done publishing %s tiny "
                     "messages", numMessagesToPublish)

      # Verify that the messages were added
      self.assertEqual(_getQueueMessageCount(mqName), numMessagesToPublish)

      connParams = amqp.connection.getRabbitmqConnectionParameters()

      with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
        amqpClient):
        actualContent = []
        for i in xrange(numMessagesToPublish):
          msg = amqpClient.getOneMessage(mqName, noAck=False)
          actualContent.append(msg.body)
          msg.ack()

        self.assertSequenceEqual(actualContent, expectedContent)


  def testPublishWithQueueNotFound(self):
    # Verify that isEmpty on a non-existent message queue raises the expected
    # exception
    mqName = self._getUniqueMessageQueueName()

    with self.assertRaises(MessageQueueNotFound):
      with MessageBusConnector() as bus:
        bus.publish(mqName, "abc", persistent=True)


  def testMessageProperties(self):
    epochNow = int(time.time())

    reference = dict(
      contentType="text/plain",
      contentEncoding="content encoding",
      headers=dict(a="1", b="2", c="3"),
      deliveryMode=amqp.constants.AMQPDeliveryModes.NON_PERSISTENT_MESSAGE,
      priority=3,
      correlationId="myCorrelationId",
      replyTo="replyToMe",
      expiration="100000",
      messageId="myMessageId",
      timestamp=epochNow,
      messageType="myMesageType",
      userId=amqp.connection.RabbitmqConfig().get("credentials", "user"),
      appId="myAppId"
    )

    msgProps = MessageProperties(**reference)

    propsAsDict = dict((key, getattr(msgProps, key)) for key in reference)

    self.assertDictEqual(propsAsDict, reference)


  @amqp_test_utils.RabbitmqVirtualHostPatch(
    clientLabel="testPublishExg",
    logger=_LOGGER)
  def testPublishExg(self):
    """ Basic test for MessageBusConnector.publishExg """

    numMessagesToPublish = 50
    mqName = "testPublishExgQ"
    exgName = "testPublishExg"
    routingKey = "testPublishExg-routing-key"

    connParams = amqp.connection.getRabbitmqConnectionParameters()

    # Create an exchange and bind a message queue to it
    with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
      amqpClient.declareExchange(exgName, exchangeType="direct")

      amqpClient.declareQueue(mqName)

      amqpClient.bindQueue(mqName,
                           exchange=exgName,
                           routingKey=routingKey)

    # Now publish to that exchange via MessageBusConnector
    properties = MessageProperties(
      contentType="text/plain",
      contentEncoding="content encoding",
      headers=dict(a="1", b="2", c="3"),
      deliveryMode=amqp.constants.AMQPDeliveryModes.NON_PERSISTENT_MESSAGE,
      priority=3,
      correlationId="myCorrelationId",
      replyTo="replyToMe",
      expiration="100000",
      messageId="myMessageId",
      timestamp=int(time.time()),
      messageType="myMesageType",
      userId=amqp.connection.RabbitmqConfig().get("credentials", "user"),
      appId="myAppId"
    )
    with MessageBusConnector() as bus:
      # Now add a bunch of messages
      expectedContent = [str(i) for i in xrange(numMessagesToPublish)]

      _LOGGER.info("testPublishExg: publishing %s tiny messages",
                   numMessagesToPublish)
      for i, body in enumerate(expectedContent):
        published = bus.publishExg(
          exchange=exgName,
          routingKey=routingKey,
          body=body,
          properties=copy.deepcopy(properties),
          mandatory=True)

        self.assertTrue(published, msg="Not published at msgIndex=%d" % (i,))

      _LOGGER.info("testPublishExg: done publishing %d tiny "
                   "messages", len(expectedContent))

    # Verify that the messages were added
    self.assertEqual(_getQueueMessageCount(mqName), numMessagesToPublish)

    with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
      actualContent = []
      for i in xrange(numMessagesToPublish):
        msg = amqpClient.getOneMessage(mqName, noAck=False)
        actualContent.append(msg.body)
        msg.ack()

        rxProps = msg.properties

        _LOGGER.info("rx properties=%s", rxProps)
        self._busMsgPropsVsAmqpClientMsgProps(properties, rxProps)

      self.assertSequenceEqual(actualContent, expectedContent)


  @amqp_test_utils.RabbitmqVirtualHostPatch(
    clientLabel="testPublishExgNotPublished",
    logger=_LOGGER)
  def testPublishExgNotPublished(self):
    """ Test MessageBusConnector.publishExg returns false when failed to publish
    immediately
    """
    exgName = "testPublishExgNotPublished"
    routingKey = "testPublishExgNotPublished-routing-key"

    # Create an exchange, but don't bind a queue to it
    connParams = amqp.connection.getRabbitmqConnectionParameters()
    with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
      amqpClient.declareExchange(exgName, exchangeType="direct")

    # Now publish to that exchange via MessageBusConnector
    with MessageBusConnector() as bus:
      # Now attempt to publish a single message with mandatory=True

      published = bus.publishExg(
        exchange=exgName,
        routingKey=routingKey,
        body="testPublishExgNotPublished-body",
        properties=None,
        mandatory=True)

    # Verify that the message failed to publish
    self.assertFalse(published)



class MessageConsumerTestCase(_TestCaseBase):
  """ Tests the consumer functionality of
  message_bus_connector.MessageBusConnector """

  def testPollOneMessage(self):
    # Verify that it can retrieve a message by polling
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName, durable=True)

        with bus.consume(mqName) as consumer:
          # Now add some messages
          msgBody1 = "a" * 100
          msgBody2 = "b" * 100000

          bus.publish(mqName, msgBody1, persistent=True)
          bus.publish(mqName, msgBody2, persistent=True)

          msg = consumer.pollOneMessage()
          msg.ack()
          self.assertEqual(msg.body, msgBody1)

          msg = consumer.pollOneMessage()
          msg.ack()
          self.assertEqual(msg.body, msgBody2)

          msg = consumer.pollOneMessage()
          self.assertIsNone(msg)

        # Verify that consumer's context manager cleaned up
        self.assertIsNone(consumer._channelMgr)

      # Verify that the message queue is empty now
      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testPollOneMessageWithQueueNotFound(self):
    # Verify that calling pollOneMessage on a non-existent queue raises the
    # expected exception
    mqName = self._getUniqueMessageQueueName()

    with MessageBusConnector() as bus:
      with self.assertRaises(MessageQueueNotFound):
        with bus.consume(mqName) as consumer:
          consumer.pollOneMessage()


  def testPollOneMessageWithUnackedMessagesReturnedToQueue(self):
    # Verify that unacked messages retrieved by polling are returned to the
    # queue after closing the MessageBusConnector instance

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Publish messages to the queue
        expectedContent = [str(i) for i in xrange(10)]
        for body in expectedContent:
          bus.publish(mqName, body, persistent=True)

      # Retrive the published messages without acking them
      actualContent = []
      with MessageBusConnector() as bus:
        with bus.consume(mqName) as consumer:
          for i in xrange(len(expectedContent)):
            msg = consumer.pollOneMessage()
            actualContent.append(msg.body)

          msg = consumer.pollOneMessage()
          self.assertIsNone(msg)

      self.assertEqual(actualContent, expectedContent)
      del actualContent

      # Now read them again, they should have been returned to the message queue
      # in the original order.
      # NOTE: RabbitMQ broker restores them back in original order, but this is
      #   not mandated by AMQP 0.9.1
      actualContent = []
      with MessageBusConnector() as bus:
        with bus.consume(mqName) as consumer:
          for i in xrange(len(expectedContent)):
            msg = consumer.pollOneMessage()
            actualContent.append(msg.body)
            msg.ack()

          msg = consumer.pollOneMessage()
          self.assertIsNone(msg)

      self.assertEqual(actualContent, expectedContent)

      # Verify that the message queue is empty now
      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testConsumerIterable(self):
    # Create a message queue, publish some messages to it, and then use
    # the message consumer iterable to retrieve those messages
    numMessagesToPublish = 10

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add a bunch of messages
        expectedContent = []

        for i in xrange(numMessagesToPublish):
          expectedContent.append(str(i))
          bus.publish(mqName, expectedContent[-1], persistent=True)

        # Verify that correct number of messages were published
        self.assertEqual(_getQueueMessageCount(mqName), numMessagesToPublish)

      # Now, create a consumer iterable and consume the messages
      # NOTE: we use a thread to avoid deadlocking the test runner in case
      #  something is wrong with the iterable
      def runConsumerThread(mqName, numMessages, resultQ):
        try:
          with MessageBusConnector() as bus:
            with bus.consume(mqName=mqName) as consumer:
              it = iter(consumer)
              for _i in xrange(numMessages):
                msg = next(it)
                resultQ.put(msg.body)
                msg.ack()
        except:
          resultQ.put(dict(exception=sys.exc_info()[1]))
          raise

      resultQ = Queue.Queue()
      consumerThread = threading.Thread(
        target=runConsumerThread,
        args=(mqName, numMessagesToPublish, resultQ))
      consumerThread.setDaemon(True)
      consumerThread.start()

      consumerThread.join(timeout=30)
      self.assertFalse(consumerThread.isAlive())

      # Verify content
      actualContent = []
      while True:
        try:
          actualContent.append(resultQ.get_nowait())
        except Queue.Empty:
          break

      self.assertEqual(actualContent, expectedContent)

      # Verify that the message queue is now empty
      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testConsumerIterableNonBlocking(self):
    # Create a message queue, publish some messages to it, and then use
    # the a non-blocking message consumer iterable to retrieve those messages
    numMessagesToPublish = 10

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add a bunch of messages
        expectedContent = [str(i) for i in xrange(numMessagesToPublish)]

        for body in expectedContent:
          bus.publish(mqName, body, persistent=True)

        # Verify that correct number of messages were published
        self.assertEqual(_getQueueMessageCount(mqName), numMessagesToPublish)

      # Now, create a non-blocking consumer iterable and consume the messages
      # NOTE: we use a thread to avoid deadlocking the test runner in case
      #  something is wrong with the iterable
      def runConsumerThread(mqName, resultQ):
        try:
          with MessageBusConnector() as bus:
            with bus.consume(mqName=mqName, blocking=False) as consumer:
              for msg in consumer:
                resultQ.put(msg.body)
                msg.ack()
        except:
          resultQ.put(dict(exception=sys.exc_info()[1]))
          raise

      resultQ = Queue.Queue()
      consumerThread = threading.Thread(
        target=runConsumerThread,
        args=(mqName, resultQ))
      consumerThread.setDaemon(True)
      consumerThread.start()

      consumerThread.join(timeout=10)
      self.assertFalse(consumerThread.isAlive())

      # Verify content
      actualContent = []
      while True:
        try:
          actualContent.append(resultQ.get_nowait())
        except Queue.Empty:
          break

      self.assertEqual(actualContent, expectedContent)

      # Verify that the message queue is now empty
      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testConsumerIterableWithQueueNotFound(self):
    # Verify that using consumer iterable with non-existent queue raises the
    # expected exception
    mqName = self._getUniqueMessageQueueName()

    # Now, create a consumer iterable and attempt to consume the messages
    # NOTE: we use a thread to avoid deadlocking the test runner in case
    #  something is wrong with the iterable
    def runConsumerThread(mqName, resultQ):
      try:
        with MessageBusConnector() as bus:
          with bus.consume(mqName=mqName) as consumer:
            # NOTE: we actually don't expect any messages in this test
            for msg in consumer:
              msg.ack()
      except:  # pylint: disable=W0702
        # NOTE: this is what we expect in this test since the mq wasn't created
        resultQ.put(dict(exception=sys.exc_info()[1]))

    resultQ = Queue.Queue()
    consumerThread = threading.Thread(
      target=runConsumerThread,
      args=(mqName, resultQ))
    consumerThread.setDaemon(True)
    consumerThread.start()

    consumerThread.join(timeout=30)
    self.assertFalse(consumerThread.isAlive())

    # Verify the exception
    exception = resultQ.get_nowait()["exception"]
    self.assertIsInstance(exception, MessageQueueNotFound)
    try:
      item = resultQ.get_nowait()
    except Queue.Empty:
      pass
    else:
      self.fail("Unexpected item in resultQ: %r" % (item,))


  def testConsumerIterableWithUnackedMessagesReturnedToQueue(self):
    # Verify that it can retrieve a message by polling
    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Add the number of messages equal to MessageBusConnector's prefetch
        # limit
        expectedContent = [str(i) for i
                           in xrange(MessageBusConnector._PREFETCH_MAX)]
        for body in expectedContent:
          bus.publish(mqName, body, persistent=True)

      # Retrive the published messages without acking them
      def runConsumerThread(mqName, numMessages, resultQ):
        try:
          with MessageBusConnector() as bus:
            with bus.consume(mqName=mqName) as consumer:
              it = iter(consumer)
              for _i in xrange(numMessages):
                # Read and don't ack
                msg = next(it)
                resultQ.put(msg.body)
        except:
          resultQ.put(dict(exception=sys.exc_info()[1]))
          raise

      resultQ = Queue.Queue()
      consumerThread = threading.Thread(
        target=runConsumerThread,
        args=(mqName, MessageBusConnector._PREFETCH_MAX, resultQ))
      consumerThread.setDaemon(True)
      consumerThread.start()

      consumerThread.join(timeout=30)
      self.assertFalse(consumerThread.isAlive())

      # Verify the retrieved unacked content
      actualContent = []
      while True:
        try:
          actualContent.append(resultQ.get_nowait())
        except Queue.Empty:
          break

      self.assertEqual(actualContent, expectedContent)
      del actualContent

      # Now read them again, they should have been returned to the message queue
      # NOTE: RabbitMQ broker restores them back in original order
      actualContent = []
      with MessageBusConnector() as bus:
        with bus.consume(mqName=mqName) as consumer:
          for i in xrange(MessageBusConnector._PREFETCH_MAX):
            msg = consumer.pollOneMessage()
            actualContent.append(msg.body)
            msg.ack()

          msg = consumer.pollOneMessage()
          self.assertIsNone(msg)

      self.assertEqual(actualContent, expectedContent)

      # Verify that the message queue is empty now
      self.assertEqual(_getQueueMessageCount(mqName), 0)


  def testMessageBusConnectorCleanupOfConsumerGenerators(self):
    # Verify that MessageBusConnector closes unclosed consumers
    numMessagesToPublish = 1

    mqName = self._getUniqueMessageQueueName()

    with amqp_test_utils.managedQueueDeleter(mqName):
      with MessageBusConnector() as bus:
        # Create the queue
        bus.createMessageQueue(mqName=mqName, durable=True)

        # Now add messages
        expectedContent = []

        for i in xrange(numMessagesToPublish):
          expectedContent.append(str(i))
          bus.publish(mqName, expectedContent[-1], persistent=True)

        # Verify that correct number of messages were published
        self.assertEqual(_getQueueMessageCount(mqName), numMessagesToPublish)

      bus = MessageBusConnector()

      # Now, create a consumer iterable and start it by consuming the expected
      # messages
      # NOTE: we use a thread to avoid deadlocking the test runner in case
      #  something is wrong with the iterable
      def runConsumerThread(bus, mqName, numMessages, resultQ):
        try:
          # NOTE: in this test, we intentionally don't close the consumer
          consumer = bus.consume(mqName=mqName)
          resultQ.put(consumer)
          it = iter(consumer)
          for _i in xrange(numMessages):
            msg = next(it)
            msg.ack()
            resultQ.put(msg.body)
        except:
          resultQ.put(dict(exception=sys.exc_info()[1]))
          raise

      resultQ = Queue.Queue()
      consumerThread = threading.Thread(
        target=runConsumerThread,
        args=(bus, mqName, numMessagesToPublish, resultQ))
      consumerThread.setDaemon(True)
      consumerThread.start()

      # Wait for thread to stop
      consumerThread.join(timeout=30)
      self.assertFalse(consumerThread.isAlive())

      # Reap the consumer
      consumer1 = resultQ.get_nowait()
      self.assertIsInstance(consumer1, message_bus_connector._QueueConsumer)

      # Verify content
      actualContent = []
      while True:
        try:
          actualContent.append(resultQ.get_nowait())
        except Queue.Empty:
          break

      self.assertEqual(actualContent, expectedContent)

      # Verify that this consumer isn't closed
      self.assertEqual(len(bus._consumers), 1)
      self.assertIn(consumer1, bus._consumers)
      self.assertIsNotNone(consumer1._channelMgr)

      # Create another consumer, but don't start it (by telling it to consume 0
      # messages; we want to test cleanup of both started and unstarted
      # consumers
      resultQ = Queue.Queue()
      consumerThread = threading.Thread(
        target=runConsumerThread,
        args=(bus, mqName, 0, resultQ))
      consumerThread.setDaemon(True)
      consumerThread.start()

      # Wait for thread to stop
      consumerThread.join(timeout=30)
      self.assertFalse(consumerThread.isAlive())

      # Reap the consumer
      consumer2 = resultQ.get_nowait()
      self.assertIsInstance(consumer2, message_bus_connector._QueueConsumer)

      try:
        item = resultQ.get_nowait()
      except Queue.Empty:
        pass
      else:
        self.fail("Unexpected item in resultQ: %r" % (item,))

      # Verify that this consumer isn't closed
      self.assertEqual(len(bus._consumers), 2)
      self.assertIn(consumer2, bus._consumers)
      self.assertIsNotNone(consumer2._channelMgr)

      # Verify that this consumer hasn't started
      self.assertIsNone(consumer2._channelMgr._client)

      # Verify that the first consumer is still there, too
      self.assertIn(consumer1, bus._consumers)


      # Finanly, close the MessageBusConnector and verify that both consumers
      # got closed, too
      bus.close()

      self.assertFalse(bus._consumers)

      self.assertIsNone(consumer1._channelMgr)
      self.assertIsNone(consumer1._bus)
      self.assertIsNone(consumer1._channelMgr)

      self.assertIsNone(consumer2._channelMgr)
      self.assertIsNone(consumer2._bus)
      self.assertIsNone(consumer2._channelMgr)



if __name__ == '__main__':
  unittest.main()
