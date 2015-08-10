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

import YOMP

from YOMP import YOMP_logging
from YOMP.app import config
from YOMP.app.repository.migrate import migrate
from YOMP.app.repository.queries import (
    addAnnotation,
    addAutostack,
    addDeviceNotificationSettings,
    addMetric,
    addMetricData,
    addMetricToAutostack,
    addNotification,
    batchAcknowledgeNotifications,
    batchSeeNotifications,
    clearOldNotifications,
    deleteAnnotationById,
    deleteAutostack,
    deleteMetric,
    deleteModel,
    deleteStaleNotificationDevices,
    getAllNotificationSettings,
    getAnnotationById,
    getAnnotations,
    getAutostack,
    getAutostackList,
    getAutostackFromMetric,
    getAutostackForNameAndRegion,
    getAutostackMetrics,
    getAutostackMetricsWithMetricName,
    getAutostackMetricsPendingDataCollection,
    getCloudwatchMetrics,
    getCloudwatchMetricsForNameAndServer,
    getCloudwatchMetricsPendingDataCollection,
    getCustomMetricByName,
    getCustomMetrics,
    getDeviceNotificationSettings,
    getInstanceCount,
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
    getNotification,
    getUnprocessedModelDataCount,
    getUnseenNotificationList,
    listMetricIDsForInstance,
    saveMetricInstanceStatus,
    setMetricCollectorError,
    setMetricLastTimestamp,
    setMetricStatus,
    updateDeviceNotificationSettings,
    updateMetricColumns,
    updateMetricColumnsForRefStatus,
    updateMetricDataColumns,
    updateNotificationDeviceTimestamp,
    updateNotificationMessageId,
    lockOperationExclusive,
    OperationLock)
from htmengine.repository import _EngineSingleton


retryOnTransientErrors = sqlalchemy_utils.retryOnTransientErrors


DSN_FORMAT = "mysql://%(user)s:%(passwd)s@%(host)s:%(port)s"
DB_DSN_FORMAT = "mysql://%(user)s:%(passwd)s@%(host)s:%(port)s/%(db)s"



g_log = logging.getLogger("YOMP.repository")



def getBaseConnectionArgsDict():
  """Return a dictonary of common database connection arguments."""
  return {
    "host": config.get("repository", "host"),
    "port": config.getint("repository", "port"),
    "user": config.get("repository", "user"),
    "passwd": config.get("repository", "passwd"),
    "charset": "utf8",
    "use_unicode": True,
  }



def getDSN():
  return DSN_FORMAT % dict(config.items("repository"))



def getUnaffiliatedEngine():
  return create_engine(getDSN())



def getDbDSN():
  config.loadConfig()
  return DB_DSN_FORMAT % dict(config.items("repository"))



def engineFactory(reset=False):
  """SQLAlchemy engine factory method

  See http://docs.sqlalchemy.org/en/rel_0_9/core/connections.html

  :param reset: Force a new engine instance.  By default, the same instance is
    reused when possible.
  :returns: SQLAlchemy engine object
  :rtype: sqlalchemy.engine.Engine

  Usage::

      from YOMP.app import repository
      engine = repository.engineFactory()
  """
  if reset:
    _EngineSingleton.reset()

  return _EngineSingleton(getDbDSN(), pool_recycle=179, pool_size=0,
                          max_overflow=-1)



def reset(offline=False):
  """
  Reset the YOMP database; upon successful completion, the necessary schema are
  created, but the tables are not populated

  :param offline: False to execute SQL commands; True to just dump SQL commands
    to stdout for offline mode or debugging
  """
  # Make sure we have the latest version of configuration
  config.loadConfig()
  dbName = config.get('repository', 'db')

  resetDatabaseSQL = (
      "DROP DATABASE IF EXISTS %(database)s; "
      "CREATE DATABASE %(database)s;" % {"database": dbName})
  statements = resetDatabaseSQL.split(";")

  engine = getUnaffiliatedEngine()
  with engine.connect() as connection:
    for s in statements:
      if s.strip():
        connection.execute(s)

  migrate(offline=offline)
