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

package com.YOMPsolutions.YOMP.mobile;

import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientFactoryImpl;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.YOMPsolutions.YOMP.mobile.service.YOMPDataSyncService;
import com.YOMPsolutions.YOMP.mobile.service.YOMPNotificationService;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPService;
import com.numenta.core.service.NotificationService;
import com.numenta.core.utils.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import android.content.SharedPreferences;
import android.content.res.Resources;
import android.preference.PreferenceManager;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;


/**
 * Maintain global application state.
 */
public class YOMPApplication extends com.numenta.core.app.YOMPApplication {

    private static final String TAG = YOMPApplication.class.getCanonicalName();

    private volatile SortOrder _sort = SortOrder.Anomaly;
    /**
     * Current Sort Order Property
     */
    public static final String SORT_PROPERTY = "sort";

    // Page uploads to avoid timeouts when there are a lot of logs.
    private static final int MAX_LOGS_PER_REQUEST = 2000;

    @Override
    public void onCreate() {
        super.onCreate();
        // Initialize API Client factory
        setYOMPClientFactory(new YOMPClientFactoryImpl());

        // Initialize preferences
        PreferenceManager.setDefaultValues(this, R.xml.preferences, false);

    }

    /**
     * @return current {@link SortOrder}
     */
    public static SortOrder getSort() {
        return getInstance()._sort;
    }

    /**
     * Update the current {@link SortOrder}
     *
     * @param value new {@link SortOrder}
     */
    public static void setSort(final SortOrder value) {
        YOMPApplication app = getInstance();

        if (value != app._sort) {
            SortOrder old = app._sort;
            app._sort = value;
            app.firePropertyChange(SORT_PROPERTY, old, value);
        }
    }
    public static YOMPApplication getInstance() {
        return (YOMPApplication) com.numenta.core.app.YOMPApplication.getInstance();
    }

    /**
     * Given a known metric name, returns the "Unit" associated to the metric.
     *
     * @see res/values/metric_units.xml
     */
    public static String getMetricUnit(String metricName) {

        if (metricName != null) {
            YOMPApplication app = getInstance();
            Resources resources = app.getResources();
            final StringBuilder resName = new StringBuilder("Unit_").append(
                    metricName.replace('/', '_'));
            final int resId = resources.getIdentifier(resName.toString(), "string",
                    app.getPackageName());
            if (resId != 0) {
                return app.getResources().getString(resId);
            }

        }
        return null;
    }

    /**
     * Returns interface to YOMP database
     */
    public static YOMPDatabase getDatabase() {
        return (YOMPDatabase) com.numenta.core.app.YOMPApplication.getDatabase();
    }

    /**
     * Override this method to create <b>YOMP</b> specific database interface
     *
     * @return {@link com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase} instance
     */
    @Override
    protected CoreDatabase createDatabase() {
        return new YOMPDatabase(getContext());
    }

    /**
     * Override this method to create <b>YOMP</b> specific notification service
     *
     * @return {@link com.YOMPsolutions.YOMP.mobile.service.YOMPNotificationService} instance
     */
    @Override
    public DataSyncService createDataSyncService(com.numenta.core.service.YOMPService service) {
        return new YOMPDataSyncService(service);
    }

    /**
     * Override this method to create <b>YOMP</b> specific notification service
     *
     * @return {@link com.YOMPsolutions.YOMP.mobile.service.YOMPNotificationService} instance
     */
    @Override
    public NotificationService createNotificationService(YOMPService service) {
        return new YOMPNotificationService(service);
    }


    /**
     * This method should be executed periodically to send logs to the server.
     *
     * @throws com.numenta.core.service.YOMPException
     * @throws java.io.IOException
     */
    @Override
    public void uploadLogs() throws YOMPException, IOException {
        if (!YOMPApplication.shouldUploadLog()) {
            return;
        }
        int failedAttempts = 0;
        ArrayList<String> logs = new ArrayList<>();
        Log.drainTo(logs);
        if (logs.isEmpty()) {
            return;
        }


        YOMPClientImpl YOMP = (YOMPClientImpl) connectToServer();
        if (YOMP == null) {
            return;
        }
        String url = YOMP.getServerUrl();
        if (url == null) {
            return;
        }
        url = url.trim() + "/_logging/android";

        while (!logs.isEmpty() && failedAttempts < 5) {
            int numLogs = Math.min(logs.size(), MAX_LOGS_PER_REQUEST);

            JSONArray logArray;
            logArray = new JSONArray();
            for (int i = 0; i < numLogs; i++) {
                String[] values = logs.get(i).split(" ", 5);
                Map<String, Object> entry = new HashMap<>();
                for (String keyValPair : values) {
                    entry.put(keyValPair.split("=", 2)[0], keyValPair.split("=", 2)[1]);
                }

                logArray.put(new JSONObject(entry));
            }
            String response = YOMP.post(url, logArray.toString());
            if (response == null) {
                failedAttempts += 1;
                Log.e(TAG,
                        "Received null HTTP response from log upload request.");
                continue;
            }
            for (int i = 0; i < numLogs; ++i) {
                logs.remove(0);
            }
            // Start over when there is a successful upload.
            failedAttempts = 0;
        }
        // Make sure we don't retain too many logs in memory. This is in
        // addition to the logs in Log.queue.
        while (logs.size() > Log.MAX_LOGS_TO_KEEP) {
            logs.remove(0);
        }
    }

    /**
     * Establish a connection to the YOMP server and returns a new instance of
     * {@link YOMPClient} using the the last known stored authentication settings, if any.
     *
     * @return {@link YOMPClient} object used to interact with the server.
     */
    @Override
    public YOMPClient connectToServer() {
        YOMPClientImpl connection = null;
        final SharedPreferences prefs = PreferenceManager
                .getDefaultSharedPreferences(com.numenta.core.app.YOMPApplication.getContext());
        String serverUrl = prefs.getString(PreferencesConstants.PREF_SERVER_URL, null);
        if (serverUrl != null) {
            serverUrl = serverUrl.trim();
            String password = prefs.getString(PreferencesConstants.PREF_PASSWORD, null);
            try {
                connection = (YOMPClientImpl) connectToYOMP(serverUrl, password);
                connection.login();
                Log.d(TAG, "Service connected to " + serverUrl);
            } catch (Exception e) {
                connection = null;
                Log.e(TAG, "Unable to connect to YOMP.", e);
            }
        } else {
            Log.e(TAG, "Unable to connect to YOMP. Missing server URL.");
        }
        return connection;
    }
}
