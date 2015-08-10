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
import sys

import requests



def getInstanceData():
  """Gets metadata about the instance this YOMP server is running on.

  Sample output:

    {
      "version" : "2010-08-31",
      "instanceId" : "i-d9e211f6",
      "billingProducts" : None,
      "accountId" : "783782770022",
      "kernelId" : "aki-88aa75e1",
      "ramdiskId" : None,
      "architecture" : "x86_64",
      "imageId" : "ami-b56a7fdc",
      "pendingTime" : "2014-03-20T14:06:46Z",
      "instanceType" : "m1.medium",
      "region" : "us-east-1",
      "devpayProductCodes" : None,
      "privateIp" : "10.122.242.151",
      "availabilityZone" : "us-east-1d"
    }

  :returns: dict of EC2 instance data; None if not available

  """
  if sys.platform.startswith("darwin"):
    return None

  url = "http://169.254.169.254/latest/dynamic/instance-identity/document"

  try:
    response = requests.get(url=url)
  except requests.exceptions.ConnectionError:
    return None

  if response.status_code != 200:
    return None

  return response.json()
