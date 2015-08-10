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

package com.YOMPsolutions.YOMP.mobile.service;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPService;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;

import android.content.Intent;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;
import android.support.v4.content.LocalBroadcastManager;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants.PREF_DATA_REFRESH_RATE;
import static com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants.PREF_PASSWORD;
import static com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants.PREF_SERVER_URL;

/**
 * This service is managed by {@link YOMPService} and is responsible for
 * synchronizing the local metric database with the server. It will poll the
 * server at {@link #REFRESH_RATE} interval for new data and download all
 * available data since last update.
 */
public class YOMPDataSyncService extends DataSyncService {

    private static final String TAG = YOMPDataSyncService.class.getSimpleName();

    // This object is used to flag the last metric data record to be processed
    private final static MetricData METRIC_DATA_EOF = new MetricData();

    // The maximum number of MetricData allowed to be pending in memory
    private final static int MAX_PENDING_METRIC_DATA_IO_BUFFER = 100000;

    /**
     * Number of new metrics added
     */
    public static final String EXTRA_NEW_METRICS = "nM+";

    /**
     * Number of new instances added
     */
    public static final String EXTRA_NEW_INSTANCES = "nI+";

    /**
     * Remaining time to process new models
     */
    public static final String EXTRA_REMAINING_TIME = "nT";


    // Handles user preferences changes
    final SharedPreferences.OnSharedPreferenceChangeListener _preferenceChangeListener
            = new SharedPreferences.OnSharedPreferenceChangeListener() {
        @Override
        public void onSharedPreferenceChanged(final SharedPreferences prefs,
                String key) {
            if (key.equals(PREF_SERVER_URL) || key.equals(PREF_PASSWORD)) {
                getService().getWorkerThreadPool().submit(new Runnable() {
                    @Override
                    public void run() {
                        // Cancel any pending I/O tasks
                        getService().cancelPendingIOTasks();

                        // Clean database
                        CoreDatabase database = YOMPApplication.getDatabase();
                        database.deleteAll();

                        // Disconnect from server
                        closeConnection();

                        // Update refresh rate
                        scheduleUpdate(Long.parseLong(prefs.getString(PREF_DATA_REFRESH_RATE,
                                REFRESH_RATE)));

                        // Notify UI
                        fireMetricChangedEvent(0, 0, 0);
                        fireMetricDataChangedEvent();
                    }
                });
            }
        }
    };

    public YOMPDataSyncService(YOMPService service) {
        super(service);
    }

    /**
     * Loads data for all metrics asynchronous.
     */
    protected void loadAllData() throws YOMPException, IOException {

        final YOMPDatabase database = YOMPApplication.getDatabase();

        // Get data since last update
        long lastTimestamp = database.getLastTimestamp();
        final long now = System.currentTimeMillis();

        // Don't get date older than NUMBER_OF_DAYS_TO_SYNC
        final long lowestTimestampAllowed = DataUtils.floorTo5minutes(System.currentTimeMillis()
                - YOMPApplication.getNumberOfDaysToSync() * DataUtils.MILLIS_PER_DAY);
        long nextTimestamp;
        // Make sure the whole database is not stale by checking if the last
        // known timestamp is greater than NUMBER_OF_DAYS_TO_SYNC
        if (lastTimestamp > lowestTimestampAllowed) {
            // Check if we have stale metrics for this period. If we all metrics
            // are stale then get all metrics at once, otherwise get stale
            // metrics first to avoid gaps in the data
            Collection<Metric> metrics = database.getAllMetrics();
            for (Metric metric : metrics) {
                // Define metric as "stale", when it has data (last_rowid > 0)
                // but the last known timestamp is lower than other metrics in
                // the local database
                long metricLastTimestamp = database.getMetricLastTimestamp(metric.getId());
                if (metric.getLastRowId() > 0 && metricLastTimestamp < lastTimestamp) {
                    // Don't get data older than NUMBER_OF_DAYS_TO_SYNC
                    if (metricLastTimestamp < lowestTimestampAllowed) {
                        nextTimestamp = lowestTimestampAllowed;
                    } else {
                        nextTimestamp = metricLastTimestamp;
                    }
                    // If the metric is stale for less than one hour then
                    // download it with together the other metrics
                    if (nextTimestamp > lastTimestamp - DataUtils.MILLIS_PER_HOUR) {
                        // Move last known timestamp to this metric timestamp
                        lastTimestamp = nextTimestamp < lastTimestamp ? nextTimestamp
                                : lastTimestamp;
                    } else {
                        // If the metric is stale for more than one hour then
                        // download it by itself
                        Log.d(TAG, "Downloading stale data for metric " + metric.getName() + "/"
                                + metric.getServerName() + ", lastTimestamp=" + nextTimestamp);
                        loadMetricData(metric.getId(), nextTimestamp, now);
                    }
                }
            }
        }

        // Don't get date older than NUMBER_OF_DAYS_TO_SYNC
        nextTimestamp = lastTimestamp + 1000;
        if (nextTimestamp < lowestTimestampAllowed) {
            nextTimestamp = lowestTimestampAllowed;
        }
        Log.d(TAG, "Start downloading data, from time stamp :" + nextTimestamp);
        loadMetricData(null, nextTimestamp, now);
    }

    /**
     * Load all metrics from YOMP and update the local database by adding new metrics and removing
     * old ones. This method will fire {@link #METRIC_CHANGED_EVENT}
     *
     * @return Number of new metrics
     */
    @Override
    protected int loadAllMetrics() throws InterruptedException,
            ExecutionException, YOMPException, IOException {
        if (getClient() == null) {
            Log.w(TAG, "Not connected to any server yet");
            return 0;
        }

        // Load all instances first
        int newInstances = loadAllInstances();

        // Get metrics from server
        List<Metric> remoteMetrics = getClient().getMetrics();
        if (remoteMetrics == null) {
            Log.e(TAG, "Unable to load metrics from server. " + getClient().getServerUrl());
            return 0;
        }
        int newMetrics = 0;
        int remainingTime = getClient().getProcessingTimeRemaining();
        HashSet<String> metricSet = new HashSet<>();
        // Save results to database
        boolean dataChanged = false;
        Metric localMetric;
        YOMPDatabase database = YOMPApplication.getDatabase();
        for (Metric remoteMetric : remoteMetrics) {
            // Check if it is a new metric
            localMetric = database.getMetric(remoteMetric.getId());
            if (localMetric == null) {
                database.addMetric(remoteMetric);
                // Refresh instance data associated with the new metric
                database.refreshInstanceData(remoteMetric.getInstanceId());
                dataChanged = true;
                newMetrics++;
            } else {
                // Check for metric changes
                if (remoteMetric.getLastRowId() != localMetric.getLastRowId()) {
                    // Use local metric last timestamp
                    remoteMetric.setLastTimestamp(localMetric.getLastTimestamp());
                    // Update metric.
                    database.updateMetric(remoteMetric);
                }
            }
            metricSet.add(remoteMetric.getId());
        }

        // Consolidate database by removing metrics from local cache
        // that were removed from the server
        try {
            for (Metric metric : database.getAllMetrics()) {
                if (!metricSet.contains(metric.getId())) {
                    database.deleteMetric(metric.getId());
                    // Refresh instance data associated with the deleted metric
                    database.refreshInstanceData(metric.getInstanceId());
                    dataChanged = true;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error loading metrics", e);
        } finally {
            // Notify receivers new data has arrived
            if (dataChanged) {
                fireMetricChangedEvent(newInstances, newMetrics, remainingTime);
            }
        }
        return newMetrics;
    }

    protected void start() {
        super.start();
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(getService()
                .getApplicationContext());
        prefs.registerOnSharedPreferenceChangeListener(_preferenceChangeListener);
    }

    protected void stop() {
        super.stop();
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(getService()
                .getApplicationContext());
        prefs.unregisterOnSharedPreferenceChangeListener(_preferenceChangeListener);
    }

    /**
     * Fire {@link DataSyncService#METRIC_CHANGED_EVENT}
     */
    protected void fireMetricChangedEvent(int newInstances, int newMetrics, int remainingTime) {
        Log.d(TAG, "Metric changed");
        Intent intent = new Intent(METRIC_CHANGED_EVENT);
        intent.putExtra(EXTRA_NEW_METRICS, newMetrics);
        intent.putExtra(EXTRA_NEW_INSTANCES, newInstances);
        intent.putExtra(EXTRA_REMAINING_TIME, remainingTime);
        LocalBroadcastManager.getInstance(getService()).sendBroadcast(intent);
    }


    /**
     * Loads metric data from the server
     *
     * @param metricId (optional) The metric Id to get the data. If metricId is {@code null} then
     *                 loads data for all metrics at once.
     * @param from     return records from this date
     * @param to       return records up to this date
     * @see com.numenta.core.service.YOMPClient#getMetricData
     */
    private void loadMetricData(final String metricId, final long from, final long to)
            throws YOMPException, IOException {

        if (getClient() == null) {
            Log.w(TAG, "Not connected to any server yet");
            return;
        }
        final CoreDatabase database = YOMPApplication.getDatabase();

        // Blocking queue holding metric data waiting to be saved to the
        // database. This queue will be filled by the YOMPClient as it downloads
        // the metric data and it will be emptied by the databaseTask as is
        // saves the data to the database
        final LinkedBlockingQueue<MetricData> pending =
                new LinkedBlockingQueue<>(MAX_PENDING_METRIC_DATA_IO_BUFFER);

        // Background task used save metric data to the database. This task will
        // wait for metric data to arrive from the server and save them to the
        // database in batches until it finds the end of the queue marked by
        // METRIC_DATA_EOF or it times out after 60 seconds
        final Future<?> databaseTask = getService().getIOThreadPool().submit(new Runnable() {
            @Override
            public void run() {

                // Make the batch size 1 hour for all metrics or one week for
                // single metric
                int batchSize = metricId == null ? DataUtils.MILLIS_PER_HOUR
                        : 24 * 7 * DataUtils.MILLIS_PER_HOUR;

                // Save metrics in batches, 24 hours at the time
                final List<MetricData> batch = new ArrayList<>();

                // Tracks batch timestamp. Once the metric timestamp is greater
                // than the batch timestamp, a new batch is created
                long batchTimestamp = 0;

                try {
                    // Process all pending metric data until the METRIC_DATA_EOF
                    // is found or a timeout is reached
                    MetricData metricData;
                    while ((metricData = pending.poll(60, TimeUnit.SECONDS)) != METRIC_DATA_EOF
                            && metricData != null) {
                        // Add metric data to batch regardless of the timestamp.
                        // At this point we may receive stale metric data with
                        // lower timestamp after we receive the latest data with
                        // the current timestamp. As a side effect, you may see
                        // gaps in the data as described in MER-1524
                        batch.add(metricData);
                        // Process batches
                        if (metricData.getTimestamp() > batchTimestamp) {
                            // Calculate next batch timestamp
                            batchTimestamp = metricData.getTimestamp() + batchSize;
                            if (database.addMetricDataBatch(batch)) {
                                Log.d(TAG, "Saving " + batch.size() + " new records");
                                // Notify receivers new data has arrived
                                fireMetricDataChangedEvent();
                            }
                            batch.clear();
                        }
                    }
                    // Last batch
                    if (!batch.isEmpty()) {
                        if (database.addMetricDataBatch(batch)) {
                            Log.d(TAG, "Received " + batch.size() + " records");
                            // Notify receivers new data has arrived
                            fireMetricDataChangedEvent();
                        }
                    }
                } catch (InterruptedException e) {
                    Log.w(TAG, "Interrupted while loading metric data");
                }
            }
        });

        try {
            // Get new data from server
            getClient().getMetricData(metricId, new Date(from), new Date(to),
                    new YOMPClient.DataCallback<MetricData>() {
                        @Override
                        public boolean onData(MetricData metricData) {
                            // enqueue data for saving
                            try {
                                Metric metric = database.getMetric(metricData.getMetricId());
                                if (metric == null) {
                                    Log.w(TAG, "Received data for unknown metric:"
                                            + metricData.getMetricId());
                                    return true;
                                }
                                pending.put(metricData);
                            } catch (InterruptedException e) {
                                pending.clear();
                                Log.w(TAG, "Interrupted while loading metric data");
                                return false;
                            }
                            return true;
                        }
                    }
            );
            // Mark the end of the records
            pending.add(METRIC_DATA_EOF);
            // Wait for the database task to complete
            databaseTask.get();
        } catch (InterruptedException e) {
            Log.w(TAG, "Interrupted while loading metric data");
        } catch (ExecutionException e) {
            Log.e(TAG, "Failed to load metric data", e);
        }
    }

    /**
     * Load all instances from YOMP and update the local database by adding new instances and
     * removing old ones. This method will fire {@link DataSyncService#METRIC_CHANGED_EVENT}
     *
     * @return Number of new instances
     */
    private int loadAllInstances() throws YOMPException, IOException {

        if (getClient() == null) {
            Log.w(TAG, "Not connected to any server yet");
            return 0;
        }
        // Get Instances from server
        List<Instance> remoteInstances = getClient().getInstances();
        if (remoteInstances == null) {
            Log.e(TAG, "Unable to load instances from server. " + getClient().getServerUrl());
            return 0;
        }

        int newInstances = 0;
        HashSet<String> instancesAdded = new HashSet<>();
        // Save results to database
        boolean dataChanged = false;
        YOMPDatabase database = YOMPApplication.getDatabase();
        Set<String> localInstances = database.getAllInstances();
        for (Instance remote : remoteInstances) {
            // Check if it is a new instance
            if (!localInstances.contains(remote.getId())) {
                // Refresh instance data
                database.addInstance(remote);
                dataChanged = true;
                newInstances++;
            }
            instancesAdded.add(remote.getId());
        }

        // Consolidate database by removing metrics from local cache
        // that were removed from the server
        try {
            for (String instance : localInstances) {
                if (!instancesAdded.contains(instance)) {
                    // delete instance data
                    database.deleteInstance(instance);
                    dataChanged = true;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error loading instances", e);
        } finally {
            // Notify receivers new data has arrived
            if (dataChanged) {
                fireMetricChangedEvent(0, 0, 0);
            }
        }
        return newInstances;
    }

    @Override
    protected YOMPClientImpl getClient() {
        return (YOMPClientImpl) super.getClient();
    }
}
