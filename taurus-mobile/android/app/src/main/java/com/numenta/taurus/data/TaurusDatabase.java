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

package com.numenta.taurus.data;


import com.numenta.core.data.CoreDatabaseImpl;
import com.numenta.core.data.InstanceData;
import com.numenta.core.data.Metric;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.TaurusApplication;

import android.content.Context;
import android.database.Cursor;
import android.database.SQLException;
import android.os.AsyncTask;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentSkipListMap;

// @formatter:off
/**
 * {@inheritDoc}
 *
 * Extends <b>mobile-core</b> database with <b>taurus</b> specific API
 *
 */
 // @formatter:on
public class TaurusDatabase extends CoreDatabaseImpl {

    // @formatter:off
    /**
     * <p><b>Taurus Database Version.</b></p>
     * <p>
     * <p><b>Change Log:</b></p>
     * <ul>
     * <li><b>Version 31</b>: Clear metric data and add instance data support.</li>
     * <li><b>Version 32</b>: Add 'metric_mask' to 'instance_data'.</li>
     * </ul>
     */
    // @formatter:on
    public static final int TAURUS_DATABASE_VERSION = 32;

    private static final String TAG = TaurusDatabase.class.getSimpleName();

    // Cache instance data. Map<InstanceID, List<SortedMap<timestamp, anomalyScore>>>
    private final ConcurrentHashMap<String, SortedMap<Long, AnomalyValue>> _instanceDataCache
            = new ConcurrentHashMap<String,SortedMap<Long,AnomalyValue>>();

    // Most recent timestamp stored in the database
    private long _lastTimestamp;

    // Oldest timestamp stored in the database
    private long _firstTimestamp;

    // The last time the database was updated
    private long _lastUpdated;

    public TaurusDatabase(Context context, TaurusDataFactory factory) {
        super(context, factory);
        // Load all instance data into memory in the background
        // After the initial load the cache is kept up to date
        AsyncTask.execute(new Runnable() {
            @Override
            public void run() {
                Cursor data = null;
                try {
                    String instanceId;
                    long timestamp;
                    float anomaly;
                    int metricMask;
                    SortedMap<Long, AnomalyValue> values;
                    _lastTimestamp = 0;

                    // Load most recent data first
                    long to = DataUtils.floorTo60minutes(System.currentTimeMillis());
                    long from = to - DataUtils.MILLIS_PER_DAY;
                    long oldestTimestamp = to;

                    // Load one day at the time to avoid long initial delay on phones with slow disk
                    for (int i = 0; i < TaurusApplication.getNumberOfDaysToSync(); i++) {
                        data = getReadableDatabase().query(true, InstanceData.TABLE_NAME,
                                new String[]{
                                        "instance_id", "timestamp", "anomaly_score", "metric_mask"
                                },
                                "timestamp >= ? AND timestamp <= ?",
                                new String[]{Long.toString(from), Long.toString(to)},
                                null, null, null, null);

                        // Cache all results for each day
                        while (data.moveToNext()) {
                            instanceId = data.getString(0);
                            timestamp = data.getLong(1);
                            anomaly = data.getFloat(2);
                            metricMask = data.getInt(3);

                            // Add new value for instance
                            values = getInstanceCachedValues(instanceId);
                            values.put(timestamp, new AnomalyValue(anomaly, metricMask));

                            // Update last timestamp value
                            if (timestamp > _lastTimestamp) {
                                _lastTimestamp = timestamp;
                            }
                            // Update first timestamp value
                            if (timestamp < oldestTimestamp) {
                                oldestTimestamp = timestamp;
                            }
                        }

                        // Previous day
                        from -= DataUtils.MILLIS_PER_DAY;
                        to -= DataUtils.MILLIS_PER_DAY;
                    }
                    // Wait until we read all the data before updating oldest timestamp in the database
                    _firstTimestamp = oldestTimestamp;
                } catch (Exception e) {
                    Log.e(TAG, "Error getting instance data", e);
                } finally {
                    // Make sure to close cursor
                    if (data != null) {
                        data.close();
                    }
                }
                // Initialize the last update time value
                _lastUpdated = System.currentTimeMillis();
            }
        });
    }

    /**
     * Get instance cached values map. This method will initialize the values map if necessary.
     * Use this method to access the value map stored in {@link #_instanceDataCache}
     *
     * @param instanceId The instance ID
     * @return A modifiable map containing the anomaly values for the given instance, sorted by time
     */
    SortedMap<Long, AnomalyValue> getInstanceCachedValues(String instanceId) {
        // Create values entry for instance if necessary
        SortedMap<Long, AnomalyValue> values = _instanceDataCache.get(instanceId);
        if (values == null) {
            // Keep results sorted by timestamp
            values = new ConcurrentSkipListMap<Long,AnomalyValue>();
            SortedMap<Long, AnomalyValue> oldValues = _instanceDataCache
                    .putIfAbsent(instanceId, values);
            if (oldValues != null) {
                values = oldValues;
            }
        }

        return values;
    }

    /**
     * Update instance data cache with new values
     *
     * @param data The new {@link com.numenta.taurus.data.InstanceData} value
     * @return {@code true} if cache was updated, {@code false} otherwise
     */
    boolean updateInstanceDataCache(InstanceData data) {
        // Get cached values
        SortedMap<Long, AnomalyValue> values = getInstanceCachedValues(data.getInstanceId());

        // Check if values are different
        long timestamp = data.getTimestamp();
        AnomalyValue oldValue = values.get(timestamp);
        AnomalyValue newValue = new AnomalyValue(data.getAnomalyScore(),
                ((com.numenta.taurus.data.InstanceData) data).getMetricMask());
        if (oldValue == null || !oldValue.equals(newValue)) {
            // Update cached values
            values.put(timestamp, newValue);
            if (timestamp > _lastTimestamp) {
                _lastTimestamp = timestamp;
            }
            if (timestamp < _firstTimestamp) {
                _firstTimestamp = timestamp;
            }
            _lastUpdated = System.currentTimeMillis();

            return true;
        }
        return false;
    }

    /**
     * Get instance data
     *
     * @param instanceId The instance to get data from
     * @param from       return records from this timestamp or 0 to ignore
     * @param to         return records up to this timestamp or 0 to ignore
     * @return List of {@link AnomalyValue} sorted by timestamp
     */
    public List<Pair<Long, AnomalyValue>> getInstanceData(String instanceId, long from, long to) {
        if (to == 0) {
            // Use current time as upper limit
            to = System.currentTimeMillis();
        }
        ArrayList<Pair<Long, AnomalyValue>> results = new ArrayList<Pair<Long,AnomalyValue>>();
        // Get instance cached values
        SortedMap<Long, AnomalyValue> cached = getInstanceCachedValues(instanceId);
        if (!cached.isEmpty()) {
            // Get all entries for the given period including both "from" and "to" in the result
            Set<Map.Entry<Long, AnomalyValue>> entries = cached.subMap(from, to + 1).entrySet();
            for (Map.Entry<Long, AnomalyValue> row : entries) {
                results.add(new Pair<Long,AnomalyValue>(row.getKey(), row.getValue()));
            }
        }
        return results;
    }

    /**
     * Returns the stock symbol for the given instance/company
     *
     * @param instanceId The instanceId of the company to get the symbol
     * @return The stock ticker symbol
     */
    public String getTickerSymbol(String instanceId) {
        ArrayList<Metric> metrics = getMetricsByInstanceId(instanceId);
        String symbol = null;
        if (!metrics.isEmpty()) {
            // FIXME: TAUR-817: Create taurus specific instance table
            symbol = metrics.get(0).getUserInfo("symbol");
        }
        return symbol;
    }

    @Override
    public long getLastTimestamp() {
        return _lastTimestamp;
    }

    public long getFirstTimestamp() {
        return _firstTimestamp;
    }

    /**
     * The last time the database was updated
     */
    public long getLastUpdated() {
        return _lastUpdated;
    }

    /**
     * Taurus database version.
     */
    @Override
    public int getVersion() {
        return TAURUS_DATABASE_VERSION;
    }

    @Override
    public boolean updateInstanceData(InstanceData data) {
        if (updateInstanceDataCache(data)) {
            // Update database
            return super.updateInstanceData(data);
        }
        return false;
    }

    @Override
    public boolean addInstanceDataBatch(Collection<InstanceData> batch) {
        boolean modified = false;
        for (InstanceData data : batch) {
            if (updateInstanceDataCache(data)) {
                modified = true;
            }
        }
        if (modified) {
            // Update database only if data was modified
            return super.addInstanceDataBatch(batch);
        }
        return false;
    }

    @Override
    public void deleteInstance(String instance) {
        _instanceDataCache.remove(instance);
        _lastUpdated = System.currentTimeMillis();
        super.deleteInstance(instance);
    }

    @Override
    public void deleteInstanceData(String instanceId) throws SQLException {
        _instanceDataCache.remove(instanceId);
        _lastUpdated = System.currentTimeMillis();
        super.deleteInstanceData(instanceId);
    }

    @Override
    public void deleteAll() {
        _instanceDataCache.clear();
        _lastUpdated = System.currentTimeMillis();
        super.deleteAll();
    }

    @Override
    public TaurusDataFactory getDataFactory() {
        return (TaurusDataFactory) super.getDataFactory();
    }

}
