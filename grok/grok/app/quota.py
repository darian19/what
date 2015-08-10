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
This module is responsible for establishing the fencing quota of the system
based on the running YOMP Edition (always 'Standard' in 1.5 and beyond)
and the resources of the host machine (e.g., m1.medium vs m1.large)
"""

import os.path
import sys

import boto.utils

from YOMP import YOMP_logging
from YOMP.app import YOMP_HOME, product, repository
from YOMP.app.exceptions import QuotaError

from nta.utils.config import Config



def _getLogger():
  return YOMP_logging.getExtendedLogger("YOMP.app.quota")



class QuotaConfig(Config):
  """ Quota layer's configuration parser.
  """


  CONFIG_NAME = "quota.conf"


  def __init__(self, *args, **kwargs):
    super(QuotaConfig, self).__init__(self.CONFIG_NAME,
                                      os.path.join(YOMP_HOME, "conf"),
                                      *args, **kwargs)



class Quota(object):
  """ Interface for managing of the system's quota """


  _cachedInstanceQuota = None
  """ Cached instance quota (# of instances allowed) """


  @classmethod
  def init(cls):
    """ Determine the quota and save it in the "quota" config. NOTE: this
    should be called once *before* starting YOMP services.
    """
    editionType = product.get("edition", "type")

    quotaConfig = QuotaConfig()

    if editionType == "free":
      print ("As of YOMP 1.5, the 'free' edition is no longer supported; "
        "using standard edition quotas instead")
      _getLogger().warn("Called updateQuota on a 'free' edition")

    hostInfo = cls._getHostInfo()
    option = "%s.%s.%s" % (editionType,
                           hostInfo["infrastructureType"],
                           hostInfo["instanceType"],)

    instanceQuota = quotaConfig.getint("instance_quota_table", option)

    overrideConfig = QuotaConfig(mode=QuotaConfig.MODE_OVERRIDE_ONLY)
    if not overrideConfig.has_section("actual"):
      overrideConfig.add_section("actual")
    overrideConfig.set("actual", "instance_quota", str(instanceQuota))
    overrideConfig.save()

    _getLogger().info("Initialized instance quota; edition=%s; "
                      "instanceQuota=%s", editionType, instanceQuota)


  @classmethod
  def getInstanceQuota(cls):
    """
    retval: max number of active instances that may be monitored by this YOMP
      product installation
    """
    if cls._cachedInstanceQuota is None:
      cls._cachedInstanceQuota = QuotaConfig().getint("actual",
                                                      "instance_quota")

    # We assume that Quota.init() is executed before YOMP services are started
    assert cls._cachedInstanceQuota > 0, (
      "Non-positive actual instance_quota=%s. Quota.init() not executed before "
      "YOMP services?") % (cls._cachedInstanceQuota,)

    return cls._cachedInstanceQuota


  @classmethod
  def _getHostInfo(cls):
    if sys.platform.startswith("darwin"):
      infrastructureType = "dev"
      instanceType = "dev"
    else:
      # NOTE: assumes AWS/EC2 YOMP host instance
      # TODO: File issue to have boot prepare a conf file with infrastructure
      #   type, instance type, etc. that this code can use
      infrastructureType = "ec2"
      instanceMetadata = boto.utils.get_instance_metadata()
      instanceType = instanceMetadata["instance-type"]


    return {
      "infrastructureType": infrastructureType,
      "instanceType": instanceType
    }


def checkQuotaForInstanceAndRaise(conn, instanceName):
  """ Perform instance quota check and raise QuotaError exception if request to
  create a model for `instanceName` would result in a new "instance" being
  created beyond quota.

  This function answers the question:

    Is there room to add a new model for a new, or existing instance?

  And raises an exception if the answer is no.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param instanceName: Instance name
  :type instanceName str:

  :raises: YOMP.app.exceptions.QuotaError
  """
  instanceCount = repository.getInstanceCount(conn)
  instanceQuota = Quota.getInstanceQuota()

  if instanceCount >= instanceQuota:
    if not repository.listMetricIDsForInstance(conn, instanceName):
      raise QuotaError(
        "Server limit exceeded; edition=%s; count=%i; limit=%i." % (
          product.get("edition", "type").title(), instanceCount,
          instanceQuota))


def checkQuotaForCustomMetricAndRaise(conn):
  """ Perform instance quota check and raise QuotaError exception if request to
  create a model for custom metric would result in a new "instance" being
  created beyond quota.

  This function answers the question:

    Is there room to add a new custom metric?

  And raises an exception if the answer is no.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection

  :raises: YOMP.app.exceptions.QuotaError
  """
  instanceCount = repository.getInstanceCount(conn)
  instanceQuota = Quota.getInstanceQuota()

  if instanceCount >= instanceQuota:
    raise QuotaError(
      "Server limit exceeded; edition=%s; count=%i; limit=%i." % (
        product.get("edition", "type").title(), instanceCount, instanceQuota))
