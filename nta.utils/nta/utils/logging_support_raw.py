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
Common Python logging initialization helper

USAGE EXAMPLES

NOTE: by convention, logging should be initialized only by the main process.
  modules that provide APIs should not initialize logging as it would
  clobber the logging configuration desired by the application.


1. A tool

    import logging
    from <application>.logging_support import LoggingSupport

    g_log = logging.getLogger("my_tool")

    if __name__ == "__main__":
      LoggingSupport.initTool()

      g_log.info("my tool started")



2. A service

    import logging
    from <application>.logging_support import LoggingSupport

    g_log = logging.getLogger("my_service")

    if __name__ == "__main__":
      LoggingSupport.initService()

      g_log.info("my service started")



3. A test app that runs in a unittest-compatible test framework that captures
console output (including stderr):

    from <application>.logging_support import LoggingSupport


    def setUpModule():
      LoggingSupport.initTestApp()

"""

from ConfigParser import ConfigParser
import logging
import logging.config
import logging.handlers
import os
from pkg_resources import resource_filename, get_distribution
from StringIO import StringIO
import sys
import time

from nta.utils import makeDirectoryFromAbsolutePath



_LOG_DIR = None

distribution = get_distribution("nta.utils")

_APPLICATION_CONF_DIR = os.path.join(distribution.location, "conf")



def setLogDir(logDir):
  """ Set log directory

  :param logDir: Absolute path to application-specific logging directory.
  """
  global _LOG_DIR

  assert os.path.isabs(logDir), "Log directory path must be absolute"

  _LOG_DIR = logDir



class LoggingSupport(object):

  @classmethod
  def initTool(cls, loggingLevel=None):
    """ Initialize python logging for a tool (e.g., set_edition, pavement) to
    output log messages to stderr and a tool-specific log file.

    This is useful for a tool whose stderr output is not redirected to a log
    file by a higher-level process manager, so it's log output needs to be
    saved in a file.

    We use stderr (vs. stdout) in order to avoid conflict with a tool's data
    output on stdout, in case the tool needs to be used in a pipe. stderr is
    also the default output of logging.StreamHandler.

    NOTE: by convention, logging should be initialized only by the main process.
        modules that provide APIs should not initialize logging as it would
        clobber the logging configuration desired by the application.

    :param loggingLevel: logging level string for filtering in root logger and
        output handlers; one of: "DEBUG", "INFO", "WARNING", "WARN", "ERROR",
        "CRITICAL" or "FATAL" that correspond to logging.DEBUG, logging.INFO,
        etc. Defaults to "INFO".
    """
    cls.initLogging(loggingLevel=loggingLevel,
                    console="stderr",
                    logToFile=True)



  @classmethod
  def initService(cls, loggingLevel=None):
    """ Initialize python logging for a Service (e.g., YOMP metric_collector,
    model_scheduler) to output log messages to stderr only (and not to a file).

    This is useful when running as a service under SupervisorD, which redirects
    the service's stderr/stdout to a log file.

    We use stderr in order for the log output of a service to be synchronized
    with python's default exception dump on stderr. stderr is also the default
    output of logging.StreamHandler.

    NOTE: by convention, logging should be initialized only by the main process.
        modules that provide APIs should not initialize logging as it would
        clobber the logging configuration desired by the application.

    :param loggingLevel: logging level string for filtering in root logger and
        output handlers; one of: "DEBUG", "INFO", "WARNING", "WARN", "ERROR",
        "CRITICAL" or "FATAL" that correspond to logging.DEBUG, logging.INFO,
        etc. Defaults to "INFO".
    """
    cls.initLogging(loggingLevel=loggingLevel,
                    console="stderr",
                    logToFile=False)



  @classmethod
  def initTestApp(cls, loggingLevel=None):
    """ Initialize python logging for a test app (e.g., unit or integration) to
    output log messages to stderr only.

    This is useful for a test app whose console output (including stderr) is
    redirected to a log file by a higher-level test framework.

    We use stderr in order for the log output to be synchronized with python's
    default exception dump on stderr. stderr is also the default output of
    logging.StreamHandler.

    NOTE: by convention, logging should be initialized only by the main process.
        modules that provide APIs should not initialize logging as it would
        clobber the logging configuration desired by the application.

    :param loggingLevel: logging level string for filtering in root logger and
        output handlers; one of: "DEBUG", "INFO", "WARNING", "WARN", "ERROR",
        "CRITICAL" or "FATAL" that correspond to logging.DEBUG, logging.INFO,
        etc. Defaults to "INFO".
    """
    cls.initLogging(loggingLevel=loggingLevel,
                    console="stderr",
                    logToFile=False)



  @classmethod
  def initLogging(cls, loggingLevel=None, console="stderr",
                  logToFile=False):
    """ A lower-level function to initialize python logging for the calling
    process. Supports logging output to a console (stderr or stdout) and/or log
    file.

    See also higher-level functions initTool() and initService().

    NOTE: by convention, logging should be initialized only by the main process.
        modules that provide APIs should not initialize logging as it would
        clobber the logging configuration desired by the application.

    :param loggingLevel: logging level string for filtering in root logger and
        output handlers; one of: "DEBUG", "INFO", "WARNING", "WARN", "ERROR",
        "CRITICAL" or "FATAL" that correspond to logging.DEBUG, logging.INFO,
        etc. Defaults to "INFO".

    :param console: Console logging destination; either "stderr" or "stdout";
        None to suppress output to console.

    :param logToFile: True to output logs to a file. If enalbed, a log file
        specific to the calling app instance will be created at file path
        generated by our getApplicationLogFilePath method.
    """
    validLoggingLevels = ["DEBUG", "INFO", "WARNING", "WARN", "ERROR",
                          "CRITICAL", "FATAL"]

    if loggingLevel is not None and loggingLevel not in validLoggingLevels:
      raise ValueError("loggingLevel %r not one of %s" %
                       (loggingLevel, validLoggingLevels))

    consoleHandlerArgsMap = dict(
      stderr="(sys.stderr, )",
      stdout="(sys.stdout, )"
    )

    if console is not None and console not in consoleHandlerArgsMap:
      raise ValueError("console %r not one of %s" %
                       (console, consoleHandlerArgsMap.keys()))

    # Configure logging timestamp for UTC
    logging.Formatter.converter = time.gmtime

    # Load the config tempalte
    config = ConfigParser()
    with open(cls.getLoggingConfTemplatePath(), 'r') as fileObj:
      config.readfp(fileObj)

    # Customize the config template

    handlers = []

    if console is not None:
      handlers.append("console")
      if loggingLevel is not None:
        config.set("handler_console", "level", loggingLevel)
      config.set("handler_console", "args", consoleHandlerArgsMap[console])

    if logToFile:
      handlers.append("file")

      # Get a log file path specific to the calling app
      logFilePath = cls.getApplicationLogFilePath()

      # Create the directory that will contain the log file
      makeDirectoryFromAbsolutePath(os.path.dirname(logFilePath))

      if loggingLevel is not None:
        config.set("handler_file", "level", loggingLevel)
      config.set("handler_file", "filename", logFilePath)

    if not handlers:
      print >> sys.stderr, (
        "WARNING: logging_support is disabling logging output because all "
        "output handlers are disabled")

      handlers.append("null")

    # Convert list of logging output handler names into comma-separated string
    handlers = ",".join(handlers)

    # Initialize the root logger
    if loggingLevel is not None:
      config.set("logger_root", "level", loggingLevel)
    config.set("logger_root", "handlers", handlers)

    # Initialize the list of all logging output handlers
    config.set("handlers", "keys", handlers)

    # Dump the customized config into a StringIO object for logging setup
    customConfigFile = StringIO()
    config.write(customConfigFile)
    customConfigFile.seek(0)

    # Initialize logging from StringIO file object
    logging.config.fileConfig(customConfigFile, disable_existing_loggers=False)



  @classmethod
  def getLoggingRootDir(cls):
    """ Return application-specific logging root directory path

    :returns: application-specific logging root directory path
    :rtype: string
    """
    loggingRootDir = _LOG_DIR
    return os.path.abspath(
      os.path.expanduser(
        os.path.expandvars(loggingRootDir)))



  @classmethod
  def getLoggingConfTemplatePath(cls):
    """
    :returns: Absolute path of logging configuration template file
    """
    if not isinstance(_APPLICATION_CONF_DIR, basestring):
      raise TypeError("Undefined base configuration directory.")

    return os.path.join(_APPLICATION_CONF_DIR, "logging.conf")



  @classmethod
  def getApplicationLogFilePath(cls):
    """ Generate a log file path specific to the calling app.

    :returns: absolute log file path specific to the calling app
    :rtype: string
    """
    appName = os.path.splitext(os.path.basename(sys.argv[0]))[0] or (
                               "UnknownApp")

    return os.path.abspath(
      os.path.join(cls.getLoggingRootDir(),
                   "processes",
                   appName + ".log"))
