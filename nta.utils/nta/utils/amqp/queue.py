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
AMQP queue.

TODO need unit tests
"""

class QueueDeclarationResult(object):
  """Result of queue declaration"""

  __slots__ = ("queue", "messageCount", "consumerCount")


  def __init__(self, queue, messageCount, consumerCount):
    """
    :param str queue: Reports the name of the queue. If the server generated a
      queue name, this field contains that name
    :param int messageCount: The number of messages in the queue, which will be
      zero for newly-declared queues
    :param int consumerCount: Reports the number of active consumers for the
      queue. Note that consumers can suspend activity (Channel.Flow) in which
      case they do not appear in this count
    """
    self.queue = queue
    self.messageCount = messageCount
    self.consumerCount = consumerCount


  def __repr__(self):
    return "%s(queue=%r, messageCount=%s, consumerCount=%s)" % (
      self.__class__.__name__,
      self.queue, self.messageCount, self.consumerCount)
