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

"""Repository object utilities for tests."""

import functools
import uuid
from mock import patch

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from YOMP.app import config, repository

# Disable warning: Access to a protected member
# pylint: disable=W0212

ENGINE = repository.getUnaffiliatedEngine()



def getAllDatabaseNames():
  """ Returns `tuple()` of available database names, result of `SHOW DATABASES`
  SQL query.
  """
  with ENGINE.connect() as connection:
    databaseNames = tuple(x[0] for x in
                          connection.execute("SHOW DATABASES").fetchall())
    return databaseNames



class ManagedTempRepository(object):
  """ Context manager that on entry patches the respository database name with
  a unique temp name and creates the repository; then deletes the repository on
  exit.

  This effectively redirects repository object transactions to the
  temporary database while in scope of ManagedTempRepository.

  It may be used as a context manager or as a function decorator (sorry, but
  no class decorator capability at this time)

  Context Manager Example::

      with ManagedTempRepository(clientLabel=self.__class__.__name__) as repoCM:
        print repoCM.tempDatabaseName
        <do test logic>

  Function Decorator Example::

      @ManagedTempRepository(clientLabel="testSomething", kw="tempRepoPatch")
      def testSomething(self, tempRepoPatch):
        print tempRepoPatch.tempDatabaseName
        <do test logic>

  """
  REPO_CONFIG_NAME = config.CONFIG_NAME
  REPO_BASE_CONFIG_DIR = config.baseConfigDir
  REPO_SECTION_NAME = "repository"
  REPO_DATABASE_ATTR_NAME = "db"


  def __init__(self, clientLabel, kw=None):
    """
    clientLabel: this *relatively short* string will be used to construct the
      temporary database name. It shouldn't contain any characters that would
      make it inappropriate for a database name (no spaces, etc.)
    kw: name of keyword argument to add to the decorated function(s). Its value
      will be a reference to this instance of ManagedTempRepository. Ignored
      when this instance is used as context manager. Defaults to kw=None to
      avoid having it added to the keyword args.
    """
    self._kw = kw

    self.tempDatabaseName = "%s_%s_%s" % (self.getDatabaseNameFromConfig(),
                                          clientLabel, uuid.uuid1().hex)

    # Create a Config patch to override the Repository database name
    self._configPatch = ConfigAttributePatch(
      self.REPO_CONFIG_NAME,
      self.REPO_BASE_CONFIG_DIR,
      values=((self.REPO_SECTION_NAME, self.REPO_DATABASE_ATTR_NAME,
               self.tempDatabaseName),))
    self._configPatchApplied = False

    self._attemptedToCreateRepository = False


  @classmethod
  def getDatabaseNameFromConfig(cls):
    return config.get(cls.REPO_SECTION_NAME,
                               cls.REPO_DATABASE_ATTR_NAME)


  def __enter__(self):
    self.start()
    return self


  def __exit__(self, *args):
    self.stop()
    return False


  def __call__(self, f):
    """ Implement the function decorator """

    @functools.wraps(f)
    def applyTempRepositoryPatch(*args, **kwargs):
      self.start()
      try:
        if self._kw is not None:
          kwargs[self._kw] = self
        return f(*args, **kwargs)
      finally:
        self.stop()

    return applyTempRepositoryPatch


  def start(self):
    # Removes possible left over cached engine
    # (needed if non-patched engine is run prior)
    repository.engineFactory(reset=True)

    # Override the Repository database name
    try:
      self._configPatch.start()
      self._configPatchApplied = True

      # Verity that the database doesn't exist yet
      assert self.tempDatabaseName not in getAllDatabaseNames(), (
        "Temp repo db=%s already existed" % (self.tempDatabaseName,))

      # Now create the temporary repository database
      self._attemptedToCreateRepository = True
      repository.reset()

      # Verify that the temporary repository database got created
      assert self.tempDatabaseName in getAllDatabaseNames(), (
        "Temp repo db=%s not found" % (self.tempDatabaseName,))
    except:
      # Attempt to clean up
      self.stop()

      raise


  def stop(self):
    try:
      if self._attemptedToCreateRepository:
        self._attemptedToCreateRepository = False
        # Delete the temporary repository database, if any
        with ENGINE.connect() as connection:
          connection.execute(
              "DROP DATABASE IF EXISTS %s" % (self.tempDatabaseName,))
    finally:
      if self._configPatchApplied:
        self._configPatch.stop()
      try:
        del repository.engineFactory.engine
      except AttributeError:
        pass
