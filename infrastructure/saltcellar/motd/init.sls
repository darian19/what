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
# Formula: motd

# Install tooling for automatic motd generation.

# Install the motd driver package.
acta-diurna:
  pkg.latest

# motd fragment scripts go here
/etc/update-motd.d:
  file.directory:
    - user: root
    - group: root
    - mode: 755

/etc/update-motd.d.disabled:
  file.directory:
    - user: root
    - group: root
    - mode: 755

# Add Numenta logo to motd
/etc/update-motd.d/00-print-logo.motd:
  file.managed:
    - source: salt://motd/files/motd.logo
    - user: root
    - group: root
    - mode: 644
    - require:
      - file: /etc/update-motd.d
    - watch_in:
      - cmd: update-motd

# Add Standard banner information to motd
/etc/update-motd.d/20-banner.motd:
  file.managed:
    - source: salt://motd/files/20-banner.motd
    - mode: 755
    - require:
      - file: /etc/update-motd.d
    - watch_in:
      - cmd: update-motd

# Add salt version to motd
/etc/update-motd.d/30-salt-version.motd:
  file.managed:
    - source: salt://motd/files/30-salt-version.motd
    - mode: 755
    - require:
      - file: /etc/update-motd.d
    - watch_in:
      - cmd: update-motd

update-motd:
# Install our motd cronjob script
  file.managed:
    - name: /etc/cron.daily/update-motd
    - source: salt://motd/files/update-motd.centos
    - mode: 755
    - require:
      - file: python-27-symlink
      - pkg: acta-diurna
# Run the update-motd job, but only run if a fragment script is added/changed
  cmd.wait:
    - name: /etc/cron.daily/update-motd
    - cwd: /
    - require:
      - file: python-27-symlink
      - pkg: acta-diurna
      - sls: numenta-python
# Install the actual cronjob
  cron.present:
    - name: /etc/cron.daily/update-motd 2>&1 > /dev/null
    - identifier: motd-updates
    - user: root
    - minute: '*/15'
    - require:
      - cron: set-sane-path-in-crontab
      - file: /etc/cron.daily/update-motd
      - file: /etc/update-motd.d
      - pkg: acta-diurna

update-motd-symlink:
  file.symlink:
    - target: /etc/cron.daily/update-motd
    - name: /usr/local/sbin/update-motd
