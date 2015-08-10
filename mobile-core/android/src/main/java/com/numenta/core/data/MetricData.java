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

import android.content.ContentValues;
import android.database.Cursor;

public final class MetricData {

    /** Database Table name */
    public static final String TABLE_NAME = "metric_data";

    private String metricId;

    private long timestamp;

    private float metricValue;

    private float anomalyScore;

    private long rowid;

    protected MetricData(Cursor cursor) {
        this.metricId = cursor.getString(cursor.getColumnIndex("metric_id"));
        this.metricValue = cursor.getFloat(cursor.getColumnIndex("metric_value"));
        this.anomalyScore = cursor.getFloat(cursor.getColumnIndex("anomaly_score"));
        this.timestamp = cursor.getLong(cursor.getColumnIndex("timestamp"));
        this.rowid = cursor.getLong(cursor.getColumnIndex("rowid"));
    }

    /**
     * @param metricId
     * @param timestamp
     * @param metricValue
     * @param anomalyScore
     * @param rowid
     */
    protected MetricData(String metricId, long timestamp, float metricValue,
            float anomalyScore, long rowid) {
        this.metricId = metricId;
        this.timestamp = timestamp;
        this.metricValue = metricValue;
        this.anomalyScore = anomalyScore;
        this.rowid = rowid;
    }

    public MetricData() {
    }

    /**
     * Convert to {@link android.content.ContentValues} to be used by the
     * {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = new ContentValues();
        values.put("metric_id", this.metricId);
        values.put("metric_value", this.metricValue);
        values.put("anomaly_score", this.anomalyScore);
        values.put("timestamp", this.timestamp);
        values.put("rowid", this.rowid);
        return values;
    }

    public String getMetricId() {
        return this.metricId;
    }

    public long getTimestamp() {
        return this.timestamp;
    }

    public float getMetricValue() {
        return this.metricValue;
    }

    public float getAnomalyScore() {
        return this.anomalyScore;
    }

    public long getRowid() {
        return this.rowid;
    }

    public void setMetricId(String metricId) {
        this.metricId = metricId;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

}
