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
import re

def stripHtml(str):
  return re.sub('\.html.*', '', str)

def extractValueByKeyArray(d, keys):
  key = keys[0]
  if len(keys) == 1:
    if key not in d:
      return {}
    return d[key]
  else:
    key = keys.pop(0)
    if key not in d:
      return {}
    return extractValueByKeyArray(d[key], keys)

class MessageManager:
  """Handles extracting values from messages.json in two different ways:
  1. by template path
  2. explicitly by message key
  """

  def __init__(self, messages):
    self.messageString = messages
    self.messageDict = json.loads(messages)


  def getMessagesForTemplate(self, templatePath):
    pathParts = map(stripHtml, templatePath.split('/'))
    return extractValueByKeyArray(self.messageDict, pathParts)


  def getMessagesByKey(self, key):
    pathParts = key.split('.')
    return extractValueByKeyArray(self.messageDict, pathParts)
