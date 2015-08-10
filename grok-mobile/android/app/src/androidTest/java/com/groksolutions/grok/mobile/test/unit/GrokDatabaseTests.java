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
package com.YOMPsolutions.YOMP.mobile.test.unit;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;
import com.numenta.core.utils.Version;
import com.numenta.core.utils.mock.MockYOMPClient;
import com.numenta.core.utils.mock.MockYOMPClientFactory;

import org.json.JSONObject;

import android.database.Cursor;
import android.test.ApplicationTestCase;
import android.test.suitebuilder.annotation.LargeTest;
import android.test.suitebuilder.annotation.SmallTest;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class YOMPDatabaseTests extends ApplicationTestCase<YOMPApplication> {

    YOMPDatabase _database;

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

    private Instance createInstance(String id, String name, String namespace, String location,
            String message, int status) {
        return _database.getDataFactory()
                .createInstance(id, name, namespace, location, message, status);
    }

    private void populateDatabase(int instances, int metrics, int totalRows, float value,
            float anomaly) {
        ArrayList<MetricData> batch = new ArrayList<MetricData>();

        long timestamp = System.currentTimeMillis() - totalRows * 5 * DataUtils.MILLIS_PER_MINUTE;
        String metricId;

        // Instances
        for (int i = 0; i < instances; i++) {
            // Metrics
            for (int m = 0; m < metrics; m++) {
                metricId = "metric_id_" + i + "_" + m;
                _database.addMetric(createMetric(metricId, "metric_" + m, "instance_" + i, "server_"
                                + i,
                        com.numenta.core.app.YOMPApplication.getLearningThreshold() + totalRows,
                        null));
                // Data
                for (int row = 0; row < totalRows; row++) {
                    batch.add(createMetricData(metricId, timestamp + row * 5
                                    * DataUtils.MILLIS_PER_MINUTE, value, anomaly,
                            com.numenta.core.app.YOMPApplication.getLearningThreshold() + row + 1));
                }
            }
        }
        _database.addMetricDataBatch(batch);
    }


    public YOMPDatabaseTests() {
        super(YOMPApplication.class);
    }

    @Override
    public void setUp() throws Exception {
        super.setUp();
        createApplication();
        YOMPApplication.clearApplicationData(YOMPApplication.getContext());
        YOMPApplication.getInstance().setYOMPClientFactory(
                new MockYOMPClientFactory(new MockYOMPClient(Version.UNKNOWN)));
        _database = YOMPApplication.getDatabase();
        _database.deleteAll();
    }

    @Override
    public void tearDown() throws Exception {
        YOMPApplication.clearApplicationData(YOMPApplication.getContext());
        _database.deleteAll();
        super.tearDown();
    }

    public void testGetAggregatedScoreNoData() {
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metric_id_0_0",
                AggregationType.Hour, 0, 24);
        assertTrue(results.isEmpty());
    }

    @LargeTest
    public void testGetAggregatedScoreByMetricIdHour() {
        populateDatabase(1, 1, 24, 0.5f, 0.5f);
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metric_id_0_0",
                AggregationType.Hour, 0, 24);

        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }
    }

    @SmallTest
    public void testGetNotificationCursor() {
        long date = System.currentTimeMillis();

        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        _database.addNotification("1", "foo", date, "Test Notification 1");
        _database.addNotification("2", "foo", date, "Test Notification 2");
        _database.addNotification("3", "foo", date, "Test Notification 3");
        _database.addNotification("4", "foo", date, "Test Notification 4");
        _database.addNotification("5", "foo", date, "Test Notification 5");
        Cursor cursor = _database.getNotificationCursor();
        assertEquals(5, cursor.getCount());
        cursor.close();
    }

    @LargeTest
    public void testGetAggregatedScoreByMetricIdDay() {
        populateDatabase(1, 1, 12 * 24, 0.5f, 0.5f);
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metric_id_0_0",
                AggregationType.Day, 0, 24);

        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(0.5f, pair.second, 0.01);
        }
    }

    @SmallTest
    public void testGetMetricLastTimestamp() {

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

        assertEquals(expectedTimestamp, _database.getMetricLastTimestamp("foo"));

    }

    @LargeTest
    public void testGetAggregatedScoreByMetricIdWeek() {
        populateDatabase(1, 1, 8 * 12 * 24, 0.5f, 0.5f);
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metric_id_0_0",
                AggregationType.Week, 0, 24);

        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }
    }

    @LargeTest
    public void testGetAggregatedScoreByInstanceIdHour() {
        populateDatabase(1, 1, 24, 0.5f, 0.5f);
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instance_0",
                AggregationType.Hour, 0, 24);

        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }
    }

    @LargeTest
    public void testGetAggregatedScoreByInstanceIdDay() {
        populateDatabase(1, 1, 12 * 24, 0.5f, 0.5f);

        // Get results from database
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instance_0",
                AggregationType.Day, 0, 24);
        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }

        // Get results from cache
        results = _database.getAggregatedScoreByInstanceId("instance_0",
                AggregationType.Day, 0, 24);
        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }
    }

    @LargeTest
    public void testGetAggregatedScoreByInstanceIdWeek() {
        populateDatabase(1, 1, 8 * 12 * 24, 0.5f, 0.5f);
        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instance_0",
                AggregationType.Week, 0, 24);

        assertEquals(24, results.size());
        for (Pair<Long, Float> pair : results) {
            assertEquals(pair.second, 0.5f, 0.01);
        }
    }

    @SmallTest
    public void testGetMetricValue() {
        // Add metric
        _database.addMetric(createMetric("foo", "bar", "forbar", "barfoo", 0, null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add 5 data points
        ArrayList<MetricData> batch = new ArrayList<MetricData>(5);
        for (long i = 0; i < 5; i++) {
            batch.add(createMetricData("foo", i, i * 10, i, i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(5, _database.getMetricData("foo", null, null, null, 0, 0).getCount());

        assertEquals(0.0, _database.getMetricValue("foo", 0), 0.01);
        assertEquals(30.0, _database.getMetricValue("foo", 3), 0.01);
        assertEquals(Float.NaN, _database.getMetricValue("foo", 10));
    }

    @SmallTest
    public void testAddInstance() {
        _database
                .addInstance(
                        createInstance("server", "name", "namespace", "location", "message", 1));
        assertEquals(1, _database.getAllInstances().size());
    }

    public void testMetricProbationPeriodHour() {
        // Add Metric
        _database.addMetric(createMetric("metricId", "metricName", "server", "name", 1012, null));
        assertEquals(1, _database.getAllInstances().size());
        assertEquals(1, _database.getAllMetrics().size());

        // Add 24 data points. 12 points in probation, 12 points after probation
        ArrayList<MetricData> batch = new ArrayList<MetricData>(24);
        for (long i = 0; i < 24; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f, 988 + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(24, _database.getMetricData("metricId", null, null, null, 0, 0).getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metricId",
                AggregationType.Hour, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.5f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

    public void testMetricProbationPeriodDay() {
        int totalRecords = 12 * 24;
        // Set half of the points to be in probation
        int probationRecords = totalRecords / 2;

        // Add server
        _database
                .addInstance(
                        createInstance("server", "name", "namespace", "location", "message", 1));
        assertEquals(1, _database.getAllInstances().size());

        // Add Metric
        _database.addMetric(createMetric("metricId", "metricName", "server", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add data points.
        // Probation scores are 0.9, normal scores are 0.5
        ArrayList<MetricData> batch = new ArrayList<MetricData>(totalRecords);
        for (long i = 0; i < probationRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.9f,
                    0.9f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        for (long i = probationRecords; i < totalRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(totalRecords, _database.getMetricData("metricId", null, null, null, 0, 0)
                .getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metricId",
                AggregationType.Day, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.9f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

    public void testMetricProbationPeriodWeek() {
        int totalRecords = 8 * 12 * 24;
        // Set half of the points to be in probation
        int probationRecords = totalRecords / 2;

        // Add server
        _database
                .addInstance(
                        createInstance("server", "name", "namespace", "location", "message", 1));
        assertEquals(1, _database.getAllInstances().size());

        // Add Metric
        _database.addMetric(createMetric("metricId", "metricName", "server", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        assertEquals(1, _database.getAllMetrics().size());

        // Add data points.
        // Probation scores are 0.9, normal scores are 0.5
        ArrayList<MetricData> batch = new ArrayList<MetricData>(totalRecords);
        for (long i = 0; i < probationRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.9f,
                    0.9f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        for (long i = probationRecords; i < totalRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(totalRecords, _database.getMetricData("metricId", null, null, null, 0, 0)
                .getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByMetricId("metricId",
                AggregationType.Week, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.9f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

    public void testInstanceProbationPeriodHour() {
        // Add server
        _database.addInstance(
                createInstance("instanceId", "name", "namespace", "location", "message",
                        1));
        assertEquals(1, _database.getAllInstances().size());

        // Add Metrics
        _database.addMetric(
                createMetric("metricId", "metricName", "instanceId", "name", 1012, null));
        _database
                .addMetric(
                        createMetric("metricId2", "metricName", "instanceId", "name", 1012, null));
        assertEquals(2, _database.getAllMetrics().size());

        // Add 24 data points. 12 points in probation, 12 points after probation
        ArrayList<MetricData> batch = new ArrayList<MetricData>(24);
        for (long i = 0; i < 24; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f, 988 + i));
            // Add metric with lower value
            batch.add(createMetricData("metricId2", i * AggregationType.Hour.milliseconds(), 0.3f,
                    0.3f, 988 + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(24, _database.getMetricData("metricId", null, null, null, 0, 0).getCount());
        assertEquals(24, _database.getMetricData("metricId2", null, null, null, 0, 0).getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instanceId",
                AggregationType.Hour, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.5f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

    public void testInstanceProbationPeriodDay() {
        int totalRecords = 12 * 24;
        // Set half of the points to be in probation
        int probationRecords = totalRecords / 2;

        // Add server
        _database.addInstance(
                createInstance("instanceId", "name", "namespace", "location", "message",
                        1));
        assertEquals(1, _database.getAllInstances().size());

        // Add Metric
        _database.addMetric(createMetric("metricId", "metricName", "instanceId", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        _database.addMetric(createMetric("metricId2", "metricName", "instanceId", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        assertEquals(2, _database.getAllMetrics().size());

        // Add data points.
        // Probation scores are 0.9, normal scores are 0.5
        ArrayList<MetricData> batch = new ArrayList<MetricData>(totalRecords);
        for (long i = 0; i < probationRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.9f,
                    0.9f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
            batch.add(createMetricData("metricId2", i * AggregationType.Hour.milliseconds(), 0.8f,
                    0.8f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        for (long i = probationRecords; i < totalRecords; i++) {
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
            batch.add(createMetricData("metricId2", i * AggregationType.Hour.milliseconds(), 0.4f,
                    0.4f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(totalRecords, _database.getMetricData("metricId", null, null, null, 0, 0)
                .getCount());
        assertEquals(totalRecords, _database.getMetricData("metricId2", null, null, null, 0, 0)
                .getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instanceId",
                AggregationType.Day, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.9f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

    public void testInstanceProbationPeriodWeek() {
        int totalRecords = 8 * 12 * 24;
        // Set half of the points to be in probation
        int probationRecords = totalRecords / 2;

        // Add server
        _database.addInstance(
                createInstance("instanceId", "name", "namespace", "location", "message",
                        1));
        assertEquals(1, _database.getAllInstances().size());

        // Add Metric
        _database.addMetric(createMetric("metricId", "metricName", "instanceId", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        _database.addMetric(createMetric("metricId2", "metricName", "instanceId", "name",
                com.numenta.core.app.YOMPApplication.getLearningThreshold() + probationRecords,
                null));
        assertEquals(2, _database.getAllMetrics().size());

        // Add data points.
        // Probation scores are 0.9, normal scores are 0.5
        ArrayList<MetricData> batch = new ArrayList<MetricData>(totalRecords);
        for (long i = 0; i < probationRecords; i++) {
            batch.add(createMetricData("metricId2", i * AggregationType.Hour.milliseconds(), 0.8f,
                    0.8f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.9f,
                    0.9f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        for (long i = probationRecords; i < totalRecords; i++) {
            batch.add(createMetricData("metricId2", i * AggregationType.Hour.milliseconds(), 0.3f,
                    0.4f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
            batch.add(createMetricData("metricId", i * AggregationType.Hour.milliseconds(), 0.5f,
                    0.5f,
                    com.numenta.core.app.YOMPApplication.getLearningThreshold() - probationRecords
                            + i));
        }
        _database.addMetricDataBatch(batch);
        assertEquals(totalRecords, _database.getMetricData("metricId", null, null, null, 0, 0)
                .getCount());
        assertEquals(totalRecords, _database.getMetricData("metricId2", null, null, null, 0, 0)
                .getCount());

        List<Pair<Long, Float>> results = _database.getAggregatedScoreByInstanceId("instanceId",
                AggregationType.Week, 0, 24);

        assertEquals(24, results.size());

        // Get probation scores
        for (int i = 0; i < 12; i++) {
            assertEquals(results.get(i).second, -0.9f, 0.01);
        }
        // Get good scores
        for (int i = 12; i < 24; i++) {
            assertEquals(results.get(i).second, 0.5f, 0.01);
        }
    }

}
