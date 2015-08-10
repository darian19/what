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

import multiprocessing
from subprocess import Popen, PIPE
import unittest2 as unittest

import sqlalchemy
import sqlalchemy.exc

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch
from taurus.metric_collectors import collectorsdb, logging_support



def setUpModule():
  logging_support.LoggingSupport.initTestApp()



def _forkedEngineId():
  """ Get engine and return id.  Needs to be in global namespace for
  multiprocessing.Pool().apply() to work properly
  """
  return id(collectorsdb.engineFactory())



def startProxy(host, port, listenPort):
  """ Start a proxy using netcat (nc)

  This generator uses two netcat processes to set up a proxy between a local
  port and remote host/port:

  > (local port) nc <==> nc <==> target addr/port

  Client will then connect to localhost on port defined by `listenPort` in the
  "wait for kill signal" period.  Because it is a generator, you must call
  next() on the return value to begin.  The function will start the proxy and
  wait for a "kill" signal.  For example:

      proxy = startProxy("taurusdb.numenta.com", 3306, 6033)
      proxy.next()
      ... connect to port 6033 on localhost and do stuff ...
      proxy.send("kill")

  :param host: Remote host to proxy
  :param port: Remote port
  :param listenPort: Local listen port
  """
  listener = destination = None
  try:
    listener = Popen(["nc", "-lk", "0.0.0.0", str(listenPort)],
                     stdin=PIPE, stdout=PIPE)
    destination = Popen(["nc", host, str(port)],
                     stdin=listener.stdout, stdout=listener.stdin)

    killed = False
    while True:
      command = (yield)
      if command == "kill" and not killed:
        killed = True
        listener.kill()
        destination.kill()

  finally:
    if isinstance(listener, Popen):
      if listener.poll() is None:
        listener.kill()

    if isinstance(destination, Popen):
      if destination.poll() is None:
        destination.kill()



class CollectorsdbTestCase(unittest.TestCase):
  def tearDown(self):
    # Return collectorsdb engine singleton to a pristine state.  If running
    # tests in non-boxed mode, for example, to collect coverage statistics,
    # this is necessary or else subsequent tests will use the engine singleton
    # that is configured to use the proxy.
    collectorsdb.resetEngineSingleton()


  def testEngineFactorySingletonPattern(self):
    # Call collectorsdb.engineFactory()
    engine = collectorsdb.engineFactory()

    # Call collectorsdb.engineFactory() again and assert singleton
    engine2 = collectorsdb.engineFactory()
    self.assertIs(engine2, engine)

    # Call collectorsdb.engineFactory() in different process, assert new
    # instance
    originalEngineId = id(engine)
    engine3 = multiprocessing.Pool(processes=1).apply(_forkedEngineId)
    self.assertNotEqual(id(engine3), originalEngineId)



class TestTransientErrorHandling(unittest.TestCase):
  def tearDown(self):
    # Return collectorsdb engine singleton to a pristine state.  If running
    # tests in non-boxed mode, for example, to collect coverage statistics,
    # this is necessary or else subsequent tests will use the engine singleton
    # that is configured to use the proxy.
    collectorsdb.resetEngineSingleton()


  def testTransientErrorRetryDecorator(self):
    # Setup proxy.  We'll patch config later, so we need to cache the values
    # so that the original proxy may be restarted with the original params
    config = collectorsdb.CollectorsDbConfig()

    originalHost = config.get("repository", "host")
    originalPort = config.getint("repository", "port")

    def _startProxy():
      p = startProxy(originalHost, originalPort, 6033)
      p.next()
      return p

    proxy = _startProxy()
    self.addCleanup(proxy.send, "kill")

    # Patch collectorsdb config with local proxy
    with ConfigAttributePatch(
          config.CONFIG_NAME,
          config.baseConfigDir,
          (("repository", "host", "127.0.0.1"),
           ("repository", "port", "6033"))):

      # Force refresh of engine singleton
      collectorsdb.resetEngineSingleton()
      engine = collectorsdb.engineFactory()

      # First, make sure valid query returns expected results
      res = engine.execute("select 1")
      self.assertEqual(res.scalar(), 1)

      @collectorsdb.retryOnTransientErrors
      def _killProxyTryRestartProxyAndTryAgain(n=[]):
        if not n:
          # Kill the proxy on first attempt
          proxy.send("kill")
          proxy.next()
          try:
            engine.execute("select 1")
            self.fail("Proxy did not terminate as expected...")
          except sqlalchemy.exc.OperationalError:
            pass
          n.append(None)
        elif len(n) == 1:
          # Restore proxy in second attempt
          newProxy = _startProxy()
          self.addCleanup(newProxy.send, "kill")
          n.append(None)

        res = engine.execute("select 2")

        return res

      # Try again w/ retry decorator
      result = _killProxyTryRestartProxyAndTryAgain()

      # Verify that the expected value is eventually returned
      self.assertEqual(result.scalar(), 2)



if __name__ == "__main__":
  unittest.main()
