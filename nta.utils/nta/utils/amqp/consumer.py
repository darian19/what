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
AMQP consumer.

TODO need unit tests
"""

class Consumer(object):
  """Represents a consumer; an object of this class is returned by the client's
  `createConsumer()` method
  """

  __slots__ = ("tag", "_queue", "_cancelImpl")


  def __init__(self, tag, queue, cancelImpl):
    """
    :param str tag: this consumer's consumer-tag
    :param str queue: name of queue being consumed (for `__repr__`)
    :param cancelImpl: function for cancelling the consumer.
    :type cancelImpl: callable cancelImpl(consumerTag)
    """
    if not callable(cancelImpl):
      raise ValueError("cancelImpl arg is not callable: %r" % (cancelImpl,))

    self.tag = tag
    self._queue = queue
    self._cancelImpl = cancelImpl


  def __repr__(self):
    return "%s(tag=%r, queue=%r)" % (self.__class__.__name__, self.tag,
                                     self._queue)


  def cancel(self):
    """Cancel the consumer. This does not affect already delivered
    messages, but it does mean the server will not send any more messages for
    this consumer. The client may receive an arbitrary number of messages in
    between sending the cancel method and receiving the cancel-ok reply

    NOTE: behavior is undefined if called after failure of the connection or
    channel on which this consumer was created (see AmqpConnectionError and
    AmqpChannelError)

    :returns: a (possibly empty) sequence of ConsumerMessage objects
      corresponding to messages delivered for the given consumer
      before the cancel operation completed that were not yet returned by
      `getNextEvent()` or by the `readEvents()` generator.


    :raises nta.utils.amqp.exceptions.AmqpChannelError:
    :raises nta.utils.amqp.exceptions.AmqpConnectionError:
    """
    return self._cancelImpl(self.tag)



class ConsumerCancellation(object):
  """Object of this class represents cancellation of consumer by broker"""

  __slots__ = ("consumerTag",)


  def __init__(self, consumerTag):
    """
    :param str consumerTag: tag of cancelled consumer
    """
    self.consumerTag = consumerTag


  def __repr__(self):
    return "%s(tag=%r)" % (self.__class__.__name__, self.consumerTag)
