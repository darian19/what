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
# Formula: nta-nucleus.settings
#
# Install the standard settings for a base numenta server

# Ensure cronjobs have the correct PATH.
set-sane-path-in-crontab:
  cron.env_present:
    - name: PATH
    - value: /opt/numenta/anaconda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/sbin:/usr/bin:/bin

# Per TAUR-564, bump up somaxconn in sysctl.conf
set-somaxconn-sysctl-conf:
  file.append:
    - name: /etc/sysctl.conf
    - text:
      - "\n"
      - "# Per TAUR-564, bump up somaxconn"
      - "net.core.somaxconn=1024"

# In addition to setting it in sysctl.conf, run it now so we don't have to
# reboot before the settings take effect.
update-somaxconn:
  cmd.wait:
    - name: sysctl -w net.core.somaxconn=1024
    - watch_in:
      - cmd: set-somaxconn-sysctl-conf
