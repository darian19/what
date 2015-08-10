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
Infrastructure exceptions
"""



class PipelineError(Exception):
  pass



class BuildFailureException(PipelineError):
  pass



class CommandFailedError(Exception):
  pass



class CommandForbiddenError(PipelineError):
  pass



class DetachedHeadError(PipelineError):
  pass



class ErrorGettingInstanceID(PipelineError):
  pass



class FailedToCreateRPMOnNonLinuxBox(PipelineError):
  pass



class FailedToMoveRPM(PipelineError):
  pass



class YOMPConfigError(PipelineError):
  pass



class InstanceLaunchError(PipelineError):
  pass



class InstanceNotFoundError(Exception):
  pass



class InstanceNotReadyError(PipelineError):
  pass



class InvalidParametersError(PipelineError):
  pass



class InvalidParameterParsing(PipelineError):
  pass



class MinionIdDoesNotExist(PipelineError):
  pass



class MinionIdVerificationFailed(PipelineError):
  pass



class MissingAWSKeysInEnvironment(PipelineError):
  pass



class MissingDirectoryError(PipelineError):
  pass



class MissingSHAError(PipelineError):
  pass



class MissingRPMError(PipelineError):
  pass



class MultipleRPMForSamePackageError(PipelineError):
  pass



class NupicBuildFailed(PipelineError):
  pass



class PermissionsFailure(Exception):
  pass



class RPMBuildingError(PipelineError):
  pass



class RPMSyncError(PipelineError):
  pass



class TestsFailed(PipelineError):
  pass



class TooManyTriesError(PipelineError):
  pass



class UnittestFailed(PipelineError):
  pass



class UrlRedirectionVerificationFailed(PipelineError):
  pass



class ValueNotSetForSaltRole(PipelineError):
  pass
