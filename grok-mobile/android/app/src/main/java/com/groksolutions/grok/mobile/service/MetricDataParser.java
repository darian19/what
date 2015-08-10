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
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.MetricData;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.utils.DataUtils;

import org.msgpack.unpacker.Unpacker;

import android.util.JsonReader;

import java.io.EOFException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * <p>
 * Internal class used to parse Metric Data JSON format as follow. <code><pre>
 * {
 *   "data":[
 *           ["2013-08-15 21:34:00", 222, 0.025, 1],
 *           ["2013-08-15 21:32:00", 202, 0, 2],
 *           ["2013-08-15 21:30:00", 202, 0, 3],
 *           ...
 *          ],
 *   "names":[
 *            "timestamp",
 *            "value",
 *            "anomaly_score",
 *            "rowid"
 *           ]
 * }
 * </pre></code>
 * <p>
 * This class also parses Metric Data Binary format using msgpack (http://msgapag.org) format.
 * <p>
 * The binary format is: <code><pre>
 * ['names', 'uid', 'timestamp', 'value', 'anomaly_score', 'rowid']
 * ['ba5a402835564aa5a4b0f13f9d6512f4', 1391040000, 2.176, 0.344578, 6839]
 * ['8add2a5eb0664bf69e4ddf9f8d7fbbf5', 1391040000, 0.334, 0.308538, 6838]
 * ['d5f9c1af092340fa9404200957fcf351', 1391040000, 44.368, 0.274253, 6818]
 * ...
 * </pre></code>
 *
 * @see JsonReader
 * @see org.msgpack.unpacker.Unpacker
 */
final public class MetricDataParser {

    private JsonReader _jsonreader;

    private String metricId;

    private long timestamp;

    private float metricValue;

    private float anomalyScore;

    private long rowid;

    private List<MetricData> _data;

    private YOMPClient.DataCallback<MetricData> _callback;

    private Unpacker _unpacker;

    /**
     * Creates a new message data parser for the given {@link JsonReader}.
     * <p>
     * The message data format is assumed to be JSON
     * <p>
     * If "metricId" is known then we can create a new metric data object and notify the caller
     * otherwise save the partial information in the _data collection and notify the caller once we
     * know the "metricId"
     */
    public MetricDataParser(String metricId, JsonReader reader) {
        this.metricId = metricId;
        _data = new ArrayList<>();
        _jsonreader = reader;
    }

    /**
     * Creates a new message data parser for the given {@link Unpacker}.
     * <p>
     * The message data format is assumed to be binary using the msgpack protocol
     */
    public MetricDataParser(Unpacker unpacker) {
        this._unpacker = unpacker;
    }

    private void parseRow() throws IOException, YOMPException {
        CoreDataFactory factory = YOMPApplication.getDatabase()
                .getDataFactory();
        _jsonreader.beginArray();
        while (_jsonreader.hasNext()) {
            timestamp = DataUtils.parseYOMPDate(_jsonreader.nextString()).getTime();
            metricValue = (float) _jsonreader.nextDouble();
            anomalyScore = (float) _jsonreader.nextDouble();
            rowid = _jsonreader.nextLong();
            // If "metricId" is known then we can create a new metric data
            // object and notify the caller otherwise save the partial
            // information in the _data collection and notify the caller once we
            // know the "metricId"
            if (metricId != null) {
                if (_callback != null) {
                    _callback.onData(factory.createMetricData(metricId, timestamp, metricValue,
                            anomalyScore, rowid));
                }
            } else {
                _data.add(factory.createMetricData(metricId, timestamp, metricValue, anomalyScore,
                        rowid));
            }
        }
        _jsonreader.endArray();
    }

    private void parseData() throws IOException, YOMPException {
        _jsonreader.beginArray();
        _data.clear();
        while (_jsonreader.hasNext()) {
            parseRow();
        }
        _jsonreader.endArray();
    }

    private void parseMetrics() throws IOException, YOMPException {
        String property;
        _jsonreader.beginArray();
        while (_jsonreader.hasNext()) {
            _jsonreader.beginObject();
            metricId = null;
            while (_jsonreader.hasNext()) {
                property = _jsonreader.nextName();
                if (property.equals("uid")) {
                    metricId = _jsonreader.nextString();
                } else if (property.equals("data")) {
                    parseData();
                }
            }
            _jsonreader.endObject();
            if (metricId != null && !_data.isEmpty()) {
                // Update "metricId" and notify caller
                for (MetricData row : _data) {
                    row.setMetricId(metricId);
                    if (_callback != null) {
                        _callback.onData(row);
                    }
                }
            }
        }
        _jsonreader.endArray();
    }

    private void parseBody() throws IOException, YOMPException {
        if (_jsonreader != null) {
            _jsonreader.beginObject();
            String property;
            while (_jsonreader.hasNext()) {
                property = _jsonreader.nextName();
                switch (property) {
                    case "metrics":
                        parseMetrics();
                        break;
                    case "data":
                        parseData();
                        break;
                    default:
                        _jsonreader.skipValue();
                        break;
                }
            }
            _jsonreader.endObject();
        } else if (_unpacker != null) {
            unpackMessage();
        }
    }

    /**
     * Unpack message data stream using msgpack protocol.
     *
     * @see http://msgpack.org
     */
    private void unpackMessage() throws IOException {

        try {
            // Ignore field names
            _unpacker.skip();

            CoreDataFactory factory = YOMPApplication.getDatabase()
                    .getDataFactory();

            // Read all rows. Expect 6 fields
            while (_unpacker.readArrayBegin() != 6) {
                metricId = _unpacker.readString();
                timestamp = _unpacker.readLong() * 1000;
                metricValue = _unpacker.readFloat();
                anomalyScore = _unpacker.readFloat();
                rowid = _unpacker.readInt();
                _unpacker.readArrayEnd();
                if (_callback != null) {
                    _callback.onData(factory.createMetricData(metricId, timestamp, metricValue,
                            anomalyScore, rowid));
                }
            }
        } catch (EOFException eof) {
            // Ignore. EOF
        }
    }

    /**
     * Parse the Data Stream asynchronously, notifying the caller on every metric parsed
     *
     * @param callback If set this callback will be called on every metric data row with the parsed
     *                 data
     */
    public void parseAsync(YOMPClient.DataCallback<MetricData> callback)
            throws IOException, YOMPException {
        _callback = callback;
        parseBody();
    }

    /**
     * Parse the Data Stream and return the parsed metrics after the whole stream is parsed
     *
     * @return List containing all metrics from the stream
     */
    public List<MetricData> parse() throws IOException, YOMPException {
        final ArrayList<MetricData> results = new ArrayList<>();
        _callback = new YOMPClient.DataCallback<MetricData>() {
            @Override
            public boolean onData(MetricData metricData) {
                results.add(metricData);
                return true;
            }
        };
        try {
            parseBody();
        } catch (IllegalStateException e) {
            throw new YOMPException("Metric Data may be corrupt.  Elements missing from JSON.", e);
        }
        return results;
    }
}
