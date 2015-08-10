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

# Read an instance's AWS role credentials from Amazon's API.
#
# Source this from any shell scripts on the box that need access to the
# instance's role credentials

read_iam_role_credentials_or_die(){
  local IAM_ENDPOINT="http://169.254.169.254/latest/meta-data/iam"

  local security_profile=$(curl -s ${IAM_ENDPOINT}/security-credentials/)

  local count=$(echo "${security_profile}" | grep -c "<h1>404 - Not Found</h1>")

  if [ "$(echo ${security_profile} | grep -c '<h1>404 - Not Found</h1>')" -gt 0 ]; then
    echo "This machine does not have an IAM role"
    exit 1
  fi

  local PROFILE_URL="${IAM_ENDPOINT}/security-credentials/${security_profile}"
  export AWS_ACCESS_KEY_ID=$(curl -s "${PROFILE_URL}" | \
                               grep AccessKeyId | \
                               cut -d":" -f2 | \
                               sed 's/[^0-9A-Z]*//g')

  export AWS_SECRET_ACCESS_KEY=$(curl -s "${PROFILE_URL}" | \
                                   grep SecretAccessKey | \
                                   cut -d":" -f2 | \
                                   sed 's/[^0-9A-Za-z/+=]*//g')
}
