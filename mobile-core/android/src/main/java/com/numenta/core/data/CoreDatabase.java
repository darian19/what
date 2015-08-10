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

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Set;

/**
 * Mobile Core Database Helper.
 * <p>
 * Interface between the application and the local mobile database
 * </p>
 *
 * <b>NOTE:</b> Database operations may take a long time to return, so you should not
 * call it from the application main thread
 */
public interface CoreDatabase {

    /**
     * <p>The current database version.</p>
     * <p>The database version is global for all applications using "mobile-core". Whenever one of
     * the applications using "mobile-core" needs to update the database this number must be
     * incremented and the application specific migration script should be placed under the apps
     * "/assets/apps/db_migrations" directory.</p>
     */
    int getVersion();

    /**
     * The database file name
     */
    String getFileName();

    /**
     * @see com.numenta.core.data.SQLiteHelper#getReadableDatabase()
     */
    SQLiteDatabase getReadableDatabase();

    /**
     * @see com.numenta.core.data.SQLiteHelper#getReadableDatabase()
     */
    SQLiteDatabase getWritableDatabase();

    /**
     * Return Factory used to create data model objects
     */
    CoreDataFactory getDataFactory();

    /**
     * Return the last timestamp known to the database
     *
     * @return last time stamp
     */
    long getLastTimestamp();

    /**
     * Delete old records keeping the database size manageable.
     * <p>
     * Old records are records outside our data time window.
     *
     * @see com.numenta.core.app.YOMPApplication#getNumberOfDaysToSync()
     */
    int deleteOldRecords();

    /**
     * Delete all records in the database
     */
    void deleteAll();

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Metric Table
    ////////////////////////////////////////////////////////////////////////////////////////////////

    /**
     * Add a new metric to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    long addMetric(Metric metric);

    /**
     * Returns a {@link java.util.Collection} of all metrics in this database
     *
     * @return {@link java.util.Collection} containing the metrics
     */
    Collection<Metric> getAllMetrics();

    /**
     * Returns a single metric definition given it's id
     *
     * @param id metric id
     * @return {@link com.numenta.core.data.Metric} or <code>null</code> if not found
     */
    Metric getMetric(String id);

    /**
     * Update metric values
     *
     * @param metric New metric values. Metric ID must exist or this call will
     *               fail
     * @return {@code true} if metric was updated {@code false} otherwise
     */
    boolean updateMetric(Metric metric);

    /**
     * Deletes the metric and it's data from the database
     *
     * @return the number of rows affected
     */
    long deleteMetric(String id);

    /**
     * Returns all metrics for the given instance
     *
     * @return {@link java.util.List} of {@link com.numenta.core.data.Metric}s for the given
     * instanceId
     */
    ArrayList<Metric> getMetricsByInstanceId(String instanceId);

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Metric Data Table
    ////////////////////////////////////////////////////////////////////////////////////////////////

    /**
     * Insert multiple metric data records in a single transaction, replacing existing values with
     * new ones.
     *
     * @param batch A {@link java.util.Collection} of {@link MetricData} batch to insert
     * @return {@code true}, if this insert is successful, {@code false} otherwise.
     */
    boolean addMetricDataBatch(Collection<MetricData> batch);

    /**
     * Get metric data as a {@link android.database.Cursor}
     *
     * @param metricId     The metric id to get. Passing null will return all data
     * @param columns      A list of which columns to return. Passing null will
     *                     return all columns
     * @param from         return records from this date
     * @param to           return records up to this date
     * @param anomalyScore return records whose anomaly score are greater or
     *                     equal to this value. 0 for all scores.
     * @param limit        max number of records to return. 0 for no limit
     * @return A {@link android.database.Cursor} object, which is positioned before the first
     * entry. Note that {@link android.database.Cursor}s are not synchronized
     */
    Cursor getMetricData(String metricId, String columns[], Date from, Date to, float anomalyScore,
            int limit);

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Instance Data Table
    ////////////////////////////////////////////////////////////////////////////////////////////////

    /**
     * Insert multiple instance data records in a single transaction, replacing existing values
     * with new ones.
     *
     * @param batch A {@link java.util.Collection} of {@link InstanceData} batch to insert
     * @return {@code true}, if this insert is successful, {@code false} otherwise.
     */
    boolean addInstanceDataBatch(Collection<InstanceData> batch);

    /**
     * Get instance data as a {@link android.database.Cursor}
     *
     * @param instanceId   The instance id to get. Passing null will return all data
     * @param columns      A list of which columns to return. Passing null will
     *                     return all columns
     * @param aggregation  return records filtered by this aggregation period or null for all
     * @param from         return records from this date or null to ignore
     * @param to           return records up to this date or null to ignore
     * @param anomalyScore return records whose anomaly score are greater or
     *                     equal to this value. 0 for all scores.
     * @param limit        max number of records to return. 0 for no limit
     * @return A {@link android.database.Cursor} object, which is positioned before the first
     * entry. Note that {@link android.database.Cursor}s are not synchronized
     */
    Cursor getInstanceData(String instanceId, String[] columns, AggregationType aggregation,
            Date from, Date to, float anomalyScore, int limit);

    /**
     * Returns a {@link java.util.Set} for all servers in this database
     *
     * @return {@link java.util.Set} containing Instance IDs.
     */
    Set<String> getAllInstances();

    /**
     * Update instance data values
     *
     * @param instanceData New instance data values.
     */
    boolean updateInstanceData(InstanceData instanceData);

    /**
     * Delete the given instance and its dependent objects such as
     * {@link com.numenta.core.data.Metric}, {@link com.numenta.core.data.Annotation} and
     * {@link com.numenta.core.data.Notification}
     *
     * @param instance The instance id to delete
     */
    void deleteInstance(String instance);

    /**
     * Deletes instance data for the given instance id
     */
    void deleteInstanceData(String instanceId);

    /**
     * Returns the server name given it's instance id
     *
     * @return The server name or the instanceId if name is not present
     */
    String getServerName(String instanceId);

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Notification Table
    ////////////////////////////////////////////////////////////////////////////////////////////////

    /**
     * Add a new notification to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    int addNotification(String notificationId, String metricId, long timestamp,
            String description);

    /**
     * Returns a {@link java.util.Collection} of all {@link com.numenta.core.data.Notification}s in
     * this database
     *
     * @return {@link java.util.Collection} containing the {@link com.numenta.core.data.Notification}s
     */
    Collection<Notification> getAllNotifications();

    /**
     * Returns Notification object given an localId.
     */
    Notification getNotificationByLocalId(int localId);

    /**
     * Returns the number of unread Notifications
     */
    long getUnreadNotificationCount();

    /**
     * Returns the number of Notifications (read and unread)
     */
    long getNotificationCount();

    /**
     * Marks a notification as read
     *
     * @param notificationId Id of the notification to mark as read
     * @return {@code true} if notification was updated {@code false} otherwise
     */
    boolean markNotificationRead(int notificationId);

    /**
     * Deletes one notification by localId.
     *
     * @return the number of rows deleted
     */
    long deleteNotification(int localId);

    /**
     * Clears the notification table completely.
     */
    long deleteAllNotifications();

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Annotation Table
    ////////////////////////////////////////////////////////////////////////////////////////////////

    /**
     * Add a new {@link com.numenta.core.data.Annotation} to the database
     *
     * @return the row ID of the newly inserted row, or -1 if an error occurred
     */
    long addAnnotation(Annotation annotation);

    /**
     * Returns a {@link java.util.Collection} of all {@link com.numenta.core.data.Annotation} in
     * this database
     *
     * @return {@link java.util.Collection} containing the {@link com.numenta.core.data.Annotation}s
     */
    Collection<Annotation> getAllAnnotations();

    /**
     * Returns a single annotation given it's id
     *
     * @param id metric id
     * @return {@link com.numenta.core.data.Annotation} or <code>null</code> if not found
     */
    Annotation getAnnotation(String id);

    /**
     * Get annotations
     *
     * @param server Filter annotations by server
     * @param from   return records from this date
     * @param to     return records up to this date
     * @return {@link java.util.List} containing the {@link com.numenta.core.data.Annotation}s
     */
    List<Annotation> getAnnotations(String server, Date from, Date to);

    /**
     * Delete {@link com.numenta.core.data.Annotation} from the database given it's id
     *
     * @return the number of rows deleted
     */
    long deleteAnnotation(String id);

    /**
     * Delete all {@link com.numenta.core.data.Annotation}s from the database associated with the
     * given instance ID
     */
    long deleteAnnotationByInstanceId(String instanceId);
}
