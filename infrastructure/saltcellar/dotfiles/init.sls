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
# Formula: dotfiles

# Installs any necessary dotfiles for ec2-user and root.
# Currently we customize .bash_profile and .zshrc

# Install shell configuration files into /etc/skel. New accounts home
# directories are created by copying /etc/skel.

etc-skel-shell-fragments-directory:
  file.directory:
    - name: /etc/skel/.sh_fragments.d
    - mode: 700
    - user: root
    - group: root

# Files in /etc/skel get copied to the home directory of newly created users

# Set standard .bashrc
/etc/skel/.bashrc:
  file.managed:
    - source: salt://dotfiles/files/bashrc_skeleton.sh
    - mode: 644

# Set standard .bash_profile
/etc/skel/.bash_profile:
  file.managed:
    - source: salt://dotfiles/files/bash_profile_skeleton.sh
    - mode: 644

# Set standard .zshrc
/etc/skel/.zshrc:
  file.managed:
    - source: salt://dotfiles/files/zshrc_skeleton.zsh
    - mode: 644

# Set up global .sh_fragments.d. Files here will be sourced every login
# by all users with our standard shell init files. This makes it easier
# for other formulas to do things like PYTHONPATH or PATH manipulations
# without having one kitchen-sink dotfile. See devtools for an example.
global-shell-fragments-directory:
  file.directory:
    - name: /etc/.sh_fragments.d
    - mode: 755
    - user: root
    - group: root

global-bashrc-fragments-directory:
  file.directory:
    - name: /etc/bashrc.d
    - mode: 755
    - user: root
    - group: root

# Now, do account-specific shell setup. Enforce that we're using our standard
# files and not the stock CentOS ones, since the accounts may have been
# created before Salt was installed, let alone had a chance to update the
# contents of /etc/skel.

# For root
/root/.sh_fragments.d:
  file.directory:
    - mode: 700
    - user: root
    - group: root

/root/.bashrc:
  file.managed:
    - source: salt://dotfiles/files/bashrc_skeleton.sh
    - mode: 644
    - user: root
    - group: root

/root/.bash_profile:
  file.managed:
    - source: salt://dotfiles/files/bash_profile_skeleton.sh
    - mode: 644
    - user: root
    - group: root

/root/.zshrc:
  file.managed:
    - source: salt://dotfiles/files/zshrc_skeleton.zsh
    - mode: 644
    - user: root
    - group: root

# For ec2-user
/home/ec2-user/.sh_fragments.d:
  file.directory:
    - mode: 700
    - user: ec2-user
    - group: ec2-user

/home/ec2-user/.bashrc:
  file.managed:
    - source: salt://dotfiles/files/bashrc_skeleton.sh
    - mode: 644
    - user: ec2-user
    - group: ec2-user

/home/ec2-user/.bash_profile:
  file.managed:
    - source: salt://dotfiles/files/bash_profile_skeleton.sh
    - mode: 644
    - user: ec2-user
    - group: ec2-user

/home/ec2-user/.zshrc:
  file.managed:
    - source: salt://dotfiles/files/zshrc_skeleton.zsh
    - mode: 644
    - user: ec2-user
    - group: ec2-user
