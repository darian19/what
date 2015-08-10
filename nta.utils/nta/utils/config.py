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
Implements the Config class that customizes the built-in ConfigParser for use in
applications.

By convention, each layer (a collection of tightly-coupled subsystems or
services) defines a configuration file shared by its subsystems. For
example: application.conf, model-swapper.conf, rabbitmq.conf, etc.

Normal Config usage...

  Retrieval Example::

      # Get the name of Model Swapper's input message queue
      from <application> import Config
      config = Config("model-swapper.conf")
      inputQueueName = config.get("interface_bus","input_queue")

  Override and Save Example::
      from <application> import Config
      config = Config("application.conf",
                      mode=Config.MODE_OVERRIDE_ONLY)
      if not config.has_section("security"):
        config.add_section("security")
      config.set("security", "apikey", "abc12")
      config.save()


Overriding an *existing* config option value via environment variable using mock
package in test code...

  For testing, it's often necessary to logically override a configuration
  setting that the component(s) under test rely on. This comes up in unit tests;
  it also comes up in integration tests involving a tree consisting of a parent
  process and some number of sub-processes, where normal Mock'ing can't traverse
  process boundaries (e.g., model_swapper_e2e_test.py).

  Example::

      NOTE: this patch affects the pure python code in the current process as
      well as the tree of descendant processes that are allowed to inherit this
      process's python environment variables.

      See nta.utils.test_utils.config_test_utils.ConfigAttributePatch.

      import os
      import uuid
      from mock import patch
      from <application> import Config

      # Override the input queue name used by model swapper interface bus
      inputQueueEnvVarName = Config.getEnvVarOverrideName(
        configName="model-swapper.conf",
        section="interface_bus",
        option="input_queue")

      environOverrideValues = {
        # Use uuid in the queue name to support concurrent executions of the
        # test
        inputQueueEnvVarName :
          "ModelSwapperE2ETest.INPUT_MQ." + uuid.uuid4().hex
      }

      with patch.dict("os.environ", values=environOverrideValues):
        <run your test logic in the context of the above patch.dict context
        manager>


"""

from ConfigParser import ConfigParser
import errno
import functools
import os
import shutil
import types

from nta.utils import file_lock, makeDirectoryFromAbsolutePath



class Config(ConfigParser, object):
  """Config class that customizes the built-in ConfigParser for use in
  applications.

  NOTE: we have "object" in our base class list because at the time of this
  writing, ConfigParser is an "old-style" class that doesn't inherit from
  "object". Adding "object" to our inheritance chain enables our subclasses
  to treat us as a "new-style" class, including the proper use of super(), etc.
  """

  # In "logical" mode, both baseline and override configs will be loaded, and
  # the save() method will raise a TypeError exception if called
  MODE_LOGICAL = 1

  # In "override only" mode, only the override config will be loaded and
  # the save() method is permitted.
  MODE_OVERRIDE_ONLY = 2

  # Configuration override directory name (located inside the base config
  # directory)
  _CONFIG_OVERRIDE_DIR_NAME = "overrides"


  def __init__(self, configName, baseConfigDir, mode=MODE_LOGICAL):
    """
    :param configName: Name of the configuration object; e.g.,
      "application.conf".
    :param baseConfigDir: Base configuration directory
    :param mode: configuration load mode: Config.MODE_LOGICAL or
      Config.MODE_OVERRIDE_ONLY. Defaults to Config.MODE_LOGICAL.

    :raises: ValueError if the baseline config corresponding to configName
      doesn't exist
    """
    # Initialize base class
    ConfigParser.__init__(self)

    if not isinstance(configName, types.StringTypes):
      raise TypeError("Expected a string configName=%r, but got %r instead" %
                      (configName, type(configName)))

    head, tail = os.path.split(configName)
    if head:
      raise TypeError("Hierarchical configuration object names not supported: "
                      "%r" % (configName,))
    if not tail:
      raise TypeError("Empty configuration object name: %r" % (configName,))

    self._configName = configName

    self._mode = mode

    self._baselineLoaded = False

    # Namespace used in generating environment variable names for overriding
    # configuration settings (for testing)
    self._envVarNamespace = self._getEnvVarOverrideNamespace(configName)

    # Value of getmtime at the time when override config was last loaded
    self._lastModTime = 0

    self.baseConfigDir = baseConfigDir

    self.loadConfig()


  @property
  def CONFIG_NAME(self):
    return self._configName


  @functools.wraps(ConfigParser.get)
  def get(self, section, option, *args, **kwargs):
    """ Override ConfigParser.ConfigParser.get() in order to apply environment
    variable-based override to an existing option.

    This is helpful for testing, especially across process boundaries to
    subprocesses.

    We apply overrides only to existing options in order to stay compatible
    with the rest of the ConfigParser API.
    """
    value = ConfigParser.get(self, section, option, *args, **kwargs)

    envValue = self._getEnvVarOverrideValue(section, option)
    if envValue is not None:
      value = envValue

    return value


  @functools.wraps(ConfigParser.items)
  def items(self, section, *args, **kwargs):
    """ Override ConfigParser.ConfigParser.items() in order to apply environment
    variable-based overrides to existing options

    This is helpful for testing, especially across process boundaries to
    subprocesses.

    We apply overrides only to existing options in order to stay compatible
    with the rest of the ConfigParser API.
    """
    result = ConfigParser.items(self, section, *args, **kwargs)

    for i in xrange(len(result)):
      option, _value = result[i]

      envValue = self._getEnvVarOverrideValue(section, option)
      if envValue is not None:
        result[i] = (option, envValue)

    return result


  def loadConfig(self):
    """
    Reload the configuration object from disk if its override has changed. The
    override may be changed by a different process. If that's a possibility for
    your app, you may use this method to conditionally reload the config
    periodically.

    NOTE: the ability to detect change is based on file modification time
    resolution, which was one second at the time of this writing
    """
    overrideConfigPath = os.path.join(
      self._getConfigOverrideDir(),
      self._configName)

    overrideConfigChanged = False
    mtime = 0
    try:
      mtime = os.path.getmtime(overrideConfigPath)
    except OSError as e:
      if e.errno != errno.ENOENT:
        raise
      if self._lastModTime != 0:
        # Override config was there earlier but disappeared
        overrideConfigChanged = True
    else:
      if mtime > self._lastModTime:
        # Override config's modification time changed
        overrideConfigChanged = True

    if ((self._mode == self.MODE_LOGICAL and not self._baselineLoaded) or
        overrideConfigChanged):
      # Reset config cache
      self._sections.clear()
      self._defaults.clear()

      if self._mode == self.MODE_LOGICAL:
        # Load baseline config
        baseConfigPath = os.path.join(self.baseConfigDir, self._configName)
        try:
          with open(baseConfigPath, "r") as fileObj:
            self.readfp(fileObj)
        except IOError as e:
          if e.errno != errno.ENOENT:
            raise
          raise ValueError("Baseline configuration object not found: %r" %
                           (baseConfigPath))

        self._baselineLoaded = True

      if overrideConfigChanged:
        if mtime != 0:
          # Load override config
          with open(overrideConfigPath, "r") as fileObj:
            with file_lock.SharedFileLock(fileObj):
              self.readfp(fileObj)

        self._lastModTime = mtime


  def save(self):
    """ Save the current override-only configuration to the override config
    file

    :raises TypeError: if mode != MODE_OVERRIDE_ONLY
    """
    if self._mode != self.MODE_OVERRIDE_ONLY:
      raise TypeError("Config=%s was not loaded in MODE_OVERRIDE_ONLY; mode=%s"
                      % (self._configName, self._mode))

    configOverrideDir = self._getConfigOverrideDir()
    makeDirectoryFromAbsolutePath(configOverrideDir)

    overrideConfigPath = os.path.join(configOverrideDir, self._configName)

    # NOTE: we open with os.O_RDWR | os.O_CREAT so that we can acquire the
    # file lock before altering contents of the file
    with os.fdopen(os.open(overrideConfigPath, os.O_RDWR | os.O_CREAT, 0644),
                   "w") as fileObj:
      with file_lock.ExclusiveFileLock(fileObj):
        self.write(fileObj)
        fileObj.flush()
        fileObj.truncate()


  def clearAllConfigOverrides(self):
    """ Delete all configuration override objects
    WARNING: this deletes user-provisioned and user-specific information (e.g.,
    AWS credentials, API key, YOMP server ID, etc.)
    """
    configOverrideDir = self._getConfigOverrideDir()
    if os.path.exists(configOverrideDir):
      shutil.rmtree(configOverrideDir)


  def _getConfigOverrideDir(self):
    """
    :returns: path of override configuration object directory
    """
    return os.path.join(self.baseConfigDir, self._CONFIG_OVERRIDE_DIR_NAME)


  def _getEnvVarOverrideName(self, configName, section, option):
    """ For testing; Given configName, section name, and option name, generate
    the name of the environment variable for overriding that setting

    configName: as in the constructor; any dash characters will be converted to
      underscores
    section: name of the section in the config file
    option: name of the option within the section

    For example::

        getEnvVarOverrideName(configName="model-swapper.conf"
                              section="interface_bus", option="input_queue")

    would produce the environment variable name::

        _NTA_UTILS_CONFIG__MODEL_SWAPPER__INTERFACE_BUS__INPUT_QUEUE
    """
    return self._combineEnvVarOverrideParts(
      envVarNamespace=self._getEnvVarOverrideNamespace(configName),
      section=section, option=option)


  def _getEnvVarOverrideValue(self, section, option):
    """
    Returns: the environment variable-based override value for the given
    section/option; if not found, returns None.
    """
    envVarName = self._combineEnvVarOverrideParts(
      envVarNamespace=self._envVarNamespace,
      section=section, option=option)

    return os.environ.get(envVarName)


  @staticmethod
  def _combineEnvVarOverrideParts(envVarNamespace, section, option):
    """
    envVarNamespace: the result from _getEnvVarOverrideNamespace
    section: name of the section in the config file
    option: name of the option within the section
    """
    return envVarNamespace + ("%s__%s" % (section, option,)).upper()


  @staticmethod
  def _getEnvVarOverrideNamespace(configName):
    """ For testing. Create an environment variable override namespace from the
    given configName
    """
    configNameRoot = os.path.splitext(os.path.basename(configName))[0]
    if not configNameRoot:
      raise ValueError("Missing filename in configName=%r" % (configName,))

    return ("_NTA_UTILS_CONFIG__" +
            configNameRoot.upper().replace("-", "_") +
            "__")
