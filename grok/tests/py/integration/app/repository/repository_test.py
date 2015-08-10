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

# TODO: TAUR-412 Move into htmengine package (partial)

import datetime
import unittest
import uuid
from mock import Mock

import MySQLdb.constants
import sqlalchemy
from sqlalchemy import insert

from htmengine import exceptions
from YOMP.app import repository
from YOMP.app.repository import queries, schema
from htmengine.repository.queries import MetricStatus
from htmengine.utils import jsonDecode, jsonEncode
from YOMP.test_utils.app.sqlalchemy_test_utils import ManagedTempRepository



class TestRepositoryAPI(unittest.TestCase):
  def setUp(self):
    self.engine = repository.engineFactory()

  def _deleteObj(self, table, where):
    delete = table.delete().where(where)
    self.engine.execute(delete)


  def _addGenericAutostack(self, **kwargs):
    details = dict(uid=str(uuid.uuid4()),
                   name=" ".join(["Generic",
                                  self.__class__.__name__,
                                  str(id(self))]),
                   region="N/A")

    details.update(kwargs)

    insert = schema.autostack.insert().values(details) # pylint: disable=E1120
    self.engine.execute(insert)
    result = self.engine.execute(
      schema.autostack.select()
                      .where(schema.autostack.c.uid == details["uid"]))
    autostackObj = result.first()

    self.addCleanup(self._deleteObj,
                    schema.autostack,
                    schema.autostack.c.uid == details["uid"])

    return autostackObj


  def _addGenericMetric(self, engineOrConn=None, **kwargs):
    engineOrConn = engineOrConn if engineOrConn is not None else self.engine
    with engineOrConn.connect() as conn:
      details = dict(uid=str(uuid.uuid4()),
                     datasource="custom",
                     name=" ".join(["Generic",
                                    self.__class__.__name__,
                                    str(id(self))]),
                     last_rowid=0)

      details.update(kwargs)

      insert = schema.metric.insert().values(details) # pylint: disable=E1120
      conn.execute(insert)
      metricObj = repository.getMetric(conn, details["uid"])
      self.addCleanup(self._deleteObj,
                      schema.metric,
                      schema.metric.c.uid == metricObj.uid)

    return metricObj


  def _addAutostackMetric(self, **kwargs):
    return self._addGenericMetric(datasource="autostack", **kwargs)


  def _addGenericNotificationSettings(self):
    details = dict(uid=str(uuid.uuid4()),
                   windowsize=3600,
                   sensitivity=0.99999,
                   email_addr="")
    insert = schema.notification_settings.insert().values(details)
    self.engine.execute(insert)
    result = self.engine.execute(
      schema.notification_settings
      .select()
      .where(schema.notification_settings.c.uid == details["uid"]))

    settingObj = result.fetchone()

    self.addCleanup(self._deleteObj,
                    schema.notification_settings,
                    schema.notification_settings.c.uid == details["uid"])

    return settingObj


  def testengineFactoryReturnsEngine(self):
    self.assertIsInstance(self.engine, sqlalchemy.engine.Engine)

    engine = repository.engineFactory()

    self.assertIs(engine, self.engine)


  def testAddMetric(self):
    metricName = " ".join([__name__,
                           "testaddMetric",
                           str(uuid.uuid4())])
    with self.engine.connect() as conn:
      result = repository.addMetric(
        conn,
        name=metricName,
        description="Custom metric %s" % (metricName,),
        server="N/A",
        location="",
        poll_interval=300,
        status=queries.MetricStatus.UNMONITORED,
        datasource="custom")

    self.assertIn("uid", result)

    metricId = result["uid"]

    self.addCleanup(self._deleteObj,
                    schema.metric,
                    schema.metric.c.uid == metricId)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricId)

    self.assertEqual(metricObj.uid, metricId)
    self.assertEqual(metricObj.name, metricName)
    self.assertEqual(metricObj.poll_interval, 300)
    self.assertEqual(metricObj.datasource, "custom")


  def testdeleteMetric(self):
    metricObj = self._addGenericMetric()

    with self.engine.connect() as conn:
      result = repository.deleteMetric(conn, metricObj.uid)

    self.assertTrue(result.rowcount)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getMetric,
                        conn,
                        metricObj.uid)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.deleteMetric,
                        conn,
                        metricObj.uid)


  def testdeleteModel(self):
    metricObj = self._addGenericMetric(
      status=queries.MetricStatus.ACTIVE)

    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)

    self.engine.execute(
      schema.metric_data # pylint: disable=E1120
      .update()
      .values(anomaly_score=1,
              raw_anomaly_score=2,
              display_value=3)
      .where(schema.metric_data.c.uid == metricObj.uid))

    with self.engine.connect() as conn:
      repository.deleteModel(conn, metricObj.uid)
      metricObj = repository.getMetric(conn, metricObj.uid)

    self.assertEqual(metricObj.status, queries.MetricStatus.UNMONITORED)
    self.assertEqual(metricObj.model_params, None)
    self.assertEqual(metricObj.message, None)

    with self.engine.connect() as conn:
      metricDataObjs = repository.getMetricData(conn, metricObj.uid)

    self.assertTrue(all(metricDataRow.anomaly_score is None and
                        metricDataRow.raw_anomaly_score is None and
                        metricDataRow.display_value is None
                        for metricDataRow in metricDataObjs))


  def testGetCustomMetricByName(self):
    metricId = str(uuid.uuid4())

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getMetric, conn, metricId)

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      retrMetricObj = repository.getCustomMetricByName(conn,
                                                       metricObj.name)

    self.assertEqual(retrMetricObj.uid, metricObj.uid)
    self.assertEqual(retrMetricObj.name, metricObj.name)
    self.assertEqual(retrMetricObj.datasource, metricObj.datasource)
    self.assertEqual(retrMetricObj.last_rowid, metricObj.last_rowid)

    with self.engine.connect() as conn:
      retrMetricObj = repository.getCustomMetricByName(
        conn,
        metricObj.name,
        fields=[schema.metric.c.name])

    self.assertEqual(retrMetricObj.keys(), ["name"])
    self.assertEqual(retrMetricObj.name, metricObj.name)


  def testUpdateMetricColumns(self):
    metricObj = self._addGenericMetric()

    with self.engine.connect() as conn:
      repository.updateMetricColumns(
        conn,
        metricObj.uid,
        {"parameters": jsonEncode({"foo": "bar"})})

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn,
                                       metricObj.uid,
                                       fields=[schema.metric.c.parameters])

    self.assertEqual(metricObj.parameters,
                     jsonEncode({"foo": "bar"}))


  def testUpdateMetricColumnsForRefStatus(self):
    metricObj = self._addGenericMetric(status=queries.MetricStatus.ACTIVE)

    with self.engine.connect() as conn:
      repository.updateMetricColumnsForRefStatus(
        conn,
        metricObj.uid,
        metricObj.status,
        {"parameters": jsonEncode({"foo": "bar"})})

    with self.engine.connect() as conn:

      metricObj = repository.getMetric(
        conn,
        metricObj.uid,
        fields=[schema.metric.c.uid, schema.metric.c.parameters])

    self.assertEqual(metricObj.parameters,
                     jsonEncode({"foo": "bar"}))

    with self.engine.connect() as conn:
      repository.updateMetricColumnsForRefStatus(
        conn,
        metricObj.uid,
        queries.MetricStatus.UNMONITORED,
        {"parameters": jsonEncode({"foo": "bar"})})

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(
        conn,
        metricObj.uid,
        fields=[schema.metric.c.uid,
                schema.metric.c.parameters])

    self.assertEqual(metricObj.parameters,
                     jsonEncode({"foo": "bar"}))



  def testaddMetricData(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    data = [[0, now]]

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.addMetricData, conn, metricId, data)

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      rows = repository.addMetricData(conn, metricObj.uid, data)

    self.assertEqual(len(data), len(rows))

    insertedRow = rows[0]
    self.assertIn("uid", insertedRow)
    self.assertEqual(insertedRow["uid"], metricId)
    self.assertIn("rowid", insertedRow)
    self.assertEqual(insertedRow["rowid"], 1)
    self.assertIn("timestamp", insertedRow)
    self.assertEqual(insertedRow["timestamp"], now)
    self.assertIn("metric_value", insertedRow)
    self.assertEqual(insertedRow["metric_value"], 0)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricId)

    self.assertEqual(metricObj.last_rowid, 1)

    data = [[1, now + datetime.timedelta(minutes=5)],
            [2, now + datetime.timedelta(minutes=10)],
            [3, now + datetime.timedelta(minutes=15)]]

    with self.engine.connect() as conn:
      rows = repository.addMetricData(conn, metricObj.uid, data)

    self.assertEqual(len(data), len(rows))

    for index, insertedRow in enumerate(rows, 0):
      self.assertIn("uid", insertedRow)
      self.assertEqual(insertedRow["uid"], metricId)
      self.assertIn("rowid", insertedRow)
      self.assertEqual(insertedRow["rowid"], index+2)
      self.assertIn("timestamp", insertedRow)
      self.assertEqual(insertedRow["timestamp"], data[index][1])
      self.assertIn("metric_value", insertedRow)
      self.assertEqual(insertedRow["metric_value"], data[index][0])

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricId)

    self.assertEqual(metricObj.last_rowid, 4)


  def testaddNotification(self):
    metricObj = self._addGenericMetric()
    settingObj = self._addGenericNotificationSettings()

    notificationId = str(uuid.uuid4())
    notificationDict = dict(uid=notificationId,
                            server=metricObj.server,
                            metric=metricObj.uid,
                            device=settingObj.uid,
                            windowsize=settingObj.windowsize,
                            acknowledged=0,
                            seen=0,
                            timestamp=datetime.datetime.now(),
                            rowid=666)
    with self.engine.connect() as conn:
      result = repository.addNotification(conn, **notificationDict)

    self.assertIsInstance(result, sqlalchemy.engine.result.ResultProxy)
    self.assertTrue(hasattr(result, "rowcount"))
    self.assertEqual(result.rowcount, 1)

    # Attempt to add the same notification and assert that it returns None
    notificationDict["uid"] = notificationId
    with self.engine.connect() as conn:
      result = repository.addNotification(conn, **notificationDict)

    self.assertFalse(result)

  def testClearOldNotifications(self):
    metricObj = self._addGenericMetric()
    settingObj = self._addGenericNotificationSettings()


    def addNotification():
      notificationId = str(uuid.uuid4())
      notificationDict = dict(uid=notificationId,
                              server=metricObj.server,
                              metric=metricObj.uid,
                              device=settingObj.uid,
                              windowsize=settingObj.windowsize,
                              acknowledged=0,
                              seen=0,
                              timestamp=datetime.datetime.now(),
                              rowid=666)

      with self.engine.connect() as conn:
        repository.addNotification(conn, **notificationDict)

      return notificationId


    def updateNotification(notificationId):
      earlier = datetime.datetime.now() - datetime.timedelta(days=31)

      self.engine.execute(schema.notification
                          .update()
                          .where(schema.notification.c.uid == notificationId)
                          .values(timestamp=earlier))


    notificationId = addNotification()
    updateNotification(notificationId)

    with self.engine.connect() as conn:
      repository.clearOldNotifications(conn)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getNotification, conn, notificationId)

    recentNotificationId = addNotification()
    expiredNotificationId = addNotification()
    updateNotification(expiredNotificationId)

    with self.engine.connect() as conn:
      repository.clearOldNotifications(conn)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getNotification,
                        conn,
                        expiredNotificationId)

    with self.engine.connect() as conn:
      recentNotification = repository.getNotification(conn,
                                                      recentNotificationId)

    self.assertEqual(recentNotificationId, recentNotification.uid)


  def testGetAllNotificationSettings(self):
    self._addGenericNotificationSettings()

    with self.engine.connect() as conn:
      settingsList = repository.getAllNotificationSettings(conn)

    self.assertIsInstance(settingsList, list)
    for settingObj in settingsList:
      self.assertTrue(hasattr(settingObj, "sensitivity"))
      self.assertTrue(hasattr(settingObj, "uid"))
      self.assertTrue(hasattr(settingObj, "windowsize"))
      self.assertTrue(hasattr(settingObj, "email_addr"))

    self._addGenericNotificationSettings()

    with self.engine.connect() as conn:
      settingsList = repository.getAllNotificationSettings(conn)

    self.assertIsInstance(settingsList, list)
    for settingObj in settingsList:
      self.assertTrue(hasattr(settingObj, "sensitivity"))
      self.assertTrue(hasattr(settingObj, "uid"))
      self.assertTrue(hasattr(settingObj, "windowsize"))
      self.assertTrue(hasattr(settingObj, "email_addr"))


  def testgetAutostackFromMetric1(self):
    autostackObj = self._addGenericAutostack()
    metricObj = self._addAutostackMetric()

    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj.uid)

      retrAutostackObj = repository.getAutostackFromMetric(conn,
                                                           metricObj.uid)

    self.assertEqual(autostackObj.uid, retrAutostackObj.uid)
    self.assertEqual(autostackObj.name, retrAutostackObj.name)
    self.assertEqual(autostackObj.region, retrAutostackObj.region)


  def testgetAutostackFromMetric2(self):
    autostackObj = self._addGenericAutostack()

    with self.engine.connect() as conn:
      retrAutostackObj = repository.getAutostack(conn, autostackObj.uid)

    self.assertEqual(autostackObj.uid, retrAutostackObj.uid)
    self.assertEqual(autostackObj.name, retrAutostackObj.name)
    self.assertEqual(autostackObj.region, retrAutostackObj.region)


  def testgetAutostackMetricsPendingDataCollection(self):
    autostackObj = self._addGenericAutostack(filters="[]")
    metricObj = self._addAutostackMetric()

    insert = (schema.metric_set # pylint: disable=E1120
              .insert()
              .values(metric=metricObj.uid,
                      autostack=autostackObj.uid))
    self.engine.execute(insert)

    update = (schema.metric # pylint: disable=E1120
              .update()
              .values(status=MetricStatus.ACTIVE,
                      last_timestamp=None)
              .where(schema.metric.c.uid == metricObj.uid))
    self.engine.execute(update)
    with self.engine.connect() as conn:
      result = repository.getAutostackMetricsPendingDataCollection(conn)

    self.assertTrue(result)

    for (autostack, metrics) in result:
      self.assertEqual(autostack.uid, autostackObj.uid)
      self.assertEqual(len(metrics), 1)
      self.assertEqual(metrics[0].uid, metricObj.uid)


  def testgetCloudwatchMetrics(self):
    self._addGenericMetric(datasource="cloudwatch")

    with self.engine.connect() as conn:
      metrics = repository.getCloudwatchMetrics(conn)

    for retrMetricObj in metrics:
      self.assertEqual(retrMetricObj.datasource, "cloudwatch")


  def testGetCloudwatchMetricsForNameAndServer(self):
    metricObj = self._addGenericMetric(datasource="cloudwatch")

    with self.engine.connect() as conn:
      metrics = repository.getCloudwatchMetricsForNameAndServer(
        conn,
        metricObj.name,
        metricObj.server)
    self.assertEqual(len(metrics), 1)
    self.assertEqual(metrics[0].datasource, metricObj.datasource)


  def testgetCloudwatchMetricsPendingDataCollection(self):
    metricObj = self._addGenericMetric(datasource="cloudwatch")

    update = (schema.metric # pylint: disable=E1120
              .update()
              .values(status=MetricStatus.ACTIVE,
                      last_timestamp=None)
              .where(schema.metric.c.uid == metricObj.uid))
    self.engine.execute(update)
    with self.engine.connect() as conn:
      metrics = repository.getCloudwatchMetricsPendingDataCollection(conn)

    self.assertTrue(metrics)
    for metricObj in metrics:
      self.assertTrue(hasattr(metricObj, "uid"))
      self.assertEqual(metricObj.datasource, "cloudwatch")


  def testgetCustomMetrics(self):
    self._addGenericMetric()

    with self.engine.connect() as conn:
      metrics = repository.getCustomMetrics(conn)

    for retrMetricObj in metrics:
      self.assertEqual(retrMetricObj.datasource, "custom")


  def _testGetMetricSimple(self, getMetric, engineOrConn):
    metricId = str(uuid.uuid4())

    self.assertRaises(exceptions.ObjectNotFoundError,
                      getMetric, engineOrConn, metricId)

    metricObj = self._addGenericMetric(engineOrConn, uid=metricId)

    with engineOrConn.connect() as conn:
      retrMetricObj = getMetric(conn, metricId)

    self.assertEqual(retrMetricObj.uid, metricObj.uid)
    self.assertEqual(retrMetricObj.name, metricObj.name)
    self.assertEqual(retrMetricObj.datasource, metricObj.datasource)
    self.assertEqual(retrMetricObj.last_rowid, metricObj.last_rowid)

    with engineOrConn.connect() as conn:
      retrMetricObj = getMetric(conn,
                                metricId,
                                fields=[schema.metric.c.name])

    self.assertEqual(retrMetricObj.keys(), ["name"])
    self.assertEqual(retrMetricObj.name, metricObj.name)


  def testGetMetric(self):
    self._testGetMetricSimple(repository.getMetric, self.engine)
    with self.engine.connect() as conn:
      self._testGetMetricSimple(repository.getMetric, conn)


  def testGetMetricWithSharedLock(self):
    engine = self.engine

    with engine.connect() as conn:
      self._testGetMetricSimple(repository.getMetricWithSharedLock, conn)
    del conn

    metricId = str(uuid.uuid4())
    metricObj = self._addGenericMetric(engine, uid=metricId)
    self.assertNotEqual(metricObj, "www")

    with engine.connect() as conn1, engine.connect() as conn2:
      # Retreive metric on conn1 and check datasource
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      # Change datasource to "www" using a seperate connection
      with engine.connect() as conn:
        with conn.begin():
          r = repository.updateMetricColumns(conn, metricId,
                                             dict(datasource="www"))
          self.assertEqual(r.rowcount, 1)
      del conn

      conn1.begin()
      # Verify that conn1 sees the old datasource
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      # Obtain a fresh version of metric on conn1 via SHARE MODE lock
      obj1 = repository.getMetricWithSharedLock(conn1, metricId)
      self.assertEqual(obj1.datasource, "www")
      self.assertNotEqual(obj1.datasource, metricObj.datasource)

      # But without SHARE MODE lock, conn1 still sees the old metric
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      conn2.begin()
      # SELECT ... LOCK IN SHARE MODE on a second connection should not block
      obj2 = repository.getMetricWithSharedLock(conn2, metricId)
      self.assertEqual(obj2.datasource, "www")

      # Verify that SELECT ... FOR UPDATE will block while SHARE MODE lock(s)
      # are outstanding
      with engine.connect() as conn:
        try:
          try:
            conn.execute("set innodb_lock_wait_timeout=2")
          except sqlalchemy.exc.OperationalError as e:
            # innodb_lock_wait_timeout is dynamic for innodb plugins, but not
            # with native innodb (e.g., on Linux)
            if (e.orig.args[0] !=
                MySQLdb.constants.ER.INCORRECT_GLOBAL_LOCAL_VAR):
              raise
          with self.assertRaises(sqlalchemy.exc.OperationalError) as cm:
            repository.getMetricWithUpdateLock(conn, metricId)
          self.assertEqual(cm.exception.orig.args[0],
                           MySQLdb.constants.ER.LOCK_WAIT_TIMEOUT)
        finally:
          conn.invalidate()
      del conn


  def testGetMetricWithUpdateLock(self):
    engine = self.engine

    with engine.connect() as conn:
      self._testGetMetricSimple(repository.getMetricWithUpdateLock, conn)
    del conn

    metricId = str(uuid.uuid4())
    metricObj = self._addGenericMetric(engine, uid=metricId)
    self.assertNotEqual(metricObj, "www")

    with engine.connect() as conn1, engine.connect() as conn2:
      # Retreive metric on conn1 and check datasource
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      # Change datasource to "www" using a seperate connection
      with engine.connect() as conn:
        with conn.begin():
          r = repository.updateMetricColumns(conn, metricId,
                                             dict(datasource="www"))
          self.assertEqual(r.rowcount, 1)
      del conn

      conn1.begin()
      # Verify that conn1 sees the old datasource
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      # Obtain a fresh version of metric on conn1 via FOR UPDATE lock
      obj1 = repository.getMetricWithUpdateLock(conn1, metricId)
      self.assertEqual(obj1.datasource, "www")
      self.assertNotEqual(obj1.datasource, metricObj.datasource)

      # But without FOR UPDATE lock, conn1 still sees the old metric
      obj1 = repository.getMetric(conn1, metricId)
      self.assertEqual(obj1.datasource, metricObj.datasource)

      conn2.begin()
      # Verify that another SELECT ... FOR UPDATE on a different connection
      # would block
      try:
        try:
          conn2.execute("set innodb_lock_wait_timeout=1")
        except sqlalchemy.exc.OperationalError as e:
          # innodb_lock_wait_timeout is dynamic for innodb plugins, but not
          # with native innodb (e.g., on Linux)
          if (e.orig.args[0] !=
              MySQLdb.constants.ER.INCORRECT_GLOBAL_LOCAL_VAR):
            raise
        with self.assertRaises(sqlalchemy.exc.OperationalError) as cm:
          repository.getMetricWithUpdateLock(conn2, metricId)
        self.assertEqual(cm.exception.orig.args[0],
                         MySQLdb.constants.ER.LOCK_WAIT_TIMEOUT)
      finally:
        conn2.invalidate()


  def testgetMetricData(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)
      retrData = repository.getMetricData(conn, metricId)

    for index, retrRow in enumerate(retrData):
      self.assertEqual(metricId, retrRow.uid)
      self.assertEqual(index, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrData = repository.getMetricData(
        conn,
        metricId,
        fields=[schema.metric_data.c.metric_value,
                schema.metric_data.c.timestamp])

    for index, retrRow in enumerate(retrData):
      self.assertEqual(retrRow.keys(), ["metric_value", "timestamp"])
      self.assertEqual(data[index][1], retrRow.timestamp)
      self.assertEqual(index, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrData = repository.getMetricData(conn, metricId, rowid=12)
      retrRow = retrData.first()

    self.assertEqual(12, retrRow.rowid)
    self.assertEqual(data[11][1], retrRow.timestamp)
    self.assertEqual(11, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrData = repository.getMetricData(conn, metricId, start=2)
      retrRow = retrData.fetchone()

    self.assertEqual(2, retrRow.rowid)
    self.assertEqual(data[1][1], retrRow.timestamp)
    self.assertEqual(1, retrRow.metric_value)

    for retrRow in retrData:
      pass # Iterate until end of cursor

    self.assertEqual(12, retrRow.rowid)
    self.assertEqual(data[11][1], retrRow.timestamp)
    self.assertEqual(11, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrData = repository.getMetricData(conn, metricId, start=2, stop=3)

    retrRow = retrData.fetchone()

    self.assertEqual(2, retrRow.rowid)
    self.assertEqual(data[1][1], retrRow.timestamp)
    self.assertEqual(1, retrRow.metric_value)

    retrRow = retrData.fetchone()

    self.assertEqual(3, retrRow.rowid)
    self.assertEqual(data[2][1], retrRow.timestamp)
    self.assertEqual(2, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrData = repository.getMetricData(conn, metricId, start=2, limit=1)

    retrRow = retrData.fetchone()

    self.assertEqual(2, retrRow.rowid)
    self.assertEqual(data[1][1], retrRow.timestamp)
    self.assertEqual(1, retrRow.metric_value)


  def testGetMetricDataCount(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      self.assertEqual(
        repository.getMetricDataCount(conn, metricObj.uid),
        0)

      repository.addMetricData(conn, metricObj.uid, data)

      self.assertEqual(
        repository.getMetricDataCount(conn, metricObj.uid),
        12)

      conn.execute(schema.metric_data # pylint: disable=E1120
                   .update()
                   .values(raw_anomaly_score=0)
                   .where(schema.metric_data.c.uid == metricObj.uid)
                   .where((schema.metric_data.c.rowid%2) == 0))

      self.assertEqual(
        repository.getMetricDataCount(conn, metricObj.uid),
        12)


  def testGetProcessedMetricDataCount(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      self.assertEqual(
        repository.getProcessedMetricDataCount(conn, metricObj.uid),
        0)

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)

    with self.engine.connect() as conn:
      self.assertEqual(
        repository.getProcessedMetricDataCount(conn, metricObj.uid),
        0)

    self.engine.execute(schema.metric_data # pylint: disable=E1120
                        .update()
                        .values(raw_anomaly_score=0)
                        .where(schema.metric_data.c.uid == metricObj.uid)
                        .where((schema.metric_data.c.rowid%2) == 0))

    with self.engine.connect() as conn:
      self.assertEqual(
        repository.getProcessedMetricDataCount(conn, metricObj.uid),
        6)

    self.engine.execute(schema.metric_data # pylint: disable=E1120
                        .update()
                        .values(raw_anomaly_score=0)
                        .where(schema.metric_data.c.uid == metricObj.uid)
                        .where((schema.metric_data.c.rowid%2) == 1))

    with self.engine.connect() as conn:
      self.assertEqual(
        repository.getProcessedMetricDataCount(conn, metricObj.uid),
        12)


  def testGetMetricDataWithRawAnomalyScoresTail(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)

    self.engine.execute(schema.metric_data # pylint: disable=E1120
                        .update()
                        .values(raw_anomaly_score=0)
                        .where(schema.metric_data.c.uid == metricObj.uid))

    with self.engine.connect() as conn:
      retrMetricData = repository.getMetricDataWithRawAnomalyScoresTail(
        conn,
        metricId,
        12)

    for index, retrRow in enumerate(reversed(retrMetricData)):
      self.assertEqual(metricId, retrRow.uid)
      self.assertEqual(index, retrRow.metric_value)

    with self.engine.connect() as conn:
      retrMetricData = repository.getMetricDataWithRawAnomalyScoresTail(
        conn,
        metricId,
        1)

    retrRow = retrMetricData[0]
    self.assertEqual(metricId, retrRow.uid)
    self.assertEqual(11, retrRow.metric_value)


  def testGetMetricStats(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.MetricStatisticsNotReadyError,
                        repository.getMetricStats,
                        conn,
                        metricId)

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)

    with self.engine.connect() as conn:
      stats = repository.getMetricStats(conn, metricId)

    self.assertIn("min", stats)
    self.assertEqual(stats["min"], 0)
    self.assertIn("max", stats)
    self.assertEqual(stats["max"], 11)


  def testGetNotification(self):
    metricObj = self._addGenericMetric()
    settingObj = self._addGenericNotificationSettings()

    notificationId = str(uuid.uuid4())
    notificationDict = dict(uid=notificationId,
                            server=metricObj.server,
                            metric=metricObj.uid,
                            device=settingObj.uid,
                            windowsize=settingObj.windowsize,
                            acknowledged=0,
                            seen=0,
                            timestamp=datetime.datetime.now(),
                            rowid=666)
    with self.engine.connect() as conn:
      repository.addNotification(conn, **notificationDict)

    with self.engine.connect() as conn:
      retrNotification = repository.getNotification(conn, notificationId)

    self.assertEqual(notificationId, retrNotification.uid)
    self.assertEqual(settingObj.uid, retrNotification.device)
    self.assertEqual(settingObj.windowsize, retrNotification.windowsize)
    self.assertEqual(metricObj.uid, retrNotification.metric)


  def testsaveMetricInstanceStatus(self):
    now = datetime.datetime.utcnow()
    metricObj = self._addGenericMetric(server=str(uuid.uuid4()))

    with self.engine.connect() as conn:
      repository.saveMetricInstanceStatus(conn,
                                          metricObj.server,
                                          "foo",
                                          now - datetime.timedelta(minutes=10))

    def _delete():

      schema.instance_status_history.delete().where( # pylint: disable=E1120
        schema.instance_status_history.c.server == metricObj.server)

    self.addCleanup(_delete)

    def getLastStatus():
      result = self.engine.execute(
        schema.instance_status_history
        .select(order_by=schema.instance_status_history.c.timestamp.desc())
        .where(schema.instance_status_history.c.server == metricObj.server))

      return result.first()

    lastStatus = getLastStatus()
    originalTimestamp = lastStatus.timestamp

    self.assertEqual("foo", lastStatus.status)

    with self.engine.connect() as conn:
      repository.saveMetricInstanceStatus(conn,
                                          metricObj.server,
                                          "foo",
                                          now - datetime.timedelta(minutes=5))

    lastStatus = getLastStatus()
    self.assertEqual("foo", lastStatus.status)
    self.assertEqual(originalTimestamp, lastStatus.timestamp)

    with self.engine.connect() as conn:
      repository.saveMetricInstanceStatus(conn, metricObj.server, "bar")

    lastStatus = getLastStatus()
    self.assertEqual("bar", lastStatus.status)
    self.assertNotEqual(originalTimestamp, lastStatus.timestamp)


  def testSetMetricCollectorError(self):
    metricId = str(uuid.uuid4())
    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.setMetricCollectorError,
                        conn,
                        metricId,
                        "ERROR!")

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.setMetricCollectorError(conn, metricObj.uid, "ERROR!")

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricObj.uid)

    self.assertEqual(metricObj.collector_error, "ERROR!")


  def testSetMetricLastTimestamp(self):
    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)

    metricId = str(uuid.uuid4())

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.setMetricLastTimestamp,
                        conn,
                        metricId,
                        now)

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.setMetricLastTimestamp(conn, metricObj.uid, now)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricObj.uid)

    self.assertEqual(metricObj.last_timestamp, now)


  def testSetMetricStatusWithObjectNotFound(self):
    metricId = str(uuid.uuid4())

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.setMetricStatus,
                        conn,
                        metricId,
                        queries.MetricStatus.ERROR)
  

  def testSetMetricStatusToError(self):
    metricId = str(uuid.uuid4())

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.setMetricStatus(conn,
                                 metricObj.uid,
                                 queries.MetricStatus.ERROR)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricObj.uid)

    self.assertEqual(metricObj.status, queries.MetricStatus.ERROR)
    self.assertIsNone(metricObj.message)


  def testSetMetricStatusToErrorWithMessage(self):
    metricId = str(uuid.uuid4())
    errorMessage = "Something wicked this way comes"

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.setMetricStatus(conn,
                                 metricObj.uid,
                                 queries.MetricStatus.ERROR,
                                 errorMessage)

    with self.engine.connect() as conn:
      metricObj = repository.getMetric(conn, metricObj.uid)

    self.assertEqual(metricObj.status, queries.MetricStatus.ERROR)
    self.assertEqual(metricObj.message, errorMessage)


  def testUpdateMetricDataColumns(self):
    metricId = str(uuid.uuid4())
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0) # truncate microseconds
    data = [[0, now - datetime.timedelta(minutes=60)],
            [1, now - datetime.timedelta(minutes=55)],
            [2, now - datetime.timedelta(minutes=50)],
            [3, now - datetime.timedelta(minutes=45)],
            [4, now - datetime.timedelta(minutes=40)],
            [5, now - datetime.timedelta(minutes=35)],
            [6, now - datetime.timedelta(minutes=30)],
            [7, now - datetime.timedelta(minutes=25)],
            [8, now - datetime.timedelta(minutes=20)],
            [9, now - datetime.timedelta(minutes=15)],
            [10, now - datetime.timedelta(minutes=10)],
            [11, now - datetime.timedelta(minutes=5)]]

    metricObj = self._addGenericMetric(uid=metricId)

    with self.engine.connect() as conn:
      repository.addMetricData(conn, metricObj.uid, data)

    fields = {"raw_anomaly_score": 1, "anomaly_score": 2, "display_value": 3}

    with self.engine.connect() as conn:
      metricData = repository.getMetricData(conn, metricObj.uid, rowid=1)

    with self.engine.connect() as conn:
      repository.updateMetricDataColumns(conn, metricData.first(), fields)

    with self.engine.connect() as conn:
      metricData = repository.getMetricData(conn, metricObj.uid, rowid=1)

    metricDataRow = metricData.first()

    self.assertEqual(metricDataRow.raw_anomaly_score, 1)
    self.assertEqual(metricDataRow.anomaly_score, 2)
    self.assertEqual(metricDataRow.display_value, 3)


  def testUpdateNotificationMessageId(self):
    metricObj = self._addGenericMetric()
    settingObj = self._addGenericNotificationSettings()

    notificationId = str(uuid.uuid4())
    notificationDict = dict(uid=notificationId,
                            server=metricObj.server,
                            metric=metricObj.uid,
                            device=settingObj.uid,
                            windowsize=settingObj.windowsize,
                            acknowledged=0,
                            seen=0,
                            timestamp=datetime.datetime.now(),
                            rowid=666)
    with self.engine.connect() as conn:
      repository.addNotification(conn, **notificationDict)

    messageId = str(uuid.uuid4())

    with self.engine.connect() as conn:
      repository.updateNotificationMessageId(conn,
                                             notificationId,
                                             messageId)

    with self.engine.connect() as conn:
      notificationObj = repository.getNotification(conn, notificationId)

    self.assertEqual(messageId, notificationObj.ses_message_id)


  def testaddAutostack(self):
    filters = {"tag:Name":["*test*", "*YOMP*"],
               "tag:Description":["Blah", "foo"]}
    with self.engine.connect() as conn:
      autostackDict = repository.addAutostack(conn,
                                              name="test autostack",
                                              region="bogus",
                                              filters=jsonEncode(filters))
    self.assertIn("uid", autostackDict)

    self.addCleanup(self._deleteObj,
                    schema.autostack,
                    schema.autostack.c.uid == autostackDict["uid"])


  def testDeleteAutostack(self):
    metricObj = self._addAutostackMetric()
    filters = {"tag:Name":["*test*", "*YOMP*"],
               "tag:Description":["Blah", "foo"]}
    with self.engine.connect() as conn:
      autostackDict = repository.addAutostack(conn,
                                              name="test autostack",
                                              region="bogus",
                                              filters=jsonEncode(filters))
    autostackId = autostackDict["uid"]
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackId,
                                      metricObj.uid)

    with self.engine.connect() as conn:
      repository.deleteAutostack(conn, autostackId)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getAutostack,
                        conn,
                        autostackId)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.deleteAutostack,
                        conn,
                        autostackId)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getMetric,
                        conn,
                        metricObj.uid)



  def testgetAutostackForNameAndRegion(self):
    autostackObj = self._addGenericAutostack()
    metricObj = self._addAutostackMetric()
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj.uid)

    with self.engine.connect() as conn:
      retrAutostackObj = repository.getAutostackForNameAndRegion(
                           conn,
                           autostackObj.name,
                           autostackObj.region)

    self.assertEqual(autostackObj.uid, retrAutostackObj.uid)
    self.assertEqual(autostackObj.name, retrAutostackObj.name)
    self.assertEqual(autostackObj.region, retrAutostackObj.region)

    with self.engine.connect() as conn:
      repository.deleteAutostack(conn, autostackObj.uid)

    with self.engine.connect() as conn:
      self.assertRaises(exceptions.ObjectNotFoundError,
                        repository.getAutostackForNameAndRegion,
                        conn,
                        autostackObj.name,
                        autostackObj.region)


  def testGetAutostackMetrics(self):
    autostackObj = self._addGenericAutostack()
    metricObj1 = self._addAutostackMetric()
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj1.uid)
    metricObj2 = self._addAutostackMetric()
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj2.uid)
    metricObj3 = self._addAutostackMetric()
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj3.uid)

    with self.engine.connect() as conn:
      metrics = (
        [metricObj
         for metricObj in repository.getAutostackMetrics(conn,
                                                         autostackObj.uid)])

    self.assertEqual(len(metrics), 3)

    foundMetrics = set([metric.uid for metric in metrics])

    self.assertTrue(metricObj1.uid in foundMetrics)
    self.assertTrue(metricObj2.uid in foundMetrics)
    self.assertTrue(metricObj3.uid in foundMetrics)


  def testGetAutostackMetricsWithMetricName(self):
    autostackObj = self._addGenericAutostack()

    metricObj1 = self._addAutostackMetric(name="name1", server="MyServer")
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj1.uid)
    metricObj2 = self._addAutostackMetric(name="name2", server="MyServer")
    with self.engine.connect() as conn:
      repository.addMetricToAutostack(conn,
                                      autostackObj.uid,
                                      metricObj2.uid)

    with self.engine.connect() as conn:
      metrics = (
        [metricObj
         for metricObj in repository.getAutostackMetricsWithMetricName(
                                       conn,
                                       autostackObj.uid,
                                       metricObj1.name)])
    self.assertEqual(len(metrics), 1)

    self.assertEqual(metrics[0].uid, metricObj1.uid)



class TestAnomalyQueries(unittest.TestCase):

  def setUp(self):
    # The server needs this when adding metrics (mysql foreign key check)
    self.cwMetric1 = Mock(uid="abc",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/Metric1",
                          location="Somewhere",
                          parameters=jsonEncode({"region":"Somewhere"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolMetric",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric1.name = "AWS/Metric1"

    self.cwMetric2 = Mock(uid="abd",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/Metric2",
                          location="Somewhere",
                          parameters=jsonEncode({"region":"Somewhere"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolMetric",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric2.name = "AWS/Metric2"


  @ManagedTempRepository("AnomalyQueryTests")
  def testGetAllMetricsListSingleMetric(self):
    engine = repository.engineFactory()

    # Add metric
    ins = (schema.metric
           .insert()
           .values(dict([col.name, getattr(self.cwMetric1, col.name)]
                        for col in schema.metric.columns)))
    engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getAllMetrics(conn).fetchall()

    self.assertIsInstance(testResult, list)
    for row in testResult:
      self.assertIsInstance(row, sqlalchemy.engine.result.RowProxy)
      for col in schema.metric.columns:
        self.assertIn(col.name, row.keys())
        self.assertEqual(getattr(row, col.name),
                         getattr(self.cwMetric1, col.name))


  @ManagedTempRepository("AnomalyQueryTests")
  def testGetAllMetricsListMultipleMetric(self):
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric2]

    for metric in metricList:
      ins = (metric.insert()
             .values(dict([col.name, getattr(metric, col.name)]
                          for col in schema.metric.columns)))
      engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getAllMetrics(conn).fetchall()

    self.assertIsInstance(testResult, list)
    for row in testResult:
      self.assertIsInstance(row, sqlalchemy.engine.result.RowProxy)
      metric = next(m for m in metricList if m.uid == row.uid)
      for col in metric.columns:
        self.assertIn(col.name, row.keys())
        self.assertEqual(getattr(row, col.name), getattr(metric, col.name))


  @ManagedTempRepository("AnomalyQueryTests")
  def testGetAllMetricsListNoMetric(self):
    engine = repository.engineFactory()

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getAllMetrics(conn).fetchall()
    self.assertIsInstance(testResult, list)
    self.assertEqual(len(testResult), 0)


class TestInstanceQueries(unittest.TestCase):

  def setUp(self):
    # The server needs this  when adding metrics (foreign check)
    self.cwMetric1 = Mock(uid="abc",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/EC2/Instance1",
                          location="Somewhere",
                          parameters=jsonEncode(
                            {"region":"Somewhere", "InstanceId":"Instance1"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolInstance1",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric1.name = "AWS/EC2/Metric1"

    self.cwMetric2 = Mock(uid="abd",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/EC2/Instance1",
                          location="Somewhere",
                          parameters=jsonEncode(
                            {"region":"Somewhere", "InstanceId":"Instance1"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolInstance1",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric2.name = "AWS/EC2/Metric2"

    self.cwMetric3 = Mock(uid="abe",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/EC2/Instance2",
                          location="Somewhere",
                          parameters=jsonEncode(
                            {"region":"Somewhere", "InstanceId":"Instance2"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolInstance2",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric3.name = "AWS/EC2/Metric1"

    self.cwMetric4 = Mock(uid="abf",
                          datasource="cloudwatch",
                          description="A typical cloudwatch metric",
                          server="Somewhere/AWS/EC2/Instance2",
                          location="Somewhere",
                          parameters=jsonEncode(
                            {"region":"Somewhere", "InstanceId":"Instance2"}),
                          status=MetricStatus.ACTIVE,
                          message=None,
                          collector_error=None,
                          last_timestamp=
                            datetime.datetime.utcnow().replace(microsecond=0),
                          poll_interval=300,
                          tag_name="CoolInstance2",
                          model_params=None,
                          last_rowid=1000)
    self.cwMetric4.name = "AWS/EC2/Metric2"


  @staticmethod
  def instanceFromMetric(m):
    instance = {"status":m.status,
                "name":m.tag_name,
                "parameters":jsonDecode(m.parameters),
                "namespace":(m.name[0:m.name.index('/', m.name.index('/')+1)]),
                "server":m.server,
                "location":m.location,
                "message":m.message or ""}
    return instance


  @ManagedTempRepository("InstanceQueryTests")
  def testGetInstanceListSingleInstanceSingleMetric(self):
    engine = repository.engineFactory()

    # Add metric
    ins = (insert(schema.metric)
           .values(dict([col.name, getattr(self.cwMetric1, col.name)]
                        for col in schema.metric.columns)))
    engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getInstances(conn)

    instanceList = [self.instanceFromMetric(self.cwMetric1)]
    self.assertEqual(testResult, instanceList)


  @ManagedTempRepository("InstanceQueryTests")
  def testGetInstanceListSingleInstanceMultMetric(self):
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric2]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getInstances(conn)

    instanceList = [self.instanceFromMetric(self.cwMetric1)]
    self.assertEqual(testResult, instanceList)


  @ManagedTempRepository("InstanceQueryTests")
  def testGetInstanceListMultInstanceSingleMetric(self):
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric3]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getInstances(conn)

    instanceList = [self.instanceFromMetric(metric) for metric in metricList]
    self.assertEqual(testResult, instanceList)


  @ManagedTempRepository("InstanceQueryTests")
  def testGetInstanceListMultInstanceMultMetric(self):
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric2,
                  self.cwMetric3, self.cwMetric4]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getInstances(conn)

    instanceList = [self.instanceFromMetric(self.cwMetric1),
                    self.instanceFromMetric(self.cwMetric3)]
    self.assertEqual(testResult, instanceList)


  @ManagedTempRepository("InstanceQueryTests")
  def testGetInstanceListNoInstance(self):
    engine = repository.engineFactory()

    # Call the function
    with engine.connect() as conn:
      testResult = repository.getInstances(conn)
    self.assertIsInstance(testResult, list)
    self.assertEqual(len(testResult), 0)


  @ManagedTempRepository("InstanceQueryTests")
  def testListMetricIDsSingleInstanceSingleMetric(self):
    # =============== Setup ===========
    engine = repository.engineFactory()

    # Add metric
    ins = (insert(schema.metric)
           .values(dict([col.name, getattr(self.cwMetric1, col.name)]
                        for col in schema.metric.columns)))
    engine.execute(ins)

    # =============== Test the function ====================
    with engine.connect() as conn:
      testResult = repository.listMetricIDsForInstance(
        conn, self.cwMetric1.server)

    metricIDList = [self.cwMetric1.uid]
    self.assertEqual(testResult, metricIDList)


  @ManagedTempRepository("InstanceQueryTests")
  def testListMetricIDsSingleInstanceMultMetric(self):
    # =============== Setup ===========
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric2]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # =============== Test the function ====================
    with engine.connect() as conn:
      testResult = repository.listMetricIDsForInstance(
        conn, self.cwMetric1.server)

    metricIDList = [self.cwMetric1.uid,
                    self.cwMetric2.uid]
    self.assertEqual(testResult, metricIDList)


  @ManagedTempRepository("InstanceQueryTests")
  def testListMetricIDsMultInstanceSingleMetric(self):
    # =============== Setup ===========
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric3]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # =============== Test the function ====================
    with engine.connect() as conn:
      testResultInstance1 = repository.listMetricIDsForInstance(
        conn, self.cwMetric1.server)
      testResultInstance2 = repository.listMetricIDsForInstance(
        conn, self.cwMetric3.server)

    metricIDListInstance1 = [self.cwMetric1.uid]
    metricIDListInstance2 = [self.cwMetric3.uid]
    self.assertEqual(testResultInstance1, metricIDListInstance1)
    self.assertEqual(testResultInstance2, metricIDListInstance2)


  @ManagedTempRepository("InstanceQueryTests")
  def testListMetricIDsMultInstanceMultMetric(self):
    # =============== Setup ===========
    engine = repository.engineFactory()

    # Add metrics
    metricList = [self.cwMetric1, self.cwMetric2,
                  self.cwMetric3, self.cwMetric4]
    for metric in metricList:
      ins = (insert(schema.metric)
             .values(dict([col.name, getattr(metric, col.name)]
                           for col in schema.metric.columns)))
      engine.execute(ins)

    # =============== Test the function ====================
    with engine.connect() as conn:
      testResultInstance1 = repository.listMetricIDsForInstance(
        conn, self.cwMetric1.server)
      testResultInstance2 = repository.listMetricIDsForInstance(
        conn, self.cwMetric3.server)

    metricIDListInstance1 = [self.cwMetric1.uid,
                             self.cwMetric2.uid]
    metricIDListInstance2 = [self.cwMetric3.uid,
                             self.cwMetric4.uid]
    self.assertEqual(testResultInstance1, metricIDListInstance1)
    self.assertEqual(testResultInstance2, metricIDListInstance2)


  @ManagedTempRepository("InstanceQueryTests")
  def testListMetricIDsNoInstance(self):
    # =============== Setup ===========
    engine = repository.engineFactory()

    # =============== Test the function ====================
    try:
      with engine.connect() as conn:
        repository.listMetricIDsForInstance(
          conn, self.cwMetric1.server)
    except exceptions.ObjectNotFoundError, e:
      self.assertIsInstance(e, exceptions.ObjectNotFoundError)
      self.assertEqual("Instance not found for server=%s"
                       % self.cwMetric1.server, e.message)



if __name__ == '__main__':
  unittest.main()
