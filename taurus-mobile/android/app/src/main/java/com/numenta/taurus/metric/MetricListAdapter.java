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

import com.numenta.core.data.Metric;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.ui.chart.AnomalyListAdapter;
import com.numenta.core.ui.chart.LineChartView;
import com.numenta.core.utils.Log;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;

import android.app.ProgressDialog;
import android.content.Context;
import android.os.AsyncTask;
import android.os.Handler;
import android.os.Message;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;

public class MetricListAdapter extends AnomalyListAdapter<MetricAnomalyChartData> {

    private static final String TAG = MetricListAdapter.class.getSimpleName();

    private static final int MESSAGE_SHOW_PROGRESS = 1;

    private static final int MESSAGE_HIDE_PROGRESS = 2;

    final Context _context;

    public Context getContext() {
        return _context;
    }

    static class ViewHolder {

        TextView name;

        TextView caption;

        LineChartView lineChartView;
    }

    private boolean _refresh;

    private boolean _collapsed;

    private String _marketClosedText;

    public MetricListAdapter(Context context) {
        super(context, new ArrayList<MetricAnomalyChartData>());
        _context = context;

        _marketClosedText = context.getString(R.string.market_closed);

        _refresh = true;
        // Hard code metric list sort order to be (Price, Volume and Twitter)
        setSortComparator(new Comparator<MetricAnomalyChartData>() {
            @Override
            public int compare(MetricAnomalyChartData lhs, MetricAnomalyChartData rhs) {
                //Compare on MetricAnomalyChartData
                if (lhs == null) {
                    return 1;
                }
                if (rhs == null) {
                    return -1;
                }
                if (lhs.equals(rhs)) {
                    return 0;
                }

                //Compare on Metric
                Metric leftMetric = lhs.getMetric();
                Metric rightMetric = rhs.getMetric();
                if (leftMetric == null) {
                    return 1;
                }
                if (rightMetric == null) {
                    return -1;
                }
                if (leftMetric.equals(rightMetric)) {
                    return 0;
                }

                // Convert to "MetricType" enum
                MetricType leftMetricType = MetricType.valueOf(leftMetric);
                MetricType rightMetricType = MetricType.valueOf(rightMetric);

                // Compare metric type name based on "MetricListSortOrder"
                if (leftMetricType == rightMetricType) {
                    return 0;
                }
                if (leftMetricType == null) {
                    // Left side is unknown, move to the bottom
                    return 1;
                }
                if (rightMetricType == null) {
                    // Right side is unknown, move to the bottom
                    return -1;
                }
                return leftMetricType.compareTo(rightMetricType);
            }
        });
    }

    protected void bindView(final View parent, final int position) {
        ViewHolder holder = (ViewHolder) parent.getTag();

        MetricAnomalyChartData metric = getItem(position);
        metric.setCollapsed(_collapsed);

        // Update metric name
        holder.name.setText(metric.getName());

        // Update metric value chart
        // Hide selection marker
        holder.lineChartView.setSelectionMarker(null);

        // Update refresh
        holder.lineChartView.setRefreshScale(_refresh);

        // Check if we have the data already
        if (metric.hasData()) {
            holder.lineChartView.setData(metric.getRawData());
            holder.lineChartView.setAnomalies(metric.getAnomalies());
        }

        // Update chart for specific metrics
        MetricType type = MetricType.valueOf(metric.getMetric());
        switch (type) {
            case StockPrice:
                holder.lineChartView.setDisplayWholeNumbers(true);
                // Fall through
            case StockVolume:
                holder.lineChartView.setEmptyChartText(_marketClosedText);
                break;
            case TwitterVolume:
                holder.caption.setVisibility(View.VISIBLE);
                break;
        }
    }

    @Override
    public View getView(int position, View convertView, final ViewGroup parent) {
        View view;
        if (convertView == null) {
            LayoutInflater inflater = (LayoutInflater) parent.getContext().getSystemService(
                    Context.LAYOUT_INFLATER_SERVICE);
            view = inflater.inflate(R.layout.fragment_metric_anomaly_chart, parent, false);
            // Cache views
            ViewHolder holder = new ViewHolder();
            holder.name = (TextView) view.findViewById(R.id.name);
            holder.caption = (TextView) view.findViewById(R.id.caption);
            holder.lineChartView = (LineChartView) view.findViewById(R.id.line_chart_view);
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
     * Gets the AsyncTask used to load metric data in the background. This task will load each
     * metric in parallel on its own I/O thread updating the UI as the data arrives.
     * If the loading process takes more than 2 seconds the UI will show a spinning circle.
     *
     * @return AsyncTask used by {@link #loadData}
     */
    @Override
    protected AsyncTask getDataLoadingTask() {
        return new DataLoadingTask() {

            Handler _handler;

            @Override
            protected void onPreExecute() {
                super.onPreExecute();
                if (isCancelled()) {
                    return;
                }

                _handler = new Handler() {
                    ProgressDialog _progress = new ProgressDialog(getContext(),
                            R.style.SpinningCircleTheme);

                    @Override
                    public void handleMessage(Message msg) {
                        if (isCancelled()) {
                            return;
                        }

                        switch (msg.what) {
                            case MESSAGE_SHOW_PROGRESS:
                                if (_progress != null) {
                                    _progress.setIndeterminate(true);
                                    _progress.setMessage(null);
                                    _progress.show();
                                }
                                break;
                            case MESSAGE_HIDE_PROGRESS:
                                if (_progress != null) {
                                    _progress.dismiss();
                                    _progress = null;
                                }
                                break;
                        }
                    }
                };
            }

            @Override
            protected void onPostExecute(Boolean modified) {
                if (isCancelled()) {
                    return;
                }
                hideProgress();
                super.onPostExecute(modified);
            }

            @Override
            protected Boolean doInBackground(AnomalyChartData... args) {
                if (isCancelled()) {
                    return false;
                }

                // Show progress after 2 seconds as we start to load all metrics
                showProgress();

                Boolean modified = false;
                // Load data in parallel
                ArrayList<Callable<Boolean>> tasks = new ArrayList<Callable<Boolean>>(args.length);
                for (final AnomalyChartData val : args) {
                    if (isCancelled()) {
                        break;
                    }
                    tasks.add(new Callable<Boolean>() {
                        @Override
                        public Boolean call() throws Exception {
                            if (val.load()) {
                                // Update the UI as the data arrives
                                publishProgress(val);
                                return true;
                            }
                            return false;
                        }
                    });
                }
                // Use I/O Thread pool to load metric data
                try {
                    ExecutorService threadPool = TaurusApplication.getIOThreadPool();
                    if (threadPool != null) {
                        List<Future<Boolean>> results = threadPool.invokeAll(tasks);
                        for (Future<Boolean> future : results) {
                            if (isCancelled() || future.isCancelled()) {
                                break;
                            }
                            modified = modified || future.get();
                        }
                    }
                } catch (InterruptedException e) {
                    Log.e(TAG, "Load metric data process was interrupted", e);
                } catch (ExecutionException e) {
                    Log.e(TAG, "Failed to load metric data", e);
                }
                return modified;
            }

            void hideProgress() {
                _handler.sendEmptyMessage(MESSAGE_HIDE_PROGRESS);
            }

            void showProgress() {
                // Show progress after 3 seconds if the task is still active
                _handler.sendEmptyMessageDelayed(MESSAGE_SHOW_PROGRESS, 3000);
            }
        };
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

    /**
     * Controls whether or not we should update the min/max based on the data
     *
     * @param refresh {@code true} to always refresh the min/max, {@code false} otherwise
     */
    public void setRefreshScale(boolean refresh) {
        if (_refresh != refresh) {
            _refresh = refresh;
            if (_refresh && _notifyOnChange) {
                notifyDataSetChanged();
            }
        }
    }

    /**
     * Set whether or not to collapse the time for this view. If {@code true} the view will
     * collapse the the time based on the current market calendar.
     *
     * @see com.numenta.taurus.TaurusApplication#getMarketCalendar()
     */
    public void setCollapsed(boolean collapsed) {
        if (_collapsed != collapsed) {
            _collapsed = collapsed;
            for (int i = 0; i < getCount(); i++) {
                MetricAnomalyChartData item = getItem(i);
                item.setCollapsed(collapsed);
            }
            if (_notifyOnChange) {
                notifyDataSetChanged();
            }
        }
    }
}
