#!/usr/bin/env python
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
import json
import os
import unittest

from mock import Mock, patch
from paste.fixture import TestApp

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

import YOMP.app
from YOMP.app.webservices import wufoo_api
from YOMP.test_utils.app.webservices import getDefaultHTTPHeaders



class WufooTest(unittest.TestCase):


  def setUp(self):
    self.headers = getDefaultHTTPHeaders(YOMP.app.config)
    self.app = TestApp(wufoo_api.app.wsgifunc())
    self.instanceData = {"version" : "2010-08-31",
                         "instanceId" : "i-d9e211f6",
                         "billingProducts" : None,
                         "accountId" : "987654321",
                         "kernelId" : "aki-88aa75e1",
                         "ramdiskId" : None,
                         "architecture" : "x86_64",
                         "imageId" : "ami-b56a7fdc",
                         "pendingTime" : "2014-03-20T14:06:46Z",
                         "instanceType" : "m1.medium",
                         "region" : "us-east-1",
                         "devpayProductCodes" : None,
                         "privateIp" : "10.122.242.151",
                         "availabilityZone" : "us-east-1d"}
    self.postData = data = {"name": "User Schmoozer",
                            "company": "Numenta, inc.",
                            "edition": "Standard",
                            "version": YOMP.__version__.__version__,
                            "build": "0",
                            "email": "uschmoozer@numenta.com"}


  @ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                        YOMP.app.config.baseConfigDir,
                        (("usertrack", "YOMP_id", "f2fec4a62c76418799e3907f1360e9b7"),))
  @patch("YOMP.app.webservices.wufoo_api.log")
  @patch("YOMP.app.webservices.wufoo_api.requests")
  @patch("YOMP.app.webservices.wufoo_api.instance_utils")
  @patch("YOMP.app.webservices.wufoo_api.sendWelcomeEmail")
  def testWufooHandlerLogsPOSTedData(self, sendWelcomeEmailMock,
                                     instance_utilsMock, requestsMock,
                                     logMock):
    """ Wufoo Handler logs POSTed data """

    instance_utilsMock.getInstanceData = Mock(return_value=self.instanceData)

    response = self.app.post("",
                             json.dumps(self.postData),
                             headers=self.headers)

    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} instanceId=i-d9e211f6"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} company=Numenta, inc."),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} edition=Standard"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} instanceType=m1.medium"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} accountId=987654321"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} name=User Schmoozer"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} region=us-east-1"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} version=%s" % YOMP.__version__.__version__),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} uniqueServerId=f2fec4a62c76418799e3907f1360e9b7"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} email=uschmoozer@numenta.com"),
    logMock.info.assert_any_call("{TAG:WUFOO.CUST.REG} build=0")

    sendWelcomeEmailMock.assert_called_once_with("uschmoozer@numenta.com")


  @ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                        YOMP.app.config.baseConfigDir,
                        (("usertrack", "send_to_wufoo", "no"),))
  @patch("YOMP.app.webservices.wufoo_api.requests")
  @patch("YOMP.app.webservices.wufoo_api.instance_utils")
  @patch("YOMP.app.webservices.wufoo_api.sendWelcomeEmail")
  def testWufooConfigFlagDisabled(self, sendWelcomeEmailMock,
                                  instance_utilsMock, requestsMock):
    """ Assert that wufoo handler honors send_to_wufoo configuration directive
    in the disabled case
    """
    response = self.app.post("",
                             json.dumps(self.postData),
                             headers=self.headers)
    self.assertFalse(requestsMock.post.called)


  @ConfigAttributePatch(YOMP.app.config.CONFIG_NAME,
                        YOMP.app.config.baseConfigDir,
                        (("usertrack", "send_to_wufoo", "yes"),))
  @patch("YOMP.app.webservices.wufoo_api.requests")
  @patch("YOMP.app.webservices.wufoo_api.instance_utils")
  @patch("YOMP.app.webservices.wufoo_api.sendWelcomeEmail")
  def testWufooConfigFlagEnabled(self, sendWelcomeEmailMock,
                                 instance_utilsMock, requestsMock):
    """ Assert that wufoo handler honors send_to_wufoo configuration directive
    in the enabled case
    """
    response = self.app.post("",
                             json.dumps(self.postData),
                             headers=self.headers)
    self.assertTrue(requestsMock.post.called)



if __name__ == "__main__":
  unittest.main()
