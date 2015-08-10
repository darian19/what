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
# Formula role-YOMP.install-YOMP

# Actually installs YOMP & NuPIC on an AMI

# TODO - Generate the YOMP.scripted-packages - TAUR-549
# include:
#   - YOMP.scripted-packages

# Add helper script to restart the YOMPservices service
/usr/local/bin/YOMPservices:
  file.managed:
    - source: salt://role-YOMP/files/YOMPservices-helper
    - user: ec2-user
    - group: ec2-user
    - mode: 755

# Ensure our permissions are correct since we can't count on user vagrant
# always having the same uid and gid.

reset-nta-permissions:
  cmd.wait:
    - name: chown -R ec2-user:ec2-user /opt/numenta/nta
    - only_if:
      - cmd: test -d /opt/numenta/nta

reset-YOMP-permissions:
  cmd.wait:
    - name: chown -R ec2-user:ec2-user /opt/numenta/products/YOMP
    - only_if:
      - cmd: test -d /opt/numenta/products/YOMP

reset-nupic-permissions:
  cmd.wait:
    - name: chown -R ec2-user:ec2-user /opt/numenta/nupic
    - only_if:
      - cmd: test -d /opt/numenta/nupic

# Per MER-2323
tickle-YOMP:
  file.managed:
    - name: /usr/local/sbin/tickle-YOMP
    - source: salt://role-YOMP/files/tickle-YOMP
    - user: ec2-user
    - group: ec2-user
    - mode: 755
  cron.present:
    - name: lockrun --lockfile=/var/lock/tickle-YOMP.lock -- /usr/local/sbin/tickle-YOMP > /dev/null 2>&1
    - identifier: tickle-YOMP
    - user: root
    - minute: '*/10'
    - require:
      - cron: set-sane-path-in-crontab
      - file: tickle-YOMP
