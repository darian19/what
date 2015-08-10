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
# Formula: nta-yum

# Install our standard yum repositories & yum-housekeeping support script

{% if grains['os_family'] == 'RedHat' %}
# Cope for both C6 and C7
{% if grains['osmajorrelease'][0] == '6' %}

# On CentOS 6, we need to make sure we have the latest ca-certificates package
# or installing the epel repo will make yum start choking with SSL errors.
update-ca-certificates:
  pkg.latest:
    - name: ca-certificates

# On CentOS 6, we have to install EPEL from a URL
install-epel-repo:
  cmd.run:
    - name: yum install -y http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
    - creates: /etc/yum.repos.d/epel.repo
    - require:
      - pkg: update-ca-certificates
    - watch_in:
      - cmd: reload-yum-database
      - cmd: epel-installed

{% elif grains['osmajorrelease'][0] == '7' %}
# CentOS 7 supports installing EPEL directly via yum!
install-epel-repo:
  cmd.run:
    - name: yum install -y epel-release
    - creates: /etc/yum.repos.d/epel.repo
    - watch_in:
      - cmd: reload-yum-database
      - cmd: epel-installed

{% endif %}

# Enable S3 repos
{% for repo in ['nta-carbonite.repo',
                'nta-thirdparty.repo'] %}
/etc/yum.repos.d/{{ repo }}:
  file.managed:
    - user: root
    - group: root
    - source: salt://nta-yum/files/{{ repo }}
    - mode: 644
    - require:
      - file: remove-stale-YOMP-repo
    - watch_in:
      - cmd: epel-installed
      - cmd: reload-yum-database
{% endfor %}

# Purge the old YOMP.repo file
remove-stale-YOMP-repo:
  file.absent:
    - name: /etc/yum.repos.d/YOMP.repo
    - watch_in:
      - cmd: reload-yum-database

# We install EPEL two different ways, based on whether we're on CentOS 6
# or CentOS 7. Here's a hack to allow other states to detect that EPEL is
# enabled either way - they can require/watch cmd: epel-installed

epel-installed:
  cmd.wait:
    - name: touch /etc/numenta/epel-installed
    - creates: /etc/numenta/epel-installed

reload-yum-database:
  cmd.wait:
    - name: yum clean all
    - watch_in:
      - cmd: rebuild-yum-cache

rebuild-yum-cache:
  cmd.wait:
    - name: yum makecache

# Do yum housekeeping on boot.
/etc/init.d/yum-housekeeping:
  file.managed:
    - source: salt://nta-yum/files/yum-housekeeping.initd
    - mode: 755
    - require:
      - file: remove-stale-yum-housekeeping-script

remove-stale-yum-housekeeping-script:
  file.absent:
    - name: /etc/init.d/yumhousekeeping

yum-housekeeping:
  service.enabled

{% endif %}
