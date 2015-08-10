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

"""Listens on a UDP or TCP port for metric data to write to a queue.

TODO: Can we re-use the message bus across connections?
TODO: (MER-1492) Use separate thread to batch upload records to queue when
they come in as a batch but to time out quickly to avoid long delays in
uploading.
"""

import datetime
import errno
import itertools
import json
import logging
import optparse
import os
import socket
import SocketServer
import threading
import time

from nta.utils.config import Config
from nta.utils.logging_support_raw import LoggingSupport
from nta.utils import threading_utils

from htmengine import raiseExceptionOnMissingRequiredApplicationConfigPath
from htmengine.htmengine_logging import getExtendedLogger
from htmengine.model_swapper.model_swapper_interface import (
  MessageBusConnector)
from nta.utils.message_bus_connector import MessageQueueNotFound



# Max number of data samples per batch
_MAX_BATCH_SIZE = 200


LOGGER = getExtendedLogger(__name__)

gQueueName = None

gProfiling = False




class Protocol(object):
  """
  Currently supports only the Carbon plaintext protocol
  Future options are pickle and amqp
  """

  PLAIN = "plain"

  current = None

  @classmethod
  def values(cls):
    return (cls.PLAIN,)

  @classmethod
  def getDefaultPort(cls, protocol):
    if protocol == cls.PLAIN:
      return int((Config("application.conf",
                         os.environ["APPLICATION_CONFIG_PATH"])
                  .get("metric_listener", "plaintext_port")))
    raise ValueError("Unknown protocol %r" % protocol)



def parsePlaintext(data):
  """ Parse a plaintext data sample

  :param data: a whitespace-separated text string containing the following items
    in order: <metric-name> <data-value> <unix-timestamp>

  :raises: ValueError when input data doesn't matches the expected type and
      format

  :returns: a three-tuple sequence:
    (<metric-name>, <floating-point-value>, <datetime-timestamp>)
  """
  try:
    output = data.split()
    assert len(output) == 3
    output[1] = float(output[1])
    output[2] = datetime.datetime.utcfromtimestamp(float(output[2]))
  except (AssertionError, AttributeError, LookupError, TypeError, ValueError):
    raise ValueError(
        "Unable to parse input of type %r: %r" % (type(data), data))
  return output



class Transport(object):
  __slots__ = ("UDP", "TCP")
  UDP = "udp"
  TCP = "tcp"

  @classmethod
  def values(cls):
    return [getattr(cls, a) for a in cls.__slots__]



def _forwardData(messageBus, data):
  """Puts the data in the custom metric queue.

  :param data: A sequence of data samples
  """
  if gProfiling:
    startTime = time.time()

  message = json.dumps({"protocol": Protocol.PLAIN, "data": data})
  try:
    LOGGER.debug("Publishing message: %s", message)
    messageBus.publish(mqName=gQueueName, body=message, persistent=True)
  except MessageQueueNotFound:
    LOGGER.debug("Creating message queue that doesn't exist: %s", gQueueName)
    messageBus.createMessageQueue(mqName=gQueueName, durable=True)
    LOGGER.debug("Re-publishing message: %s", message)
    messageBus.publish(mqName=gQueueName, body=message, persistent=True)

  LOGGER.debug("forwarded batchLen=%d", len(data))

  if gProfiling and data:
    now = time.time()
    try:
      for sample in data:
        metricName, _value, timestamp = parsePlaintext(sample)
        LOGGER.info(
          "{TAG:CUSLSR.FW.DONE} metricName=%s; timestamp=%s; duration=%.4fs",
          metricName, timestamp.isoformat() + "Z", now - startTime)
    except Exception:
      LOGGER.exception("Profiling failed for sample=%r in data=[%r..%r]",
                       sample, data[0], data[-1])



class _TimeoutSafeBufferedLineReader(object):
  """We have and use this class as an indirect replacement for socket.makefile()
  instance, because socket.makefile() doesn't work properly when timeout is set
  on a socket; see socket.makefile doc for details.
  """

  _RECV_BUF_SIZE = 1024

  def __init__(self, sock):
    """
    :param socket.socket sock: A socket that may have timeout set on it
    """
    self._s = sock

    self._recvBuf = bytearray(b" " * self._RECV_BUF_SIZE)
    self._lineBuf = bytearray()


  def readlinesWithTimeout(self):
    """ Generator that reads newline-terminated lines from the socket and
    yields:
      - None if input inactivity exceeded socket timeout and a
        newline-terminated line is not available
      - non-empty string when a line is available; will include the
        trailing newline unless the stream ends without a newline
    """
    line = None
    # Read some more data
    while True:
      eolPos = self._lineBuf.find("\n")
      if eolPos != -1:
        # Got newline
        line = str(self._lineBuf[0:eolPos + 1])
        del self._lineBuf[0:eolPos + 1]
        yield line
        continue

      try:
        nbytes = self._s.recv_into(self._recvBuf)
      except socket.timeout:
        # A complete line not available yet
        LOGGER.debug("got socket timeout exception")
        yield None
      except OSError, e:
        if e.errno == errno.EINTR:
          continue

        raise
      else:
        if nbytes == 0:
          LOGGER.debug("nbytes=0")
          # EOF reached
          if self._lineBuf:
            line = str(self._lineBuf)
            del self._lineBuf[:]

            # Yield remaining buffer content (without newline)
            yield line

          # Exit generator
          break

        # Append the new data to our line buffer and loop to scan for a line
        self._lineBuf.extend(itertools.islice(self._recvBuf, 0, nbytes))
        continue

    LOGGER.debug("LEAVING readlinesWithTimeout")



def _readlines(sock):
  """ Generator that reads lines from the socket connection and yields:
  - None if a short pause in input activity is detected and a line is not
    available
  - non-empty string when a line is available; will include the
    trailing newline unless the stream ends without a newline

  :param socket.socket sock: input socket
  """
  socketTimeoutOnEntry = sock.gettimeout()
  try:
    # Start in blocking mode
    timeout = None
    sock.settimeout(timeout)

    reader = _TimeoutSafeBufferedLineReader(sock)

    for line in reader.readlinesWithTimeout():
      if line is None:
        # Signal break in data flow
        LOGGER.debug("socket timeout, yielding None")
        yield None

        # Resume blocking mode
        LOGGER.debug("resuming blocking socket mode")
        timeout = None
        sock.settimeout(timeout)
        continue

      # Set a short timeout to detect break in data flow
      if timeout is None:
        LOGGER.debug("lowering timeout")
        timeout = 0.0001
        sock.settimeout(timeout)

      # Yield the line
      yield line
  finally:
    # Restore socket timeout
    sock.settimeout(socketTimeoutOnEntry)



class UDPHandler(SocketServer.BaseRequestHandler):


  def handle(self):
    data = self.request[0].strip()
    with MessageBusConnector() as messageBus:
      _forwardData(messageBus, (data,))



class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
  allow_reuse_address = True



class TCPHandler(SocketServer.StreamRequestHandler):

  def handle(self):

    with self.server.concurrencyTracker as concurrencyCount:
      LOGGER.info("(thread=%s) Receiving samples from client=%s at "
                  "currentConcurrency=%d", threading.currentThread().ident,
                  self.client_address, concurrencyCount)

      batch = []
      with MessageBusConnector() as messageBus:
        for line in _readlines(self.connection):
          if line is not None:
            batch.append(line.strip())
            LOGGER.debug("got line=%r; batchLen=%d", line, len(batch))
          else:
            LOGGER.debug("got data break; batchLen=%d", len(batch))

          if (line is None and batch) or len(batch) >= _MAX_BATCH_SIZE:
            _forwardData(messageBus, batch)
            batch = []
        else:
          if batch:
            # Send the remnant
            _forwardData(messageBus, batch)
          return



class ThreadedTCPServer(SocketServer.ThreadingMixIn,
                        SocketServer.TCPServer,
                        object):
  allow_reuse_address = True


  def __init__(self, listeningAddr, handlerClass):
    self.concurrencyTracker = threading_utils.ThreadsafeCounter()

    super(ThreadedTCPServer, self).__init__(listeningAddr, handlerClass)



@raiseExceptionOnMissingRequiredApplicationConfigPath
def runServer(host="0.0.0.0", port=None, protocol=Protocol.PLAIN,
              transport=Transport.TCP):
  Protocol.current = protocol
  if port is None:
    port = Protocol.getDefaultPort(protocol)

  LOGGER.info("Starting with host=%s, port=%s, protocol=%s, transport=%s",
              host, port, protocol, transport)

  if transport == Transport.UDP:
    server = ThreadedUDPServer((host, port), UDPHandler)
  elif transport == Transport.TCP:
    server = ThreadedTCPServer((host, port), TCPHandler)

  config = Config("application.conf",
                  os.environ["APPLICATION_CONFIG_PATH"])

  global gQueueName
  gQueueName = config.get("metric_listener", "queue_name")

  global gProfiling
  gProfiling = (config.getboolean("debugging", "profiling") or
                LOGGER.isEnabledFor(logging.DEBUG))

  # Serve until there is an interrupt
  server.serve_forever()



if __name__ == "__main__":
  LoggingSupport.initService()

  parser = optparse.OptionParser()
  parser.add_option("--host", default="0.0.0.0")
  parser.add_option("--port", type="int", default=None,
                    help="Default ports (from config): 2003 for plaintext, "
                         "2004 for pickle")
  parser.add_option("--protocol", choices=Protocol.values(),
                    default=Protocol.PLAIN)
  parser.add_option("--transport", choices=Transport.values(),
                    default=Transport.TCP)
  options, _ = parser.parse_args()

  runServer(options.host, options.port, options.protocol, options.transport)
