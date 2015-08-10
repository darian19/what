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
AMQP exceptions.

TODO need unit tests
"""


class _AmqpErrorBase(Exception):
  """Signals failure of AMQP operation """

  def __init__(self, code, text, classId, methodId):
    """
    :param int code: AMQP reply code
    :param str text: reply text
    :param int classId: failing method class
    :param int methodId:failing method ID
    """
    super(_AmqpErrorBase, self).__init__(code, text, classId, methodId)
    self.code = code
    self.text = text
    self.classId = classId
    self.methodId = methodId


  def __repr__(self):
    return self.__class__.__name__ + (
      "(code=%s, text=%s, class_id=%s, method_id=%s)" % (
      self.code, self.text, self.classId, self.methodId))



class AmqpChannelError(_AmqpErrorBase):
  """Signals failure of AMQP operation on a channel and concludes in closing of
  the channel.
  """
  pass



class AmqpConnectionError(_AmqpErrorBase):
  """AMQP broker closed connection or connection with broker dropped suddently

  If TCP/IP connection dropped suddenly, classId will be 0, text will contain an
  error message, and the rest of the attributes are undefined """
  pass



class UnroutableError(Exception):
  """Raised when one or more unroutable messages have been returned by broker.
  """

  def __init__(self, messages):
    """
    :param messages: sequence of returned unroutable messages
    :type messages: sequence of nta.utils.amqp.messages.ReturnedMessage objects
    """
    super(UnroutableError, self).__init__(
      "%s unroutable message(s) returned: %.255s" % (len(messages), messages))

    self.messages = messages



class NackError(Exception):
  """Published message was NACKed by broker; only applicable in RabbitMQ
  publisher-acknowledgments mode
  """

  def __init__(self, messages):
    """
    :param messages: sequence of returned nacked messages
    :type messages: sequence of nta.utils.amqp.messages.ReturnedMessage objects
    """
    super(NackError, self).__init__(
      "%s nacked message(s) returned: %.255s" % (len(messages), messages))

    self.messages = messages
