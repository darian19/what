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
# Formula: numenta-python

# Install anaconda python and ensure that the packages we require are
# installed and are the correct version.
#
# Numenta style requires we lock to specific versions so we don't get
# burned again by mystery bugs when new module versions come out.

include:
  - devtools
  - nta-nucleus

anaconda-python:
  pkg:
    - installed
    - pkgs:
      - gs-anaconda
    - require:
      - pkg: compiler-toolchain
    - watch_in:
      - cmd: enforce-anaconda-permissions

# Install our standard pip packages into anaconda python

anaconda-paver:
  pip.installed:
    - name: paver == 1.2.3
    - bin_env: /opt/numenta/anaconda/bin/pip
    - watch_in:
      - cmd: enforce-anaconda-permissions
    - require:
      - pkg: anaconda-python

anaconda-pip:
  pip.installed:
    - name: pip == 7.1.0
    - bin_env: /opt/numenta/anaconda/bin/pip
    - watch_in:
      - cmd: enforce-anaconda-permissions
    - require:
      - pkg: anaconda-python

anaconda-setuptools:
  pip.installed:
    - name: setuptools
    - upgrade: True
    - bin_env: /opt/numenta/anaconda/bin/pip
    - watch_in:
      - cmd: enforce-anaconda-permissions
    - require:
      - pkg: anaconda-python

anaconda-wheel:
  pip.installed:
    - name: wheel == 0.24.0
    - bin_env: /opt/numenta/anaconda/bin/pip
    - watch_in:
      - cmd: enforce-anaconda-permissions
    - require:
      - pkg: anaconda-python

# Install a python2.7 symlink so /usr/bin/env python2.7 will work
python-27-symlink:
  file.symlink:
    - target: /opt/numenta/anaconda/bin/python
    - name: /usr/local/bin/python2.7
    - require:
      - cmd: enforce-anaconda-permissions
      - pkg: anaconda-python

# Once we have installed our packages, make sure that the anaconda python
# directory tree has the correct ownership.
enforce-anaconda-permissions:
  cmd.wait:
    - name: chown -R ec2-user:ec2-user /opt/numenta/anaconda
    - require:
      - group: ec2-user
      - pkg: anaconda-python
      - user: ec2-user
