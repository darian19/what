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

import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.YOMPsolutions.YOMP.mobile.service.MetricParser;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.Metric;
import com.numenta.core.utils.YOMPAndroidTestCase;

import org.json.JSONObject;

import android.test.suitebuilder.annotation.SmallTest;
import android.util.JsonReader;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.List;

public class MetricParserTests extends YOMPAndroidTestCase {

    Metric _expectedStandardMetric;
    Metric _expectedCustomMetric;
    Metric _expectedUserInfoMetric;

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        CoreDataFactory factory = YOMPApplication.getDatabase()
                .getDataFactory();
        _expectedStandardMetric = factory.createMetric("3654d3972c1742a0bef5e0022f210544",
                "AWS/EC2/CPUUtilization", "us-east-1/AWS/EC2/i-d9e211f6",
                "testN.domain.tld - 2014-03-20", 4289, null);
        _expectedCustomMetric = factory.createMetric("f32565f1b6454eb9a26df2ba994e83a9",
                "stocks.defaultID.AAPL.VOLUME", "stocks.defaultID.AAPL.VOLUME",
                "stocks.defaultID.AAPL.VOLUME", 359, new JSONObject("{"
                + "\"datasource\": \"custom\","
                + "\"metricSpec\": {"
                + "     \"metric\": \"stocks.defaultID.AAPL.VOLUME\","
                + "     \"unit\": \"Count\""
                + "  }"
                + "}"));
        _expectedUserInfoMetric = factory.createMetric("f5fc7d3cd38146ed964bcc67f198432b",
                "INTERACTIVEDATA.KND.VOLUME", "Kindred Healthcare",
                "Kindred Healthcare", 639, new JSONObject("{"
                + "\"datasource\": \"custom\","
                + "\"metricSpec\": {"
                + "    \"metric\": \"INTERACTIVEDATA.KND.VOLUME\","
                + "    \"resource\": \"Kindred Healthcare\","
                + "    \"userInfo\": {"
                + "        \"symbol\": \"KND\","
                + "        \"metricTypeName\": \"Stock Volume (InteractiveData)\""
                + "      }"
                + "    }"
                + "}"));
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    @SuppressWarnings("unchecked")
    @SmallTest
    public void testParseSingleMetric_1_3() {
        JsonReader reader = null;
        try {
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_3, "single_model.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            MetricParser parser = new MetricParser(reader);
            List<Metric> metrics = parser.parse();
            assertEquals(metrics.size(), 1);
            Metric metric = metrics.get(0);
            assertEquals(_expectedStandardMetric, metric);
        } catch (IOException e) {
            fail(e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    @SmallTest
    public void testParseSingleCustomMetric_1_6() {
        JsonReader reader = null;
        try {
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_6, "single_custom_model.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            MetricParser parser = new MetricParser(reader);
            List<Metric> metrics = parser.parse();
            assertEquals(metrics.size(), 1);
            Metric metric = metrics.get(0);
            assertEquals(_expectedCustomMetric, metric);
            assertEquals("Count", metric.getUnit());
        } catch (IOException e) {
            fail(e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    @SmallTest
    public void testParseMultiMetric_1_3() {
        JsonReader reader = null;
        try {
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_3, "multi_model.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            MetricParser parser = new MetricParser(reader);
            List<Metric> metrics = parser.parse();
            assertEquals(metrics.size(), 26);
            Metric metric = metrics.get(0);
            assertEquals(_expectedStandardMetric, metric);
        } catch (IOException e) {
            fail(e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }

    @SmallTest
    @SuppressWarnings("unchecked")
    public void testParseInvalidMetric_1_3() {
        JsonReader reader = null;
        try {
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_3, "invalid_model.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            MetricParser parser = new MetricParser(reader);
            parser.parse();
            fail("If this is passing the parser isn't failing when it should");
        } catch (FileNotFoundException | UnsupportedEncodingException e) {
            fail(e.getMessage());
        } catch (IOException e) {
            assertNotNull(e);
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }

    @SmallTest
    public void testParseUserInfo_1_6() {
        JsonReader reader = null;
        try {
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_6, "metric_user_info.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            MetricParser parser = new MetricParser(reader);
            List<Metric> metrics = parser.parse();
            assertEquals(metrics.size(), 1);
            Metric metric = metrics.get(0);
            assertEquals(_expectedUserInfoMetric, metric);
            assertEquals("KND", metric.getUserInfo("symbol"));
        } catch (FileNotFoundException | UnsupportedEncodingException e) {
            fail(e.getMessage());
        } catch (IOException e) {
            fail(e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }
}
