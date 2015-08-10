/*
 * Numenta Platform for Intelligent Computing (NuPIC)
 * Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
 * Numenta, Inc. a separate commercial license for this software code, the
 * following terms and conditions apply:
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 3 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses.
 *
 * http://numenta.org/licenses/
 *
 */

package com.numenta.core.data;

import com.numenta.core.R;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.utils.Log;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.DatabaseUtils;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteStatement;
import android.os.Looper;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Mobile Core Database Helper.
 * <p>
 * This is the core database interface implementation used to access the local database.
 * You should not instantiate this class directly, use
 * {@link com.numenta.core.app.YOMPApplication#getDatabase()} instead.
 * </p>
 * <p>
 * Each application could implement its own version of the core database by extending this class to
 * customize the database access.
 * </p>
 *
 * <b>NOTE:</b> Database operations may take a long time to return, so you should not
 * call it from the application main thread
 */
public class CoreDatabaseImpl implements CoreDatabase {

    static final String TAG = CoreDatabaseImpl.class.getCanonicalName();

    // @formatter:off
    /**
     * <p><b>Database Version.</b></p>
     *
     * <p>
     * Because the way android handles database migrations in
     * {@link android.database.sqlite.SQLiteOpenHelper#onUpgrade},
     * the database version is global for all applications using "mobile-core".
     * Whenever one of the applications using "mobile-core" updates the database this number must be
     * incremented and the application specific migration script should be placed under
     * "/assets/app/db_migrations" directory. For "mobile-core" migrations, the scripts should be
     * placed under "/assets/db_migrations" directory</p>
     * <p>
     * Migration scripts must be named after the new version and should contain the necessary
     * SQL script used to migrate from the "oldVersion" to the next version. Each SQL script will
     * run in order updating the database to the next version.</p>
     * <p>
     * For example, the file "/assets/db_migrations/23.sql" contains the SQL script required
     * to update the database from version "22" to version "23" and so on.</p>
     * <p><b>Change Log:</b></p>
     * <ul>
     * <li><b>Version 1</b>: Create initial database.</li>
     * <li><b>Version 2</b>: Add "last_rowid" to metric table | Tables: {@link Metric}</li>
     * <li><b>Version 3</b>: Added "readable_name" field | Tables: {@link Metric}</li>
     * <li><b>Version 4</b>: Remove "readable_name" field | Tables: {@link Metric}</li>
     * <li><b>Version 5</b>: Add new table "notification" | Tables: {@link Notification}</li>
     * <li><b>Version 6</b>: Rename "id" field to "_id" | Tables: {@link Notification}</li>
     * <li><b>Version 7</b>: Remove "location" index and add "anomaly_score" index | Tables: {@link Metric}, {@link MetricData}</li>
     * <li><b>Version 8</b>: Add "DEFAULT" value to "last_rowid" | Tables: {@link Metric}</li>
     * <li><b>Version 9</b>: No changes.</li>
     * <li><b>Version 10</b>: No changes.</li>
     * <li><b>Version 11</b>: No changes.</li>
     * <li><b>Version 12</b>: Change "last_rowid" to "NUMERIC" | Tables: {@link Metric}</li>
     * <li><b>Version 13</b>: Remove "parameters" field from metric table | Tables: {@link Metric}</li>
     * <li><b>Version 14</b>: Remove "description" field from metric table. Added "rowid" to metric_data table | Tables: {@link Metric}, {@link MetricData}</li>
     * <li><b>Version 15</b>: Added "server_name" field to metric table | Tables: {@link Metric}</li>
     * <li><b>Version 16</b>: Replace "NUMERIC" fields with "INTEGER" or "DATETIME" where appropriate | Tables: {@link Metric}, {@link MetricData}, {@link Notification}</li>
     * <li><b>Version 17</b>: Rename "server" field into "instance_id" | Tables: {@link Metric}</li>
     * <li><b>Version 18</b>: Add "last_timestamp" to metric table | Tables: {@link Metric}</li>
     * <li><b>Version 19</b>: Remove unused field "location" from metric table | Tables: {@link Metric}</li>
     * <li><b>Version 20</b>: Create primary key on metric_data table using "metric_id" and "rowid" | Tables: {@link MetricData}</li>
     * <li><b>Version 21</b>: Update notification table adding server based notification id. The original "_id" now represents OS notifications | Tables: {@link Notification}</li>
     * <li><b>Version 22</b>: Added new table "InstanceData" | Tables: {@link InstanceData}</li>
     * <li><b>Version 23</b>: Fix SQLite syntax for "UNIQUE" constraint | Tables: {@link Notification}</li>
     * <li><b>Version 24</b>: Update instance data table marking probation values with negative anomaly scores | Tables: {@link InstanceData}</li>
     * <li><b>Version 25</b>: Add new table "annotation" | Tables: {@link Annotation}</li>
     * <li><b>Version 26</b>: Add 'unit' column for custom metrics | Tables: {@link Metric}</li>
     * <li><b>Version 27</b>: Removed 'unit' column and added 'parameters' column | Tables: {@link Metric}</li>
     * </ul>
     */
    // @formatter:on
    public static final int DATABASE_VERSION = 27;

    // Cache All metrics definition in memory
    private final ConcurrentHashMap<String, Metric> _metricCache = new ConcurrentHashMap<String, Metric>();

    // Maps between instance id and instance name
    protected final ConcurrentHashMap<String, String> _instanceToName = new ConcurrentHashMap<String, String>();

    private final SQLiteHelper _sqlite;

    /**
     * Returns a list of valid aggregation types supported by this application.By default it will
     * support all types. Each application should configure the "aggregation_type_options" array in
     * their "core_config.xml" file with the valid values supported by the application.
     *
     * @see com.numenta.core.R.array#aggregation_type_options
     */
    public Set<AggregationType> getValidAggregationTypes() {
        return Collections.unmodifiableSet(_validAggregationTypes);
    }

    private final Set<AggregationType> _validAggregationTypes;

    // Factory used to create database objects
    private final CoreDataFactory _coreDataFactory;

    /**
     * Create a new database wrapper using the given context
     */
    public CoreDatabaseImpl(Context context) {
        this(context, new CoreDataFactoryImpl());
    }

    /**
     * Create a new database wrapper using the given context and factory used to create database
     * model objects
     *
     * @param context The context
     * @param factory Factory used to create database model objects
     */
    public CoreDatabaseImpl(Context context, CoreDataFactory factory) {
        _sqlite = new SQLiteHelper(context, getFileName(), getVersion());
        // Initialize aggregation type options supported by the application
        String[] options = context.getResources().getStringArray(R.array.aggregation_type_options);
        _validAggregationTypes = new HashSet<AggregationType>(options.length);
        for (String option : options) {
            _validAggregationTypes.add(AggregationType.valueOf(option));
        }
        _coreDataFactory = factory;
    }

    /**
     * <p>The current database version.</p>
     * <p>The database version is global for all applications using "mobile-core". Whenever one of
     * the applications using "mobile-core" needs to update the database this number must be
     * incremented and the application specific migration script should be placed under the apps
     * "/assets/apps/db_migrations" directory.</p>
     */
    @Override
    public int getVersion() {
        return DATABASE_VERSION;
    }

    /**
     * The database file name
     */
    @Override
    public String getFileName() {
        return "YOMP.db";
    }

    /**
     * @see SQLiteHelper#getReadableDatabase()
     */
    @Override
    public SQLiteDatabase getReadableDatabase() {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            throw new IllegalStateException(
                    "You should not access the database from the UI thread");
        }
        return _sqlite.getReadableDatabase();
    }

    /**
     * @see SQLiteHelper#getReadableDatabase()
     */
    @Override
    public SQLiteDatabase getWritableDatabase() {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            throw new IllegalStateException(
                    "You should not access the database from the UI thread");
        }
        return _sqlite.getWritableDatabase();
    }

    /**
     * Insert multiple metric data records in a single transaction, replacing existing values with
     * new ones.
     *
     * @param batch A {@link Collection} of {@link MetricData} batch to insert
     * @return {@code true}, if this insert is successful, {@code false}
     * otherwise.
     */
    @Override
    public boolean addMetricDataBatch(Collection<MetricData> batch) {

        if (batch.isEmpty()) {
            return false;
        }

        long lastRow;
        long rows = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        SQLiteStatement insertDataSQL = null;
        SQLiteStatement updateMetricSQL = null;
        Metric metric;
        long timestamp;
        int i;
        try {
            // Infer column names from content values
            ContentValues values = batch.iterator().next().getValues();
            Set<String> columns = values.keySet();
            insertDataSQL = preparedInsertStatement(db, MetricData.TABLE_NAME, columns, "IGNORE");
            updateMetricSQL = db.compileStatement("UPDATE metric SET last_timestamp = ? "
                    + "WHERE metric_id = ? AND last_timestamp < ?");

            for (MetricData metricData : batch) {
                // Bind columns
                insertDataSQL.clearBindings();
                values = metricData.getValues();
                i = 1;
                for (String col : columns) {
                    insertDataSQL.bindString(i, values.getAsString(col));
                    i++;
                }
                // Try to insert data
                lastRow = insertDataSQL.executeInsert();
                if (lastRow != -1) {
                    rows++;
                    // Update metric last timestamp
                    metric = getMetric(metricData.getMetricId());
                    timestamp = metricData.getTimestamp();
                    if (timestamp > metric.getLastTimestamp()) {

                        // Try to update the database
                        updateMetricSQL.clearBindings();
                        updateMetricSQL.bindLong(1, timestamp);
                        updateMetricSQL.bindString(2, metric.getId());
                        updateMetricSQL.bindLong(3, timestamp);

                        if (updateMetricSQL.executeUpdateDelete() > 0) {
                            // Update cached metric
                            metric.setLastTimestamp(timestamp);
                            updateMetricCache(metric);
                        }
                    }
                } else {
                    Log.w(TAG, "Metric " + metricData.getMetricId()
                            + "(" + metricData.getRowid() + ") was not inserted");
                }
            }
            db.setTransactionSuccessful();
            return rows > 0;
        } catch (Exception e) {
            Log.e(TAG, "Error A        } catch (Exception e) {\ndding metrics in batch", e);
        } finally {
            if (updateMetricSQL != null) {
                updateMetricSQL.close();
            }
            if (insertDataSQL != null) {
                insertDataSQL.close();
            }
            db.endTransaction();
        }
        return false;
    }

    /**
     * Deletes the metric and it's data from the database
     *
     * @return the number of rows affected
     */
    @Override
    public long deleteMetric(String id) {
        SQLiteDatabase db;
        long deleted = 0;
        db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            deleted = db.delete(Metric.TABLE_NAME, "metric_id = ?", new String[]{
                    id
            });
            if (deleted > 0) {
                removeMetricFromCache(id);
            } else {
                Log.w(TAG, "Metric " + id + " was not deleted");
            }
            db.setTransactionSuccessful();
        } catch (Exception e) {
            Log.e(TAG, "Error deleting metric", e);
        } finally {
            db.endTransaction();
        }
        return deleted;
    }

    protected Metric removeMetricFromCache(String id) {
        Metric metric = getMetricCache().remove(id);
        if (metric != null) {
            if (getMetricsByInstanceId(metric.getInstanceId()).isEmpty()) {
                _instanceToName.remove(metric.getInstanceId());
                // Remove annotations associated to this instance
                deleteAnnotationByInstanceId(metric.getInstanceId());
            }
        }
        return metric;
    }

    /**
     * Get metric data as a {@link android.database.Cursor}
     *
     * @param columns      A list of which columns to return. Passing null will
     *                     return all columns
     * @param from         return records from this date
     * @param to           return records up to this date
     * @param anomalyScore return records whose anomaly score are greater or
     *                     equal to this value. 0 for all scores.
     * @param limit        max number of records to return. 0 for no limit
     * @return A {@link Cursor} object, which is positioned before the first
     * entry. Note that {@link Cursor}s are not synchronized
     */
    @Override
    public Cursor getMetricData(String metricId, String columns[], Date from, Date to,
            float anomalyScore, int limit) {
        String selection = "";
        boolean append = false;
        if (from != null) {
            selection += "timestamp >= " + from.getTime();
            append = true;
        }
        if (to != null) {
            if (append) {
                selection += " AND ";
            }
            selection += "timestamp <= " + to.getTime();
            append = true;
        }
        if (anomalyScore > 0) {
            if (append) {
                selection += " AND ";
            }
            selection += "anomaly_score >= " + anomalyScore;
            append = true;
        }
        if (metricId != null) {
            if (append) {
                selection += " AND ";
            }
            selection += "metric_id = '" + metricId + "'";
        }
        // FIXME: Get distinct value. In version 1.0.1 there are some occasions
        // where the metric data table may contain duplicate records
        return getReadableDatabase().query(true, MetricData.TABLE_NAME, columns, selection, null,
                null, null, null, limit > 0 ? Integer.toString(limit) : null);

    }

    /**
     * Insert multiple instance data records in a single transaction, replacing existing values
     * with new ones.
     *
     * @param batch A {@link java.util.Collection} of {@link InstanceData} batch to insert
     * @return {@code true}, if this insert is successful, {@code false} otherwise.
     */
    @Override
    public boolean addInstanceDataBatch(Collection<InstanceData> batch) {
        if (batch == null || batch.size() == 0) {
            return false;
        }
        long rows = 0;
        long lastRow;
        SQLiteStatement insertDataSQL = null;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            // Infer column names from content values
            ContentValues values = batch.iterator().next().getValues();
            Set<String> columns = values.keySet();
            insertDataSQL = preparedInsertStatement(db, InstanceData.TABLE_NAME, columns,
                    "REPLACE");
            int i;
            for (InstanceData data : batch) {
                insertDataSQL.clearBindings();
                values = data.getValues();
                i = 1;
                // Bind columns
                for (String col : columns) {
                    insertDataSQL.bindString(i, values.getAsString(col));
                    i++;
                }
                lastRow = insertDataSQL.executeInsert();
                if (lastRow != -1) {
                    rows++;
                } else {
                    Log.w(TAG, "Failed to insert InstanceData for " + data.getInstanceId()
                            + "(" + data.getTimestamp() + ")");
                }
            }
            db.setTransactionSuccessful();
            return rows > 0;
        } catch (Exception e) {
            Log.e(TAG, "Error Adding InstanceData in batch", e);
        } finally {
            if (insertDataSQL != null) {
                insertDataSQL.close();
            }
            db.endTransaction();
        }
        return false;
    }

    /**
     * Get instance data as a {@link android.database.Cursor}
     *
     * @param instanceId   The instance id to get. Passing null will return all data
     * @param columns      A list of which columns to return. Passing null will
     *                     return all columns
     * @param aggregation  return records filtered by this aggregation period or null for all
     * @param from         return records from this date or null to ignore
     * @param to           return records up to this date or null to ignore
     * @param anomalyScore return records whose anomaly score are greater or
     *                     equal to this value. 0 for all scores.
     * @param limit        max number of records to return. 0 for no limit
     * @return A {@link android.database.Cursor} object, which is positioned before the first
     * entry. Note that {@link android.database.Cursor}s are not synchronized
     */
    @Override
    public Cursor getInstanceData(String instanceId, String[] columns, AggregationType aggregation,
            Date from, Date to, float anomalyScore, int limit) {

        String selection = "";
        boolean append = false;
        if (from != null) {
            selection += "timestamp >= " + from.getTime();
            append = true;
        }
        if (to != null) {
            if (append) {
                selection += " AND ";
            }
            selection += "timestamp <= " + to.getTime();
            append = true;
        }
        if (aggregation != null) {
            if (append) {
                selection += " AND ";
            }
            selection += "aggregation = " + aggregation.minutes();
        }
        if (anomalyScore > 0) {
            if (append) {
                selection += " AND ";
            }
            selection += "anomaly_score >= " + anomalyScore;
            append = true;
        }
        if (instanceId != null) {
            if (append) {
                selection += " AND ";
            }
            selection += "instance_id = '" + instanceId + "'";
        }
        // where the metric data table may contain duplicate records
        return getReadableDatabase().query(true, InstanceData.TABLE_NAME, columns, selection, null,
                null, null, null, limit > 0 ? Integer.toString(limit) : null);
    }

    /**
     * Return the last timestamp known to the database
     *
     * @return last time stamp
     */
    @Override
    public long getLastTimestamp() {
        long timestamp = 0;
        Collection<Metric> allMetrics = getMetricCache().values();
        for (Metric metric : allMetrics) {
            if (metric.getLastTimestamp() > timestamp) {
                timestamp = metric.getLastTimestamp();
            }
        }
        return timestamp;
    }

    protected void updateMetricCache(Metric metric) {
        getMetricCache().put(metric.getId(), metric);
        _instanceToName.put(metric.getInstanceId(), metric.getServerName());
    }

    /**
     * Returns a {@link Set} for all servers in this database
     *
     * @return {@link Set} containing Instance IDs.
     */
    @Override
    public Set<String> getAllInstances() {
        if (_instanceToName.isEmpty()) {
            loadMetricCache();
        }

        return Collections.unmodifiableSet(_instanceToName.keySet());
    }

    /**
     * Returns a {@link Collection} of all metrics in this database
     *
     * @return {@link Collection} containing the metrics
     */
    @Override
    public Collection<Metric> getAllMetrics() {
        return Collections.unmodifiableCollection(getMetricCache().values());
    }

    /**
     * Delete old records keeping the database size manageable.
     * <p>
     * Old records are records outside our data time window.
     *
     * @see com.numenta.core.app.YOMPApplication#getNumberOfDaysToSync()
     */
    @Override
    public synchronized int deleteOldRecords() {

        // Delete records older than a given value
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        cal.add(Calendar.DAY_OF_MONTH, -YOMPApplication.getNumberOfDaysToSync());
        int deleted = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            final String whereClause = "timestamp < " + cal.getTime().getTime();
            deleted = db.delete(MetricData.TABLE_NAME, whereClause, null);
            deleted += db.delete(InstanceData.TABLE_NAME, whereClause, null);
            deleted += db.delete(Notification.TABLE_NAME, whereClause, null);
            deleted += db.delete(Annotation.TABLE_NAME, whereClause, null);
            db.setTransactionSuccessful();
        } catch (Exception e) {
            Log.e(TAG, "Error deleting old records", e);
        } finally {
            db.endTransaction();
        }
        if (deleted > 0) {
            db.execSQL("vacuum");
        }
        return deleted;
    }

    /**
     * Returns a single metric definition given it's id
     *
     * @param id metric id
     * @return {@link Metric} or <code>null</code> if not found
     */
    @Override
    public Metric getMetric(String id) {
        return getMetricCache().get(id);
    }

    /**
     * Returns all metrics for the given instance
     *
     * @return {@link List} of {@link Metric}s for the given instanceId
     */
    @Override
    public ArrayList<Metric> getMetricsByInstanceId(String instanceId) {
        ArrayList<Metric> results = new ArrayList<Metric>();
        Collection<Metric> allMetrics = getMetricCache().values();
        for (Metric metric : allMetrics) {
            if (metric.getInstanceId().equals(instanceId)) {
                results.add(metric);
            }
        }
        return results;
    }


    @Override
    public void deleteInstance(String instance) {
        deleteInstanceData(instance);
        _instanceToName.remove(instance);
        // Remove annotations associated to this instance
        deleteAnnotationByInstanceId(instance);
        // Remove metrics associated to this instance
        ArrayList<Metric> metrics = getMetricsByInstanceId(instance);
        for (Metric metric : metrics) {
            deleteMetric(metric.getId());
        }
    }

    /**
     * Deletes instance data for the given instance id
     */
    @Override
    public void deleteInstanceData(String instanceId)
            throws SQLException {
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            db.delete(InstanceData.TABLE_NAME, "instance_id = ?", new String[]{
                    instanceId
            });
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    /**
     * Update instance data
     *
     * @param instanceData The new values
     */
    @Override
    public boolean updateInstanceData(InstanceData instanceData) {
        int rows = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            rows = db.update(InstanceData.TABLE_NAME, instanceData.getValues(),
                    "aggregation = ? AND instance_id = ? AND timestamp = ?",
                    new String[]{
                            Long.toString(instanceData.getAggregation()),
                            instanceData.getInstanceId(),
                            Long.toString(instanceData.getTimestamp())
                    });
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to add data to database", e);
        } finally {
            db.endTransaction();
        }
        return rows > 0;
    }

    /**
     * Add a new metric to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    @Override
    public long addMetric(Metric metric) {

        long rowid = -1;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            rowid = db.insertWithOnConflict(Metric.TABLE_NAME, null, metric.getValues(),
                    SQLiteDatabase.CONFLICT_REPLACE);
            if (rowid != -1) {
                updateMetricCache(metric);
            }
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to add data to database", e);
        } finally {
            db.endTransaction();
        }
        return rowid;
    }

    /**
     * Update metric values
     *
     * @param metric New metric values. Metric ID must exist or this call will
     *               fail
     * @return {@code true} if metric was updated {@code false} otherwise
     */
    @Override
    public boolean updateMetric(Metric metric) {
        int rows = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            rows = db.update(Metric.TABLE_NAME, metric.getValues(), "metric_id = ?",
                    new String[]{
                            metric.getId()
                    });
            if (rows > 0) {
                updateMetricCache(metric);
            }
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to add data to database", e);
        } finally {
            db.endTransaction();
        }
        return rows > 0;
    }

    /**
     * Marks a notification as read
     *
     * @param notificationId Id of the notification to mark as read
     * @return {@code true} if notification was updated {@code false} otherwise
     */
    @Override
    public boolean markNotificationRead(int notificationId) {
        int rows = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            ContentValues values = new ContentValues();
            values.put("read", 1);
            rows = db.update(Notification.TABLE_NAME, values, "_id = ?",
                    new String[]{
                            Integer.toString(notificationId)
                    });
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to update notification table in database", e);
        } finally {
            db.endTransaction();
        }
        return rows > 0;
    }

    /**
     * Add a new notification to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    @Override
    public int addNotification(String notificationId, String metricId, long timestamp,
            String description) {
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        int rowid = -1;
        try {
            ContentValues values = new ContentValues();
            values.put("notification_id", notificationId);
            values.put("metric_id", metricId);
            values.put("timestamp", timestamp);
            values.put("description", description);
            values.put("read", 0);
            rowid = (int) db.insertOrThrow(Notification.TABLE_NAME, null, values);
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to add data to database", e);
        } finally {
            db.endTransaction();
        }
        return rowid;
    }

    /**
     * Add a new {@link Annotation} to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    @Override
    public long addAnnotation(Annotation annotation) {
        long rowid = -1;
        // Make sure instance exist for annotation
        if (!_instanceToName.containsKey(annotation.getInstanceId())) {
            Log.e(TAG, "Failed to add annotation to database. Missing or unknown instance id");
            return -1;
        }
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            rowid = db.insertWithOnConflict(Annotation.TABLE_NAME, null,
                    annotation.getValues(), SQLiteDatabase.CONFLICT_REPLACE);
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Failed to add annotation to database", e);
        } finally {
            db.endTransaction();
        }
        return rowid;
    }

    /**
     * Delete {@link Annotation} from the database given it's id
     *
     * @return the number of rows deleted
     */
    @Override
    public long deleteAnnotation(String id) {
        long deleted = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            deleted = db.delete(Annotation.TABLE_NAME, "annotation_id = ?",
                    new String[]{
                            id
                    });
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Error deleting Annotation", e);
        } finally {
            db.endTransaction();
        }
        return deleted;
    }

    /**
     * Delete all {@link Annotation}s from the database associated with the
     * given instance ID
     */
    @Override
    public long deleteAnnotationByInstanceId(String instanceId) {
        long deleted = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            deleted = db.delete(Annotation.TABLE_NAME, "instance_id = ?",
                    new String[]{
                            instanceId
                    });
            db.setTransactionSuccessful();
        } catch (SQLException e) {
            Log.e(TAG, "Error deleting Annotation", e);
        } finally {
            db.endTransaction();
        }
        return deleted;
    }

    /**
     * Returns a single annotation given it's id
     *
     * @param id metric id
     * @return {@link Annotation} or <code>null</code> if not found
     */
    @Override
    public Annotation getAnnotation(String id) {
        Cursor cursor = getReadableDatabase().query(true, Annotation.TABLE_NAME,
                null, "annotation_id = ?", new String[]{
                        id + ""
                }, null,
                null, null, null);
        try {
            if (cursor.moveToFirst()) {
                return _coreDataFactory.createAnnotation(cursor);
            }
        } finally {
            cursor.close();
        }
        return null;
    }

    /**
     * Get annotations
     *
     * @param server Filter annotations by server
     * @param from   return records from this date
     * @param to     return records up to this date
     * @return {@link java.util.List} containing the {@link Annotation}s
     */
    @Override
    public List<Annotation> getAnnotations(String server, Date from, Date to) {
        StringBuilder selection = new StringBuilder();
        ArrayList<String> selectionArgs = new ArrayList<String>(3);
        boolean append = false;
        if (from != null) {
            selection.append("timestamp >= ?");
            selectionArgs.add(String.valueOf(from.getTime()));
            append = true;
        }
        if (to != null) {
            if (append) {
                selection.append(" AND ");
            }
            selection.append("timestamp <= ?");
            selectionArgs.add(String.valueOf(to.getTime()));
            append = true;
        }
        if (server != null) {
            if (append) {
                selection.append(" AND ");
            }
            selection.append("instance_id = ?");
            selectionArgs.add(String.valueOf(server));
        }
        Cursor cursor = null;
        try {
            ArrayList<Annotation> results = new ArrayList<Annotation>();
            cursor = getReadableDatabase().query(true, Annotation.TABLE_NAME,
                    null, selection.toString(),
                    selectionArgs.isEmpty() ? null
                            : selectionArgs.toArray(new String[selectionArgs.size()]),
                    null, null, "timestamp ASC, created ASC", null);
            while (cursor.moveToNext()) {
                results.add(_coreDataFactory.createAnnotation(cursor));
            }
            return results;
        } catch (Exception e) {
            Log.e(TAG, "Error getting server list", e);
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        return null;
    }

    /**
     * Returns a {@link Collection} of all {@link Annotation} in this database
     *
     * @return {@link Collection} containing the {@link Annotation}s
     */
    @Override
    public Collection<Annotation> getAllAnnotations() {
        Cursor cursor = null;
        try {
            ArrayList<Annotation> results = new ArrayList<Annotation>();
            SQLiteDatabase db = getReadableDatabase();
            cursor = db.query(true, Annotation.TABLE_NAME,
                    null, null, null, null, null, null, null);
            while (cursor.moveToNext()) {
                results.add(_coreDataFactory.createAnnotation(cursor));
            }
            return results;
        } catch (Exception e) {
            Log.e(TAG, "Error getting server list", e);
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        return null;
    }

    /**
     * Returns a {@link Collection} of all {@link Notification}s in this database
     *
     * @return {@link Collection} containing the {@link Notification}s
     */
    @Override
    public Collection<Notification> getAllNotifications() {
        Cursor cursor = null;
        try {
            ArrayList<Notification> results = new ArrayList<Notification>();
            SQLiteDatabase db = getReadableDatabase();
            cursor = db.query(true, Notification.TABLE_NAME,
                    null, null, null, null, null, null, null);
            while (cursor.moveToNext()) {
                results.add(_coreDataFactory.createNotification(cursor));
            }
            return results;
        } catch (Exception e) {
            Log.e(TAG, "Error getting server list", e);
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        return null;
    }

    /**
     * Clears the notification table completely.
     */
    @Override
    public long deleteAllNotifications() {
        long deleted = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            deleted = db.delete(Notification.TABLE_NAME, "1", null);
            db.setTransactionSuccessful();
        } catch (Exception e) {
            Log.e(TAG, "Error deleting notifications", e);
        } finally {
            db.endTransaction();
        }
        return deleted;
    }

    /**
     * Deletes one notification by localId.
     *
     * @return the number of rows deleted
     */
    @Override
    public long deleteNotification(int localId) {
        long deleted = 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            deleted = db.delete(Notification.TABLE_NAME, "_id = ?",
                    new String[]{
                            String.valueOf(localId)
                    });
            db.setTransactionSuccessful();
        } catch (Exception e) {
            Log.e(TAG, "Error deleting Notification", e);
        } finally {
            db.endTransaction();
        }
        return deleted;
    }

    /**
     * Returns Notification object given an localId.
     */
    @Override
    public Notification getNotificationByLocalId(int localId) {
        Cursor cursor = getReadableDatabase().query(true, Notification.TABLE_NAME,
                null, "_id = ?", new String[]{
                        localId + ""
                }, null,
                null, null, null);
        try {
            if (cursor.moveToFirst()) {
                return new Notification(cursor);
            }
        } finally {
            cursor.close();
        }
        return null;
    }

    /**
     * Returns the number of unread Notifications
     */
    @Override
    public long getUnreadNotificationCount() {
        return DatabaseUtils.queryNumEntries(getReadableDatabase(), Notification.TABLE_NAME,
                "read = 0");
    }

    /**
     * Returns the prepared "INSERT" {@link SQLiteStatement}.
     *
     * @param database {@link SQLiteDatabase}, usually returned from
     *                 {@link #getWritableDatabase()}
     * @param table    Table name. For example {@link MetricData#TABLE_NAME}
     * @param columns  The column names
     * @param conflict Conflict resolution : {@literal ROLLBACK},
     *                 {@literal ABORT}, {@literal FAIL}, {@literal IGNORE},
     *                 {@literal REPLACE} or {@code null}
     * @return Compiled {@link SQLiteStatement} ready to be used in "INSERT"
     * batch operations
     * @see <a href="http://www.sqlite.org/lang_conflict.html">http://www.sqlite.org/lang_conflict.html</a>
     */
    protected SQLiteStatement preparedInsertStatement(SQLiteDatabase database, String table,
            Set<String> columns, String conflict) {
        if (columns == null || columns.size() == 0) {
            return null;
        }
        StringBuilder sql = new StringBuilder(128);
        sql.append("INSERT");
        if (conflict != null && !conflict.trim().isEmpty()) {
            sql.append(" OR ").append(conflict);
        }
        sql.append(" INTO ");
        sql.append(table);
        sql.append(" (");
        int size = columns.size();
        int i = 0;
        for (String name : columns) {
            sql.append((i > 0) ? "," : "");
            sql.append(name);
            i++;
        }
        sql.append(')');
        sql.append(" VALUES (");
        for (i = 0; i < size; i++) {
            sql.append((i > 0) ? ",?" : "?");
        }
        sql.append(')');
        return database.compileStatement(sql.toString());
    }

    @Override
    public long getNotificationCount() {
        return DatabaseUtils.queryNumEntries(getReadableDatabase(),
                Notification.TABLE_NAME);
    }

    /**
     * Returns the server name given it's instance id
     *
     * @return The server name or the instanceId if name is not present
     */
    @Override
    public String getServerName(String instanceId) {
        // Make sure to populate cache
        getAllInstances();
        String name = _instanceToName.get(instanceId);
        return name != null && !name.trim().isEmpty() ? name : instanceId;
    }

    private volatile boolean _loadingMetricCache;

    private void loadMetricCache() {
        if (_loadingMetricCache) {
            return;
        }
        synchronized (this) {
            if (_loadingMetricCache) {
                return;
            }
            _loadingMetricCache = true;
        }

        Cursor cursor = null;
        Metric metric;
        try {
            invalidateMetricCache();

            SQLiteDatabase db = getReadableDatabase();
            cursor = db.query(true, Metric.TABLE_NAME,
                    null, null, null, null, null, null, null);
            while (cursor.moveToNext()) {
                metric = _coreDataFactory.createMetric(cursor);
                _instanceToName.putIfAbsent(metric.getInstanceId(), metric.getServerName());
                _metricCache.put(metric.getId(), metric);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error getting server list", e);
            _instanceToName.clear();
        } finally {
            if (cursor != null) {
                cursor.close();
            }
            _loadingMetricCache = false;
        }
    }

    protected void invalidateMetricCache() {
        _instanceToName.clear();
        _metricCache.clear();
    }


    /**
     * Delete all data from the database
     */
    private volatile boolean _deletingAllData;

    @Override
    public void deleteAll() {
        if (_deletingAllData) {
            return;
        }

        synchronized (this) {
            if (_deletingAllData) {
                return;
            }
            _deletingAllData = true;
        }

        SQLiteDatabase db = getWritableDatabase();
        db.beginTransactionNonExclusive();
        try {
            db.delete(Annotation.TABLE_NAME, null, null);
            db.delete(Notification.TABLE_NAME, null, null);
            db.yieldIfContendedSafely();
            db.delete(MetricData.TABLE_NAME, null, null);
            db.yieldIfContendedSafely();
            db.delete(Metric.TABLE_NAME, null, null);
            db.yieldIfContendedSafely();
            db.setTransactionSuccessful();
            invalidateMetricCache();
        } catch (Exception e) {
            Log.e(TAG, "Error deleting all tables", e);
        } finally {
            db.endTransaction();
            _deletingAllData = false;
        }
    }

    @Override
    public CoreDataFactory getDataFactory() {
        return _coreDataFactory;
    }

    protected Map<String, Metric> getMetricCache() {
        if (_metricCache.isEmpty()) {
            loadMetricCache();
        }
        return _metricCache;
    }
}
