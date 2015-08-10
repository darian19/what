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

package com.YOMPsolutions.YOMP.mobile.metric;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Metric;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.Pair;

import java.io.Serializable;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Metric data for each row in the list
 */
public class MetricAnomalyChartData implements AnomalyChartData, Serializable {
    private static final long serialVersionUID = -2538370060333880050L;

    public static final char CHART_TYPE = 'M';

    private final ReentrantReadWriteLock _lock = new ReentrantReadWriteLock();
    private final Lock _readLock = _lock.readLock();
    private final Lock _writeLock = _lock.writeLock();
    private Metric _metric;
    private long _endDate;

    /** Aggregated metric data */
    private List<Pair<Long, Float>> _data;

    /** Metric Aggregation type */
    private final AggregationType _aggregation;

    /**
     * {@link Comparator} to be used with the
     * instance name
     */
    public static final Comparator<MetricAnomalyChartData> SORT_BY_NAME = new Comparator<MetricAnomalyChartData>() {
        @Override
        public int compare(MetricAnomalyChartData lhs,
                MetricAnomalyChartData rhs) {
            if (lhs == rhs)
                return 0;
            if (lhs == null)
                return 1;
            if (rhs == null)
                return -1;

            if (lhs._metric == null && rhs._metric == null) {
                return 0;
            }
            if (lhs._metric == null)
                return 1;
            if (rhs._metric == null)
                return -1;
            return lhs._metric.getName().compareToIgnoreCase(rhs._metric.getName());
        }
    };

    public MetricAnomalyChartData(Metric metric, AggregationType aggregation) {
        this._aggregation = aggregation;
        this._metric = metric;
    }

    @Override
    public String getId() {
        _readLock.lock();
        try {
            return _metric == null ? null : _metric.getId();
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public String getName() {
        _readLock.lock();
        try {
            return _metric == null ? null : _metric.getName();
        } finally {
            _readLock.unlock();
        }
    }

    public String getInstanceId() {
        _readLock.lock();
        try {
            return _metric == null ? null : _metric.getInstanceId();
        } finally {
            _readLock.unlock();
        }
    }

    public String getServerName() {
        _readLock.lock();
        try {
            return _metric == null ? null : _metric.getServerName();
        } finally {
            _readLock.unlock();
        }
    }

    public int getLastRowid() {
        _readLock.lock();
        try {
            return _metric != null ? _metric.getLastRowId() : -1;
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public AggregationType getAggregation() {
        return this._aggregation;
    }

    /**
     * Aggregated metric data, should be called after {@link #load()}
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
     * Clears memory cache, call {@link #load()} to reload data from the
     * database
     */
    @Override
    public void clear() {
        _writeLock.lock();
        try {
            _data = null;
        } finally {
            _writeLock.unlock();
        }
    }

    /**
     * Load metric data from the database
     *
     * @return {@code true} if got new data {@code false} otherwise
     */
    @Override
    public boolean load() {
        if (_aggregation == null) {
            return false;
        }
        _writeLock.lock();
        try {
            YOMPDatabase YOMPDb = YOMPApplication.getDatabase();
            this._metric = YOMPDb.getMetric(getId());

            // Query database for aggregated values
            List<Pair<Long, Float>> oldValues = _data;
            if (this._metric != null) {
                _data = YOMPDb.getAggregatedScoreByMetricId(getId(), getAggregation(), _endDate,
                        YOMPApplication.getTotalBarsOnChart());
                if (_endDate <= 0) {
                    _endDate = YOMPDb.getLastTimestamp();
                }
            } else {
                _data = null;
            }
            // Check if anything changed
            if (oldValues != null && oldValues.equals(_data)) {
                return false;
            }

            return true;
        } finally {
            _writeLock.unlock();
        }
    }

    @Override
    public boolean equals(Object o) {
        if (o == null) {
            return false;
        }
        if (o == this) {
            return true;
        }
        if (o instanceof MetricAnomalyChartData) {
            MetricAnomalyChartData other = (MetricAnomalyChartData) o;
            if (_metric != other._metric && _metric != null && !_metric.equals(other._metric)) {
                return false;
            }
            if (_aggregation != other._aggregation && _aggregation != null
                    && !_aggregation.equals(other._aggregation)) {
                return false;
            }
            if (_endDate != other._endDate) {
                return false;
            }
            return _data == other._data || (_data != null && _data.equals(other._data));
        }
        return false;
    }

    @Override
    public int hashCode() {
        return (_metric != null ? (_metric.hashCode() << 3) : 0) + (_aggregation.ordinal() << 1);
    }

    public Metric getMetric() {
        return _metric;
    }

    /**
     * Load data up to this date, {@code null} for last known date
     *
     * @param endDate the endDate to set
     */
    @Override
    public void setEndDate(Date endDate) {
        _endDate = endDate == null ? 0 : endDate.getTime();
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

    @Override
    public char getType() {
        return CHART_TYPE;
    }

    @Override
    public String getUnit() {
        if (_metric != null) {
            return _metric.getUnit();
        }
        return null;
    }

    @Override
    public long[] getAnnotations() {
        // TODO Auto-generated method stub
        return null;
    }

    @Override
    public float getRank() {
        return 0;
    }
}
