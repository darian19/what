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
# Formula: YOMP-plumbing.loghandling
#
# Install support for YOMP logging, both to S3 and locally on the instance

# Rotate YOMP's logfiles, and upload to S3 if user has enabled it.
shuffle-YOMPlogs:
  file.managed:
    - name: /usr/local/sbin/shuffle_YOMPlogs
    - source: salt://YOMP-plumbing/files/loghandling/shuffle_YOMPlogs
    - user: root
    - group: root
    - mode: 0755
  cron.present:
    - name: /usr/local/sbin/lockrun --lockfile=/var/lock/shuffle_YOMPlogs -- /usr/local/sbin/shuffle_YOMPlogs 2>&1 | logger -t gs-shuffle-YOMPlogs
    - identifier: shuffle_YOMPlogs
    - user: root
    - hour: '*'
    - minute: '7'
    - require:
      - file: shuffle-YOMPlogs

# Enforce absence of old logrotate conf file now that we're rotating our logs
# ourselves.
scrub-stale-logrotate-file:
  file.absent:
    - name: /etc/logrotate.d/YOMP-logs
