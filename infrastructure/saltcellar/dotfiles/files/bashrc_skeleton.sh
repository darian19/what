# .bash_profile
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

# Numenta's standard .bashrc

# Source global definitions
if [ -f /etc/bashrc ]; then
  . /etc/bashrc
fi

# Source any files in the global bashrc fragments directory. This allows
# roles to override the values in the default .bashrc, while still permitting
# multiple roles to add overrides. Loading fragments lets us have a clean
# .bashrc instead of one with hacks for roles that aren't installed on the
# machine.
#
# Check that there are fragment files first, otherwise we'll get a complaint
# about $dotfile not existing when we try to source it
if [ -n "$(ls /etc/bashrc.d)" ]; then
  for dotfile in /etc/bashrc.d/*
  do
    if [ -r "${dotfile}" ]; then
      source "${dotfile}"
    fi
  done
fi
# Now that we're done with dotfile, clean up our namespace
unset dotfile
