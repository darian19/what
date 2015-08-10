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
# Formula: YOMP-plumbing.motd

# Installs YOMP's motd fragment scripts so /etc/motd shows YOMP version,
# rpms, and whether updates are available for YOMP.

/etc/update-motd.d/10-show-YOMP-version:
  file.managed:
    - source: salt://YOMP-plumbing/files/motd/show-YOMP-version
    - user: root
    - group: root
    - mode: 0755

/etc/update-motd.d/40-show-YOMP-rpms:
  file.managed:
    - source: salt://YOMP-plumbing/files/motd/show-YOMP-rpms
    - user: root
    - group: root
    - mode: 0755

/etc/update-motd.d/50-show-available-updates:
  file.managed:
    - source: salt://YOMP-plumbing/files/motd/show-available-updates
    - user: root
    - group: root
    - mode: 0755

# Set up convenience scripts

show-YOMP-info:
  file.symlink:
    - target: /etc/update-motd.d/40-show-YOMP-rpms
    - name: /usr/local/sbin/show-YOMP-info
    - require:
      - file: /etc/update-motd.d/40-show-YOMP-rpms

show-YOMP-version:
  file.symlink:
    - target: /etc/update-motd.d/10-show-YOMP-version
    - name: /usr/local/sbin/show-YOMP-version
    - require:
      - file: /etc/update-motd.d/10-show-YOMP-version

