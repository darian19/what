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

package com.numenta.taurus.data;

import com.numenta.taurus.metric.MetricType;

import android.content.ContentValues;
import android.database.Cursor;

import java.util.EnumSet;

/**
 * Represents taurus instance data composed of aggregated anomaly value and a mask indicating the
 * metric types with anomalous values if any.
 */
public class InstanceData extends com.numenta.core.data.InstanceData {

    // The metrics with anomalies.
    private int _metricMask;

    /**
     * Create a {@link InstanceData} object using the contents of the given
     * {@link android.database.Cursor}. The {@link android.database.Cursor} must contain all
     * columns required to initialize the {@link InstanceData} object.
     *
     * @param cursor Database cursor with initial data
     */
    public InstanceData(Cursor cursor) {
        super(cursor);
        this._metricMask = cursor.getInt(cursor.getColumnIndex("metric_mask"));
    }

    /**
     * Convert to {@link android.content.ContentValues} to be used by the
     * {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = super.getValues();
        values.put("metric_mask", _metricMask);
        return values;
    }

    /**
     * Constructor used by {@link com.numenta.taurus.data.TaurusDataFactory#createInstanceData}
     */
    protected InstanceData(String instanceId, int aggregation, long timestamp,
            float anomalyScore, EnumSet<MetricType> metricMask) {
        super(instanceId, aggregation, timestamp, anomalyScore);
        _metricMask = 0;
        for (MetricType m : metricMask) {
            _metricMask |= m.flag();
        }
    }

    /**
     * Constructor used by {@link com.numenta.taurus.data.TaurusDataFactory#createInstanceData}
     */
    protected InstanceData(String instanceId, int aggregation, long timestamp,
            float anomalyScore, int metricMask) {
        super(instanceId, aggregation, timestamp, anomalyScore);
        _metricMask = metricMask;
    }

    /**
     * If this data point is anomalous this value will contain a bitmask representing the
     * anomalous metrics
     *
     * @see com.numenta.taurus.metric.MetricType#fromMask(int)
     */
    public int getMetricMask() {
        return _metricMask;
    }
}
