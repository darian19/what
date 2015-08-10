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
import com.numenta.core.data.Metric;
import com.numenta.core.utils.Log;

import org.json.JSONException;
import org.json.JSONObject;

import android.util.JsonReader;
import android.util.JsonToken;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Internal class used to parse Metric JSON format as follow. <code><pre>
 * [
 *       {
 *          "status": 1,
 *          "last_rowid": 359,
 *          "display_name": "stocks.defaultID.AAPL.VOLUME",
 *          "uid": "f32565f1b6454eb9a26df2ba994e83a9",
 *          "parameters": {
 *              "datasource": "custom",
 *              "metricSpec": {
 *                  "metric": "stocks.defaultID.AAPL.VOLUME",
 *                  "unit": "Count"
 *                  "userInfo": {
 *                      "symbol": "AAPL",
 *                      "metricTypeName": "Stock Volume (Google)"
 *                  }
 *              }
 *          },
 *          "last_timestamp": null,
 *          "description": "Custom metric stocks.defaultID.AAPL.VOLUME",
 *          "poll_interval": 300,
 *          "location": "",
 *          "server": "stocks.defaultID.AAPL.VOLUME",
 *          "tag_name": null,
 *          "instance_status_history": [],
 *          "datasource": "custom",
 *          "message": null,
 *          "name": "stocks.defaultID.AAPL.VOLUME"
 *       }, ...
 * ]
 * </pre></code>
 *
 * @see YOMPClientImpl#getMetrics()
 * @see JsonReader
 */
final public class MetricParser {

    private final JsonReader _reader;

    private final List<Metric> _results;

    public MetricParser(JsonReader reader) {
        this._reader = reader;
        _results = new ArrayList<>();
    }

    /**
     * Peeks at the next token and returns a {@link String} or {@code null}
     */
    String nextStringOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        return _reader.nextString();
    }

    /**
     * Peeks at the next token and returns a {@link Double} or {@code null}
     */
    Double nextNumberOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        return _reader.nextDouble();
    }

    /**
     * Peeks at the next token and returns a {@link Boolean} or {@code null}
     */
    Boolean nextBooleanOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        return _reader.nextBoolean();
    }

    /**
     * Peeks at the next token and returns a {@link List} or {@code null}
     */
    List nextArrayOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        _reader.beginArray();
        Object value = null;
        List arr = new ArrayList();

        while (_reader.hasNext()) {
            switch (_reader.peek()) {
                case STRING:
                    value = nextStringOrNull();
                    break;
                case BEGIN_ARRAY:
                    value = nextArrayOrNull();
                    break;
                case BEGIN_OBJECT:
                    value = nextObjectOrNull();
                    break;
                case BOOLEAN:
                    value = nextBooleanOrNull();
                    break;
                case NUMBER:
                    value = nextNumberOrNull();
                    break;
                case NULL:
                    _reader.nextNull();
                    value = null;
                    break;
            }
            arr.add(value);
        }
        _reader.endArray();
        return arr;
    }

    /**
     * Peeks at the next token and returns a {@link org.json.JSONObject} or {@code null}
     */
    JSONObject nextObjectOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        JSONObject json = new JSONObject();
        String name;
        Object value;
        _reader.beginObject();
        while (_reader.hasNext()) {
            name = _reader.nextName();
            switch (_reader.peek()) {
                case STRING:
                    value = nextStringOrNull();
                    break;
                case BEGIN_ARRAY:
                    value = nextArrayOrNull();
                    break;
                case BEGIN_OBJECT:
                    value = nextObjectOrNull();
                    break;
                case BOOLEAN:
                    value = nextBooleanOrNull();
                    break;
                case NUMBER:
                    value = nextNumberOrNull();
                    break;
                case NULL:
                    _reader.nextNull();
                    value = null;
                    break;
                default:
                    _reader.skipValue();
                    value = null;
            }
            try {
                json.put(name, value);
            } catch (JSONException e) {
                Log.e(getClass().getSimpleName(),
                        "Failed to parse JSON object: " + name + ", value = " + value);
            }
        }
        _reader.endObject();

        return json;
    }

    /**
     * Parse single metric body
     */
    void parseBody() throws IOException {

        // reset values
        String metricId = null;
        int lastRowId = 0;
        String instanceId = null;
        String serverName = null;
        String name = null;
        JSONObject parameters = null;

        _reader.beginObject();
        while (_reader.hasNext()) {
            String property = _reader.nextName();
            switch (property) {
                case "uid":
                    metricId = nextStringOrNull();
                    break;
                case "last_rowid":
                    lastRowId = _reader.nextInt();
                    break;
                case "name":
                    name = nextStringOrNull();
                    break;
                case "server":
                    instanceId = nextStringOrNull();
                    break;
                case "tag_name":
                    serverName = nextStringOrNull();
                    break;
                case "parameters":
                    parameters = nextObjectOrNull();
                    break;
                default:
                    _reader.skipValue();
                    break;
            }
        }
        _reader.endObject();

        serverName = serverName == null ? instanceId : serverName;
        Metric metric = YOMPApplication.getDatabase().getDataFactory()
                .createMetric(metricId, name, instanceId, serverName, lastRowId, parameters);
        _results.add(metric);
    }

    /**
     * Parse metric array
     */
    void parseArray() throws IOException {
        _reader.beginArray();
        while (_reader.hasNext()) {
            parseBody();
        }
        _reader.endArray();
    }

    /**
     * Parse metric JSON response
     */
    public List<Metric> parse() throws IOException {
        parseArray();
        return _results;
    }
}
