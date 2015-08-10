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

package com.numenta.core.utils.mock;

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPUnauthorizedException;
import com.numenta.core.utils.Version;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SortedSet;
import java.util.UUID;
import java.util.concurrent.ConcurrentSkipListSet;

/**
 * Configurable mock {@link YOMPClient} to be used in unit tests.
 * <p>
 * Sample usage:
 *
 * <pre>
 * <code>
 *     MockYOMPClient YOMPClient = new MockYOMPClient();
 *     Random rnd = new Random();
 *
 *     // Set start date for data
 *     Calendar cal = Calendar.getInstance();
 *     cal.setTimeZone(TimeZone.getTimeZone("UTC"));
 *     cal.set(2014, Calendar.JANUARY, 1, 0, 0, 0);
 *
 *     String metricId, instanceId, serverName, metricName;
 *
 *     // Create 10 mock instances with 4 mock metrics each, 1000 rows each metric
 *     for (int i = 0; i < 10; i++) {
 *
 *         // New Instance
 *         instanceId = "i-" + i;
 *         serverName = "server_" + i;
 *         for (int m = 0; m < 4; m++) {
 *
 *             // New Metric
 *             metricId = "m-" + i + "_" + m;
 *             metricName = "metric_" + m;
 *             YOMPClient.addMetric(new Metric(metricId, metricName, instanceId, serverName, 1000));
 *
 *             // Add Data
 *             for (int rowid = 1; rowid <= 1000; rowid++) {
 *                  YOMPClient.addMetricData(new MetricData(metricId, cal.getTime(), rnd.nextFloat(), rnd.nextFloat(), rowid));
 *             }
 *         }
 *     }
 *     // Override default factory
 *     YOMPApplication.setYOMPClientFactory(new MockYOMPClientFactory(YOMPClient));
 *
 * </code>
 * </pre>
 */
public class MockYOMPClient implements YOMPClient {
    protected final ArrayList<Metric> _metrics = new ArrayList<Metric>();
    protected Version _version;

    // Keep metric data sorted by timestamp within the same metric id
    protected SortedSet<MetricData> _metricData = new ConcurrentSkipListSet<MetricData>(
            new Comparator<MetricData>() {
                @Override
                public int compare(MetricData lhs, MetricData rhs) {
                    if (lhs == rhs)
                        return 0;
                    if (lhs == null)
                        return 1;
                    if (rhs == null)
                        return -1;
                    int res = lhs.getMetricId().compareTo(rhs.getMetricId());
                    if (res == 0) {
                        // sort by timestamp within the same metric id
                        res = (int) (lhs.getTimestamp() - rhs.getTimestamp());
                    }
                    return res;
                }
            });

    final Map<String, Notification> _notifications = new HashMap<String, Notification>();
    final Map<String, Annotation> _annotations = new HashMap<String, Annotation>();


    public MockYOMPClient(Version version) {

        this._version = version;
    }

    @Override
    public boolean isOnline() {
        return true;
    }

    @Override
    public void login() throws IOException, YOMPException {
        // Ignore
    }

    @Override
    public List<Metric> getMetrics() throws YOMPException, IOException {
        return Collections.unmodifiableList(_metrics);
    }

    @Override
    public String getServerUrl() {
        return "https://localhost";
    }

    /**
     * Add a new {@link MetricData} row to this Mock object.  <p>
     * You should make sure to add the appropriate {@link Metric} using
     * {@link #addMetric(Metric)}.
     */
    public void addMetricData(MetricData data) {
        _metricData.add(data);
    }

    /**
     * Add a new {@link Metric} to this Mock object. This value will be returned
     * by {@link #getMetrics()} as-is.
     * <p>
     * The order the data is inserted is the order returned by those methods.
     */
    public void addMetric(Metric metric) {
        _metrics.add(metric);
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.service.YOMPClient#getServerVersion()
     */
    @Override
    public Version getServerVersion() {
        return _version;
    }

    /**
     * Add a new {@link Notification} to this Mock object. This value will be
     * returned by {@link #getNotifications()} as-is.
     * <p>
     * The order the data is inserted is the order returned by those methods.
     *
     * @param notification
     */
    public void addNotification(Notification notification) {
        _notifications.put(notification.getNotificationId(), notification);
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.service.YOMPClient#getNotifications()
     */
    @Override
    public List<Notification> getNotifications() throws YOMPException, IOException {
        return new ArrayList<Notification>(_notifications.values());
    }

    /**
     * Add a new {@link com.numenta.core.data.Annotation} to this Mock Object. This
     * value will be returned by {@link #getAnnotations}
     * @param annotation
     */
    public  void addAnnotation(Annotation annotation) {
        _annotations.put(annotation.getId(), annotation);
    }

    @Override
    public List<Annotation> getAnnotations(Date from, Date to) throws YOMPException, IOException {
        return new ArrayList<Annotation>(_annotations.values());
    }

    @Override
    public void deleteAnnotation(Annotation annotation) throws YOMPUnauthorizedException, YOMPException, IOException {
        // Verify device ID before deleting
        if (annotation.getDevice().equals(YOMPApplication.getDeviceId())) {
            throw  new YOMPUnauthorizedException("Cannot delete annotations created on a different device");
        }
        _annotations.remove(annotation.getId());
    }

    @Override
    public Annotation addAnnotation(Date timestamp, String server, String message, String user) throws YOMPException, IOException {
        CoreDataFactory factory = YOMPApplication.getDatabase()
                .getDataFactory();
        return factory.createAnnotation(UUID.randomUUID().toString(), timestamp.getTime(),
                new Date().getTime(), YOMPApplication.getDeviceId(), user, server, message, null);
    }

    /*
     * (non-Javadoc)
     * @see
     * com.numenta.core.service.YOMPClient#deleteNotifications(
     * java.lang.String[])
     */
    @Override
    public void acknowledgeNotifications(String[] ids) throws YOMPException, IOException {
        for (String id : ids) {
            _notifications.remove(id);
        }
    }

    /*
     * (non-Javadoc)
     * @see
     * com.numenta.core.service.YOMPClient#getMetricData(java
     * .lang.String, java.util.Date, java.util.Date,
     * com.numenta.core.service.MetricDataParserCallback)
     */
    @Override
    public void getMetricData(String metricId, Date from, Date to,
            DataCallback<MetricData> callback) throws YOMPException, IOException {
        long now = to.getTime();
        long timestamp;
        for (MetricData data : _metricData) {
            timestamp = data.getTimestamp();
            if ((from == null || timestamp >= from.getTime()) &&
                    timestamp <= now &&
                    (metricId == null || metricId.equals(data.getMetricId()))) {
                callback.onData(data);
            }
        }
    }

    @Override
    public String getServerName() {
        return "Mock";
    }

}
