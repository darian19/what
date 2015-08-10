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
# Formula: YOMP-plumbing.yumrepos
#
# YOMP and NuPIC are installed via RPMs from our internal yum repositories.
# Ensure they're installed on the AMI.

# Enable YOMP-specific S3 repos
{% for repo in ['YOMP-release-candidates.repo',
                'YOMP-development.repo',
                'YOMP-releases.repo'] %}
/etc/yum.repos.d/{{ repo }}:
  file.managed:
    - user: root
    - group: root
    - source: salt://YOMP-plumbing/files/repos/{{ repo }}
    - mode: 644
    - require:
      - file: remove-stale-YOMP-repo
    - watch_in:
      - cmd: reload-yum-database
{% endfor %}

# Nuke stale repo files.
{% for forbidden in ['YOMP_development.repo',
                     'YOMP_releases.repo'] %}
stale-repo-{{ forbidden }}:
  file.absent:
    - name: /etc/yum.repos.d/{{ forbidden }}
    - watch_in:
      - cmd: reload-yum-database
{% endfor %}
