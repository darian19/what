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
class HTMEngineError(Exception):
  pass



class ObjectNotFoundError(HTMEngineError):
  pass



class ApplicationNotConfiguredError(HTMEngineError, KeyError):
  pass



class ObjectAlreadyExistsBase(HTMEngineError):
  """ Base exception class for reporting metric/models that
  already exist; the `uid` attribute is used to report the unique id of the
  existing object.
  """


  def __init__(self, *args, **kwargs):
    """
    :params uid: keyword arg uid provides the uid of the existing metric; other
      args and kwargs are passed directly to the parent constructor
    """
    uid = kwargs["uid"]
    kwargs.pop("uid")
    super(ObjectAlreadyExistsBase, self).__init__(*args, **kwargs)

    self.uid = uid



class MetricAlreadyExists(ObjectAlreadyExistsBase):
  """ Create failed: HTMEngine Metric with the same name already exists;
  `uid` attribute contains the unique identifier of existing metric
  """
  pass



class MetricAlreadyMonitored(ObjectAlreadyExistsBase):
  """ The metric is already monitored; `uid` attribute contains unique
  identifier of the monitored metric
  """
  pass


class MetricNotMonitoredError(HTMEngineError):
  """ The metric is not monitored """
  pass


class MetricNotSupportedError(HTMEngineError):
  """ Operation failed because the requested metric isn't supported """
  pass



class MetricNotActiveError(HTMEngineError):
  """ Operation failed because the metric's status is not MetricStatus.ACTIVE
  """
  pass



class MetricStatisticsNotReadyError(HTMEngineError):
  """ Unable to compute Meric statistics (e.g., no or insufficent samples) """
  pass



class MetricStatusChangedError(HTMEngineError):
  """ Metric status was changed by someone else (most likely another process)
  before this operation could complete
  """
  pass



class DuplicateRecordError(HTMEngineError):
  """Adding a database record failed due to existing duplicate record."""
  pass
