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
# Formula: mysql.repositories
#
# Installs the MySQL community repositories

{% if grains['os_family'] == 'RedHat' %}

# Install the mysql community repository for CentOS
mysql-community-repository:
  cmd.run:
    - creates: /etc/yum.repos.d/mysql-community-source.repo
  {% if grains['osmajorrelease'][0] == '6' %}
    - name: yum install -y http://repo.mysql.com/mysql-community-release-el6-5.noarch.rpm
  {% elif grains['osmajorrelease'][0] == '7' %}
    - name: yum install -y http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm
  {% endif %}
    - watch_in:
      - cmd: reload-yum-database

{% endif %}
