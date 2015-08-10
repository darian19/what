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
# Formula: mysql.server
#
# Installs the MySQL community repository, then installs MySQL 5.6.23

include:
  - mysql.client
  - mysql.repositories

{% if grains['os_family'] == 'RedHat' %}

# Add our changes to my.cnf for 5.6
configure-mysql-slow-query-log:
  file.append:
    - name: /etc/my.cnf
    - text:
      - "#"
      - "# Apply slow query settings per TAUR-559"
      - "slow_query_log = 1"
      - "slow_query_log_file = /var/log/mysql/slow.log"
    - require:
      - pkg: mysql-community-server
    - watch_in:
      - service: mysqld.service

install-mysqld:
  pkg.latest:
    - name: mysql-community-server
    - require:
      - pkg: install-mysql-client

mysqld.service:
  service.running:
    - enable: true
  {% if grains['osmajorrelease'][0] == '6' %}
    - name: mysqld
  {% elif grains['osmajorrelease'][0] == '7' %}
    - name: mysqld.service
  {% endif %}

{% endif %}

# Add agamotto tests
local-mysqld-agamotto-tests:
  file.managed:
    - name: /etc/numenta/tests/test_local_mysqld.py
    - source: salt://mysql/files/tests/test_local_mysqld.py
    - mode: 0755
    - require:
      - file: ami-test-directory
