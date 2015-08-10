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
# Formula: rabbitmq.YOMP
#
# Installs YOMP-specific rabbitmq configuration changes

# And our log dir
rabbitmq-log-directory:
  file.directory:
    - name: /opt/numenta/logs/rabbitmq
    - user: root
    - group: root
    - mode: 0777
    - require:
      - file: numenta-log-directory

/etc/rabbitmq/rabbitmq-env.conf:
  file.managed:
    - source: salt://rabbitmq/files/rabbitmq-env.YOMP.conf
    - user: root
    - group: root
    - mode: 0644
    - require_in:
      - service: rabbitmq-server
