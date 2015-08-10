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

package com.numenta.taurus.instance;

import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Metric;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.AnomalyValue;
import com.numenta.taurus.data.MarketCalendar;
import com.numenta.taurus.data.TaurusDatabase;
import com.numenta.taurus.metric.MetricType;

import android.util.Log;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Date;
import java.util.EnumSet;
import java.util.List;
import java.util.ListIterator;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Instance data used by the AnomalyChart
 */
public class InstanceAnomalyChartData implements AnomalyChartData, Serializable {

    private static final long serialVersionUID = 2218295453223414L;

    private static final String TAG = InstanceAnomalyChartData.class.getCanonicalName();

    private final ReentrantReadWriteLock _lock = new ReentrantReadWriteLock();

    private final Lock _readLock = _lock.readLock();

    private final Lock _writeLock = _lock.writeLock();

    private String _ticker;

    private String _instanceId;

    private List<Pair<Long, Float>> _data;

    private float _rank;

    private AggregationType _aggregation;

    private String _name;

    private long _endDate;

    private List<Metric> _metrics;

    private int _anomalousMetrics;

    private boolean _modified;

    private long _lastDbTimestamp;

    public InstanceAnomalyChartData(final String instanceId, AggregationType aggregation) {
        this._instanceId = instanceId;
        this._aggregation = aggregation;
        _modified = true;
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

    public List<Pair<Long, Float>> getCollapsedData() {
        _readLock.lock();
        try {
            ArrayList<Pair<Long, Float>> collapsedData = new ArrayList<Pair<Long, Float>>();
            if (_data != null) {
                boolean closed = false;
                MarketCalendar marketCalendar = TaurusApplication.getMarketCalendar();
                // Iterate over data and closed hours to created a consolidated collapsed data
                for (Pair<Long, Float> value : _data) {
                    // Add interval to time to make sure the range fall into period
                    long time = value.first + DataUtils.METRIC_DATA_INTERVAL;
                    // Check if data falls into closed period
                    if (!marketCalendar.isOpen(time)) {
                        closed = true;
                        // Get next data value
                        continue;
                    }

                    // Add one empty bar for closed period
                    if (closed) {
                        collapsedData.add(new Pair<Long, Float>(null, null));
                        closed = false;
                    }
                    collapsedData.add(value);
                }
                // Check for last closed period and add the empty bar if necessary
                if (closed) {
                    collapsedData.add(new Pair<Long, Float>(null, null));
                }
            }
            return collapsedData;
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public long[] getAnnotations() {
        return null;
    }

    /**
     * Return the overall rank for the data represented by this class.
     * Usually the rank is calculated as the sum of all anomaly score values
     */
    @Override
    public float getRank() {
        return _rank;
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
        boolean changed = false;
        _writeLock.lock();
        try {
            TaurusDatabase database = TaurusApplication.getDatabase();
            _name = database.getServerName(_instanceId);
            _ticker = database.getTickerSymbol(_instanceId);
            _metrics = database.getMetricsByInstanceId(_instanceId);

            // If no endDate is given then use the last known timestamp
            long timestamp = database.getLastTimestamp();
            if (_endDate <= 0) {
                _endDate = timestamp;
            }

            final int limit = TaurusApplication.getTotalBarsOnChart();
            // Make sure to load 7 days worth of data to accommodate collapsed view
            final long startDate = _endDate - 7 * limit * _aggregation.milliseconds();
            // Query database for aggregated values
            List<Pair<Long, AnomalyValue>> anomalies =
                    database.getInstanceData(_instanceId, startDate, _endDate);

            // Extract anomaly scores
            ArrayList<Pair<Long, Float>> scores = new ArrayList<Pair<Long, Float>>(anomalies.size());
            for (Pair<Long, AnomalyValue> value : anomalies) {
                scores.add(new Pair<Long, Float>(value.first, value.second.anomaly));
            }
            // Check if anything changed
            if (!scores.equals(_data)) {
                _data = scores;
                changed = true;
            }
            // Rank data based on the last bars if changed
            if (timestamp != _lastDbTimestamp || changed) {
                _lastDbTimestamp = timestamp;
                anomalies = database.getInstanceData(_instanceId,
                        _lastDbTimestamp - limit * _aggregation.milliseconds(),
                        _lastDbTimestamp);
                _rank = 0;
                _anomalousMetrics = 0;
                ListIterator<Pair<Long, AnomalyValue>> iterator = anomalies
                        .listIterator(anomalies.size());
                for (int i = 0; i < limit && iterator.hasPrevious(); i++) {
                    Pair<Long, AnomalyValue> point = iterator.previous();
                    if (point.second != null) {
                        // Add anomaly to sort rank
                        _rank += DataUtils.calculateSortRank(Math.abs(point.second.anomaly));
                        // Update metric mask
                        _anomalousMetrics |= point.second.metricMask;
                    }
                }
                // Update rank based on anomalous metric type
                // Stock + Twitter > Stock > Twitter > None
                if (_anomalousMetrics != 0) {
                    EnumSet<MetricType> metricTypes = MetricType.fromMask(_anomalousMetrics);
                    // Check for anomalous stock values
                    if (metricTypes.contains(MetricType.StockPrice) ||
                            metricTypes.contains(MetricType.StockVolume)) {
                        _rank += DataUtils.RED_SORT_FLOOR * 1000;
                    }
                    // Check for anomalous twitter values
                    if (metricTypes.contains(MetricType.TwitterVolume)) {
                        _rank += DataUtils.RED_SORT_FLOOR * 100;
                    }
                }
            }
            _modified = false;
        } catch (Exception e) {
            Log.e(TAG, "Failed to load data for server :" + _instanceId, e);
            return false;
        } finally {
            _writeLock.unlock();
        }
        return changed;
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
            _rank = 0;
            _modified = true;
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
        _modified = true;
    }

    public void setEndDate(long endDate) {
        this._endDate = endDate;
        _modified = true;
    }

    @Override
    public boolean equals(Object o) {
        if (o == this) {
            return true;
        }
        if (o instanceof InstanceAnomalyChartData) {
            InstanceAnomalyChartData other = (InstanceAnomalyChartData) o;
            if (_instanceId != null && !_instanceId.equals(other._instanceId)) {
                return false;
            }
            if (_aggregation != other._aggregation) {
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
        return (_instanceId.hashCode() << 3) + _aggregation.ordinal();
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.ui.chart.AnomalyChartData#getType()
     */
    @Override
    public char getType() {
        return 'I';
    }

    @Override
    public String getUnit() {
        return null;
    }

    public String getTicker() {
        return _ticker;
    }

    public List<Metric> getMetrics() {
        return _metrics;
    }

    public boolean isModified() {
        return _modified;
    }

    /**
     * Last timestamp store in the databased from the time the data was last loaded
     */
    public long getLastDbTimestamp() {
        return _lastDbTimestamp;
    }

    /**
     * The anomalous metric types
     */
    public EnumSet<MetricType> getAnomalousMetrics() {
        return MetricType.fromMask(_anomalousMetrics);
    }
}
