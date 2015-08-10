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

package com.numenta.taurus.service;

import com.numenta.core.data.InstanceData;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPService;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.TaurusDatabase;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;
import android.support.v4.content.LocalBroadcastManager;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_LAST_METRIC_SYNC_TIME;
import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_PREVIOUS_HOUR_THRESHOLD;

/**
 * This service is synchronizing the local database with DynamoDB. It will poll the
 * server at {@link #REFRESH_RATE} interval for new data and download all
 * available data since last update.
 */
public class TaurusDataSyncService extends DataSyncService {

    private static final String TAG = TaurusDataSyncService.class.getSimpleName();

    // This object is used to flag the last data record to be processed
    private final static InstanceData DATA_EOF = new InstanceData();

    // The maximum number of data records allowed to be pending in memory
    private final static int PENDING_IO_BUFFER_SIZE = 100000;

    /** This Event is fired on instance data changes */
    public static final String INSTANCE_DATA_CHANGED_EVENT
            = "com.numenta.taurus.data.InstanceDataChangedEvent";

    public TaurusDataSyncService(YOMPService service) {
        super(service);
    }

    /**
     * Load all instance data from the database
     */
    @Override
    protected void loadAllData() throws YOMPException, IOException {

        Context context = TaurusApplication.getContext();
        if (context == null) {
            // Should not happen.
            // We need application context to run.
            return;
        }

        // Get last known date from the database
        final TaurusDatabase database = TaurusApplication.getDatabase();
        if (database == null) {
            // Should not happen.
            // We need application context to run.
            return;
        }
        long from = database.getLastTimestamp();

        // Get current time
        final long now = System.currentTimeMillis();

        // The server updates the instance data table into hourly buckets as the models process
        // data. This may leave the last hour with outdated values when the server updates the
        // instance data table after we start loading the new hourly bucket.
        // To make sure the last hour bucket is updated we should get data since last update up to
        // now and on when the time is above a certain threshold (15 minutes) also download the
        // previous hour once.
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);

        // Check if we need to update the previous hour
        long previousHourThreshold = prefs.getLong(PREF_PREVIOUS_HOUR_THRESHOLD, now);
        if (now >= previousHourThreshold) {
            // Download the previous hour
            from -= DataUtils.MILLIS_PER_HOUR;

            // Set threshold time to minute 15 of next hour
            Calendar calendar = Calendar.getInstance();
            calendar.setTimeInMillis(now);
            calendar.add(Calendar.HOUR, 1);
            calendar.set(Calendar.MINUTE, 15);
            calendar.set(Calendar.SECOND, 0);
            calendar.set(Calendar.MILLISECOND, 0);
            prefs.edit().putLong(PREF_PREVIOUS_HOUR_THRESHOLD, calendar.getTimeInMillis()).apply();
        }
        final long oldestTimestamp = DataUtils.floorTo60minutes(
                now - TaurusApplication.getNumberOfDaysToSync() * DataUtils.MILLIS_PER_DAY);

        // Check if we need to catch up and download old data
        if (database.getFirstTimestamp() > oldestTimestamp) {
            from = oldestTimestamp;
        }

        // Don't get date older than NUMBER_OF_DAYS_TO_SYNC
        from = Math.max(from, oldestTimestamp);

        // Blocking queue holding data waiting to be saved to the database.
        // This queue will be filled by the TaurusClient as it downloads data and it will be
        // emptied by the databaseTask as is saves data to the database
        final LinkedBlockingQueue<InstanceData> pending = new LinkedBlockingQueue<InstanceData>(
                PENDING_IO_BUFFER_SIZE);

        // Background task used save data to the database. This task will wait for data to arrive
        // from the server and save them to the database in batches until it finds the end of the
        // queue marked by DATA_EOF or it times out after 60 seconds
        final Future<?> databaseTask = getService().getIOThreadPool().submit(new Runnable() {
            @Override
            public void run() {
                // Save data in batches, one day at the time
                final List<InstanceData> batch = new ArrayList<InstanceData>();
                int batchSize = -DataUtils.MILLIS_PER_HOUR;

                // Tracks batch timestamp. Once the data timestamp is greater than the batch
                // timestamp, a new batch is created
                long batchTimestamp = now - DataUtils.MILLIS_PER_HOUR;

                try {
                    // Process all pending data until the DATA_EOF is found or a timeout is reached
                    InstanceData data;
                    while ((data = pending.poll(60, TimeUnit.SECONDS)) != DATA_EOF
                            && data != null) {
                        batch.add(data);
                        // Process batches
                        if (data.getTimestamp() < batchTimestamp) {
                            // Calculate next batch timestamp
                            batchTimestamp = data.getTimestamp() + batchSize;
                            if (database.addInstanceDataBatch(batch)) {
                                // Notify receivers new data has arrived
                                fireInstanceDataChangedEvent();
                            }
                            batch.clear();
                        }
                    }
                    // Last batch
                    if (!batch.isEmpty()) {
                        if (database.addInstanceDataBatch(batch)) {
                            // Notify receivers new data has arrived
                            fireInstanceDataChangedEvent();
                        }
                    }
                } catch (InterruptedException e) {
                    Log.w(TAG, "Interrupted while loading data");
                }
            }
        });

        try {
            // Get new data from server
            Log.d(TAG, "Start downloading data from " + from);
            TaurusClient client = getClient();
            client.getAllInstanceData(new Date(from), new Date(now), false,
                    new YOMPClient.DataCallback<InstanceData>() {
                        @Override
                        public boolean onData(InstanceData data) {
                            // enqueue data for saving
                            try {
                                pending.put(data);
                            } catch (InterruptedException e) {
                                pending.clear();
                                Log.w(TAG, "Interrupted while loading data");
                                return false;
                            }
                            return true;
                        }
                    });
            // Mark the end of the records
            pending.add(DATA_EOF);
            // Wait for the database task to complete
            databaseTask.get();
            // Clear client cache
            client.clearCache();
        } catch (InterruptedException e) {
            Log.w(TAG, "Interrupted while loading data");
        } catch (ExecutionException e) {
            Log.e(TAG, "Failed to load data", e);
        }
    }

    /**
     * {@inheritDoc}
     *
     * <p>
     * <b>TAURUS:</b> Only attempt to load metrics once a day to save on network data usage
     * </p>
     *
     * @return Number of new metrics
     */
    @Override
    protected int loadAllMetrics()
            throws InterruptedException, ExecutionException, YOMPException, IOException {
        // Check last time the metric list was loaded
        Context context = TaurusApplication.getContext();
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);
        long lastSyncTime = prefs.getLong(PREF_LAST_METRIC_SYNC_TIME, 0);
        long now = System.currentTimeMillis();
        // Check if at least 24h has passed since we last downloaded the metrics
        if (now < lastSyncTime + DataUtils.MILLIS_PER_DAY) {
            return 0;
        }

        // Update last synchronization time
        prefs.edit().putLong(PREF_LAST_METRIC_SYNC_TIME, now).apply();
        return super.loadAllMetrics();
    }

    /**
     * Fire {@link #INSTANCE_DATA_CHANGED_EVENT}
     */
    protected void fireInstanceDataChangedEvent() {
        Log.d(TAG, "Instance Data changed");
        Intent intent = new Intent(INSTANCE_DATA_CHANGED_EVENT);
        LocalBroadcastManager.getInstance(getService()).sendBroadcast(intent);
    }

    @Override
    protected void loadAllAnnotations() throws IOException, YOMPException {

    }

    /**
     * Returns API Client
     */
    @Override
    protected TaurusClient getClient() {
        return (TaurusClient) super.getClient();
    }
}
