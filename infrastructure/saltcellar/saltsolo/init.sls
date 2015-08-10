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
# Formula: saltsolo

# Installs salt solo tooling

/usr/local/bin/run-salt-solo:
  file.managed:
    - source: salt://saltsolo/files/run-salt-solo
    - mode: 755

# Install salt crontask.
#
# DO NOT DISABLE SALT RUNNING FROM CRON, EVER!
#
# If a script has a problem with being triggered during Salt runs, the problem
# is in the script, not because we run Salt automatically.
salt-cronjob:
  file.managed:
    - source: salt://saltsolo/files/salt-cronjob
    - name: /usr/local/sbin/salt-cronjob
    - mode: 755
    - require:
      - file: /usr/local/bin/run-salt-solo
  cron.present:
    - name: /usr/local/sbin/salt-cronjob 2>&1 | tee /var/log/salt-solo-lastrun.log | logger -t run-salt-solo
    - identifier: salt-cronjob
    - user: root
    - minute: '17'
    - hour: '*'
    - require:
      - cron: set-sane-path-in-crontab
      - file: salt-cronjob
      - file: set-salt-output-to-mixed

# Install saltsolo init script
/etc/init.d/saltsolo:
  file.managed:
    - source: salt://saltsolo/files/saltsolo.initd
    - mode: 755

# Enable the service
saltsolo:
  service.enabled:
    - require:
      - file: /etc/init.d/saltsolo
      - file: salt-cronjob

# Make salt output sane
set-salt-output-to-mixed:
  file.append:
    - name: /etc/salt/minion
    - text:
      - "state_output: mixed"
