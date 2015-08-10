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
"""
AMI unit tests for nginx support
"""

import agamotto
import os
import requests
import socket
import unittest


CONF_D = os.environ.get("APPLICATION_CONFIG_PATH", "/opt/numenta/YOMP/conf")

def probePort(host="127.0.0.1", port=80, command=None):
  s = socket.socket()
  s.connect((host, port))
  if command:
    s.send(command)
  rawData = s.recv(1024)
  s.close()
  return rawData


def probeHttps(host="127.0.0.1", port=443, verifyCertificate=False, path="/"):
  return requests.get("https://%s:%s/%s" % (host, port, path),
                      verify=verifyCertificate).text


class TestNginxInstallation(unittest.TestCase):

  def testListeningOnPort80(self):
    self.assertTrue(agamotto.network.isListening(80))


  def testListeningOnPort443(self):
    self.assertTrue(agamotto.network.isListening(443))


  def testHttpRedirectsToHttps(self):
    # Use probePort so we use socket. We don't want the call to actually
    # follow the redirect since we want to confirm the redirect is in place.
    portResponse = probePort(command="GET / HTTP/1.1\nHost: localhost\n\n")
    self.assertIn("301 Moved Permanently", portResponse,
                  "Did not see 301 redirect on port 80")


  def testCheckHttpsContent(self):
    self.assertIn("<title>| YOMP</title>", probeHttps(path="/YOMP"),
                  "port 443 is not returning a YOMP title")


  def testNginxApiConfiguration(self):
    self.assertTrue(agamotto.file.exists("%s/YOMP-api.conf" % CONF_D))


  def testNginxMaintenanceConfiguration(self):
    self.assertTrue(agamotto.file.exists("%s/nginx-maint.conf" % CONF_D))


  def testNginxIsRunning(self):
    self.assertTrue(agamotto.process.is_running(
      "nginx: master process /usr/sbin/nginx -p . -c %s/YOMP-api.conf"
      % CONF_D))
    self.assertTrue(agamotto.process.is_running("nginx: worker process"))


  def testNginxInitScript(self):
    self.assertTrue(agamotto.file.exists("/etc/init.d/nginx"))
    self.assertTrue(agamotto.file.contains("/etc/init.d/nginx",
                    "YOMP_HOME=/opt/numenta/YOMP"))
    self.assertTrue(agamotto.file.contains("/etc/init.d/nginx",
                    "YOMP_NGINX_CONF=conf/YOMP-api.conf"))
    self.assertTrue(agamotto.file.contains("/etc/init.d/nginx",
                    "NGINX_MAINT_CONF=conf/nginx-maint.conf"))
    self.assertTrue(agamotto.file.contains("/etc/init.d/nginx",
                    "start_maintenance() {"))



if __name__ == "__main__":
  unittest.main()
