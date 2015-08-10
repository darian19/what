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

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.support.v4.content.LocalBroadcastManager;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.metric.MetricListFragment;
import com.numenta.core.service.DataSyncService;

public class InstanceDetailPageFragment extends Fragment {
    private InstanceAnomalyChartData _chartData;
    // Event listeners
    private final BroadcastReceiver _metricDataChangedReceiver;
    private AsyncTask<InstanceAnomalyChartData, Void, Void> _instanceLoadTask;
    private final BroadcastReceiver _annotationChangedReceiver;

    public InstanceDetailPageFragment() {

        _metricDataChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                reloadChartData();
            }
        };
        _annotationChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                reloadChartData();
            }
        };
    }

    public void setRowData(InstanceAnomalyChartData row) {
        if (_chartData != null && _chartData.equals(row)) {
            return;
        }
        if (_instanceLoadTask != null) {
            _instanceLoadTask.cancel(true);
            _instanceLoadTask = null;
        }

        _chartData = row;
        updateRowData();
    }

    void updateServerHeader() {
        if (_chartData == null) {
            return;
        }
        View view = getView();
        if (view == null) {
            return;
        }

        // Update server header
        View instanceChartView = view.findViewById(R.id.instance_anomaly_chart);
        InstanceAnomalyChartFragment chartFrag = (InstanceAnomalyChartFragment) instanceChartView
                .getTag();
        chartFrag.clearData();
        chartFrag.setChartData(_chartData);
    }

    public void updateRowData() {
        if (_chartData == null) {
            return;
        }
        View view = getView();
        if (view == null) {
            return;
        }
        _chartData.setEndDate(null);
        updateServerHeader();

        // Update Metric List
        View list = view.findViewById(android.R.id.list);
        MetricListFragment metricList = (MetricListFragment) list.getTag();
        metricList.setAggregation(_chartData.getAggregation());
        metricList.setInstanceId(_chartData.getId());

    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_instance_detail_page, container, false);
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

    private void reloadChartData() {
        if (_instanceLoadTask != null) {
            _instanceLoadTask.cancel(true);
            _instanceLoadTask = null;
        }

        if (_chartData != null) {
            _instanceLoadTask = new AsyncTask<InstanceAnomalyChartData, Void, Void>() {
                @Override
                protected Void doInBackground(InstanceAnomalyChartData... params) {
                    InstanceAnomalyChartData chartData = params[0];
                    if (chartData != null) {
                        if (isCancelled())
                            return null;
                        chartData.load();
                    }
                    return null;
                }

                @Override
                protected void onPostExecute(Void result) {
                    _instanceLoadTask = null;
                    updateServerHeader();
                }
            }.execute(_chartData);
        }
    }

    private void hide() {
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _metricDataChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _annotationChangedReceiver);
    }

    private void show() {
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _metricDataChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_DATA_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _annotationChangedReceiver,
                new IntentFilter(DataSyncService.ANNOTATION_CHANGED_EVENT));
        updateRowData();
    }

    @Override
    public void onResume() {
        super.onResume();
        show();
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.Fragment#onPause()
     */
    @Override
    public void onPause() {
        super.onPause();
        hide();
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.Fragment#onStop()
     */
    @Override
    public void onStop() {
        super.onStop();
        if (_instanceLoadTask != null) {
            _instanceLoadTask.cancel(true);
            _instanceLoadTask = null;
        }
    }
}
