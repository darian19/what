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

import errno


class ManagedSubprocessTerminator(object):
  """ Kills the managed subrocess on exit from Context Manager """

  def __init__(self, p):
    """
    p: an instance of subprocess.Popen class.
    """
    self._p = p


  def __enter__(self):
    return self._p


  def __exit__(self, *args):
    if self._p.returncode is None:
      try:
        self._p.kill()
      except OSError as e:
        if e.errno == errno.ESRCH:
          # "no such process" - we must have already killed it
          pass
        else:
          raise
      else:
        self._p.wait()
    return False
