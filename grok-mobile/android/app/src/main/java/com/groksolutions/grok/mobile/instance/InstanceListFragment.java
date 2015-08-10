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
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.SortOrder;
import com.YOMPsolutions.YOMP.mobile.annotation.AddAnnotationActivity;
import com.YOMPsolutions.YOMP.mobile.annotation.AnnotationListActivity;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.numenta.core.data.AggregationType;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.ui.chart.AnomalyChartView;
import com.numenta.core.utils.Log;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.ListFragment;
import android.support.v4.content.LocalBroadcastManager;
import android.view.ContextMenu;
import android.view.MenuItem;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ListAdapter;
import android.widget.ListView;

import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

/**
 * This Fragment is responsible for displaying the server list. The list item is
 * composed of the server name, notification icon and combined anomaly chart
 * aggregated by Hour, Day or Week.
 */
public class InstanceListFragment extends ListFragment {

    private static final String TAG = InstanceListFragment.class.getSimpleName();
    private InstanceListAdapter _listAdapter;
    private volatile SortOrder _sortOrder;
    private volatile boolean _sorting;
    private AggregationType _aggregation;

    // Event listeners
    private final BroadcastReceiver _metricDataChangedReceiver;
    private final BroadcastReceiver _metricChangedReceiver;
    private final BroadcastReceiver _annotationChangedReceiver;

    // Check if sort selection changed
    private final PropertyChangeListener _sortSelectionChangeListener = new PropertyChangeListener() {
        @Override
        public void propertyChange(PropertyChangeEvent event) {
            sort(false);
        }
    };

    private AsyncTask<Void, InstanceAnomalyChartData, Void> _metricLoadTask;

    /**
     * InstanceListFragment constructor
     */
    public InstanceListFragment() {
        // Listen for new metric data
        _metricDataChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateMetricData();
            }
        };
        // Listens for new metrics
        _metricChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateInstanceList();
            }
        };

        // Listen for annotations
        _annotationChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateMetricData();
            }
        };
    }

    /**
     * Refresh {@link ListAdapter} with new metric data if available
     */
    private void updateMetricData() {
        if (_listAdapter != null) {
            // Check if we are already updating the metric data from a previous
            // call
            if (_metricLoadTask != null && _metricLoadTask.getStatus() != AsyncTask.Status.FINISHED) {
                return;
            }
            // Background task for loading metric data
            _metricLoadTask = new AsyncTask<Void, InstanceAnomalyChartData, Void>() {
                @Override
                protected void onPostExecute(Void servers) {
                    if (isCancelled())
                        return;
                    // Force sort once done
                    sort(true);
                }

                @Override
                protected Void doInBackground(Void... params) {
                    // Get current list of metrics kept in the adapter.
                    ArrayList<InstanceAnomalyChartData> instances = new ArrayList<InstanceAnomalyChartData>();
                    synchronized (_listAdapter) {
                        for (int i = 0, count = _listAdapter.getCount(); i < count; i++) {
                            if (isCancelled())
                                return null;
                            instances.add(_listAdapter.getItem(i));
                        }
                    }
                    for (InstanceAnomalyChartData data : instances) {
                        if (isCancelled())
                            return null;
                        // Refresh the content of each metric and resort if the
                        // data was changed as we load the rest of the data.
                        // This partial resort is done in order to give the user
                        // some feedback as the rest of the data loads.
                        data.setEndDate(null);
                        if (data.load()) {
                            publishProgress(data);
                        }
                    }
                    return null;
                }

                @Override
                protected void onProgressUpdate(InstanceAnomalyChartData... data) {
                    if (isCancelled())
                        return;
                    // Partial resort
                    sort(true);
                }
            }.execute();
        }
    }

    /**
     * Sort the contents of the list based on {@link YOMPApplication#getSort()}
     *
     * @param force {@code true} to force the contents to be sorted, otherwise
     *              the contents will only sort if the current sort order is
     *              different than {@link YOMPApplication#getSort()}
     */
    private void sort(boolean force) {
        if (_sorting) {
            return;
        }
        synchronized (this) {
            if (_sorting) {
                return;
            }
            _sorting = true;
        }
        try {
            if (_listAdapter != null && !_listAdapter.isEmpty()
                    && (force || _sortOrder != YOMPApplication.getSort())) {
                _sortOrder = YOMPApplication.getSort();
                synchronized (_listAdapter) {
                    switch (_sortOrder) {
                        case Name:
                            _listAdapter.sort(InstanceAnomalyChartData.SORT_BY_NAME);
                            break;
                        default:
                            _listAdapter.sort(InstanceAnomalyChartData.SORT_BY_ANOMALY);
                            break;
                    }
                }
                _listAdapter.notifyDataSetChanged();
            }
        } finally {
            _sorting = false;
        }
    }

    /**
     * Refresh Instance List with contents from the database
     */
    private void updateInstanceList() {
        if (_listAdapter != null && _aggregation != null) {
            new AsyncTask<Void, Void, Set<String>>() {

                @Override
                protected Set<String> doInBackground(Void... params) {
                    return YOMPApplication.getDatabase().getAllInstances();
                }

                @Override
                protected void onPostExecute(Set<String> servers) {
                    if (isCancelled()) {
                        return;
                    }
                    boolean updated = false;
                    HashSet<String> existing = new HashSet<String>();
                    HashSet<InstanceAnomalyChartData> deleted = new HashSet<InstanceAnomalyChartData>();
                    // synchronized (_listAdapter) {
                    _listAdapter.setNotifyOnChange(false);
                    try {
                        synchronized (_listAdapter) {

                            // Remove deleted instances
                            for (int i = 0, count = _listAdapter.getCount(); i < count; i++) {
                                if (isCancelled()) {
                                    return;
                                }
                                InstanceAnomalyChartData instance = _listAdapter.getItem(i);
                                if (servers.contains(instance.getId())) {
                                    existing.add(instance.getId());
                                } else {
                                    deleted.add(instance);
                                    updated = true;
                                }
                            }

                            // Remove deleted instances
                            if (isCancelled()) {
                                return;
                            }
                            for (InstanceAnomalyChartData instance : deleted) {
                                if (isCancelled()) {
                                    return;
                                }
                                _listAdapter.remove(instance);
                                updated = true;
                            }

                            // Add new instances
                            if (isCancelled()) {
                                return;
                            }
                            for (String newServer : servers) {
                                if (isCancelled()) {
                                    return;
                                }
                                if (existing.contains(newServer)) {
                                    continue;
                                }
                                _listAdapter.add(new InstanceAnomalyChartData(newServer,
                                        _aggregation));
                                updated = true;
                            }
                        }
                        if (isCancelled()) {
                            return;
                        }

                        if (updated) {
                            if (getListAdapter() == null) {
                                setListAdapter(_listAdapter);
                            }

                            updateMetricData();
                            _listAdapter.notifyDataSetChanged();
                        }
                    } finally {
                        _listAdapter.setNotifyOnChange(true);
                        _listAdapter.sort(InstanceListAdapter.getComparator());
                    }
                }

                @Override
                protected void onCancelled() {
                    _listAdapter.notifyDataSetChanged();
                }
            }.execute();
        }
    }

    @Override
    public void onPause() {
        super.onPause();
        if (_listAdapter != null) {
            _listAdapter.setNotifyOnChange(false);
        }

        YOMPApplication.removePropertyChangeListener(YOMPApplication.SORT_PROPERTY,
                _sortSelectionChangeListener);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(_metricChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _annotationChangedReceiver);
        LocalBroadcastManager.getInstance(getActivity()).unregisterReceiver(
                _metricDataChangedReceiver);
    }

    @Override
    public void onResume() {
        super.onResume();
        updateInstanceList();
        updateMetricData();
        if (_listAdapter != null) {
            _listAdapter.setNotifyOnChange(true);
            sort(false);
        }

        // Attach event listeners
        YOMPApplication.addPropertyChangeListener(YOMPApplication.SORT_PROPERTY,
                _sortSelectionChangeListener);

        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(_metricChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _metricDataChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_DATA_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _annotationChangedReceiver,
                new IntentFilter(DataSyncService.ANNOTATION_CHANGED_EVENT));
    }

    @Override
    public void onAttach(Activity activity) {
        super.onAttach(activity);

        // Create server list adapter and refresh its contents from the database
        _listAdapter = new InstanceListAdapter(activity, new ArrayList<InstanceAnomalyChartData>());
        updateInstanceList();
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);
        // On long click the list fragment will open the context menu.
        // We use this event to add our "Add Annotation" option.
        registerForContextMenu(getListView());
    }

    @Override
    public void onCreateContextMenu(ContextMenu menu, View view, ContextMenu.ContextMenuInfo menuInfo) {
        super.onCreateContextMenu(menu, view, menuInfo);
        //TODO:FEATURE_FLAG: Annotations were introduced in version 1.6
        if (YOMPApplication.getInstance().getServerVersion().compareTo(YOMPClientImpl.YOMP_SERVER_1_6) < 0) {
            return ;
        }
        if ( isMenuVisible()) {
            // Make sure we have data for this instance before showing the menu
            AdapterView.AdapterContextMenuInfo info = (AdapterView.AdapterContextMenuInfo) menuInfo;
            InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter().getItem(
                    info.position);
            if (instance != null && instance.hasData()) {
                // Get timestamp from the selected bar on the anomaly chart
                AnomalyChartView targetView = (AnomalyChartView) info.targetView.findViewById(R.id.anomaly_chart_view);
                long selectedTimestamp = targetView.getSelectedTimestamp();
                if (selectedTimestamp == -1) {
                    // The user did not select any anomaly bar. He must have clicked around the chart
                    return;
                }
                menu.add(0, R.id.menu_add_annotation, 0, R.string.menu_add_annotation);
            }
        }
    }

    @Override
    public boolean onContextItemSelected(MenuItem item) {
        if (isMenuVisible() && item.getItemId() == R.id.menu_add_annotation) {
            // Get instance from context menu position
            AdapterView.AdapterContextMenuInfo info = (AdapterView.AdapterContextMenuInfo) item.getMenuInfo();
            InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter().getItem(
                    info.position);

            // Get timestamp from the selected bar on the anomaly chart
            AnomalyChartView view = (AnomalyChartView) info.targetView.findViewById(R.id.anomaly_chart_view);
            long selectedTimestamp = view.getSelectedTimestamp();
            if (selectedTimestamp == -1) {
                // Should not happen
                Log.w(TAG, "Failed to get annotation timestamp from chart view. Using current time instead");
                return true;
            }

            // Open "Add  Annotation" activity
            Intent addAnnotation = new Intent(getActivity(), AddAnnotationActivity.class);
            addAnnotation.setFlags(Intent.FLAG_ACTIVITY_NO_HISTORY
                            | Intent.FLAG_ACTIVITY_CLEAR_TOP
                            | Intent.FLAG_ACTIVITY_NEW_TASK
                            | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
            );
            addAnnotation.putExtra(AddAnnotationActivity.EXTRA_INSTANCE_ID, instance.getId());
            addAnnotation.putExtra(AddAnnotationActivity.EXTRA_TIMESTAMP, selectedTimestamp);
            getActivity().startActivity(addAnnotation);
        }

        return super.onContextItemSelected(item);
    }

    @Override
    public void onListItemClick(ListView list, View item, int position, long id) {

        // Get item from position
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter().getItem(
                position);

        // Make user the instance has data before opening the detail page
        if (instance == null || !instance.hasData()) {
            // Nothing to show
            return;
        }

        // Check if clicked on annotations
        // If bar has annotations on the selected timestamp then open the annotation list
        AnomalyChartView view = (AnomalyChartView) item.findViewById(R.id.anomaly_chart_view);
        long timestamp = view.getSelectedTimestamp();
        long selectedTimestamp = -1;

        // The bar selection will be flexible, accepting user click on the bar with annotation
        // or any neighbouring bars.
        if (instance.hasAnnotationsForTime(timestamp)) {
            // The user clicked exactly on the bar with annotation
            selectedTimestamp = timestamp;
        } else if (instance.hasAnnotationsForTime(timestamp - instance.getAggregation().milliseconds())) {
            // The user clicked on the previous bar
            selectedTimestamp = timestamp - instance.getAggregation().milliseconds();
        } else if (instance.hasAnnotationsForTime(timestamp + instance.getAggregation().milliseconds())) {
            // The user clicked on the next bar
            selectedTimestamp = timestamp + instance.getAggregation().milliseconds();
        }

        if (selectedTimestamp != -1) {
            // Open annotation list
            Intent openListIntent = new Intent(getActivity(), AnnotationListActivity.class);
            openListIntent.putExtra(AnnotationListActivity.EXTRA_INSTANCE_DATA, instance);
            openListIntent.putExtra(AnnotationListActivity.EXTRA_TIMESTAMP, selectedTimestamp);
            getActivity().startActivity(openListIntent);
            return;
        }

        // Show detail page
        Intent instanceDetail = new Intent(getActivity(), InstanceDetailActivity.class);
        instanceDetail.putExtra(InstanceDetailActivity.INSTANCE_ID_ARG, instance.getId());
        startActivity(instanceDetail);
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Bundle args = getArguments();
        if (args != null) {
            _aggregation = (AggregationType) args.get(AggregationType.class.getCanonicalName());
            if (_listAdapter != null) {
                _listAdapter.setAggregation(_aggregation);
                updateInstanceList();
            }
        }
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            updateInstanceList();
        } else if (isAdded()) {
            setSelection(0);
        }
    }

    @Override
    public void onStop() {
        super.onStop();
        if (_metricLoadTask != null) {
            _metricLoadTask.cancel(true);
        }
    }
}
