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
import com.YOMPsolutions.YOMP.mobile.service.NotificationParser;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.YOMPAndroidTestCase;

import android.test.suitebuilder.annotation.SmallTest;
import android.util.JsonReader;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.List;

public class NotificationParserTests extends YOMPAndroidTestCase {

    @Override
    protected void setUp() throws Exception {
        super.setUp();
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    @SmallTest
    @SuppressWarnings("unchecked")
    public void testParseSingleNotificaitonJson_1_3() {
        JsonReader reader = null;
        try {
            Notification expected = YOMPApplication.getDatabase().getDataFactory()
                    .createNotification("5fa710b8-ca07-4deb-be64-a7772c3da520",
                            "f0e7145ae0844811bc2b3a83e1e899a8", 1404844860000l, false, null);

            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_3, "notification.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            NotificationParser parser = new NotificationParser(reader);
            List<Notification> notifications = parser.parse();
            assertEquals(notifications.size(), 2);
            Notification notification = notifications.get(0);
            assertEquals(expected.getLocalId(), notification.getLocalId());
            assertEquals(expected.getMetricId(), notification.getMetricId());
            assertEquals(expected.getNotificationId(), notification.getNotificationId());
            assertEquals(expected.getTimestamp(), notification.getTimestamp());
            assertEquals(expected.isRead(), notification.isRead());
            assertEquals(expected.getDescription(), notification.getDescription());
        } catch (FileNotFoundException e) {
            fail(e.getMessage());
        } catch (UnsupportedEncodingException e) {
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
