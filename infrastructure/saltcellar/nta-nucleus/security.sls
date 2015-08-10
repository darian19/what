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
# Formula: nta-nucleus.security
#
# Install security tests for AMI acceptance testing. We currently
# test that heartbleed and shellshock are fixed.

# Make sure we have the latest bash & openssl to protect us from shellshock
# and heartbleed
security-patch-packages:
  pkg:
    - latest
    - pkgs:
      - bash

# TODO: TAUR-759 Re-enable the openssl kludge after getting the YOMP pipeline
# unstuck
#      - openssl

include:
  - ssh

# Install user AMI tests
/etc/numenta/tests/test_user_accounts.py:
  file.managed:
    - source: salt://nta-nucleus/files/tests/test_user_accounts.py
    - user: root
    - group: root
    - mode: 755
    - require:
      - file: ami-test-directory

# Install shellshock tests
/etc/numenta/tests/test_shellshock.py:
  file.managed:
    - user: root
    - group: root
    - source: salt://nta-nucleus/files/tests/test_shellshock.py
    - mode: 755
    - require:
      - file: ami-test-directory

# Install test support for CVE-2015-0235 (GHOST)
# Install ghost test helper
/etc/numenta/tests/helpers/ghost-test-helper.py:
  file.managed:
    - user: root
    - group: root
    - source: salt://nta-nucleus/files/tests/ghost-test-helper.py
    - mode: 755
    - require:
      - file: ami-test-helper-directory

# Install ghost tests
/etc/numenta/tests/test_ghost.py:
  file.managed:
    - user: root
    - group: root
    - source: salt://nta-nucleus/files/tests/test_ghost.py
    - mode: 755
    - require:
      - file: ami-test-directory
