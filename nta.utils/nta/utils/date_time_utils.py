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

""" Utility functions for dates and times
"""

from datetime import datetime

import pytz



_NAIVE_EPOCH_BASE = datetime.utcfromtimestamp(0)
_LOCALIZED_EPOCH_BASE = pytz.timezone("UTC").localize(_NAIVE_EPOCH_BASE)



def epochFromNaiveUTCDatetime(dt):
  """ Convert a naive UTC datetime value to epoch-based timestamp

  :param datetime.datetime dt: Naive datetime in UTC (and without tzinfo)
  :returns: epoch-based timestamp
  :rtype: float
  """
  return (dt - _NAIVE_EPOCH_BASE).total_seconds()



def epochFromLocalizedDatetime(dt):
  """ Convert a localized datetime objects to epoch-based timestamp

  :param datetime.datetime dt: Localized datetime (with tzinfo)
  :returns: epoch-based timestamp
  :rtype: float
  """
  return (dt - _LOCALIZED_EPOCH_BASE).total_seconds()
