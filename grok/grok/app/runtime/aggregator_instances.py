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
Aggregator Instance utilitities.

NOTE: The first phase supports only AWS/EC2 Instances.
"""

from collections import namedtuple
import dateutil.parser
import re

from boto import ec2

from .aggregator_utils import getAWSCredentials

from YOMP import YOMP_logging

_MODULE_NAME = "YOMP.aggregator_instances"



def _getLogger():
  return YOMP_logging.getExtendedLogger(_MODULE_NAME)



# Information about an AWS EC2 Instance
# instanceID: EC2 ID of the Instsance; string; e.g., "i-ab15a19d"
# regionName: AWS region name; string; e.g., "us-west-2"
# state: EC2 Instance state; string; e.g., "running"
# stateCode: EC2 Instance state code; number; e.g., 80
# instanceType: EC2 Instance type; string; e.g., "m1.medium"
# launchTime: UTC launch time of the instance; datetime.datetime
# tags: EC2 Instance tags; dict; e.g.,
#   {"Type":"Jenkins", "Name":"jenkins-master"})
InstanceInfo = namedtuple(
  "InstanceInfo",
  "instanceID regionName state stateCode instanceType "
  "launchTime tags")



class EC2InstanceTagMatcher(object):

  _SPECIAL_RE_CHARACTERS_TO_ESCAPE = (
    ".^$+{}[]|()")

  def __init__(self):
    # Cache of compiled patterns
    self._compiledPatterns = dict()


  @classmethod
  def _convertAWSPatternToRE(cls, awsPattern):
    """ Convert an AWS tag filter pattern into a python regular experssion
    pattern

    :param awsPattern: AWS pattern match string that may include the following
                       special characters:
                        '?': match any single char
                        "*": match any zero or more characters
                        "\": escapes "?*\"
    """
    resultPattern = []
    wasEscaped = False
    for c in awsPattern:
      if wasEscaped:
        if c not in "\\?*":
          raise ValueError("Unexpected escaping of %r in AWS pattern %r" %
                           (c, awsPattern,))
        resultPattern.append(c)
        wasEscaped = False
        continue

      elif c == "\\":
        wasEscaped = True
        resultPattern.append(c)

      elif c == "?":
        # Translate AWS's "?" metacharacater into the corresponding regex char
        resultPattern.append(".")

      elif c == "*":
        resultPattern.extend(("(", ".", "*", ")"))

      elif c in cls._SPECIAL_RE_CHARACTERS_TO_ESCAPE:
        # The character is not one of the AWS wildcard metacharacters and also
        # not a numeric diYOMP (re.compile raises bogus escape error when
        # numeric diYOMPs are escaped)
        resultPattern.extend(("\\", c))

      else:
        resultPattern.append(c)

    if wasEscaped:
      raise ValueError("Dangling escape in AWS pattern %r" % (awsPattern,))

    return "".join(resultPattern)



  def match(self, tags, tagFilter):
    """ Return True if one of the tags matches tagFilter

    :param tags: a dictionary of an instance's tags, where each key is a tag's
                 name and the correpsonding value is the the tag's value
    :param tagFilter: a two-tuple of tag name and AWS compatible value pattern
                      possibly containing "*" and "?" wildcard metacharacters
    :return: True if one of the tags matches tagFilter
    """
    key, valuePattern = tagFilter

    tagValue = tags.get(key, None)
    if tagValue is None:
      return False

    patternObj = self._compiledPatterns.get(valuePattern, None)
    if patternObj is None:
      pattern = self._convertAWSPatternToRE(valuePattern)

      # Compile and cache the pattern object
      # NOTE: use re.DOTALL to have "." match any single char, including newline
      patternObj = self._compiledPatterns[valuePattern] = re.compile(
        pattern, flags=re.DOTALL)

    match = patternObj.match(tagValue)
    return (match is not None and
            match.start() == 0 and
            match.end() == len(tagValue))



def getAutostackInstances(regionName, filters):
  """ Query AWS for instances that belong to an Autostack

  :param regionName: The name of the AWS region

  :param filters: One or more filters. Each filter consists of a filter name and
      one or more values for that filter; the instances matched by a single
      filter are the union of instances that match any of the filter's values.
      When multiple filters are used, they return instances that match all the
      spedified filters (intersection).
  :type filters: a dict; the each key is a filter name ("tag:" + tag-name) and
      the corresponding value is a sequence of one or more filter values. E.g.,
      {"tag:Name":["*test*", "*YOMP*"], "tag:Description":["Blah", "foo"]}

  :returns: a sequence of zero or more InstanceInfo objects matching the given
      filters in the given region
  """
  log = _getLogger()

  if not filters:
    raise ValueError("filters must be non-empty, but got: %r" % (filters,))

  log.debug("Requesting reservations from region=%s with filters=%s",
            regionName, filters)

  ec2Conn = ec2.connect_to_region(region_name=regionName,
                                  **getAWSCredentials())

  return tuple(
    InstanceInfo(
      instanceID=instance.id,
      regionName=regionName,
      state=instance.state,
      stateCode=instance.state_code,
      instanceType=instance.instance_type,
      launchTime=dateutil.parser.parse(instance.launch_time),
      tags=instance.tags)
    for reservation in ec2Conn.get_all_reservations(filters=filters)
    for instance in reservation.instances)
