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

import com.google.android.gms.analytics.HitBuilders;
import com.google.android.gms.analytics.Tracker;

import com.numenta.core.data.AggregationType;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.utils.DataUtils;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.TaurusBaseActivity;
import com.numenta.taurus.chart.TimeSliderView;
import com.numenta.taurus.service.TaurusDataSyncService;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.ListFragment;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.annotation.NonNull;
import android.support.v4.content.LocalBroadcastManager;
import android.support.v4.view.GestureDetectorCompat;
import android.view.ContextMenu;
import android.view.GestureDetector;
import android.view.LayoutInflater;
import android.view.MenuItem;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.Filter;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.Toast;

import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.Set;

/**
 * This Fragment is responsible for displaying the server list. The list item is
 * composed of the server name and anomaly chart
 */
public class InstanceListFragment extends ListFragment {

    private static final String TAG = InstanceListFragment.class.getSimpleName();

    private InstanceListAdapter _listAdapter;

    private final AggregationType _aggregation = TaurusApplication.getAggregation();

    // Event listeners
    private final BroadcastReceiver _instanceDataChangedReceiver;

    private final PropertyChangeListener _favoritesChangedReceiver;

    private AsyncTask<Void, Void, Boolean> _instanceLoadTask;

    private InstanceFilter _instanceFilter = InstanceFilter.None;

    private TimeSliderView _timeView;

    private boolean _scrolling;

    // Whether or not the list view is currently loading  data
    volatile boolean _loading;

    /** Horizontal scrolling threshold angle (30 deg) */
    static double HORIZ_SCROLLING_THRESHOLD_ANGLE = Math.PI / 6;

    private Toast _toast;

    /**
     * Handles date/time scrolling
     */
    final class GestureListener implements GestureDetector.OnGestureListener {

        private final View _view;

        long _initialTimestamp;

        public GestureListener(View view) {
            this._view = view;
        }

        @Override
        public boolean onDown(MotionEvent e) {
            Date endDate = _listAdapter.getEndDate();
            _initialTimestamp = endDate == null ? TaurusApplication.getDatabase().getLastTimestamp()
                    : endDate.getTime();
            _scrolling = false;
            return false;
        }

        @Override
        public void onShowPress(MotionEvent e) {
        }

        @Override
        public boolean onSingleTapUp(MotionEvent e) {
            return false;
        }

        @Override
        public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX, float distanceY) {
            long distance = getDistance(e1, e2);
            if (Math.abs(distance) > 1) {
                // Check if scrolling on a 45 degree angle
                double angle = Math.atan2(e1.getY() - e2.getY(), e1.getX() - e2.getX());
                if (_scrolling
                        || angle >= -HORIZ_SCROLLING_THRESHOLD_ANGLE
                        && angle <= HORIZ_SCROLLING_THRESHOLD_ANGLE
                        || angle >= Math.PI - HORIZ_SCROLLING_THRESHOLD_ANGLE
                        || angle <= -Math.PI + HORIZ_SCROLLING_THRESHOLD_ANGLE) {
                    Date scrolledDate = new Date(
                            DataUtils.floorTo5minutes(_initialTimestamp + distance));
                    if (_listAdapter != null) {
                        _listAdapter.setEndDate(scrolledDate);
                        scrolledDate = _listAdapter.getEndDate();
                        _timeView.setEndDate(scrolledDate.getTime());
                    }
                    // Show current scrolled date
                    _toast.setText(String.format("%1$tA, %1$tb %1$te", scrolledDate));
                    _toast.show();
                    _scrolling = true;
                }
            }
            return _scrolling;
        }

        /**
         * Calculate the time interval between 2 events
         *
         * @return Time interval in milliseconds
         */
        private long getDistance(MotionEvent e1, MotionEvent e2) {
            final float x1 = e1.getX();
            final float x2 = e2.getX();
            final float distance = x1 - x2;
            int width = _view.getMeasuredWidth();
            int pixels = width / TaurusApplication.getTotalBarsOnChart();
            int scrolledBars = (int) (distance / pixels);
            // Scroll date by aggregation interval
            long interval = _aggregation.milliseconds();
            return interval * scrolledBars;
        }

        @Override
        public void onLongPress(MotionEvent e) {
        }

        @Override
        public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX, float velocityY) {
            return false;
        }
    }

    final class TouchListener implements View.OnTouchListener {

        // Attach gesture detector to values chart handling scrolling.
        final GestureDetectorCompat _gestureDetector;

        // The current view
        final View _view;

        public TouchListener(View view) {
            _view = view;
            _gestureDetector = new GestureDetectorCompat(getActivity(),
                    new GestureListener(_view));
        }

        @Override
        public boolean onTouch(View v, MotionEvent event) {
            switch (event.getAction()) {
                case MotionEvent.ACTION_UP:
                    // Fall through
                case MotionEvent.ACTION_CANCEL:
                    // Done scrolling, refresh the chart scale
                    v.post(new Runnable() {
                        @Override
                        public void run() {
                            // Hide text if scrolled back 2 hours
                            long threshold = TaurusApplication.getDatabase().getLastTimestamp()
                                    - DataUtils.MILLIS_PER_HOUR * 2;
                            Date endDate = _listAdapter.getEndDate();
                            if (endDate != null && endDate.getTime() < threshold) {
                                _listAdapter.showHeaderText(false);
                            } else {
                                _listAdapter.showHeaderText(true);
                            }
                        }
                    });
                    break;
                default:
                    break;
            }

            // Detect scroll gestures on the metric detail chart
            return _gestureDetector.onTouchEvent(event);
        }
    }

    /**
     * InstanceListFragment constructor
     */
    public InstanceListFragment() {
        // Listen for new instance data
        _instanceDataChangedReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateInstanceData();
            }
        };

        // Listen for favorites changes
        _favoritesChangedReceiver = new PropertyChangeListener() {
            @Override
            public void propertyChange(PropertyChangeEvent event) {
                if (_instanceFilter == InstanceFilter.Favorites) {
                    filterFavorites();
                } else {
                    clearFilter();
                }
            }
        };
    }


    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container,
            Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_instance_list, container, false);
        _timeView = (TimeSliderView) view.findViewById(R.id.time_slider);
        _timeView.setCollapsed(false);
        setListAdapter(_listAdapter);
        return view;
    }

    @SuppressLint("ShowToast")
    @Override
    public void onViewCreated(View view, Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        View list = getListView();
        list.setOnTouchListener(new TouchListener(list));
        _toast = Toast.makeText(getActivity(), "", Toast.LENGTH_SHORT);
    }


    /**
     * Refresh {@link ListAdapter} with new instance data if available
     */
    private void updateInstanceData() {
        if (_loading) {
            return;
        }
        synchronized (this) {
            // Cancel previous task
            if (_instanceLoadTask != null) {
                cancelTrackedBackgroundTask(_instanceLoadTask);
            }
            _loading = true;
        }
        if (_listAdapter != null) {
            // Background task for loading instance data
            _instanceLoadTask = new AsyncTask<Void, Void, Boolean>() {
                HashSet<InstanceAnomalyChartData> deletedItems = new HashSet<InstanceAnomalyChartData>();

                HashSet<InstanceAnomalyChartData> addedItems = new HashSet<InstanceAnomalyChartData>();

                @Override
                protected void onPostExecute(Boolean modified) {
                    if (isCancelled()) {
                        return;
                    }
                    // Add new instances
                    if (!addedItems.isEmpty()) {
                        _listAdapter.addAll(addedItems
                                .toArray(new InstanceAnomalyChartData[addedItems.size()]));
                    }

                    // Remove deleted instances
                    for (InstanceAnomalyChartData item : deletedItems) {
                        _listAdapter.remove(item);
                    }
                    // Refresh
                    _listAdapter.sort();
                    updateTimeSlider();

                    if (_instanceFilter == InstanceFilter.Favorites) {
                        filterFavorites();
                    }
                    _loading = false;
                }

                @SuppressWarnings("SynchronizeOnNonFinalField")
                @Override
                protected Boolean doInBackground(Void... params) {
                    if (isCancelled()) {
                        return false;
                    }
                    // Consolidate adapter instance list with database
                    Set<String> persistedInstances = TaurusApplication.getDatabase()
                            .getAllInstances();
                    ArrayList<InstanceAnomalyChartData> items = new ArrayList<InstanceAnomalyChartData>();
                    HashSet<String> adapterInstances = new HashSet<String>();
                    boolean modified = false;
                    Date endDate;

                    synchronized (_listAdapter) {

                        endDate = _listAdapter.getEndDate();
                        // Find deleted instances
                        for (InstanceAnomalyChartData item : _listAdapter.getUnfilteredItems()) {
                            if (isCancelled()) {
                                return false;
                            }
                            if (persistedInstances.contains(item.getId())) {
                                adapterInstances.add(item.getId());
                                items.add(item);
                            } else {
                                modified = true;
                                deletedItems.add(item);
                            }
                        }
                    }

                    // Find new instances
                    if (isCancelled()) {
                        return false;
                    }
                    for (String instance : persistedInstances) {
                        if (isCancelled()) {
                            return false;
                        }
                        if (adapterInstances.contains(instance)) {
                            continue;
                        }
                        addedItems.add(new InstanceAnomalyChartData(instance, _aggregation));
                        modified = true;
                    }

                    // Refresh current items  data.
                    for (InstanceAnomalyChartData item : items) {
                        if (isCancelled()) {
                            return null;
                        }
                        item.setEndDate(endDate);
                        modified = item.load() || modified;
                    }

                    // Load data for the new instances.
                    for (InstanceAnomalyChartData item : addedItems) {
                        if (isCancelled()) {
                            return null;
                        }
                        item.setEndDate(endDate);
                        modified = item.load() || modified;
                    }
                    return modified;
                }

                @Override
                protected void onCancelled() {
                    _listAdapter.sort();
                    _listAdapter.notifyDataSetChanged();
                    _loading = false;
                }

            }.executeOnExecutor(TaurusApplication.getWorkerThreadPool());
            trackBackgroundTask(_instanceLoadTask);
        }
    }

    private void trackBackgroundTask(AsyncTask task) {
        Activity activity = getActivity();
        if (activity instanceof TaurusBaseActivity) {
            ((TaurusBaseActivity) activity).trackBackgroundTask(task);
        }
    }

    private void cancelTrackedBackgroundTask(AsyncTask task) {
        Activity activity = getActivity();
        if (activity instanceof TaurusBaseActivity) {
            ((TaurusBaseActivity) activity).cancelTrackedBackgroundTask(task);
        }
    }

    /**
     * Apply "favorite" instance filter to the list
     *
     * @see com.numenta.taurus.TaurusApplication#isInstanceFavorite(String)
     */
    public void filterFavorites() {
        _instanceFilter = InstanceFilter.Favorites;
        if (_listAdapter != null) {
            Filter listFilter = _listAdapter.getFavoritesFilter();
            if (listFilter != null) {
                listFilter.filter(null);
            }
        }
    }

    public void applyFilter(CharSequence query) {
        if (_listAdapter != null && query != null) {
            Filter listFilter = _listAdapter.getFilter();
            if (listFilter != null) {
                listFilter.filter(query);
            }
        }
    }

    /**
     * Remove any filter and show all instances
     */
    public void clearFilter() {
        _instanceFilter = InstanceFilter.None;
        if (_listAdapter != null) {
            _listAdapter.clearFilter();
        }
    }

    /**
     * Whether or not show group header
     */
    public void showHeaders(boolean show) {
        if (_listAdapter != null) {
            _listAdapter.showHeaders(show);
        }
    }

    @Override
    public void onPause() {
        super.onPause();

        LocalBroadcastManager.getInstance(getActivity())
                .unregisterReceiver(_instanceDataChangedReceiver);
        TaurusApplication.removePropertyChangeListener(TaurusApplication.FAVORITE_PROPERTY,
                _favoritesChangedReceiver);
    }

    @Override
    public void onResume() {
        super.onResume();
        updateInstanceData();

        // Attach event listeners
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _instanceDataChangedReceiver,
                new IntentFilter(TaurusDataSyncService.INSTANCE_DATA_CHANGED_EVENT));
        LocalBroadcastManager.getInstance(getActivity()).registerReceiver(
                _instanceDataChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_CHANGED_EVENT));
        TaurusApplication.addPropertyChangeListener(TaurusApplication.FAVORITE_PROPERTY,
                _favoritesChangedReceiver);

    }

    /**
     * Update {@link com.numenta.taurus.chart.TimeSliderView} matching the dates of this fragment's
     * list adapter.
     *
     * @see com.numenta.taurus.R.id#time_slider
     * @see com.numenta.taurus.R.layout#fragment_instance_list
     */
    private void updateTimeSlider() {
        // Update time
        Long end = _listAdapter.getEndDate() != null
                ? _listAdapter.getEndDate().getTime()
                : TaurusApplication.getDatabase().getLastTimestamp();
        View mainView = getView();
        if (mainView != null) {
            _timeView.setAggregation(_aggregation);
            _timeView.setEndDate(end);
        }
    }

    @Override
    public void onAttach(Activity activity) {
        super.onAttach(activity);

        // Create server list adapter and refresh its contents from the database
        _listAdapter = new InstanceListAdapter(activity, new ArrayList<InstanceAnomalyChartData>());
        _listAdapter.setAggregation(_aggregation);
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);
        // On long click the list fragment will open the context menu.
        // We use this event to add our "Add Annotation" option.
        registerForContextMenu(getListView());
    }

    @Override
    public void onCreateContextMenu(ContextMenu menu, View view,
            ContextMenu.ContextMenuInfo menuInfo) {
        if (_scrolling) {
            return;
        }
        super.onCreateContextMenu(menu, view, menuInfo);
        // Make sure we have an instance before showing the menu
        AdapterView.AdapterContextMenuInfo info = (AdapterView.AdapterContextMenuInfo) menuInfo;
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter().getItem(
                info.position);
        if (instance != null) {
            // Show Context menu with "Add/Remove Favorites" depending on the instance selected
            if (!TaurusApplication.isInstanceFavorite(instance.getId())) {
                menu.add(0, R.id.menu_add_favorite, 0, R.string.menu_add_favorite);
            } else {
                menu.add(0, R.id.menu_remove_favorite, 0, R.string.menu_remove_favorite);
            }
        }
    }

    @Override
    public boolean onContextItemSelected(MenuItem item) {
        // Get instance from context menu position
        AdapterView.AdapterContextMenuInfo info = (AdapterView.AdapterContextMenuInfo) item
                .getMenuInfo();
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter()
                .getItem(info.position);
        Tracker t = TaurusApplication.getInstance().getGoogleAnalyticsTracker();

        switch (item.getItemId()) {
            case R.id.menu_add_favorite:
                TaurusApplication.addInstanceToFavorites(instance.getId());
                t.send(new HitBuilders.EventBuilder()
                        .setCategory("Favorites")
                        .setAction("Add")
                        .setLabel(instance.getTicker())
                        .build());
                return true;
            case R.id.menu_remove_favorite:
                TaurusApplication.removeInstanceFromFavorites(instance.getId());
                t.send(new HitBuilders.EventBuilder()
                        .setCategory("Favorites")
                        .setAction("Remove")
                        .setLabel(instance.getTicker())
                        .build());
                return true;
        }
        return super.onContextItemSelected(item);

    }

    @Override
    public void onListItemClick(ListView list, View item, int position, long id) {

        // Check for network connection before opening detail screen
        Activity activity = getActivity();
        if (activity instanceof TaurusBaseActivity &&
                !((TaurusBaseActivity) activity).checkNetworkConnection()) {
            return;
        }

        // Get item from position
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) getListAdapter().getItem(
                position);

        // Make user the instance has data before opening the detail page
        if (instance == null || !instance.hasData()) {
            // Nothing to show
            return;
        }

        // Show detail page
        Intent instanceDetail = new Intent(getActivity(), InstanceDetailActivity.class);
        instanceDetail.putExtra(InstanceDetailActivity.INSTANCE_ID_ARG, instance.getId());
        instanceDetail.setFlags(Intent.FLAG_ACTIVITY_NO_ANIMATION);
        Date endDate = instance.getEndDate();
        instanceDetail.putExtra(InstanceDetailActivity.TIMESTAMP_ARG,
                endDate == null ? 0 : instance.getEndDate().getTime());
        startActivity(instanceDetail);
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            updateInstanceData();
        } else if (isAdded()) {
            setSelection(0);
        }
    }
}
