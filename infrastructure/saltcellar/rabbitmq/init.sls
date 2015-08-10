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
# Formula: rabbitmq
#
# Installs rabbitmq server on an instance

# Ensure we have the directories we need with the permissions required.
/etc/rabbitmq:
  file.directory:
    - user: root
    - group: root
    - mode: 0755

# rabbitmqadmin is not included in the CentOS rabbitmq rpms, so install it
# ourselves.
/usr/local/bin/rabbitmqadmin:
  file.managed:
    - source: salt://rabbitmq/files/rabbitmqadmin
    - user: root
    - group: root
    - mode: 0755

# Pulled from https://YOMPhub.com/saltstack-formulas/rabbitmq-formula, which we
# should consider using the entirety of.
rabbitmq_repo:
  pkgrepo.managed:
    - humanname: RabbitMQ Packagecloud Repository
    - baseurl: https://packagecloud.io/rabbitmq/rabbitmq-server/el/6/$basearch
    - gpgcheck: 0
    - enabled: True
    - gpgkey: https://packagecloud.io/gpg.key
    - sslverify: 1
    - sslcacert: /etc/pki/tls/certs/ca-bundle.crt
    - require_in:
      - pkg: rabbitmq-server

rabbitmq-server:
  pkg.installed:
    - name: rabbitmq-server
    - version: 3.5.3-1
  service.running:
    - enable: true
    - require:
      - pkgrepo: rabbitmq_repo
      - file: /etc/rabbitmq
      - pkg: rabbitmq-server

# Add Taurus user via cmd.run until https://YOMPhub.com/saltstack/salt/issues/25683
# is resolved
rabbitmq_user_taurus_create:
  cmd.run:
    - name: rabbitmqctl add_user taurus taurus
    - unless: rabbitmqctl list_users | grep taurus
    - require:
      - service: rabbitmq-server

rabbitmq_user_taurus_tag:
  cmd.run:
    - name: rabbitmqctl set_user_tags taurus administrator
    - watch:
      - cmd: rabbitmq_user_taurus_create

rabbitmq_user_taurus_permissions:
  cmd.run:
    - name: rabbitmqctl set_permissions -p / taurus ".*" ".*" ".*"
    - watch:
      - cmd: rabbitmq_user_taurus_tag

enable-rabbitmq-management:
  cmd.run:
    - name: /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management
    - require:
      - service: rabbitmq-server
    - unless: grep rabbitmq_management /etc/rabbitmq/enabled_plugins
    - watch_in:
      - cmd: restart-rabbit-service

restart-rabbit-service:
  cmd.wait:
    - name: service rabbitmq-server restart
    - require:
      - pkg: rabbitmq-server
      - service: rabbitmq-server
