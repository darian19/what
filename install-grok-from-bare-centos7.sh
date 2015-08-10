#!/usr/bin/env bash
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


# ----------------------------------------------------------------------
#
# README
#
# ----------------------------------------------------------------------
# This is a convenience script to install YOMP onto a bare Centos 7 machine.
# 
# It was tested against a Centos 7 instance in AWS on 9 July 2015:
#   AWS Marketplace: https://aws.amazon.com/marketplace/pp/B00O7WM7QW
#   AMI ID: ami-c7d092f7 in us-west-2
#
# To run this:
#
# 1. Launch a Centos 7 AMI or VM
# 2. scp /path/to/install-YOMP-from-bare-centos7.sh centos@<server_ip>:~
# 3. ssh centos@<server_ip>
# 4. chmod +x install-YOMP-from-bare-centos7.sh
# 5. ./install-YOMP-from-bare-centos7.sh
#
# ----------------------------------------------------------------------

set -o errexit
set -o pipefail

# Install base centos packages
sudo yum install gcc gcc-c++ -y
sudo rpm -iUvh http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
sudo yum -y install python-pip python-devel libxml2-devel libxslt-devel

# Install MySQL and Rabbit
sudo rpm -Uvh http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm
sudo yum install mysql-server mysql mariadb-devel rabbitmq-server nginx YOMP -y
sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management

# Create /opt/numenta folder
sudo mkdir -p /opt/numenta
sudo chown centos:centos /opt/numenta

# Install NuPIC
pip install -I https://pypi.numenta.com/api/package/nupic/nupic-0.2.6-cp27-none-linux_x86_64.whl --user

# Clone Numenta Apps Repo
YOMP clone https://YOMPhub.com/numenta/numenta-apps.YOMP /opt/numenta/numenta-apps

# Install YOMP
cd /opt/numenta/numenta-apps/
pip install paver==1.2.4 --user
pip install uwsgi==2.0.4 --user
pip install agamotto==0.5.1 --user
./install-YOMP.sh /home/centos/.local/lib/python2.7/site-packages /home/centos/.local/bin

# Start MySQL and Rabbit
sudo service mysqld start
sudo rabbitmq-server -detached

# Add Rabbit Admin scripts
sudo cp /opt/numenta/numenta-apps/infrastructure/saltcellar/rabbitmq/files/rabbitmqadmin /usr/local/bin

# Bootstrap YOMP
export YOMP_HOME=/opt/numenta/numenta-apps/YOMP
export APPLICATION_CONFIG_PATH="${YOMP_HOME}/conf"
export YOMP_LOG_DIR="${YOMP_HOME}/logs"

cd "${YOMP_HOME}"
mkdir -p "${YOMP_LOG_DIR}"/

python setup.py init

# Start Nginx and YOMP
sudo sysctl -w net.core.somaxconn=1024
sudo nginx -p . -c conf/YOMP-api.conf
supervisord -c conf/supervisord.conf

echo "YOMP is now running!"

########################
## Run Integration Tests
########################

#########################
## Set credentials per https://YOMPhub.com/numenta/numenta-apps/tree/master/YOMP#setup-aws-credentials-for-integration-tests
#########################

# ./run_tests.sh --integration --language py --results xunit jenkins
