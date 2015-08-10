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


import com.numenta.core.app.YOMPApplication;
import com.numenta.core.utils.BackgroundThreadFactory;
import com.numenta.core.utils.Log;

import android.app.IntentService;
import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.support.v4.content.LocalBroadcastManager;
import android.support.v4.content.WakefulBroadcastReceiver;

import java.io.IOException;
import java.util.Date;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;


/**
 * <code>YOMPService</code> is a background {@link Service} responsible for
 * fetching data from YOMP server and updating its local data cache.
 */
public class YOMPService extends IntentService {
    private static final String TAG = "YOMPService";

    // Upload logs each hour.
    private static final int LOG_UPLOAD_INTERVAL = 60;
    // Run clean up task each hour.
    private static final int CLEANUP_TASK_INTERVAL = 60;
    // Max HTTP Connections to cache (http.maxConnections) @see
    // http://developer.android.com/reference/java/net/HttpURLConnection.html
    private static final int HTTP_CONNECTION_POOL_SIZE = 100;
    // I/O thread pool size
    private static final int IOTHREAD_POOL_SIZE = 10;
    // I/O thread pool
    private ExecutorService _ioThreadPool;
    // Generic worker thread pool size
    //private static final int WORKER_POOL_SIZE = 10;

    // Generic worker thread pool
    private ExecutorService _workerPool;
    // Single thread pool used to schedule periodic tasks
    private ScheduledExecutorService _timer;
    // This task will periodically upload the application logs to the server
    private ScheduledFuture<?> _updateLogsTask;
    // This task will periodically run clean up tasks
    private ScheduledFuture<?> _cleanupTask;
    // Data synchronization service
    private DataSyncService _dataSyncService;
    // Notification Services
    private NotificationService _notificationService;

    // Background worker thread factory
    private static final ThreadFactory WORKER_THREAD_FACTORY = new BackgroundThreadFactory("Worker");
    // Background IO thread factory
    private static final ThreadFactory IO_THREAD_FACTORY = new BackgroundThreadFactory("IOThread");
    // Background timer thread factory
    private static final ThreadFactory TIMER_THREAD_FACTORY = new BackgroundThreadFactory("Timer");

    private final YOMPDataBinder _binder = new YOMPDataBinder();

    /**
     * This Event is fired whenever the client fails to authenticate with the
     * server.
     */
    public static final String AUTHENTICATION_FAILED_EVENT = "com.numenta.core.data.AuthenticationFailedEvent";

    /**
     * Force client to refresh the data by downloading new data from the server
     */
    public void forceRefresh() {
        _dataSyncService.forceRefresh();
    }

    /**
     * Delete annotation from the server
     * @param annotationId The annotation ID to delete
     */
    public boolean deleteAnnotation(String annotationId) {
        return _dataSyncService.deleteAnnotation(annotationId);
    }

    /**
     * Add new annotation associating it to the given server and the given timestamp.
     * The current device will also be associated with the annotation.
     *
     * @param timestamp The date and time to be annotated
     * @param server    Instance Id associated with this annotation
     * @param message   Annotation message
     * @param user      User name
     *
     * @return {@code true} if the annotation was successfully added to the server
     */
    public boolean addAnnotation(Date timestamp, String server, String message, String user) {
        return _dataSyncService.addAnnotation(timestamp, server, message, user);
    }
    /**
     * Force client to synchronize notifications with the server
     *
     * @throws IOException
     * @throws YOMPException
     */
    public void synchronizeNotifications() throws YOMPException, IOException {
        _notificationService.synchronizeNotifications();
    }

    /**
     * Validate user credentials and server connection
     */
    public void checkConnection() {
        getIOThreadPool().execute(new Runnable() {
            @Override
            public void run() {
                // Try to connect to YOMP
                try {
                    YOMPClient YOMP = connectToServer();
                    if (YOMP != null) {
                        YOMP.login();
                    } else {
                        throw new YOMPException("Unable to connect to YOMP");
                    }
                } catch (AuthenticationException e) {
                    fireAuthenticationFailedEvent();
                } catch (YOMPException e) {
                    Log.e(TAG, "Unable to connect to YOMP", e);
                } catch (IOException e) {
                    Log.e(TAG, "Unable to connect to YOMP", e);
                }
            }
        });
    }

    /**
     * Returns {@code true} if the data service is refreshing the data
     */
    public boolean isRefreshing() {
        return _dataSyncService.isRefreshing();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return _binder;
    }

    /**
     * Class used for the client Binder. Because we know this service always
     * runs in the same process as its clients, we don't need to deal with IPC.
     */
    public class YOMPDataBinder extends Binder {
        public YOMPService getService() {
            // Return this instance of LocalService so clients can call public
            // methods
            return YOMPService.this;
        }
    }

    /**
     * Creates and executes a periodic action at the given delay, and
     * subsequently with the given delay between the termination of one
     * execution and the commencement of the next. If any execution of the task
     * encounters an exception, subsequent executions are suppressed. Otherwise,
     * the task will only terminate via cancellation or termination of the
     * executor.
     *
     * @param task the task to execute
     * @param rate the delay between the termination of one execution and the
     *            commencement of the next
     * @param unit the time unit of the initialDelay and delay parameters
     * @return a ScheduledFuture representing pending completion of the task,
     *         and whose <tt>get()</tt> method will throw an exception upon
     *         cancellation
     * @throws RejectedExecutionException if the task cannot be scheduled for
     *             execution
     * @throws NullPointerException if command is null
     * @throws IllegalArgumentException if delay less than or equal to zero
     */
    public ScheduledFuture<?> scheduleTask(Runnable task, long rate,
            TimeUnit unit) {
        return _timer.scheduleWithFixedDelay(task, 0, rate, unit);
    }

    /**
     * Returns the service {@link ScheduledExecutorService} used to schedule
     * background task at specific time or repeating periodic time
     *
     * @return {@link ScheduledExecutorService}
     */
    public ScheduledExecutorService getTimerThread() {
        return _timer;
    }

    /**
     * Returns a pre-configured thread pool to be used for I/O Tasks
     *
     * @return {@link ExecutorService} for the I/O thread pool
     */
    public ExecutorService getIOThreadPool() {
        return _ioThreadPool;
    }

    /**
     * Returns a pre-configured thread pool to be used for generic background
     * Tasks
     *
     * @return {@link ExecutorService} for the generic thread pool
     */
    public ExecutorService getWorkerThreadPool() {
        return _workerPool;
    }

    public YOMPService() {
        super("YOMPService");
    }

    public void cancelScheduledTasks() {
        if (_timer != null) {
            if (_cleanupTask != null) {
                _cleanupTask.cancel(false);
            }
            if (_updateLogsTask != null) {
                _updateLogsTask.cancel(false);
            }
        }
    }

    public void startScheduledTasks() {
        // Schedule clean up tasks
        _cleanupTask = _timer.scheduleWithFixedDelay(new Runnable() {
            @Override
            public void run() {
                YOMPApplication.getDatabase().deleteOldRecords();
            }
        }, CLEANUP_TASK_INTERVAL / 10, CLEANUP_TASK_INTERVAL, TimeUnit.MINUTES);

        // Schedule Log uploads
        if (YOMPApplication.shouldUploadLog()) {
            _updateLogsTask = _timer.scheduleWithFixedDelay(new Runnable() {
                @Override
                public void run() {
                    try {
                        YOMPApplication.getInstance().uploadLogs();
                    } catch (Exception e) {
                        Log.e(TAG, "Error uploading Logs", e);
                    }
                }
            }, LOG_UPLOAD_INTERVAL / 6, LOG_UPLOAD_INTERVAL, TimeUnit.MINUTES);
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i(TAG, "Service started");
        AlarmReceiver alarm = new AlarmReceiver();
        alarm.startAlarm(getApplicationContext());

        // Initialize thread pools
        _timer = Executors.newSingleThreadScheduledExecutor(TIMER_THREAD_FACTORY);
        _ioThreadPool = Executors.newFixedThreadPool(IOTHREAD_POOL_SIZE, IO_THREAD_FACTORY);
        _workerPool = Executors.newCachedThreadPool(WORKER_THREAD_FACTORY);// Executors.newFixedThreadPool(WORKER_POOL_SIZE);

        // Optimize HTTP connection by keeping the HTTP connections alive and
        // reusing them
        System.getProperties().setProperty(
                "sun.net.http.errorstream.enableBuffering", "true");
        System.getProperties().setProperty("http.maxConnections",
                String.valueOf(HTTP_CONNECTION_POOL_SIZE));

        startScheduledTasks();

        // Start Metric Data Sync Service
        _dataSyncService = YOMPApplication.getInstance().createDataSyncService(this);
        _dataSyncService.start();

        // TODO: Start Notification Service, taking into account prefs
        _notificationService = YOMPApplication.getInstance().createNotificationService(this);
        _notificationService.start();
    }

    /**
     * Fire {@link YOMPService#AUTHENTICATION_FAILED_EVENT}
     */
    public void fireAuthenticationFailedEvent() {
        Intent intent = new Intent(YOMPService.AUTHENTICATION_FAILED_EVENT);
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent);
    }

    /**
     * Attempts to stop all actively executing I/O tasks and halts the
     * processing of waiting I/O tasks.
     * <p>
     * This method does not wait for actively executing tasks to terminate
     * beyond best-effort attempts to stop processing actively executing tasks.
     *
     * @see ExecutorService#shutdownNow()
     */
    public void cancelPendingIOTasks() {
        if (_ioThreadPool != null) {
            // Shutdown pending task. Interrupt if necessary
            _ioThreadPool.shutdownNow();
            // Don't wait for old tasks to terminate before restarting the pool
            _ioThreadPool = Executors.newFixedThreadPool(IOTHREAD_POOL_SIZE, IO_THREAD_FACTORY);
        }
    }

    /**
     * Establish a connection with YOMP server.
     *
     * @return {@link YOMPClient} object used to get data from the server
     * @throws IOException
     * @throws YOMPException
     */
    public YOMPClient connectToServer() throws YOMPException, IOException {
        YOMPClient connection;
        try {
            connection = YOMPApplication.getInstance().connectToServer();
            if (connection != null) {
                connection.login();
                YOMPApplication.getInstance().setServerVersion(connection.getServerVersion());
                Log.i(TAG, "Service connected to " + connection.getServerUrl()
                        + " - Version : " + YOMPApplication.getInstance().getServerVersion());
            } else {
                Log.e(TAG, "Unable to connect to YOMP.");
            }
        } catch (AuthenticationException e) {
            Log.w(TAG, "Authentication failure");
            throw e;
        } catch (YOMPException e) {
            Log.e(TAG, "Unable to connect to YOMP.", e);
            throw e;
        } catch (IOException e) {
            Log.e(TAG, "Unable to connect to YOMP.", e);
            throw e;
        }

        //if we're connecting to a new server, make sure to cancel existing scheduled tasks
        //and restart them so that they use the new connection
        cancelScheduledTasks();
        startScheduledTasks();

        return connection;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.i(TAG, "Service stopped");

        // Stop child Services
        if (_dataSyncService != null) {
            _dataSyncService.stop();
        }
        if (_notificationService != null) {
            _notificationService.stop();
        }

        // Stop periodic tasks
        if (_updateLogsTask != null) {
            _updateLogsTask.cancel(true);
        }
        if (_cleanupTask != null) {
            _cleanupTask.cancel(true);
        }

        // Shutdown thread pools
        if (_ioThreadPool != null) {
            _ioThreadPool.shutdown();
        }
        if (_workerPool != null) {
            _workerPool.shutdown();
        }
        if (_timer != null) {
            _timer.shutdown();
        }
    }

    @Override
    protected void onHandleIntent(Intent intent) {
        Log.i(TAG, "onHandleIntent:");
        // Force data synchronization
        try {
            _dataSyncService.synchronizeWithServer();
        } catch (IOException e) {
            Log.e(TAG, "Unable to connect", e);
        }
        // Handle the case when the intent was sent from the AlarmManger
        if (intent != null) {
            WakefulBroadcastReceiver.completeWakefulIntent(intent);
        }
    }
}
