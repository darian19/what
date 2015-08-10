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
# Formula: nta-nucleus.test-support
#
# Install test tooling

# Install a standard location for AMI tests to install into
ami-test-directory:
  file.directory:
    - user: root
    - group: root
    - mode: 755
    - name: /etc/numenta/tests
    - require:
      - file: /etc/numenta

# Install a standard location for AMI tests helper scripts to install into
ami-test-helper-directory:
  file.directory:
    - user: root
    - group: root
    - mode: 755
    - name: /etc/numenta/tests/helpers
    - require:
      - file: ami-test-directory

# Install image test runner
/usr/local/sbin/run-ami-tests:
  file.managed:
    - source: salt://nta-nucleus/files/tests/run-ami-tests
    - user: root
    - group: root
    - mode: 755

# Add the generic AMI tests
/etc/numenta/tests/test_generic_instance.py:
  file.managed:
    - source: salt://nta-nucleus/files/tests/test_generic_instance.py
    - mode: 755
    - require:
      - file: ami-test-directory
