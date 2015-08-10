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
Message Bus Connector for communication between services.
"""

from collections import namedtuple
import contextlib
import json
import logging
import select
import socket
import time

import requests

from nta.utils import error_handling
from nta.utils import amqp

g_log = logging.getLogger("nta.utils.message_bus_connector")



class MessageBusConnectorError(Exception):
  """ Base exception class for MessageBusConnector error exceptions """
  pass



class MessageQueueNotFound(MessageBusConnectorError):
  """ The requested message queue was not found (already deleted?) """
  pass



class ConsumerCancelled(MessageBusConnectorError):
  """Message consumer was cancelled by remote peer"""
  pass



# Decorator for retrying operations on potentially-transient AMQP errrors
_RETRY_ON_AMQP_ERROR = error_handling.retry(
  timeoutSec=10, initialRetryDelaySec=0.05, maxRetryDelaySec=2,
  retryExceptions=(
    amqp.exceptions.AmqpChannelError,
    amqp.exceptions.AmqpConnectionError,
    amqp.exceptions.UnroutableError,
    socket.gaierror,
    socket.error,
    select.error,
  ),
  logger=g_log
)



class MessageProperties(amqp.messages.BasicProperties):
  """ basic.Properties of a message per AMQP 0.9.1

  Some attributes are used by AMQP brokers, but most are open to interpretation
  by applications that receive them.
  """
  pass


class MessageBusConnector(object):
  """
  An instance of this class represents a connection to the message bus.
  Presently, it provides primitives based on message queues. Both durable and
  non-durable message queues are supported.

  NOTE: An instance of this class is NOT thread-safe. Use an instance per thread
  if needed.
  """

  _PERSISTENT_PUBLISH_PROPERTIES = amqp.messages.BasicProperties(
      deliveryMode=amqp.constants.AMQPDeliveryModes.PERSISTENT_MESSAGE)

  # This is the limit for how many unacked messages the broker may deliver
  _PREFETCH_MAX = 2


  def __init__(self):
    self._logger = g_log

    def configureChannel(client):
      """
      For publisher

      :param amqp.synchronous_amqp_client.SynchronousAmqpClient client:
      """
      # This makes sure that the broker ACKs/NACKs a message after it takes
      # complete responsibility for it (e.g., saves to disk for persistent
      # messages) or returns the message
      client.enablePublisherAcks()

    self._channelMgr = _ChannelManager(configureChannel=configureChannel)

    # Active _QueueConsumer instances
    self._consumers = []


  def __enter__(self):
    return self


  def __exit__(self, _excType, _excVal, _excTb):
    self.close()
    return False


  def close(self):
    if self._consumers:
      self._logger.error(
        "While closing %s, discovered %s unclosed consumers; will "
        "attempt to close them now", self.__class__.__name__,
        len(self._consumers))
      for consumer in tuple(self._consumers):
        consumer.close()

      assert not self._consumers

    try:
      self._channelMgr.close()
    finally:
      self._channelMgr = None


  @_RETRY_ON_AMQP_ERROR
  def createMessageQueue(self, mqName, durable):
    """ Create a persistent Message Queue

    mqName: name of the existing destination message queue
    durable: True to create it as durable so its contents will be backed up to
      disk (performance vs. reliability); False for non-durable
    """
    self._channelMgr.client.declareQueue(queue=mqName,
                                         durable=durable,
                                         exclusive=False,
                                         autoDelete=False)
    self._logger.info("Declared mq=%s", mqName)


  @_RETRY_ON_AMQP_ERROR
  def deleteMessageQueue(self, mqName):
    """ Delete a message queue, if it exists; also returns successfully if the
    message queue didn't exist at the time of the call.

    mqName: name of the existing destination message queue

     NOTE: deleting an entity that doesn't exist used to result in NOT_FOUND=404
     channel error from RabbitMQ. However, more recent versions of RabbitMQ
     changed the behavior such that it now completes with success. Per
     https://www.rabbitmq.com/specification.html: "We have made queue.delete
     into an idempotent assertion that the queue must not exist, in the same way
     that queue.declare asserts that it must."

     So, to provide our clients the same semantics with both old and new
     RabbitMQ broker versions, we suppress the NOT_FOUND=404 error.
    """

    try:
      numMsgDeleted = self._channelMgr.client.deleteQueue(mqName,
                                                          ifUnused=False,
                                                          ifEmpty=False)
      self._logger.info("Deleted mq=%s; messageCount=%s", mqName, numMsgDeleted)
    except amqp.exceptions.AmqpChannelError as e:
      if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
        # Suppress the exception
        self._channelMgr.reset()
        self._logger.warn(
          "You appear to be using an older version of RabbitMQ broker: "
          "attempted to delete mq=%s, but broker reported not-found (%r). "
          "See https://www.rabbitmq.com/specification.html", mqName, e)
      else:
        raise


  @_RETRY_ON_AMQP_ERROR
  def purge(self, mqName):
    """ Purge all unacknowledged messages from message queue

    mqName: name of the existing destination message queue

    raises: MessageQueueNotFound
    """
    try:
      self._channelMgr.client.purgeQueue(mqName)
    except amqp.exceptions.AmqpChannelError as e:
      if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
        self._channelMgr.reset()
        self._logger.error("Attempted purge of mq=%s, but it wasn't found "
                           "(probably deleted?) (%r)", mqName, e)
        raise MessageQueueNotFound("purge: mq=%s not found" % (mqName,))

      else:
        raise


  @_RETRY_ON_AMQP_ERROR
  def isEmpty(self, mqName):
    """
    raises: MessageQueueNotFound
    """
    try:
      r = self._channelMgr.client.declareQueue(mqName,
                                               passive=True)
      return r.messageCount == 0
    except amqp.exceptions.AmqpChannelError as e:
      if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
        self._channelMgr.reset()
        raise MessageQueueNotFound(
          "isEmpty: mq=%s not found (%r)" % (mqName, e,))
      else:
        raise


  def isMessageQeueuePresent(self, mqName):
    """
    retval: True if the queue exists; False if it doesn't exist

    TODO: need test for isMessageQeueuePresent (MER-948)
    """
    # NOTE: we implement this on top of isEmpty(), which already uses
    # _RETRY_ON_AMQP_ERROR, so we don't need retries on this method.

    try:
      self.isEmpty(mqName)
    except MessageQueueNotFound:
      return False
    else:
      return True


  def getAllMessageQueues(self):
    """ Get all message queue names

    retval: (possibly empty) sequence of message queue names
    """
    connectionParams = (
        amqp.connection.RabbitmqManagementConnectionParams())

    # Use RabbitMQ Management Plugin to retrieve the names of message
    # queues

    # Buld a URL for retrieving queue names from the default vhost
    # NOTE: we encode the default vhost name ("/") in hex because it cannot be
    # passed verbatim in the URL
    vhost = connectionParams.vhost
    url = "http://%s:%s/api/queues/%s" % (
      connectionParams.host, connectionParams.port,
      vhost if vhost != "/" else "%" + vhost.encode("hex"))

    response = None
    try:
      response = requests.get(
        url,
        auth=(connectionParams.username,
              connectionParams.password),
        params={"columns": "name"})

      response.raise_for_status()
    except Exception:
      self._logger.exception(
        "getAllMessageQueues failed; url=%r; response=%r", url, response)
      raise


    return tuple(d["name"] for d in json.loads(response.text))


  @_RETRY_ON_AMQP_ERROR
  def publish(self, mqName, body, persistent):
    """ Publish a message to the queue; delivers message to the queue or "dies"
    trying. Assumes the message queue already exists. See
    `MessageBusConnector.publishExg`

    NOTE: provides an "at-least-once" delivery guarantee on success. The
      current underlying MQ broker RabbitMQ doesn't provide "exactly-once"
      semantics)

    mqName: name of the existing destination message queue
    body: The message body (string)
    persistent: True to have the message backed up to disk; this only makes
      sense if the message queue was created as "durable" (
      see createMessageQueue). False for no backup.

    raises: MessageQueueNotFound
    """
    if not mqName:
      raise ValueError("Name cannot be empty or None: %r" % (mqName,))

    msg = amqp.messages.Message(body,
                       properties=(self._PERSISTENT_PUBLISH_PROPERTIES
                                   if persistent else None))

    # NOTE: when using the default exchange (""), the the routing key is used
    #   to select the destination queue
    try:
      self._channelMgr.client.publish(msg,
                                      exchange="",
                                      routingKey=mqName,
                                      mandatory=True)
    except amqp.exceptions.UnroutableError:
      raise MessageQueueNotFound("Could not deliver message to mq=%s; did "
                                 "you delete the mq or forget to create it?"
                                 % (mqName,))


  @_RETRY_ON_AMQP_ERROR
  def publishExg(self,
                 exchange,
                 routingKey,
                 body,
                 properties=None,
                 mandatory=False):
    """ Publish a message to an exchange with retries on transient errors.

    :param str exchange: Name of destination exchange; the exchange name can be
      empty string, meaning the default exchange.
    :param str routingKey: Routing key for the message
    :param body: The message body (byte string)
    :param message_bus_connector.MessageProperties properties: message
      properties
    :param bool mandatory: "This flag tells the server how to react if the
      message cannot be routed to a queue. If this flag is set, the server will
      return an unroutable message with a Return method. If this flag is zero,
      the server silently drops the message."

    :returns: True on success, False on failure; see more info in docstring for
      the arg `mandatory`
    :rtype: bool
    """
    # NOTE: when using the default exchange (""), the the routing key is used
    #   to select the destination queue
    msg = amqp.messages.Message(body, properties=properties)
    try:
      self._channelMgr.client.publish(
        msg,
        exchange=exchange,
        routingKey=routingKey,
        mandatory=mandatory)
    except amqp.exceptions.UnroutableError:
      return False

    return True


  def consume(self, mqName, blocking=True):
    """ Create an instance of _QueueConsumer iterable for consuming messages.
    The iterable yields an instance of _ConsumedMessage.

    mqName: name of the existing source message queue
    blocking: if True, the iterable will block until another message becomes
      available; if False, the iterable will terminate iteration when no more
      messages are available in the queue. [Defaults to blocking=True]

    The iterable raises: MessageQueueNotFound

    Blocking iterable example:
      with MessageBusConnector() as bus:
        with bus.consume("myqueue") as consumer:
          for msg in consumer:
            processMessageBody(msg.body)
            msg.ack()

    Polling example:
      with MessageBusConnector() as bus:
        with bus.consume("myqueue") as consumer:
          msg = consumer.pollOneMessage()
          if msg is not None:
            processMessageBody(msg.body)
            msg.ack()
    """
    consumer = _QueueConsumer(
      mqName=mqName,
      blocking=blocking,
      prefetchMax=self._PREFETCH_MAX,
      bus=self)

    self._consumers.append(consumer)

    return consumer


  def _onConsumerClosed(self, consumer):
    """ Called by consumer instances to decouple themselves from this
    MessageBusConnector instance.
    """
    self._consumers.remove(consumer)



# Message container for a consumed message
#
# body: the body of the message (string)
# ack: function to call to ack the message: NoneType ack(multiple=False)
#  TODO: Need test for ack with multiple=True (MER-948)
_ConsumedMessage = namedtuple(  # pylint: disable=C0103
  "_ConsumedMessage",
  "body ack")



class _QueueConsumer(object):
  """ Consumer interface implementation for a given message queue

  An instance of this class is an iterable that yields _ConsumedMessage
  instances
  """

  def __init__(self, mqName, blocking, prefetchMax, bus):
    """
    param mqName: Message queue name to associate with this consumer
    param blocking: if True, the iterable will block until another message
      becomes available; if False, the iterable will terminate iteration when no
      more messages are available in the queue.
    param prefetchMax:
    param bus: host MessageBusConnector instance
    """
    self._logger = g_log
    self._mqName = mqName
    self._blocking = blocking
    self._bus = bus

    def configureChannel(client):
      """
      For consumer

      :param amqp.synchronous_amqp_client.SynchronousAmqpClient client:
      """
      # NOTE: prefetch_count doesn't apply to the polling mode
      if self._blocking:
        client.requestQoS(prefetchCount=prefetchMax)

    # The consumer maintains its own channel so that consumed messages may be
    # acked, etc., independently of errors from other operations on the host
    # message bus connection channel.
    self._channelMgr = _ChannelManager(configureChannel=configureChannel)


  def __enter__(self):
    return self


  def __exit__(self, _excType, _excVal, _excTb):
    self.close()
    return False


  def __iter__(self):
    """ yield an instance of _ConsumedMessage when a message becomes available

    :raises MessageQueueNotFound:
    :raises ConsumerCancelled:
    """
    sleepOnFailureSec = 0.2
    failureSequenceStartTime = None
    failureWindowSec = 30
    maxFailures = 10
    numFailures = 0

    @_RETRY_ON_AMQP_ERROR
    def getAmqpClientWithRetries():
      return self._channelMgr.client

    def consumeNonBlocking(amqpClient, mqName):
      self._logger.debug("Entering non-blocking consumer for mq=%s", mqName)
      numRetrieved = 0
      try:
        while True:
          message = amqpClient.getOneMessage(mqName, noAck=False)

          if message is not None:
            numRetrieved += 1
            yield message

          else:
            self._logger.debug(
              "Non-blocking consumer generator detected end of messages in "
              "mq=%s; numRetrieved=%s", mqName, numRetrieved)
            break
      finally:
        self._logger.debug(
          "Leaving non-blocking consumer generator for mq=%s; numRetrieved=%s",
          mqName, numRetrieved)


    def consumeBlocking(amqpClient, mqName):
      self._logger.debug("Entering blocking consumer for mq=%s", mqName)
      numRetrieved = 0

      consumer = amqpClient.createConsumer(mqName,
                                           noLocal=False,
                                           noAck=False,
                                           exclusive=False)
      try:
        while True:
          evt = amqpClient.getNextEvent()
          if type(evt) is amqp.messages.ConsumerMessage:

            assert evt.methodInfo.consumerTag == consumer.tag, (
              evt.methodInfo.consumerTag, consumer, evt)

            numRetrieved += 1
            yield evt

          elif type(evt) is amqp.consumer.ConsumerCancellation:
            # NOTE: this may happen when the consumed queue is deleted

            assert evt.consumerTag == consumer.tag, (evt, consumer)

            errorMessage = ("Blocking consumer cancelled by broker "
                            "evt=%r; consumer=%r; numRetrieved=%s"
                            % (evt, consumer, numRetrieved))
            self._logger.error(errorMessage)

            raise ConsumerCancelled(errorMessage)

          else:
            raise MessageBusConnectorError("Unexpected event=%r; consumer=%r" %
                                           (evt, consumer))

      finally:
        self._logger.debug(
          "Leaving blocking consumer generator consumer=%r; numRetrieved=%s",
          consumer, numRetrieved)



    # Retrieve messages from the queue, while attemting to recover from AMQP
    # channel and connection closures
    done = False
    while not done:
      amqpClient = getAmqpClientWithRetries()

      if self._blocking:
        source = consumeBlocking(amqpClient, self._mqName)
      else:
        source = consumeNonBlocking(amqpClient, self._mqName)

      try:
        for message in source:
          yield _ConsumedMessage(body=message.body, ack=message.ack)
        else:
          assert not self._blocking, (
            "Unexpected termination of blocking iterator")
          done = True
      except (amqp.exceptions.AmqpChannelError,
            amqp.exceptions.AmqpConnectionError) as e:
        if isinstance(e, amqp.exceptions.AmqpChannelError):
          if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
            self._logger.error("Requested server entity not found (%r)", e)
            raise MessageQueueNotFound("_QueueConsumer: mq=%s not found"
                                       % self._mqName)
          else:
            self._logger.exception(
              "Channel closed while in consumer loop, will reconnect shortly")
        else:
          self._logger.exception(
            "Connection closed while in consumer loop, will reconnect shortly")

        # Initiate connection/channel failure recovery
        if failureSequenceStartTime is None:
          failureSequenceStartTime = time.time()

        numFailures += 1

        if numFailures >= maxFailures:
          if time.time() - failureSequenceStartTime <= failureWindowSec:
            self._logger.exception("Too many connection and/or channel errors")
            raise
          else:
            numFailures = 0
            failureSequenceStartTime = time.time()

        time.sleep(sleepOnFailureSec)


  def close(self):
    if self._channelMgr is None:
      return

    self._bus._onConsumerClosed(self)  # pylint: disable=W0212
    self._bus = None

    try:
      self._channelMgr.close()
    finally:
      self._channelMgr = None


  @_RETRY_ON_AMQP_ERROR
  def pollOneMessage(self):
    """ Poll for a single message. Assumes the message queue already exists.

    retval: _ConsumedMessage instance if message was available; None
      if not. NOTE: the caller is responsible for acking the message by calling
      ack on the returned _ConsumedMessage instance:
        NoneType ack(multiple=False)

    raises: MessageQueueNotFound
    """
    amqpClient = self._channelMgr.client

    try:
      message = amqpClient.getOneMessage(self._mqName, noAck=False)
    except amqp.exceptions.AmqpChannelError as e:
      if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
        self._logger.error("Requested server entity not found (%r)", e)
        raise MessageQueueNotFound("pollOneMessage: mq=%s not found (%r)"
                                   % (self._mqName, e,))
      else:
        raise

    if message is not None:
      return _ConsumedMessage(body=message.body, ack=message.ack)



class _ChannelManager(object):
  """
  NOT thread-safe
  """

  _CLIENT_CLASS = amqp.synchronous_amqp_client.SynchronousAmqpClient

  def __init__(self, configureChannel=None):
    """
    configureChannel: Function to call to configure channel after channel is
      created: NoneType
      configureChannel(amqp.synchronous_amqp_client.SynchronousAmqpClient)
    """
    self._logger = g_log

    # Function to call on channel after channel is created or re-created;
    # passed as channelConfigCb arg to
    # amqp.synchronous_amqp_client.SynchronousAmqpClient
    self._configureChannel = configureChannel

    # AMQP client
    self._client = None


  @property
  def client(self):
    """ Returns the underlying AMQP client instance, (re)connecting and
    (re)establishing the channel as needed
    """
    self._refreshChannelNoRetries()
    return self._client


  def reset(self):
    """ Reset channel so that a subsequent access of the `channel`
    property-getter will cause refresh of the channel/connection
    """
    if self._client is not None:
      try:
        self._client.close()
      finally:
        self._client = None


  def close(self):
    """ Close Channel Manager; it's not reusable after this call """
    self.reset()
    self._configureChannel = None
    self._logger.debug("Closed")


  def _connectToBrokerNoRetries(self):
    connectionParams = amqp.connection.getRabbitmqConnectionParameters()

    g_log.debug("Connecting to broker at %s:%d as %s",
                connectionParams.host, connectionParams.port,
                connectionParams.credentials.username)

    return self._CLIENT_CLASS(connectionParams,
                              channelConfigCb=self._configureChannel)


  def _refreshChannelNoRetries(self):
    if self._client is not None:
      if not self._client.isOpen():
        self.reset()
        self._logger.warn("Reconnecting to broker due to closed client")

    if self._client is None:
      try:
        self._client = self._connectToBrokerNoRetries()
        self._logger.debug("Connected to broker")
      except Exception:
        self._logger.exception("Failed while connecting to broker")
        raise
