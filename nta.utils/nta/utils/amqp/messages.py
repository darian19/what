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
AMQP messages.

TODO need unit tests
"""

class MessageDeliveryInfo(object):
  """Information about a message received via Basic.Deliver as the result of
  Basic.Consume
  """

  __slots__ = ("consumerTag", "deliveryTag", "redelivered", "exchange",
               "routingKey")


  def __init__(self,
               consumerTag,
               deliveryTag,
               redelivered,
               exchange,
               routingKey):
    """
    :param str consumerTag: consumer tag
    :param int deliveryTag: message delivery tag
    :param bool redelivered: True if message was redelivered
    :param str exchange: Specifies the name of the exchange that the message was
      originally published to. May be empty, indicating the default exchange.
    :param str routingKey: Specifies the routing key name specified when the
      message was published
    """
    self.consumerTag = consumerTag
    self.deliveryTag = deliveryTag
    self.redelivered = redelivered
    self.exchange = exchange
    self.routingKey = routingKey


  def __repr__(self):
    return ("%s(consumerTag=%r, deliveryTag=%s, redelivered=%s, exchange=%r, "
            "routingKey=%r)") % (
              self.__class__.__name__, self.consumerTag, self.deliveryTag,
              self.redelivered, self.exchange, self.routingKey)


  def __eq__(self, other):
    return all(getattr(self, slot) == getattr(other, slot)
               for slot in self.__slots__)


  def __ne__(self, other):
    return not self.__eq__(other)



class MessageGetInfo(object):
  """Information about a message received via Basic.Get-Ok"""

  __slots__ = ("deliveryTag", "redelivered", "exchange", "routingKey",
               "messageCount")


  def __init__(self,
               deliveryTag,
               redelivered,
               exchange,
               routingKey,
               messageCount=None):
    """
    :param int deliveryTag: message delivery tag
    :param bool redelivered: True if message was redelivered
    :param str exchange: Specifies the name of the exchange that the message was
      originally published to. May be empty, indicating the default exchange.
    :param str routingKey: Specifies the routing key name specified when the
      message was published
    :param int messageCount: basic.get-ok.message-count
    """
    self.deliveryTag = deliveryTag
    self.redelivered = redelivered
    self.exchange = exchange
    self.routingKey = routingKey
    self.messageCount = messageCount


  def __repr__(self):
    return ("%s(deliveryTag=%s, redelivered=%s, exchange=%s, "
            "routingKey=%s, messageCount=%s)") % (
              self.__class__.__name__, self.deliveryTag, self.redelivered,
              self.exchange, self.routingKey, self.messageCount)


  def __eq__(self, other):
    return all(getattr(self, slot) == getattr(other, slot)
               for slot in self.__slots__)


  def __ne__(self, other):
    return not self.__eq__(other)



class MessageReturnInfo(object):
  """Information about a message returned via Basic.Return"""

  __slots__ = ("replyCode", "replyText", "exchange", "routingKey")


  def __init__(self, replyCode, replyText, exchange, routingKey):
    """
    :param int replyCode: Reply code (int)
    :param str replyText: Reply text
    :param str exchange: Specifies the name of the exchange that the message
      was originally published to. May be empty, meaning the default exchange.
    :param str routingKey: The routing key name specified when the message was
      published
    """
    self.replyCode = replyCode
    self.replyText = replyText
    self.exchange = exchange
    self.routingKey = routingKey


  def __repr__(self):
    return "%s(replyCode=%s, replyText=%s, exchange=%s, routingKey=%s)" % (
      self.__class__.__name__, self.replyCode, self.replyText, self.exchange,
      self.routingKey)


  def __eq__(self, other):
    return all(getattr(self, slot) == getattr(other, slot)
               for slot in self.__slots__)


  def __ne__(self, other):
    return not self.__eq__(other)


class BasicProperties(object):
  """Content properties of a message (Basic.Properties)"""

  __slots__ = ("contentType", "contentEncoding", "headers", "deliveryMode",
               "priority", "correlationId", "replyTo", "expiration",
               "messageId", "timestamp", "messageType", "userId", "appId",
               "clusterId")


  def __init__(self,
               contentType=None,
               contentEncoding=None,
               headers=None,
               deliveryMode=None,
               priority=None,
               correlationId=None,
               replyTo=None,
               expiration=None,
               messageId=None,
               timestamp=None,
               messageType=None,
               userId=None,
               appId=None,
               clusterId=None):
    """
    NOTE: Unless noted otherwise, the value None signals absence of the property

    :param str contentType: application use; MIME content type (shortstr).
    :param str contentEncoding: application use MIME content encoding (shortstr)
    :param dict headers: application use; message header field table; similar to
      X-Headers in HTTP
    :param int deliveryMode: queue implementation use; message delivery mode;
      see AMQPDeliveryModes.
    :param int priority: queue implementation use; message priority, 0 to 9.
    :param str correlationId: application use; application correlation
      identifier (shortstr); useful for correlating responses with requests.
    :param str replyTo: application use; address to reply to (shortstr);
      commonly used to name a callback queue
    :param str expiration: queue implementation use; message expiration TTL
      specification (shortstr). The value is in whole number of milliseconds
      converted to a string; a message that has been in the queue for longer
      than the configured TTL is said to be dead and will not be delivered from
      that queue.
    :param str messageId: application use; application message identifier
      (shortstr)
    :param long timestamp: application use; message publishing timestamp in
      seconds since unix Epoch (e.g., long(time.time()))
    :param str messageType: application use; message type name (basic.type;
      shortstr)
    :param str userId: queue implementation use; creating user id (shortstr).
      RabbitMQ: "If this property is set by a publisher, its value must be equal
      to the name of the user used to open the connection. If the user-id
      property is not set, the publisher's identity remains private."
    :param str appId: application use; creating application id (shortstr)
    :param str clusterId: DEPRECATED

    """
    self.contentType = contentType
    self.contentEncoding = contentEncoding
    self.headers = headers
    self.deliveryMode = deliveryMode
    self.priority = priority
    self.correlationId = correlationId
    self.replyTo = replyTo
    self.expiration = expiration
    self.messageId = messageId
    self.timestamp = timestamp
    self.messageType = messageType
    self.userId = userId
    self.appId = appId
    self.clusterId = clusterId


  def __repr__(self):
    args = (
      ("%s=%r" % (attr, getattr(self, attr)))
      for attr in sorted(self.__slots__)
      if not callable(getattr(self, attr)) and getattr(self, attr) is not None)

    return "%s(%s)" % (self.__class__.__name__, ", ".join(args))


  def __eq__(self, other):
    return all(getattr(self, slot) == getattr(other, slot)
               for slot in self.__slots__)


  def __ne__(self, other):
    return not self.__eq__(other)



class Message(object):
  """Represents a message to publish; also base class for messages originated
  from server
  """

  __slots__ = ("body", "properties")


  def __init__(self, body, properties=None):
    """
    :param body: message body, which may be an empty string
    :type body: bytes or string
    :param BasicProperties: message properties; defaults to BasicProperties with
      all attributes having the value None
    """
    self.body = body
    self.properties = (properties if properties is not None
                       else BasicProperties())

  def __repr__(self):
    return "%s(props=%s, body=%.255r)" % (self.__class__.__name__,
                                               self.properties, self.body)



class ReturnedMessage(Message):
  """Message received as the result of Basic.Return"""

  __slots__ = ("methodInfo",)


  def __init__(self, body, properties, methodInfo):
    """
    :param body: see Message.body
    :param BasicProperties properties: message properties
    :param MessageReturnInfo methodInfo: info from Basic.Return method

    """
    super(ReturnedMessage, self).__init__(body, properties)
    self.methodInfo = methodInfo


  def __repr__(self):
    return "%s(info=%r, props=%r, body=%.255r)" % (
      self.__class__.__name__, self.methodInfo, self.properties, self.body)


  def __eq__(self, other):
    return all(getattr(self, slot) == getattr(other, slot)
               for slot in self.__slots__)


  def __ne__(self, other):
    return not self.__eq__(other)



class _AckableMessage(Message):
  """Base class for ConsumerMessage and PolledMessage with ack/nack support"""

  __slots__ = ("methodInfo", "_ackImpl", "_nackImpl")


  def __init__(self, body, properties, methodInfo, ackImpl, nackImpl):
    """
    :param body: see Message.body
    :param BasicProperties properties: message properties
    :param methodInfo: MessageDeliveryInfo or MessageGetInfo
    :param ackImpl: function for acking the message that has the following
      signature: ackImpl(deliveryTag, multiple)
    :type ackImpl: callable ackImpl(deliveryTag, multiple) or None
    :param nackImpl: function for nacking the message that has the following
      signature: nackImpl(deliveryTag, requeue)
    :type nackImpl: callable nackImpl(deliveryTag, multiple, requeue) or None

    """
    super(_AckableMessage, self).__init__(body, properties)
    self.methodInfo = methodInfo
    self._ackImpl = ackImpl
    self._nackImpl = nackImpl


  def __repr__(self):
    return "%s(info=%r, props=%r, body=%.255r)" % (
      self.__class__.__name__, self.methodInfo, self.properties, self.body)


  def ack(self, multiple=False):
    """Ack the message; only use with messages received with no-ack=False

    NOTE: Behavior is undefined on messages received with no-ack=True

    NOTE: behavior is undefined if called after failure of the connection or
    channel on which this consumer was created (see AmqpConnectionError and
    AmqpChannelError)

    :param int deliveryTag: delivery tag of message being acknowledged
    :param bool multiple: If true, the delivery tag is treated as "up to and
      including", so that the client can acknowledge multiple messages with a
      single method. If false, the delivery tag refers to a single
      message.
    """
    self._ackImpl(self.methodInfo.deliveryTag, multiple)


  def nack(self, multiple=False, requeue=False):
    """Nack the message; only use with messages received with no-ack=False;

    NOTE: Behavior is undefined on messages received with no-ack=True

    NOTE: behavior is undefined if called after failure of the connection or
    channel on which this consumer was created (see AmqpConnectionError and
    AmqpChannelError)

    :param bool multiple: If true, the delivery tag is treated as "up to and
      including", so that multiple messages can be rejected with a single
      method. If false, the delivery tag refers to a single message.
    :param bool requeue: If requeue is true, the server will attempt to
      requeue the message. If requeue is false or the requeue attempt fails
      the messages are discarded or dead-lettered
    """
    self._nackImpl(self.methodInfo.deliveryTag, multiple, requeue)



class PolledMessage(_AckableMessage):
  """Message received via Basic.Get-Ok as the result of Basic.Get

  methodInfo arg is of type MessageGetInfo
  """
  pass



class ConsumerMessage(_AckableMessage):
  """Message received via Basic.Deliver as the result of Basic.Consume

  methodInfo arg is of type MessageDeliveryInfo
  """
  pass
