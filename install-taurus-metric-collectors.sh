#!/bin/bash
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

# Install taurus.metric_collectors and its dependencies
# ARGS:
# First position arg: installation directory;
#   e.g., Linux: /opt/numenta/anaconda/lib/python2.7/site-packages/
#   e.g., Mac OS X: ~/Library/Python/2.7/lib/python/site-packages/
# Second positional arg: script directory; e.g., /opt/numenta/anaconda/bin/
#   e.g., Linux: /opt/numenta/anaconda/bin/
#   e.g., Mac OS X: ~/Library/Python/2.7/bin/ 

set -o errexit

function install {
  pushd $1
  python setup.py develop --install-dir=$2 --script-dir=$3
  popd
}

install nta.utils $1 $2
install infrastructure $1 $2
install taurus.metric_collectors $1 $2
