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

import optparse
import random
import os


import sqlalchemy

from nta.utils import sqlalchemy_utils
from nta.utils.config import Config

from taurus.metric_collectors import CONF_DIR
from taurus.metric_collectors.collectorsdb import schema
from taurus.metric_collectors.collectorsdb.migrate import migrate

# Retry decorator for mysql transient errors
retryOnTransientErrors = sqlalchemy_utils.retryOnTransientErrors



_DSN_FORMAT = ("mysql://%(user)s:%(password)s@%(host)s:%(port)s/%(db)s?"
               "charset=%(charset)s")



_REPOSITORY_OPTIONS = dict(
  charset=schema.MYSQL_CHARSET
)



class CollectorsDbConfig(Config):
  """ Metric Collectors SQL DB Configuration """

  CONFIG_NAME = "collectors-sqldb.conf"


  def __init__(self, mode=Config.MODE_LOGICAL):
    super(CollectorsDbConfig, self).__init__(self.CONFIG_NAME,
                                             CONF_DIR,
                                             mode=mode)



def _getRepoParams():
  """
  :returns: a dict of repository parameters for substitutions in _DSN_FORMAT
  """
  repoParams = dict(CollectorsDbConfig().items("repository"))
  if not repoParams["host"] or not repoParams["user"]:
    raise ValueError("Missing host and/or user value from collectors-sqldb "
                     "config: %s", repoParams)
  repoParams.update(_REPOSITORY_OPTIONS)
  return repoParams




def getDSN():
  return _DSN_FORMAT % _getRepoParams()



class _EngineSingleton(object):


  _engine = None
  _pid = None


  @classmethod
  def getEngine(cls):
    pid = os.getpid()

    if cls._pid != pid:
      if cls._engine is not None:
        cls._engine.dispose()
        cls._engine = None

      cls._engine = sqlalchemy.create_engine(getDSN())
      cls._pid = pid

    return cls._engine


  @classmethod
  def reset(cls):
    """ Reset internal engine and pid references
    """
    cls._engine = None
    cls._pid = None



def engineFactory():
  """
  :returns: SQLAlchemy engine object
  :rtype: sqlalchemy.engine.Engine
  """
  return _EngineSingleton.getEngine()



def resetEngineSingleton():
  """ Reset engine singleton
  """
  _EngineSingleton.reset()



def resetCollectorsdbMain():
  """ Setuptools console script entry point for resetting collectorsdb (
  taurus_collectors database).
  :returns: 0 if reset was completed successfully; 1 if user doesn't confirm the
    request
  """
  repoParams = _getRepoParams()

  helpString = (
    "%%prog [--suppress-prompt-and-obliterate-database]\n\n"
    "WARNING: PERMANENT DATA LOSS. Obliterate/reset collectorsdb sql "
    "database %(db)s on server %(host)s." % repoParams)

  parser = optparse.OptionParser(helpString)

  parser.add_option(
      "--suppress-prompt-and-obliterate-database",
      action="store_true",
      default=False,
      dest="suppressPrompt",
      help=("Suppresses confirmation prompt and proceedes with this "
            "DESTRUCTIVE operation. This option is intended for scripting. "
            "[default: %default]"))

  options, remainingArgs = parser.parse_args()
  if remainingArgs:
    parser.error("Unexpected remaining args: %r" % (remainingArgs,))

  if options.suppressPrompt:
    return reset(suppressPromptAndObliterateDatabase=True)
  else:
    return reset()



def reset(offline=False, **kwargs):
  """ Reset the taurus_collectors database; upon successful completion, the
  necessary tables are created, but the tables are not populated

  :param offline: False to execute SQL commands; True to just dump SQL commands
    to stdout for offline mode or debugging
  :param bool suppressPromptAndObliterateDatabase: kwarg only! When passed with
    the value of True, proceeds to drop the taurus_collectors database without
    prompting. Without this arg or if it's False, will prompt the user via
    terminal and expect a specific string to be entered
  :returns: 0 if reset was completed successfully; 1 if user doesn't confirm the
    request
  """
  repoParams = _getRepoParams()

  promptAvoidanceArgName = "suppressPromptAndObliterateDatabase"

  if not kwargs.get(promptAvoidanceArgName):
    expectedAnswer = "Yes-%s" % (random.randint(1, 30),)

    answer = raw_input(
      "Attention!  You are about to do something irreversible, and potentially"
      " dangerous.\n"
      "\n"
      "To back out immediately without making any changes, feel free to type "
      "anything but \"%s\" in the prompt below, and press return.\n"
      "\n"
      "Should you choose to continue, the DATABASE \"%s\" on \"%s\" will be "
      "PERMANENTLY DELETED.  If you do not wish to \n"
      "see this message again, you can pass %s=True as a kwarg to the "
      "collectorsdb.reset() function.\n"
      "\n"
      "Are you sure you want to continue? " % (
        expectedAnswer, repoParams["db"], repoParams["host"],
        promptAvoidanceArgName))

    if answer.strip() != expectedAnswer:
      print "Aborting - Wise choice, my friend. Bye."
      return 1

  resetDatabaseSQL = (
    "DROP DATABASE IF EXISTS %(database)s; "
    "CREATE DATABASE %(database)s;" % {"database": repoParams["db"]})
  statements = [s.strip() for s in resetDatabaseSQL.split(";") if s.strip()]

  dsn = "mysql://%(user)s:%(password)s@%(host)s:%(port)s" % repoParams
  e = sqlalchemy.create_engine(dsn)
  try:
    for s in statements:
      e.execute(s)
  finally:
    e.dispose()

  migrate(offline=offline)

  return 0
