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
AMI unit tests for base YOMP tooling
"""
import agamotto
import os
import unittest


APPLICATION_CONFIG_PATH = os.environ.get("APPLICATION_CONFIG_PATH",

YOMP_SCRIPTS = [
  "/usr/local/bin/run-YOMP-tests",
  "/usr/local/sbin/YOMPlog_rotator",
  "/usr/local/sbin/update-motd"
]

YOMP_CONFIG_FILES = [
  "%s/YOMP-api.conf" % APPLICATION_CONFIG_PATH,
  "%s/application.conf" % APPLICATION_CONFIG_PATH,
  "%s/../../nta.utils/conf/logging.conf" % APPLICATION_CONFIG_PATH,
  "%s/model-swapper.conf" % APPLICATION_CONFIG_PATH,
  "%s/nginx-maint.conf" % APPLICATION_CONFIG_PATH,
  "%s/product.conf" % APPLICATION_CONFIG_PATH,
  "%s/quota.conf" % APPLICATION_CONFIG_PATH,
  "%s/../../nta.utils/conf/rabbitmq.conf" % APPLICATION_CONFIG_PATH,
  "%s/supervisord.conf" % APPLICATION_CONFIG_PATH
]


class TestYOMPInstallation(unittest.TestCase):


  def testYOMPConfigurationFilesPresent(self):
    for confFile in YOMP_CONFIG_FILES:
      self.assertTrue(agamotto.file.exists(confFile), "%s missing" % confFile)


  def testYOMPCronjobs(self):
    self.assertTrue(agamotto.cron.entry(
      "7 * * * * /usr/local/sbin/lockrun --lockfile=/var/lock/shuffle_YOMPlogs -- /usr/local/sbin/shuffle_YOMPlogs 2>&1 | logger -t gs-shuffle-YOMPlogs"))


  def testMetricCollectorIsRunning(self):
    self.assertTrue(agamotto.process.running(
                    "python -m YOMP.app.runtime.metric_collector"))


  def testAnomalyServiceIsRunning(self):
    self.assertTrue(agamotto.process.running(
                    "python -m htmengine.runtime.anomaly_service"))


  def testModelSchedulerIsRunning(self):
    self.assertTrue(agamotto.process.running(
      "python -m htmengine.model_swapper.model_scheduler_service"))


  def testNginxServiceEnabled(self):
    self.assertTrue(agamotto.service.enabled("YOMP-preload"))


  def testYOMPServicesEnabled(self):
    self.assertTrue(agamotto.service.enabled("YOMPservices"))


  def testYOMPupdates(self):
    self.assertTrue(agamotto.service.enabled("YOMPupdates"))


  def testSupervisordListening(self):
    self.assertTrue(agamotto.network.isListening(9001))


  def testSupervisordConfiguration(self):
    self.assertTrue(agamotto.file.exists("/etc/YOMP/supervisord.vars"))
    self.assertTrue(agamotto.file.exists("/etc/init.d/YOMPservices"))


  def testSupervisordInitscript(self):
    self.assertTrue(agamotto.file.contains("/etc/init.d/YOMPservices",
                    'su ec2-user -c "${supervisor_helper} start"'))
    self.assertTrue(agamotto.file.contains("/etc/init.d/YOMPservices",
                    'supervisor_helper="${NUMENTA}/supervisord-helper"'))


  def testYOMPDatabaseExists(self):
    mysqlPasswordFile = "/etc/YOMP/mysql_password"
    sqlPrefix = "mysql -u root --silent "
    if os.path.isfile(mysqlPasswordFile):
      with open(mysqlPasswordFile) as passwordFile:
        mysqlPassword = passwordFile.read().strip()
        sqlPrefix = sqlPrefix + " --password=" + "'" + mysqlPassword + "' "
    raw = "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'YOMP';"
    sqlQuery = sqlPrefix + '--execute "' + raw + '"' + "|grep '^YOMP$'"
    self.assertTrue(agamotto.process.stdoutContains(sqlQuery, 'YOMP'),
                    "YOMP database missing")



if __name__ == "__main__":
  unittest.main()
