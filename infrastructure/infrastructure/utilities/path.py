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
import os

from contextlib import contextmanager
from shutil import rmtree

@contextmanager
def changeToWorkingDir(path):
  """
  Equivalent of pushd X; foo; popd in bash.

  Change into destination path, yield
  context, and finally change back to original path

  @param path: The path to change to.
  """
  original = os.getcwd()
  os.chdir(path)
  yield
  os.chdir(original)



def rmrf(path, logger=None):
  """
  There isn't a single function that deletes both files and directories,
  you have to use different calls if a path points to a directory or file,
  which bloats the code.

  @note: This behaves like `rm -rf` and will not complain if the directory
  isn't empty, it will delete it and the contents anyway.

  @param path: path to file/directory you want deleted.

  @param logger: optional logging object
  """
  if logger:
    logger.debug("removing %s", path)
  if os.path.isfile(path):
    os.remove(path)
  if os.path.isdir(path):
    rmtree(path)



def purgeDirectory(path, whitelist=None, logger=None):
  """
  Delete everything from path that is not whitelisted.

  If whitelist is None, purge everything.

  @param path - path to purge

  @param whitelist - allowed files/directories to keep

  @param logger: optional logging object
  """
  # Pylint didn't like a default argument of [] for whitelist
  if not whitelist:
    whitelist = []

  if logger:
    logger.debug("Purging directory %s", path)

  for thing in os.listdir(path):
    if thing not in whitelist:
      rmrf("%s/%s" % (path, thing), logger=logger)
    else:
      if logger:
        logger.debug("Retaining %s", thing)
