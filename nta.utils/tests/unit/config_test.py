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

"""Unit tests for config utilities"""

import ConfigParser
import contextlib
import copy
import os
import shutil
import tempfile
import time
import unittest

from mock import patch

from nta.utils import config



_SAMPLE_CONF_CONTENTS = """
# MySQL database connection parameters
[config_test_database]
db = YOMP
host = localhost
user = root
passwd =
port = 3306

# RabbitMQ connection parameters
[rabbit]
host = localhost
port = 5672
user = guest
password = guest

"""


# Disable warning: Access to a protected member
# pylint: disable=W0212



class ConfigTest(unittest.TestCase):

  def setUp(self):
    # Use a temp directory for each test
    self._tempDir = tempfile.mkdtemp()
    # Make sure it gets cleaned up
    self.addCleanup(shutil.rmtree, self._tempDir)


  @contextlib.contextmanager
  def _redirectConfigBase(self, configName, contents):
    """ Managed config patch that redirects Config class to use a temp
    directory as the "product home", and sets up a config object
    with the given contents
    """
    confDirPath = os.path.join(self._tempDir, "conf")
    os.mkdir(confDirPath)


    if contents is not None:
      filePath = os.path.join(confDirPath, configName)

      # Create a conf file in the temp directory
      with open(filePath, "w") as fileObj:
        fileObj.write(contents)

    # Make a copy of os.environ, sans config.Config._CONFIG_PATH_ENV_VAR, if any
    environCopy = copy.copy(config.os.environ)



    environPatch = patch.dict(config.os.environ, values=environCopy, clear=True)

    environPatch.start()

    try:
      yield confDirPath
    except:
      raise
    finally:
      environPatch.stop()


  def testHierarchicalConfigNameTypeError(self):
    # Expects TypeError when given configName is hierarchical
    configName = "a/b/c/hieararchical_config_name.conf"
    filePath = os.path.join(self._tempDir, configName)

    with self.assertRaises(TypeError) as cm:
      config.Config(filePath, self._tempDir)

    self.assertIn("Hierarchical configuration object names not supported",
                  cm.exception.args[0])


  def testLoadBaselineConfig(self):
    # Expects to find the baseline config object

    configName = "test.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)

      self.assertEqual(c.get("config_test_database", "db"), "YOMP")
      self.assertEqual(c.CONFIG_NAME, configName)


  def testBaselineConfigObjectNotFound(self):
    # Expects ValueError if baseline config object isn't found

    configName = "test.conf"
    with self._redirectConfigBase(configName, contents=None) as baseConfigDir:
      with self.assertRaises(ValueError) as cm:
        config.Config(configName, baseConfigDir)

      self.assertIn("Baseline configuration object not found",
                    cm.exception.args[0])


  def testReloadConfigAfterOverrideObjectIsCreated(self):
    configName = "test.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c1 = config.Config(configName, baseConfigDir)
      self.assertEqual(c1.get("config_test_database", "db"), "YOMP")
      self.assertEqual(c1.get("rabbit", "host"), "localhost")


      c2 = config.Config(configName,
                         baseConfigDir,
                         mode=config.Config.MODE_OVERRIDE_ONLY)
      c2.add_section("config_test_database")
      c2.set("config_test_database", "new_option", "new_value")
      c2.add_section("rabbit")
      c2.set("rabbit", "host", "new_host")
      self.assertEqual(c2.get("config_test_database", "new_option"),
                       "new_value")
      c2.save()
      del c2

      # Check for "new_option" before and after reloading c1
      with self.assertRaises(ConfigParser.NoOptionError):
        c1.get("config_test_database", "new_option")

      # Reload config and verify that the new option is now found and
      # the overridden option has the new value
      c1.loadConfig()

      self.assertEqual(c1.get("config_test_database", "new_option"),
                       "new_value")
      self.assertEqual(c1.get("rabbit", "host"), "new_host")

      # and that the original option still has the expected value
      self.assertEqual(c1.get("config_test_database", "db"), "YOMP")


  def testReloadConfigAfterOverrideObjectChanges(self):
    configName = "test.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c1 = config.Config(configName, baseConfigDir)
      self.assertEqual(c1.get("config_test_database", "db"), "YOMP")
      self.assertEqual(c1.get("rabbit", "host"), "localhost")


      # Update, but sleep first since getmtime resolution appears to be in
      # seconds
      time.sleep(1.1)
      c2 = config.Config(configName,
                         baseConfigDir,
                         mode=config.Config.MODE_OVERRIDE_ONLY)
      c2.add_section("config_test_database")
      c2.set("config_test_database", "new_option", "new_value")
      c2.add_section("rabbit")
      c2.set("rabbit", "host", "new_host")
      self.assertEqual(c2.get("config_test_database", "new_option"),
                       "new_value")
      c2.save()
      del c2

      # Check for "new_option" before and after reloading c1
      with self.assertRaises(ConfigParser.NoOptionError):
        c1.get("config_test_database", "new_option")

      # Reload config and verify that the new option is now found and
      # the overridden option has the new value
      c1.loadConfig()

      self.assertEqual(c1.get("config_test_database", "new_option"),
                       "new_value")
      self.assertEqual(c1.get("rabbit", "host"), "new_host")

      # and that the original option still has the expected value
      self.assertEqual(c1.get("config_test_database", "db"), "YOMP")


  def testGetEnvVarOverrideName(self):
    # Test Config.getEnvVarOverrideName
    configName = "model-swapper.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      envVarName = config.Config("model-swapper.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        "model-swapper.conf", "interface_bus", "input_queue")
      self.assertEqual(
        envVarName,
        "_NTA_UTILS_CONFIG__MODEL_SWAPPER__INTERFACE_BUS__INPUT_QUEUE")


  def testEnvVarOveridesExistingOptionInGet(self):
    # Test override of an existing option via environment variable
    # in Config.get()
    configName = "test.conf"
    section = "config_test_database"
    option = "db"

    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)
      self.assertEqual(c.get(section, option), "YOMP")
      del c

      # Now, try with an override
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      overrideValues = {
        envVarName : "YOMP rules!"
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        self.assertEqual(c.get(section, option), overrideValues[envVarName])


  def testEnvVarOveridesExistingOptionWithInteger(self):
    # Test override of an existing integer option via environment variable
    # in Config.getint()
    configName = "test.conf"
    section = "config_test_database"
    option = "port"

    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)
      self.assertEqual(c.getint(section, option), 3306)
      del c

      # Now, try with an override
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      newIntValue = 9999
      overrideValues = {
        envVarName : str(newIntValue)
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        self.assertEqual(c.getint(section, option), newIntValue)


  def testEnvVarOveridesExistingOptionWithFloat(self):
    # Test override of an existing integer option via environment variable
    # in Config.getint()
    configName = "test.conf"
    section = "config_test_database"
    option = "port"

    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)
      self.assertEqual(c.getint(section, option), 3306)
      del c

      # Now, try with an override
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      newFloatValue = 9999.99
      overrideValues = {
        envVarName : str(newFloatValue)
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        self.assertEqual(c.getfloat(section, option), newFloatValue)


  def testEnvVarOveridesExistingOptionWithBoolean(self):
    # Test override of an existing integer option via environment variable
    # in Config.getint()
    configName = "test.conf"
    section = "config_test_database"
    option = "port"

    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)
      self.assertEqual(c.getint(section, option), 3306)
      del c

      # Now, try with an override
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      overrideValues = {
        envVarName : 'true'
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        self.assertEqual(c.getboolean(section, option), True)


  def testEnvVarMustNotOverideMissingOptionInGet(self):
    # Test that a missing option is not replaced via environment variable in
    # Config.get()
    #
    # Config applies overrides only to existing options in order to stay
    # compatible with the rest of the ConfigParser API.
    section = "config_test_database"
    option = "no_such_option"

    configName = "test.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      c = config.Config(configName, baseConfigDir)

      # Check that it doesn't exist without the override
      with self.assertRaises(ConfigParser.NoOptionError):
        c.get(section, option)
      del c

      # Now, try with an override, and make sure that it still raises
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      overrideValues = {
        envVarName : "YOMP rules!"
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)

        with self.assertRaises(ConfigParser.NoOptionError):
          c.get(section, option)


  def testEnvVarOveridesExistingOptionInItems(self):
    # Test override of an existing option via environment variable
    # in Config.items()

    configName = "test.conf"
    section = "config_test_database"
    option = "db"

    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      # Try without the override first
      c = config.Config(configName, baseConfigDir)
      originalItemsMap = dict(c.items(section))
      self.assertEqual(len(originalItemsMap), 5)
      self.assertEqual(originalItemsMap[option], "YOMP")
      del c

      # Compare against ConfigParser.ConfigParser
      c = ConfigParser.ConfigParser()
      c.read(os.path.join(config.Config("test.conf", baseConfigDir)
                                .baseConfigDir,
                          configName))
      groundTruthItemsMap = dict(c.items(section))
      self.assertEqual(originalItemsMap, groundTruthItemsMap)
      del c

      # Now, try with an override
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      overrideValues = {
        envVarName : "YOMP rules!"
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        newItemsMap = dict(c.items(section))
        self.assertEqual(newItemsMap[option], overrideValues[envVarName])
        del c

      # Verify that the other options were not altered
      newItemsMap.pop(option)
      originalItemsMap.pop(option)
      self.assertEqual(newItemsMap, originalItemsMap)


  def testEnvVarMustNotOverideMissingOptionInItems(self):
    # Test that a missing option is not replaced via environment variable in
    # Config.items()
    #
    # Config applies overrides only to existing options in order to stay
    # compatible with the rest of the ConfigParser API.

    section = "config_test_database"
    option = "no_such_option"

    configName = "test.conf"
    with self._redirectConfigBase(configName,
                                  _SAMPLE_CONF_CONTENTS) as baseConfigDir:
      # Check that it doesn't exist without the override first
      c = config.Config(configName, baseConfigDir)
      originalItemsMap = dict(c.items(section))
      self.assertEqual(len(originalItemsMap), 5)
      self.assertNotIn(option, originalItemsMap)
      del c

      # Compare against ConfigParser.ConfigParser
      c = ConfigParser.ConfigParser()
      c.read(os.path.join(config.Config("test.conf", baseConfigDir)
                                .baseConfigDir,
                          configName))
      groundTruthItemsMap = dict(c.items(section))
      self.assertEqual(originalItemsMap, groundTruthItemsMap)
      del c

      # Now, try with an override, and make sure that it's still missing
      envVarName = config.Config("test.conf",
                                 baseConfigDir)._getEnvVarOverrideName(
        configName, section, option)

      overrideValues = {
        envVarName : "YOMP rules!"
      }

      with patch.dict(config.os.environ, values=overrideValues):
        c = config.Config(configName, baseConfigDir)
        newItemsMap = dict(c.items(section))
        self.assertNotIn(option, newItemsMap)
        del c

      # Verify that the other options were not altered
      self.assertEqual(newItemsMap, originalItemsMap)



if __name__ == '__main__':
  unittest.main()
