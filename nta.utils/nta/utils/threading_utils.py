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

""" Threading utilitites """


import threading



class ThreadsafeCounter(object):
  """ Reentrancy-safe threadsafe counter """

  def __init__(self, initialValue=0):
    self._counter = initialValue
    self._rlock = threading.RLock()


  @property
  def value(self):
    """ Property for returning the value of the counter """
    with self._rlock:
      return self._counter


  def adjust(self, amount):
    """ Atomically adjust the counter by the given (positive or negative) amount

    :param amount: the posite/negative numbe by which to adjust the counter

    :returns: the new value of the counter
    """
    with self._rlock:
      self._counter += amount
      return self._counter


  def __enter__(self):
    """ Enters the context and atomicaly increments the counter by 1

    :returns: returns the value of the counter corresponding to this entry
    """
    return self.adjust(+1)


  def __exit__(self, *args):
    """ Exits the context and atomically decrements the counter by 1
    """
    self.adjust(-1)