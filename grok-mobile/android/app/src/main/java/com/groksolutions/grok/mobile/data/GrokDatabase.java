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

package com.YOMPsolutions.YOMP.mobile.data;

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.CoreDatabaseImpl;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Pair;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.DatabaseUtils;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteDoneException;
import android.database.sqlite.SQLiteStatement;
import android.util.LruCache;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * {@inheritDoc}
 *
 * Extends <b>mobile-core</b> database with <b>YOMP</b> specific API
 */
public class YOMPDatabase extends CoreDatabaseImpl {

    public static final int YOMP_DATABASE_VERSION = 0;

    // Select maximum anomaly score group by X intervals.
    // $1 - time interval in milliseconds. Use AggregationType#milliseconds()
    // $2 - last time stamp
    // $3 - number of records
    // $4 - probation period (rowid)
    private static final String AGGREGATED_METRIC_ANOMALY_SCORE =
            "SELECT (timestamp/%1$d)*%1$d AS timestamp,"
                    + " MAX(CASE WHEN rowid >= %4$d THEN anomaly_score ELSE 0 END) AS anomaly_score,"
                    + " MAX(CASE WHEN rowid < %4$d THEN anomaly_score else 0 END) AS probation_score,"
                    + " MAX(rowid) as rowid "
                    + "FROM metric_data "
                    + "WHERE metric_id = ? AND timestamp <= %2$d "
                    + "GROUP BY 1 ORDER BY timestamp DESC LIMIT %3$d;";

    private static final String AGGREGATED_INSTANCE_ANOMALY_SCORE =
            "SELECT timestamp, anomaly_score FROM instance_data "
                    + "WHERE aggregation = ? "
                    + "AND instance_id = ? "
                    + "AND timestamp <= %2$d "
                    + "ORDER BY timestamp DESC LIMIT %3$d";

    private static final String DELETE_INSTANCE_DATA
            = "DELETE FROM instance_data WHERE instance_id = ?";

    // $1 - time interval in minutes. Use AggregationType#minutes()
    // $2 - time interval in milliseconds. Use AggregationType#milliseconds()
    private static final String CREATE_INSTANCE_DATA =
            "INSERT INTO instance_data "
                    + "SELECT %1$d AS \"aggregation\","
                    + " instance_id, "
                    + " (timestamp/%2$d)*%2$d AS \"timestamp\","
                    + " CASE WHEN MAX(rowid) < 1000"
                    + "   THEN -MAX(anomaly_score)"
                    + "   ELSE MAX(anomaly_score) "
                    + " END AS \"anomaly_score\" "
                    + "FROM metric JOIN metric_data ON metric.metric_id = metric_data.metric_id "
                    + "WHERE instance_id = ? GROUP BY 2, 3";

    private static final String INSERT_INSTANCE_DATA_ANOMALY_SCORE
            = "INSERT OR IGNORE INTO instance_data"
            + " (aggregation, instance_id, timestamp, anomaly_score)"
            + " VALUES (?, ?, ?, ?) ";

    private static final String UPDATE_INSTANCE_DATA_ANOMALY_SCORE
            = "UPDATE instance_data"
            + " SET anomaly_score = "
            + "   CASE WHEN ?"
            + "     THEN MIN(anomaly_score, ?)"
            + "     ELSE MAX(anomaly_score, ?) "
            + "   END"
            + " WHERE aggregation = ? AND instance_id = ? AND timestamp = ?";

    private static final String TAG = YOMPDatabase.class.getSimpleName();


    // Cache aggregated results.
    private final ConcurrentHashMap<String, List<Pair<Long, Float>>> _aggregateInstanceCache
            = new ConcurrentHashMap<>();

    private final LruCache<String, List<Pair<Long, Float>>> _aggregateMetricCache
            = new LruCache<>(100);

    public YOMPDatabase(Context context) {
        super(context);
    }

    /**
     * <p>The current database version.</p>
     */
    @Override
    public int getVersion() {
        return YOMP_DATABASE_VERSION * 1000 + super.getVersion();
    }

    /**
     * The database file name
     */
    @Override
    public String getFileName() {
        return "YOMP.db";
    }

    private void invalidateMetricDataCache() {
        _aggregateMetricCache.evictAll();
        _aggregateInstanceCache.clear();
    }

    @Override
    protected void invalidateMetricCache() {
        super.invalidateMetricCache();
        invalidateMetricDataCache();
    }

    private void removeInstanceDataCache(String instanceId) {
        synchronized (_aggregateInstanceCache) {
            for (AggregationType aggregation : getValidAggregationTypes()) {
                _aggregateInstanceCache.remove(instanceId + aggregation.name());
            }
        }
    }

    private void removeMetricDataCache(Metric metric) {
        synchronized (_aggregateMetricCache) {
            // Remove cached metric data
            for (AggregationType aggregation : getValidAggregationTypes()) {
                _aggregateMetricCache.remove(metric.getId() + aggregation.name());
            }
        }
        // Remove cached instance data
        removeInstanceDataCache(metric.getInstanceId());
    }


    protected Metric removeMetricFromCache(String id) {
        Metric metric = super.removeMetricFromCache(id);
        if (metric != null) {
            removeMetricDataCache(metric);
        }
        return metric;
    }


    public void addInstance(Instance instance) {
        refreshInstanceData(getWritableDatabase(), instance.getId());
        removeInstanceDataCache(instance.getId());
        _instanceToName.put(instance.getId(), instance.getName());
    }

    /**
     * Rebuild all instances anomaly scores based on the current metric data
     * values stored in the database for the given instance id
     */
    public void refreshInstanceData(String instanceId) {
        refreshInstanceData(getWritableDatabase(), instanceId);
        removeInstanceDataCache(instanceId);
    }

    /**
     * Get the aggregated metric score for the given {@code metricId}, grouped
     * by the given {@link AggregationType}, sorted by date in descending order,
     * limiting the results to dates below the given {@code timestamp} up to
     * {@code limit} records
     *
     * @return A {@link java.util.List} containing the aggregated metric data grouped by
     * the {@link AggregationType} interval, sorted by date in
     * descending order
     * @see com.numenta.core.app.YOMPApplication#getTotalBarsOnChart()
     */
    public List<Pair<Long, Float>> getAggregatedScoreByMetricId(String metricId,
            AggregationType aggregation, long timestamp, int limit) {
        if (!getValidAggregationTypes().contains(aggregation)) {
            throw new IllegalArgumentException("'AggregationType' cannot be " + aggregation);
        }

        // Cache results by metric ID and aggregation type
        String key = metricId + aggregation;
        List<Pair<Long, Float>> cached;
        synchronized (_aggregateMetricCache) {
            cached = _aggregateMetricCache.get(key);
            if (cached == null) {
                // Cache all the data
                int size = YOMPApplication.getNumberOfDaysToSync() * 24 * 60 / aggregation
                        .minutes();
                cached = getAggregatedAnomalyScore(aggregation, size,
                        AGGREGATED_METRIC_ANOMALY_SCORE, metricId);
                _aggregateMetricCache.put(key, cached);
            }
        }
        // Filter results from cache
        ArrayList<Pair<Long, Float>> results = new ArrayList<>();
        if (cached != null) {
            int len = limit;
            for (Pair<Long, Float> row : cached) {
                if (len == 0) {
                    break;
                }
                if (timestamp > 0 && row.first > timestamp) {
                    continue;
                }
                results.add(0, row);
                len--;
            }
        }
        return results;
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
        int deleted = super.deleteOldRecords();
        if (deleted > 0) {
            invalidateMetricDataCache();
        }
        return deleted;
    }

    /**
     * Get the aggregated instance score for the given {@code instanceId},
     * grouped by the given {@link AggregationType}, limiting the results to
     * dates below the given {@code timestamp} and the number of bars shown on
     * the chart
     *
     * @param instanceId  The instance ID of the server we are calculating the
     *                    aggregate score
     * @param aggregation The {@link AggregationType} to use
     * @param timestamp   Get records up to this timestamp
     * @param limit       The number of records to return
     * @return A {@link List} containing the aggregated metric data grouped by
     * the {@link AggregationType} interval
     */
    public List<Pair<Long, Float>> getAggregatedScoreByInstanceId(String instanceId,
            AggregationType aggregation, long timestamp, int limit) {
        if (!getValidAggregationTypes().contains(aggregation)) {
            throw new IllegalArgumentException("'AggregationType' cannot be " + aggregation);
        }

        // Cache results by instance ID and aggregation type
        List<Pair<Long, Float>> cached;
        String key = instanceId + aggregation.name();
        cached = _aggregateInstanceCache.get(key);
        if (cached == null) {
            // Cache all the data
            int size = YOMPApplication.getNumberOfDaysToSync() * 24 * 60
                    / aggregation.minutes();
            cached = getAggregatedAnomalyScore(aggregation, size,
                    AGGREGATED_INSTANCE_ANOMALY_SCORE,
                    Integer.toString(aggregation.minutes()), instanceId);
            _aggregateInstanceCache.put(key, cached);
            Log.d(TAG, "Loading instance data for " + key);
        }
        // Filter results from cache
        ArrayList<Pair<Long, Float>> results = new ArrayList<>(limit);
        if (cached != null) {
            int len = limit;
            for (Pair<Long, Float> row : cached) {
                if (len == 0) {
                    break;
                }
                if (timestamp > 0 && row.first > timestamp) {
                    continue;
                }
                results.add(0, row);
                len--;
            }
        }
        return results;
    }

    /**
     * Refresh instance data contents by re-aggregating the current metric data values
     * into the instance data
     */
    public void refreshInstanceData(SQLiteDatabase db, String instanceId) throws SQLException {
        db.beginTransactionNonExclusive();
        try {
            db.execSQL(DELETE_INSTANCE_DATA, new String[]{
                    instanceId
            });
            for (AggregationType aggregation : getValidAggregationTypes()) {
                String query = String
                        .format(Locale.US, CREATE_INSTANCE_DATA, aggregation.minutes(),
                                aggregation.milliseconds());
                db.execSQL(query, new String[]{
                        instanceId
                });
            }
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    /**
     * Insert multiple metric data records in a single transaction, replacing existing values with
     * new ones.
     *
     * @param batch A {@link java.util.Collection} of {@link com.numenta.core.data.MetricData}
     *              batch
     *              to insert
     * @return {@code true}, if this insert is successful, {@code false}
     * otherwise.
     */
    @Override
    public boolean addMetricDataBatch(Collection<MetricData> batch) {
        if (batch == null || batch.size() == 0) {
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
        try {
            // Infer column names from content values
            ContentValues values = batch.iterator().next().getValues();
            Set<String> columns = values.keySet();
            insertDataSQL = preparedInsertStatement(db, MetricData.TABLE_NAME, columns, "IGNORE");
            updateMetricSQL = db.compileStatement("UPDATE metric SET last_timestamp = ? "
                    + "WHERE metric_id = ? AND last_timestamp < ?");
            int i;
            for (MetricData metricData : batch) {
                // Bind columns
                insertDataSQL.clearBindings();
                values = metricData.getValues();
                i = 1;
                // Bind columns
                for (String col : columns) {
                    insertDataSQL.bindString(i, values.getAsString(col));
                    i++;
                }

                // Try to insert data
                lastRow = insertDataSQL.executeInsert();
                if (lastRow != -1) {
                    rows++;
                    // Data was successfully inserted, update caches.
                    removeMetricDataCache(getMetric(metricData.getMetricId()));

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

                    // Update instance aggregated data associated with this
                    // metric
                    updateInstanceDataAnomalyScore(db,
                            metric.getInstanceId(),
                            metricData.getTimestamp(), metricData.getAnomalyScore(),
                            metricData.getRowid());

                } else {
                    Log.w(TAG, "Metric " + metricData.getMetricId()
                            + "(" + metricData.getRowid() + ") was not inserted");
                }
            }
            db.setTransactionSuccessful();
            return rows > 0;
        } catch (Exception e) {
            Log.e(TAG, "Error Adding metrics in batch", e);
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
     * Update instance anomaly score for the given timestamp and instance id
     */
    public void updateInstanceDataAnomalyScore(SQLiteDatabase db, String instanceId, long timestamp,
            float score, long rowid) throws SQLException {
        SQLiteStatement updateStmt = null;
        SQLiteStatement insertStmt = null;

        db.beginTransactionNonExclusive();
        try {
            insertStmt = db.compileStatement(INSERT_INSTANCE_DATA_ANOMALY_SCORE);
            updateStmt = db.compileStatement(UPDATE_INSTANCE_DATA_ANOMALY_SCORE);

            // Update probation period
            int probation = 0;
            // Mark learning period with negative scores
            float probationScore = score;
            if (rowid < YOMPApplication.getLearningThreshold()) {
                probationScore = -score;
                probation = 1;
            }

            // Update aggregated values
            for (AggregationType aggregation : getValidAggregationTypes()) {
                long roundedTS = (timestamp / aggregation.milliseconds())
                        * aggregation.milliseconds();
                insertStmt.clearBindings();
                insertStmt.bindLong(1, aggregation.minutes());
                insertStmt.bindString(2, instanceId);
                insertStmt.bindLong(3, roundedTS);
                insertStmt.bindDouble(4, probationScore);
                insertStmt.executeUpdateDelete();

                updateStmt.clearBindings();
                updateStmt.bindLong(1, probation);
                updateStmt.bindDouble(2, probationScore);
                updateStmt.bindDouble(3, probationScore);
                updateStmt.bindLong(4, aggregation.minutes());
                updateStmt.bindString(5, instanceId);
                updateStmt.bindLong(6, roundedTS);
                updateStmt.executeUpdateDelete();

            }
            db.setTransactionSuccessful();
        } finally {
            if (updateStmt != null) {
                updateStmt.close();
            }
            if (insertStmt != null) {
                insertStmt.close();
            }
            db.endTransaction();
        }
    }


    private List<Pair<Long, Float>> getAggregatedAnomalyScore(AggregationType aggregation,
            int size, String queryTemplate, String... args) {

        if (!getValidAggregationTypes().contains(aggregation)) {
            throw new IllegalArgumentException("'AggregationType' cannot be " + aggregation);
        }
        // Last time bucket
        long lastTimestamp = getLastTimestamp();
        if (lastTimestamp == 0) {
            return Collections.emptyList();
        }

        // Round to the closest time interval (5 minutes, 1 hour or 8 hours)
        long timeInterval = aggregation.milliseconds();
        lastTimestamp = (lastTimestamp / timeInterval) * timeInterval;

        // Build query based on aggregation interval.
        String query = String.format(Locale.US, queryTemplate, aggregation.milliseconds(),
                lastTimestamp + timeInterval, size, YOMPApplication.getLearningThreshold());
        ArrayList<Pair<Long, Float>> results = new ArrayList<>(size);
        Cursor cursor = null;
        try {
            cursor = getReadableDatabase().rawQuery(query, args);
            int rowidIdx = cursor.getColumnIndex("rowid");
            int timestampIdx = cursor.getColumnIndex("timestamp");
            int anomalyScoreIdx = cursor.getColumnIndex("anomaly_score");
            int probationScoreIdx = cursor.getColumnIndex("probation_score");
            int i = 0;
            long timestamp, expectedTimestamp;
            while (i < size) {
                expectedTimestamp = lastTimestamp - timeInterval * i++;
                if (cursor.moveToNext()) {
                    timestamp = cursor.getLong(timestampIdx);
                    while (timestamp < expectedTimestamp) {
                        results.add(new Pair<Long, Float>(expectedTimestamp, null));
                        expectedTimestamp = lastTimestamp - timeInterval * i++;
                    }
                    if (timestamp == expectedTimestamp) {
                        float score = cursor.getFloat(anomalyScoreIdx);
                        if (rowidIdx != -1) {
                            int rowid = cursor.getInt(rowidIdx);
                            if (rowid < YOMPApplication.getLearningThreshold()) {
                                // Mark probationary period with negative anomaly score
                                if (probationScoreIdx != -1) {
                                    score = -cursor.getFloat(probationScoreIdx);
                                } else {
                                    score = -score;
                                }
                            }
                        }
                        results.add(new Pair<>(expectedTimestamp, score));
                    }
                } else {
                    results.add(new Pair<Long, Float>(expectedTimestamp, null));
                }
            }
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        return results;
    }

    /**
     * Get the metric value associated to the given metric at the given
     * timestamp
     *
     * @param metricId  The metric Id
     * @param timestamp The exact timestamp
     * @return Metric raw value or {@code Double.NaN} if no value is found
     */
    public float getMetricValue(String metricId, long timestamp) {
        try {
            String result = DatabaseUtils.stringForQuery(getReadableDatabase(),
                    "select metric_value from metric_data where metric_id = ? and timestamp = ?",
                    new String[]{
                            metricId, Long.toString(timestamp)
                    });
            if (result != null) {
                return Float.parseFloat(result);
            }
            return Float.NaN;
        } catch (NumberFormatException e) {
            return Float.NaN;
        } catch (SQLiteDoneException e) {
            return Float.NaN;
        }
    }

    /**
     * Returns the metric last know timestamp known in the database
     *
     * @return The metric last timestamp
     */
    public long getMetricLastTimestamp(String metricId) {
        Metric metric = getMetric(metricId);
        if (metric != null) {
            return metric.getLastTimestamp();
        }
        return 0;
    }

    /**
     * Gets a cursor over the notification table for views to use when
     * populating UI.
     */
    public Cursor getNotificationCursor() {
        return getReadableDatabase()
                .query(true, Notification.TABLE_NAME, null, null, null, null, null,
                        "timestamp DESC", null);
    }
}
