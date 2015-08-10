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

from sqlalchemy import func, MetaData, Numeric, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection, Engine

from htmengine.exceptions import (DuplicateRecordError,
                                  MetricStatisticsNotReadyError,
                                  ObjectNotFoundError)
import htmengine.utils
from htmengine.utils import jsonDecode
from htmengine.repository import schema
from htmengine.repository.schema import metadata



class MetricStatus(object):
  """ Metric states stored in the "metric" SQL table

  WARNING: changing existing status values/semantics will be incompatible with
    status values already stored in the existing SQL table (think software
    upgrade)
  """
  # This is used when a metric exists but is not monitored. HTM metrics
  # utilize this when data is sent in but the metric isn't monitored yet.
  UNMONITORED = 0b0000 # 0

  # This means the model has been created in the engine and there are no errors.
  ACTIVE = 0b0001 # 1

  # This state is used when a model creation command has been sent to the
  # engine but hasn't been processed yet.
  CREATE_PENDING = 0b0010 # 2

  # When there is an irrecoverable error with a model it is put into this state
  # and the message field is populated with the reason.
  ERROR = 0b0100 # 4

  # The state is used for delayed model creation when there is a specified min
  # and max and there isn't sufficient data to estimate the min and max with
  # confidence.
  PENDING_DATA = 0b1000 # 8



class OperationLock(object):
  """ Operation-level locks for use with lockOperationExclusive

  The constants here correspond to rows in the `lock` table
  """

  # Lock for adding metrics, while ensuring their uniqueness
  METRICS = "metrics"



def deleteMetric(conn, metricId):
  """Delete metric

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :returns: Result of delete operation
  :rtype: sqlalchemy.engine.result.ResultProxy
  """
  result = None

  with conn.begin():

    # Make sure to clear the model. This call will also make sure data integrity
    # is kept by deleting any related data when necessary
    deleteModel(conn, metricId)

    # Delete metric
    result = (conn.execute(schema.metric.delete()
                           .where(schema.metric.c.uid == metricId)))

    if result.rowcount == 0:
      raise ObjectNotFoundError("Metric not found for uid=%s" % metricId)

  return result



def deleteModel(conn, metricId):
  """Delete the model by reseting model-specific attributes.
  This method will also make sure the data integrity is kept by removing any
  model related data when necessary, either at the model level or at the
  server/instance level

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param metricId: Metric uid
  """
  # TODO MER-3781: Deleting custom model should also delete notifications

  with conn.begin():
    # Reset model and model data
    update = (schema.metric.update()
              .values(parameters=None,
                      model_params=None,
                      status=MetricStatus.UNMONITORED,
                      message=None)
              .where(schema.metric.c.uid == metricId))

    result = conn.execute(update)

    if result.rowcount == 0:
      raise ObjectNotFoundError("Metric not found for uid=%s" % metricId)

    update = (schema.metric_data.update() # pylint: disable=E1120
              .values(anomaly_score=None,
                      raw_anomaly_score=None,
                      display_value=None)
              .where(schema.metric_data.c.uid == metricId))

    conn.execute(update)




def addMetric(conn, # pylint: disable=C0103
              uid=None, datasource=None, name=None,
              description=None, server=None, location=None,
              parameters=None, status=None, message=None, collector_error=None,
              last_timestamp=None, poll_interval=None,
              tag_name=None, model_params=None, last_rowid=0):
  """Add metric

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: Key-value pairs for inserted columns and values
  :rtype: dict

  Usage::

      metricDict = repository.addMetric(conn, ...)
      metricId = metricDict["uid"]
      metricObj = repository.getMetric(conn, metricId)

  """
  uid = uid or htmengine.utils.createGuid()

  ins = schema.metric.insert().values(uid=uid, # pylint: disable=E1120
                                      datasource=datasource,
                                      name=name,
                                      description=description,
                                      server=server,
                                      location=location,
                                      parameters=parameters,
                                      status=status,
                                      message=message,
                                      collector_error=collector_error,
                                      last_timestamp=last_timestamp,
                                      poll_interval=poll_interval,
                                      tag_name=tag_name,
                                      model_params=model_params,
                                      last_rowid=last_rowid)

  return conn.execute(ins).last_inserted_params()



def getCustomMetrics(conn, fields=None):
  """Get Custom metrics

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Result of querying database for custom metrics
  :rtype: sqlalchemy.engine.ResultProxy
  """
  fields = fields or [schema.metric]

  sel = select(fields).where(schema.metric.c.datasource == "custom")

  return conn.execute(sel)



  return _getMetrics(conn, fields=fields, where=where)



def getMetric(conn, metricId, fields=None):
  """Get Metric given metric uid

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param fields: Sequence of columns to be returned by underlying query
  :returns: Metric
  :rtype: sqlalchemy.engine.RowProxy

  :raises ObjectNotFoundError: if a row with the requested metricId wasn't found
  """
  return _getMetricImpl(conn, metricId, fields, lockKind=None)



def getMetricWithSharedLock(conn, metricId, fields=None):
  """ Perform SELECT ... LOCK IN SHARE MODE on the given metric uid and return
  the requested fields.

  :param conn: SQLAlchemy connection
  :type conn: sqlalchemy.engine.Connection

  :param metricId: Metric uid
  :type metricId: str

  :param fields: Sequence of columns to be returned by underlying query

  :returns: Metric
  :rtype: sqlalchemy.engine.RowProxy

  :raises ObjectNotFoundError: if a row with the requested metricId wasn't found
  """
  return _getMetricImpl(conn, metricId, fields, lockKind=_SelectLock.SHARED)



def getMetricWithUpdateLock(conn, metricId, fields=None):
  """ Perform SELECT ... FOR UPDATE on the given metric uid and return the
  requested fields.

  :param conn: SQLAlchemy connection
  :type conn: sqlalchemy.engine.Connection

  :param metricId: Metric uid
  :type metricId: str

  :param fields: Sequence of columns to be returned by underlying query

  :returns: Metric
  :rtype: sqlalchemy.engine.RowProxy

  :raises ObjectNotFoundError: if a row with the requested metricId wasn't found
  """
  return _getMetricImpl(conn, metricId, fields, lockKind=_SelectLock.UPDATE)



class _SelectLock(object):
  """ Values for the read parameter of
  sqlalchemy.sql.selectable.Select.with_for_update
  """
  SHARED = True    # SELECT ... LOCK IN SHARE MODE
  UPDATE = False   # SELECT ... FOR UPDATE



def _getMetricImpl(conn, metricId, fields, lockKind):
  """Get Metric given metric uid

  :param conn: SQLAlchemy;
  :type conn: sqlalchemy.engine.Connection

  :param metricId: Metric uid
  :type metricId: str

  :param fields: Sequence of columns to be returned by underlying query
  :returns: Metric

  :param lockKind: None for no lock or one of the _SelectLock constants to
    choose either "SELECT ... LOCK IN SHARE MODE" or "SELECT ... FOR UPDATE".

  :rtype: sqlalchemy.engine.RowProxy

  :raises ObjectNotFoundError: if a row with the requested metricId wasn't found
  """
  fields = fields or [schema.metric]

  sel = select(fields).where(schema.metric.c.uid == metricId)
  if lockKind is not None:
    sel = sel.with_for_update(read=lockKind)

  result = conn.execute(sel)
  metric = result.first()

  if metric is None:
    raise ObjectNotFoundError("Metric not found for uid=%s" % (metricId,))

  return metric



def getAllMetrics(conn, fields=None):
  """Get all metrics currently in the db.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :rtype: sqlalchemy.engine.ResultProxy
  """
  return _getMetrics(conn, fields=fields)



def getAllMetricsForServer(conn, server, fields=None):
  """Get all metrics currently in the db.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :rtype: sqlalchemy.engine.ResultProxy
  """
  where = schema.metric.c.server == server
  return _getMetrics(conn, fields=fields, where=where)



def getMetricCountForServer(conn, server):
  """Get the count of all currently monitored
  metrics with specified server.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param server: The name of the server to check

  :rtype: int
  """
  sel = (select([func.count(schema.metric.c.uid)])
         .where(schema.metric.c.server == server))
  result = conn.execute(sel)

  return result.scalar()



def _getMetrics(conn, fields=None, where=None):
  """Get all metrics currently in the db that satisfy the given parameters.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :param where: An operation to be passed into a sqlalchemy where clause
  :rtype: sqlalchemy.engine.ResultProxy
  """
  fields = fields or [schema.metric]

  sel = select(fields)

  if where is not None:
    sel = sel.where(where)

  return conn.execute(sel)



def getAllModels(conn, fields=None):
  """Get all models currently in the db.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Sequence of columns to be returned by underlying query
  :rtype: sqlalchemy.engine.ResultProxy
  """
  where = schema.metric.c.status != MetricStatus.UNMONITORED
  return _getMetrics(conn, fields=fields, where=where)



def getMetricIdsSortedByDisplayValue(conn, period):
  """ Get Metric IDs in order of anomalous behavior over a given time period

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param period: Time period (hours) over which to aggregate display values
  :type period: str
  :returns: Mapping of metric ids and aggregated display values
            {metricId: MAX(display_value), ...}
  """

  # This sub-query gets the last timestamp from any metric which is used as
  # the end of the window. The period parameter determines how large the
  # window is.
  subQuery = ("(SELECT timestamp from metric_data ORDER BY timestamp DESC "
              "LIMIT 1)")

  # This query first uses a sub-query to get the max display value within each
  # bar in the window determined by the period and the sub-query above. It
  # then sums these max values for each model to get the aggregate display
  # value for the models. The number 150 converts the hours in the window
  # into the seconds per bar (since we want to break the values into blocks
  # for each bar). The value 150 comes from the hour-to-second conversion
  # (multiply by 60 * 60) and the window-to-bar conversion (divide by 24).
  sql = (
    "SELECT uid, SUM(aggregated_display_value) "
    "FROM (SELECT uid, "
    "             MAX(display_value) as `aggregated_display_value`, "
    "             FLOOR(UNIX_TIMESTAMP(timestamp) / ("+period+" * 150)) as "
    "                 `time_block` "
    "      FROM metric_data WHERE "
    "          timestamp > date_sub("+subQuery+", interval "+period+" hour) "
    "      GROUP BY uid, time_block) AS inner_select "
    "GROUP BY uid")

  result = conn.execute(sql)
  displayValueMap = (
    dict([(row[schema.metric.c.uid], row[1]) for row in result]))
  return displayValueMap



def getCustomMetricByName(conn, name, fields=None):
  """Get Metric given metric name and datasource

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param name: Metric name
  :returns: Metric
  :rtype: sqlalchemy.engine.RowProxy
  """
  where = ((schema.metric.c.name == name) &
           (schema.metric.c.datasource == "custom"))

  result = _getMetrics(conn, fields=fields, where=where)

  metricObj = result.first()
  if metricObj is None:
    raise ObjectNotFoundError("Custom metric not found for name=%s" % name)

  return metricObj


def setMetricCollectorError(conn, metricId, value):
  """Set Metric given metric uid

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param value: Collector error value
  :type value: str
  :raises: htmengine.exceptions.ObjectNotFoundError if no match
  """
  update = schema.metric.update().where(schema.metric.c.uid == metricId)
  result = conn.execute(update.values(collector_error=value))

  if result.rowcount == 0:
    raise ObjectNotFoundError("Metric not found for uid=%s" % metricId)



def setMetricLastTimestamp(conn, metricId, value):
  """Set Timestamp for most recent update of metric

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param value: Timestamp value
  :type value: str
  :raises: htmengine.exceptions.ObjectNotFoundError if no match
  """
  update = schema.metric.update().where(schema.metric.c.uid == metricId)
  result = conn.execute(update.values(last_timestamp=value))

  if result.rowcount == 0:
    raise ObjectNotFoundError("Metric not found for uid=%s" % metricId)



def setMetricStatus(conn, metricId, status, message=None, refStatus=None):
  """Set metric status

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection

  :param metricId: Metric uid
  :type metricId: str

  :param status: metric status value to set
  :type status: one of MetricStatus values

  :param message: message to set; clears message field by default
  :type message: string or None; if None, the message field will be cleared

  :param refStatus: reference status; if None (default), the requested values
      will be set regardless of the current value of the row's status field;
      otherwise, the status will be updated only if the metric row's current
      status is refStatus (checked automically). If the current value was not
      refStatus, then upon return, the reloaded metric dao's `status`
      attribute will reflect the status value that was in the metric row at
      the time the update was attempted instead of the requested status value.
  :type refStatus: None or one of MetricStatus values

  :raises: htmengine.exceptions.ObjectNotFoundError if no match
  """
  updateValues = {"status": status, "message": message}

  update = schema.metric.update().where(schema.metric.c.uid == metricId)

  if refStatus is not None:
    # Add refStatus match to the predicate
    update = update.where(schema.metric.c.status == refStatus)

  result = conn.execute(update.values(updateValues))

  # "result.rowcount" returns the number of rows matching the where expression
  if result.rowcount == 0:
    raise ObjectNotFoundError("Metric not found for uid=%s" % metricId)



def saveMetricInstanceStatus(conn, server, status, timestamp=None):
  """Save metric instance status

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection

  :param server: "server" column in ``htmengine.repository.schema.metric``
  :type server: str

  :param status: instance status value to set

  :param timestamp: Timestamp for instance status

  """
  with conn.begin():
    timestamp = timestamp or datetime.utcnow()

    sel = (select([schema.instance_status_history.c.status],
                  order_by=schema.instance_status_history.c.timestamp.desc())
           .where(schema.instance_status_history.c.server == server)
           .limit(1))
    result = conn.execute(sel)

    if result.rowcount == 0 or result.fetchone().status != status:
      ins = (schema.instance_status_history # pylint: disable=E1120
             .insert()
             .values(server=server,
                     status=status,
                     timestamp=timestamp))
      conn.execute(ins)



def incrementMetricRowid(conn, metricId, amount=1):
  """ Increment Metric Row ID

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param amount: Amount
  :type amount: integer

  :returns: the resulting last_rowid
  :rtype: int

  :raises ObjectNotFoundError: if a row with the requested metricId wasn't found
  """
  assert type(conn) is Connection

  if amount < 1:
    raise ValueError("Expected positive integer amount for incrementing "
                       "last_rowid, but got: %r" % (amount,))

  with conn.begin():
    oldLastRowid = getMetricWithUpdateLock(
      conn, metricId, fields=[schema.metric.c.last_rowid])[0]

    update = schema.metric.update().where(schema.metric.c.uid == metricId)

    conn.execute(update.values(last_rowid=schema.metric.c.last_rowid+amount))

  return oldLastRowid + amount



def addMetricData(conn, metricId, data):
  """ Add Metric Data
  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param data: A sequence of metric data sample pairs (value, datetime.datetime)
  :returns: Sequence of metric data rows ordered by rowid in ascending order.
    each row is a dict of column names/values
  """
  assert type(conn) is Connection

  numRows = len(data)

  if numRows == 0:
    return []

  with conn.begin():
    lastRowid = incrementMetricRowid(conn, metricId, amount=numRows)

    rows = [
      dict(uid=metricId,
           rowid=rowid,
           timestamp=timestamp,
           metric_value=metricValue)
      for rowid, (metricValue, timestamp) in enumerate(data,
                                                       lastRowid - numRows + 1)
    ]

    conn.execute(schema.metric_data.insert(), rows)

  return rows



def getMetricData(conn,
                  metricId=None,
                  fields=None,
                  rowid=None,
                  start=None,
                  stop=None,
                  limit=None,
                  fromTimestamp=None,
                  toTimestamp=None,
                  score=None,
                  sort=None):
  """Get Metric Data

  The parameters {rowid}, {fromTimestamp ad toTimestamp}, and {start and stop}
  are to be used independently for different queries.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param fields: Sequence of columns to be returned by underlying query
  :param rowid: Specific MetricData row id
  :param start: Starting MetricData row id; inclusive
  :param stop: Max MetricData row id; inclusive
  :param limit: Limit on number of results to return
  :param fromTimestamp: Starting timestamp
  :param toTimestamp: Ending timestamp
  :param score: Return only rows with scores above this threshold
    (all non-null scores for score=0)
  :param sort: Sort by this sqlalchemy column
  :returns: Metric data
  :rtype: sqlalchemy.engine.ResultProxy
  """
  fields = fields or [schema.metric_data]

  if sort is None:
    sel = select(fields, order_by=schema.metric_data.c.rowid.asc())
  else:
    sel = select(fields, order_by=sort)

  if metricId is not None:
    sel = sel.where(schema.metric_data.c.uid == metricId)

  if rowid is not None:
    sel = sel.where(schema.metric_data.c.rowid == rowid)
  elif fromTimestamp is not None or toTimestamp is not None:
    if fromTimestamp:
      sel = sel.where(schema.metric_data.c.timestamp >= fromTimestamp)
    if toTimestamp:
      sel = sel.where(schema.metric_data.c.timestamp <= toTimestamp)
  else:
    if start is not None:
      sel = sel.where(schema.metric_data.c.rowid >= start)

    if stop is not None:
      sel = sel.where(schema.metric_data.c.rowid <= stop)

  if limit is not None:
    sel = sel.limit(limit)

  if score > 0.0:
    sel = sel.where(schema.metric_data.c.anomaly_score >= score)
  elif score == 0.0:
    sel = sel.where(schema.metric_data.c.anomaly_score != None)

  result = conn.execute(sel)

  return result



def getMetricDataWithRawAnomalyScoresTail(conn, metricId, limit):
  """Get MetricData ordered by timestamp, descending

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :type metricId: str
  :param limit: Limit on number of results to return
  :returns: Metric data
  """
  sel = (select([schema.metric_data],
                from_obj=schema.metric_data,
                order_by=schema.metric_data.c.timestamp.desc())
         .where(schema.metric_data.c.uid == metricId)
         .where(schema.metric_data.c.raw_anomaly_score != None)
         .limit(limit))

  result = conn.execute(sel)

  return result.fetchall()



def getMetricDataCount(conn, metricId):
  """Get count of all MetricData rows for the given metricId.

  :param conn: SQLAlchemy Connection object for executing SQL
  :type conn: sqlalchemy.engine.Connection
  :param metricId: Metric uid
  """
  sel = (select([func.count()], from_obj=schema.metric_data)
         .where(schema.metric_data.c.uid == metricId))

  result = conn.execute(sel)
  return result.first()[0]



def getProcessedMetricDataCount(conn, metricId):
  """Get count of processed MetricData for the given metricId.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  """
  sel = (select([func.count()], from_obj=schema.metric_data)
         .where(schema.metric_data.c.uid == metricId)
         .where(schema.metric_data.c.raw_anomaly_score != None))

  result = conn.execute(sel)
  return result.scalar()



def updateMetricDataColumns(conn, metricDataObj, fields):
  """Update MetricData

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricDataObj:
  :param fields: Sequence of columns to be updated by underlying query
  """
  update = (schema.metric_data.update() # pylint: disable=E1120
            .where(schema.metric_data.c.uid == metricDataObj.uid)
            .where(schema.metric_data.c.rowid == metricDataObj.rowid))
  conn.execute(update.values(fields))



def getMetricStats(conn, metricId):
  """
  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :raises: htmengine.exceptions.MetricStatisticsNotReadyError if there are no
    or insufficent samples at this time; this may also happen if the metric
    and its data were deleted by another process in the meantime
  """
  sel = (select([func.min(schema.metric_data.c.metric_value),
                 func.max(schema.metric_data.c.metric_value)],
                from_obj=schema.metric_data)
         .where(schema.metric_data.c.uid == metricId))

  result = conn.execute(sel)

  if result.rowcount > 0:
    statMin, statMax = result.first().values()

    if statMin is not None and statMax is not None:
      return {"min": statMin, "max": statMax}

  raise MetricStatisticsNotReadyError()



def _updateMetricColumns(conn, fields, where):
  """Update existing metric

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param fields: Dictionary of column name to values mappings
  :returns: Update result
  :rtype: sqlalchemy.engine.ResultProxy
  """
  update = schema.metric.update().where(where) # pylint: disable=E1120
  return conn.execute(update.values(fields))


def updateMetricColumnsForRefStatus(conn, metricId, refStatus, fields):
  """Update existing metric for known status

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :param refStatus: Status;  Update only if metric status currently matches
    ``refStatus`` in database.
  :param fields: Dictionary of column name to values mappings
  :returns: Update result
  :rtype: sqlalchemy.engine.ResultProxy
  """
  where = ((schema.metric.c.uid == metricId) &
           (schema.metric.c.status == refStatus))
  return _updateMetricColumns(conn, fields, where)


def updateMetricColumns(conn, metricId, fields):
  """Update existing metric

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param metricId: Metric uid
  :param fields: Dictionary of column name to values mappings
  :returns: Update result
  :rtype: sqlalchemy.engine.ResultProxy
  """
  return _updateMetricColumns(conn, fields, schema.metric.c.uid == metricId)


def getInstances(conn):
  """Returns a sequence of all running instances

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :returns: a sequence of instances
  """
  sel = (select([schema.metric])
         .where(schema.metric.c.status != MetricStatus.UNMONITORED))
  metricRows = conn.execute(sel)

  instances = {}
  for metricRow in metricRows:
    if ("/" in metricRow.name and
            "/" in metricRow.name[metricRow.name.index("/")+1:]):
      endOfNamespace = metricRow.name.index("/", metricRow.name.index("/")+1)
      namespace = metricRow.name[0:endOfNamespace]
    else:
      namespace = metricRow.name
    server = metricRow.server

    instances.setdefault(server,
                         {"server":metricRow.server,
                          "location":metricRow.location,
                          "namespace":namespace,
                          "name":metricRow.tag_name,
                          "status":MetricStatus.UNMONITORED,
                          "parameters":jsonDecode(metricRow.parameters),
                          "message":metricRow.message})

    instances[server]["status"] |= metricRow.status

    instances[server]["message"] = "\n".join(message for message in
                                             (instances[server]["message"],
                                              metricRow.message)
                                             if message)


  return instances.values()



def getInstanceStatusHistory(conn, server):
  """
  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  """
  sel = (select([schema.instance_status_history])
         .where(schema.instance_status_history.c.server == server))
  return conn.execute(sel).fetchall()



def listMetricIDsForInstance(conn, server):
  """ Returns a list of all metric uids for a particular instance

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  :param server: The name of a single server
  :returns: A list of metric ids
  :rtype: list
  """
  sel = select([schema.metric.c.uid]).where(schema.metric.c.server == server)
  result = conn.execute(sel)

  return [row.uid for row in result]



def getUnprocessedModelDataCount(conn):
  """Returns the count of unprocessed data for all active models.

  :param conn: SQLAlchemy connection object
  :type conn: sqlalchemy.engine.base.Connection
  """
  sel = (select([func.count(schema.metric_data.c.rowid)])
         .select_from(schema
                      .metric_data
                      .join(schema.metric,
                            schema.metric_data.c.uid == schema.metric.c.uid))
         .where(schema.metric_data.c.anomaly_score == None)
         .where(schema.metric.c.status == MetricStatus.ACTIVE))

  result = conn.execute(sel)
  return result.scalar()



def lockOperationExclusive(conn, operationLock):
  """Get Metric given metric uid

  This provides a more granular lock versus locking entire tables. It's needed
  in scenarios where sql-based integrity is not available or does not suffice.

  :param conn: SQLAlchemy;
  :type conn: sqlalchemy.engine.Connection

  :param operationLock: lock selector
  :type metricId: One of OperationLock constants; e.g., OperationLock.METRICS

  ::
      with engine.begin() as conn: # start transaction
        # Acquire exclusive lock for the operation
        repository.lockOperationExclusive(conn, OperationLock.METRICS)

        # Perfrom operations that need to be performed atomically under
        # protection from this lock

        <check if the model already exists>
        <if it doesn't exist, create a new one and initialize it>
        <send data to the model if needed>
  """
  sel = select([schema.lock.c.name]).where(schema.lock.c.name == operationLock)
  sel = sel.with_for_update(read=False)
  result = conn.execute(sel)

  assert result.rowcount, "operationLock=%r row not found" % (operationLock,)
