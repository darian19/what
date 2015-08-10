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

import base64



def getDefaultHTTPHeaders(config):
  """
  This returns Basic Aunthentication headers for webservices
  calls.
  config :YOMP.app.config
  """
  headers = {}

  if config.has_section("security"):
    apikey = config.get("security", "apikey")
    headers["Authorization"] = "Basic %s" % base64.b64encode(apikey + ":")

  return headers


def getInvalidHTTPHeaders(invalidApiKey="abcd"):
  """
  This returns Invalid Aunthentication headers for webservices
  calls.
  invalidApiKey : invalid api key defaults to abcd
  """
  headers = {}
  headers["Authorization"] = "Basic %s" % base64.b64encode(invalidApiKey + ":")
  return headers
