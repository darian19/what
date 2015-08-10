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

import com.YOMPsolutions.YOMP.mobile.R;
import com.numenta.core.ui.chart.AnomalyChartView;

import android.content.Context;
import android.os.AsyncTask;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.TextView;

import java.util.ArrayList;

public class MetricListAdapter extends ArrayAdapter<MetricAnomalyChartData> {
    protected static final String TAG = MetricListAdapter.class.getCanonicalName();
    private AsyncTask<MetricAnomalyChartData, Void, MetricAnomalyChartData> _metricLoadTask;

    public MetricListAdapter(Context context) {
        super(context, 0, new ArrayList<MetricAnomalyChartData>());
    }

    protected void bindView(final View parent, final int position) {

        MetricAnomalyChartData metric = getItem(position);

        // Update metric name
        TextView textView = (TextView) parent.findViewById(R.id.name);
        if (textView != null) {
            textView.setText(metric.getName());
        }

        // Update metric unit
        textView = (TextView) parent.findViewById(R.id.metric_unit);
        if (textView != null) {
            textView.setText(metric.getUnit());
        }

        // Update Chart
        final AnomalyChartView chartView = (AnomalyChartView) parent
                .findViewById(R.id.anomaly_chart_view);
        if (chartView == null) {
            return;
        }

        // Check if we have the data already
        if (!metric.hasData()) {
            // Load data in the background
            if (_metricLoadTask != null) {
                notifyDataSetChanged();
                _metricLoadTask.cancel(true);
            }

            _metricLoadTask = new AsyncTask<MetricAnomalyChartData, Void, MetricAnomalyChartData>() {
                @Override
                protected void onPostExecute(MetricAnomalyChartData metricData) {
                    chartView.setData(metricData.getData());
                    chartView.setFlags(metricData.getAnnotations());
                    notifyDataSetChanged();
                }

                @Override
                protected MetricAnomalyChartData doInBackground(MetricAnomalyChartData... args) {
                    MetricAnomalyChartData metricData = args[0];
                    if (isCancelled())
                        return null;
                    // Query database for aggregated values
                    metricData.load();
                    return metricData;
                }
            }.execute(metric);
        } else {
            // Use cached data
            chartView.setData(metric.getData());
            chartView.setFlags(metric.getAnnotations());
        }
    }

    @Override
    public View getView(int position, View convertView, final ViewGroup parent) {
        View view;
        if (convertView == null) {
            LayoutInflater inflater = (LayoutInflater) parent.getContext().getSystemService(
                    Context.LAYOUT_INFLATER_SERVICE);
            view = inflater.inflate(R.layout.fragment_metric_anomaly_chart, parent, false);
        } else {
            view = convertView;
        }
        if (parent.isShown()) {
            bindView(view, position);
        }
        return view;
    }
}
