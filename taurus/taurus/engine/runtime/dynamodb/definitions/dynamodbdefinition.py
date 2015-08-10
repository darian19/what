#!/usr/bin/env python
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

from abc import abstractmethod, abstractproperty, ABCMeta



class DynamoDBDefinition(object):
  """ DynamoDB definition abstract base class.  Specific DynamoDB table
  definitions must implement interface defined here.
  """


  __metaclass__ = ABCMeta


  @abstractproperty
  def tableName(self):
    """ DynamoDB table name
    """
    pass


  @abstractproperty
  def tableCreateKwargs(self):
    """ DynamoDB table creation kwargs to
    `boto.dynamodb2.table.Table.create()`, excluding `table_name` and
    `connection`.
    """
    pass


  @abstractproperty
  def Item(self):
    """ Object constructor for item suitable for use in
    `boto.dynamodb2.table.Table.put_item()`
    """
    pass
