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
# Formula: nta-nucleus.services
#
# Install & enable the base services for a numenta server

# Install init script to set domain search order in /etc/resolv.conf
/etc/init.d/fix-resolv-conf:
  file.managed:
    - source: salt://nta-nucleus/files/fix-resolv-conf.initd
    - mode: 755

# Install cleantmp init script
/etc/init.d/cleantmp:
  file.managed:
    - source: salt://nta-nucleus/files/cleantmp.initd
    - mode: 755

# Ensure ntp is running - synced time is essential
ntpd:
  service.running:
    - enable: true

# Ensure syslog running
rsyslog:
  service.running:
    - enable: true

# Ensure cleantmp is enabled
cleantmp:
  service.enabled

fix-resolv-conf:
  service.enabled
