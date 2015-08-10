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

package com.numenta.core.service;

import com.numenta.core.R;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.data.Metric;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.NetUtils;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.OnSharedPreferenceChangeListener;
import android.os.Looper;
import android.preference.PreferenceManager;
import android.support.v4.content.LocalBroadcastManager;
import android.text.format.DateUtils;

import java.io.IOException;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

import static com.numenta.core.preference.PreferencesConstants.PREF_DATA_REFRESH_RATE;
import static com.numenta.core.preference.PreferencesConstants.PREF_LAST_CONNECTED_TIME;


/**
 * This service is managed by {@link YOMPService} and is responsible for
 * synchronizing the local metric database with the server. It will poll the
 * server at {@link #REFRESH_RATE} interval for new data and download all
 * available data since last update.
 */
public class DataSyncService {

    /**
     * This Event is fired on metric data changes
     */
    public static final String METRIC_DATA_CHANGED_EVENT
            = "com.numenta.core.data.MetricDataChangedEvent";

    /**
     * This Event is fired on metric changes
     */
    public static final String METRIC_CHANGED_EVENT = "com.numenta.core.data.MetricChangedEvent";

    /**
     * This Event is fired on annotations changes
     */
    public static final String ANNOTATION_CHANGED_EVENT
            = "com.numenta.core.data.AnnotationChangedEvent";

    /**
     * This Event is fired when the server starts and stops downloading data. Check event's <b>
     * <code>isRefreshing</code></b> parameter for refreshing status.
     */
    public static final String REFRESH_STATE_EVENT = "com.numenta.core.data.RefreshStateEvent";

    /**
     * Default Refresh rate in minutes. User may override using application settings
     */
    public static final String REFRESH_RATE = "5";

    // Handles user preferences changes
    private final OnSharedPreferenceChangeListener _preferenceChangeListener
            = new OnSharedPreferenceChangeListener() {
        @Override
        public void onSharedPreferenceChanged(final SharedPreferences prefs,
                String key) {
            if (key.equals(PREF_DATA_REFRESH_RATE)) {
                scheduleUpdate(Long
                        .parseLong(prefs.getString(PREF_DATA_REFRESH_RATE, REFRESH_RATE)));
            }
        }
    };

    private static final String TAG = DataSyncService.class.getSimpleName();

    // Main Service
    private final YOMPService _service;

    // This task will periodically load data from the server
    private ScheduledFuture<?> _updateTask;

    // YOMP API Helper
    private YOMPClient _YOMPCli;

    // Prevent multiple threads from downloading data from the server
    // simultaneously
    private volatile boolean _synchronizingWithServer;

    /**
     * DataSyncService constructor.
     * <p>
     * Should only be called by {@link YOMPService}
     * </p>
     *
     * @param service The main {@link YOMPService}
     */
    /* package */
    public DataSyncService(YOMPService service) {
        this._service = service;
    }

    /**
     * Fire {@link DataSyncService#REFRESH_STATE_EVENT}
     */
    protected void fireRefreshStateEvent(boolean isRefreshing) {
        Intent intent = new Intent(DataSyncService.REFRESH_STATE_EVENT);
        intent.putExtra("isRefreshing", isRefreshing);
        LocalBroadcastManager.getInstance(_service).sendBroadcast(intent);
        YOMPApplication.setLastError(null);
    }

    /**
     * Fire {@link DataSyncService#REFRESH_STATE_EVENT}
     */
    protected void fireRefreshStateEvent(boolean isRefreshing, String result) {
        Intent intent = new Intent(DataSyncService.REFRESH_STATE_EVENT);
        intent.putExtra("isRefreshing", isRefreshing);
        LocalBroadcastManager.getInstance(_service).sendBroadcast(intent);
        YOMPApplication.setLastError(result);
    }

    /**
     * Fire {@link DataSyncService#METRIC_CHANGED_EVENT}
     */
    protected void fireMetricChangedEvent() {
        Log.d(TAG, "Metric changed");
        Intent intent = new Intent(DataSyncService.METRIC_CHANGED_EVENT);
        LocalBroadcastManager.getInstance(_service).sendBroadcast(intent);
    }

    /**
     * Fire {@link DataSyncService#METRIC_DATA_CHANGED_EVENT}
     */
    protected void fireMetricDataChangedEvent() {
        Log.d(TAG, "Metric Data changed");
        Intent intent = new Intent(METRIC_DATA_CHANGED_EVENT);
        LocalBroadcastManager.getInstance(_service).sendBroadcast(intent);
    }

    /**
     * Fire {@link #ANNOTATION_CHANGED_EVENT}
     */
    protected void fireAnnotationChangedEvent() {
        Log.d(TAG, "Annotation changed");
        Intent intent = new Intent(ANNOTATION_CHANGED_EVENT);
        LocalBroadcastManager.getInstance(_service).sendBroadcast(intent);
    }

    /**
     * Load all metrics from YOMP and update the local database by adding new metrics and removing
     * old ones. This method will fire {@link #METRIC_CHANGED_EVENT}
     *
     * @return Number of new metrics
     */
    protected int loadAllMetrics() throws InterruptedException,
            ExecutionException, YOMPException, IOException {
        if (_YOMPCli == null) {
            Log.w(TAG, "Not connected to any server yet");
            return 0;
        }

        // Check for connectivity
        if (!_YOMPCli.isOnline()) {
            return 0;
        }

        // Get metrics from server
        List<Metric> remoteMetrics = _YOMPCli.getMetrics();
        if (remoteMetrics == null) {
            Log.e(TAG, "Unable to load metrics from server. " + _YOMPCli.getServerUrl());
            return 0;
        }
        int newMetrics = 0;
        HashSet<String> metricSet = new HashSet<String>();
        // Save results to database
        boolean dataChanged = false;
        Metric localMetric;
        CoreDatabase database = YOMPApplication.getDatabase();
        for (Metric remoteMetric : remoteMetrics) {
            // Check if it is a new metric
            localMetric = database.getMetric(remoteMetric.getId());
            if (localMetric == null) {
                database.addMetric(remoteMetric);
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
                    dataChanged = true;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error loading metrics", e);
        } finally {
            // Notify receivers new data has arrived
            if (dataChanged) {
                fireMetricChangedEvent();
            }
        }
        return newMetrics;
    }

    /**
     * Schedule the update task to execute periodically at the given rate
     *
     * @param rate The rate given in minutes
     */
    protected synchronized void scheduleUpdate(long rate) {
        if (_updateTask != null) {
            _updateTask.cancel(true);
        }
        _updateTask = _service.scheduleTask(new Runnable() {
            @Override
            public void run() {
                try {
                    synchronizeWithServer();
                } catch (Exception e) {
                    Log.e(TAG, "Error updating data", e);
                }
            }
        }, rate, TimeUnit.MINUTES);
    }

    /**
     * This method is execute periodically and update {@link com.numenta.core.data.CoreDatabase}
     * with new data from the
     * server.
     */
    protected void synchronizeWithServer() throws IOException {
        Log.i(TAG, "synchronizeWithServer");

        if (_synchronizingWithServer) {
            return;
        }
        if (!NetUtils.isConnected()) {
            // Not connected, skip until we connect
            return;
        }

        final CoreDatabase database = YOMPApplication.getDatabase();
        if (database == null) {
            return;
        }
        synchronized (this) {
            if (_synchronizingWithServer) {
                return;
            }
            _synchronizingWithServer = true;
        }
        String result = null;
        try {
            // Guard against blocking the UI Thread
            if (Looper.myLooper() == Looper.getMainLooper()) {
                throw new IllegalStateException(
                        "You should not access the database from the UI thread");
            }

            fireRefreshStateEvent(_synchronizingWithServer);

            final Context context = _service.getApplicationContext();
            final long now = System.currentTimeMillis();

            // Check if enough time has passed since we checked for new data
            SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);
            final long lastConnectedTime = prefs.getLong(PREF_LAST_CONNECTED_TIME, 0);
            if (now - lastConnectedTime < DataUtils.METRIC_DATA_INTERVAL) {
                return;
            }

            // Calculate hours since last update. This information will be
            // passed to the user together with error message
            final CharSequence hoursSinceData = DateUtils.getRelativeTimeSpanString(
                    database.getLastTimestamp(), now, DateUtils.MINUTE_IN_MILLIS);

            Future<?> pendingIO = null;
            try {
                // Try to connect to YOMP
                if (_YOMPCli == null) {
                    _YOMPCli = _service.connectToServer();
                }
                if (_YOMPCli == null) {
                    throw new IOException("Unable to connect to server");
                }

                // Update last connected time
                SharedPreferences.Editor editor = prefs.edit();
                editor.putLong(PREF_LAST_CONNECTED_TIME, now);
                editor.apply();

                // Start by downloading all the metrics available from YOMP
                // in a background IO thread
                pendingIO = _service.getIOThreadPool().submit(new Callable<Void>() {
                    @Override
                    public Void call() throws Exception {

                        try {
                            // First load metrics
                            loadAllMetrics();

                            // Load all annotations after metrics
                            loadAllAnnotations();

                            // Load all data after annotations
                            loadAllData();

                            // Synchronize notifications after data
                            synchronizeNotifications();

                            // Synchronize application data last
                            YOMPApplication.getInstance().loadApplicationData(_YOMPCli);

                        } catch (android.database.sqlite.SQLiteFullException e) {
                            // Try to delete old records to make room if possible
                            Log.e(TAG, "Failed to save data into database", e);
                            database.deleteOldRecords();
                        }
                        return null;
                    }
                });
                // Wait for metric data to finish
                pendingIO.get();
            } catch (InterruptedException e) {
                // Cancel pending tasks
                if (!pendingIO.isDone()) {
                    pendingIO.cancel(true);
                }
                Log.w(TAG, "Interrupted while loading data");
            } catch (ExecutionException e) {
                // Cancel pending tasks
                if (!pendingIO.isDone()) {
                    pendingIO.cancel(true);
                }
                Throwable original = e.getCause();
                if (original instanceof AuthenticationException) {
                    _service.fireAuthenticationFailedEvent();
                } else if (original instanceof ObjectNotFoundException) {
                    Log.e(TAG, "Error loading data", e);
                    result = context.getString(R.string.refresh_update_error, hoursSinceData);
                } else if (original instanceof IOException) {
                    Log.e(TAG, "Unable to connect", e);
                    result = context.getString(R.string.refresh_server_unreachable, hoursSinceData);
                } else {
                    Log.e(TAG, "Error loading data", e);
                    result = context.getString(R.string.refresh_update_error, hoursSinceData);
                }
            } catch (AuthenticationException e) {
                _service.fireAuthenticationFailedEvent();
            } catch (YOMPException e) {
                Log.e(TAG, "Error loading data", e);
                result = context.getString(R.string.refresh_update_error, hoursSinceData);
            } catch (IOException e) {
                Log.e(TAG, "Unable to connect", e);
                result = context.getString(R.string.refresh_server_unreachable, hoursSinceData);
            }
        } finally {
            _synchronizingWithServer = false;
            fireRefreshStateEvent(_synchronizingWithServer, result);
        }
    }

    /**
     * Called periodically to synchronize notifications in the background
     */
    protected void synchronizeNotifications() {
        try {
            _service.synchronizeNotifications();
        } catch (YOMPException e) {
            Log.e(TAG, "Failed to synchronize notifications", e);
        } catch (IOException e) {
            Log.e(TAG, "Failed to synchronize notifications", e);
        }
    }

    /**
     * Loads data for all metrics asynchronous.
     */
    protected void loadAllData() throws YOMPException, IOException {

    }

    /**
     * Load all annotations from YOMP and update the local database by adding new annotations and
     * removing old ones. This method will fire {@link DataSyncService#ANNOTATION_CHANGED_EVENT}
     * <p><b>Note:</b></p>
     * This method will only load the last {@link com.numenta.core.app.YOMPApplication#getNumberOfDaysToSync()}
     * days of data.
     */
    protected void loadAllAnnotations() throws IOException, YOMPException {
        if (_YOMPCli == null) {
            Log.w(TAG, "Not connected to any server yet");
            return;
        }
        // Get Annotations from server for the last 2 weeks
        long now = System.currentTimeMillis();
        long from = now - YOMPApplication.getNumberOfDaysToSync() * DataUtils.MILLIS_PER_DAY;
        List<Annotation> remoteAnnotations = _YOMPCli.getAnnotations(new Date(from), new Date(now));
        if (remoteAnnotations == null) {
            Log.e(TAG, "Unable to load annotations from server. " + _YOMPCli.getServerUrl());
            return;
        }

        HashSet<String> activeAnnotations = new HashSet<String>();
        HashSet<String> localAnnotations = new HashSet<String>();
        // Save results to database
        boolean dataChanged = false;
        CoreDatabase database = YOMPApplication.getDatabase();
        // Get a set of all annotations in the database
        for (Annotation annotation : database.getAllAnnotations()) {
            localAnnotations.add(annotation.getId());
        }
        for (Annotation remote : remoteAnnotations) {
            // Check if it is a new annotation
            if (!localAnnotations.contains(remote.getId())) {
                // Add annotation to database
                database.addAnnotation(remote);
                dataChanged = true;
            }
            activeAnnotations.add(remote.getId());
        }

        // Consolidate database by removing annotations from local database
        // that were removed from the server
        try {
            for (String annotation : localAnnotations) {
                if (!activeAnnotations.contains(annotation)) {
                    // delete annotation
                    database.deleteAnnotation(annotation);
                    dataChanged = true;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error loading annotations", e);
        } finally {
            // Notify receivers of changes
            if (dataChanged) {
                fireAnnotationChangedEvent();
            }
        }
    }

    /**
     * Delete annotation from the server
     *
     * @param annotationId The annotation ID to delete
     * @return {@code true} if the annotation was successfully deleted from the server
     */
    protected boolean deleteAnnotation(String annotationId) {
        if (_YOMPCli == null) {
            Log.w(TAG, "Not connected to any server yet");
            return false;
        }
        try {
            CoreDatabase database = YOMPApplication.getDatabase();
            // Check if annotation exists
            Annotation annotation = database.getAnnotation(annotationId);
            if (annotation != null) {
                // Delete from the server
                _YOMPCli.deleteAnnotation(annotation);
                // Delete from the database
                if (database.deleteAnnotation(annotationId) == 1) {
                    // Notify receivers of changes
                    fireAnnotationChangedEvent();
                    return true;
                }
            }
            // Annotation not found
            Log.e(TAG, "Failed to delete annotation. " + annotationId + " was not found");
        } catch (YOMPException e) {
            Log.e(TAG, "Failed to delete annotation " + annotationId, e);
        } catch (IOException e) {
            Log.e(TAG, "Failed to delete annotation " + annotationId, e);
        }
        return false;
    }

    /**
     * Add new annotation associating it to the given server and the given timestamp.
     * The current device will also be associated with the annotation.
     *
     * @param timestamp The date and time to be annotated
     * @param server    Instance Id associated with this annotation
     * @param message   Annotation message
     * @param user      User name
     * @return {@code true} if the annotation was successfully added to the server
     */
    public boolean addAnnotation(Date timestamp, String server, String message, String user) {
        if (_YOMPCli == null) {
            Log.w(TAG, "Not connected to any server yet");
            return false;
        }
        try {
            Annotation annotation = _YOMPCli.addAnnotation(timestamp, server, message, user);
            // Update database with new annotation
            if (annotation != null) {
                CoreDatabase database = YOMPApplication.getDatabase();
                if (database.addAnnotation(annotation) != -1) {
                    fireAnnotationChangedEvent();
                    return true;
                }
            }
        } catch (YOMPException e) {
            Log.e(TAG, "Failed to add annotation ", e);
        } catch (IOException e) {
            Log.e(TAG, "Failed to add annotation ", e);
        }
        return false;
    }

    /**
     * Force client to refresh the data by downloading new data from the server
     */
    protected void forceRefresh() {
        Log.i(TAG, "forceRefresh");

        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(_service
                .getApplicationContext());
        prefs.registerOnSharedPreferenceChangeListener(_preferenceChangeListener);
        scheduleUpdate(Long.parseLong(prefs.getString(PREF_DATA_REFRESH_RATE, REFRESH_RATE)));
    }

    /**
     * Start the data sync service.
     * <p>
     * Should only be called by {@link YOMPService}
     * </p>
     */
    protected void start() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(_service
                .getApplicationContext());
        prefs.registerOnSharedPreferenceChangeListener(_preferenceChangeListener);
        scheduleUpdate(Long.parseLong(prefs.getString(PREF_DATA_REFRESH_RATE, REFRESH_RATE)));
    }

    /**
     * Stop the data sync service.
     * <p>
     * Should only be called by {@link YOMPService}
     * </p>
     */
    protected void stop() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(_service
                .getApplicationContext());
        prefs.unregisterOnSharedPreferenceChangeListener(_preferenceChangeListener);
        if (_updateTask != null) {
            _updateTask.cancel(true);
        }
        _updateTask = null;
    }

    /**
     * Returns {@code true} if the service is refreshing the data
     */
    public boolean isRefreshing() {
        return _synchronizingWithServer;
    }

    /**
     * Returns API Client
     */
    protected YOMPClient getClient() {
        return _YOMPCli;
    }

    /**
     * Return underlying background service
     */
    public YOMPService getService() {
        return _service;
    }

    /**
     * Close server connection
     */
    public void closeConnection() {
        _YOMPCli = null;
    }
}
