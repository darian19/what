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

package com.numenta.core.app;

import com.google.android.gms.analytics.GoogleAnalytics;
import com.google.android.gms.analytics.Tracker;

import com.numenta.core.BuildConfig;
import com.numenta.core.R;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.data.CoreDatabaseImpl;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPClientFactory;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPService;
import com.numenta.core.service.YOMPService.YOMPDataBinder;
import com.numenta.core.service.NotificationService;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Version;

import android.app.Application;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import android.content.res.Resources;
import android.os.AsyncTask;
import android.os.Build;
import android.os.IBinder;
import android.preference.PreferenceManager;
import android.provider.Settings;

import java.beans.PropertyChangeListener;
import java.beans.PropertyChangeSupport;
import java.io.IOException;
import java.net.MalformedURLException;
import java.util.Date;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.atomic.AtomicInteger;

import static java.util.concurrent.TimeUnit.MILLISECONDS;
import static java.util.concurrent.TimeUnit.MINUTES;

/**
 * Maintain global application state.
 */
public class YOMPApplication extends Application {

    // NOTE: It is guaranteed to only have one instance of the
    // android.app.Application class so it's safe (and recommended by the
    // Google Android team) to treat it as a Singleton.
    private static YOMPApplication _instance;

    private static final String TAG = YOMPApplication.class.getCanonicalName();

    /**
     * Activity Action: Opens the Notification List Activity
     */
    public static final String ACTION_SHOW_NOTIFICATION_LIST
            = "com.numenta.core.intent.action.SHOW_NOTIFICATION_LIST";

    /**
     * Activity Action: Open the Notification Detail Activity whose "id" is given by the intent's
     * extra parameter named "id"
     */
    public static final String ACTION_SHOW_NOTIFICATION
            = "com.numenta.core.intent.action.SHOW_NOTIFICATION";

    /** Current Aggregation Property */
    public static final String AGGREGATION_PROPERTY = "aggregation";

    public static final long MAX_DURATION = MILLISECONDS.convert(5, MINUTES);

    private static ExecutorService _defaultThreadPool
            = (ExecutorService) AsyncTask.THREAD_POOL_EXECUTOR;

    /** Maximum number of days to sync. */
    public int _numberOfDaysToSync;

    /** The number of bars to display on the anomaly charts */
    private int _chartTotalBars;

    /** The number of records for which the model is still learning */
    private int _learningThreshold;

    /** Control whether or not we should upload the android logs to the server */
    private boolean _uploadLog;

    /** Google Analytics tracker for this application */
    private Tracker _tracker;

    /** The Yellow bar floor value. See {@link com.numenta.core.R.fraction#yellow_bar_floor} */
    private float _yellowBarFloor;

    /** The Red bar floor value. See {@link com.numenta.core.R.fraction#red_bar_floor} */
    private float _redBarFloor;

    private String _deviceId;

    private String _applicationName;

    private volatile YOMPClientFactory _YOMPClientFactory;

    private CoreDatabase _database;

    private YOMPService _dataService;

    private volatile boolean _bound;

    private volatile String _lastError;

    private volatile AggregationType _aggregation;

    private volatile long _activityLastUsed;

    private volatile Version _serverVersion = Version.UNKNOWN;

    private final AtomicInteger _activityCount = new AtomicInteger();

    protected final PropertyChangeSupport _pcs = new PropertyChangeSupport(this);

    /**
     * Defines callbacks for service binding, passed to bindService()
     */
    private final ServiceConnection _YOMPDataServiceConn = new ServiceConnection() {
        @Override
        public void onServiceConnected(final ComponentName className,
                final IBinder service) {
            // We've bound to LocalService, cast the IBinder and get
            // LocalService instance
            YOMPDataBinder dataServiceBinder = (YOMPDataBinder) service;
            _dataService = dataServiceBinder.getService();
            _bound = true;
        }

        @Override
        public void onServiceDisconnected(ComponentName arg0) {
            _bound = false;
        }
    };

    /**
     * Set singleton instance object used by unit tests.
     * This method should only be called from unit tests. In a normal android runtime environment
     * the application instance singleton will be initialized via {@link #onCreate()}
     */
    public static void setStaticInstanceForUnitTestsOnly(YOMPApplication testApplicationObject) {
        _instance = testApplicationObject;
    }

    /**
     * Subscribes {@code listener} to change notifications for the property
     * named {@code propertyName}. If the listener is already subscribed, it
     * will receive an additional notification when the property changes. If the
     * property name or listener is null, this method silently does nothing.
     * <p>
     * Valid property names are :
     * <ul>
     * <li>{@link #AGGREGATION_PROPERTY},
     * </ul>
     *
     * @see PropertyChangeSupport#addPropertyChangeListener(String,
     * PropertyChangeListener)
     */
    public static void addPropertyChangeListener(String propertyName,
            PropertyChangeListener listener) {
        if (_instance != null) {
            _instance._pcs.addPropertyChangeListener(propertyName, listener);
        }
    }

    /**
     * @see PropertyChangeSupport#removePropertyChangeListener(String,
     * PropertyChangeListener)
     */
    public static void removePropertyChangeListener(String propertyName,
            PropertyChangeListener listener) {
        if (_instance != null) {
            _instance._pcs.removePropertyChangeListener(propertyName, listener);
        }
    }

    /**
     * @see PropertyChangeSupport#addPropertyChangeListener(PropertyChangeListener)
     */
    public static void addPropertyChangeListener(PropertyChangeListener listener) {
        if (_instance != null) {
            _instance._pcs.addPropertyChangeListener(listener);
        }
    }

    /**
     * @see PropertyChangeSupport#removePropertyChangeListener(PropertyChangeListener)
     */
    public static void removePropertyChangeListener(PropertyChangeListener listener) {
        if (_instance != null) {
            _instance._pcs.removePropertyChangeListener(listener);
        }
    }

    /**
     * @see java.beans.PropertyChangeSupport#firePropertyChange(String, Object, Object)
     */
    public static void firePropertyChange(String propertyName, Object oldValue, Object newValue) {
        if (_instance != null) {
            _instance._pcs.firePropertyChange(propertyName, oldValue, newValue);
        }
    }

    /**
     * The number of records for which the model is still learning
     */
    public static int getLearningThreshold() {
        if (_instance != null) {
            return _instance._learningThreshold;
        }
        return 0;
    }

    /**
     * Returns this application Singleton instance.
     */
    public static YOMPApplication getInstance() {
        return _instance;
    }

    /**
     * Return this application interface to the database
     */
    public static CoreDatabase getDatabase() {
        if (_instance != null) {
            return _instance._database;
        }
        return null;
    }

    /**
     * @return The number of bars to display on the anomaly charts.
     * @see R.integer#chart_total_bars
     */
    public static int getTotalBarsOnChart() {
        if (_instance != null) {
            return _instance._chartTotalBars;
        }
        return 24;
    }

    /**
     * Return the context of the single, global Application object of the
     * current process
     *
     * @see android.app.Application#getApplicationContext()
     */
    public static Context getContext() {
        if (_instance != null) {
            return _instance.getApplicationContext();
        }
        return null;
    }

    /**
     * Returns the application version from <code>AndroidManifest.xml</code>
     *
     * @see PackageInfo
     */
    public static Version getVersion() {
        if (_instance != null) {
            PackageInfo pInfo;
            try {
                PackageManager pkgMgr = _instance.getPackageManager();
                String pkgName = _instance.getPackageName();
                if (pkgMgr != null && pkgName != null) {
                    pInfo = pkgMgr.getPackageInfo(pkgName, 0);
                    return new Version(pInfo.versionName);
                }
            } catch (NameNotFoundException e) {
                Log.e(TAG, "Failed to get version");
            }
        }
        return new Version(BuildConfig.VERSION_NAME);
    }


    public static void refresh() {
        if (_instance != null && _instance._bound && _instance._dataService != null) {
            _instance._dataService.forceRefresh();
        }
    }

    /**
     * Returns {@code true} if the data service is refreshing the data
     */
    public static boolean isRefreshing() {
        return _instance != null && _instance._bound && _instance._dataService != null &&
                _instance._dataService.isRefreshing();
    }

    /**
     * Validate server connection and user credentials
     */
    public static void checkConnection() {
        if (_instance != null && _instance._bound && _instance._dataService != null) {
            _instance._dataService.checkConnection();
        }
    }

    /**
     * Overrides the default {@link YOMPClientFactory} with a custom factory.
     * <p>
     * This is useful for unit tests, allowing the test to create a custom
     * factory returning mock objects
     *
     * @param factory The factory used to create {@link YOMPClient}
     * @see YOMPApplication#connectToYOMP(String, String)
     */
    public void setYOMPClientFactory(final YOMPClientFactory factory) {
        _YOMPClientFactory = factory;
    }

    /**
     * Establish a connection to the YOMP server and returns a new instance of
     * {@link YOMPClient}
     *
     * @param serverUrl YOMP Server URL.
     * @param password  Password used to connect to YOMP server. See YOMP Web UI
     *                  to retrieve password
     * @return {@link YOMPClient} object used to interact with the server.
     */
    public YOMPClient connectToYOMP(final String serverUrl, final String password)
            throws MalformedURLException {
        if (_YOMPClientFactory != null) {
            return _YOMPClientFactory.createClient(serverUrl, password);
        }
        return null;
    }


    /**
     * Establish a connection to the YOMP server and returns a new instance of
     * {@link YOMPClient} using the the default authentication settings.
     *
     * @return {@link YOMPClient} object used to interact with the server.
     */
    public YOMPClient connectToServer() throws MalformedURLException {
        if (_YOMPClientFactory != null) {
            return _YOMPClientFactory.createClient(null, null);
        }
        return null;
    }

    /**
     * Clears the application data:
     * <ol>
     * <li>Preferences
     * <li>Database
     * </ol>
     */
    public static void clearApplicationData(Context context) {

        if (_instance != null && context != null) {
            // Clear preferences
            final SharedPreferences preferences = PreferenceManager
                    .getDefaultSharedPreferences(context);
            if (preferences != null) {
                preferences.edit().clear().apply();
                if (_instance._database != null) {
                    _instance._database.deleteAll();
                }
            }
        }
    }

    /**
     * Returns an unique device ID
     */
    public static String getDeviceId() {
        if (_instance != null) {
            return _instance._deviceId;
        }
        return Build.SERIAL;
    }

    public static long getActivityLastUsed() {
        if (_instance != null) {
            return _instance._activityLastUsed;
        }
        return System.currentTimeMillis();
    }

    public static void setActivityLastUsed() {
        if (_instance != null) {
            _instance._activityLastUsed = System.currentTimeMillis();
        }
    }

    public static int getActivityCount() {
        if (_instance != null) {
            return _instance._activityCount.get();
        }
        return 0;
    }

    public static void incrementActivityCount() {
        if (_instance != null) {
            _instance._activityCount.incrementAndGet();
        }
    }

    public static void decrementActivityCount() {
        if (_instance != null) {
            _instance._activityCount.decrementAndGet();
        }
    }

    public static String getLastError() {
        if (_instance != null) {
            return _instance._lastError;
        }
        return null;
    }

    public static void setLastError(String error) {
        if (_instance != null) {
            _instance._lastError = error;
        }
    }

    /**
     * Maximum number of days to sync.
     */
    public static int getNumberOfDaysToSync() {
        if (_instance != null) {
            return _instance._numberOfDaysToSync;
        }
        return 14;
    }

    /**
     * Stop background services
     */
    public static void stopServices() {
        if (_instance != null) {
            final Intent dataService = new Intent(_instance, YOMPService.class);
            _instance.stopService(dataService);
        }
    }

    public static boolean deleteAnnotation(String annotationId) {
        return _instance != null && _instance._bound && _instance._dataService != null &&
                _instance._dataService.deleteAnnotation(annotationId);
    }

    /**
     * @return the current {@link AggregationType}
     */
    public static AggregationType getAggregation() {
        if (_instance != null) {
            return _instance._aggregation;
        }
        return AggregationType.Day;
    }

    /**
     * Update the current {@link AggregationType}
     *
     * @param value new {@link AggregationType}
     */
    public static void setAggregation(AggregationType value) {
        if (_instance != null && value != _instance._aggregation) {
            AggregationType old = _instance._aggregation;
            _instance._aggregation = value;
            firePropertyChange(AGGREGATION_PROPERTY, old, value);
        }
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
    public static boolean addAnnotation(Date timestamp, String server, String message,
            String user) {
        return _instance != null && _instance._bound && _instance._dataService != null &&
                _instance._dataService.addAnnotation(timestamp, server, message, user);
    }

    /**
     * Control whether or not we should upload the android logs to the server.
     */
    public static boolean shouldUploadLog() {
        return _instance != null && _instance._uploadLog;
    }

    /**
     * The Yellow bar floor value, meaning the anomaly bar is yellow from this value
     *
     * @see com.numenta.core.R.fraction#yellow_bar_floor
     */
    public static float getYellowBarFloor() {
        if (_instance != null) {
            return _instance._yellowBarFloor;
        }
        return 0.4f;
    }

    /**
     * The Red bar floor value, meaning the anomaly bar is red from this value
     *
     * @see com.numenta.core.R.fraction#red_bar_floor
     */
    public static float getRedBarFloor() {
        if (_instance != null) {
            return _instance._redBarFloor;
        }
        return 0.5f;
    }

    /**
     * Returns a pre-configured thread pool to be used for generic background
     * Tasks
     *
     * @return {@link java.util.concurrent.ExecutorService} for the generic thread pool
     */
    public static ExecutorService getWorkerThreadPool() {
        if (_instance != null && _instance._bound && _instance._dataService != null) {
            return _instance._dataService.getWorkerThreadPool();
        }
        return _defaultThreadPool;
    }

    /**
     * Returns a pre-configured thread pool to be used for background tasks.
     *
     * @return {@link ExecutorService} of the background thread pool
     */

    /**
     * Returns a pre-configured thread pool to be used for I/O tasks.
     *
     * @return {@link ExecutorService} of the background thread pool
     */
    public static ExecutorService getIOThreadPool() {
        if (_instance != null && _instance._bound && _instance._dataService != null) {
            return _instance._dataService.getIOThreadPool();
        }
        return _defaultThreadPool;
    }

    /**
     * Returns the service {@link ScheduledExecutorService} used to schedule
     * background task at specific time or repeating periodic time
     *
     * @return {@link ScheduledExecutorService} of the timer thread pool
     */
    public static ScheduledExecutorService getTimerThread() {
        if (_instance != null && _instance._bound && _instance._dataService != null) {
            return _instance._dataService.getTimerThread();
        }
        return null;
    }

    /**
     * Return this application name ("YOMP", "Taurus", ...) see "core_config.xml"
     *
     * @see com.numenta.core.R.string#application_name
     */
    public static String getApplicationName() {
        if (_instance != null) {
            return _instance._applicationName;
        }
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        // At this point the Application object was created by the OS. Save instance for singleton
        _instance = this;

        // Initialize the database
        _database = createDatabase();

        Resources res = getResources();
        // Get the default number of bars to show in the anomaly chart
        _chartTotalBars = res.getInteger(R.integer.chart_total_bars);

        // Whether or not we should upload the android logs to the server
        _uploadLog = res.getBoolean(R.bool.upload_logs);

        // The number of records for which the model is still learning
        _learningThreshold = res.getInteger(R.integer.learning_threshold);

        // Maximum number of days to sync.
        _numberOfDaysToSync = res.getInteger(R.integer.number_of_days_to_sync);

        // Configure Anomaly bar settings
        _yellowBarFloor = res.getFraction(R.fraction.yellow_bar_floor, 1, 1);
        _redBarFloor = res.getFraction(R.fraction.red_bar_floor, 1, 1);

        // Default aggregation
        _aggregation = AggregationType.valueOf(res.getString(R.string.aggregation_type));

        // Application name
        _applicationName = res.getString(R.string.application_name);

        // Get this device ID
        _deviceId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);

        // Initialize Google Analytics
        try {
            String trackingId = res.getString(R.string.ga_trackingId);
            if (trackingId != null && !trackingId.isEmpty()) {
                _tracker = GoogleAnalytics.getInstance(this).newTracker(trackingId);
                _tracker.enableAutoActivityTracking(true);
                _tracker.enableExceptionReporting(true);
            } else {
                Log.w(TAG, "Failed to initialize Google Analytics. Invalid value for 'ga_trackingId'");
            }
        } catch (Resources.NotFoundException e) {
            Log.w(TAG, "Failed to initialize Google Analytics. Missing value for 'ga_trackingId'");
        }

        // Start background data synchronization service
        if (res.getBoolean(R.bool.start_services)) {
            startBackgroundServices();
        }
    }

    /**
     * Start background service
     *
     * @return If the service is being started or is already running, the ComponentName of the
     * actual service that was started is returned; else if the service does not exist null is
     * returned
     */
    public ComponentName startBackgroundServices() {
        final Intent dataService = new Intent(this, YOMPService.class);
        bindService(dataService, _YOMPDataServiceConn, Context.BIND_AUTO_CREATE);
        return startService(dataService);
    }

    /**
     * Factory used to create a new database interface allowing subclasses to override and create
     * their own database interface.
     *
     * @return The new database interface.
     */
    protected CoreDatabase createDatabase() {
        return new CoreDatabaseImpl(getContext());
    }

    /**
     * Factory used to create a new Data Synchronization service allowing subclasses to override
     * and extend  with their own Synchronization service.
     */
    public DataSyncService createDataSyncService(YOMPService service) {
        return new DataSyncService(service);
    }

    /**
     * Factory used to create a new notification service allowing subclasses to override and extend
     * with their own notification service.
     */
    public NotificationService createNotificationService(YOMPService service) {
        return new NotificationService(service);
    }

    /**
     * Returns the Google Analytics tracker for this application or {@code null} if we are not
     * using Google Analytics for this application.
     */
    public Tracker getGoogleAnalyticsTracker() {
        return _tracker;
    }

    /**
     * Allow applications to load application specific data in the background service.
     *
     * @param connection The API client connection
     */
    public void loadApplicationData(YOMPClient connection) {

    }

    /**
     * Get server version
     */
    public Version getServerVersion() {
        return _serverVersion;
    }

    /**
     * Update server version
     */
    public void setServerVersion(final Version serverVersion) {
        _serverVersion = serverVersion;
    }

    /**
     * This method should be executed periodically to send logs to the server.
     *
     * @throws com.numenta.core.service.YOMPException
     * @throws java.io.IOException
     */
    public void uploadLogs() throws YOMPException, IOException { }

}
