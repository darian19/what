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

package com.YOMPsolutions.YOMP.mobile.chart;

import com.YOMPsolutions.YOMP.mobile.R;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.ui.chart.AnomalyChartView;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentActivity;
import android.support.v4.content.LocalBroadcastManager;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;


/**
 * This {@link Fragment} is the base to the metric and instance anomaly chart
 * fragments. It will display the anomaly bar chart, the metric/instance name
 * and the last date shown on the chart unless it is the current time.
 * <p/>
 * Subclasses should implement {@link #getResources()} returning the XML layout
 * resource ID to load as the root view of this fragment.
 * <p/>
 * The layout must include {@link com.numenta.core.ui.chart.AnomalyChartView} for the chart, a
 * {@link TextView} for the display name (@id/name) and a {@link TextView} for
 * the date (@id/date).
 * <p/>
 * The XML layout should look like this one:
 * <p/>
 * <pre>
 * {@code
 * <?xml version="1.0" encoding="utf-8"?>
 * <LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:orientation="vertical" >
 *  <FrameLayout android:orientation="horizontal" >
 *    <TextView android:id="@+id/name" android:gravity="left" />
 *    <TextView android:id="@+id/date" android:visibility="gone" android:layout_gravity="right"/>
 *  </FrameLayout>
 *     <com.numenta.core.ui.chart.AnomalyChartView
 *         android:id="@+id/anomaly_chart_view"
 *         style="@style/InstanceAnomalyChart.Chart" />
 * </LinearLayout>
 * }
 * </pre>
 *
 */
public abstract class AbstractAnomalyChartFragment extends Fragment {
    public static final String EXTRA_TYPE = "com.numenta.core.ui.chart.type";
    public static final String EXTRA_AGGREGATION = "com.numenta.core.ui.chart.aggregation";
    public static final String EXTRA_ID = "com.numenta.core.ui.chart.id";
    private final BroadcastReceiver _metricDataChangedReceiver;
    protected AnomalyChartData _chartData;
    private AsyncTask<AnomalyChartData, Void, AnomalyChartData> _chartLoadTask;
    private SimpleDateFormat _sdf;
    private final BroadcastReceiver _annotationChangedReceiver;
    private boolean _frozen;
    private long _selectedTimestamp;

    public AbstractAnomalyChartFragment() {
        super();
        _selectedTimestamp = -1;
        // Listen to MetricData changes
        _metricDataChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(final Context context, final Intent intent) {
                update();
            }
        };
        // Listen to Annotations changes
        _annotationChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(final Context context, final Intent intent) {
                update();
            }
        };
    }

    /**
     * Override this method to return the resource ID for an XML layout resource
     * to load as the root view of this {@link Fragment}.
     * <p/>
     * The layout must include {@link com.numenta.core.ui.chart.AnomalyChartView} for the chart, a
     * {@link TextView} for the display name (@id/name) and a {@link TextView}
     * for the date (@id/date).
     * <p/>
     * The XML layout should look like this one:
     * <p/>
     * <pre>
     * {@code
     * <?xml version="1.0" encoding="utf-8"?>
     * <LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:orientation="vertical" >
     *  <FrameLayout android:orientation="horizontal" >
     *    <TextView android:id="@+id/name" android:gravity="left" />
     *    <TextView android:id="@+id/date" android:visibility="gone" android:layout_gravity="right"/>
     *  </FrameLayout>
     *  <com.numenta.core.ui.chart.AnomalyChartView android:id="@+id/anomaly_chart_view"
     *                      style="@style/InstanceAnomalyChart.Chart" />
     * </LinearLayout>
     * }
     * </pre>
     */
    protected abstract int getResourceView();

    @Override
    public View onCreateView(final LayoutInflater inflater, final ViewGroup container,
                             final Bundle savedInstanceState) {
        final View view = inflater.inflate(getResourceView(), container, false);
        view.setTag(this);
        view.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(final View v) {
                performClick(v);
            }
        });
        view.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                return performLongClick(v);
            }
        });
        this._sdf = new SimpleDateFormat(getString(R.string.date_format_chart),
                Locale.getDefault());

        return view;
    }

    /**
     * Called when a view has been clicked.
     *
     * @param view The view that was clicked.
     */
    public void performClick(final View view) {
        goBack();
    }

    public void goBack() {
        final FragmentActivity activity = getActivity();
        if (activity != null && !activity.isTaskRoot()) {
            final Intent data = new Intent();
            if (_chartData != null) {
                data.putExtra(EXTRA_TYPE, _chartData.getType());
                data.putExtra(EXTRA_ID, _chartData.getId());
                data.putExtra(EXTRA_AGGREGATION, _chartData.getAggregation());
            }

            activity.setResult(Activity.RESULT_OK, data);
            // Go Back
            activity.finish();
        }
    }

    /**
     * Called when a view has been clicked and held.
     *
     * @param view The view that was clicked
     *
     * @return true if the callback consumed the long click, false otherwise.
     */
    public boolean performLongClick(final View view) {
        return false;
    }

    /**
     * Sets the data to plot
     *
     * @param data
     */
    public void setChartData(final AnomalyChartData data) {
        if (_chartData != null && _chartData.equals(data)) {
            return;
        }
        _chartData = data;
        update();
    }

    /**
     * Clear chart data
     */
    public void clearData() {
        setChartData(null);
    }

    public AnomalyChartView getBarChart() {
        final View layout = getView();
        if (layout == null) {
            return null;
        }
        return (AnomalyChartView) layout.findViewById(R.id.anomaly_chart_view);
    }

    /**
     * Update the {@link com.numenta.core.ui.chart.AnomalyChartView} with the contents of
     * the current {@link com.numenta.core.ui.chart.AnomalyChartData}, loading the data
     * from the database if necessary.
     *
     * @see #setChartData(AnomalyChartData)
     */
    public void update() {
        final View layout = getView();
        if (layout == null) {
            return;
        }

        // Update Chart
        final AnomalyChartView chart = getBarChart();
        if (chart == null) {
            return;
        }

        // Check if we have the data already
        if (_chartData != null && _chartData.hasData()) {
            updateName(layout, _chartData);
            updateDate(layout, _chartData);
            updateUnit(layout, _chartData);
            chart.setData(_chartData.getData());
            chart.setFlags(_chartData.getAnnotations());
            chart.setSelectedTimestamp(getSelectedTimestamp());
        } else if (!_frozen) {
            if (_chartLoadTask != null) {
                // Make sure to cancel previous running task
                _chartLoadTask.cancel(true);
            }
            if (_chartData == null) {
                return;
            }
            // Load data in the background
            _chartLoadTask = new AsyncTask<AnomalyChartData, Void, AnomalyChartData>() {
                @Override
                protected void onPostExecute(final AnomalyChartData result) {
                    if (isCancelled()) {
                        return;
                    }
                    updateName(layout, result);
                    updateDate(layout, result);
                    updateUnit(layout, result);
                    chart.setData(result.getData());
                    chart.setFlags(result.getAnnotations());
                    chart.setSelectedTimestamp(getSelectedTimestamp());
                }

                @Override
                protected AnomalyChartData doInBackground(
                        final AnomalyChartData... params) {
                    if (isCancelled()) {
                        return null;
                    }
                    // Query database for aggregated values
                    final AnomalyChartData data = params[0];
                    data.load();
                    return data;
                }
            }.execute(_chartData);
        }
    }

    protected void updateName(final View parent, final AnomalyChartData data) {
        final TextView textView = (TextView) parent.findViewById(R.id.name);
        if (textView != null) {
            final CharSequence oldName = textView.getText();
            if (data == null) {
                textView.setText(null);
                textView.setSelected(false);
            } else if (!oldName.equals(data.getName())) {
                textView.setText(data.getName());
                textView.setSelected(true);
            }
            parent.forceLayout();
        }
    }

    protected void updateDate(final View parent, final AnomalyChartData data) {
        final TextView dateView = (TextView) parent.findViewById(R.id.date);
        if (dateView != null) {
            if (data == null) {
                dateView.setVisibility(View.GONE);
            } else {
                Date endDate = data.getEndDate();
                if (endDate != null) {
                    dateView.setVisibility(View.VISIBLE);
                    dateView.setText(_sdf.format(data.getEndDate()));
                } else {
                    dateView.setVisibility(View.GONE);
                }
            }
            parent.forceLayout();
        }
    }

    protected void updateUnit(final View parent, final AnomalyChartData data) {
        final TextView text = (TextView) parent.findViewById(R.id.metric_unit);
        if (text != null) {
            if (data == null) {
                text.setVisibility(View.GONE);
            } else {
                text.setVisibility(View.VISIBLE);
                text.setText(data.getUnit());
            }
            parent.forceLayout();
        }
    }

    @Override
    public void setUserVisibleHint(final boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            show();
        }
    }

    @Override
    public void onPause() {
        super.onPause();
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _metricDataChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _annotationChangedReceiver);
    }

    @Override
    public void onResume() {
        super.onResume();
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _metricDataChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_DATA_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _annotationChangedReceiver,
                new IntentFilter(DataSyncService.ANNOTATION_CHANGED_EVENT));
        if (_chartData != null) {
            _chartData.clear();
            update();
        }
    }

    @Override
    public void onStop() {
        super.onStop();
        if (_chartLoadTask != null) {
            _chartLoadTask.cancel(true);
        }
    }

    private void show() {
        update();
    }

    /**
     * Freeze the data, preventing it from being loaded from the database upon update.
     * This is useful when updating the chart with in-memory data manually.
     *
     * @see #unfreeze()
     */
    public void freeze() {
        _frozen = true;
    }

    /**
     * Unfreeze the data, allowing it to be loaded from the database upon update.
     *
     * @see #freeze()
     */
    public void unfreeze() {
        _frozen = false;
    }

    /**
     * Set the current selected timestamp
     *
     * @param timestamp
     */
    public void setSelectedTimestamp(long timestamp) {
        _selectedTimestamp = timestamp;
        update();
    }

    /**
     * Returns the current selected timestamp
     */
    public long getSelectedTimestamp() {
        return _selectedTimestamp;
    }
}
