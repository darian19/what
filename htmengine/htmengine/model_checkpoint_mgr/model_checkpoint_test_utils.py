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

""" Model Checkpoint utilities for tests """

import functools
import logging
import os
import shutil
import tempfile
import types


from mock import patch


from nta.utils.test_utils.config_test_utils import ConfigAttributePatch


# Disable warning: Access to a protected member
# pylint: disable=W0212


class ModelCheckpointStoragePatch(object):
  """ An instance of this class may be used as a decorator, class decorator
  or Context Manager for redirecting ModelCheckpoint storage to a temporary
  directory in-proc and in child processes.
  """

  def __init__(self, kw=None, logger=logging):
    """
    kw: name of keyword argument to add to the decorated function(s). Its value
      will be a reference to this instance of ModelCheckpointStoragePatch.
      Ignored when this instance is used as context manager. Defaults to kw=None
      to avoid having it added to the keyword args.
    """
    # True when applied successfully; False after successfully removed or not
    # applied
    self.active = False

    self._kw = kw
    self._logger = logger
    self._tempParentDir = None
    self.tempModelCheckpointDir = None
    self._configPatch = None


  def __enter__(self):
    self.start()
    return self


  def __exit__(self, *args):
    self.stop()
    return False


  def __call__(self, f):
    """ Implement the function or class decorator """
    if isinstance(f, types.TypeType):
      return self._decorateClass(f)

    @functools.wraps(f)
    def applyModelCheckpointPatch(*args, **kwargs):
      self.start()
      try:
        if self._kw is not None:
          kwargs[self._kw] = self
        return f(*args, **kwargs)
      finally:
        self.stop()

    return applyModelCheckpointPatch


  def _decorateClass(self, targetClass):
    """ Decorate the test methods in the given class. Honors
    `mock.patch.TEST_PREFIX` for choosing which methods to wrap
    """
    for attrName in dir(targetClass):
      if attrName.startswith(patch.TEST_PREFIX):
        f = getattr(targetClass, attrName)
        if callable(f):
          decoratedFunc = ModelCheckpointStoragePatch(
            self._kw, self._logger)(f)
          setattr(targetClass, attrName, decoratedFunc)
    return targetClass


  def start(self):
    assert not self.active

    self._tempParentDir = tempfile.mkdtemp(
      prefix=self.__class__.__name__)

    self.tempModelCheckpointDir = os.path.join(self._tempParentDir,
                                               "tempStorageRoot")
    os.mkdir(self.tempModelCheckpointDir)

    self._configPatch = ConfigAttributePatch(
      "model-checkpoint.conf",
      os.environ.get("APPLICATION_CONFIG_PATH"),
      (("storage", "root", self.tempModelCheckpointDir),))

    self._configPatch.start()

    self.active = True
    self._logger.info("%s: redirected model checkpoint storage to %s",
                      self.__class__.__name__, self.tempModelCheckpointDir)


  def stop(self):
    self._configPatch.stop()

    shutil.rmtree(self._tempParentDir)

    self.active = False
    self._logger.info("%s: removed model checkpoint storage override %s",
                      self.__class__.__name__, self.tempModelCheckpointDir)
