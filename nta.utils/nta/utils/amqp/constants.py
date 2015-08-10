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
AMQP constants.

TODO need unit tests
"""

class AMQPDeliveryModes(object):
  """ Message delivery modes of interest """

  NON_PERSISTENT_MESSAGE = 1

  # NOTE: A durable queue is necessary for persiting persistent messages at
  # queue level
  PERSISTENT_MESSAGE = 2



class AMQPErrorCodes(object):
  """ AMQP Error Codes of interest; these occur in the method frame of
  Channel.Close and Connection.Close methods
  """

  # Requested resource not found
  NOT_FOUND = 404
