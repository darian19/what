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

"""Unit tests for logging_support_raw utilities"""

import ConfigParser
import contextlib
import copy
import logging
import os
import shutil
import sys
import tempfile
import unittest

from mock import patch

from nta.utils import logging_support_raw
from nta.utils.logging_support_raw import LoggingSupport as LS



_SAMPLE_CONNECTION_CONTENTS = """
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



class LoggingSupportTest(unittest.TestCase):
  """ Unit tests for the logging-support utilities """

  def setUp(self):
    # Use a temp directory for each test
    self._tempDir = tempfile.mkdtemp()
    # Make sure it gets cleaned up
    self.addCleanup(shutil.rmtree, self._tempDir)


  @contextlib.contextmanager
  def _redirectLogBase(self, loggingName, contents):
    """ Managed log patch that redirects LoggingSupport class to use a temp
      directory as the "product home", and sets up a logging_support object
      with the given contents
      """
    # Save/restore the value changed by logging_support.setLogir()
    logDirPatch = patch.object(logging_support_raw, "_LOG_DIR")
    logDirPatch.start()

    logDirPath = os.path.join(self._tempDir, "log")
    os.mkdir(logDirPath)
    logging_support_raw.setLogDir(logDirPath)

    if contents is not None:
      filePath = os.path.join(logDirPath, loggingName)

      # Create a log file in the temp directory
      with open(filePath, "w") as fileObj:
        fileObj.write(contents)

    # Make a copy of os.environ
    environCopy = copy.copy(logging_support_raw.os.environ)


    def resourceFilenamePatch(module, path):
      self.assertEqual(module, "YOMP")
      self.assertEqual(path, "")
      return os.path.join(self._tempDir, "YOMP")

    environPatch = patch.dict(logging_support_raw.os.environ, values=environCopy, clear=True)
    resourceFilenamePatch = patch.object(
      logging_support_raw, "resource_filename",
      autospec=True, side_effect=resourceFilenamePatch)

    environPatch.start()
    resourceFilenamePatch.start()

    try:
      yield
    except:
      raise
    finally:
      resourceFilenamePatch.stop()
      environPatch.stop()
      logDirPatch.stop()


  def testInitLoggingInputs(self):
    # Invalid loggingLevel throws a ValueError
    temp_ls = LS()
    with self.assertRaises(ValueError):
      temp_ls.initLogging("DEBUGGING")
    # Invalid console throws a ValueError
    with self.assertRaises(ValueError):
      temp_ls.initLogging("DEBUG", "stderror")


  def testInitLoggingNullHandlers(self):
    # Null handlers should throw ConfigParser.NoOptionError and print a sys.stderr message
    temp_ls = LS()
    with self.assertRaises(ConfigParser.NoOptionError):
      temp_ls.initLogging(None, None)
      assertEqual(sys.stderr.getvalue(), "WARNING: logging_support is disabling logging output because all output handlers are disabled")


  def testLogFilePathExists(self):
    # Directory containing the log file should be created; loggin_support.py line 250-257
    with self._redirectLogBase("logging_example", _SAMPLE_CONNECTION_CONTENTS):
      temp_ls = LS()
      temp_ls.initLogging("DEBUG", "stderr", True)
      path = temp_ls.getApplicationLogFilePath()
      self.assertTrue(os.path.isdir(os.path.dirname(path)))


  def testLoggingInitForUsageExamples(self):
    g_log = logging.getLogger("my_example")
    assert isinstance(g_log, logging.Logger)

    with self._redirectLogBase("logging_example", _SAMPLE_CONNECTION_CONTENTS):
      # Test logging init for a tool
      self.assertEqual(LS.initTool(), LS.initLogging(None, console="stderr", logToFile=True))

      # Test logging init for a service
      self.assertEqual(LS.initService(), LS.initLogging(None, console="stderr", logToFile=False))

      # Test logging init for a test app
      self.assertEqual(LS.initTestApp(), LS.initLogging(None, console="stderr", logToFile=False))


  def testLoggingRootPath(self):
    # getLoggingRootDir() should return the temp path
    with self._redirectLogBase("logging_example", _SAMPLE_CONNECTION_CONTENTS):
      temp_ls = LS()
      temp_ls.initLogging("DEBUG", "stderr", True)
      self.assertEqual(temp_ls.getLoggingRootDir(), os.path.join(self._tempDir, "log"))


  def testLoggingConfigPath(self):
    # getLoggingConfTemplatePath() should return path to ../logging.conf
    temp_ls = LS()
    temp_ls.initLogging()
    self.assertEqual(os.path.join(logging_support_raw._APPLICATION_CONF_DIR, "logging.conf"),
                       temp_ls.getLoggingConfTemplatePath())


  def testLoggingAppPath(self):
    # getApplicationLogFilePath() should return path to ../app_name.log
    app_name = "py"  # Because called with py.test
    with self._redirectLogBase(app_name, _SAMPLE_CONNECTION_CONTENTS):
      temp_ls = LS()
      temp_ls.initLogging("DEBUG", "stderr", True)
      self.assertEqual(os.path.abspath(os.path.join(temp_ls.getLoggingRootDir(), "processes", app_name + ".log")), temp_ls.getApplicationLogFilePath())
