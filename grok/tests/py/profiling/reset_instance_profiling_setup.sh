#!/bin/sh
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

# This script sets up a new YOMP instance for profiling

# Instructions for use:
# ./profiling_setup.sh <MODELNUM>
# where modelnum is the number of models you would like to create (set in quota.conf)

# After this script runs, restart all supervisord services from the webUI.
# Then Copy the api key to the clipboard.
# In the ec2 instance to be sending data, issue a command along the lines of:
# ./YOMP_custom_metric_stress.py --csv ~/OUTPUTFILENAME.csv ec2-12.34.56.78.us-west-2.compute.amazonaws.com HHJTf &
# (Replace HHTJTf with whatever API key this script emitted)

MODELNUM=$1

SUPERVISOR_CONF="/opt/numenta/YOMP/conf/supervisord.conf"

# First, stop supervisord services
supervisorctl -c $SUPERVISOR_CONF stop all

# Kill any already-running capture processes (ie capture_disk_space.py)
ps aux | grep [c]apture_ | awk {'print $2'} | xargs kill

# Delete old logs
# Remember the directory this script was called from (we assume the capture scripts are in the same dir)
pushd /opt/numenta/YOMP/
rm -r logs/*

# Reinitialize everything
python setup.py init

# Set profiling flags in application.conf and model-swapper.conf
sed '5s/false/true/' /opt/numenta/YOMP/conf/application.conf > /opt/numenta/YOMP/conf/application.conf.new
mv /opt/numenta/YOMP/conf/application.conf.new /opt/numenta/YOMP/conf/application.conf
sed '5s/false/true/' /opt/numenta/YOMP/conf/model-swapper.conf > /opt/numenta/YOMP/conf/model-swapper.conf.new
mv /opt/numenta/YOMP/conf/model-swapper.conf.new /opt/numenta/YOMP/conf/model-swapper.conf

# Update the model quota
sed -E "s/= ([0-9]+)/= $MODELNUM/" /opt/numenta/YOMP/conf/quota.conf > /opt/numenta/YOMP/conf/quota.conf.new
mv /opt/numenta/YOMP/conf/quota.conf.new /opt/numenta/YOMP/conf/quota.conf
/opt/numenta/YOMP/bin/update_quota.py

# Reload supervisord's configs
supervisorctl -c $SUPERVISOR_CONF reread
supervisorctl -c $SUPERVISOR_CONF update

# Send USR2 signal to supervisord to cause it to reopen its logs (which we deleted earlier)
ps aux | grep [s]upervisord | awk '{print $2}' | xargs kill -USR2

# Restart supervisord services
supervisorctl -c $SUPERVISOR_CONF restart all

# Go back from whence we came
popd

# Start the capture processes
./capture_disk_space.py > ./capture_disk_space.csv 2> ./capture_disk_space.stderr &
./capture_processes.py > ./capture_processes.csv 2> ./capture_processes.stderr &
./capture_system_summary.py > ./capture_system_summary.csv 2> ./capture_system_summary.stderr &

# Print the api key
echo "API key: "
grep apikey /opt/numenta/YOMP/conf/application.conf
