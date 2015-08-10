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

import com.numenta.core.data.Annotation;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.Version;

import java.io.IOException;
import java.util.Date;
import java.util.List;

/**
 * <code>YOMPClient</code> interface wraps a connection to the YOMP REST API
 */
public interface YOMPClient {

    /**
     * Used by the client to notify the caller the when a new data object is ready
     */
    interface DataCallback<T> {

        /**
         * Called on every new data value
         *
         * @param data The parsed data object
         * @return false to stop loading
         */
        boolean onData(T data);
    }

    /**
     * Check whether the server is online
     *
     * @return {@code true} if we are able to connect to the server
     */
    boolean isOnline();

    /**
     * Login to YOMP server
     */
    void login() throws IOException, YOMPException;

    /**
     * returns the serverUrl
     */
    String getServerUrl();

    /**
     * The server name identifying the server, usually returned via the HTTP header "Server"
     */
    String getServerName();

    /**
     * Returns the server version in the following format: <code>"1.1"</code>
     */
    Version getServerVersion();

    /**
     * Returns a list of metrics from the server
     *
     * @return List of {@link Metric}
     */
    List<Metric> getMetrics() throws YOMPException, IOException;

    /**
     * Returns metric data asynchronously for the given model starting from the given range
     *
     * @param modelId  The model to get the data from
     * @param from     The starting timestamp
     * @param to       The ending timestamp
     * @param callback User defined callback to receive metric data
     */
    void getMetricData(String modelId, Date from, Date to,
            DataCallback<MetricData> callback)
            throws YOMPException, IOException;

    /**
     * Returns all notifications available for this device. Only unacknowledged notifications will
     * be returned by this call.
     */
    List<Notification> getNotifications() throws YOMPException, IOException;

    /**
     * Acknowledge notifications on the server. The server may decide to keep or delete
     * acknowledged
     * notifications, however acknowledged notifications will not be returned by
     * {@link #getNotifications()}
     *
     * @param ids Array of notification IDs to be acknowledged
     */
    void acknowledgeNotifications(String[] ids) throws YOMPException, IOException;

    /**
     * Returns all annotations for the given time range
     *
     * @param from Starting time (inclusive)
     * @param to   Ending time (inclusive)
     * @return {@link java.util.List} of {@link com.numenta.core.data.Annotation}
     * matching the criteria. Returns empty list if no annotation is found matching the criteria
     */
    List<Annotation> getAnnotations(Date from, Date to)
            throws YOMPException, IOException;

    /**
     * Delete annotation from the server.
     * Users are only allowed to delete annotations created on this device.
     * If the user is not allowed to delete the annotation a
     * {@link com.numenta.core.service.YOMPUnauthorizedException} is thrown.
     *
     * @param annotation annotation to delete
     */
    void deleteAnnotation(Annotation annotation)
            throws YOMPUnauthorizedException, YOMPException, IOException;

    /**
     * Add new annotation associating it to the given server and the given timestamp.
     * The current device will also be associated with the annotation.
     *
     * @param timestamp The date and time to be annotated
     * @param server    Instance Id associated with this annotation
     * @param message   Annotation message
     * @param user      User name
     * @return The newly created {@link com.numenta.core.data.Annotation}
     */
    Annotation addAnnotation(Date timestamp, String server, String message,
            String user) throws YOMPException, IOException;
}
