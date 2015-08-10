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

package com.YOMPsolutions.YOMP.mobile.test.integration;

import com.YOMPsolutions.YOMP.mobile.BuildConfig;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.YOMPsolutions.YOMP.mobile.service.InstanceParser;
import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.service.NotificationSettings;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPUnauthorizedException;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import android.test.ApplicationTestCase;
import android.test.suitebuilder.annotation.LargeTest;
import android.test.suitebuilder.annotation.Suppress;

import java.io.IOException;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.UUID;

// FIXME: TAUR-601 Move all YOMP integration tests to the YOMP folder path
public class YOMPClientIntegrationTests extends ApplicationTestCase<YOMPApplication> {

    // Server Info
    YOMPClientImpl _client;

    String _serverUrl;

    String _serverPass;

    // Model created by the test
    String _instanceId;

    String _modelId;

    // Annotations created by the test
    List<Annotation> _annotations;

    // Test info
    boolean _firstRun = true;

    public YOMPClientIntegrationTests() {
        super(YOMPApplication.class);
    }

    /**
     * This method is used to emulate JUnit4 @BeforeClass behavior.
     * It will be called only once for all the tests in this class.
     * The main purpose of this method is to prepare the server with all the data necessary to run
     * the tests.
     */
    private void beforeClass() {
        /* When using "gradle" to run the tests, the android generated class "BuildConfig" will be
         * populated with the two extra fields "SERVER_URL" and "SERVER_PASS", see "build.gradle".
         */
        try {
            Field field = BuildConfig.class.getField("SERVER_URL");
            _serverUrl = (String) field.get(null);
            field = BuildConfig.class.getField("SERVER_PASS");
            _serverPass = (String) field.get(null);
        } catch (NoSuchFieldException | IllegalAccessException | IllegalArgumentException ignore) {
            // ignore
        }
        // If no values is given, default to emulator's host machine
        if (_serverUrl == null || _serverUrl.isEmpty()) {
            _serverUrl = "https://10.0.2.2";
            _serverPass = "12345";
        }

        // Connect to backend server
        System.out.println("Server URL:" + _serverUrl);
        System.out.println("Server Pass:" + _serverPass);
        try {
            _client = (YOMPClientImpl) YOMPApplication.getInstance().connectToYOMP(_serverUrl, _serverPass);
            assertNotNull(_client);
            // Create instances
            JSONArray metrics = new JSONArray(_client.get(_serverUrl
                    + "/_metrics/cloudwatch/us-west-2/AWS/EC2/CPUUtilization"));
            assertTrue("Failed to get cloudwatch metrics for 'us-west-2' region",
                    metrics.length() > 0);

            // Get first EC2 metric
            JSONObject metricJSON = metrics.getJSONObject(0);

            // Create model for metric
            String result = _client.post(_serverUrl + "/_models", metricJSON.toString());
            assertNotNull(result);
            JSONArray resultsArr = new JSONArray(result);
            assertEquals("Failed to create model", 1, resultsArr.length());
            JSONObject modleJson = resultsArr.getJSONObject(0);

            _instanceId = InstanceParser.MER2764InstanceIdHACK(_client.getServerVersion(),
                    modleJson.getString("server"));
            _modelId = modleJson.getString("uid");

            // keep track of annotations created by this test
            _annotations = new ArrayList<Annotation>();
        } catch (JSONException | YOMPException | IOException e) {
            fail(e.getLocalizedMessage());
        }
    }

    @LargeTest
    public void testPreconditions() {
        assertNotNull("Unable to initialize YOMPClient", _client);
        assertNotNull("Unable to create test model", _modelId);
        assertNotNull("Unable to get Instance ID", _instanceId);
    }

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        createApplication();
        if (_firstRun) {
            // Emulate JUnit 4 @BeforeClass
            beforeClass();
            _firstRun = false;
        }
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
        //Delete Model
        if (_modelId != null) {
            _client.delete(_serverUrl + "/_models/" + _modelId);
        }
        // Delete annotations
        if (_annotations != null) {
            for (Annotation ann : _annotations) {
                _client.deleteAnnotation(ann);
            }
            _annotations.clear();
        }
    }

    @LargeTest
    public final void testIsOnline() {
        assertTrue(_client.isOnline());
    }

    @LargeTest
    public final void testLogin() {
        try {
            _client.login();
        } catch (IOException | YOMPException e) {
            fail(e.getLocalizedMessage());
        }
    }


    @LargeTest
    public final void testAnnotationBackwardCompatibility() throws IOException, YOMPException {
        // Annotations were introduced in version 1.6
        if (_client.getServerVersion().compareTo(YOMPClientImpl.YOMP_SERVER_1_6) >= 0) {
            // If the server version is 1.6 and above then ignore this test and run #testAnnotations
            return;
        }
        // If the server version is lower than 1.6 then the result should be null
        assertNull(_client.addAnnotation(new Date(), _instanceId, "test message1", "user1"));
        assertNull(_client.getAnnotations(null, null));

        // If the server version is lower than 1.6 then it should ignore the request and
        // not throw any exception
        CoreDataFactory factory = YOMPApplication.getDatabase()
                .getDataFactory();
        _client.deleteAnnotation(factory.createAnnotation(UUID.randomUUID().toString(), 0, 0,
                "fake_device", "other_user", _instanceId, "Other user's annotation", null));


    }

    @LargeTest
    public final void testAnnotations() throws IOException, YOMPException, InterruptedException {
        // Annotations were introduced in version 1.6
        if (_client.getServerVersion().compareTo(YOMPClientImpl.YOMP_SERVER_1_6) < 0) {
            // If the server version is lower than 1.6 then ignore this test and
            // run #testAnnotationCompatibility
            return;
        }

        Calendar cal = Calendar.getInstance();
        cal.set(2014, Calendar.JANUARY, 25, 9, 0, 0);
        cal.set(Calendar.MILLISECOND, 0);
        Date timestamp1 = cal.getTime();
        Date now = new Date();
        // Make sure "created" time is different
        Thread.sleep(1000);

        // Test add annotation
        Annotation expected1 = _client
                .addAnnotation(timestamp1, _instanceId, "test message1", "user1");
        // Make sure annotation was created
        assertNotNull(expected1);

        // Mark for deletions after the test
        _annotations.add(expected1);

        // Validate fields
        assertEquals("Invalid device", YOMPApplication.getDeviceId(), expected1.getDevice());
        assertNotNull("Invalid uid", expected1.getId());
        assertEquals("Invalid instance", _instanceId, expected1.getInstanceId());
        assertEquals("Invalid message", "test message1", expected1.getMessage());
        assertEquals("Invalid user", "user1", expected1.getUser());
        assertEquals("Invalid timestamp", timestamp1.getTime(), expected1.getTimestamp());
        assertTrue(
                "Invalid created date: Expected " + now.getTime() + " < " + expected1.getCreated(),
                now.getTime() < expected1.getCreated());
        assertNull("Invalid data", expected1.getData());

        // Test Unable to add annotation with Invalid server
        Annotation actual = _client
                .addAnnotation(timestamp1, "invalid_server", "test message1", "user1");
        assertNull("Created annotation with invalid server", actual);

        // Add more annotations
        cal.set(2014, Calendar.JANUARY, 26, 9, 0, 0);
        Date timestamp2 = cal.getTime();
        cal.set(2014, Calendar.JANUARY, 27, 9, 0, 0);
        Date timestamp3 = cal.getTime();
        // Make sure "created" time is different
        Thread.sleep(1000);
        Annotation expected2 = _client
                .addAnnotation(timestamp2, _instanceId, "test message 2", "user2");
        // Mark for deletions after the test
        _annotations.add(expected2);
        // Make sure "created" time is different
        Thread.sleep(1000);
        Annotation expected3 = _client
                .addAnnotation(timestamp3, _instanceId, "test message 3", "user3");
        // Mark for deletions after the test
        _annotations.add(expected3);

        // Test get annotations
        List<Annotation> actualList = _client.getAnnotations(timestamp1, timestamp3);
        assertEquals("Unable to get annotations", 3, actualList.size());
        // Make sure annotations are returned by "created" order
        assertEquals("Get annotation in wrong order", actualList.get(0).getId(), expected3.getId());
        actualList = _client.getAnnotations(timestamp2, timestamp3);
        assertEquals("Unable to get annotations", 2, actualList.size());

        // Test Delete annotation
        _client.deleteAnnotation(expected2);
        actualList = _client.getAnnotations(timestamp2, timestamp3);
        assertEquals("Failed to delete annotation", 1, actualList.size());

        // Check if the correct annotation was deleted. Only 'expected3' should be returned here
        assertEquals("Failed to delete annotation", actualList.get(0).getId(), expected3.getId());

        // Test unable to delete annotations created on other devices
        try {
            cal.set(2014, Calendar.JANUARY, 28, 9, 0, 0);
            Date timestamp4 = cal.getTime();
            // NOTE: This is basically a unit test not integration test.
            // It will use a fake annotation object with fake device id instead of real annotation
            // object from the server. This test will make sure "YOMPClient" does not even attempt
            // to delete annotations from other devices.

            CoreDataFactory factory = YOMPApplication.getDatabase().getDataFactory();
            Annotation otherUserAnnotation = factory.createAnnotation(UUID.randomUUID().toString(),
                    timestamp4.getTime(), now.getTime(), "fake_device", "other_user", _instanceId,
                    "Other user's annotation", null);
            _client.deleteAnnotation(otherUserAnnotation);
            fail("Should not be able to delete other user's annotations");
        } catch (YOMPUnauthorizedException e) {
            // Expected exception
        }
    }

    @LargeTest
    public final void testGetMetrics() {
        try {
            List<Metric> list = _client.getMetrics();
            assertNotNull(list);
            // Find our metric in the returned list
            boolean found = false;
            for (Metric m : list) {
                if (m.getId().equals(_modelId)) {
                    // Found it
                    found = true;
                    break;
                }
            }
            assertTrue("Failed to get all metrics. Test Metric " + _modelId + " is missing", found);
        } catch (YOMPException | IOException e) {
            fail(e.getMessage());
        }
    }

    @LargeTest
    public final void testGetServerVersion() {
        assertTrue("Server must be " + YOMPClientImpl.YOMP_SERVER_OLDEST + " or greater",
                _client.getServerVersion().compareTo(YOMPClientImpl.YOMP_SERVER_OLDEST) >= 0);
    }

    @LargeTest
    public final void testGetInstances() throws YOMPException, IOException, JSONException {
        List<Instance> list = _client.getInstances();
        assertNotNull(list);
        boolean found = false;
        // Find our instance in the returned list
        for (Instance instance : list) {
            String id = instance.getId();
            // FIXME: HACK for server 1.4 and higher. See MER-2764
            id = InstanceParser.MER2764InstanceIdHACK(_client.getServerVersion(), id);
            if (id.equals(_instanceId)) {
                found = true;
                break;
            }
        }
        assertTrue("Failed to get all instances. Test Instance " + _instanceId + " is missing",
                found);
    }

    @LargeTest
    @Suppress
    /*
    FIXME: This Tests assumes the server does not have any notification settings for the device.
           Suppress until we add an API to clear the notification settings for a specific device.
    */
    public final void testNotificationSettings() throws IOException, YOMPException {
        // Should not have any settings for this device
        assertNull("Invalid notification settings", _client.getNotificationSettings());

        // Create test settings
        _client.updateNotifications("test@test", 3600);

        // Verify server response for test settings
        NotificationSettings settings = _client.getNotificationSettings();
        assertEquals("Invalid notification settings", "test@test", settings.getEmail());
        assertEquals("Invalid notification settings", 3600, settings.getFrequency());
    }

    @LargeTest
    public final void testNotifications() throws IOException, YOMPException {
        //FIXME There is no easy way to add notifications to the server
        // For now just test the notification API is working
        assertNull("Invalid Notification Response", _client.getNotifications());
    }

    /* (non-Javadoc)
     * @see android.test.AndroidTestCase#scrubClass(java.lang.Class)
     */
    @Override
    protected void scrubClass(Class<?> testCaseClass) throws IllegalAccessException {
        //FIXME HACK: Prevent values from being reset by AndroidTestCase#scrubClass
    }
}
