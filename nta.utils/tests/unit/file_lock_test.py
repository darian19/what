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

"""Unit tests for file_lock utilities"""

import tempfile
import fcntl
import unittest

from nta.utils import file_lock



class FileLockTest(unittest.TestCase):
  """ Unit tests for the file-lock utilities """

  def setUp(self):
    # Use a temp file for each test
    self._tempFileID = tempfile.TemporaryFile()


  def testSharedLock(self):
    flock = file_lock.SharedFileLock(self._tempFileID)
    # Check creation of file_lock object
    self.assertEqual(type(flock), file_lock._FileLock)


  def testExclusiveLock(self):
    flock = file_lock.ExclusiveFileLock(self._tempFileID)
    self.assertEqual(type(flock), file_lock._FileLock)


  def testContextMgrWithGoodFile(self):
    with file_lock._FileLock(self._tempFileID, fcntl.LOCK_SH) as flock:
      self.assertEqual(type(flock), file_lock._FileLock)


  def testFileLockAcquireException(self):
    # Expects an exception when file is not opened for read or write
    
    self._tempFileID.close()
    with self.assertRaises(file_lock.FileLockAcquireException):
      with file_lock._FileLock(self._tempFileID, fcntl.LOCK_SH) as f_err:
        self.assertIn("FileLock acquire failed on",
                      f_err.exception.args[0])

    with self.assertRaises(file_lock.FileLockAcquireException):
      with file_lock._FileLock([], fcntl.LOCK_SH) as f_err:
        self.assertIn("FileLock acquire failed on",
                      f_err.exception.args[0])


  """To do: test ReleaseException"""


  def testValidLockOperation(self):
    # lockOperation must be one of {LOCK_UN, LOCK_SH, LOCK_EX}
    with self.assertRaises(AttributeError):
      file_lock._FileLock(self._tempFileID, fcntl.LOCK_S)
