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

package com.numenta.core.data;

import org.json.JSONException;
import org.json.JSONObject;

import android.content.ContentValues;
import android.database.Cursor;
import android.util.Log;

import java.io.IOException;
import java.io.Serializable;

/**
 * Helper class representing one "metric" record
 */
public final class Metric implements Serializable {

    private static final long serialVersionUID = 5441566818295535142L;

    /** Database Table name */
    public static final String TABLE_NAME = "metric";

    private final String _metricId;

    private final String _name;

    private final String _instanceId;

    private final int _lastRowId;

    private final String _serverName;

    private final String _parameters;

    /** Holds parsed parameters */
    private transient JSONObject _parametersJson;

    private long _lastTimestamp;

    /**
     * Create a {@link com.numenta.core.data.Metric} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link com.numenta.core.data.Metric} object.
     */
    protected Metric(Cursor cursor) {
        this._metricId = cursor.getString(cursor.getColumnIndex("metric_id"));
        this._lastRowId = cursor.getInt(cursor.getColumnIndex("last_rowid"));
        this._name = cursor.getString(cursor.getColumnIndex("name"));
        this._instanceId = cursor.getString(cursor.getColumnIndex("instance_id"));
        this._serverName = cursor.getString(cursor.getColumnIndex("server_name"));
        this._lastTimestamp = cursor.getLong(cursor.getColumnIndex("last_timestamp"));

        // Get metric JSON Parameters from the database
        _parameters = cursor.getString(cursor.getColumnIndex("parameters"));
        if (_parameters != null && !_parameters.trim().isEmpty()) {
            try {
                _parametersJson = new JSONObject(_parameters);
            } catch (JSONException e) {
                _parametersJson = null;
                Log.e(Metric.class.getSimpleName(), "Failed to parse metric parameters", e);
            }
        }
    }

    /**
     * Construct a new {@link Metric} object
     */
    protected Metric(String metricId, String name, String instanceId, String serverName,
            int lastRowId, JSONObject parameters) {
        this._metricId = metricId;
        this._name = name;
        this._instanceId = instanceId;
        this._serverName = serverName;
        this._lastRowId = lastRowId;
        this._parametersJson = parameters;
        this._parameters = parameters != null ? parameters.toString() : null;

        // Should be updated with the the last timestamp available in the
        // metric_data table
        this._lastTimestamp = 0;
    }

    /**
     * Convert to {@link android.content.ContentValues} to be used by the
     * {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = new ContentValues();
        values.put("metric_id", this._metricId);
        values.put("last_rowid", this._lastRowId);
        values.put("name", this._name);
        values.put("instance_id", this._instanceId);
        values.put("server_name", this._serverName);
        values.put("last_timestamp", this._lastTimestamp);
        if (this._parameters != null) {
            values.put("parameters", this._parameters);
        }
        return values;
    }

    /**
     * Get the top level parameter value
     *
     * @param name The parameter name
     * @return The parameter value or {@code null} if the parameter does not exist
     */
    public String getParameter(String name) {
        if (_parametersJson != null) {
            return _parametersJson.optString(name, null);
        }
        return null;
    }

    /**
     * Get the "metricSpec" parameter value
     *
     * @param name The name of the "metricSpec" parameter
     * @return The parameter value or {@code null} if the parameter does not exist
     */
    public String getMetricSpec(String name) {
        if (_parametersJson != null) {
            JSONObject spec = _parametersJson.optJSONObject("metricSpec");
            if (spec != null) {
                return spec.optString(name, null);
            }
        }
        return null;
    }

    /**
     * Get the "userInfo" parameter value
     *
     * @param name The name of the "userInfo" parameter
     * @return The parameter value or {@code null} if the parameter does not exist
     */
    public String getUserInfo(String name) {
        if (_parametersJson != null) {
            JSONObject spec = _parametersJson.optJSONObject("metricSpec");
            if (spec != null) {
                JSONObject info = spec.optJSONObject("userInfo");
                if (info != null) {
                    return info.optString(name, null);
                }
            }
        }
        return null;
    }

    /**
     * Get the metric ID
     */
    public String getId() {
        return this._metricId;
    }

    /**
     * Get metric name
     */
    public String getName() {
        return this._name;
    }

    /**
     * Get server name of the instance associated with this metric
     *
     * @see #getInstanceId()
     */
    public String getServerName() {
        return this._serverName;
    }

    /**
     * Get instance ID associated with this metric
     */
    public String getInstanceId() {
        return this._instanceId;
    }

    /**
     * Get last know row ID for this metric
     */
    public int getLastRowId() {
        return _lastRowId;
    }

    /**
     * Get the metric unit if available, {@code null} if unknown
     */
    public String getUnit() {
        String unit = getParameter("unit");
        if (unit == null) {
            unit = getMetricSpec("unit");
        }
        return unit;
    }

    /*
     * (non-Javadoc)
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {
        return (this._metricId == null) ? 0 : this._metricId.hashCode();
    }

    /*
     * (non-Javadoc)
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null) {
            return false;
        }
        if (!(obj instanceof Metric)) {
            return false;
        }
        Metric other = (Metric) obj;
        if (this._metricId == null) {
            return other._metricId == null;
        }
        return this._metricId.equals(other._metricId);
    }

    /**
     * Get the last Timestamp
     */
    public long getLastTimestamp() {
        return this._lastTimestamp;
    }

    /**
     * Update metric Timestamp
     *
     * @param lastTimestamp the lastTimestamp to set
     */
    public void setLastTimestamp(long lastTimestamp) {
        this._lastTimestamp = lastTimestamp;
    }

    /**
     * Get metric parameters
     */
    public JSONObject getParameters() {
        return _parametersJson;
    }

    /**
     * Process custom deserialization
     */
    private void readObject(java.io.ObjectInputStream in)
            throws IOException, ClassNotFoundException {
        // Deserialize serializable fields
        in.defaultReadObject();

        // "JSONObject" is not serializable and marked as "tansient" therefore we have to parse the
        // JSON parameters once the object is de-serialized
        if (_parameters != null && !_parameters.trim().isEmpty()) {
            try {
                _parametersJson = new JSONObject(_parameters);
            } catch (JSONException e) {
                _parametersJson = null;
                Log.e(Metric.class.getSimpleName(), "Failed to parse metric parameters", e);
            }
        }
    }
}
