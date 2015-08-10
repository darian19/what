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

set -o errexit
set -o nounset
set -o pipefail

export NUMENTA=/opt/numenta
export PATH=${NUMENTA}/anaconda/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin

mkdir -p /etc/YOMP

# If you stop writing to $STAMPFILE, or change the path, you will break
# integration testing. The integration test suite uses the presence of
# $STAMPFILE to tell that the YOMP services have been configured.
STAMPFILE="/etc/YOMP/firstboot-root.run"
export PIP_SCRATCH_D=$(mktemp --directory /tmp/pip_scratch_d.XXXXX)

log_info() {
  echo "$*"
  logger -t firstboot-root -p local0.info "$*"
}

log_error() {
  echo "$*"
  logger -t firstboot-root -p local0.error "$*"
}

die() {
  log_error "$*"
  exit 1
}

if [ -r /etc/YOMP/supervisord.vars ]; then
  log_info "Loading supervisord.vars"
  source /etc/YOMP/supervisord.vars
else
  die "Could not load supervisord.vars"
fi

${YOMP_HOME:?"You must set the YOMP_HOME env var"}

setup_logdirs() {
  # setup logdir if missing
  NUMENTA_LOGS_D=/opt/numenta/nta/eng/logs/numenta-logs-ec2-user
  mkdir -p ${NUMENTA_LOGS_D}
  chown ec2-user:ec2-user ${NUMENTA_LOGS_D}
}

setup_logdirs
wait-until-network-up --tries 300 --delay 1 --pinghost google.com

# Make sure that /etc/motd shows the correct rpm entries
/etc/cron.daily/update-motd

# Everything after this check is run only on the very first boot for
# an instance.
# We only want to run this once, on the first boot
if [ -f ${STAMPFILE} ]; then
  echo "Found ${STAMPFILE}, exiting firstboot-root.sh"
  exit 0
fi

chown -R ec2-user:ec2-user /opt/numenta/products/YOMP

date > ${STAMPFILE}
