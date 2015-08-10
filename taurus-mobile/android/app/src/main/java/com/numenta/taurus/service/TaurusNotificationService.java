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

import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPService;
import com.numenta.core.service.NotificationService;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.NotificationUtils;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.AnomalyValue;
import com.numenta.taurus.data.Notification;
import com.numenta.taurus.data.TaurusDataFactory;
import com.numenta.taurus.data.TaurusDatabase;
import com.numenta.taurus.metric.MetricType;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.Uri;
import android.preference.PreferenceManager;
import android.support.v4.app.NotificationCompat;
import android.text.format.DateUtils;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_NOTIFICATIONS_ENABLE;
import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_NOTIFICATIONS_FREQUENCY;
import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_NOTIFICATIONS_RINGTONE;
import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_NOTIFICATIONS_VIBRATE;
import static com.numenta.taurus.preference.TaurusPreferenceConstants.PREF_NOTIFICATION_LAST_RUN_TIME;

/**
 * Taurus notification service
 *
 * <p>
 * Taurus will only notify on stock anomalies for user's "Favorite" companies.
 * The notification frequency is based on the following rules:
 * <ol>
 *
 * <li><b>No Limit:</b> Notify every time any of the favorite companies has an anomaly</li>
 *
 * <li><b>1 per <i>X</i> Hour(s):</b> Notify only once on the first anomaly received within
 * <i>X</i> hours for any of the favorite companies. Once the first anomaly notification is
 * fired for the company, all other anomalies for that company will be ignored for a period
 * of <i>X</i> hours. Currently <i>'X'</i> period can be <i>1,2,8 or 24 hours</i></li>
 *
 * </ol>
 * </p>
 */
public class TaurusNotificationService extends NotificationService {

    public TaurusNotificationService(YOMPService service) {
        super(service);
    }

    /**
     * Check if we need to fire new notifications based on the current application data and state
     */
    protected void synchronizeNotifications() throws YOMPException, IOException {
        Context context = getService().getApplicationContext();
        final SharedPreferences prefs = PreferenceManager
                .getDefaultSharedPreferences(context);

        // Check if the notifications are enabled
        boolean enable = prefs.getBoolean(PREF_NOTIFICATIONS_ENABLE, true);
        if (enable) {
            final long now = System.currentTimeMillis();

            // Get last time we checked for notifications
            final long lastRunTime =
                    DataUtils.floorTo60minutes(prefs.getLong(PREF_NOTIFICATION_LAST_RUN_TIME, now));
            prefs.edit().putLong(PREF_NOTIFICATION_LAST_RUN_TIME, now).apply();

            // Get user frequency preference
            final long frequency =
                    Long.parseLong(prefs.getString(PREF_NOTIFICATIONS_FREQUENCY, "0")) * 1000;

            // Check for pending notifications since last time
            List<Notification> notifications = getPendingNotifications(lastRunTime, now, frequency);
            if (notifications.isEmpty()) {
                // No new notifications
                return;
            }

            // Build notification based on user settings
            NotificationCompat.Builder notificationBuilder =
                    new NotificationCompat.Builder(context)
                            .setOnlyAlertOnce(true)
                            .setSmallIcon(com.numenta.core.R.drawable.ic_launcher)
                            .setAutoCancel(true);

            // Get notifications ringtone
            String ringUrlStr = prefs.getString(PREF_NOTIFICATIONS_RINGTONE, null);
            if (ringUrlStr != null && !ringUrlStr.trim().isEmpty()) {
                notificationBuilder.setSound(Uri.parse(ringUrlStr));
            }

            // Check if we should vibrate
            if (prefs.getBoolean(PREF_NOTIFICATIONS_VIBRATE, false)) {
                notificationBuilder.setDefaults(NotificationCompat.DEFAULT_VIBRATE);
                notificationBuilder.setVibrate(new long[]{1000l});
            }

            // Fire new notifications
            NotificationUtils
                    .createGroupedOsNotification(notificationBuilder, notifications, false);

            // Update notification times
            for (Notification notification : notifications) {
                TaurusApplication.setLastNotificationTime(notification.getInstanceId(),
                        notification.getTimestamp());
            }
        }
        fireNotificationChangedEvent(getService());
    }

    /**
     * Generate a list of Pending Notifications for the given period and frequency
     *
     * @param from      The initial timestamp of the period to check (inclusive)
     * @param to        The end timestamp of the period to check (inclusive)
     * @param frequency The frequency in which to fire notifications in milliseconds
     * @return pending notifications matching the criteria
     */
    List<Notification> getPendingNotifications(long from, long to, long frequency) {
        TaurusDatabase database = TaurusApplication.getDatabase();
        if (database == null) {
            return Collections.emptyList();
        }
        ArrayList<Notification> results = new ArrayList<Notification>();
        HashMap<String, Pair<Long, AnomalyValue>> anomalies = new HashMap<String, Pair<Long, AnomalyValue>>();
        EnumSet<MetricType> mask;
        // Get all anomalies for favorite instances
        for (String instance : TaurusApplication.getFavoriteInstances()) {
            // Check last time a notification was fired for this instance
            long lastFired = TaurusApplication.getLastNotificationTime(instance);
            if (lastFired > to - frequency) {
                // This instance already fired a notification for this period
                continue;
            }

            // Check for anomalies
            List<Pair<Long, AnomalyValue>> data = database.getInstanceData(instance, from, to);
            for (Pair<Long, AnomalyValue> value : data) {
                if (value.second == null) {
                    continue;
                }
                // Check for "red" anomalies
                float logScale = (float) DataUtils.logScale(Math.abs(value.second.anomaly));
                if (logScale >= TaurusApplication.getRedBarFloor()) {
                    // Check if found new stock related anomaly
                    mask = MetricType.fromMask(value.second.metricMask);
                    if (!anomalies.containsKey(instance) &&
                            !Collections.disjoint(mask, MetricType.STOCK_TYPES)) {
                        anomalies.put(instance, value);
                    }
                }
            }
        }
        // Create notifications based on anomalies filtered for the period
        TaurusDataFactory factory = database.getDataFactory();
        long timestamp;
        String instance;
        String text;
        AnomalyValue value;
        for (Map.Entry<String, Pair<Long, AnomalyValue>> entry : anomalies.entrySet()) {
            timestamp = entry.getValue().first;
            value = entry.getValue().second;
            mask = MetricType.fromMask(value.metricMask);
            instance = entry.getKey();
            text = formatAnomalyTitle(instance, mask, timestamp);
            results.add(factory.createNotification(instance, timestamp, text));
        }
        return results;
    }

    /**
     * Format anomaly title
     *
     * @param company   The company name
     * @param types     The anomaly types triggering the anomaly
     * @param timestamp The time the anomaly was fired
     * @return The formatted text suitable for OS notification
     */
    String formatAnomalyTitle(String company, EnumSet<MetricType> types, long timestamp) {
        Context ctx = getService();
        String anomalyTypes = "";

        if (!Collections.disjoint(types, MetricType.STOCK_TYPES)) {
            if (types.contains(MetricType.TwitterVolume)) {
                anomalyTypes = ctx.getString(R.string.header_stock_twitter);
            } else {
                anomalyTypes = ctx.getString(R.string.header_stock);
            }
        } else if (types.contains(MetricType.TwitterVolume)) {
            anomalyTypes = ctx.getString(R.string.header_twitter);
        }
        return String.format(ctx.getString(R.string.taurus_notification_description_template),
                company, DateUtils.formatDateTime(ctx, timestamp,
                        DateUtils.FORMAT_SHOW_DATE | DateUtils.FORMAT_SHOW_TIME), anomalyTypes);
    }
}
