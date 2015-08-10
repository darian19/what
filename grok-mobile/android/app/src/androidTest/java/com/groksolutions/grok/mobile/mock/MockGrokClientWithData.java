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

package com.YOMPsolutions.YOMP.mobile.mock;

import com.YOMPsolutions.YOMP.mobile.service.MetricDataParser;
import com.YOMPsolutions.YOMP.mobile.service.MetricParser;
import com.YOMPsolutions.YOMP.mobile.service.NotificationParser;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.service.YOMPException;
import com.numenta.core.utils.Version;
import com.numenta.core.utils.mock.MockYOMPClient;

import junit.framework.Assert;

import org.msgpack.MessagePack;
import org.msgpack.unpacker.Unpacker;

import android.content.Context;
import android.util.JsonReader;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.List;

public class MockYOMPClientWithData extends MockYOMPClient {

    private final Context _context;

    public MockYOMPClientWithData(Context context, Version version) {
        super(version);
        this._context = context;
        // Populate mock with data
        loadMetrics();
        loadMetricData();
        loadNotifications();
    }

    private void loadNotifications() {
        JsonReader reader = null;
        try {
            InputStream in = _context.getResources().getAssets()
                    .open(_version + "/data/_notification.json");
            reader = new JsonReader(
                    new BufferedReader(new InputStreamReader(in, "UTF-8"), 8192));
            NotificationParser parser = new NotificationParser(reader);
            List<Notification> results = parser.parse();
            for (Notification notification : results) {
                addNotification(notification);
            }
            reader.close();
        } catch (IOException e) {
            Assert.fail(e.getLocalizedMessage());
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

    private void loadMetricData() {
        try {
            InputStream in = _context.getResources().getAssets()
                    .open(_version + "/data/_models_data.bin");
            MessagePack msgpack = new MessagePack();
            @SuppressWarnings("resource")
            Unpacker unpacker = msgpack.createUnpacker(new BufferedInputStream(in));
            MetricDataParser parser = new MetricDataParser(unpacker);
            parser.parseAsync(new DataCallback<MetricData>() {
                @Override
                public boolean onData(MetricData metricData) {
                    _metricData.add(metricData);
                    return true;
                }
            });
            unpacker.close();
        } catch (IOException | YOMPException e) {
            Assert.fail(e.getLocalizedMessage());
        }
    }

    private void loadMetrics() {
        JsonReader reader = null;
        try {
            InputStream in = _context.getResources().getAssets()
                    .open(_version + "/data/_models.json");
            reader = new JsonReader(
                    new BufferedReader(new InputStreamReader(in, "UTF-8"), 8192));
            MetricParser parser = new MetricParser(reader);
            _metrics.addAll(parser.parse());
            reader.close();
        } catch (IOException e) {
            Assert.fail(e.getLocalizedMessage());
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
