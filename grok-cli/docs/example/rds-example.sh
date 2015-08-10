#!/bin/bash
#------------------------------------------------------------------------------
# Copyright 2013-2014 Numenta Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#------------------------------------------------------------------------------

OPTIND=1

AWS_REGION=""
YOMP_SERVER=""
INSTANCES_TO_MONITOR=""

show_credential_usage() {
  echo "You must set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
  echo " before running this example."
  echo
  echo "ex: AWS_SECRET_ACCESS_KEY='foo' AWS_ACCESS_KEY_ID='bar' ./$0"
  echo
  echo "or"
  echo
  echo "export AWS_ACCESS_KEY_ID=YOURACCESSKEY"
  echo "export AWS_SECRET_ACCESS_KEY=YOURSECRETKEY"
  echo "./$0"
  echo
}

show_help() {
  show_credential_usage
  echo "$0 -s https://your.YOMP.server -r AWS_REGION -d RDS_SERVER"
  echo
  echo "If you are working with a running server, add -a API_KEY"
  echo
}

parse_cli(){
  while getopts "ha:d:r:s:" opt; do
    case "$opt" in
      h) show_help
         exit 0
         ;;
      a) YOMP_API_KEY="$OPTARG"
         ;;
      d) RDS_SERVER_LIST="$RDS_SERVER_LIST $OPTARG"
         ;;
      r) AWS_REGION="$OPTARG"
         ;;
      s) YOMP_SERVER="$OPTARG"
         ;;
    esac
  done
}

sanity_check_configuration() {
  if [ -z $AWS_ACCESS_KEY_ID ]; then
    show_credential_usage
    exit 1
  fi
  if [ -z $AWS_SECRET_ACCESS_KEY ]; then
    show_credential_usage
    exit 1
  fi
  if [ "$RDS_SERVER_LIST" == "" ]; then
    echo "You must specify at least one RDS instance with -d"
    show_help
    exit 1
  fi
  if [ "$AWS_REGION" == "" ]; then
    echo "You must specify the AWS region with -r"
    show_help
    exit 1
  fi
  if [ "$YOMP_SERVER" == "" ]; then
    echo "You must specify the YOMP server to configure with -s"
    show_help
    exit 1
  fi
  which YOMP &> /dev/null
  if [ $? != 0 ]; then
    echo 'YOMP needs to be installed and in your $PATH'
    echo
    echo "Have you run python setup.py install or pip install YOMPcli yet?"
    exit 1
  fi
}

set_server_credentials() {
  YOMP credentials ${YOMP_SERVER} \
    --AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
    --AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
    --accept-eula
}

monitor_rds_instances() {
  for instance in ${RDS_SERVER_LIST}
  do
    echo "Monitoring ${instance} RDS instance in ${AWS_REGION}"
    YOMP cloudwatch instances monitor ${YOMP_SERVER} ${YOMP_API_KEY} \
      --namespace='AWS/RDS' \
      --region=${AWS_REGION} \
      --instance=${instance}
  done
}

configure_YOMP_server() {
  if [ -z ${YOMP_API_KEY} ]; then
    echo "Setting server credentials"
    YOMP_API_KEY=$(set_server_credentials)
    echo "Generated YOMP_API_KEY, ${YOMP_API_KEY}"
  else
    echo "Using preset YOMP_API_KEY: ${YOMP_API_KEY}"
  fi
  monitor_rds_instances
}

parse_cli $*
sanity_check_configuration

echo "Configuring ${YOMP_SERVER}..."
configure_YOMP_server
echo
echo "Instances monitored:"
YOMP instances list ${YOMP_SERVER} ${YOMP_API_KEY}
echo
