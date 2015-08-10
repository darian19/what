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
import time

from nta.utils.extended_logger import ExtendedLogger


class HTMEngineExtendedLogger(ExtendedLogger):
  """ Extends the NuPIC ExtendedLogger by calculating the duration of an
  htmengine instance and adding it as a prefix to the log message.
  """
  cached_htmengine_update_epoch = None

  def __init__(self, name):
    super(HTMEngineExtendedLogger, self).__init__(name)
    self._logPrefix = ""

