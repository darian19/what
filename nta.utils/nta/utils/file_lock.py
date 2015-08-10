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

import fcntl
import sys



class FileLockAcquireException(Exception):
  pass



class FileLockReleaseException(Exception):
  pass



def SharedFileLock(fileObj):
  """ Create a shared file lock context manager; shared file locks are
  typically used for read locks.

  :param fileObj:  A file object to be used for locking; The file MUST already
    exist and be open. This could also be a file descriptor (file.fileno()).
  """
  return _FileLock(fileObj, fcntl.LOCK_SH)



def ExclusiveFileLock(fileObj):
  """ Create a shared file lock context manager; shared file locks are
  typically used for write locks.

  :param fileObj:  A file object to be used for locking; The file MUST already
    exist and be open. This could also be a file descriptor (file.fileno()).
  """
  return _FileLock(fileObj, fcntl.LOCK_EX)



class _FileLock(object):
  """ 
  This class implements a global file lock that can be used as a
  a mutex between cooperating processes. It can be used as a context manager.

  NOTE: the present implementation's behavior is undefined when multiple
        threads may try ackquire a lock on the same file.

  NOTE: the present implementation assumes the calling class opens the file
        for read or write and handles closing the file properly.
  """

  def __init__(self, fileObj, lockOperation):
    """
  :param fileObj:  A file object to be used for locking; The file MUST already
    exist and be open. This could also be a file descriptor (file.fileno()).

    :param lockOperation: one of: fcntl.LOCK_EX or fcntl.LOCK_SH
    """

    self.__file = fileObj
    self.__lockOperation = lockOperation


  def __enter__(self):
    """ 
    Context Manager protocol method. Allows a FileLock instance to be
    used in a "with" statement for automatic acquire/release

    Parameters:
    ------------------------------------------------------------------------
    retval:     self.
    """
    self.acquire()
    return self


  def __exit__(self, excType, excVal, excTb):
    """ 
    Context Manager protocol method. Allows a FileLock instance to be
    used in a "with" statement for automatic acquire/release
    """
    self.release()
    return False


  def acquire(self):
    """ 
    Acquire global lock

    exception: FileLockAcquireException on failure
    """
    try:
      fcntl.flock(self.__file, self.__lockOperation)
    except Exception as e:
      e = FileLockAcquireException(
        "FileLock acquire failed on %r" % (self.__file), e)
      raise e, None, sys.exc_info()[2]


  def release(self):
    """ Release global lock """
    try:
      fcntl.flock(self.__file, fcntl.LOCK_UN)
    except Exception as e:
      e = FileLockReleaseException(
        "FileLock release failed on %r" % (self.__file), e)
      raise e, None, sys.exc_info()[2]
