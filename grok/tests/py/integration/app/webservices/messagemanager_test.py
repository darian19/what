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
"""
Tests MessageManager
"""
import json
import os
import unittest
import YOMP.app
from YOMP.app.webservices import messagemanager



class MessageManagerTest(unittest.TestCase):
  """
  Tests for extracting values from messages.json in two different ways:
  1. by template path
  2. explicitly by message key
  """


  def setUp(self):
    self.maxDiff = None


  def testgetMessagesByKey(self):
    """
     Test extracting values explicitly by message key
    """
    messageManager = messagemanager.MessageManager(
        open(os.path.join(YOMP.app.YOMP_HOME,
          'resources/messages/us/messages.json')).read()
    )
    messageOut = messageManager.getMessagesByKey('site')
    messages = json.load(open(os.path.join(YOMP.app.YOMP_HOME,
      'resources/messages/us/messages.json')))
    self.assertDictEqual(messageOut, messages["site"])


  def testGetMessagesForTemplate(self):
    """
     Tests extracting values by template path
    """
    messageManager = messagemanager.MessageManager(
        open(os.path.join(YOMP.app.YOMP_HOME,
          'resources/messages/us/messages.json')).read()
    )
    messageOut = messageManager.getMessagesForTemplate('pages/terms.html')

    self.assertDictEqual(messageOut, {})



if __name__ == '__main__':
  unittest.main()
