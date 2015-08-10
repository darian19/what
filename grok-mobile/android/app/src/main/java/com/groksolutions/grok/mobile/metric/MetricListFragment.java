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
import com.YOMPsolutions.YOMP.mobile.chart.AbstractAnomalyChartFragment;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Metric;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.ui.chart.AnomalyChartData;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.ListFragment;
import android.support.v4.content.LocalBroadcastManager;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ListView;

import java.util.List;

/**
 * This Fragment is responsible for displaying the metric list. The list item is
 * composed of the metric name, notification icon and combined anomaly chart
 * aggregated by Hour, Day or Week.
 */
public class MetricListFragment extends ListFragment {

    static final String TAG = MetricListFragment.class.getCanonicalName();

    private static final int METRIC_DETAIL_REQUEST = 1;

    // Event listeners
    private final BroadcastReceiver _metricDataChangedReceiver;
    private final BroadcastReceiver _metricChangedReceiver;

    AggregationType _aggregation;
    private MetricListAdapter _listAdapter;
    private String _instanceId;

    private AsyncTask<Void, Void, List<Metric>> _metricLoadTask;

    private final BroadcastReceiver _annotationChangedReceiver;

    public MetricListFragment() {
        _metricDataChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateMetricData();
            }
        };
        _metricChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateMetricList();
            }
        };
        _annotationChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateMetricData();
            }
        };
    }

    /**
     * Refresh Metric List with contents from the database
     */
    void updateMetricList() {
        if (_listAdapter != null && _instanceId != null) {
            if (_metricLoadTask != null) {
                _listAdapter.notifyDataSetChanged();
                _metricLoadTask.cancel(true);
            }

            _metricLoadTask = new AsyncTask<Void, Void, List<Metric>>() {
                @Override
                protected void onPostExecute(List<Metric> metrics) {
                    _listAdapter.setNotifyOnChange(false);
                    _listAdapter.clear();
                    for (Metric metric : metrics) {
                        _listAdapter.add(new MetricAnomalyChartData(metric, _aggregation));
                    }
                    _listAdapter.sort(MetricAnomalyChartData.SORT_BY_NAME);
                    _listAdapter.notifyDataSetChanged();
                }

                @Override
                protected List<Metric> doInBackground(Void... params) {
                    if (isCancelled())
                        return null;
                    return YOMPApplication.getDatabase().getMetricsByInstanceId(_instanceId);
                }

                /*
                 * (non-Javadoc)
                 * @see android.os.AsyncTask#onCancelled()
                 */
                @Override
                protected void onCancelled() {
                    if (_listAdapter != null)
                        _listAdapter.notifyDataSetChanged();
                }
            }.execute();
        }
    }

    /**
     * Refresh Metric data with contents from the database
     */
    void updateMetricData() {
        if (_listAdapter != null && !_listAdapter.isEmpty()) {
            for (int i = 0, count = _listAdapter.getCount(); i < count; i++) {
                AnomalyChartData metricData = _listAdapter.getItem(i);
                // TODO: Delete only changed metric
                metricData.clear();
            }
            _listAdapter.notifyDataSetChanged();
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
            Bundle savedInstanceState) {
        View root = super.onCreateView(inflater, container, savedInstanceState);
        // Attach fragment to list view
        View list = root.findViewById(android.R.id.list);
        list.setTag(this);
        return root;
    }

    @Override
    public void onResume() {
        super.onResume();
        updateMetricList();
        updateMetricData();

        // Attach event listeners
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _metricDataChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_DATA_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _annotationChangedReceiver,
                new IntentFilter(DataSyncService.ANNOTATION_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(_metricChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_CHANGED_EVENT));
    }

    @Override
    public void onPause() {
        super.onPause();
        // Remove event listeners
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _metricDataChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(_metricChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _annotationChangedReceiver);
    }

    @Override
    public void onAttach(Activity activity) {
        super.onAttach(activity);

        // Create metric list adapter and refresh its contents from the database
        _listAdapter = new MetricListAdapter(getActivity());
        setListAdapter(_listAdapter);
        updateMetricList();
    }

    @Override
    public void onListItemClick(ListView list, View item, int position, long id) {
        MetricAnomalyChartData metric = (MetricAnomalyChartData) getListAdapter().getItem(position);
        // Show detail page
        Intent metricDetail = new Intent(getActivity(), MetricDetailActivity.class);
        metricDetail.putExtra(MetricDetailActivity.EXTRA_METRIC, metric.getMetric().getId());
        startActivityForResult(metricDetail, METRIC_DETAIL_REQUEST);
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.Fragment#onCreate(android.os.Bundle)
     */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // TODO Auto-generated method stub
        super.onCreate(savedInstanceState);
    }

    public void setAggregation(AggregationType aggregation) {
        this._aggregation = aggregation;
    }

    public void setInstanceId(String instanceId) {
        this._instanceId = instanceId;
        updateMetricList();
        updateMetricData();
    }

    @Override
    public void onStop() {
        super.onStop();
        if (_metricLoadTask != null) {
            if (_listAdapter != null) {
                _listAdapter.notifyDataSetChanged();
            }
            _metricLoadTask.cancel(true);
        }
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.Fragment#onActivityResult(int, int,
     * android.content.Intent)
     */
    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {

        switch (requestCode) {
            case MetricListFragment.METRIC_DETAIL_REQUEST:
                if (resultCode == Activity.RESULT_OK) {
                    // Check if clicked on "InstanceAnomalyChartFragment"
                    char type = data.getCharExtra(AbstractAnomalyChartFragment.EXTRA_TYPE, ' ');
                    if (InstanceAnomalyChartData.CHART_TYPE == type) {
                        // If clicked on instance chart then close this activity
                        // and
                        // go back to instance list
                        if (isAdded()) {
                            getActivity().finish();
                        }
                    }
                }
                break;

            default:
                break;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }
}
