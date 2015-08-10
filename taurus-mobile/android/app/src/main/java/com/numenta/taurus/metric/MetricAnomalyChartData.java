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

package com.numenta.taurus.metric;

import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Metric;
import com.numenta.core.service.YOMPException;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.TaurusDatabase;
import com.numenta.taurus.service.TaurusClient;

import java.io.IOException;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.ListIterator;
import java.util.TreeMap;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import static com.numenta.core.utils.DataUtils.METRIC_DATA_INTERVAL;
import static com.numenta.core.utils.DataUtils.MILLIS_PER_DAY;
import static com.numenta.core.utils.DataUtils.MILLIS_PER_HOUR;

/**
 * Metric data for each row in the list
 */
public class MetricAnomalyChartData implements AnomalyChartData, Serializable {

    private static final long serialVersionUID = -2538370060333880050L;

    private static final String TAG = MetricAnomalyChartData.class.getSimpleName();

    private final Metric _metric;

    // The right most date shown on the chart
    private volatile long _endDate;

    // Cached last date from database
    private volatile long _lastTimestamp;

    // Visible anomaly scores
    private List<Pair<Long, Float>> _data;

    // Anomalous data points for the visible data
    private Pair<Integer, Float>[] _anomalies;

    // Visible raw metric data
    private float[] _rawData;

    // Whether or not to collapse market closed hours
    private boolean _collapsed;

    // Cached collapsed metric raw data
    private float[] _collapsedData;

    // Cached collapsed anomalies
    private Pair<Integer, Float>[] _collapsedAnomalies;

    // All raw metric data for the whole 2 weeks
    private float[] _allRawData;

    // All Anomalies for the whole 2 weeks
    private List<Pair<Long, Float>> _allAnomalies;

    // Milliseconds per bar
    private static final long BAR_INTERVAL = TaurusApplication.getAggregation().milliseconds();

    // Used to control data access from multiple threads
    private final ReentrantReadWriteLock _lock = new ReentrantReadWriteLock();
    private final Lock _readLock = _lock.readLock();
    private final Lock _writeLock = _lock.writeLock();

    /**
     * Construct a new chart data for the given metric and selected date
     *
     * @param metric  The metric to load data from
     * @param endDate Load data up to this date
     */
    public MetricAnomalyChartData(Metric metric, long endDate) {
        this._metric = metric;
        this._endDate = endDate;
    }

    @Override
    public String getId() {
        return _metric == null ? null : _metric.getId();
    }

    /**
     * {@inheritDoc}
     *
     * NOTE: For Taurus, the metric display name is stored in the "userInfo" object
     */
    @Override
    public String getName() {
        // For Taurus, the metric display name is stored in the "userInfo" object
        return _metric == null ? null : _metric.getUserInfo("metricTypeName");
    }

    @Override
    public AggregationType getAggregation() {
        return TaurusApplication.getAggregation();
    }

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
     * Get the anomalous data points.
     *
     * @see #computeAnomalies()
     * @see #computeCollapsed()
     */
    public Pair<Integer, Float>[] getAnomalies() {
        _readLock.lock();
        try {
            return _collapsed ? _collapsedAnomalies : _anomalies;
        } finally {
            _readLock.unlock();
        }
    }

    private void refreshData() {
        if (_allAnomalies != null && !_allAnomalies.isEmpty()
                && _allRawData != null && _allRawData.length != 0) {
            computeDataForCurrentPeriod();
            computeAnomalies();
            computeCollapsed();
        }
    }

    /**
     * Compute data for the current period. The current period is defined by the number
     * of bars and the current end date
     */
    private void computeDataForCurrentPeriod() {
        // Compute chart data returned by #getData()
        final int bars = TaurusApplication.getTotalBarsOnChart();
        int size = _allAnomalies.size();

        // Calculate end date index
        long idx = Math.max(size - (_lastTimestamp - _endDate) / BAR_INTERVAL - bars, 0);
        _data = new ArrayList<Pair<Long, Float>>(
                _allAnomalies.subList((int) idx, (int) Math.min(idx + bars, size)));

        // Compute raw data returned by #getRawData()
        size = (int) (bars * BAR_INTERVAL / METRIC_DATA_INTERVAL);
        _rawData = new float[size];
        idx = Math.max(0,
                _allRawData.length - (_lastTimestamp - _endDate) / METRIC_DATA_INTERVAL - size - 1);
        System.arraycopy(_allRawData, (int) idx, _rawData, 0, size);
    }

    /**
     * Compute anomalous data points.
     *
     * The result is a {@link com.numenta.core.utils.Pair} where the first value contains the index
     * of the "rawData" values whose anomaly score is "yellow" or "red", the second  value contains
     * the anomaly score
     *
     * @see com.numenta.taurus.TaurusApplication#getRedBarFloor()
     * @see com.numenta.taurus.TaurusApplication#getYellowBarFloor()
     * @see #getRawData()
     * @see #getAnomalies()
     */
    private void computeAnomalies() {
        ArrayList<Pair<Integer, Float>> result = new ArrayList<Pair<Integer, Float>>();

        final long startDate = _data.get(0).first;
        float value;
        for (Pair<Long, Float> point : _data) {
            if (point.second != null) {
                // Match log scale used by the anomaly charts
                value = (float) DataUtils.logScale(Math.abs(point.second));
                // Check values for greater or equals to "yellow"
                if (value >= TaurusApplication.getYellowBarFloor()) {
                    int idx = (int) (point.first - startDate) / METRIC_DATA_INTERVAL;
                    result.add(new Pair<Integer, Float>(idx, value));
                }
            }
        }
        _anomalies = result.toArray(new Pair[result.size()]);
    }

    /**
     * Compute collapsed data based on the default market calendar and data range
     *
     * <p>This method will compute the collapsed raw metric data and collapsed anomalies for the
     * market open hours</p>
     *
     * <p>The collapse raw metric data will be separated by one "empty bar". The number of points
     * per bar used to separate the raw metric data is determined by the aggregation type, for
     * example if the aggregation type is {@link com.numenta.core.data.AggregationType#Day}(60 min)
     * then each market period will be separated by 12 empty points (60 min/5 min)
     * </p>
     *
     * <p>The resulting arrays will be layered together on a {@link com.numenta.core.ui.chart.LineChartView}</p>
     *
     * @see TaurusApplication#getMarketCalendar()
     * @see com.numenta.taurus.data.MarketCalendar#getClosedHoursForPeriod
     * @see #getAnomalies()
     */
    private void computeCollapsed() {
        if (!_collapsed
                || _allAnomalies == null || _allAnomalies.isEmpty()
                || _allRawData == null || _allRawData.length == 0) {
            return;
        }
        long time;
        final long msecsPerBar = getAggregation().milliseconds();
        final int bars = TaurusApplication.getTotalBarsOnChart();

        // Total number of data points per anomaly bar
        final long pointsPerBar = msecsPerBar / METRIC_DATA_INTERVAL;

        ArrayList<Pair<Integer, Float>> anomalies = new ArrayList<Pair<Integer, Float>>();

        // Clear all data values
        int size = (int) (bars * msecsPerBar / METRIC_DATA_INTERVAL);
        _collapsedData = new float[size];
        Arrays.fill(_collapsedData, Float.NaN);
        _collapsedAnomalies = null;

        // Calculate end date index
        int endIdx = (int) (_allAnomalies.size() - (_lastTimestamp - _endDate) / msecsPerBar);
        endIdx = Math.max(0, endIdx);

        // Compute collapsed data based on the default market calendar and data range
        final long endDate = _allAnomalies.get(Math.min(endIdx, _allAnomalies.size() - 1)).first;
        final long startDate = _allAnomalies.get(0).first;
        final List<Pair<Long, Long>> closedHours = TaurusApplication.getMarketCalendar()
                .getClosedHoursForPeriod(startDate, endDate);

        // Traverse the data backwards, from most recent first
        ListIterator<Pair<Long, Float>> dataIterator = _allAnomalies.listIterator(endIdx);
        ListIterator<Pair<Long, Long>> closedIterator = closedHours
                .listIterator(closedHours.size());

        // First closed period
        Pair<Long, Long> closed = closedIterator.hasPrevious() ? closedIterator.previous() : null;
        boolean closedPeriod = false;
        while (size > 0 && dataIterator.hasPrevious()) {
            Pair<Long, Float> value = dataIterator.previous();
            // Add interval to time to make sure the range fall into period
            time = value.first + METRIC_DATA_INTERVAL;
            // Check if data falls into closed period
            if (closed != null) {
                if (time >= closed.first && time <= closed.second) {
                    closedPeriod = true;
                    // Get next data value
                    continue;
                } else if (time < closed.first) {
                    // Get next closed period
                    closed = closedIterator.hasPrevious() ? closedIterator.previous() : null;
                }
            }
            // Check if we have a closed period
            if (closedPeriod) {
                // Skip closed period
                size -= pointsPerBar;
                closedPeriod = false;
            }
            // Add raw value
            int idx = (int) ((value.first - startDate) / METRIC_DATA_INTERVAL
                    + pointsPerBar) - 1;
            for (int i = 0; i < pointsPerBar; i++) {
                if (size > 0) {
                    size--;
                    _collapsedData[size] = _allRawData[idx - i];
                } else {
                    break;
                }
            }
            // Add collapsed anomaly
            if (value.second != null) {
                // Match log scale used by the anomaly charts
                float logScale = (float) DataUtils.logScale(Math.abs(value.second));
                // Check values for greater or equals to "yellow"
                if (logScale >= TaurusApplication.getYellowBarFloor()) {
                    anomalies.add(new Pair<Integer, Float>(size, logScale));
                }
            }
        }
        if (!anomalies.isEmpty()) {
            _collapsedAnomalies = anomalies.toArray(new Pair[anomalies.size()]);
        }
    }

    /**
     * Metric raw data for the period represented by this chart.
     * <p>
     * The period is determined by the {@link #getEndDate()}, {@link #getAggregation()} and
     * {@link com.numenta.taurus.TaurusApplication#getTotalBarsOnChart()}.
     * </p>
     *
     * For Example:
     * <p>
     * If the aggregation is set to <b>{@link AggregationType#Hour}</b> and the chart is configured
     * to use <b>24</b> bars then the period represented by this chart will be 24 hours from the
     * <b>{@link #getEndDate()}</b> inclusive. At 5 minutes interval the total number of records
     * returned will be <code>24 * 60 / 5</code>.
     * </p>
     *
     * <p><b>NOTE: </b> Should be called after {@link #load()}
     * </p>
     *
     * @return Metric raw data for the period represented by this chart
     */
    public float[] getRawData() {
        _readLock.lock();
        try {
            if (_rawData != null) {
                int size = (int) (TaurusApplication.getTotalBarsOnChart() * BAR_INTERVAL
                        / DataUtils.METRIC_DATA_INTERVAL);
                float[] data = new float[size];
                if (_collapsed) {
                    if (_collapsedData != null) {
                        System.arraycopy(_collapsedData, _collapsedData.length - size, data, 0,
                                size);
                    }
                } else {
                    // Copy last 'size' raw values
                    System.arraycopy(_rawData, _rawData.length - size, data, 0, size);
                }
                return data;
            } else {
                return null;
            }
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public boolean hasData() {
        if (_readLock.tryLock()) {
            try {
                return _data != null && !_data.isEmpty();
            } finally {
                _readLock.unlock();
            }
        }
        return false;
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
            _rawData = null;
            _collapsedData = null;
            _collapsedAnomalies = null;
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
        if (getId() == null) {
            return false; // No metric
        }
        final TaurusDatabase database = TaurusApplication.getDatabase();
        if (database == null) {
            return false;
        }
        final long lastDBTimestamp = database.getLastTimestamp();
        if (_lastTimestamp == lastDBTimestamp) {
            return false; // No new data
        }

        _writeLock.lock();
        try {
            _lastTimestamp = lastDBTimestamp;
            // Make sure end date is valid
            if (_endDate <= 0) {
                _endDate = _lastTimestamp;
            }
            // Query database for aggregated values
            if (_metric != null) {
                try {
                    final int numOfDays = TaurusApplication.getNumberOfDaysToSync();
                    // Make sure to get the full last one hour bucket
                    final long to = _lastTimestamp + MILLIS_PER_HOUR;
                    // Get all scrollable data
                    final long from = to - numOfDays * MILLIS_PER_DAY;
                    final int size = numOfDays * MILLIS_PER_DAY / METRIC_DATA_INTERVAL;
                    _allRawData = new float[size];
                    Arrays.fill(_allRawData, Float.NaN);
                    _allAnomalies = new ArrayList<Pair<Long, Float>>();

                    // Aggregate anomalies hourly
                    final TreeMap<Long, Float> aggregated = new TreeMap<Long, Float>();

                    TaurusClient client = TaurusApplication.connectToTaurus();
                    if (client == null) {
                        // Failed to get connection to taurus
                        return false;
                    }
                    if (!client.isOnline()) {
                        return false; // Not connected
                    }
                    client.getMetricValues(getId(), new Date(from), new Date(to), true,
                            new TaurusClient.MetricValuesCallback() {
                                @Override
                                public boolean onData(String metricId, long timestamp, float value,
                                        float anomaly) {
                                    // Calculate data index based on timestamp
                                    int idx = (int) ((timestamp - from) / METRIC_DATA_INTERVAL);
                                    if (idx >= _allRawData.length) {
                                        idx = _allRawData.length - 1;
                                    }
                                    _allRawData[idx] = value;
                                    // Aggregate anomalies hourly using the max anomaly
                                    long hour = DataUtils.floorTo60minutes(timestamp);
                                    Float score = aggregated.get(hour);
                                    if (score == null || score < anomaly) {
                                        aggregated.put(hour, anomaly);
                                    }
                                    return true;
                                }
                            });

                    // Populate anomaly array for all scrollable period
                    for (long time = from; time < to; time += MILLIS_PER_HOUR) {
                        _allAnomalies.add(new Pair<Long, Float>(time, aggregated.get(time)));
                    }

                    // Refresh data
                    refreshData();
                } catch (IOException e) {
                    Log.e(TAG, "Failed to load metric data", e);
                } catch (YOMPException e) {
                    Log.e(TAG, "Failed to load metric data", e);
                }
            } else {
                clear();
            }
        } finally {
            _writeLock.unlock();
        }

        return true;
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
            if (_endDate != other._endDate) {
                return false;
            }
            _readLock.lock();
            try {
                return _data == other._data || (_data != null && _data.equals(other._data));
            } finally {
                _readLock.unlock();
            }
        }
        return false;
    }

    @Override
    public int hashCode() {
        return _metric != null ? _metric.hashCode() : 0;
    }

    public Metric getMetric() {
        return _metric;
    }

    /**
     * Set whether or not to collapse the time for this view. If {@code true} the view will
     * collapse the the time based on the current market calendar.
     *
     * @see com.numenta.taurus.TaurusApplication#getMarketCalendar()
     */
    public void setCollapsed(boolean collapsed) {
        if (_collapsed != collapsed) {
            _writeLock.lock();
            try {
                if (_collapsed != collapsed) {
                    _collapsed = collapsed;
                    if (_collapsed) {
                        computeCollapsed();
                    }
                }
            } finally {
                _writeLock.unlock();
            }
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
        long newDate = endDate == null ? 0 : endDate.getTime();
        if (newDate != _endDate) {
            _writeLock.lock();
            try {
                if (newDate != _endDate) {
                    _endDate = newDate;
                    refreshData();
                }
            } finally {
                _writeLock.unlock();
            }
        }
    }

    public long getEndTimestamp() {
        return _endDate;
    }

    /**
     * Return the start date for this chart
     */
    public long getStartTimestamp() {
        long endTime = _endDate;
        if (endTime <= 0) {
            endTime = System.currentTimeMillis();
            if (_readLock.tryLock()) {
                try {
                    if (_data != null && !_data.isEmpty()) {
                        endTime = _data.get(_data.size() - 1).first;
                    }
                } finally {
                    _readLock.unlock();
                }
            }
        }
        return endTime - BAR_INTERVAL * (TaurusApplication.getTotalBarsOnChart() - 1);
    }

    @Override
    public char getType() {
        return 'M';
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
        // Metrics do not support annotations
        return null;
    }

    @Override
    public float getRank() {
        return 0;
    }
}
