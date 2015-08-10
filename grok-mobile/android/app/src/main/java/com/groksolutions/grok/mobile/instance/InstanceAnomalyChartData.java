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

package com.YOMPsolutions.YOMP.mobile.instance;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Annotation;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;

import android.util.Log;
import android.widget.ArrayAdapter;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collection;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Instance data used by the AnomalyChart
 */
public class InstanceAnomalyChartData implements AnomalyChartData, Serializable {
    public static final char CHART_TYPE = 'I';
    private static final long serialVersionUID = 2218295453223414L;
    private static final String TAG = InstanceAnomalyChartData.class
            .getCanonicalName();
    private final ReentrantReadWriteLock _lock = new ReentrantReadWriteLock();
    private final Lock _readLock = _lock.readLock();
    private final Lock _writeLock = _lock.writeLock();
    /**
     * Instance ID
     */
    private final String _instanceId;
    /**
     * Aggregated server data
     */
    private List<Pair<Long, Float>> _data;
    /**
     * Sort rank
     */
    private float _rank;
    /**
     * {@link Comparator} to be used with the
     * {@link ArrayAdapter#sort(Comparator)} function when sorting the data by
     * most anomalous instance
     */
    public static final Comparator<InstanceAnomalyChartData> SORT_BY_ANOMALY = new Comparator<InstanceAnomalyChartData>() {
        @Override
        public int compare(InstanceAnomalyChartData lhs,
                           InstanceAnomalyChartData rhs) {
            if (lhs == rhs)
                return 0;
            if (lhs == null)
                return 1;
            if (rhs == null)
                return -1;

            // Sort by rank in descending order
            return -Double.compare(lhs._rank, rhs._rank) * 100 + SORT_BY_NAME.compare(lhs, rhs);
        }
    };
    private final AggregationType _aggregation;
    private final String _name;
    /**
     * {@link Comparator} to be used with the
     * {@link ArrayAdapter#sort(Comparator)} function when sorting the data by
     * instance name
     */
    public static final Comparator<InstanceAnomalyChartData> SORT_BY_NAME = new Comparator<InstanceAnomalyChartData>() {
        @Override
        public int compare(InstanceAnomalyChartData lhs,
                           InstanceAnomalyChartData rhs) {
            if (lhs == rhs)
                return 0;
            if (lhs == null)
                return 1;
            if (rhs == null)
                return -1;

            if (lhs._name == null && rhs._name == null) {
                return 0;
            }
            if (lhs._name == null)
                return 1;
            if (rhs._name == null)
                return -1;

            return lhs._name.compareToIgnoreCase(rhs._name);
        }
    };
    private long _endDate;
    private long[] _annotations;

    public InstanceAnomalyChartData(String instanceId,
                                    AggregationType aggregation) {
        this._instanceId = instanceId;
        YOMPDatabase YOMPDb = YOMPApplication.getDatabase();
        this._name = YOMPDb.getServerName(_instanceId);
        this._aggregation = aggregation;
    }

    /**
     * @return Instance ID
     */
    @Override
    public String getId() {
        return this._instanceId;
    }

    /**
     * @return Instance Name (tag_name)
     */
    @Override
    public String getName() {
        _readLock.lock();
        try {
            return this._name;
        } finally {
            _readLock.unlock();
        }
    }

    /**
     * @return The {@link AggregationType} used on this instance data
     */
    @Override
    public AggregationType getAggregation() {
        return this._aggregation;
    }

    /**
     * @return Aggregated server data grouped by {@link AggregationType}
     * @see #getAggregation()
     */
    @Override
    public List<Pair<Long, Float>> getData() {
        _readLock.lock();
        try {
            return this._data;
        } finally {
            _readLock.unlock();
        }
    }

    /**
     * Get time stamps with annotations
     */
    @Override
    public long[] getAnnotations() {
        _readLock.lock();
        try {
            return this._annotations;
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public float getRank() {
        return _rank;
    }

    /**
     *  Replace annotations with new values
     * @param newAnnotations the new annotations timestamps
     * @return Old values or {@code null}
     */
    public long[] setAnnotations(long[] newAnnotations) {
        _writeLock.lock();
        try {
            long [] old = this._annotations;
            this._annotations = Arrays.copyOf(newAnnotations, newAnnotations.length);
            return old;
        } finally {
            _writeLock.unlock();
        }
    }
    /**
     * Check if the given timestamp has annotations. The timestamp will be rounded to the correct
     * time window based on the aggregation type: HOUR (5 min), DAY (1 hour), WEEK (8 hours)
     *
     * @param timestamp The time stamp to check.
     * @return {@code true} if there are one or more annotations for the given timestamp
     */
    public boolean hasAnnotationsForTime(long timestamp) {

        if (_annotations != null && _annotations.length > 0) {
            // Set date range to be the whole range based on the current
            // aggregation: HOUR (5 min), DAY (60 min), WEEK (8 hours)
            long from = (timestamp / _aggregation.milliseconds())
                    * _aggregation.milliseconds();
            long to = from + _aggregation.milliseconds();
            for (int i = 0; i < _annotations.length; i++) {
                // Check if we have any annotation in the range of the selected bar.
                if (_annotations[i] >= from && _annotations[i] < to) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * @return {@code true} if we have data, {@code false} otherwise
     */
    @Override
    public boolean hasData() {
        _readLock.lock();
        try {
            return _data != null && !_data.isEmpty();
        } finally {
            _readLock.unlock();
        }
    }

    /**
     * Load server data from the database
     *
     * @return {@code true} if got new data {@code false} otherwise
     */
    @Override
    public boolean load() {
        if (_aggregation == null) {
            return false;
        }
        // Load all annotations
        boolean changed = loadAnnotations();

        _writeLock.lock();
        try {
            YOMPDatabase YOMPDb = YOMPApplication.getDatabase();

            // Query database for aggregated values
            List<Pair<Long, Float>> oldValues = _data;
            if (_endDate <= 0) {
                _endDate = YOMPDb.getLastTimestamp();
            }
            _data = YOMPDb.getAggregatedScoreByInstanceId(_instanceId,
                    _aggregation, _endDate, YOMPApplication.getTotalBarsOnChart());

            // Check if anything changed
            if (oldValues != null && _data.equals(oldValues)) {
                return changed;
            }
            // Calculate sort rank.
            _rank = 0;
            for (Pair<Long, Float> point : _data) {
                if (point.second != null) {
                    _rank += DataUtils.calculateSortRank(point.second);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to load data for server :" + _instanceId, e);
            return false;
        } finally {
            _writeLock.unlock();
        }
        return true;
    }

    /**
     * Load annotations from the database
     *
     * @return {@code true} if got new annotation {@code false} otherwise
     */
    public boolean loadAnnotations() {
        _writeLock.lock();
        try {
            YOMPDatabase YOMPDb = YOMPApplication.getDatabase();
            if (_endDate <= 0) {
                _endDate = YOMPDb.getLastTimestamp();
            }

            // Load Annotations
            Collection<Annotation> result = YOMPDb.getAnnotations(_instanceId, null, new Date(
                    _endDate));
            long newValues[] = null;
            if (result != null && !result.isEmpty()) {
                int i = 0;
                newValues = new long[result.size()];
                for (Annotation ann : result) {
                    newValues[i++] = ann.getTimestamp();
                }
            }
            if (_annotations == null && newValues == null) {
                return false;
            }
            if (!Arrays.equals(_annotations, newValues)) {
                _annotations = newValues;
                return true;
            }
            return false;
        } finally {
            _writeLock.unlock();
        }
    }

    /**
     * Clears the annotations from this chart
     */
    public void clearAnnotations() {
        _writeLock.lock();
        try {
            _annotations = null;
        } finally {
            _writeLock.unlock();
        }
    }

    /**
     * Clears memory cache, call {@link #load()} to reload data from the
     * database
     */
    @Override
    public void clear() {
        _writeLock.lock();
        try {
            _data = null;
            _annotations = null;
            _rank = 0;
        } finally {
            _writeLock.unlock();
        }
    }


    /**
     * Load data up to this date, {@code null} for last known date
     *
     * @return the endDate
     */
    @Override
    public Date getEndDate() {
        return _endDate <= 0 ? null : new Date(_endDate);
    }

    /**
     * Load data up to this date, {@code null} for last known date
     *
     * @param endDate the endDate to set
     */
    @Override
    public void setEndDate(Date endDate) {
        this._endDate = endDate == null ? 0 : endDate.getTime();
    }

    @Override
    public boolean equals(Object o) {
        if (o == null) {
            return false;
        }
        if (o == this) {
            return true;
        }
        if (o instanceof InstanceAnomalyChartData) {
            InstanceAnomalyChartData other = (InstanceAnomalyChartData) o;
            if (_instanceId != other._instanceId && _instanceId != null
                    && !_instanceId.equals(other._instanceId)) {
                return false;
            }
            if (_aggregation != other._aggregation && _aggregation != null
                    && !_aggregation.equals(other._aggregation)) {
                return false;
            }
            if (_endDate != other._endDate) {
                return false;
            }
            if (!Arrays.equals(_annotations, other._annotations)) {
                return false;
            }
            return _data == other._data || (_data != null && _data.equals(other._data));
        }
        return false;
    }

    @Override
    public int hashCode() {
        return (_instanceId.hashCode() << 3) + _aggregation.ordinal();
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.ui.chart.AnomalyChartData#getType()
     */
    @Override
    public char getType() {
        return CHART_TYPE;
    }

    @Override
    public String getUnit() {
        return null;
    }


}
