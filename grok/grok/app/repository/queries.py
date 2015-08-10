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

from collections import namedtuple
from datetime import datetime, timedelta

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection

from YOMP.app.exceptions import (DuplicateRecordError,
                                 ObjectNotFoundError)
from YOMP.app.repository import schema
import htmengine.utils
from htmengine.utils import jsonDecode


# There is an error with pylint's handling of sqlalchemy, so we disable E1120
# until https://bitbucket.org/logilab/astroid/issues/39/support-for-sqlalchemy
# is resolved; these are disabled line by line throughout

# TODO: Update references elsewhere to htmengine directly and remove these
# imports. Until then, disable pylint W0611.
#pylint: disable=W0611
from htmengine.repository.queries import (
  addMetric,
  addMetricData,
  deleteMetric,
  deleteModel as htmengineDeleteModel,
  getCustomMetrics,
  getAllMetrics,
  getAllMetricsForServer,
  getAllModels,
  getCustomMetricByName,
  getInstances,
  getInstanceStatusHistory,
  getMetric,
  getMetricCountForServer,
  getMetricData,
  getMetricDataCount,
  getMetricDataWithRawAnomalyScoresTail,
  getMetricIdsSortedByDisplayValue,
  _getMetricImpl,
  _getMetrics,
  getMetricStats,
  getMetricWithSharedLock,
  getMetricWithUpdateLock,
  getProcessedMetricDataCount,
  getUnprocessedModelDataCount,
  incrementMetricRowid,
  listMetricIDsForInstance,
  lockOperationExclusive,
  updateMetricColumns,
  updateMetricColumnsForRefStatus,
  updateMetricDataColumns,
  MetricStatus,
  OperationLock,
  saveMetricInstanceStatus,
  setMetricCollectorError,
  setMetricLastTimestamp,
  setMetricStatus,
  _SelectLock,
  _updateMetricColumns)
#pylint: enable=W0611



def deleteModel(conn, metricId):
  """Delete the model by reseting model-specific attributes.
  This method will also make sure the data integrity is kept by removing any
  model related data when necessary, either at the model level or at the
  server/instance level

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param metricId: Metric uid
  """
  with conn.begin():
    # Save server name before deleting model
    # The server name is used later to delete server annotations if necessary
    serverRows = conn.execute((select([schema.metric.c.server])
                               .where(schema.metric.c.uid == metricId)))
    server = serverRows.scalar()

    # Defer actual deletion to htmengine deleteModel() implementation, which
    # will raise ObjectNotFound exception appropriately, terminating execution
    # of *this* function without prejudice.
    htmengineDeleteModel(conn, metricId)

    # When deleting the server's last model, also delete all annotations
    # associated with the server

    delete = (schema.annotation #pylint: disable=E1120
              .delete()
              .where((schema.annotation.c.server == server) &
                     ~schema.annotation.c.server.in_(
                        select([schema.metric.c.server])
                        .where(schema.metric.c.server == server)
                        .where(schema.metric.c.status != 0))))
    conn.execute(delete)


def addAnnotation(conn, timestamp, device, user, server, message, data,
                  created, uid):
  """
  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection

  :param timestamp: The date and time to be annotated
  :param device: Device ID if the annotation was created by the mobile app
                 or Service UID if the annotation was created by a service
  :param user: User name who created the annotation if the annotation was
               created by the mobile app or service name if the annotation
               was created by a service
  :param server: Instance ID associated with this annotation
  :param message: Optional annotation message
  :param data: Optional annotation data
  :param created: The date and time when the annotation was created
  :param uid: Annotation ID
  :rtype: sqlalchemy.engine.ResultProxy
  :raises: ObjectNotFoundError when the Instance ID is not found
  """
  result = None

  with conn.begin():
    # Make sure Instance ID exists prior to adding a new annotations
    sel = (select([func.count(schema.metric.c.server.distinct())])
           .where(schema.metric.c.server == server))
    instanceRows = conn.execute(sel)
    if instanceRows.scalar() == 0:
      raise ObjectNotFoundError("Failed to add annotation. "
                                "Server '%s' was not found." % server)

    # Add new annotation
    add = (schema.annotation.insert() #pylint: disable=E1120
                            .values(timestamp=timestamp,
                                    device=device,
                                    user=user,
                                    server=server,
                                    message=message,
                                    data=data,
                                    created=created,
                                    uid=uid))
    result = conn.execute(add)

  return result


def addAutostack(conn, name, region, filters=None, uid=None):
  """Add Autostack

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param annotationId: Annotation uid
  :param fields: Sequence of columns to be returned by underlying query
  :rtype: dict representing last inserted params
  """
  uid = uid or htmengine.utils.createGuid()

  ins = schema.autostack.insert().values(uid=uid, # pylint: disable=E1120
                                         name=name,
                                         region=region,
                                         filters=filters)
  try:
    response = conn.execute(ins)
  except IntegrityError as e:
    raise DuplicateRecordError(e.message)

  return response.last_inserted_params()



def deleteAnnotationById(conn, annotationId):
  """Delete Annotation given annotation uid

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param annotationId: Annotation uid
  :rtype: sqlalchemy.engine.ResultProxy
  """
  stmt = (schema.annotation.delete() #pylint: disable=E1120
                           .where(schema.annotation.c.uid == annotationId))
  result = conn.execute(stmt)

  if result.rowcount == 0:
    raise ObjectNotFoundError("Annotation not found for uid=%s" % annotationId)

  return result



def getAnnotationById(conn, annotationId, fields=None):
  """Get Annotation given annotation uid

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param annotationId: Annotation uid
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Annotation
  :rtype: sqlalchemy.engine.RowProxy
  """
  fields = fields or [schema.annotation]

  stmt = select(fields).where(schema.annotation.c.uid == annotationId)

  result = conn.execute(stmt)

  annotation = result.first()
  if annotation is None:
    raise ObjectNotFoundError("Annotation not found for uid=%s" % annotationId)

  return annotation



def getAnnotations(conn, device=None, user=None, server=None, fromDate=None,
                   toDate=None, fields=None):
  """
  Query the database for annotations matching the given criteria order by
  annotation "created" time

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param device: Device ID if the annotation was created by the mobile app
                 or Service UID if the annotation was created by a service
  :param user: User name who created the annotation if the annotation was
               created by the mobile app or service name if the annotation was
               created by a service
  :param server: Instance ID associated with the annotation

  :param fromDate: Lower bound "timestamp"
  :param toDate:  Upper bound "timestamp"
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Annotation
  :rtype: sqlalchemy.engine.ResultProxy
  """
  fields = fields or [schema.annotation]

  sel = select(fields, order_by=schema.annotation.c.created.desc())
  if device is not None:
    sel = sel.where(schema.annotation.c.device == device)

  if user is not None:
    sel = sel.where(schema.annotation.c.user == user)

  if server is not None:
    sel = sel.where(schema.annotation.c.server == server)

  if fromDate is not None:
    sel = sel.where(schema.annotation.c.timestamp >= fromDate)

  if toDate is not None:
    sel = sel.where(schema.annotation.c.timestamp <= toDate)

  result = conn.execute(sel)

  return result


def deleteAutostack(conn, autostackId):
  """Delete autostack

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param autostackId: Autostack uid
  :returns: Result of delete operation
  :rtype: sqlalchemy.engine.result.ResultProxy
  """

  assert type(conn) is Connection

  with conn.begin():
    # Delete metrics first
    subselect = (select([schema.metric_set.c.metric])
                 .where(schema.metric_set.c.autostack == autostackId))

    delete = schema.metric.delete().where( #pylint: disable=E1120
      schema.metric.c.uid.in_(subselect))

    conn.execute(delete)

    # Then delete autostack
    delete = (schema.autostack.delete() #pylint: disable=E1120
                              .where(schema.autostack.c.uid == autostackId))

    result = conn.execute(delete)

    # "result.rowcount" returns the number of rows matching the where expression
    if result.rowcount == 0:
      raise ObjectNotFoundError("Autostack not found for uid=%s" % autostackId)

    return result


def addMetricToAutostack(conn, autostackId, metricId):
  """Associate metric with autostack

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param autostackId: Autostack uid
  :param metricId: Metric uid
  """
  ins = schema.metric_set.insert().values( #pylint: disable=E1120
                                          metric=metricId,
                                          autostack=autostackId)
  conn.execute(ins)


def getAutostack(conn, autostackId, fields=None):
  """Get Autostack

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param autostackId: Autostack uid
  :type autostackId: str
  :returns: Autostack
  :rtype: sqlalchemy.engine.RowProxy
  """
  fields = fields or [schema.autostack]

  sel = select(fields).where(schema.autostack.c.uid == autostackId)

  result = conn.execute(sel)

  autostack = result.first()
  if autostack is None:
    raise ObjectNotFoundError("Autostack not found for uid=%s" % autostackId)

  return autostack



def getAutostackFromMetric(conn, metricId):
  """Get the Autostack instance that metric belongs to.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :returns: Autostack
  :rtype: sqlalchemy.engine.RowProxy
  """
  joinAutostack = (
    schema.autostack.join(
      schema.metric_set,
      schema.metric_set.c.autostack == schema.autostack.c.uid))

  sel = (select([schema.autostack], from_obj=joinAutostack)
         .where(schema.metric_set.c.metric == metricId))

  result = conn.execute(sel)

  autostack = result.first()
  if autostack is None:
    raise ObjectNotFoundError("Autostack not found for metric %s" % metricId)

  # There should never be multiple matches.
  assert result.rowcount == 1, "metric=%s matched %d autostacks" % (
      metricId, result.rowcount)

  return autostack


def getAutostackForNameAndRegion(conn, name, region, fields=None):
  """ Get Autostack given name and region

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param name: Autostack name
  :param region: AWS region
  :param fields: Sequence of columns to be returned by underlying query
  :returns: AutoStack
  :rtype: sqlalchemy.engine.RowProxy
  :raises: YOMP.app.exceptions.ObjectNotFoundError if no match
  """
  fields = fields or [schema.autostack]

  sel = select(fields).where((schema.autostack.c.name == name) &
                             (schema.autostack.c.region == region))

  result = conn.execute(sel)

  autostack = result.first()
  if autostack is None:
    raise ObjectNotFoundError(
      "Autostack not found for name=%s and region=%s" % (name, region))

  return autostack



def getAutostackMetrics(conn, autostackId, fields=None):
  """Return a list of all metrics in an Autostack

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param autostackId: Autostack uid
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Autostack metrics
  :rtype: Iterable of sqlalchemy.engine.RowProxy
  """
  fields = fields or [schema.metric]

  sel = (select(fields)
         .select_from(schema.metric
                      .join(schema.metric_set,
                            schema.metric_set.c.metric == schema.metric.c.uid))
         .where(schema.metric_set.c.autostack == autostackId))

  return conn.execute(sel)



def getAutostackMetricsWithMetricName(conn, autostackId, name, fields=None):
  """Get Autostack metrics given autostackId and metric name

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param autostackId: Autostack uid
  :param name: metric name
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Matching metric rows
  :rtype: Iterable of sqlalchemy.engine.RowProxy
  """
  fields = fields or [schema.metric]

  sel = (select(fields)
         .select_from(schema.metric
                      .join(schema.metric_set,
                            schema.metric_set.c.metric == schema.metric.c.uid))
         .where(schema.metric_set.c.autostack == autostackId)
         .where(schema.metric.c.name == name))

  return conn.execute(sel)



def _getCloudwatchMetricReadinessPredicate():
  """ Generate an sqlAlchemy predicate that determines whether the metric is
  ready for data collection.

  :returns: sqlAlchemy predicate for use in `where` clause
  """
  # NOTE: the time arithmetic must be coordinated with
  # YOMP.app.aws.cloudwatch_utils.getMetricCollectionBackoffSeconds()

  # NOTE: the time difference logic here is a heuristic fine-tuned for
  # cloudwatch-based metrics as follows:
  #   * Cloudwatch metrics aggregated over a specific period (e.g., 5 minutes)
  #     appear to be arranged in contiguous time buckets each with a specific
  #     start and end time; we don't have visibility into the actual start time
  #     of any bucket, which appears to depend on when the cloudwatch metric was
  #     created.
  #   * In the higher-level logic, the first time we query a metric, we pick the
  #     metric's virtual starting time based on a 14-day backoff from current
  #     time (which is not the actual metric time bucket's start time) and
  #     subsequently add the metric's period to arrive at the next metric
  #     value's virtual start time, and so on.
  #   * Based on experiments with 5-minute-aggregated metrics, it appears that a
  #     metric's aggregated value becomes availabe one period after the true end
  #     of the metric value's time bucket. If you don't wait long enough, you
  #     either don't get any value from cloudwatch (which is a wasted slow call
  #     that contributes to API throttling) or you might get a non-final
  #     value.
  #   * Since we don't know the true start time of the time bucket, we
  #     compensate for it: first, we add the metric period to the virtual start
  #     time, which should get us at least to the end of the true time bucket;
  #     then we add another period to get us at least to the point in time where
  #     the time-bucket's data becomes available, and finally add a fudge value
  #     (60 seconds at time of this writing) for the metric value to stabilize
  return (
    (schema.metric.c.last_timestamp == None)
    | (func.timestampdiff(text("SECOND"),
                          schema.metric.c.last_timestamp,
                          func.utc_timestamp())
       >= (schema.metric.c.poll_interval +
           (schema.metric.c.poll_interval + 60))))



def getAutostackMetricsPendingDataCollection(conn):
  """Load ACTIVE Autostack Metric instances that should be ready for data
     collection

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: a sequence of tuples where the zeroth item is an Autostack
    instance, and the other is a list of Metric instances in the ACTIVE
    state that are ready for data collection
  """
  sel = (select([schema.autostack, schema.metric], use_labels=True)
         .select_from(
            schema.metric
            .join(schema.metric_set,
                  schema.metric_set.c.metric == schema.metric.c.uid)
            .join(schema.autostack,
                  schema.metric_set.c.autostack == (
                    schema.metric_set.c.autostack)))
         .where(schema.metric_set.c.metric == schema.metric.c.uid)
         .where(schema.autostack.c.uid == schema.metric_set.c.autostack)
         .where((schema.metric.c.status == 1) | (schema.metric.c.status == 8))
         .where(_getCloudwatchMetricReadinessPredicate()))

  retval = {}

  for result in conn.execute(sel):
    autostackDict = dict((c.name, jsonDecode(
                                    result["autostack_" + c.name])
                                  if c.name == "filters"
                                  else result["autostack_" + c.name])
                         for c in schema.autostack.columns
                         if "autostack_" + c.name in result)
    autostackObj = (namedtuple("AutostackRecord", # pylint: disable=W0212
                               autostackDict.keys())
                    ._make(autostackDict.values()))

    metricDict = dict((c.name, result["metric_" + c.name])
                      for c in schema.metric.columns
                      if "metric_" + c.name in result)
    metricObj = (namedtuple("MetricRecord", # pylint: disable=W0212
                            metricDict.keys())
                 ._make(metricDict.values()))
    retval.setdefault(autostackObj.uid, (autostackObj, []))[1].append(metricObj)

  return retval.values()



def getCloudwatchMetrics(conn, fields=None):
  """Get Cloudwatch metrics

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Result of querying database for cloudwatch metrics
  :rtype: sqlalchemy.engine.ResultProxy
  """
  where = (schema.metric.c.datasource == "cloudwatch")

  return _getMetrics(conn, fields=fields, where=where)


def getCloudwatchMetricsForNameAndServer(conn, name, server, fields=None):
  """Get Cloudwatch metrics given name and server

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param name: metric name
  :param server: metric server
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Sequence of matching cloudwatch metric rows
  :rtype: Sequence of sqlalchemy.engine.RowProxy
  """
  where = ((schema.metric.c.datasource == "cloudwatch") &
           (schema.metric.c.server == server) &
           (schema.metric.c.name == name))

  return _getMetrics(conn, fields=fields, where=where).fetchall()



def getCloudwatchMetricsPendingDataCollection(conn):
  """Load ACTIVE Metric instances that should be ready for data
     collection

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: a sequence of Metric instances in the ACTIVE state that are ready
    for data collection
  """
  sel = (select([schema.metric])
         .where(schema.metric.c.datasource == "cloudwatch")
         .where((schema.metric.c.status == MetricStatus.ACTIVE)
                | (schema.metric.c.status == MetricStatus.PENDING_DATA))
         .where(_getCloudwatchMetricReadinessPredicate()))

  return conn.execute(sel).fetchall()



def getAutostackList(conn):
  """Return a list of all autostacks

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: [Autostack]
  :rtype: sqlalchemy.engine.RowProxy
  """
  sel = select([schema.autostack])

  return conn.execute(sel).fetchall()



def getNotification(conn, notificationId, fields=None):
  """Get Notification

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param notificationId: Notification uid
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Notification
  :rtype: sqlalchemy.engine.RowProxy
  :raises: YOMP.app.exceptions.ObjectNotFoundError if Notification doesn't
    exist for given uid
  """
  fields = fields or [schema.notification]

  sel = select(fields).where(schema.notification.c.uid == notificationId)

  result = conn.execute(sel)

  notification = result.first()
  if notification is None:
    raise ObjectNotFoundError("Notification not found for uid=%s" % (
      notificationId))

  return notification



def getUnseenNotificationList(conn, deviceId, limit=None, fields=None):
  """Get unseen notifications

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param deviceId: Device uid
  :param limit: The number of notifications to return
  :type limit: int
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Notifications that have not been acknowledged or marked as seen
    and which were created within the last seven days
  :rtype: List of sqlalchemy.engine.RowProxy
  """
  fields = fields or [schema.notification]
  lastWeekTS = datetime.now() - timedelta(days=7)

  sel = (select(fields)
         .where(schema.notification.c.device == deviceId)
         .where(schema.notification.c.acknowledged == 0)
         .where(schema.notification.c.seen == 0)
         .where(schema.notification.c.timestamp > lastWeekTS)
         .order_by(schema.notification.c.timestamp.desc()))

  if limit is not None:
    sel = sel.limit(limit)

  return conn.execute(sel).fetchall()



def addNotification(conn, uid, server, metric, rowid, device, windowsize,
                    timestamp, acknowledged, seen):
  """Add Notification

  :param conn: SQLAlchemy Connection object for executing SQL
  :type conn: sqlalchemy.engine.Connection
  :param uid: Notification uid
  :param server: Metric server
  :param metric: Metric uid
  :param rowid: Metric Data row id
  :param device: Device id (notification_settings.uid)
  :param windowsize: Window size (seconds)
  :param timestamp: Metric Data timestamp
  :param acknowledged:
  :param seen:
  :returns: Result
  :rtype: sqlalchemy.engine.ResultProxy
  """
  result = None

  with conn.begin():
    # Secure a write lock on notification table.  Other processes attempting to
    # access the notification table will be blocked until the lock is released.
    # This is to ensure that in the time between the first SELECT and the
    # followup INSERT there are no other potentially conflicting INSERTS that
    # could result in duplicated notifications.  Meanwhile, other processes may
    # execute concurrent inserts to metric table.

    conn.execute("LOCK TABLES notification WRITE, metric READ;")

    try:
      # New notification is potentially a duplicate if there exists an unseen
      # notification for the same metric and server created within the
      # requested windowsize.

      query = (
        select([func.count(schema.notification.c.uid)])
        .select_from(
          schema.notification.outerjoin(
            schema.metric,
            schema.metric.c.uid == schema.notification.c.metric))
        .where(
          (schema.metric.c.server == server) &
          (schema.notification.c.device == device) &
          (schema.notification.c.seen == 0) &
          (func.date_add(schema.notification.c.timestamp,
                         text("INTERVAL :windowsize SECOND")) >
           timestamp))
      )

      if conn.execute(query, windowsize=windowsize).scalar() == 0:

        # Previous query yielded no results, notification is unique according
        # to our constraints.  Insert new notification details.

        ins = (schema.notification.insert().values( #pylint: disable=E1120
                                                   uid=uid,
                                                   metric=metric,
                                                   device=device,
                                                   windowsize=windowsize,
                                                   timestamp=timestamp,
                                                   acknowledged=acknowledged,
                                                   seen=seen,
                                                   rowid=rowid))

        try:
          result = conn.execute(ins)
        except IntegrityError:
          result = None

    finally:
      conn.execute("UNLOCK TABLES;") # Release table lock.

  return result



def addDeviceNotificationSettings(conn, # pylint: disable=C0103
                                  deviceId,
                                  windowsize,
                                  sensitivity,
                                  email_addr):
  """Add notification settings for device

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param deviceId: Device uid
  :param windowsize: Time during which no other notifications may be created
  :param sensitivity: Anomaly likelihood threashold
  :param email_addr: Email address
  """
  ins = (schema.notification_settings.insert() # pylint: disable=E1120
         .values(uid=deviceId,
                 windowsize=windowsize,
                 sensitivity=sensitivity,
                 email_addr=email_addr,
                 last_timestamp=datetime.utcnow()))
  conn.execute(ins)



def getDeviceNotificationSettings(conn, deviceId):
  """Get notification settings for device

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param deviceId: Device uid
  :returns: Notification settings
  :rtype: sqlalchemy.engine.RowProxy
  """
  sel = (select([schema.notification_settings])
         .where(schema.notification_settings.c.uid == deviceId))

  result = conn.execute(sel)

  notificationSettings = result.first()
  if notificationSettings is None:
    raise ObjectNotFoundError(
      "Notification settings not found for deviceId=%s" % (deviceId))

  return notificationSettings



def updateNotificationDeviceTimestamp(conn, deviceId):
  """Updates last access timestamp for the specified device.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param deviceId: Device uid
  :type deviceId: str
  :raises: ObjectNotFoundError when there is no device with deviceId configured
  """
  query = (schema.notification_settings #pylint: disable=E1120
           .update()
           .where(schema.notification_settings.c.uid == deviceId)
           .values(last_timestamp=func.utc_timestamp()))
  result = conn.execute(query)
  if result.rowcount == 0:
    raise ObjectNotFoundError("No notification settings for device: %s" %
                              deviceId)



def deleteStaleNotificationDevices(conn, days):
  """Deletes devices from notifications if they haven't been active recently.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param days: the number of days of absense before considering a device stale
  :type days: int
  """
  query = schema.notification_settings.delete().where(  # pylint: disable=E1120
      func.date_add(schema.notification_settings.c.last_timestamp,
                    text("INTERVAL %i DAY" % days)) <
      func.utc_timestamp())
  conn.execute(query)



def getAllNotificationSettings(conn):
  """Get all Notifications

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: list of sqlalchemy.engine.RowProxy
  :rtype: list
  """
  sel = select([schema.notification_settings])
  return conn.execute(sel).fetchall()



def clearOldNotifications(conn):
  """Clear old notifications

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  """
  delete = (schema.notification # pylint: disable=E1120
            .delete()
            .where(func.date_add(schema.notification.c.timestamp,
                                 text("INTERVAL 30 DAY"))
                    < func.utc_timestamp()))
  conn.execute(delete)


def updateNotificationMessageId(conn, notificationId, messageId):
  """Update notification messageId

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param notificationId: Notification uid
  :param messageId: AWS-assigned message id for notifications sent via Amazon
    SES
  """
  update = (schema.notification # pylint: disable=E1120
            .update()
            .where(schema.notification.c.uid == notificationId))
  conn.execute(update.values(ses_message_id=messageId))



def getInstanceCount(conn):
  """ Get total instance count (including autostacks without metrics).

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: Total number of instances
  """
  query = select([func.count(schema.metric.c.server.distinct())]).where(
      schema.metric.c.status != MetricStatus.UNMONITORED)
  metricInstanceCount = conn.execute(query).scalar()

  query = select([func.count(schema.autostack.c.uid.distinct())]).select_from(
      schema.autostack.outerjoin(
          schema.metric_set,
          schema.metric_set.c.autostack == schema.autostack.c.uid)).where(
            schema.metric_set.c.autostack == None)

  autostackWithoutMetricCount = conn.execute(query).scalar()

  # The instance count is all instances with metrics monitored plus any
  # autostacks that have no metrics.
  return metricInstanceCount + autostackWithoutMetricCount



def updateDeviceNotificationSettings(conn, deviceId, changes):
  """Update notification settings for device

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param deviceId: Device uid
  :param changes: Data to update
  :type changes: dict
  """
  update = (schema.notification_settings.update() # pylint: disable=E1120
            .where(schema.notification_settings.c.uid == deviceId))

  conn.execute(update.values(changes))



def batchAcknowledgeNotifications(conn, notificationIds):
  """Mark batch of notifications as acknowledged

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param notificationIds: Notification uids
  :type notificationIds: list
  """
  update = (schema.notification.update() # pylint: disable=E1120
            .where(schema.notification.c.uid.in_(notificationIds)))
  conn.execute(update.values(acknowledged=1))



def batchSeeNotifications(conn, notificationIds):
  """Mark batch of notifications as seen

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param notificationIds: Notification uids
  :type notificationIds: list
  """
  update = schema.notification.update().where( #pylint: disable=E1120
      schema.notification.c.uid.in_(notificationIds))
  conn.execute(update.values(seen=1))
