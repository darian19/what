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

from optparse import OptionParser
import socket
import time



def createCustomMetric(server, port):
  runIdentifier = str(time.time())
  metricName = "test.metric.%s" % runIdentifier
  sock = socket.socket()
  sock.connect((server, port))
  sock.sendall("%s 5.0 1386201600\n" % metricName)
  sock.shutdown(socket.SHUT_WR)
  _response = sock.recv(4096)
  sock.close()



if __name__ == "__main__":
  usage = "usage: %prog [options]"
  parser = OptionParser(usage=usage)
  parser.add_option(
    "--server",
    dest="server",
    help="Server",
    default="localhost")
  parser.add_option(
    "--port",
    dest="port",
    help="Port",
    default=2003)

  (options, args) = parser.parse_args()

  createCustomMetric(options.server, options.port)
