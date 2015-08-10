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
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.chart.AbstractAnomalyChartFragment;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartFragment;
import com.numenta.core.data.AggregationType;
import com.numenta.core.ui.chart.LineChartView;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Pair;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.database.Cursor;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.support.v4.view.GestureDetectorCompat;
import android.support.v4.view.ViewCompat;
import android.view.GestureDetector.OnDoubleTapListener;
import android.view.GestureDetector.OnGestureListener;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.View.OnTouchListener;
import android.view.ViewGroup;
import android.view.ViewParent;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

import static java.util.concurrent.TimeUnit.DAYS;
import static java.util.concurrent.TimeUnit.MILLISECONDS;

/**
 * This {@link Fragment} will display the {@link MetricAnomalyChartData} as the
 * <b>Metric Detail Page</b>.
 * <p>
 * The <b>Metric Detail Page</b> is composed of the
 * {@link InstanceAnomalyChartFragment} at the top section, <b>Metric Values
 * Chart</b> in the middle section followed by the
 * {@link MetricAnomalyChartFragment} at the bottom section.
 */
@SuppressLint("ClickableViewAccessibility")
public class MetricDetailFragment extends Fragment {

    /**
     * Handles date/time scrolling
     */
    final class GestureListener implements OnGestureListener {

        private final View _view;

        // Holds the initial timestamp.
        long _initialTimestamp;

        public GestureListener(View view) {
            this._view = view;
        }

        @Override
        public boolean onDown(MotionEvent event) {
            ViewCompat.postInvalidateOnAnimation(_lineChartView);
            _initialTimestamp = _currentTimestamp;
            return true;
        }

        @Override
        public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX,
                float velocityY) {
            return true;
        }

        @Override
        public void onLongPress(MotionEvent event) {
            // Close the view if the user 'Taps' on the anomaly chart
            if (_view != null) {
                if (_view.getTag() instanceof AbstractAnomalyChartFragment) {
                    AbstractAnomalyChartFragment frag = (AbstractAnomalyChartFragment) _view
                            .getTag();
                    frag.performLongClick(_view);
                }
            }
        }

        /**
         * Calculate the time interval between 2 events
         *
         * @param e1
         * @param e2
         * @return Time interval in milliseconds
         */
        private long getDistance(MotionEvent e1, MotionEvent e2) {
            final float x1 = e1.getX();
            final float x2 = e2.getX();
            final float distance = x1 - x2;
            int width = _lineChartView.getMeasuredWidth();
            int pixels = width / YOMPApplication.getTotalBarsOnChart();
            int scrolledBars = (int) (distance / pixels);
            // Scroll date by aggregation interval
            long interval = _metricAnomalyData.getAggregation().milliseconds();
            return interval * scrolledBars;
        }

        @Override
        public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX,
                float distanceY) {

            List<Pair<Long, Float>> metricData = _metricAnomalyData.getData();
            if (metricData != null) {
                // Scrolls from the initial timestamp to the distance between
                // the events
                Date scrolledDate = new Date(_initialTimestamp + getDistance(e1, e2));
                scrolledDate = scrollTo(scrolledDate);
                Activity activity = getActivity();
                if (activity instanceof MetricDetailActivity) {
                    ((MetricDetailActivity) activity).setCurrentDate(scrolledDate);
                }
            }
            return true;
        }

        @Override
        public void onShowPress(MotionEvent event) {
            // Do not scale the chart while scrolling
            _lineChartView.setRefreshScale(false);
        }

        @Override
        public boolean onSingleTapUp(MotionEvent event) {
            return false;
        }
    }

    final class TouchListener implements OnTouchListener, OnDoubleTapListener {
        // Attach gesture detector to values chart handling scrolling.
        final GestureDetectorCompat _gestureDetector;

        // The current view
        View _view;

        public TouchListener(View view) {
            _view = view;
            _gestureDetector = new GestureDetectorCompat(getActivity(),
                    new GestureListener(_view));
            // Handle 'Tap' events
            _gestureDetector.setOnDoubleTapListener(this);
        }

        @Override
        public boolean onTouch(View v, MotionEvent event) {

            // Prevent ViewPager from intercepting touch events
            ViewParent parent = v.getParent();
            // Prevent ViewPager from intercepting touch events
            parent.requestDisallowInterceptTouchEvent(true);
            switch (event.getAction()) {
                case MotionEvent.ACTION_MOVE:
                    // Do not scale the chart while scrolling
                    _lineChartView.setRefreshScale(false);
                    break;
                case MotionEvent.ACTION_UP:
                    // Done scrolling, refresh the chart scale
                    _lineChartView.setRefreshScale(true);
                    ViewCompat.postInvalidateOnAnimation(_lineChartView);
                    break;
                case MotionEvent.ACTION_CANCEL:
                    // Done scrolling, refresh the chart scale
                    _lineChartView.setRefreshScale(true);
                    ViewCompat.postInvalidateOnAnimation(_lineChartView);
                    // Allow ViewPager to intercept touch events
                    // parent.requestDisallowInterceptTouchEvent(false);
                    break;
                default:
                    break;
            }
            this._view = v;
            // Detect scroll gestures on the metric detail chart
            return _gestureDetector.onTouchEvent(event);
        }

        @Override
        public boolean onSingleTapConfirmed(MotionEvent e) {
            // Close the view if the user 'Taps' on the anomaly chart
            if (_view != null) {
                if (_view.getTag() instanceof AbstractAnomalyChartFragment) {
                    AbstractAnomalyChartFragment frag = (AbstractAnomalyChartFragment) _view
                            .getTag();
                    frag.performClick(_view);
                    return true;
                }
            }
            return false;
        }

        @Override
        public boolean onDoubleTap(MotionEvent e) {
            return false;
        }

        @Override
        public boolean onDoubleTapEvent(MotionEvent e) {
            return false;
        }
    }

    private static final String TAG = MetricDetailFragment.class.getCanonicalName();
    private MetricAnomalyChartData _metricAnomalyData;
    private InstanceAnomalyChartData _instanceAnomalyData;
    private long _startTimestamp;
    private long _endTimestamp;
    private long _currentTimestamp;
    private LineChartView _lineChartView;
    private AsyncTask<Void, Void, float[]> _metricValueLoadTask;
    private static final int METRIC_DATA_INTERVAL = 5 * DataUtils.MILLIS_PER_MINUTE;

    /**
     * Default constructor. <strong>Every</strong> fragment must have an empty
     * constructor
     */
    public MetricDetailFragment() {
        // Empty
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        final View view = inflater.inflate(R.layout.fragment_metric_detail, container, false);

        _lineChartView = (LineChartView) view.findViewById(R.id.line_chart_view);
        _lineChartView.setOnTouchListener(new TouchListener(_lineChartView));
        View instanceChartView = view.findViewById(R.id.instance_anomaly_chart);
        instanceChartView.setOnTouchListener(new TouchListener(instanceChartView));
        View metricChartView = view.findViewById(R.id.metric_anomaly_chart);
        metricChartView.setOnTouchListener(new TouchListener(metricChartView));
        view.setOnTouchListener(new TouchListener(view));

        return view;
    }

    public Date scrollTo(Date scrolledDate) {
        if (_metricAnomalyData == null) {
            Log.w(TAG, "Called MetricDetailFragment.scrollTo() with no metric anomaly data");
            return null;
        }
        Date newDate = null;
        List<Pair<Long, Float>> metricData = _metricAnomalyData.getData();
        if (metricData != null && !metricData.isEmpty()) {
            // Check if date is valid
            long timeWindow = YOMPApplication.getTotalBarsOnChart()
                    * _metricAnomalyData.getAggregation().milliseconds();
            if (scrolledDate == null || scrolledDate.getTime() >= _endTimestamp) {
                _currentTimestamp = _endTimestamp;
                _metricAnomalyData.setEndDate(null);
            } else if (scrolledDate.getTime() <= _startTimestamp + timeWindow) {
                _currentTimestamp = _startTimestamp + timeWindow;
                newDate = new Date(_currentTimestamp);
                _metricAnomalyData.setEndDate(newDate);
            } else {
                _currentTimestamp = scrolledDate.getTime();
                _metricAnomalyData.setEndDate(scrolledDate);
                newDate = scrolledDate;
            }

            // Update
            _metricAnomalyData.clear();
            update();
        } else {
            if (scrolledDate == null) {
                _currentTimestamp = _endTimestamp;
                _metricAnomalyData.setEndDate(null);
            } else {
                _currentTimestamp = scrolledDate.getTime();
                _metricAnomalyData.setEndDate(scrolledDate);
                newDate = scrolledDate;
            }
        }
        return newDate;
    }

    /**
     * Set the {@link MetricAnomalyChartData} to display. Calling this method
     * will cause the UI to update
     *
     * @param metricData
     */
    public void setMetricAnomalyData(MetricAnomalyChartData metricData) {
        _metricAnomalyData = metricData;
        _instanceAnomalyData = new InstanceAnomalyChartData(_metricAnomalyData.getInstanceId(),
                _metricAnomalyData.getAggregation());
        update();
    }

    /**
     * @return the metricAnomalyData
     */
    public MetricAnomalyChartData getMetricAnomalyData() {
        return this._metricAnomalyData;
    }

    float _metricValues[] = null;

    /**
     * Load the metric values for the given {@code metricId} for the time period
     * specified by the given {@code from} and {@code to} dates.
     *
     * @param metricId The metric to get the data from
     * @param from Start Date
     * @param to End Date
     * @return metric data
     */
    private float[] getMetricRawValues(String metricId, long from, long to) {
        if (_metricValues != null && from == _startTimestamp && to == _endTimestamp) {
            return _metricValues;
        }
        // Outside buffered range
        if (to > _endTimestamp) {

            // Calculate the maximum time window we keep in the database. From
            // the last known timestamp up to the maximum number of days we keep
            // in the local database.
            // This window will be used by the scroller.
            _endTimestamp = Math.max(to, YOMPApplication.getDatabase().getLastTimestamp());
            _startTimestamp = _endTimestamp - YOMPApplication.getNumberOfDaysToSync()
                    * DataUtils.MILLIS_PER_DAY;

            // Calculate result size based on the date range and time
            // interval
            int size = (int) (_endTimestamp - _startTimestamp) / METRIC_DATA_INTERVAL;
            _metricValues = new float[size];
            Arrays.fill(_metricValues, Float.NaN);
            YOMPDatabase YOMPdb = YOMPApplication.getDatabase();
            Cursor cursor = null;
            try {
                cursor = YOMPdb.getMetricData(metricId, new String[] {
                        "timestamp",
                        "metric_value"
                }, new Date(_startTimestamp), new Date(_endTimestamp), 0, 0);
                int i = 0;
                // Round timestamp to closest 5 minute interval
                long currentTimestamp = (_startTimestamp / METRIC_DATA_INTERVAL)
                        * METRIC_DATA_INTERVAL;

                // In the hour view, start from the end of the bar
                if (_metricAnomalyData.getAggregation() == AggregationType.Hour) {
                    currentTimestamp += METRIC_DATA_INTERVAL;
                }
                while (i < size) {
                    if (cursor.moveToNext()) {
                        long timestamp = cursor.getLong(0);
                        // Round timestamp to closest 5 minute interval
                        timestamp = (timestamp / METRIC_DATA_INTERVAL) * METRIC_DATA_INTERVAL;

                        while (currentTimestamp < timestamp && i < size) {
                            _metricValues[i++] = Float.NaN;
                            currentTimestamp += METRIC_DATA_INTERVAL;
                        }
                        currentTimestamp += METRIC_DATA_INTERVAL;
                        _metricValues[i++] = cursor.getFloat(1);
                    } else {
                        currentTimestamp += METRIC_DATA_INTERVAL;
                        _metricValues[i++] = Float.NaN;
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Error getting metric data", e);
            } finally {
                if (cursor != null) {
                    cursor.close();
                }
            }
        }

        long fromRounded = (from / METRIC_DATA_INTERVAL) * METRIC_DATA_INTERVAL;
        long toRounded = (to / METRIC_DATA_INTERVAL) * METRIC_DATA_INTERVAL;

        int start;
        // In the hour view, start from the end of the bar
        if (_metricAnomalyData.getAggregation() == AggregationType.Hour) {
            start = (int) Math.max(0, (fromRounded - _startTimestamp - METRIC_DATA_INTERVAL)
                    / METRIC_DATA_INTERVAL);
        } else {
            start = (int) Math.max(0, (fromRounded - _startTimestamp) / METRIC_DATA_INTERVAL);
        }
        int end = (int) Math.min(_metricValues.length, (toRounded - _startTimestamp)
                / METRIC_DATA_INTERVAL);

        return Arrays.copyOfRange(_metricValues, start, end);
    }

    /**
     * Update the UI with the data from {@link MetricAnomalyChartData}
     */
    private void update() {
        final Context context = getActivity();
        final View layout = getView();
        if (context != null && layout != null && _metricAnomalyData != null) {
            if (_metricValueLoadTask != null) {
                _metricValueLoadTask.cancel(true);
            }

            // Update Metric chart
            _metricValueLoadTask = new AsyncTask<Void, Void, float[]>() {
                @Override
                protected float[] doInBackground(Void... params) {

                    if (isCancelled())
                        return null;

                    // Load metric anomaly data
                    if (!_metricAnomalyData.load()) {
                        return null;
                    }
                    if (isCancelled())
                        return null;
                    List<Pair<Long, Float>> data = _metricAnomalyData.getData();
                    if (!_metricAnomalyData.hasData()) {
                        return null;
                    }

                    if (isCancelled())
                        return null;
                    // Load Instance Data
                    if (_instanceAnomalyData == null) {
                        _instanceAnomalyData = new InstanceAnomalyChartData(
                                _metricAnomalyData.getInstanceId(),
                                _metricAnomalyData.getAggregation());
                    }
                    _instanceAnomalyData.setEndDate(_metricAnomalyData.getEndDate());
                    if (isCancelled())
                        return null;
                    _instanceAnomalyData.load();

                    // Load Metric values data
                    // Set lower bounds of the chart based on the anomaly bar
                    // chart. Use the first bar as lower bound.
                    long from = data.get(0).first;

                    // Set upper bound to be the end date represented by the
                    // last bar.
                    long to = data.get(data.size() - 1).first;
                    _currentTimestamp = to;

                    // Add interval to date to get the end date of each bar
                    if (_metricAnomalyData.getAggregation() != AggregationType.Hour) {
                        to = to + _metricAnomalyData.getAggregation().milliseconds();
                    }
                    if (isCancelled())
                        return null;
                    return getMetricRawValues(_metricAnomalyData.getId(), from, to);
                }

                @Override
                protected void onPostExecute(float[] result) {

                    // Update instance anomaly chart
                    View instanceChartView = layout.findViewById(R.id.instance_anomaly_chart);
                    InstanceAnomalyChartFragment instanceChartFrag =
                            (InstanceAnomalyChartFragment) instanceChartView.getTag();
                    instanceChartFrag.clearData();
                    instanceChartFrag.setChartData(_instanceAnomalyData);

                    // Update metric anomaly chart
                    View metricChartView = layout.findViewById(R.id.metric_anomaly_chart);
                    MetricAnomalyChartFragment metricAnomalyChart =
                            (MetricAnomalyChartFragment) metricChartView.getTag();
                    metricAnomalyChart.clearData();
                    metricAnomalyChart.setChartData(_metricAnomalyData);

                    if (result == null || result.length < 2) {
                        return;
                    }
                    // Update metric value chart
                    _lineChartView.setData(result);
                    ViewCompat.postInvalidateOnAnimation(_lineChartView);
                }

            }.execute();
        }
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            show();
        } else {
            hide();
        }
    }

    private void hide() {
        // Do nothing
    }

    private void show() {
        MetricDetailActivity activity = (MetricDetailActivity) getActivity();
        Date date = activity.getCurrentDate();
        Date now = new Date();
        if (date != null) {
            if (_metricAnomalyData != null) {
                AggregationType aggregation = _metricAnomalyData.getAggregation();
                AggregationType oldAggregation = activity.getOldAggregation();

                // Round time to aggregation bucket
                long timestamp = (date.getTime() / aggregation.milliseconds())
                        * aggregation.milliseconds();
                date = new Date(timestamp);
                if (AggregationType.Hour.equals(aggregation)) {
                    // Scrolled to "Hour" view from anywhere.
                    // Round to the closest hour and move the current date to
                    // the middle of the time window.
                    timestamp = (timestamp / DataUtils.MILLIS_PER_HOUR) * DataUtils.MILLIS_PER_HOUR
                            + YOMPApplication.getTotalBarsOnChart()
                            * AggregationType.Hour.milliseconds() / 2;
                    date = new Date(timestamp);
                } else if (AggregationType.Day.equals(aggregation)) {
                    if (AggregationType.Week.equals(oldAggregation)) {
                        // Scrolled to the "Day" view from the "Week" view
                        timestamp += AggregationType.Week.milliseconds();
                        date = new Date(timestamp);
                    }
                    else if (AggregationType.Hour.equals(oldAggregation)) {
                        long maxDaySpan = MILLISECONDS.convert(
                                YOMPApplication.getNumberOfDaysToSync(), DAYS)
                                - AggregationType.Day.milliseconds()
                                * YOMPApplication.getTotalBarsOnChart();
                        if (now.getTime() - date.getTime() > maxDaySpan) {
                            date = new Date(now.getTime() - maxDaySpan);
                        }
                    }
                } else if (AggregationType.Week.equals(aggregation)) {
                    long maxWeekSpan = MILLISECONDS.convert(
                            YOMPApplication.getNumberOfDaysToSync(), DAYS)
                            - AggregationType.Week.milliseconds()
                            * YOMPApplication.getTotalBarsOnChart();
                    if (now.getTime() - date.getTime() > maxWeekSpan) {
                        date = new Date(now.getTime() - maxWeekSpan);
                    }
                }
            }
        }
        scrollTo(date);
        update();
    }

    @Override
    public void onStop() {
        super.onStop();
        if (_metricValueLoadTask != null) {
            _metricValueLoadTask.cancel(true);
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        if (getUserVisibleHint() && isAdded()) {
            show();
        }
    }
}
