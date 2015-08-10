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
# Formula: devtools
#
# Install developer tools repository and updated developer tools

# Install devtool repo - v2
install-devtools-repo:
  file.managed:
    - user: root
    - group: root
    - source: salt://devtools/files/devtools-2.repo
    - name: /etc/yum.repos.d/devtools-2.repo
    - mode: 644
    - watch_in:
      - cmd: reload-yum-database

# Ensure we don't have both devtools-1.1 and devtools-2 repo files at the
# same time on a machine
remove-stale-devtools-repo:
  file.absent:
    - name: /etc/yum.repos.d/devtools-1.1.repo
    - watch_in:
      - cmd: reload-yum-database

# Install devtools
compiler-toolchain:
  pkg:
    - require:
      - file: install-devtools-repo
      - file: remove-stale-devtools-repo
    - latest
    - pkgs:
      - cmake
      - devtoolset-2-binutils
      - devtoolset-2-gcc
      - devtoolset-2-gcc-c++
      - libjpeg-turbo-devel
      - libX11-devel
      - libXt-devel
      - rpm-build

# Add devtools to path for all users using our standard dotfiles
/etc/.sh_fragments.d/00-add-devtools-to-path.sh:
  file.managed:
    - source: salt://devtools/files/00-add-devtools-to-path.sh
    - mode: 644
    - user: ec2-user
    - group: ec2-user

# Add mysql development tools

# First, client tools. If they need a server, they should include mysql.server
# in their machine role, or use an RDS instance for anything long-lived.
include:
  - mysql.client
  - nta-yum

# And development tools
mysql-development-tools:
  pkg.latest:
    - name: mysql-community-devel
    - require:
      - cmd: mysql-community-repository
