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
# Formula: nta-nucleus.files

{% for dirpath in ['/etc/numenta',
                   '/usr/local/bin',
                   '/usr/local/sbin'] %}
{{ dirpath }}:
  file.directory:
    - user: root
    - group: root
    - mode: 755
{% endfor %}

/opt/numenta:
  file.directory:
    - user: ec2-user
    - group: ec2-user
    - mode: 755
    - require:
      - user: ec2-user

# Install salt helper scripts
{% for cmd in ['get-minion-id',
               'set-minion-id'] %}
/usr/local/bin/{{ cmd }}:
  file.managed:
    - source: salt://nta-nucleus/files/saltsupport/{{ cmd }}
    - user: root
    - group: root
    - mode: 755
{% endfor %}

# Populate /usr/local/bin
{% for cmd in ['concat-directory',
               'create-random-password',
               'YOMP-with-sshkey',
               'sleep_random'] %}
/usr/local/bin/{{ cmd }}:
  file.managed:
    - source: salt://nta-nucleus/files/{{ cmd }}
    - user: root
    - group: root
    - mode: 755
{% endfor %}

# Populate /usr/local/sbin
{% for cmd in ['publicip',
               'lockrun',
               'wait-until-network-up'] %}
/usr/local/sbin/{{ cmd }}:
  file.managed:
    - source: salt://nta-nucleus/files/{{ cmd }}
    - user: root
    - group: root
    - mode: 755
{% endfor %}
