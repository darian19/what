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
# Formula: nta-nucleus
#
# Install the standard set of base files, packages and services for a
# numenta server.

# Add users/groups before files & directories so we can safely chown to them
ec2-user:
  user.present:
    - uid: 500
    - gid: 500
    - home: /home/ec2-user
    - shell: /bin/bash
  group.present:
    - gid: 500
    - members:
      - ec2-user

wheel:
  group.present:
    - gid: 10
    - members:
      - ec2-user

# Load the support formulas we need, and the various nta-nucleus.* formulas
include:
  - nta-yum
  - aws-support
  - numenta-python
  - agamotto
  - motd
  - logrotate
  - sudoers-setup
  - nta-nucleus.packages
  - nta-nucleus.files
  - nta-nucleus.services
  - nta-nucleus.security
  - nta-nucleus.settings
  - nta-nucleus.test-support
  - dotfiles
