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

# Note: we don't allow autostacks of Opsworks, so disable warnings about
# `getMatchingResources` not being implemented (disable=W0223 comments below)

from boto.opsworks import layer1

from YOMP.app.adapters.datasource.cloudwatch.aws_base import (
    AWSResourceAdapterBase)
from YOMP.app.adapters.datasource.cloudwatch.aws_base import ResourceTypeNames
from YOMP.app.aws.opsworks_utils import retryOnOpsworksTransientError



@AWSResourceAdapterBase.registerResourceAdapter #pylint: disable=W0223
class OpsWorksAdapter(AWSResourceAdapterBase):
  RESOURCE_TYPE = ResourceTypeNames.OPSWORKS_STACK

  NAMESPACE = "AWS/OpsWorks"

  # Cloudwatch metric dimension combinations supported by all metric adapters on
  # this resource;
  # NOTE: the first dimension name in each group is the dimension that
  # identifies the resource
  DIMENSION_GROUPS = (("StackId",),)


  @retryOnOpsworksTransientError()
  def getResourceName(self):
    """ Query AWS for the name value of the OpsWorks instance

    NOTE: overrides method in base class

    :returns: name value if available or None if not
    :rtype: string or NoneType
    """

    conn = layer1.OpsWorksConnection(**self._getFreshAWSAuthenticationArgs())

    result = conn.describe_stacks([self._dimensions["StackId"]])

    if "Stacks" in result:
      stack = next(iter(result["Stacks"]))
      return stack["Name"]


  @classmethod
  def describeResources(cls, region):
    """Describe available OpsWorks stacks in the given region.

    :param region: AWS region

    :returns: description of available OpsWorks Instances in the given region

    ::

        [
          {   # NOTE: grn = "YOMP resource name"
              "grn": "aws://us-west-2/instance/i-4be0d87f",
              "resID": "i-4be0d87f",
              "name": value-of-name-tag-or-empty-str
          },

          ...
        ]
    """
    instanceType = cls.RESOURCE_TYPE[cls.RESOURCE_TYPE.rfind(":") + 1:]

    @retryOnOpsworksTransientError()
    def getResources():
      conn = layer1.OpsWorksConnection(**cls._getFreshAWSAuthenticationArgs())
      return conn.describe_stacks()

    stacks = getResources()

    stackList = [{"grn": ("aws://%s/%s/%s" %
                          (region, instanceType, stack["StackId"])),
                  "resID": stack["StackId"],
                  "name": stack["Name"]} for stack in stacks["Stacks"]
                 if stack["Region"] == region]
    return stackList


  def _queryCloudWatchMetricStats(self, period, start, end, stats):
    """Override to hard-code us-east-1 region."""
    return super(OpsWorksAdapter, self)._queryCloudWatchMetricStats(
        period, start, end, stats, "us-east-1")



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSCPUIdleMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "cpu_idle"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return "Amount of time the cpu is idle for %s in %s" % (
      self._dimensions["StackId"], self._region)



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSCPUNiceMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "cpu_nice"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of time the cpu is handling process with a positive nice "
            "value for %s in %s" %
            (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSCPUSystemMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "cpu_system"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of time the cpu is handling system operations for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSCPUUserMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "cpu_user"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of time the cpu is handling user operations for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSCPUWaitioMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "cpu_waitio"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of time the cpu is waiting for input/output operations "
            "for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSLoad5MetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "load_5"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("The load averaged over a 5-minute window for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemoryBuffersMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_buffers"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of buffered memory for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemoryCachedMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_cached"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of cached memory for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemoryFreeMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_free"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of free memory for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemorySwapMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_swap"

  IS_INSTANCE_DEFAULT = True

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of swap space for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemoryTotalMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_total"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Total amount of memory for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSMemoryUsedMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "memory_used"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = 100

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Amount of memory in use for %s in %s"
            % (self._dimensions["StackId"], self._region))



@AWSResourceAdapterBase.registerMetricAdapter #pylint: disable=W0223
class OPSProcsMetricAdapter(OpsWorksAdapter):

  METRIC_NAME = "procs"

  STATISTIC = "Average"

  UNIT = "None"

  # default min/max from legacy metric template
  MIN = 0
  MAX = None

  def getMetricSummary(self):
    """ Get a short description of the metric

    NOTE: derived classes must override this method

    :returns: a short description of the metric
    :rtype: string
    """
    return ("Number of Active processes for %s in %s"
            % (self._dimensions["StackId"], self._region))
