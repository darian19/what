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
# Formula: YOMP-plumbing

# Install YOMP's support requirements on a server. Essentially, everything
# except YOMP & NuPic so we can have as much as possible already in place
# when Jenkins starts to bake a new YOMP AMI.

# Ensure the directories we need are in place
etc-YOMP:
  file.directory:
    - name: /etc/YOMP
    - user: ec2-user
    - group: ec2-user
    - mode: 0755

products-directory:
  file.directory:
    - name: /opt/numenta/products
    - user: root
    - group: root
    - mode: 0755
    - require:
      - file: /opt/numenta

YOMP-directory:
  file.directory:
    - name: /opt/numenta/products/YOMP
    - user: root
    - group: root
    - mode: 0755
    - require:
      - file: products-directory

YOMP-bin-directory:
  file.directory:
    - name: /opt/numenta/products/YOMP/bin
    - user: root
    - group: root
    - mode: 0755
    - require:
      - file: YOMP-directory

numenta-log-directory:
  file.directory:
    - name: /opt/numenta/logs
    - user: root
    - group: root
    - mode: 0755

# Pull in the other formulas required for a YOMP server
include:
  - nta-nucleus
  - aws-support
  - saltsolo
  - YOMP-plumbing.yumrepos
  - YOMP-plumbing.loghandling
  - YOMP-plumbing.motd
  - YOMP-plumbing.support-tools
  - YOMP-plumbing.supervisor-tooling
  - YOMP-plumbing.YOMP-updater-support
  - YOMP-plumbing.zap-public-keys
  - YOMP-plumbing.nginx-tooling
  - mysql
  - rabbitmq
  - rabbitmq.YOMP

# Set rpm name to use in salt solo
set-saltsolo-formula-rpm-to-YOMP:
  file.managed:
    - name: /etc/numenta/saltsolo-rpmname
    - require:
      - file: /etc/numenta
    - contents: YOMP-saltcellar

# Add the YOMP test helper
/usr/local/bin/run-YOMP-tests:
  file.managed:
    - source: salt://YOMP-plumbing/files/run-YOMP-tests
    - user: ec2-user
    - group: ec2-user
    - mode: 755

# YOMP boxes should only run salt during bake or during a YOMP update. They're
# a special case since they're customer machines and we can't go in and fix
# them if an update to the salt formulas breaks them.
#
# Other boxes that run solo, like our webservers, should still run salt out
# of cron. If a formula push breaks something on them, we have the power to
# either spin up replacements or go in and do whatever fix is required.
#
# Only external customer boxes get to not run salt out of cron.

disable-salt-cronjob:
  file.managed:
    - name: /etc/numenta/no-salt-cron
    - contents: Never run salt manually or via cron on YOMP instances. Salt should only run during AMI bake or when triggered by the YOMP-updater"
    - require:
      - file: /etc/numenta

# Install numenta pipeline utilities.
numenta-infrastructure-python:
  pkg.latest

# We'll need YOMPcli
anaconda-YOMPcli:
  pip.installed:
    - name: YOMPcli >= 1.1.1
    - bin_env: /opt/numenta/anaconda/bin/pip
    - watch_in:
      - cmd: enforce-anaconda-permissions
    - require:
      - pkg: anaconda-python

# Configure s3cmd for root & ec2-user
ec2user-s3cmd-configuration:
  file.managed:
    - name: /root/.s3cfg
    - source: salt://YOMP-plumbing/files/updater/s3cfg
    - user: root
    - group: root
    - mode: 0600

root-s3cmd-configuration:
  file.managed:
    - name: /home/ec2-user/.s3cfg
    - source: salt://YOMP-plumbing/files/updater/s3cfg
    - user: ec2-user
    - group: ec2-user
    - mode: 0600

# The install-YOMP-packages script handles downloading YOMP/nupic/etc rpms and
# wheels and then installing them
YOMP-installer:
  file.managed:
    - name: /usr/local/bin/install-YOMP-packages
    - source: salt://YOMP-plumbing/files/install-YOMP-packages
    - user: root
    - group: root
    - mode: 755
    - require:
      - file: etc-YOMP
      - file: root-s3cmd-configuration
      - pkg: aws-tools
      - pkg: numenta-infrastructure-python
