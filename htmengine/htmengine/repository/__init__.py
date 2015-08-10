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
import os
import traceback

from sqlalchemy import create_engine

from nta.utils import sqlalchemy_utils

from htmengine.repository.queries import (
    addMetric,
    addMetricData,
    deleteMetric,
    deleteModel,
    getCustomMetricByName,
    getCustomMetrics,
    getInstances,
    getInstanceStatusHistory,
    getAllMetrics,
    getAllMetricsForServer,
    getAllModels,
    getMetric,
    getMetricWithSharedLock,
    getMetricWithUpdateLock,
    getMetricCountForServer,
    getMetricData,
    getMetricDataCount,
    getProcessedMetricDataCount,
    getMetricDataWithRawAnomalyScoresTail,
    getMetricIdsSortedByDisplayValue,
    getMetricStats,
    getUnprocessedModelDataCount,
    listMetricIDsForInstance,
    saveMetricInstanceStatus,
    setMetricCollectorError,
    setMetricLastTimestamp,
    setMetricStatus,
    updateMetricColumns,
    updateMetricColumnsForRefStatus,
    updateMetricDataColumns,
    lockOperationExclusive,
    OperationLock)


retryOnTransientErrors = sqlalchemy_utils.retryOnTransientErrors


DSN_FORMAT = "mysql://%(user)s:%(passwd)s@%(host)s:%(port)s"
DB_DSN_FORMAT = "mysql://%(user)s:%(passwd)s@%(host)s:%(port)s/%(db)s"




g_log = logging.getLogger("htmengine.repository")



def getBaseConnectionArgsDict(config):
  """Return a dictonary of common database connection arguments."""
  return {
    "host": config.get("repository", "host"),
    "port": config.getint("repository", "port"),
    "user": config.get("repository", "user"),
    "passwd": config.get("repository", "passwd"),
    "charset": "utf8",
    "use_unicode": True,
  }



class _EngineSingleton(object):

  _dsn = None
  _engine = None
  _pid = None

  def __new__(cls, dsn, *args, **kwargs):
    """ Construct a new SQLAlchemy engine, returning a known engine if one
    exists, keeping track of the dsn used to create it.  If the dsn changes,
    dispose of the connection pool and reassign to a new engine instance.
    """
    pid = os.getpid()

    if cls._pid is not None:
      if cls._pid != pid:
        checkedin = cls._engine.pool.checkedin()
        checkedout = cls._engine.pool.checkedout()
        g_log.info(
          "_EngineSingleton.__new__(): forked process inherited engine=%s: "
          "oldPid=%s, newPid=%s, pool.checkedin=%s, pool.checkedout=%s",
          cls._engine, cls._pid, pid, checkedin, checkedout)

        if checkedin != 0:
          g_log.error("_EngineSingleton.__new__(): non-zero inherited "
                      "engine.pool.checkedin=%s", checkedin)
        if checkedout != 0:
          g_log.error("_EngineSingleton.__new__(): non-zero inherited "
                      "engine.pool.checkedout=%s", checkedout)

    if not cls._engine or not cls._dsn or (cls._dsn and cls._dsn != dsn):
      if cls._engine:
        # cls._engine may be set already, but the dsn has changed
        cls._engine.dispose()
        cls._engine = None

      cls._engine = create_engine(dsn, *args, **kwargs)
      cls._dsn = dsn
      cls._pid = os.getpid()
      if g_log.isEnabledFor(logging.DEBUG):
        # NOTE: checking isEnabledFor first because we don't want to pay the
        # price for traceback.format_stack unless we're actually going to log it
        g_log.debug(
          "_EngineSingleton.__new__(): created new engine=%s: "
          "pid=%s, pool.checkedin=%s, pool.checkedout=%s, callerStack=%s",
          cls._engine,
          cls._pid,
          cls._engine.pool.checkedin(),
          cls._engine.pool.checkedout(),
          traceback.format_stack(limit=10))


    return cls._engine # Note: Returning an instance of an engine, as returned
                       # by create_engine() rather than an instance of
                       # _EngineSingleton

  @classmethod
  def reset(cls):
    if cls._engine:
      cls._engine.dispose() # Explicitly dispose of the connection pool before
                            # deleting.
    cls._dsn = None
    cls._engine = None
    cls._pid = None



def getDSN(config):
  return DSN_FORMAT % dict(config.items("repository"))



def getUnaffiliatedEngine(config):
  return create_engine(getDSN(config))



def getDbDSN(config):
  return DB_DSN_FORMAT % dict(config.items("repository"))



def engineFactory(config, reset=False):
  """SQLAlchemy engine factory method

  See http://docs.sqlalchemy.org/en/rel_0_9/core/connections.html

  :param reset: Force a new engine instance.  By default, the same instance is
    reused when possible.
  :returns: SQLAlchemy engine object
  :rtype: sqlalchemy.engine.Engine

  Usage::

      from htmengine import repository
      engine = repository.engineFactory()
  """
  if reset:
    _EngineSingleton.reset()

  return _EngineSingleton(getDbDSN(config), pool_recycle=179, pool_size=0,
                          max_overflow=-1)
