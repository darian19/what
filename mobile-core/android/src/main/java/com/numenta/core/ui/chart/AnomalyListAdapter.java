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

package com.numenta.core.ui.chart;

import com.numenta.core.R;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.AggregationType;
import com.numenta.core.utils.DataUtils;

import android.content.Context;
import android.os.AsyncTask;
import android.view.LayoutInflater;
import android.widget.BaseAdapter;
import android.widget.Filterable;

import java.lang.reflect.Array;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Base {@link android.widget.ListAdapter} backed by an array of {@link AnomalyChartData}
 * for anomaly list charts (Instances & Metrics).
 * This class was mostly based on {@link android.widget.ArrayAdapter}
 */
public abstract class AnomalyListAdapter<T extends AnomalyChartData> extends BaseAdapter implements Filterable {

    /**
     * Lock used to modify the content of {@link #_values}. Any write operation
     * performed on the array should be synchronized on this lock. This lock is also
     * used by the filter (see {@link #getFilter()} to make a synchronized copy of
     * the original array of data.
     */
    protected final Object _lock = new Object();
    /**
     * Contains the list of AnomalyChartData that represent the data of this Adapter.
     */
    protected List<T> _values;
    protected final LayoutInflater _inflater;
    /**
     * A copy of the original _values array, initialized from and then used instead as soon as the
     * {@link AnomalyListAdapter.Filter} is used.
     * The _values array will then only contain the filtered values.
     */
    protected List<T> _originalValues;
    /**
     * Indicates whether or not {@link #notifyDataSetChanged()} must be called whenever
     * {@link #_values} is modified.
     */
    protected boolean _notifyOnChange = true;


    /**
     * Indicate whether or not {@link #loadData(T[])} must be called
     */
    protected boolean _loadDataOnChange = true;

    /**
     * Default sort comparator to use when calling {@link #sort()} with no arguments.
     *
     * @see #setSortComparator(java.util.Comparator)
     */
    protected Comparator<T> _comparator;

    /**
     * Date formatter to use when displaying dates.
     *
     * @see com.numenta.core.R.string#date_format_chart
     */
    protected final SimpleDateFormat _sdf;

    /**
     * The end date used by all the instances shown by this adapter.
     * The start date is determined by the {@link com.numenta.core.data.AggregationType}.
     * If no end date is set then the adapter will show the last known date in the database.
     */
    protected Date _endDate;

    /**
     * The current {@link com.numenta.core.data.AggregationType} to group the results of this
     * adapter.
     */
    protected AggregationType _aggregation;

    /**
     * The current data loading tasks
     */
    private ConcurrentLinkedQueue<AsyncTask> _taskList;


    /**
     * Represents a predicate used by {@link AnomalyListAdapter.Filter}
     */
    protected interface Predicate<T, CharSequence> {
        /**
         * Evaluates this predicate on the given argument and constraint.
         *
         * @param val        the input argument
         * @param constraint the given constraint
         * @return true if the input argument matches the predicate, otherwise false
         */
        boolean test(T val, CharSequence constraint);
    }

    /**
     * Filter the contents of this adapter based on a given {@link Predicate}.
     * <p/>
     * For Example:
     * <code><pre>
     * new Filter(new Predicate<InstanceAnomalyChartData, CharSequence>() {
     *     public boolean test(InstanceAnomalyChartData instance, CharSequence constraint) {
     *         return YOMPApplication.isInstanceFavorite(instance.getId());
     *     }
     * }
     * </pre></code>
     *
     * @see android.widget.Filter
     * @see #getFilter()
     */
    protected class Filter extends android.widget.Filter {
        final Predicate<T, CharSequence> _predicate;

        /**
         * Construct a new filter based on the given {@link Predicate}
         *
         * @param predicate The {@link Predicate} used to filter the results
         */
        public Filter(Predicate<T, CharSequence> predicate) {
            _predicate = predicate;
        }

        @Override
        protected FilterResults performFiltering(CharSequence constraint) {
            FilterResults results = new FilterResults();
            ArrayList<T> values;
            synchronized (_lock) {
                if (_originalValues == null) {
                    _originalValues = new ArrayList<T>(_values);
                }
                values = new ArrayList<T>(_originalValues);
            }
            final ArrayList<T> newValues = new ArrayList<T>();
            for (final T value : values) {
                if (_predicate.test(value, constraint)) {
                    newValues.add(value);
                }
            }

            results.values = newValues;
            results.count = newValues.size();

            return results;
        }

        @Override
        protected void publishResults(CharSequence constraint, FilterResults results) {
            _values = (List<T>) results.values;
            if (results.count > 0) {
                notifyDataSetChanged();
            } else {
                notifyDataSetInvalidated();
            }
        }
    }

    /**
     * AsyncTask used to load the AnomalyChartData in the background.
     *
     * The default implementation will first load and sort all the data in the background.
     *
     * @see #loadData
     * @see #getDataLoadingTask
     */
    protected class DataLoadingTask extends AsyncTask<AnomalyChartData, AnomalyChartData, Boolean> {

        @Override
        protected void onPostExecute(Boolean modified) {
            if (isCancelled()) {
                return;
            }
            if (modified) {
                sort();
            }
        }

        @Override
        protected Boolean doInBackground(AnomalyChartData... args) {
            boolean modified = false;
            for (AnomalyChartData val : args) {
                if (isCancelled()) {
                    break;
                }
                if (val.load()) {
                    modified = true;
                    publishProgress(val);
                }
            }
            return modified;
        }
    }

    /**
     * Constructor
     *
     * @param context The current context.
     * @param values  The values to represent in the ListView.
     */
    public AnomalyListAdapter(Context context, List<T> values) {
        _inflater = (LayoutInflater) context.getSystemService(Context.LAYOUT_INFLATER_SERVICE);
        _values = values == null ? new ArrayList<T>() : values;
        _sdf = new SimpleDateFormat(context.getString(R.string.date_format_chart), Locale.getDefault());
    }

    @Override
    public int getCount() {
        return _values != null ? _values.size() : 0;
    }

    @Override
    public T getItem(int position) {
        return _values != null ? _values.get(position) : null;
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    /**
     * Set the current {@link com.numenta.core.data.AggregationType} to apply the results of this
     * adapter.
     *
     * @param aggregation The new aggregation type to use.
     */
    public void setAggregation(AggregationType aggregation) {
        this._aggregation = aggregation;
    }

    /**
     * Load the given values data in a background Thread and
     * update the UI once all the data from the given values are loaded
     *
     * @param values One or more values to load
     */
    @SafeVarargs
    protected final void loadData(T... values) {

        if (!_loadDataOnChange) {
            return;
        }
        // Load data in the background
        AsyncTask task = getDataLoadingTask();
        if (task != null) {
            task.executeOnExecutor(YOMPApplication.getWorkerThreadPool(), values);
            if (_taskList == null) {
                _taskList = new ConcurrentLinkedQueue<AsyncTask>();
            }
            _taskList.add(task);
        }
    }

    /**
     * Gets the AsyncTask used to load AnomalyChartData in the background.
     *
     * @return AsyncTask to use. Usually based on {@link com.numenta.core.ui.chart.AnomalyListAdapter.DataLoadingTask}
     * @see #loadData
     */
    protected AsyncTask getDataLoadingTask() {
        return new DataLoadingTask();
    }

    /**
     * Set the end date for the instances shown by this adapter.
     * The start date is determined by the {@link com.numenta.core.data.AggregationType}.
     * If no end date is set then the adapter will show the last known date in the database.
     *
     * @param endDate The end date to limit the results. If this value is null
     *                then the adapter will show the last know date in the database
     */
    public void setEndDate(Date endDate) {
        // Make sure the date does not exceed the data boundaries
        long maxDate = DataUtils.floorTo5minutes(YOMPApplication.getDatabase().getLastTimestamp());
        long minDate = maxDate
                - (YOMPApplication.getNumberOfDaysToSync() - 1) * DataUtils.MILLIS_PER_DAY;
        // Check max date and no date
        if (endDate == null || endDate.getTime() > maxDate) {
            _endDate = new Date(maxDate);
        } else {
            _endDate = endDate;
        }
        // Check min date
        if (_endDate.getTime() < minDate) {
            _endDate = new Date(minDate);
        }

        List<T> objects;
        synchronized (_lock) {
            if (_originalValues != null) {
                objects = _originalValues;
            } else {
                objects = _values;
            }
        }
        if (objects.isEmpty()) {
            if (_notifyOnChange) notifyDataSetChanged();
            return;
        }

        // Update all objects managed by this adapter to the new end date
        for (T i : objects) {
            i.setEndDate(_endDate);
        }
        // Workaround to create typed array using generic type.
        // Get concrete class from first object and create array using that class
        Class<? extends AnomalyChartData> clazz = objects.get(0).getClass();
        T array[] = (T[]) Array.newInstance(clazz, objects.size());

        // Load data in the background
        loadData(objects.toArray(array));
    }

    /**
     * Get the end date shown in the adapter. If this value is null then the adapter will show the
     * last know date in the database
     *
     * @return The current end date
     */
    public Date getEndDate() {
        return _endDate;
    }

    /**
     * Adds the specified value at the end of the array.
     *
     * @param value The value to add at the end of the array.
     */
    public void add(T value) {
        // Update value's end date to match adapter's
        value.setEndDate(_endDate);
        synchronized (_lock) {
            if (_originalValues != null) {
                _originalValues.add(value);
            } else {
                _values.add(value);
            }
        }
        sort();

        loadData(value);
    }

    /**
     * Adds the objects in the specified collection to the end of the array
     *
     * @param values the collection of objects to add at the end of the array
     */
    @SafeVarargs
    public final void addAll(T... values) {
        // Update all objects managed by this adapter to the new end date
        synchronized (_lock) {
            for (T i : values) {
                if (_originalValues != null) {
                    _originalValues.add(i);
                } else {
                    _values.add(i);
                }
                i.setEndDate(_endDate);
            }
        }
        sort();

        // Load data in the background
        loadData(values);
    }

    /**
     * Removes the specified value from the array.
     *
     * @param value The object to remove.
     */
    public void remove(T value) {
        synchronized (_lock) {
            if (_originalValues != null) {
                _originalValues.remove(value);
            } else {
                _values.remove(value);
            }
        }
        sort();
    }

    /**
     * Control whether methods that change the list ({@link #add}, {@link #remove}, {@link #clear})
     * or loading instance data ({@link #loadData}) automatically call {@link #notifyDataSetChanged}.
     * If set to false, caller must manually call notifyDataSetChanged() to have the changes
     * reflected in the attached view.
     * <p/>
     * The default is true, and calling notifyDataSetChanged() resets the flag to true.
     *
     * @param notifyOnChange if true, modifications to the list will automatically
     *                       call {@link #notifyDataSetChanged}
     */
    public void setNotifyOnChange(boolean notifyOnChange) {
        _notifyOnChange = notifyOnChange;
    }

    @Override
    public void notifyDataSetChanged() {
        super.notifyDataSetChanged();
        _notifyOnChange = true;
    }

    /**
     * Remove all values from the adapter
     */
    public void clear() {
        synchronized (_lock) {
            if (_originalValues != null) {
                _originalValues.clear();
            } else {
                _values.clear();
            }
        }
        if (_notifyOnChange) {
            notifyDataSetChanged();
        }
    }

    /**
     * Resorts the content of this adapter using the comparator set by
     * {@link #setSortComparator(java.util.Comparator)}
     *
     * @see #setSortComparator(java.util.Comparator)
     */
    public void sort() {
        sort(_comparator);
    }

    /**
     * Sets the default sort comparator to use
     *
     * @param comparator
     */
    public void setSortComparator(Comparator<T> comparator) {
        _comparator = comparator;
        sort(_comparator);
    }

    /**
     * Sorts the content of this adapter using the specified comparator.
     *
     * @param comparator The comparator used to sort the objects contained
     *                   in this adapter.
     */
    public void sort(Comparator<? super T> comparator) {
        if (comparator != null) {
            synchronized (_lock) {
                if (_originalValues != null) {
                    Collections.sort(_originalValues, comparator);
                } else {
                    Collections.sort(_values, comparator);
                }
            }
        }
        if (_notifyOnChange) notifyDataSetChanged();
    }

    /**
     * Returns all objects managed by this adapter ignoring any filter
     */
    public List<T> getUnfilteredItems() {
        synchronized (_lock) {
            if (_originalValues != null) {
                return Collections.unmodifiableList(_originalValues);
            } else {
                return Collections.unmodifiableList(_values);
            }
        }
    }

    @Override
    public android.widget.Filter getFilter() {
        return null;
    }
    /**
     * Remove any filters and show all items
     */
    public void clearFilter() {
        synchronized (_lock) {
            if (_originalValues != null) {
                _values = new ArrayList<T>(_originalValues);
                _originalValues = null;
            }
        }
        if (_notifyOnChange) notifyDataSetChanged();
    }

    /**
     * Indicate whether or not {@link #loadData(T[])} must be called
     */
    public void setLoadDataOnChange(boolean val) {
        _loadDataOnChange = val;
    }

    /**
     * Stop any background tasks
     */
    public void stop() {
        // Cancel pending tasks
        if (_taskList != null) {
            AsyncTask task;
            while ((task = _taskList.poll()) != null) {
                task.cancel(true);
            }
        }
    }
}
