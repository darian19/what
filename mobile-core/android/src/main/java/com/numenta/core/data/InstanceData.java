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

import java.io.Serializable;

/**
 * Represents Instance aggregated data
 */
public class InstanceData implements Serializable {

    private static final long serialVersionUID = 3843336684219539713L;

    /** Database Table name */
    public static final String TABLE_NAME = "instance_data";

    private String instanceId;

    private int aggregation;

    private long timestamp;

    private float anomalyScore;

    public InstanceData() {

    }

    protected InstanceData(Cursor cursor) {
        this.instanceId = cursor.getString(cursor.getColumnIndex("instance_id"));
        this.aggregation = cursor.getInt(cursor.getColumnIndex("aggregation"));
        this.timestamp = cursor.getLong(cursor.getColumnIndex("timestamp"));
        this.anomalyScore = cursor.getFloat(cursor.getColumnIndex("anomaly_score"));
    }

    protected InstanceData(String instanceId, int aggregation, long timestamp,
            float anomalyScore) {
        this.instanceId = instanceId;
        this.aggregation = aggregation;
        this.timestamp = timestamp;
        this.anomalyScore = anomalyScore;
    }

    /**
     * Convert to {@link android.content.ContentValues} to be used by the
     * {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = new ContentValues();
        values.put("instance_id", this.instanceId);
        values.put("aggregation", this.aggregation);
        values.put("timestamp", this.timestamp);
        values.put("anomaly_score", this.anomalyScore);
        return values;
    }

    public String getInstanceId() {
        return this.instanceId;
    }

    public void setInstanceId(String instanceId) {
        this.instanceId = instanceId;
    }

    public int getAggregation() {
        return this.aggregation;
    }

    public void setAggregation(int aggregation) {
        this.aggregation = aggregation;
    }

    public long getTimestamp() {
        return this.timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public float getAnomalyScore() {
        return this.anomalyScore;
    }

    public void setAnomalyScore(float anomalyScore) {
        this.anomalyScore = anomalyScore;
    }

}
