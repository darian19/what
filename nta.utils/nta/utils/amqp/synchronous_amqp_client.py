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
AMQP synchronous client.

TODO need unit tests
"""
from collections import deque
from datetime import datetime
import logging
import socket

from haigha.connections.rabbit_connection import RabbitConnection
from haigha.message import Message as HaighaMessage

from nta.utils.date_time_utils import epochFromNaiveUTCDatetime

from nta.utils.amqp import connection as amqp_connection
from nta.utils.amqp import consumer as amqp_consumer
from nta.utils.amqp import exceptions as amqp_exceptions
from nta.utils.amqp import messages as amqp_messages
from nta.utils.amqp import queue as amqp_queue

g_log = logging.getLogger(__name__)



class _CallbackSink(object):

  __slots__ = ("values",)

  def __init__(self):
    self.values = []

  def __call__(self, *args):
    self.values.append(args)

  @property
  def ready(self):
    return bool(self.values)

  def __repr__(self):
    return "%s(ready=%s, values=%.255r)" % (self.__class__.__name__,
                                            self.ready,
                                            self.values)


class _PubackState(_CallbackSink):

  __slots__ = ()

  ACK = 1
  NACK = 2

  def handleAck(self, deliveryTag):
    """Message Ack'ed in RabbitMQ Publisher Acknowledgments mode"""
    g_log.debug("Message ACKed: tag=%s", deliveryTag)

    assert not self.ready, (deliveryTag, self.values)

    self(self.ACK, deliveryTag)

  def handleNack(self, deliveryTag):
    """Message Nack'ed in RabbitMQ Publisher Acknowledgments mode"""
    g_log.error("Message NACKed: tag=%s", deliveryTag)

    assert not self.ready, (deliveryTag, self.values)

    self(self.NACK, deliveryTag)


class _ChannelContext(object):

  __slots__ = ("channel", "nextConsumerTag", "consumerSet", "pendingEvents",
               "pubacksSelected", "returnedMessages")

  def __init__(self, channel):
    self.channel = None
    self.nextConsumerTag = None

    # Consumer tags of active consumers
    self.consumerSet = None

    # Events pending delivery via SynchronousAmqpClient.getNextEvent
    self.pendingEvents = None

    # True after publisher-acknowledgments mode has been selected
    self.pubacksSelected = None

    # Holds messages of type ReturnedMessage received via Basic.Return
    self.returnedMessages = None

    self.reset()
    self.channel = channel

  def reset(self):
    """ Reset member variables to default state """
    self.channel = None
    self.nextConsumerTag = 1

    # Consumer tags of active consumers
    self.consumerSet = set()

    # Events pending delivery via SynchronousAmqpClient.getNextEvent
    self.pendingEvents = deque()

    # True after publisher-acknowledgments mode has been selected
    self.pubacksSelected = False

    # Holds messages of type ReturnedMessage received via Basic.Return
    self.returnedMessages = []


  def __repr__(self):
    return ("%s(channel=%s, nextConsumerTag=%s, pubacksSelected=%s, "
            "numReturned=%s, numCons=%s, numEvts=%s)") % (
              self.__class__.__name__,
              self.channel.channel_id if self.channel is not None else None,
              self.nextConsumerTag, self.pubacksSelected,
              len(self.returnedMessages), len(self.consumerSet),
              len(self.pendingEvents))


  def ack(self, deliveryTag, multiple):
    """ Acks a messages or multiple messages using the context's channel.

    NOTE: This method is passed to the constructors of _AckableMessage
    subclasses as implementation of Ack to make sure that the Ack will be
    attempted on the channel whence the message originated.

    NOTE: behavior is undefined on messages received with no-ack=True

    :param int deliveryTag: delivery tag of message being acknowledged
    :param bool multiple: If true, the delivery tag is treated as "up to and
      including", so that the client can acknowledge multiple messages with a
      single method. If false, the delivery tag refers to a single
      message. If the multiple is true, and the delivery tag is zero, tells
      the server to acknowledge all outstanding messages.
    """
    self.channel.basic.ack(delivery_tag=deliveryTag, multiple=multiple)

  def nack(self, deliveryTag, multiple, requeue):
    """ Nacks a messages or multiple messages using the context's channel

    NOTE: This method is passed to the constructors of _AckableMessage
    subclasses as implementation of Nack to make sure that the Nack will be
    attempted on the channel whence the message originated.

    NOTE: behavior is undefined on messages received with no-ack=True

    :param int deliveryTag: delivery tag of message being acknowledged
    :param bool multiple: If true, the delivery tag is treated as "up to and
      including", so that multiple messages can be rejected with a single
      method. If false, the delivery tag refers to a single message. If the
      multiple true, and the delivery tag is zero, this indicates rejection of
      all outstanding messages.
    :param bool requeue: If requeue is true, the server will attempt to
      requeue the message. If requeue is false or the requeue attempt fails
      the messages are discarded or dead-lettered
    """
    self.channel.basic.nack(delivery_tag=deliveryTag,
                            multiple=multiple,
                            requeue=requeue)

  def cancelConsumer(self, consumerTag):
    """This method cancels a consumer. This does not affect already delivered
    messages, but it does mean the server will not send any more messages for
    that consumer. The client may receive an arbitrary number of messages in
    between sending the cancel method and receiving the cancel-ok reply

    NOTE: behavior is undefined if called after failure of the connection or
    channel on which this consumer was created (see AmqpConnectionError and
    AmqpChannelError)

    :param str consumerTag: tag of consumer to cancel

    :returns: a (possibly empty) sequence of ConsumerMessage objects
      corresponding to messages delivered for the given consumer
      before the cancel operation completed that were not yet returned by
      `getNextEvent()` or by the `readEvents()` generator.


    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    :raises nta.utils.amqp.exceptions.AmqpConnectionError:
    """
    self.consumerSet.discard(consumerTag)

    self.channel.basic.cancel(consumer_tag=consumerTag, nowait=False)

    # Remove unprocessed messages destined for this consumer from pending
    # events
    remainingEvents = deque()
    unprocessedMessages = []
    while self.pendingEvents:
      evt = self.pendingEvents.popleft()

      if (isinstance(evt, amqp_messages.ConsumerMessage) and
          evt.methodInfo.consumerTag == consumerTag):
        unprocessedMessages.append(evt)

      elif (isinstance(evt, amqp_consumer.ConsumerCancellation) and
            evt.consumerTag == consumerTag):
        # A broker-initiated Basic.Cancel must have arrived before
        # our cancel request completed
        g_log.warn("cancel_consumer: discarding evt=%s", evt)

      else:
        remainingEvents.append(evt)

    self.pendingEvents = remainingEvents

    return unprocessedMessages


class SynchronousAmqpClient(object):
  """Synchronous (blocking) AMQP client abstraction that exposes AMQP
  functionality presently needed by nta.utils and products. New AMQP
  functionality will be exposed as the need arises.

  This class provides a consistent AMQP client API to the rest of the products
  regardless of the underlying implementation. This helps avoid/minimize changes
  to the higher-level code when we need to swap out the underlying client
  implementation.

  This class is NOT the place for higher-level constructs: see
  message_bus_connector module for an example of higher-level functionality
  built on top of this class.

  NOTE: this implementation is completely synchronous and MUST NOT expose
  callbacks (callbaks lead to complexities, such as an opportunity for
  unintended/unsupported recursion)

  NOTE: The `no*` parameters, such as `noLocal` and `noAck`, are artificats
  of the AMQP protocol specification. The author of SynchronousAmqpClient chose
  to preserve those semantics to facilitate better correlation with AMQP
  documentation.
  """
  # Correlations between names of BasicProperties attributes and Haigha's
  # message property names.
  #
  # The table consists of the tollowing columns
  #     BasicProperty attribute name
  #     Corresponding Haigha property name
  #     Value conversion function from BasicProperty to Haigha
  #     Value conversion function from Haigha to BasicProperty
  #
  _asIs = lambda x: x
  _PROPERTY_CORRELATIONS = (
    ("contentType", "content_type", _asIs, _asIs),
    ("contentEncoding", "content_encoding", _asIs, _asIs),
    ("headers", "application_headers", _asIs, _asIs),
    ("deliveryMode", "delivery_mode", _asIs, _asIs),
    ("priority", "priority", _asIs, _asIs),
    ("correlationId", "correlation_id", _asIs, _asIs),
    ("replyTo", "reply_to", _asIs, _asIs),
    ("expiration", "expiration", _asIs, _asIs),
    ("messageId", "message_id", _asIs, _asIs),
    ("timestamp", "timestamp",
     datetime.utcfromtimestamp, epochFromNaiveUTCDatetime),
    ("messageType", "type", _asIs, _asIs),
    ("userId", "user_id", _asIs, _asIs),
    ("appId", "app_id", _asIs, _asIs),
    ("clusterId", "cluster_id", _asIs, _asIs),
  )


  # haigha returns body as bytearray, but our current users of the interface
  # assume they are getting str or bytes
  _decodeMessageBody = str


  def __init__(self, connectionParams=None, channelConfigCb=None):
    """
    NOTE: Connection establishment may be performed in the scope of the
    constructor or on demand, depending on the underlying implementation

    :param nta.utils.amqp.connection.ConnectionParams connectionParams:
      parameters for connecting to AMQP broker;
      [default=default params for RabbitMQ broker on localhost]
    :param channelConfigCb: An optional callback function that will be
      called whenever a new AMQP Channel is being brought up
    :type channelConfigCb: None or callable with the signature
      channelConfigCb(SynchronousAmqpClient)
    """
    self._channelConfigCb = channelConfigCb

    # Holds _ChannelContext when channel is created; we create the channel on
    # demand. The implementation accesses this member via the
    # `_liveChannelContext` property getter when it's desirable to bring up the
    # channel on-on demand. When it's undesirable to bring up the channel, the
    # implementation interacts directly with this member, which will be None
    # when we don't have a channel.
    self._channelContextInstance = None

    # Set to True when user calls close, so we know to not raise an exception
    # from our _on*Closed callback methods
    self._userInitiatedClosing = False

    # Instantiate underlying connection object
    params = (connectionParams if connectionParams is not None
              else amqp_connection.ConnectionParams())

    # NOTE: we could get a `close_cb` call from RabbitConnection constructor, so
    # prepare for it by initializing `self._connection`
    self._connection = None
    self._connection = RabbitConnection(
      transport="socket",
      sock_opts={(socket.IPPROTO_TCP, socket.TCP_NODELAY) : 1},
      synchronous=True,
      close_cb=self._onConnectionClosed,
      user=params.credentials.username,
      password=params.credentials.password,
      vhost=params.vhost,
      host=params.host,
      port=params.port,
      logger=g_log)


  def __repr__(self):
    # NOTE: we don't use the _liveChannelContext property getter in order to
    # avoid creation of channel here
    return "%s(channelContext=%r)" % (self.__class__.__name__,
                                      self._channelContextInstance)


  @property
  def _liveChannelContext(self):
    """NOTE: Creates channel on demand"""
    if self._channelContextInstance is None:
      self._channelContextInstance = _ChannelContext(
        self._connection.channel(synchronous=True))
      try:
        self._channelContextInstance.channel.add_close_listener(
          self._onChannelClosed)

        self._channelContextInstance.channel.basic.set_return_listener(
          self._onMessageReturn)

        if self._channelConfigCb is not None:
          self._channelConfigCb(self)
      except Exception:  # pylint: disable=W0703
        g_log.exception("Channel configuration failed")
        try:
          # Preserve the original exception
          raise
        finally:
          # Close channel and reset channel context
          try:
            if self._channelContextInstance is not None:
              self._channelContextInstance.channel.close(disconnect=True)
          except Exception:  # pylint: disable=W0703
            # Suppress the secondary exception from cleanup
            g_log.exception(
              "Channel closing Failed following configuration failure")
          finally:
            self._channelContextInstance.reset()
            self._channelContextInstance = None

    return self._channelContextInstance


  def __enter__(self):
    return self


  def __exit__(self, *args):
    self.close()


  def isOpen(self):
    return self._connection is not None and not self._connection.closed


  def close(self):
    """Gracefully close client"""
    self._userInitiatedClosing = True
    try:
      # NOTE: we check _channelContextInstance directly to avoid creating a
      # channel if one doesn't exist
      if self._channelContextInstance is not None:
        channelContext = self._channelContextInstance
        try:
          channelContext.channel.close()
        except Exception:  # pylint: disable=W0703
          g_log.exception("Channel close failed")

      if self._connection is not None:
        try:
          self._connection.close(disconnect=True)
        except Exception:  # pylint: disable=W0703
          g_log.exception("Connection close failed")
    finally:
      self._connection = None
      if self._channelContextInstance is not None:
        self._channelContextInstance.reset()
        self._channelContextInstance = None


  def enablePublisherAcks(self):
    """Enable RabbitMQ publisher acknowledgments

    :raises nta.utils.amqp.exceptions.UnroutableError: raised when messages
      that were sent in non-publisher-acknowledgments mode are returned by
      the time the Confirm.Select-Ok is received
    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    channelContext = self._liveChannelContext

    if channelContext.pubacksSelected:
      g_log.warning("enablePublisherAcks: already enabled")
    else:
      channelContext.channel.confirm.select(nowait=False)
      channelContext.pubacksSelected = True

      # NOTE: Unroutable messages returned after this will be in the context of
      # publisher acknowledgments
      self._raiseAndClearIfReturnedMessages()


  def publish(self, message, exchange, routingKey, mandatory=False):
    """ Publish a message

    :param nta.utils.amqp.messages.Message message:
    :param str exchange: destination exchange name; "" for default exchange
    :param str routingKey: Message routing key
    :param bool mandatory: This flag tells the server how to react if the
      message cannot be routed to a queue. If this flag is True, the server will
      return an unroutable message with a Return method. If this flag is False
      the server silently drops the message.

    :raises nta.utils.amqp.exceptions.UnroutableError: when in
      non-publisher-acknowledgments mode, raised before attempting to publish
      given message if unroutable messages had been returned. In
      publisher-acknowledgments mode, raised if the given
      message is returned as unroutable.
    :raises nta.utils.amqp.exceptions.NackError: when the given message is
      NACKed by broker while channel is in RabbitMQ publisher-acknowledgments
      mode
    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    message = HaighaMessage(
      body=message.body,
      **self._makeHaighaPropertiesDict(message.properties))

    channelContext = self._liveChannelContext

    if channelContext.pubacksSelected:
      # In publisher-acknowledgments mode
      assert not channelContext.returnedMessages, (
        len(channelContext.returnedMessages),
        channelContext.returnedMessages)

      pubackState = _PubackState()
      channelContext.channel.basic.set_ack_listener(pubackState.handleAck)
      channelContext.channel.basic.set_nack_listener(pubackState.handleNack)

      deliveryTag = channelContext.channel.basic.publish(
        message,
        exchange=exchange,
        routing_key=routingKey,
        mandatory=mandatory)

      # Wait for ACK or NACK
      while not pubackState.ready:
        self._connection.read_frames()

      try:
        ((how, responseTag),) = pubackState.values
      except ValueError:
        g_log.exception("Error unpacking values=%r", pubackState.values)
        raise

      assert responseTag == deliveryTag, ((how, responseTag), deliveryTag)

      if how == _PubackState.NACK:
        # Raise NackError with returned message
        returnedMessages = channelContext.returnedMessages
        channelContext.returnedMessages = []

        raise amqp_exceptions.NackError(returnedMessages)

      # It was Acked
      assert how == _PubackState.ACK, how

      # Raise if this message was returned as unroutable
      self._raiseAndClearIfReturnedMessages()

    else:
      # Not in publisher-acknowledgments mode

      # Raise if some prior messages were returned as unroutable
      self._raiseAndClearIfReturnedMessages()

      channelContext.channel.basic.publish(message,
                                           exchange=exchange,
                                           routing_key=routingKey,
                                           mandatory=mandatory)


  def requestQoS(self, prefetchSize=0, prefetchCount=0, entireConnection=False):
    """This method requests a specific quality of service. The QoS can be
    specified for the current channel or for all channels on the connection. The
    particular properties and semantics of a qos method always depend on the
    content class semantics

    :param int prefetchSize: The client can request that messages be sent in
      advance so that when the client finishes processing a message, the
      following message is already held locally, rather than needing to be sent
      down the channel. Prefetching gives a performance improvement. This field
      specifies the prefetch window size in octets. The server will send a
      message in advance if it is equal to or smaller in size than the available
      prefetch size (and also falls into other prefetch limits). May be set to
      zero, meaning "no specific limit", although other prefetch limits may
      still apply. The prefetchsize is ignored if the no-ack option is set.
    :param int prefetchCount: Specifies a prefetch window in terms of whole
      messages. This field may be used in combination with the prefetch-size
      field; a message will only be sent in advance if both prefetch windows
      (and those at the channel and connection level) allow it. The
      prefetch-count is ignored if the no-ack option is set.
    :param bool entireConnection: By default the QoS settings apply to the
      current channel only. If this field is set, they are applied to the entire
      connection.

    :raises AmqpChannelError:
    """
    self._liveChannelContext.channel.basic.qos(prefetch_size=prefetchSize,
                                               prefetch_count=prefetchCount,
                                               is_global=entireConnection)


  def createConsumer(self, queue, noLocal=False, noAck=False, exclusive=False):
    """This method asks the server to start a "consumer", which is a transient
    request for messages from a specific queue. Consumers last as long as the
    channel they were declared on, or until the client or broker cancels them.
    See `Consumer.cancel()`

    Use `getNextEvent()` to retrieve consumed messages and other events.

    :param str queue: name of the queue to consume from
    :param bool noLocal: If true, the server will not send messages to the
      connection that published them.
    :param bool noAck: if true, the broker will not expect messages to be ACKed
    :param bool exclusive: Request exclusive consumer access, meaning only this
      consumer can access the queue

    :returns: consumer context
    :rtype: nta.utils.amqp.consumer.Consumer

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    :raises nta.utils.amqp.exceptions.AmqpConnectionError:
    """
    consumerTag = self._makeConsumerTag()

    channelContext = self._liveChannelContext

    channelContext.channel.basic.consume(queue,
                                         consumer=self._onMessageDelivery,
                                         consumer_tag=consumerTag,
                                         no_local=noLocal,
                                         no_ack=noAck,
                                         exclusive=exclusive,
                                         cancel_cb=self._onConsumerCancelled,
                                         nowait=False)

    channelContext.consumerSet.add(consumerTag)

    consumer = amqp_consumer.Consumer(tag=consumerTag,
                                      queue=queue,
                                      cancelImpl=channelContext.cancelConsumer)

    g_log.info(
      "Created consumer=%r; queue=%r, noLocal=%r, noAck=%r, exclusive=%r",
      consumer, queue, noLocal, noAck, exclusive)

    return consumer


  def hasEvent(self):
    """Check if there are events ready for consumption. See `getNextEvent()`.

    :returns: True if there is at least one event ready for consumption, in
      which case `getNextEvent()` may be called once without blocking.
    :rtype: bool
    """
    channelContext = self._channelContextInstance
    return bool(channelContext is not None and channelContext.pendingEvents)


  def getNextEvent(self):
    """Get next event, blocking if there isn't one yet. See `hasEvent()`. You
    MUST have an active consumer (`createConsumer`) or other event source before
    calling this method.

    An event may be an object of one of the following classes:

      nta.utils.amqp.messages.ConsumerMessage
      nta.utils.amqp.consumer.ConsumerCancellation

    :returns: the next event when it becomes available

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    # We expect the context to be set up already
    channelContext = self._channelContextInstance

    while not channelContext.pendingEvents:
      self._connection.read_frames()

    return channelContext.pendingEvents.popleft()


  def readEvents(self):
    """Generator that yields results of `getNextEvent()`"""
    while True:
      yield self.getNextEvent()


  def getOneMessage(self, queue, noAck=False):
    """This is the polling, less-performant method of getting a message. This
    method provides a direct access to the messages in a queue using a
    synchronous dialogue that is designed for specific types of application
    where synchronous functionality is more important than performance.

    :param str queue: name of the queue to get a message from
    :param bool noAck: if true, the broker will not be expecting an Ack

    :returns: A PolledMessage object if there was a message in queue; None if
      there was no message in queue.
    :rtype: PolledMessage or None

    :raises AmqpChannelError:
    """
    channelContext = self._liveChannelContext

    consumer = _CallbackSink()

    channelContext.channel.basic.get(queue, consumer=consumer, no_ack=noAck)
    while not consumer.ready:
      self._connection.read_frames()

    try:
      ((message,),) = consumer.values
    except ValueError:
      g_log.exception("Error unpacking values=%r", consumer.values)
      raise

    if message is not None:
      ackImpl = channelContext.ack if not noAck else None
      nackImpl = channelContext.nack if not noAck else None
      message = self._makePolledMessage(message, ackImpl, nackImpl)

    return message


  @classmethod
  def _makePolledMessage(cls, haighaMessage, ackImpl, nackImpl):
    """Make PolledMessage from haigha message retrieved via Basic.Get

    :param haigha.message.Message haighaMessage: haigha message retrieved via
      Basic.Get
    :param ackImpl: callable for acking the message that has the following
      signature: ackImpl(deliveryTag, multiple=False); or None
    :param nackImpl: callable for nacking the message that has the following
      signature: nackImpl(deliveryTag, requeue); or None

    :rtype: nta.utils.amqp.messages.PolledMessage
    """
    info = haighaMessage.delivery_info

    methodInfo = amqp_messages.MessageGetInfo(
      deliveryTag=info["delivery_tag"],
      redelivered=bool(info["redelivered"]),
      exchange=info["exchange"],
      routingKey=info["routing_key"],
      messageCount=info["message_count"]
    )

    return amqp_messages.PolledMessage(
      body=cls._decodeMessageBody(haighaMessage.body),
      properties=cls._makeBasicProperties(haighaMessage.properties),
      methodInfo=methodInfo,
      ackImpl=ackImpl,
      nackImpl=nackImpl)


  def recover(self, requeue=False):
    """This method asks the server to redeliver all unacknowledged messages on a
    specified channel. Zero or more messages may be redelivered.

    NOTE: RabbitMQ does not currently support recovering with requeue=False

    :param bool requeue: If false, the message will be redelivered to the
      original recipient. If true, the server will attempt to requeue the
      message, potentially then delivering it to an alternative subscriber.
    """
    self._liveChannelContext.channel.basic.recover(requeue=requeue)


  def ackAll(self):
    """Acknowledge all unacknowledged messages on current channel instance.

    Acknowledgemets related to specific messages are performed via the message's
    own `ack()` method.

    NOTE: messages received prior to the AmqpChannelError exception cannot be
    acknowledged since that exception occurs after the AMQP channel is closed
    """
    self._channelContextInstance.ack(deliveryTag=0, multiple=True)


  def nackAll(self, requeue=False):
    """Reject all outstanding (unacknowledged) messages on current channel
    instance.

    Rejections related to specific messages are performed via the message's
    own `nack()` method.

    NOTE: has no impact on messages received prior to the AmqpChannelError
    exception since AmqpChannelError is raised after the AMQP channel is closed

    :param bool requeue: If requeue is true, the server will attempt to requeue
      the messages. If requeue is false or the requeue attempt fails the
      messages are discarded or dead-lettered
    """
    self._channelContextInstance.nack(deliveryTag=0,
                                      multiple=True,
                                      requeue=requeue)


  def declareExchange(self,
                      exchange,
                      exchangeType,
                      passive=False,
                      durable=False,
                      autoDelete=False,
                      arguments=None):
    """Declare an exchange

    :param str exchange: name of the exchange
    :param str exchangeType: type of the exchange
    :param bool passive: If True, the server will reply with Declare-Ok if the
      exchange already exists with the same name, and raise an error if not. The
      client can use this to check whether an exchange exists without modifying
      the server state. When set, all other method fields except name are
      ignored. Arguments are compared for semantic equivalence.
    :param bool durable: If True when creating a new exchange, the exchange will
      be marked as durable. Durable exchanges remain active when a server
      restarts. Non-durable exchanges (transient exchanges) are purged if/when a
      server restarts.
    :param bool autoDelete: If true, the exchange is deleted when all queues
      have finished using it (RabbitMQ-specific).
    :param dict arguments: custom key/value pairs for the exchange

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    self._liveChannelContext.channel.exchange.declare(
      exchange,
      exchangeType,
      passive=passive,
      durable=durable,
      auto_delete=autoDelete,
      arguments=arguments or dict(),
      nowait=False)


  def deleteExchange(self, exchange, ifUnused=False):
    """Delete an exchange

    :param str exchange: exchange to be deleted
    :param bool ifUnused: If True, the server will only delete the exchange if
      it has no queue bindings. If the exchange has queue bindings the server
      does not delete it but raises a channel exception instead.

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    self._liveChannelContext.channel.exchange.delete(exchange,
                                                     if_unused=ifUnused,
                                                     nowait=False)


  def declareQueue(self, queue, passive=False, durable=False, exclusive=False,
                   autoDelete=False, arguments=None):
    """Declare a queue

    :param str queue: name of queue
    :param bool passive: If True, the server will reply with Declare-Ok if the
      queue already exists with the same name, and raise an error if not. The
      client can use this to check whether a queue exists without modifying the
      server state. When set, all other method fields except name are ignored.
      Arguments are compared for semantic equivalence.
    :param bool durable: If true when creating a new queue, the queue will be
      marked as durable. Durable queues remain active when a server restarts.
      Non-durable queues (transient queues) are purged if/when a server
      restarts. Note that durable queues do not necessarily hold persistent
      messages, although it does not make sense to send persistent messages to a
      transient queue.
    :param bool exclusive: Exclusive queues may only be accessed by the current
      connection, and are deleted when that connection closes. Passive
      declaration of an exclusive queue by other connections are not allowed.
    :param bool autoDelete: If true, the queue is deleted when all consumers
      have finished using it. The last consumer can be cancelled either
      explicitly or because its channel is closed. If there was no consumer ever
      on the queue, it won't be deleted. Applications can explicitly delete
      auto-delete queues using the Delete method as normal. (RabbitMQ-specific)
    :param dict arguments: A set of key/value pairs for the declaration. The
      syntax and semantics of these arguments depends on the server
      implementation.

    :rtype: nta.utils.amqp.queue.QueueDeclarationResult

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    queue, messageCount, consumerCount = (
      self._liveChannelContext.channel.queue.declare(
        queue,
        passive=passive,
        durable=durable,
        exclusive=exclusive,
        auto_delete=autoDelete,
        arguments=arguments or dict(),
        nowait=False))

    return amqp_queue.QueueDeclarationResult(queue, messageCount, consumerCount)


  def deleteQueue(self, queue, ifUnused=False, ifEmpty=False):
    """Delete a queue. When a queue is deleted any pending messages are sent to
    a dead-letter queue if this is defined in the server configuration, and all
    consumers on the queue are cancelled

    :param str queue: name of the queue to delete
    :param bool ifUnused: If true, the server will only delete the queue if it
      has no consumers. If the queue has consumers the server does does not
      delete it but raises a channel exception instead.
    :param bool ifEmpty: If true, the server will only delete the queue if it
      has no messages

    :returns: number of messages deleted
    :rtype: int

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    return self._liveChannelContext.channel.queue.delete(queue,
                                                         if_unused=ifUnused,
                                                         if_empty=ifEmpty,
                                                         nowait=False)


  def purgeQueue(self, queue):
    """Remove all messages from a queue which are not awaiting acknowledgment.

    :param str queue: name of the queue to purge

    :returns: number of messages purged
    :rtype: int

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    return self._liveChannelContext.channel.queue.purge(queue, nowait=False)


  def bindQueue(self, queue, exchange, routingKey, arguments=None):
    """Bind a queue to an exchange

    :param str queue: name of the queue to bind
    :param str exchange: name of the exchange to bind to
    :param str routingKey: Specifies the routing key for the binding. The
      routing key is used for routing messages depending on the exchange
      configuration. Not all exchanges use a routing key refer to the
      specific exchange documentation. If the queue name is empty, the server
      uses the last queue declared on the channel. If the routing key is also
      empty, the server uses this queue name for the routing key as well. If the
      queue name is provided but the routing key is empty, the server does the
      binding with that empty routing key. The meaning of empty routing keys
      depends on the exchange implementation.
    :param dict arguments: A set of key/value pairs for the binding. The syntax
      and semantics of these arguments depends on the exchange class and server
      implemenetation.

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    self._liveChannelContext.channel.queue.bind(queue=queue,
                                                exchange=exchange,
                                                routing_key=routingKey,
                                                arguments=arguments or dict(),
                                                nowait=False)


  def unbindQueue(self, queue, exchange, routingKey, arguments=None):
    """Unbind a queue fro an exchange

    :param str queue: name of the queue to unbind
    :param str exchange: name of the exchange to unbind from
    :param str routingKey: the routing key of the binding to unbind
    :param dict arguments: Specifies the arguments of the binding to unbind

    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    """
    self._liveChannelContext.channel.queue.unbind(queue=queue,
                                                  exchange=exchange,
                                                  routing_key=routingKey,
                                                  arguments=arguments or dict())


  def _raiseAndClearIfReturnedMessages(self):
    """If returned messages are present, raise UnroutableError and clear
    returned messages holding buffer

    :raises nta.utils.amqp.exceptions.UnroutableError: if returned messages
      are present
    """
    channelContext = self._channelContextInstance

    if channelContext and channelContext.returnedMessages:
      messages = channelContext.returnedMessages
      channelContext.returnedMessages = []
      raise amqp_exceptions.UnroutableError(messages)


  @classmethod
  def _makeHaighaPropertiesDict(cls, BasicProperties):
    """Marshal BasicProperties into the haigha properties dict

    :param nta.utils.amqp.messages.BasicProperties BasicProperties:

    :returns: dict of Properties expected by Haigha's publish method
    :rtype: dict
    """
    props = dict()

    for attrName, propName, clientToHaigha, _ in cls._PROPERTY_CORRELATIONS:
      value = getattr(BasicProperties, attrName)
      # Add only those properties that have concrete values
      if value is not None:
        props[propName] = clientToHaigha(value)

    return props


  @classmethod
  def _makeBasicProperties(cls, haighaProperties):
    attributes = dict()

    for attrName, propName, _, haighaToClient in cls._PROPERTY_CORRELATIONS:
      value = haighaProperties.get(propName)

      if value is not None:
        value = haighaToClient(value)

      attributes[attrName] = value

    return amqp_messages.BasicProperties(**attributes)


  def _makeConsumerTag(self):
    channelContext = self._liveChannelContext

    tag = "channel-%d-%d" % (channelContext.channel.channel_id,
                             channelContext.nextConsumerTag)
    channelContext.nextConsumerTag += 1
    return tag


  def _onMessageDelivery(self, message):
    """Handle consumer message from Basic.Deliver

    :param haigha.message.Message message:
    """
    channelContext = self._channelContextInstance

    g_log.debug("Consumer message received: %.255s", message)
    channelContext.pendingEvents.append(
      self._makeConsumerMessage(message,
                                channelContext.ack,
                                channelContext.nack))


  @classmethod
  def _makeConsumerMessage(cls, haighaMessage, ackImpl, nackImpl):
    """Make ConsumerMessage from haigha message received via Basic.Deliver

    :param haigha.message.Message haighaMessage: haigha message received via
      Basic.Deliver
    :param ackImpl: callable for acking the message that has the following
      signature: ackImpl(deliveryTag, multiple=False); or None
    :param nackImpl: callable for nacking the message that has the following
      signature: nackImpl(deliveryTag, requeue); or None

    :rtype: ConsumerMessage
    """
    info = haighaMessage.delivery_info

    methodInfo = amqp_messages.MessageDeliveryInfo(
      consumerTag=info["consumer_tag"],
      deliveryTag=info["delivery_tag"],
      redelivered=bool(info["redelivered"]),
      exchange=info["exchange"],
      routingKey=info["routing_key"]
    )

    return amqp_messages.ConsumerMessage(
      body=cls._decodeMessageBody(haighaMessage.body),
      properties=cls._makeBasicProperties(haighaMessage.properties),
      methodInfo=methodInfo,
      ackImpl=ackImpl,
      nackImpl=nackImpl)


  def _onConsumerCancelled(self, consumerTag):
    """Handle notification of Basic.Cancel from broker

    :param str consumerTag: tag of consumer cancelled by broker
    """
    channelContext = self._channelContextInstance

    channelContext.pendingEvents.append(
        amqp_consumer.ConsumerCancellation(consumerTag))

    channelContext.consumerSet.discard(consumerTag)


  def _onMessageReturn(self, message):
    """Handle unroutable message returned by broker

    NOTE: this may happen regardless of RabbitMQ-specific puback mode; however,
    if it's going to happen in puback mode, RabbitMQ guarantees that it will
    take palce *before* Basic.Ack

    :param haigha.message.Message message:
    """
    g_log.warning("Message returned: %.255s", message)

    self._channelContextInstance.returnedMessages.append(
      self._makeReturnedMessage(message))


  @classmethod
  def _makeReturnedMessage(cls, haighaMessage):
    """
    :param haigha.message.Message haighaMessage: haigha message returned via
      Basic.Return

    :rtype: nta.utils.amqp.messages.ReturnedMessage
    """
    info = haighaMessage.return_info

    methodInfo = amqp_messages.MessageReturnInfo(
      replyCode=info["reply_code"],
      replyText=info["reply_text"],
      exchange=info["exchange"],
      routingKey=info["routing_key"])

    return amqp_messages.ReturnedMessage(
      body=cls._decodeMessageBody(haighaMessage.body),
      properties=cls._makeBasicProperties(haighaMessage.properties),
      methodInfo=methodInfo)


  @staticmethod
  def _amqpErrorArgsFromCloseInfo(closeInfo):
    """
    :param dict closeInfo: channel or connection close_info from Haigha

    :returns: a dict with property names compatible with _AmqpErrorBase
      constructor args
    """
    return dict(code=closeInfo["reply_code"],
                text=closeInfo["reply_text"],
                classId=closeInfo["class_id"],
                methodId=closeInfo["method_id"])


  def _onConnectionClosed(self):
    try:
      if self._connection is None:
        # Failure during connection setup
        raise amqp_exceptions.AmqpConnectionError(code=0,
                                                  text="connection setup failed",
                                                  classId=0,
                                                  methodId=0)

      closeInfo = self._connection.close_info

      if self._userInitiatedClosing:
        if closeInfo["reply_code"] != 0:
          raise amqp_exceptions.AmqpConnectionError(
            **self._amqpErrorArgsFromCloseInfo(closeInfo))
      else:
        raise amqp_exceptions.AmqpConnectionError(
            **self._amqpErrorArgsFromCloseInfo(closeInfo))
    finally:
      self._connection = None
      if self._channelContextInstance is not None:
        self._channelContextInstance.reset()
        self._channelContextInstance = None


  def _onChannelClosed(self, channel):
    try:
      closeInfo = channel.close_info

      if self._userInitiatedClosing:
        if closeInfo["reply_code"] != 0:
          raise amqp_exceptions.AmqpChannelError(
              **self._amqpErrorArgsFromCloseInfo(closeInfo))
      else:
        raise amqp_exceptions.AmqpChannelError(
            **self._amqpErrorArgsFromCloseInfo(closeInfo))
    finally:
      if self._channelContextInstance is not None:
        self._channelContextInstance.reset()
        self._channelContextInstance = None
