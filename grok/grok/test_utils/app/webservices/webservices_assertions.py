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
Various utility assertions used by webservices tests
"""

import json
import types

from htmengine import utils as app_utils



#Update RESPONSE_STATUS_MAP for supporting various status
RESPONSE_STATUS_MAP = {
  200 : "200 OK",
  201 : "201 Created",
  400 : "400 Bad Request",
  403 : "403 Forbidden",
  404 : "404 Not Found",
  405 : "405 Method Not Allowed",
  500 : "500 Internal Server Error"
}


def assertResponseStatusCode(test, response, code):
  """
  Asserts response code and full status.
  Update RESPONSE_STATUS_MAP for supporting various status

  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  code : This Integer should be expected response code.
    This will be used for asseting response code and response full status
  """
  test.assertEqual(response.status, code)
  test.assertEqual(response.full_status, RESPONSE_STATUS_MAP[code])


def assertResponseHeaders(test, response, headerType="json"):
  """
  Asserts response headers for API call, currently looking for Content-Type
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  headerType : Expects string . Currently supporting header type for json and
    html. Update this utility for supporting other headers if needs.
    Defauls to json as with majority we are returning json
    data(also backward compatibity with integration tests that are in prodction)
  """
  headers = dict(response.headers)
  if headerType == "json":
    test.assertEqual(headers["Content-Type"], "application/json; charset=UTF-8")
  elif headerType == "html":
    test.assertEqual(headers["Content-Type"], "text/html")
  else:
    test.fail("Unexpected headerType=%r" % (headerType,))


def assertResponseBody(test, response):
  """
  Asserts response body for API call
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  test.assertIsInstance(response.body, types.StringTypes)
  headers = dict(response.headers)
  if headers["Content-Type"] == "application/json; charset=UTF-8":
    json.loads(response.body)


def assertSuccess(test, response, code=200):
  """
  Asserts response for API call, for 200 OK,
  This is wrapper for asserting happy path testcases
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  code :Defautls to 200, this is the expected response code.This will
    be used for asserting response code and response full status
  """
  assertResponseHeaders(test, response, headerType="json")
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code)


def assertNotFound(test, response, headerType="html"):
  """
  Asserts response for API call, for 404 Not Found
  This is wrapper which is useful to assert Not Found scenario across APIs
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response, headerType)
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code=404)


def assertBadRequest(test, response, headerType="html"):
  """
  Asserts response for API call, for 400 Bad Request
  This is wrapper which is useful to assert Bad Request scenario across APIs
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  headerType : Optional, will default to html but can be manually overridden as "json"
    if this is what file type we expect.
  """
  assertResponseHeaders(test, response, headerType)
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code=400)


def assertDeleteSuccessResponse(test, response):
  """
  This method wraps all assertions for any successful Delete call
  This could be used for model, instances etc
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertSuccess(test, response)
  result = app_utils.jsonDecode(response.body)
  test.assertIsInstance(result, dict)
  test.assertEqual(result, {"result": "success"})


def assertForbiddenResponse(test, response):
  """
  This method wraps all assertions for 403 Forbidden
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response, headerType="json")
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code=403)


def assertInvalidAuthenticationResponse(test, response):
  """
  This method wraps all assertions for Authentication.
  Currently we are returning "400 Bad Request" instead of "401 Unauthorized"
  as a design decision
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response)
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code=400)
  result = app_utils.jsonDecode(response.body)
  test.assertIsInstance(result, dict)
  test.assertEqual(result, {"result": "Invalid API Key"})


def assertMethodNotAllowed(test, response):
  """
  This method wraps all assertions 405 Method Not Allowed
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response, headerType="html")
  assertResponseBody(test, response)
  assertResponseStatusCode(test, response, code=405)


def assertRouteNotFound(test, response):
  """
  This method wraps all assertions for scenarop when invalid route is invoked
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertNotFound(test, response)
  test.assertIn("not found", response.body)


def assertInternalServerError(test, response):
  """
  This method wraps all assertions 500 internal server error
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response, headerType="html")
  assertResponseStatusCode(test, response, code=500)


def assertObjectNotFoundError(test, response):
  """
  This method wraps all assertions 404 ObjectNotFoundError
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  """
  assertResponseHeaders(test, response, headerType="html")
  assertResponseStatusCode(test, response, code=404)
  test.assertIn("ObjectNotFoundError", response.body)


def assertInvalidArgumentsError(test, response, headerType="html"):
  """
  This method wraps all assertions 500 InvalidArgumentsError()
  test : This parameter expects handle for current testcase under execution.
    This is used for further assertions
  response : response received from YOMP webservice call
  headerType : Optional, will default to html but can be manually overridden as "json"
    if this is what file type we expect.
  """
  assertResponseHeaders(test, response, headerType)
  assertResponseStatusCode(test, response, code=400)
  test.assertIn("InvalidArgumentsError()", response.body)
