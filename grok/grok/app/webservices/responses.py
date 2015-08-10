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
from web import BadRequest, HTTPError, NoMethod

from utils import encodeJson
from YOMP.app.exceptions import QuotaError


class UnauthorizedResponse(BadRequest):
  """`400 Bad Request` error."""
  # Should be 401, but Browser auto-401 dialog is a bad user experience
  # Note: The Unauthorized exception provided by web.py is not json-compatible
  message = {
    "result":"unauthorized"
  }
  def __init__(self, message=None):
    status = "400 Bad Request"
    headers = {
      "Content-Type": "application/json; charset=UTF-8"
    }
    HTTPError.__init__(self, status, headers, encodeJson(message or self.message))


class InvalidRequestResponse(BadRequest):
  """`400 Bad Request` error."""
  # Should be 401, but Browser auto-401 dialog is a bad user experience
  # Note: The Unauthorized exception provided by web.py is not json-compatible
  message = {
    "result":"Invalid"
  }
  def __init__(self, message=None):
    status = "400 Bad Request"
    headers = {
      "Content-Type": "application/json; charset=UTF-8"
    }
    HTTPError.__init__(self, status, headers, encodeJson(message or self.message))


class QuotaErrorResponse(HTTPError):
  """`403 Forbidden` error."""
  # Note: The Unauthorized exception provided by web.py is not json-compatible
  message = {
    "result":"Instance quota reached"
  }
  def __init__(self, message=None):
    status = "403 Forbidden"
    headers = {
      "Content-Type": "application/json; charset=UTF-8"
    }
    HTTPError.__init__(self, status, headers, encodeJson(message or self.message))


class NotAllowedResponse(NoMethod):
  """`405 Method Not Allowed` error."""
  message = {
    "result": "Not allowed."
  }
  def __init__(self, message=None):
    status = "405 Method Not Allowed"
    headers = {
      "Content-Type": "application/json; charset=UTF-8"
    }
    HTTPError.__init__(self, status, headers, encodeJson(message or self.message))


def quotaErrorResponseWrapper(func):
  """ Response wrapper to ensure that if a QuotaError exception is raised,
  then a proper 403 Forbidden response is returned.
  """
  def _(*args, **kwargs):
    try:
      response = func(*args, **kwargs)
      return response
    except QuotaError as e:
      raise QuotaErrorResponse({"result":str(e)})
  return _
