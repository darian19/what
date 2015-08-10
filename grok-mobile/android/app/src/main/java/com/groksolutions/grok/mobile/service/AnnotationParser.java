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
import com.numenta.core.data.Annotation;
import com.numenta.core.utils.DataUtils;

import android.util.JsonReader;
import android.util.JsonToken;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Parse {@link com.numenta.core.data.Annotation} JSON format as follow:
 * <p>
 * <code><pre>
 *     [
 *        {
 *        "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
 *        "device", "1231AC32FE",
 *        "created":"2013-08-27 16:46:51",
 *        "timestamp":"2013-08-27 16:45:00",
 *        "user":"User Name",
 *        "server":" AWS/EC2/i-53f52b67",
 *        "message":" The CPU Utilization was high …",
 *        "data": { Optional JSON Object }
 *        },
 *        ...
 *      ]
 * <p/>
 * </pre></code>
 * </p>
 *
 * @see com.numenta.core.data.Annotation
 * @see android.util.JsonReader
 */
public class AnnotationParser {
    private final JsonReader _reader;
    private final List<Annotation> _results;

    public AnnotationParser(JsonReader _reader) {
        this._reader = _reader;
        this._results = new ArrayList<>();
    }

    void parseBody() throws IOException {
        String annotationId = null;
        String device = null;
        String user = null;
        String instanceId = null;
        String message = null;
        String data = null;
        long timestamp = 0;
        long created = 0;

        _reader.beginObject();
        while (_reader.hasNext()) {
            String property = _reader.nextName();
            switch (property) {
                case "uid":
                    annotationId = _reader.nextString();
                    break;
                case "device":
                    device = _reader.nextString();
                    break;
                case "created":
                    created = DataUtils.parseYOMPDate(_reader.nextString()).getTime();
                    break;
                case "timestamp":
                    timestamp = DataUtils.parseYOMPDate(_reader.nextString()).getTime();
                    break;
                case "user":
                    user = _reader.nextString();
                    break;
                case "server":
                    instanceId = _reader.nextString();
                    break;
                case "message":
                    message = nextStringOrNull();
                    break;
                case "data":
                    data = nextStringOrNull();
                    break;
                default:
                    _reader.skipValue();
                    break;
            }
        }
        _reader.endObject();

        _results.add(YOMPApplication.getDatabase().getDataFactory().createAnnotation(annotationId, timestamp, created, device, user,
                instanceId, message, data));
    }

    void parseArray() throws IOException {
        _reader.beginArray();
        while (_reader.hasNext()) {
            parseBody();
        }
        _reader.endArray();
    }

    public List<Annotation> parse() throws IOException {
        if (_reader.peek() == JsonToken.BEGIN_ARRAY) {
            parseArray();
        } else {
            parseBody();
        }
        return _results;
    }
    /**
     * Peeks at the next token and returns a {@link String} or {@code null}
     *
     * @throws IOException
     */
    String nextStringOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        return _reader.nextString();
    }
}
