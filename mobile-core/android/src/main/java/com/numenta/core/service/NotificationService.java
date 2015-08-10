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
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.data.Metric;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.NotificationUtils;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.Resources;
import android.preference.PreferenceManager;
import android.support.v4.content.LocalBroadcastManager;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import static com.numenta.core.preference.PreferencesConstants.PREF_NOTIFICATIONS_ENABLE;

/**
 * This service is managed by {@link YOMPService} and is responsible for creating notifications
 * based on the user's preferences.
 */
public class NotificationService {

    /**
     * This Event is fired on new notifications
     */
    public static final String NOTIFICATION_CHANGED_EVENT
            = "com.numenta.core.data.NotificationChangedEvent";

    private static final String TAG = NotificationService.class.getSimpleName();

    private final YOMPService _service;

    // YOMP API Helper
    private YOMPClient _YOMPCli;

    public NotificationService(YOMPService service) {
        this._service = service;
    }

    /**
     * Fire {@link #NOTIFICATION_CHANGED_EVENT}
     */
    protected static void fireNotificationChangedEvent(Context context) {
        Log.i(TAG, "{TAG:ANDROID.NOTIFICATION.FIRE} Notification changed");
        Intent intent = new Intent(NOTIFICATION_CHANGED_EVENT);
        LocalBroadcastManager.getInstance(context).sendBroadcast(intent);
    }

    /**
     * Delete all notifications and Broadcast {@link #NOTIFICATION_CHANGED_EVENT} if any
     * notification
     * was deleted
     *
     * @return number of notifications deleted
     */
    public static long deleteAllNotifications() {
        long deleted = YOMPApplication.getDatabase().deleteAllNotifications();
        if (deleted > 0) {
            fireNotificationChangedEvent(YOMPApplication.getContext());
        }
        return deleted;
    }

    /**
     * Delete the notification by id.
     *
     * @param notificationId The notification id to delete
     * @return number of notifications deleted (1 or 0)
     */
    public static long deleteNotification(int notificationId) {
        long deleted = YOMPApplication.getDatabase().deleteNotification(notificationId);
        if (deleted > 0) {
            fireNotificationChangedEvent(YOMPApplication.getContext());
        }
        return deleted;
    }

    /**
     * Download and fire new notifications from the server
     */
    protected void synchronizeNotifications() throws YOMPException, IOException {
        final Resources res = YOMPApplication.getContext().getResources();

        // Try to connect to YOMP
        if (_YOMPCli == null) {
            _YOMPCli = _service.connectToServer();
        }
        if (_YOMPCli == null) {
            throw new IOException("Unable to connect to server");
        }

        Metric metric;
        long localId;
        boolean newNotification = false;
        long notificationCount;
        ArrayList<String> acknowledge = new ArrayList<String>();
        final CoreDatabase YOMPdb = YOMPApplication.getDatabase();
        final SharedPreferences prefs =
                PreferenceManager.getDefaultSharedPreferences(_service.getApplicationContext());

        // Check if the notifications are enabled
        boolean enable = prefs.getBoolean(PREF_NOTIFICATIONS_ENABLE, true);
        boolean groupNotifications = res.getBoolean(R.bool.group_notifications);

        // Download pending notifications from the server
        List<Notification> pendingNotifications = _YOMPCli.getNotifications();
        if (pendingNotifications == null || pendingNotifications.isEmpty()) {
            return;
        }

        if (groupNotifications) {
            if (enable) {
                for (Notification notification : pendingNotifications) {
                    // Add Notification to local database
                    localId = YOMPdb.addNotification(notification.getNotificationId(),
                            notification.getMetricId(),
                            notification.getTimestamp(),
                            notification.getDescription());
                    if (localId != -1) {
                        newNotification = true;
                    }
                }
                NotificationUtils.createGroupedOsNotification(pendingNotifications);
            }
        } else {
            for (Notification notification : pendingNotifications) {
                // Update notification description;
                metric = YOMPdb.getMetric(notification.getMetricId());
                if (metric != null) {
                    // Add Notification to local database
                    localId = YOMPdb.addNotification(notification.getNotificationId(),
                            notification.getMetricId(),
                            notification.getTimestamp(),
                            notification.getDescription());
                    if (localId != -1) {
                        // This is a new notification
                        newNotification = true;

                        // Fire OS notification
                        if (enable) {
                            notificationCount = YOMPdb.getUnreadNotificationCount();
                            NotificationUtils.createOSNotification(notification.getDescription(),
                                    notification.getTimestamp(), (int) localId, notificationCount);
                        }
                        Log.i(TAG, "{TAG:ANDROID.NOTIFICATION.ADD} "
                                + notification.getTimestamp()
                                + " "
                                + notification.getMetricId()
                                + " - "
                                + notification.getDescription());

                    }
                } else {
                    Log.w(TAG, "Notification received for unknown metric: " + notification
                            .getMetricId());
                }
                acknowledge.add(notification.getNotificationId());
            }

            // Acknowledge notifications
            _YOMPCli.acknowledgeNotifications(acknowledge.toArray(new String[acknowledge.size()]));
        }

        // Fire notification event
        if (newNotification) {
            fireNotificationChangedEvent(_service);
        }
    }

    /**
     * Return the background service object
     */
    public YOMPService getService() {
        return _service;
    }

    /**
     * Returns the API client connection
     */
    public YOMPClient getClient() throws IOException, YOMPException {
        if (_YOMPCli == null) {
            _YOMPCli = _service.connectToServer();
        }
        if (_YOMPCli == null) {
            throw new IOException("Unable to connect to server");
        }
        return _YOMPCli;
    }

    /**
     * Close Client API connection forcing the service to reopen a new connection upon request
     */
    public void disconnect() {
        _YOMPCli = null;
    }

    /**
     * Start the notification service.
     * <p>
     * Should only be called by {@link YOMPService}
     * </p>
     */
    protected void start() {
    }

    /**
     * Stop the notification service.
     * <p>
     * Should only be called by {@link YOMPService}
     * </p>
     */
    protected void stop() {
    }
}
