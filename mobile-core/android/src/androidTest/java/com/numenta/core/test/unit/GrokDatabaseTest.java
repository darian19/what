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

package com.numenta.core.test.unit;

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;
import com.numenta.core.utils.Version;
import com.numenta.core.utils.mock.MockYOMPClient;
import com.numenta.core.utils.mock.MockYOMPClientFactory;

import org.json.JSONException;
import org.json.JSONObject;

import android.database.Cursor;
import android.database.DatabaseUtils;
import android.os.AsyncTask;
import android.test.ApplicationTestCase;
import android.test.UiThreadTest;
import android.test.suitebuilder.annotation.LargeTest;
import android.test.suitebuilder.annotation.SmallTest;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.TimeZone;

public class YOMPDatabaseTest extends ApplicationTestCase<YOMPApplication> {

    CoreDatabase _database;

    public YOMPDatabaseTest() {
        super(YOMPApplication.class);
    }

    @Override
    public void setUp() throws Exception {
        super.setUp();
        createApplication();
        YOMPApplication.clearApplicationData(YOMPApplication.getContext());
        YOMPApplication.getInstance().setYOMPClientFactory(new MockYOMPClientFactory(new MockYOMPClient(Version.UNKNOWN)));
        _database = YOMPApplication.getDatabase();
        _database.deleteAll();
    }

    @Override
    public void tearDown() throws Exception {
        YOMPApplication.clearApplicationData(YOMPApplication.getContext());
        _database.deleteAll();
        super.tearDown();
    }

    private Metric createMetric(String metricId, String name, String instanceId, String serverName,
            int lastRowId, JSONObject parameters) {
        return _database.getDataFactory()
                .createMetric(metricId, name, instanceId, serverName, lastRowId, parameters);
    }

    private MetricData createMetricData(String metricId, long timestamp, float metricValue,
            float anomalyScore, long rowid) {
        return _database.getDataFactory()
                .createMetricData(metricId, timestamp, metricValue, anomalyScore, rowid);
    }

    private MetricData createMetricData(Cursor cursor) {
        return _database.getDataFactory().createMetricData(cursor);
    }

    private Instance createInstance(String id, String name, String namespace, String location,
            String message, int status) {
        return _database.getDataFactory()
                .createInstance(id, name, namespace, location, message, status);
    }


    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#getReadableDatabase()}
     */
    @UiThreadTest
    public void testGetReadableDatabase() {
        AsyncTask.execute(new Runnable() {
            @Override
            public void run() {
                // Access database from background thread
                YOMPApplication.getDatabase().getReadableDatabase();
            }
        });
    }

    @UiThreadTest
    public void testGetReadableDatabaseUIThread() {
        new AsyncTask<Void, Void, Void>() {
            @Override
            protected Void doInBackground(Void... params) {
                return null;
            }

            @Override
            protected void onPostExecute(Void result) {
                try {
                    YOMPApplication.getDatabase().getReadableDatabase();
                } catch (IllegalStateException t) {
                    // Should fail to access database from UI thread
                    return;
                }
                fail("Should not access database on UI Thread");
            }
        }.execute();

    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#getWritableDatabase()}
     */
    @UiThreadTest
    public void testGetWritableDatabase() {
        AsyncTask.execute(new Runnable() {
            @Override
            public void run() {
                // Access database from background thread
                YOMPApplication.getDatabase().getWritableDatabase();
            }
        });
    }

    @UiThreadTest
    public void testGetWritableDatabaseUIThread() {
        new AsyncTask<Void, Void, Void>() {
            @Override
            protected Void doInBackground(Void... params) {
                return null;
            }

            @Override
            protected void onPostExecute(Void result) {
                try {
                    YOMPApplication.getDatabase().getWritableDatabase();
                } catch (IllegalStateException t) {
                    // Should fail to access database from UI thread
                    return;
                }
                fail("Should not access database on UI Thread");
            }
        }.execute();

    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#addMetricDataBatch(java.util.Collection)}
     */
    @SmallTest
    public void testAddMetricDataBatch() {
        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add 5 data points
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (long i = 0; i < 5; i++) {
            batch.add(createMetricData("foo", i, 0, 0, i));
        }
        _database.addMetricDataBatch(batch);
        Cursor data = _database.getMetricData("foo", null, null, null, 0, 0);
        assertEquals(5, data.getCount());
        data.close();
    }

    @SmallTest
    public void testAddMetricDataBatchUnknownMetric() {

        // Add 5 data points
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (long i = 0; i < 5; i++) {
            batch.add(createMetricData("foo", i, 0, 0, i));
        }
        _database.addMetricDataBatch(batch);
        // Should not add data for unknown metric
        assertEquals(0, _database.getMetricData("foo", null, null, null, 0, 0).getCount());
    }

    @SmallTest
    public void testAddMetricDataBatchDuplicateKey() {
        // Add 5 identical data points
        final String metricId = "1";
        _database.addMetric(createMetric(metricId, "bar", "foobar", "barfoo", 5, null));
        final long rowid = 1;
        final long timestamp = System.currentTimeMillis();
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (int i = 0; i < 5; i++) {
            batch.add(createMetricData(metricId, timestamp, 0, 0, rowid));
        }
        _database.addMetricDataBatch(batch);

        // Should ignore duplicate key (metric_id, rowid)
        assertEquals(1, _database.getMetricData(metricId, null, null, null, 0, 0).getCount());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#deleteMetric(java.lang.String)}.
     */
    @SmallTest
    public void testDeleteMetric() {
        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());
        // Delete metric
        _database.deleteMetric("foo");

        // Check if the metric is not found
        assertNull(_database.getMetric("foo"));
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getMetricData(java.lang.String,
     * java.lang.String[], java.util.Date, java.util.Date, float, int)}
     * .
     */
    public void testGetMetricData() {

        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add 5 data points
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (long i = 0; i < 5; i++) {
            batch.add(createMetricData("foo", i, i, 0.2f, i));
        }
        _database.addMetricDataBatch(batch);
        Cursor cursor = _database.getMetricData("foo", null, null, null, 0, 0);
        assertEquals(5, cursor.getCount());

        // Make sure the values match
        MetricData data;
        float actual = 0;
        while (cursor.moveToNext()) {
            data = createMetricData(cursor);
            actual += data.getAnomalyScore();
        }
        assertEquals(1.0, actual, 0.01);
        cursor.close();
    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#getLastTimestamp()}.
     */
    public void testGetLastTimestamp() {

        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());
        // Add 5 data points
        long expectedTimestamp = new Date().getTime();
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (int i = 0; i < 5; i++) {
            expectedTimestamp += 300000;
            batch.add(createMetricData("foo", expectedTimestamp, i, 0.2f, i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(5, _database.getMetricData("foo", null, null, null, 0, 0).getCount());

        assertEquals(expectedTimestamp, _database.getLastTimestamp());

    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#getAllInstances()}.
     */
    public void testGetAllInstances() {

        // Add 10 instances, 4 metrics per instance
        for (int i = 0; i < 10; i++) {
            for (int m = 0; m < 4; m++) {
                _database.addMetric(
                        createMetric(i + "_" + m, "metric_" + m, "I_" + i, "server_" + i, 0, null));
            }
        }

        assertEquals(10, _database.getAllInstances().size());
    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#getAllMetrics()}.
     */
    public void testGetAllMetrics() {

        // Add 10 instances, 4 metrics per instance
        for (int i = 0; i < 10; i++) {
            for (int m = 0; m < 4; m++) {
                _database.addMetric(
                        createMetric(i + "_" + m, "metric_" + m, "I_" + i, "server_" + i, 0, null));
            }
        }

        assertEquals(40, _database.getAllMetrics().size());
    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#deleteOldRecords()}.
     */
    public void testDeleteOldRecords() {

        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add 5 old data points
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        cal.add(Calendar.DAY_OF_MONTH, -(YOMPApplication.getNumberOfDaysToSync() + 1));
        long timestamp = cal.getTimeInMillis();
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (int i = 0; i < 5; i++) {
            timestamp += 300000;
            batch.add(createMetricData("foo", timestamp, 0, 0.0f, i));
        }

        // Add 5 new points
        timestamp = new Date().getTime();
        for (int i = 0; i < 5; i++) {
            timestamp += 300000;
            batch.add(createMetricData("foo", timestamp, 0, 0.2f, 5 + i));
        }

        _database.addMetricDataBatch(batch);

        _database.deleteOldRecords();

        // There should be only the 5 new records
        Cursor cursor = _database.getMetricData("foo", new String[]{
                "metric_id",
                "rowid",
                "anomaly_score"
        }, null, null, 0, 0);
        assertEquals(5, cursor.getCount());

        float actual = 0;
        while (cursor.moveToNext()) {
            actual += cursor.getFloat(2);
        }
        assertEquals(1, actual, 0.01);
        cursor.close();
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getMetric(java.lang.String)}.
     */
    public void testGetMetric() {

        Metric metric = createMetric("foo", "bar", "forbar", "barfoo", 0, null);
        _database.addMetric(metric);

        assertEquals(metric, _database.getMetric("foo"));
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getMetricsByInstanceId(java.lang.String)}
     * .
     */
    public void testGetMetricsByInstanceId() {

        // Add 10 instances, 4 metrics per instance
        for (int i = 0; i < 10; i++) {
            for (int m = 0; m < 4; m++) {
                _database.addMetric(
                        createMetric(i + "_" + m, "metric_" + m, "I_" + i, "server_" + i, 0, null));
            }
        }
        ArrayList<Metric> metrics = _database.getMetricsByInstanceId("I_0");
        assertEquals(4, metrics.size());
        for (Metric metric : metrics) {
            assertEquals("I_0", metric.getInstanceId());
            assertEquals("server_0", metric.getServerName());
        }
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#addMetric(com.numenta.core.data.Metric)}
     * .
     */
    @SmallTest
    public void testAddMetric() throws JSONException {
        Metric expected = createMetric("metric_1", "name_1", "instance_1", "server_1", 1,
                new JSONObject("{"
                        + "      \"datasource\": \"custom\","
                        + "      \"metricSpec\": {"
                        + "        \"unit\": \"Count\","
                        + "        \"metric\": \"metric_1\","
                        + "        \"resource\": \"name_1\","
                        + "        \"userInfo\": {"
                        + "          \"symbol\": \"SYMB\","
                        + "          \"metricTypeName\": \"name_1\""
                        + "        }"
                        + "      }"
                        + "    }"));
        _database.addMetric(expected);
        Metric actual = _database.getMetric("metric_1");
        assertEquals(expected, actual);
        assertEquals("Count", actual.getUnit());
        assertEquals("SYMB", actual.getUserInfo("symbol"));
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#updateMetric(com.numenta.core.data.Metric)}
     * .
     */
    @SmallTest
    public void testUpdateMetric() {
        Metric metric = createMetric("metric_1", "name_1", "instance_1", "server_1", 1, null);
        long date1 = System.currentTimeMillis();
        metric.setLastTimestamp(date1);
        _database.addMetric(metric);
        assertEquals(date1, _database.getMetric("metric_1").getLastTimestamp());
        long date2 = System.currentTimeMillis();
        metric.setLastTimestamp(date2);
        _database.updateMetric(metric);
        assertEquals(date2, _database.getMetric("metric_1").getLastTimestamp());

    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#markNotificationRead(int)}.
     */
    @SmallTest
    public void testMarkNotificationRead() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        int readId = _database.addNotification("1", "foo", date, "Test Notification 1");
        int unreadId = _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
        _database.markNotificationRead(readId);
        Notification notification = _database.getNotificationByLocalId(readId);
        assertTrue(notification.isRead());
        notification = _database.getNotificationByLocalId(unreadId);
        assertFalse(notification.isRead());
    }


    @SmallTest
    public void testAddNotification() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
    }

    @SmallTest
    public void testAddNotificationUnknownMetric() {
        long date = System.currentTimeMillis();

        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");

        // Should not add notification for unknown metric
        assertEquals(0, _database.getNotificationCount());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getAllNotifications()}
     */
    public void testGetAllNotifications() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        Collection<Notification> notificationList = _database.getAllNotifications();
        assertEquals(5, notificationList.size());
        for (int i = 0; i < notificationList.size(); i++) {
            assertEquals(String.valueOf(i+1),
                    ((Notification)notificationList.toArray()[i]).getNotificationId());
        }
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#deleteAllNotifications()}.
     */
    @SmallTest
    public void testDeleteAllNotifications() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
        _database.deleteAllNotifications();
        assertEquals(0, _database.getNotificationCount());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#deleteNotification(int)}.
     */
    @SmallTest
    public void testDeleteNotification() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        int notificationId = _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
        _database.deleteNotification(notificationId);
        assertEquals(4, _database.getNotificationCount());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getNotificationByLocalId(int)}.
     */
    @SmallTest
    public void testGetNotificationByRowid() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        int rowid = _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
        Notification notification = _database.getNotificationByLocalId(rowid);
        assertEquals("1", notification.getNotificationId());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getNotificationCount()}.
     */
    @SmallTest
    public void testGetNotificationCount() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
    }

    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getServerName(java.lang.String)}.
     */
    @SmallTest
    public void testGetServerName() {
        _database
                .addMetric(
                        createMetric("metric_1_1", "metric_1", "instance_1", "server_1", 0, null));
        _database
                .addMetric(
                        createMetric("metric_2_1", "metric_1", "instance_2", "server_2", 0, null));
        _database
                .addMetric(
                        createMetric("metric_3_1", "metric_1", "instance_3", "server_3", 0, null));
        _database.addMetric(createMetric("metric_4_1", "metric_1", "instance_4", "", 0, null));

        assertEquals("server_1", _database.getServerName("instance_1"));
        assertEquals("server_2", _database.getServerName("instance_2"));
        assertEquals("server_3", _database.getServerName("instance_3"));
        assertEquals("instance_4", _database.getServerName("instance_4"));
    }

    /**
     * Test method for {@link com.numenta.core.data.CoreDatabaseImpl#deleteAll()}.
     */
    @SmallTest
    public void testDeleteAll() {
        // Add one metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.deleteAll();
        assertEquals(0, _database.getAllMetrics().size());
    }


    /**
     * Test method for
     * {@link com.numenta.core.data.CoreDatabaseImpl#getUnreadNotificationCount()}
     */
    @SmallTest
    public void testGetUnreadNotificationCount() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        int id = _database.addNotification("5", "foo", date, "Test Notification 5");
        assertEquals(5, _database.getNotificationCount());
        assertEquals(5, _database.getUnreadNotificationCount());
        _database.markNotificationRead(id);
        assertEquals(4, _database.getUnreadNotificationCount());
    }




    @SmallTest
    public void testUniqueNotification() {
        _database.addMetric(createMetric("foo", "metricName", "server", "name", 5, null));
        assertEquals(1, _database.getAllMetrics().size());
        assertEquals(1, _database.getAllInstances().size());
        long date = System.currentTimeMillis();
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        assertEquals(4, _database.getNotificationCount());
    }

    @SmallTest
    public void testCascadeOnDelete() {
        _database.addMetric(createMetric("metricId", "metricName", "server", "name", 5, null));
        assertEquals(1, _database.getAllMetrics().size());
        assertEquals(1, _database.getAllInstances().size());
        // Add 5 data points
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (long i = 0; i < 5; i++) {
            batch.add(createMetricData("metricId", i, 0.5f, 0.5f, i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(5, _database.getMetricData("metricId", null, null, null, 0, 0).getCount());

        // Delete Metric
        _database.deleteMetric("metricId");

        // Metric data should be deleted
        assertEquals(0, _database.getMetricData("metricId", null, null, null, 0, 0).getCount());
    }

    public void testIsForeignKeyEnabled() {
        assertEquals(1, DatabaseUtils.longForQuery(_database.getWritableDatabase(),
                "pragma foreign_keys", null));
    }

    public void testDeleteNotificationWhenMetricIsDeleted() {
        _database.addMetric(createMetric("foo", "metricName", "server", "name", 5, null));
        assertEquals(1, _database.getAllInstances().size());
        assertEquals(1, _database.getAllMetrics().size());
        long date = System.currentTimeMillis();
        _database.addNotification("1", "foo", date, "Test Notification 1");
        assertEquals(1, _database.getNotificationCount());
        _database.deleteMetric("foo");
        assertEquals(0, _database.getAllMetrics().size());
        assertEquals(0, _database.getNotificationCount());
    }


    public void testAnnotation() {
        // Test Annotations
        Annotation first = _database.getDataFactory()
                .createAnnotation("annotationId1", 1, 1, "device", "user", "instanceId1", "message",
                        null);
        Annotation second = _database.getDataFactory()
                .createAnnotation("annotationId2", 2, 2, "device",
                        "user", "instanceId2", null, "data");
        Annotation third = _database.getDataFactory()
                .createAnnotation("annotationId3", 3, 3, "device",
                        "user", "instanceId3", "message", "data");

        // Test unable to add annotation with invalid/unknown instance
        assertTrue("Add annotation with invalid/unknown instance",
                _database.addAnnotation(first) == -1);

        // Add instances
        _database.addMetric(createMetric("metricId1", "metricName", "instanceId1",
                "serverName1", 1, null));
        _database.addMetric(createMetric("metricId2", "metricName", "instanceId2",
                "serverName2", 2, null));
        _database.addMetric(createMetric("metricId3", "metricName", "instanceId3",
                "serverName3", 3, null));
        assertEquals("Failed to add 3 instances",
                3, _database.getAllInstances().size());

        // Add Annotations
        assertTrue("Failed to add annotation",
                _database.addAnnotation(first) != -1);
        assertTrue("Failed to add annotation",
                _database.addAnnotation(second) != -1);
        assertTrue("Failed to add annotation",
                _database.addAnnotation(third) != -1);

        // Get all annotations. There should be 3 annotations
        assertEquals("Failed to get all annotations",
                3, _database.getAllAnnotations().size());

        // Get Annotation By ID
        Annotation actual = _database.getAnnotation(first.getId());
        assertEquals(first.getId(), actual.getId());

        // Get Annotations By Server
        Collection<Annotation> col = _database.getAnnotations(first.getInstanceId(), null, null);
        assertTrue("Failed to get annotation by instance", !col.isEmpty());
        actual = col.iterator().next();
        assertEquals(first.getId(), actual.getId());

        // Get Annotations By Date
        col = _database.getAnnotations(null, new Date(1), new Date(1));
        assertTrue("Failed to get annotation by date", !col.isEmpty());
        actual = col.iterator().next();
        assertEquals(first.getId(), actual.getId());

        // Delete annotation by id.
        assertEquals("Failed to delete annotation by id", 1,
                _database.deleteAnnotation(first.getId()));
        col = _database.getAllAnnotations();
        // There should be 2 annotations left
        assertEquals("Failed to delete annotation by id", 2, col.size());

        // Delete annotation by instance id
        assertEquals("Failed to delete annotation by instance id", 1,
                _database.deleteAnnotationByInstanceId(second.getInstanceId()));
        col = _database.getAllAnnotations();
        // There should be 1 annotation left
        assertEquals("Failed to delete annotation by instance id", 1, col.size());

        // Check if annotation goes away with the instance
        _database.deleteInstance(third.getInstanceId());
        assertNull(_database.getAnnotation(third.getId()));
    }
}
