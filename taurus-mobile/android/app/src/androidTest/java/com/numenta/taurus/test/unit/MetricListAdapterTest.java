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

package com.numenta.taurus.test.unit;

import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.Metric;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.metric.MetricAnomalyChartData;
import com.numenta.taurus.metric.MetricListAdapter;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import android.app.Instrumentation;
import android.support.test.InstrumentationRegistry;
import android.support.test.annotation.UiThreadTest;
import android.support.test.rule.UiThreadTestRule;
import android.support.test.runner.AndroidJUnit4;
import android.test.ApplicationTestCase;

import java.util.concurrent.Executors;

/**
 * MetricListAdapter contains MetricAnomalyChartData elements
 * MetricAnomalyChartData has a Metric
 * Metric has a Json specifying Metric type name
 * MetricAnomalyChartData are sorted by MetricType name.
 */
@RunWith(AndroidJUnit4.class)
public class MetricListAdapterTest extends ApplicationTestCase<TaurusApplication> {

    private MetricListAdapter adapter;
    private MetricAnomalyChartData data0;
    private MetricAnomalyChartData data1;
    private MetricAnomalyChartData data2;
    private MetricAnomalyChartData data3;
    private MetricAnomalyChartData dataNullJson1;
    private MetricAnomalyChartData dataNullJson2;

    public MetricListAdapterTest() {
        super(TaurusApplication.class);
    }

    @Rule public final UiThreadTestRule uiThread = new UiThreadTestRule();

    @Before
    public void setUp() throws Exception {
        super.setUp();
        setContext(InstrumentationRegistry.getTargetContext());
        createApplication();
        TaurusApplication.setStaticInstanceForUnitTestsOnly(getApplication());
        CoreDataFactory factory = TaurusApplication.getDatabase().getDataFactory();

        adapter = new MetricListAdapter(getContext());
        JSONObject obj0 = new JSONObject("{"
                + "\"datasource\": \"custom\","
                + "\"metricSpec\": {"
                + "    \"metric\": \"INTERACTIVEDATA.KND.VOLUME\","
                + "    \"resource\": \"Kindred Healthcare\","
                + "    \"userInfo\": {"
                + "        \"symbol\": \"KND\","
                + "        \"metricTypeName\": \"Stock Price\""
                + "      }"
                + "    }"
                + "}");
        JSONObject obj1 = new JSONObject("{"
                + "\"datasource\": \"custom\","
                + "\"metricSpec\": {"
                + "    \"metric\": \"INTERACTIVEDATA.KND.VOLUME\","
                + "    \"resource\": \"Kindred Healthcare\","
                + "    \"userInfo\": {"
                + "        \"symbol\": \"KND\","
                + "        \"metricTypeName\": \"Twitter Volume\""
                + "      }"
                + "    }"
                + "}");
        JSONObject obj2 = new JSONObject("{"
                + "      \"datasource\": \"custom\","
                + "      \"metricSpec\": {"
                + "        \"unit\": \"Count\","
                + "        \"metric\": \"metric_1\","
                + "        \"resource\": \"name_1\","
                + "        \"userInfo\": {"
                + "          \"symbol\": \"SYMB\","
                + "          \"metricTypeName\": \"Stock Volume\""
                + "        }"
                + "      }"
                + "    }");
        JSONObject obj3 = new JSONObject("{"
                + "\"datasource\": \"custom\","
                + "\"metricSpec\": {"
                + "    \"metric\": \"INTERACTIVEDATA.KND.VOLUME\","
                + "    \"resource\": \"Kindred Healthcare\","
                + "    \"userInfo\": {"
                + "        \"symbol\": \"KND\","
                + "        \"metricTypeName\": \"Twitter Volume\""
                + "      }"
                + "    }"
                + "}");
        Metric metric0 = factory.createMetric("123", "bob", "456", "a", 1, obj0);
        Metric metric1 = factory.createMetric("123", "bob", "456", "a", 1, obj1);
        Metric metric2 = factory.createMetric("123", "bob", "456", "a", 1, obj2);
        Metric metric3 = factory.createMetric("123", "bob", "456", "a", 1, obj3);
        Metric metricNullJson1 = factory.createMetric("123", "bob", "456", "a", 1, null);
        Metric metricNullJson2 = factory.createMetric("123", "bob", "456", "a", 1, null);
        data0 = new MetricAnomalyChartData(metric0, 1L);
        data1 = new MetricAnomalyChartData(metric1, 2L);
        data2 = new MetricAnomalyChartData(metric2, 3L);
        data3 = new MetricAnomalyChartData(metric3, 4L);
        dataNullJson1 = new MetricAnomalyChartData(metricNullJson1, 5L);
        dataNullJson2 = new MetricAnomalyChartData(metricNullJson2, 5L);
    }

    @Test
    public void testAddNull() throws Exception {
        //noinspection EmptyCatchBlock
        try {
            adapter.add(null);
        }catch(Exception e){
        }
        assertEquals(0, adapter.getCount());
    }

    @Test @UiThreadTest
    public void testSortNullMetric() throws Exception {
        MetricAnomalyChartData dataNull1 = new MetricAnomalyChartData(null, 10L);
        MetricAnomalyChartData dataNull2 = new MetricAnomalyChartData(null, 20L);

        //empty list
        auxTestSort();

        //add data with null metric
        adapter.add(dataNull1);
        assertEquals(1, adapter.getCount());
        auxTestSort();

        adapter.add(dataNull2);
        assertEquals(2, adapter.getCount());
        auxTestSort();

        adapter.add(data0);
        assertEquals(3, adapter.getCount());
        auxTestSort();

        //check positions
        assertEquals(data0, adapter.getItem(0));
        assertEquals(dataNull1, adapter.getItem(1));
        assertEquals(dataNull2, adapter.getItem(2));
    }

    @Test @UiThreadTest
    public void testSortDiffMetrics() throws Exception {
        //add data with non-null metrics
        adapter.add(data1);
        adapter.add(data2);
        adapter.add(data0);
        auxTestSort();

        // Check if the MetricAnomalyChartDatas were sorted by 'metricTypeName'
        assertEquals(3, adapter.getCount());
        assertEquals(data0, adapter.getItem(0));
        assertEquals(data2, adapter.getItem(1));
        assertEquals(data1, adapter.getItem(2));
    }

    @Test @UiThreadTest
    public void testSortDiffMetrics2() throws Exception {
        //add data1 and data3 with type 'twitter volume'
        adapter.add(data3);
        adapter.add(data1);
        adapter.add(data2);
        adapter.add(data0);
        auxTestSort();

        // Check if the MetricAnomalyChartDatas were sorted by 'metricTypeName'
        assertEquals(4, adapter.getCount());
        assertEquals(data0, adapter.getItem(0));
        assertEquals(data2, adapter.getItem(1));
        assertEquals(data3, adapter.getItem(2));
        assertEquals(data1, adapter.getItem(3));
    }

    @Test @UiThreadTest
    public void testSortMetricNullJson() throws Exception {
        //add data with a null Json for the metric type
        adapter.add(dataNullJson2);
        adapter.add(data3);
        adapter.add(data1);
        adapter.add(data2);
        adapter.add(dataNullJson1);
        adapter.add(data0);

        auxTestSort();

        // Check sorted order
        assertEquals(6, adapter.getCount());
        assertEquals(data0, adapter.getItem(0));
        assertEquals(data2, adapter.getItem(1));
        assertEquals(data3, adapter.getItem(2));
        assertEquals(data1, adapter.getItem(3));
        assertEquals(dataNullJson2, adapter.getItem(4));
        assertEquals(dataNullJson1, adapter.getItem(5));
    }

    private void auxTestSort(){
        try {
            adapter.sort();
            assertTrue(true);
        }catch(Exception e){
            assertTrue(false);
        }
    }
}
