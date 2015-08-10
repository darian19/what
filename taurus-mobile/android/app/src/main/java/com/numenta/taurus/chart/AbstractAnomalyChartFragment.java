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

package com.numenta.taurus.chart;

import com.numenta.core.service.DataSyncService;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.service.TaurusDataSyncService;

import android.app.Activity;
import android.app.Fragment;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
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
    private final BroadcastReceiver _instanceDataChangedReceiver;
    protected AnomalyChartData _chartData;
    private AsyncTask<AnomalyChartData, Void, AnomalyChartData> _chartLoadTask;
    private SimpleDateFormat _sdf;
    private BroadcastReceiver _annotationChangedReceiver;
    private long _selectedTimestamp;

    public AbstractAnomalyChartFragment() {
        super();
        _selectedTimestamp = -1;
        // Listen to InstanceData changes
        _instanceDataChangedReceiver = new BroadcastReceiver() {
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
        final Activity activity = getActivity();
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
        View view = getView();
        if (view != null) {
            return (AnomalyChartView) view.findViewById(R.id.anomaly_chart_view);
        }
        return null;
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
            updateDate(layout, _chartData);
            updateName(layout, _chartData);
            updateUnit(layout, _chartData);
            updateChart(chart, _chartData);
        } else {
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
                    if (isCancelled() || result == null) {
                        return;
                    }
                    updateName(layout, result);
                    updateDate(layout, result);
                    updateUnit(layout, result);
                    updateChart(chart, result);
                }

                @Override
                protected AnomalyChartData doInBackground(
                        final AnomalyChartData... params) {
                    if (isCancelled()) {
                        return null;
                    }
                    // Query database for aggregated values
                    final AnomalyChartData data = params[0];
                    if (data.load()) {
                        return data;
                    }
                    return null;
                }
            }.executeOnExecutor(TaurusApplication.getWorkerThreadPool(), _chartData);
        }
    }

    protected void updateChart(AnomalyChartView chart, AnomalyChartData data) {
        chart.setData(data.getData());
        chart.setSelectedTimestamp(getSelectedTimestamp());
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
                if (endDate != null && endDate.getTime() > 0) {
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
                _instanceDataChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _annotationChangedReceiver);
    }

    @Override
    public void onResume() {
        super.onResume();
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _instanceDataChangedReceiver,
                new IntentFilter(TaurusDataSyncService.INSTANCE_DATA_CHANGED_EVENT));
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
