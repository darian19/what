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
import YOMP.app
from YOMP.app.webservices import messagemanager


class TestMessageManager(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.messageManager_data  = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      "tests/py/data/app/webservices/message_manager_data.json")))

  def setUp(self):
    self.maxDiff = None

  def testgetMessagesByKey(self):
    messageManager = messagemanager.MessageManager(
        open(os.path.join(YOMP.app.YOMP_HOME,
        'resources/messages/us/messages.json')).read()
    )
    messageOut = messageManager.getMessagesByKey('site')
    self.assertDictEqual(messageOut, self.messageManager_data['site'])


  def testGetMessagesForTemplate(self):
    messageManager = messagemanager.MessageManager(
        open(os.path.join(YOMP.app.YOMP_HOME,
         'resources/messages/us/messages.json')).read()
    )
    messageOut = messageManager.getMessagesForTemplate('pages/terms.html')
    self.assertDictEqual(messageOut, {})


if __name__ == '__main__':
  unittest.main()
