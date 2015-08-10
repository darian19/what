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

""" Config utilities for tests """

import copy
import functools
import types


from mock import patch


from nta.utils.config import Config



class ConfigAttributePatch(object):
  """ An instance of this class may be used as a decorator, class decorator
  or Context Manager to patch existing configuration attribute values. Honors
  `mock.patch.TEST_PREFIX` for choosing which methods to wrap

  Context Manager Example::

      with ConfigAttributePatch(
          YOMP.app.config.CONFIG_NAME,
          (("aws", "aws_access_key_id",
            os.environ["AWS_ACCESS_KEY_ID"]),
           ("aws", "aws_secret_access_key",
            os.environ["AWS_SECRET_ACCESS_KEY"]))):

        <do test logic in the context of the patched config attributes>


  Function Decorator Example::

      @ConfigAttributePatch(
        YOMP.app.config.CONFIG_NAME,
        (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
         ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"])))
      def testSomething(self):

        <do test logic in the context of the patched config attributes>


  Class Decorator Example::

      @ConfigAttributePatch(
        YOMP.app.config.CONFIG_NAME,
        (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
         ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"])))
      class MyTestCase(unittest.TestCase):
        def testSomething(self):

          <do test logic in the context of the patched config attributes>

        def testSomethingElse(self):
          <do test logic in the context of the patched config attributes>

  """

  def __init__(self, configName, baseConfigDir, values):
    """
    configName: target configuration; see configName definition in
      nta.utils.config
    values: a sequence of overrides, where each element is a three-tuple:
      (<section name>, <attribute name>, <new value>) and <new value> is a string
    """
    self.active = False
    """ True when applied successfully; False after successfully removed or not
    applied """

    # Save for self-validation after patch
    self._configName = configName
    self._baseConfigDir = baseConfigDir
    self._values = copy.deepcopy(values)

    # Verify that the requested attributes already exist and that override
    # values are strings
    config = Config(configName, baseConfigDir)
    for sec, attr, val in values:
      # This will raise an exception if the expected attribute isn't defined
      config.get(sec, attr)

      # Verify that the override value is a string
      if not isinstance(val, types.StringTypes):
        raise TypeError("Expected a string as override for %r/%r, but got a "
                        "value of type %s; value=%r"
                        % (sec, attr, type(val), val,))

    # Create the patch, but don't start it yet
    osEnvironOverrideValues = dict(
      (Config(configName, baseConfigDir)._getEnvVarOverrideName(
        configName, sec, attr), val)
      for sec, attr, val in values
    )
    self._osEnvironPatch = patch.dict("os.environ",
                                      values=osEnvironOverrideValues)


  def __enter__(self):
    self.start()
    return self


  def __exit__(self, *args):
    self.stop()
    return False


  def __call__(self, f):
    """ Implement the function decorator """
    if isinstance(f, types.TypeType):
      return self.decorateClass(f)

    @functools.wraps(f)
    def applyConfigPatch(*args, **kwargs):
      self.start()
      try:
        return f(*args, **kwargs)
      finally:
        self.stop()

    return applyConfigPatch


  def decorateClass(self, cls):
    """ Decorate the test methods in the given class. Honors
    `mock.patch.TEST_PREFIX` for choosing which methods to wrap
    """
    for attrName in dir(cls):
      if attrName.startswith(patch.TEST_PREFIX):
        f = getattr(cls, attrName)
        if callable(f):
          decoratedFunc = ConfigAttributePatch(
            self._configName, self._baseConfigDir, self._values)(f)
          setattr(cls, attrName, decoratedFunc)
    return cls


  def start(self):
    assert not self.active

    # Apply the config attribute overrides
    self._osEnvironPatch.start()

    # Perform self-validation
    config = Config(self._configName, self._baseConfigDir)
    for sec, attr, val in self._values:
      # This will raise an exception if the expected attribute isn't defined
      r = config.get(sec, attr)
      assert r == val, (
        "Config override failed; sec=%s, attr=%s, expected value=%r, but got %r"
        % (sec, attr, val, r))

    self.active = True


  def stop(self):
    assert self.active

    # Revert the config attribute overrides
    self._osEnvironPatch.stop()
    self.active = False
