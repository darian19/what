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

package com.numenta.core.data;

import org.json.JSONObject;

import android.database.Cursor;

/**
 * Factory used to create Core Database objects. It should be supplied by applications who need to
 * extend any of the {@link CoreDatabase} objects.
 *
 * @see com.numenta.core.data.Metric
 * @see com.numenta.core.data.MetricData
 * @see com.numenta.core.data.Instance
 * @see com.numenta.core.data.InstanceData
 * @see com.numenta.core.data.Notification
 * @see com.numenta.core.data.Annotation
 */
public interface CoreDataFactory {

    /**
     * Create a {@link com.numenta.core.data.Annotation} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.Annotation} object.
     *
     * @see com.numenta.core.data.Annotation
     */
    Annotation createAnnotation(Cursor cursor);

    /**
     * Create a new {@link com.numenta.core.data.Metric} object
     *
     * @param annotationId The annotation ID
     * @param timestamp    The timestamp for the annotation
     * @param created      The timestamp the annotation was created
     * @param device       The device ID in which the annotation was created
     * @param user         The user who created the annotation
     * @param instanceId   The instance ID associated with this annotation
     * @param message      The annotation message
     * @param data         Annotation user data
     */
    Annotation createAnnotation(String annotationId, long timestamp, long created,
            String device, String user, String instanceId, String message,
            String data);

    /**
     * Create a {@link com.numenta.core.data.Metric} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.Metric} object.
     *
     * @see com.numenta.core.data.Metric
     */
    Metric createMetric(Cursor cursor);

    /**
     * Create a new {@link com.numenta.core.data.Metric} object
     *
     * @param metricId   The metric ID
     * @param name       Metric Name
     * @param instanceId The instance ID of the instance associated with this metric
     * @param serverName The name of the instance associated with this metric
     * @param lastRowId  Last know row ID for this metric
     * @param parameters Optional metric parameters
     */
    Metric createMetric(String metricId, String name, String instanceId, String serverName,
            int lastRowId, JSONObject parameters);

    /**
     * Create a {@link com.numenta.core.data.MetricData} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.MetricData} object.
     *
     * @see com.numenta.core.data.MetricData
     */
    MetricData createMetricData(Cursor cursor);

    /**
     * Create a new {@link com.numenta.core.data.MetricData} object
     *
     * @param metricId     The metric ID
     * @param timestamp    The timestamp
     * @param metricValue  The metric value
     * @param anomalyScore The anomaly score
     * @param rowid        The row id
     */
    MetricData createMetricData(String metricId, long timestamp, float metricValue,
            float anomalyScore, long rowid);

    /**
     * Create a new {@link com.numenta.core.data.Instance} object
     *
     * @param id        The instance ID
     * @param name      The instance name
     * @param namespace The instance namespace
     * @param location  The instance location
     * @param message   The last known error message
     * @param status    The last known error status
     */
    Instance createInstance(String id, String name, String namespace, String location,
            String message,
            int status);

    /**
     * Create a {@link com.numenta.core.data.InstanceData} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.InstanceData} object.
     *
     */
    InstanceData createInstanceData(Cursor cursor);

    /**
     * Create a new {@link com.numenta.core.data.Metric} object
     *
     * @param instanceId   The instance ID
     * @param aggregation  The aggregation type
     * @param timestamp    The timestamp
     * @param anomalyScore The anomaly score
     */
    InstanceData createInstanceData(String instanceId, AggregationType aggregation, long timestamp,
            float anomalyScore);

    /**
     * Create a {@link com.numenta.core.data.Notification} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.Notification} object.
     *
     * @see com.numenta.core.data.Notification
     */
    Notification createNotification(Cursor cursor);


    /**
     * Create a new {@link com.numenta.core.data.Notification} object
     *
     * @param notificationId Server generated notification ID
     * @param metricId       The metric ID associated with the notification
     * @param timestamp      The notification timestamp
     * @param read           Whether or not the notification was read
     * @param description    The notification description
     */
    Notification createNotification(String notificationId, String metricId, long timestamp,
            boolean read, String description);
}
