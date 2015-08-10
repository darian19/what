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

"""Tests the metric listener."""

import socket
import unittest

import mock
from mock import MagicMock, Mock, patch

from htmengine.runtime import metric_listener
from htmengine.runtime.metric_listener import Protocol, TCPHandler



class MetricListenerTest(unittest.TestCase):


  def testParsePlaintext(self):
    data = "test.metric 4.0 1386792175"
    result = metric_listener.parsePlaintext(data)
    self.assertEqual(len(result), 3)
    name, value, dt = result
    self.assertEqual(name, "test.metric")
    self.assertAlmostEqual(value, 4.0)
    self.assertEqual(dt.year, 2013)
    self.assertEqual(dt.month, 12)
    self.assertEqual(dt.day, 11)
    self.assertEqual(dt.hour, 20)
    self.assertEqual(dt.minute, 2)
    self.assertEqual(dt.second, 55)


  @patch.object(metric_listener, "MessageBusConnector", autospec=True)
  @patch.object(metric_listener, "_forwardData", autospec=True)
  def testPlaintextTCP(self, forwardDataMock,
                       _MessageBusConnectorMock):

    class ThreadedTCPServerMockTemplate (metric_listener.ThreadedTCPServer):
      concurrencyTracker=MagicMock(
        spec=metric_listener.threading_utils.ThreadsafeCounter)

    metric_listener.Protocol.current = Protocol.PLAIN

    samples = [
      "test.metric 4 1386120789\n",
      "test.metric 5 1386120799\n",
      socket.timeout("timed out"),
      "test.metric 6 1386120999"
    ]

    def recvIntoMock(buf):
      try:
        data = samples.pop(0)
        if isinstance(data, socket.timeout):
          raise data

        buf[0:len(data)] = data[:]
        return len(data)
      except IndexError:
        return 0

    mockSock = MagicMock(
      spec_set=socket.socket,
      recv_into=Mock(spec_set=socket.socket.recv_into,
                     side_effect=recvIntoMock))
    mockClientAddr = ("127.0.0.1", 2999)
    mockServer = MagicMock(spec_set=ThreadedTCPServerMockTemplate)

    self.assertEqual(metric_listener.Protocol.current,
                     Protocol.PLAIN)
    handler = TCPHandler(request=mockSock,
                         client_address=mockClientAddr,
                         server=mockServer)

    # Check the results
    self.assertEqual(forwardDataMock.call_count, 2)
    data = ["test.metric 4 1386120789", "test.metric 5 1386120799"]
    call0 = mock.call(mock.ANY, data)
    self.assertEqual(forwardDataMock.call_args_list[0], call0)

    data = ["test.metric 6 1386120999"]
    call1 = mock.call(mock.ANY, data)
    self.assertEqual(forwardDataMock.call_args_list[1], call1)


  @patch.object(metric_listener, "_TimeoutSafeBufferedLineReader", autospec=True)
  def testReadlines(self, lineReaderClassMock):
    lineReaderClassMock.return_value.readlinesWithTimeout.return_value = [
      "abc",
      None,
      "def",
    ]

    reader = iter(metric_listener._readlines(sock=Mock()))

    self.assertEqual(reader.next(), "abc")
    self.assertEqual(reader.next(), None)
    self.assertEqual(reader.next(), "def")
    with self.assertRaises(StopIteration):
      reader.next()



if __name__ == "__main__":
  unittest.main()
