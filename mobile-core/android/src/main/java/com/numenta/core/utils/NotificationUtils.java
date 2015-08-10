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

package com.numenta.core.utils;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.support.v4.app.NotificationCompat;
import android.text.format.DateUtils;

import com.numenta.core.R;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Metric;
import com.numenta.core.data.Notification;

import java.util.List;

public class NotificationUtils {

    final static Context _ctx = YOMPApplication.getContext();

    // In order to persist the right notification counts and messages, we need to keep some objects
    // static for the life of the application.  If the app resets, so will the notifications, but
    // that is the designed behavior.
    private static int _groupedNotificationCount = 0;
    private static NotificationCompat.InboxStyle _inboxStyle = new NotificationCompat.InboxStyle();

    /**
     * Creates a new OS notification
     *
     * @param description
     * @param when
     * @param notificationId
     * @param totalNotifications
     */
    public static void createOSNotification(String description, long when,
            int notificationId, long totalNotifications) {
        final int osNotificationId = 1;
        // TODO: Do the proper thing with strings here instead
        // of concatenating them.

        String groupedMessage = totalNotifications + " "
                + _ctx.getString(R.string.title_os_notification_grouped);
        Intent resultIntent;
        NotificationCompat.Builder notificationBuilder = new NotificationCompat.Builder(_ctx)
                .setDefaults(android.app.Notification.DEFAULT_ALL)
                .setOnlyAlertOnce(true)
                .setSmallIcon(R.drawable.ic_launcher)
                .setContentTitle("YOMP Anomaly Notification");

        // Send OS notification.
        if (totalNotifications > 1) {
            notificationBuilder.setContentText(groupedMessage);
            // Intent to open the notification list when there's
            // multiple activities.
            resultIntent = new Intent(YOMPApplication.ACTION_SHOW_NOTIFICATION_LIST);
            notifyOS(_ctx, resultIntent, notificationBuilder, osNotificationId);
        } else {
            notificationBuilder.setContentText(description).setWhen(when);
            // Get the metric necessary for the new intent to
            // view the metric detail page.
            resultIntent = new Intent(YOMPApplication.ACTION_SHOW_NOTIFICATION);
            resultIntent.putExtra("id", notificationId);
            notifyOS(_ctx, resultIntent, notificationBuilder, osNotificationId);
        }
    }

    /**
     *
     */
    public static void resetGroupedNotifications() {
        _groupedNotificationCount = 0;
        _inboxStyle = new NotificationCompat.InboxStyle();
    }

    /**
     * Create "Inbox" style OS notification
     *
     * @param notificationList The list of notifications to add to the notification inbox
     */
    public static void createGroupedOsNotification(
            List<? extends Notification> notificationList) {
        NotificationCompat.Builder builder =
                new NotificationCompat.Builder(_ctx)
                        .setDefaults(android.app.Notification.DEFAULT_ALL)
                        .setOnlyAlertOnce(true)
                        .setSmallIcon(R.drawable.ic_launcher)
                        .setAutoCancel(true);
        createGroupedOsNotification(builder, notificationList, true);
    }

    /**
     * Create "Inbox" style OS notification
     *
     * @param notificationBuilder The notification builder to use
     * @param notificationList    The list of notifications to add to the notification inbox
     * @param showSummary         Whether or not to show a summary header
     */
    public static void createGroupedOsNotification(NotificationCompat.Builder notificationBuilder,
            List<? extends Notification> notificationList,
            boolean showSummary) {
        if (notificationList == null || notificationList.isEmpty()) {
            return;
        }

        final int osNotificationId = 1;
        _groupedNotificationCount += notificationList.size();

        StringBuilder groupedTitle = new StringBuilder();
        groupedTitle.append(_groupedNotificationCount);
        groupedTitle.append(" ");
        groupedTitle.append(_ctx.getString(R.string.title_os_notification_grouped));

        if (showSummary) {
            // Display summary as title and list below
            _inboxStyle.setBigContentTitle(groupedTitle);
            notificationBuilder.setContentTitle(groupedTitle);
            for (Notification notification : notificationList) {
                _inboxStyle.addLine(notification.getDescription());
            }
        } else {
            // Show first item as title and other items below
            String description = notificationList.get(0).getDescription();
            _inboxStyle.setBigContentTitle(description);
            notificationBuilder.setContentTitle(description).setContentText(groupedTitle);
            for (int i = 1; i < notificationList.size(); i++) {
                _inboxStyle.addLine(notificationList.get(i).getDescription());
            }
        }
        // There seems to be a bug in the notification display system where, unless you set
        // summary text, single line expanded inbox state will not expand when the notif
        // drawer is fully pulled down. However, it still works in the lock-screen.
        // See http://stackoverflow.com/a/27972211/2812273
        _inboxStyle.setSummaryText(groupedTitle);
        notificationBuilder.setNumber(_groupedNotificationCount);
        notificationBuilder.setStyle(_inboxStyle);

        Intent resultIntent = new Intent(YOMPApplication.ACTION_SHOW_NOTIFICATION_LIST);
        notifyOS(_ctx, resultIntent, notificationBuilder, osNotificationId);
    }

    /**
     * Format Notification description based on instance name and timestamp
     *
     * @param instanceName
     * @param timestamp
     * @return Formatted notification description using
     */
    public static String formatSimpleNotificationDescription(String instanceName, long timestamp) {
        // Formatted Notification description:
        // $1=metric.instanceName,
        // $2=timestamp

        // Gets the standard date formatter for the current locale of
        // the device
        String formattedCurrentDate = DateUtils.formatDateTime(
                YOMPApplication.getContext(), timestamp,
                DateUtils.FORMAT_SHOW_DATE | DateUtils.FORMAT_SHOW_TIME);

        return String.format(
                YOMPApplication.getContext().getString(R.string.simple_notification_description_template),
                instanceName,
                formattedCurrentDate);
    }

    /**
     * Format Notification description based on metric and metric data
     *
     * @param metric
     * @param metricValue
     * @param timestamp
     * @return Formatted notification description using
     */
    public static String formatNotificationDescription(Metric metric, float metricValue,
            long timestamp) {
        // Formatted Notification description:
        // $1=metric.instance,
        // $2=metric.name,
        // $3=metric_data.value,
        // $4=metric.unit
        // $5=timestamp
        return String.format(
                YOMPApplication.getContext().getString(R.string.notification_description_template),
                metric.getServerName(),
                metric.getName(),
                metricValue,
                metric.getUnit(),
                timestamp);
    }

    public static void notifyOS(Context ctx, Intent resultIntent,
            NotificationCompat.Builder notificationBuilder, int osNotificationId) {
        PendingIntent resultPendingIntent = PendingIntent.getActivity(
                ctx,
                0,
                resultIntent,
                PendingIntent.FLAG_UPDATE_CURRENT);
        notificationBuilder.setContentIntent(resultPendingIntent);

        NotificationManager notificationManager = (NotificationManager) ctx
                .getSystemService(Context.NOTIFICATION_SERVICE);
        notificationManager.notify(osNotificationId, notificationBuilder.build());

    }
}
