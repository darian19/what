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

import com.numenta.core.ui.chart.AnomalyListAdapter;
import com.numenta.core.utils.DataUtils;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.chart.AnomalyChartView;
import com.numenta.taurus.metric.MetricType;

import android.content.Context;
import android.os.AsyncTask;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.lang.ref.WeakReference;
import java.util.Date;
import java.util.EnumSet;
import java.util.List;
import java.util.regex.Pattern;

/**
 * A {@link android.widget.ListAdapter} containing {@link InstanceAnomalyChartData}
 * used by the {@link InstanceListFragment}.
 * <p>
 * This adapter will call {@link InstanceAnomalyChartData#load()} in the background when necessary.
 * </p>
 * <p>
 * See {@link R.layout.fragment_instance_anomaly_chart} for the list item layout. If you change
 * the layout then you need to make sure to update {@link #bindView(android.view.View, int)} to
 * bind the instance data to the UI elements.
 * </p>
 */
@SuppressWarnings("JavadocReference")
class InstanceListAdapter extends AnomalyListAdapter<InstanceAnomalyChartData> {

    /**
     * Background task used to update the anomaly chart view
     */
    static class ChartLoadTask
            extends AsyncTask<InstanceAnomalyChartData, Void, InstanceAnomalyChartData> {

        private final WeakReference<AnomalyChartView> _chartViewReference;

        ChartLoadTask(AnomalyChartView view) {
            // Use a WeakReference to ensure the view can be garbage collected
            _chartViewReference = new WeakReference<AnomalyChartView>(view);
        }

        @Override
        protected InstanceAnomalyChartData doInBackground(InstanceAnomalyChartData... params) {
            InstanceAnomalyChartData chartData = params[0];
            chartData.load();
            return chartData;
        }

        @Override
        protected void onPostExecute(InstanceAnomalyChartData chartData) {
            if (isCancelled()) {
                return;
            }
            final AnomalyChartView chartView = _chartViewReference.get();
            if (chartView != null) {
                chartView.setData(chartData.getData());
            }
        }
    }

    static class ViewHolder {

        View groupHeader;

        TextView groupTitle;

        TextView ticker;

        AnomalyChartView chartView;

        TextView name;
    }

    /**
     * Whether or not to show group headers
     */
    private boolean _showHeaders = true;

    /**
     * Whether or not to display the group header text.
     */
    private boolean _showHeaderText = true;

    /**
     * Constructor
     *
     * @param context   The current context.
     * @param instances The instances to represent in the ListView.
     */
    public InstanceListAdapter(Context context, List<InstanceAnomalyChartData> instances) {
        super(context, instances);
        setSortComparator(DataUtils.<InstanceAnomalyChartData>getSortByAnomalyComparator());
    }

    /**
     * Whether or not to show group headers
     *
     * @param show true to show headers false otherwise
     */
    public void showHeaders(boolean show) {
        _showHeaders = show;
    }

    /**
     * Whether or not to display the group header text. When this value is set to false the group
     * headers will be visible but the header text will be blank.
     * This behavior is used by the {@link InstanceListFragment} to hide the header text when
     * scrolling
     */
    public void showHeaderText(boolean show) {
        _showHeaderText = show;
        if (_notifyOnChange) {
            notifyDataSetChanged();
        }
    }

    void updateGroupHeader(ViewHolder holder, InstanceAnomalyChartData instance) {
        if (instance == null || !instance.hasData()) {
            return;
        }
        if (!_showHeaders) {
            holder.groupHeader.setVisibility(View.GONE);
            return;
        }
        // Make sure it is visible
        if (holder.groupHeader.getVisibility() != View.VISIBLE) {
            holder.groupHeader.setVisibility(View.VISIBLE);
        }
        if (_showHeaderText) {
            EnumSet<MetricType> metricTypes = instance.getAnomalousMetrics();
            if (metricTypes.size() == 0) {
                holder.groupTitle.setText(R.string.header_no_anomalies);
            } else if (metricTypes.contains(MetricType.TwitterVolume)) {
                if (metricTypes.contains(MetricType.StockPrice) ||
                        metricTypes.contains(MetricType.StockVolume)) {
                    holder.groupTitle.setText(R.string.header_stock_twitter);
                } else {
                    holder.groupTitle.setText(R.string.header_twitter);
                }
            } else {
                holder.groupTitle.setText(R.string.header_stock);
            }
        } else {
            // Clear text
            holder.groupTitle.setText("");
        }
    }

    /**
     * Bind {@link InstanceAnomalyChartData} to the list item layout elements at the specified
     * position in the data.
     * <p>
     * The List Item is defined by the {@link R.layout.fragment_instance_anomaly_chart} layout.
     * </p>
     *
     * @param parent   The parent view obtained by inflating {@link R.layout.fragment_instance_anomaly_chart}
     * @param position The position of the item within the adapter's data set of the item whose
     *                 view we want.
     */
    void bindView(final View parent, final int position) {
        final InstanceAnomalyChartData instance = getItem(position);
        ViewHolder holder = (ViewHolder) parent.getTag();

        // Update ticker
        String ticker = instance.getTicker();
        if (ticker != null) {
            holder.ticker.setText(ticker);
        }

        // Update company name
        holder.name.setText(instance.getName());

        // Update Chart
        if (holder.chartView == null) {
            return;
        }

        // Check if we have the data already
        if (instance.hasData() && !instance.isModified()) {
            holder.chartView.setData(instance.getData());
        } else {
            // Load data and update chart
            new ChartLoadTask(holder.chartView).execute(instance);
        }
        if (position == 0) {
            // First item
            updateGroupHeader(holder, instance);
        } else {
            InstanceAnomalyChartData prev = getItem(position - 1);
            EnumSet<MetricType> prevTypes = prev.getAnomalousMetrics();
            EnumSet<MetricType> curTypes = instance.getAnomalousMetrics();

            // Stock volume and Stock price should be grouped together
            // so use StockPrice only for comparison purposes
            if (prevTypes.removeAll(MetricType.STOCK_TYPES)) {

                prevTypes.add(MetricType.StockPrice);
            }
            if (curTypes.removeAll(MetricType.STOCK_TYPES)) {
                curTypes.add(MetricType.StockPrice);
            }

            // Only show if crossing the group boundary
            if (!prevTypes.equals(curTypes)) {
                updateGroupHeader(holder, instance);
            } else {
                // Within the same group. Hide header
                holder.groupHeader.setVisibility(View.GONE);
            }
        }
    }

    @Override
    public void setEndDate(Date endDate) {
        setLoadDataOnChange(false);
        super.setEndDate(endDate);
        setLoadDataOnChange(true);
        if (_notifyOnChange) {
            notifyDataSetChanged();
        }
    }

    @Override
    public View getView(int position, View convertView, final ViewGroup parent) {
        View view;
        if (convertView == null) {
            view = _inflater.inflate(R.layout.fragment_instance_anomaly_chart, parent, false);

            // Cache views
            ViewHolder holder = new ViewHolder();
            holder.groupHeader = view.findViewById(R.id.group_header_anomaly);
            holder.groupTitle = (TextView) holder.groupHeader.findViewById(R.id.title);
            holder.ticker = (TextView) view.findViewById(R.id.ticker);
            holder.name = (TextView) view.findViewById(R.id.name);
            holder.chartView = (AnomalyChartView) view.findViewById(R.id.anomaly_chart_view);
            view.setTag(holder);
        } else {
            view = convertView;
        }
        if (parent.isShown()) {
            bindView(view, position);
        }
        return view;
    }

    /**
     * Filter instances by favorites.
     *
     * @return Favorites instance filter
     * @see com.numenta.taurus.TaurusApplication#isInstanceFavorite(String)
     */
    public android.widget.Filter getFavoritesFilter() {
        return new Filter(
                new AnomalyListAdapter.Predicate<InstanceAnomalyChartData, CharSequence>() {
                    public boolean test(InstanceAnomalyChartData instance,
                            CharSequence constraint) {
                        return TaurusApplication.isInstanceFavorite(instance.getId());
                    }
                });
    }

    /**
     * Filter instances by name.
     *
     * @return Instances named filter
     */
    @Override
    public android.widget.Filter getFilter() {
        return new Filter(
                new AnomalyListAdapter.Predicate<InstanceAnomalyChartData, CharSequence>() {
                    public boolean test(InstanceAnomalyChartData instance,
                            CharSequence constraint) {
                        if (constraint != null) {
                            if (instance.getName() == null || instance.getTicker() == null) {
                                Log.w(getClass().getSimpleName(),
                                        "Invalid instance ticker or name");
                                return false;
                            }
                            String query = constraint.toString();
                            if (query.isEmpty()) {
                                return true;
                            }

                            // Matches any word starting with the given string
                            Pattern pattern = Pattern.compile("(?i-m)(^|\\W)" + query);

                            // Check if the pattern matches either the ticker or the company name
                            return pattern.matcher(instance.getName()).find() ||
                                    pattern.matcher(instance.getTicker()).find();
                        }
                        return true;
                    }
                });
    }
}
