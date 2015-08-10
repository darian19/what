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
Test shellshock and other related bash bugs
"""
import agamotto
import unittest


class TestForBashSecurityBugs(unittest.TestCase):

  def testForBashCVE_2014_6271(self):
    """Is bash immune to CVE-2014-6271?
    """
    test6271 = ("(env x='() { :;}; echo vulnerable' "
                "bash -c \"echo this is a test\") 2>&1")
    self.assertFalse(agamotto.process.stdoutContains(test6271, 'vulnerable'),
                     'Bash is vulnerable to CVE-2014-6271')


  def testForBashCVE_2014_6277(self):
    """Is bash immune to CVE-2014-6277?
    """
    test6277 = "foo='() { echo still vulnerable; }' bash -c foo 2>&1"
    self.assertFalse(agamotto.process.stdoutContains(test6277,
                                                     'still vulnerable'),
                     'Bash is vulnerable to CVE-2014-6277')


  def testForBashCVE_2014_6278(self):
    """Is bash immune to CVE-2014-6278?
    """
    test6278 = ("shellshocker='() { echo You are vulnerable; }' "
                "bash -c shellshocker")
    self.assertFalse(agamotto.process.stdoutContains(test6278, 'vulnerable'),
                     'Bash is vulnerable to CVE-2014-6278')


  def testForBashCVE_2014_7169(self):
    """Is bash immune to CVE-2014-7169?
    """
    testFor7169 = ("env X='() { (a)=>\' bash -c \"echo echo vuln\";"
                   " [[ \"$(cat echo)\" == \"vuln\" ]] && "
                   "echo \"still vulnerable :(\" 2>&1")
    self.assertFalse(agamotto.process.stdoutContains(testFor7169,
                                                     'still vulnerable'),
                     'Bash is vulnerable to CVE-2014-7169')


  def testForBashCVE_2014_7186_a(self):
    """Is bash immune to CVE-2014-7186 using test from shellshocker.net?"""
    test7186shellshocker = ("bash -c 'true <<EOF <<EOF <<EOF <<EOF <<EOF "
      "<<EOF <<EOF <<EOF <<EOF <<EOF <<EOF <<EOF <<EOF <<EOF' ||"
      " echo 'CVE-2014-7186 vulnerable, redir_stack'")
    self.assertFalse(agamotto.process.stdoutContains(test7186shellshocker,
                                                     'vulnerable'),
                     'Vulnerable to CVE-2014-7186, redir_stack')


  def testForBashCVE_2014_7186_c(self):
    """Is bash immune to CVE-2014-7186 using eblake@redhat.com's test?"""
    # Try Eric Blake's test too
    blake7186Test = ("""bash -c "export f=1 g='() {'; f() { echo 2;}; 
                        export -f f; bash -c 'echo \$f \$g; f; env |
                        grep ^f='"
                     """)
    safe=("1 () {\n2\nf=1\n")
    self.assertTrue(agamotto.process.stdoutContains(blake7186Test, safe),
                    "Fails Eric Blake's CVE-2014-7186 test")


  def testForBashCVE_2014_7187a(self):
    """Is bash immune to CVE-2014-7187 using shellshocker.net test?"""
    test7187 = ("""(for x in {1..200} ; do echo "for x$x in ; do :"; done; 
                    for x in {1..200} ; do echo done ; done) | bash || 
                    echo "CVE-2014-7187 vulnerable, word_lineno" """)
    self.assertFalse(agamotto.process.stdoutContains(test7187, 'vulnerable'),
                     'CVE-2014-7187 vulnerable, word_lineno')


if __name__ == '__main__':
  unittest.main()
