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
import logging
import sys

LOG_LEVELS = ["critical", "debug", "error", "info", "warning"]


def initPipelineLogger(name, logLevel="info"):
  """
    Initializes a logger for the pipeline.

    :param name: The name of the calling pipeline

    :param logLevel: What level to log at; default = info. Valid values are:
      [debug, info, warning, error, exception]

    :returns: An initialized logger
  """
  logger = logging.getLogger(name)
  consoleHandler = logging.StreamHandler(stream=sys.stderr)
  formatter  = logging.Formatter(
    "%(name)s:%(levelname)s:%(asctime)s:%(message)s")
  consoleHandler.setFormatter(formatter)
  logger.setLevel(logLevel.upper())
  logger.addHandler(consoleHandler)
  return logger


def printEnv(env, logger):
  """
    Prints the environment.

    :param env: The current environment dict.
  """
  for (key, value) in sorted(env.items()):
    logger.debug("%s=%s", key, value)
