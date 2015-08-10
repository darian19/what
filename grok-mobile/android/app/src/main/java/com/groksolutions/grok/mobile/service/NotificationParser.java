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

package com.YOMPsolutions.YOMP.mobile.service;

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Notification;
import com.numenta.core.utils.DataUtils;

import android.util.JsonReader;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Internal class used to parse Notificaiton JSON format as follow. <code><pre>
 *   [
 *     {
 *       "uid": "bfe698de-9867-4ee2-a2d2-d5326405a03e",
 *       "timestamp": "2014-02-10 23:47:27",
 *       "metric": "efaf60e420cb4d269bdf60f89304b675",
 *       "acknowledged": 0,
 *       "windowsize": 3600,
 *       "device": "1"
 *     },
 *     ...
 *   ]
 * </pre></code>
 *
 * @see YOMPClientImpl#getMetrics()
 * @see JsonReader
 */
final public class NotificationParser {

    private final JsonReader _reader;

    private String metricId;

    private String notificationId;

    private final List<Notification> _results;

    private long timestamp;

    public NotificationParser(JsonReader reader) {
        this._reader = reader;
        _results = new ArrayList<>();
    }

    void parseBody() throws IOException {

        _reader.beginObject();
        while (_reader.hasNext()) {
            String notificationProperty = _reader.nextName();
            switch (notificationProperty) {
                case "uid":
                    notificationId = _reader.nextString();
                    break;
                case "metric":
                    metricId = _reader.nextString();
                    break;
                case "timestamp":
                    timestamp = DataUtils.parseYOMPDate(_reader.nextString()).getTime();
                    break;
                default:
                    _reader.skipValue();
                    break;
            }
        }
        _reader.endObject();

        _results.add(YOMPApplication.getDatabase().getDataFactory().createNotification(
                notificationId, metricId, timestamp, false, null));
    }

    void parseArray() throws IOException {
        _reader.beginArray();
        while (_reader.hasNext()) {
            parseBody();
        }
        _reader.endArray();
    }

    public List<Notification> parse() throws IOException {
        parseArray();
        return _results;
    }
}
