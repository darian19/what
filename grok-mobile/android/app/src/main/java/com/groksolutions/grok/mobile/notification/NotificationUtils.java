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

package com.YOMPsolutions.YOMP.mobile.notification;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.YOMPsolutions.YOMP.mobile.metric.MetricDetailActivity;
import com.numenta.core.data.Metric;
import com.numenta.core.data.Notification;

import android.content.Context;
import android.content.Intent;
import android.os.AsyncTask;
import android.support.v4.app.NotificationCompat;

public class NotificationUtils extends com.numenta.core.utils.NotificationUtils {

    /**
     * Create {@link MetricDetailActivity} {@link Intent} configured to be used
     * as the notification result intent for the given notification and the
     * given metric
     *
     * @param ctx The {@link Context}
     * @param notification The {@link Notification}
     * @return A new {@link Intent} that will open the
     *         {@link MetricDetailActivity} showing the metric data associated
     *         with the notification.
     * @see #createOSNotification(String, long, int, long)
     * @see NotificationListActivity
     */
    public static Intent createMetricDetailIntent(final Context ctx,
            final Notification notification) {
        final YOMPDatabase YOMPDb = YOMPApplication.getDatabase();
        final Metric metric = YOMPDb.getMetric(notification.getMetricId());
        final Intent resultIntent = new Intent(ctx, MetricDetailActivity.class);
        resultIntent.setFlags(
                Intent.FLAG_ACTIVITY_NO_HISTORY
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
                        | Intent.FLAG_ACTIVITY_NEW_TASK
                        // | Intent.FLAG_ACTIVITY_SINGLE_TOP
                        | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS);
        resultIntent.putExtra(MetricDetailActivity.EXTRA_METRIC, metric.getId());
        resultIntent.putExtra(MetricDetailActivity.EXTRA_DATE,
                notification.getTimestamp());
        return resultIntent;

    }

    static final class NotificationAsyncTask extends AsyncTask<Void, Void, Intent> {

        private final NotificationCompat.Builder notificationBuilder;
        private final int notificationId;
        private final Context ctx;
        private final int osNotificationId = 1;

        public NotificationAsyncTask(NotificationCompat.Builder notificationBuilder,
                int notificationId, Context ctx) {
            this.notificationBuilder = notificationBuilder;
            this.notificationId = notificationId;
            this.ctx = ctx;
        }

        @Override
        protected Intent doInBackground(Void... voids) {
            final YOMPDatabase YOMPDb = YOMPApplication.getDatabase();
            Notification notification = YOMPDb.getNotificationByLocalId(notificationId);
            return createMetricDetailIntent(ctx, notification);
        }

        @Override
        protected void onPostExecute(Intent resultIntent) {
            notifyOS(ctx, resultIntent, notificationBuilder, osNotificationId);
        }
    }
}
