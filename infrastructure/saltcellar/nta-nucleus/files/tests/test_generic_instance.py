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
Base AMI sanity checking. These tests are common to all of our AMIs.

* Cleantmp should be enabled on all of our machines
* NTPd should be enabled and running. Many things break when time is unsynced
* SSH should be enabled and running.
* All files on an AMI should have owners.

Security related checks:
* SUID file check - If a package adds a new suid file, we want to know
* SGID file check - We want to know about new sgid files too.
"""

import agamotto
import unittest
from agamotto.process import execute

SGID_FILE_WHITELIST = [
  "/bin/cgclassify",
  "/bin/cgexec",
  "/sbin/netreport",
  "/usr/bin/at",
  "/usr/bin/chage",
  "/usr/bin/chfn",
  "/usr/bin/chsh",
  "/usr/bin/crontab",
  "/usr/bin/gpasswd",
  "/usr/bin/ksu",
  "/usr/bin/locate",
  "/usr/bin/lockfile",
  "/usr/bin/newgrp",
  "/usr/bin/passwd",
  "/usr/bin/screen",
  "/usr/bin/ssh-agent",
  "/usr/bin/staprun",
  "/usr/bin/sudo",
  "/usr/bin/wall",
  "/usr/bin/write",
  "/usr/lib64/vte/gnome-pty-helper",
  "/usr/libexec/abrt-action-install-debuginfo-to-abrt-cache",
  "/usr/libexec/openssh/ssh-keysign",
  "/usr/libexec/pt_chown",
  "/usr/libexec/utempter/utempter",
  "/usr/sbin/lockdev",
  "/usr/sbin/postdrop",
  "/usr/sbin/postqueue",
  "/usr/sbin/userhelper",
  "/usr/sbin/usernetctl",
]

SUID_FILE_WHITELIST = [
  "/bin/fusermount",
  "/bin/mount",
  "/bin/ping",
  "/bin/ping6",
  "/bin/su",
  "/bin/umount",
  "/lib64/dbus-1/dbus-daemon-launch-helper",
  "/sbin/mount.nfs",
  "/sbin/netreport",
  "/sbin/pam_timestamp_check",
  "/sbin/unix_chkpwd",
  "/usr/bin/at",
  "/usr/bin/chage",
  "/usr/bin/chfn",
  "/usr/bin/chsh",
  "/usr/bin/crontab",
  "/usr/bin/gpasswd",
  "/usr/bin/ksu",
  "/usr/bin/locate",
  "/usr/bin/newgrp",
  "/usr/bin/passwd",
  "/usr/bin/ssh-agent",
  "/usr/bin/staprun",
  "/usr/bin/sudo",
  "/usr/bin/sudoedit",
  "/usr/bin/wall",
  "/usr/bin/write",
  "/usr/lib64/vte/gnome-pty-helper",
  "/usr/libexec/abrt-action-install-debuginfo-to-abrt-cache",
  "/usr/libexec/openssh/ssh-keysign",
  "/usr/libexec/pt_chown",
  "/usr/libexec/utempter/utempter",
  "/usr/sbin/lockdev",
  "/usr/sbin/postdrop",
  "/usr/sbin/postqueue",
  "/usr/sbin/userhelper",
  "/usr/sbin/usernetctl",
]

class TestGenericPlumbing(unittest.TestCase):

  def testCleantmpEnabled(self):
    """
    Cleantmp service is enabled to periodically clean up /tmp so
    we don't fill up / again.
    """
    self.assertTrue(agamotto.service.enabled("cleantmp"))


  def testSsh(self):
    """
    ssh service is enabled and listening on the AMI.
    """
    self.assertTrue(agamotto.network.isListening(22))
    self.assertTrue(agamotto.service.enabled("sshd"))


  def testNtpEnabled(self):
    """
    NTP enabled so instance clock time stays valid.
    """
    self.assertTrue(agamotto.service.enabled("ntpd"))


  def testNtpRunning(self):
    """
    NTP is actually running on the instance.
    """
    self.assertTrue(agamotto.process.running(
                    "ntpd -u ntp:ntp -p /var/run/ntpd.pid -g"))


  def testThereAreNoUnownedFiles(self):
    """
    No files on AMI that are not owned by a user
    """
    self.assertEquals(execute(
      "find / -xdev \( -nouser -o -nogroup \) \( -path /tmp -o -path /var/tmp \) -prune -print 2>&1 | \
         grep -vi 'No such file or directory' | \
         wc -l").strip(), "0")


  def testAllSuidFilesAreInWhitelist(self):
    """
    All SUID files are on whitelist

    Ensure that no new packages we add to the AMI add suid files without
    us knowing about them since they're potential security issues.
    """
    foundSuidFiles = execute("find / -xdev -perm +4000 2>&1 | \
      grep -v 'No such file or directory'").split('\n')
    for suidFile in foundSuidFiles:
      if len(suidFile) > 0:
        self.assertTrue(suidFile in SUID_FILE_WHITELIST,
                        "suid file %s not in SUID_FILE_WHITELIST" % suidFile)


  def testAllSgidFilesAreInWhitelist(self):
    """
    All SGID files are on whitelist

    Ensure that no new packages we add to the AMI add sgid files without
    us knowing about them, since they're potential security issues.
    """
    foundSgidFiles = execute("find / -xdev -perm +2000 2>&1 | \
      grep -v 'No such file or directory'").split('\n')
    for sgidFile in foundSgidFiles:
      if len(sgidFile) > 0:
        self.assertTrue(sgidFile in SGID_FILE_WHITELIST,
                        "sgid file %s not in SGID_FILE_WHITELIST" % sgidFile)



if __name__ == "__main__":
  unittest.main()
