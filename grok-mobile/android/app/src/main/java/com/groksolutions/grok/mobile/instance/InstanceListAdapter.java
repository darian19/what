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
import com.numenta.core.data.AggregationType;
import com.numenta.core.ui.chart.AnomalyChartView;

import android.content.Context;
import android.os.AsyncTask;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Comparator;

public class InstanceListAdapter extends ArrayAdapter<InstanceAnomalyChartData> {
    private AggregationType _aggregation;
    private final LayoutInflater _inflater;

    public InstanceListAdapter(Context context, ArrayList<InstanceAnomalyChartData> data) {
        super(context, 0, data);
        _inflater = (LayoutInflater) context.getSystemService(Context.LAYOUT_INFLATER_SERVICE);
    }

    protected void bindView(final View parent, final int position) {
        InstanceAnomalyChartData instance = getItem(position);

        // Update server name
        TextView textView = (TextView) parent.findViewById(R.id.name);
        CharSequence oldText = textView.getText();
        if (!oldText.equals(instance.getName()))
            textView.setText(instance.getName());

        // Update Chart
        final AnomalyChartView chartView = (AnomalyChartView) parent
                .findViewById(R.id.anomaly_chart_view);
        if (chartView == null) {
            return;
        }

        // Check if we have the data already
        if (instance.hasData()) {
            chartView.setData(instance.getData());
            chartView.setFlags(instance.getAnnotations());
        } else {
            // TODO: Show loading?
        }
    }

    /**
     * Refresh Metric data with contents from the database
     */
    void clearData() {
        InstanceAnomalyChartData instance;
        for (int i = 0, count = getCount(); i < count; i++) {
            // TODO: Delete only changed server
            instance = getItem(i);
            instance.clear();
            loadData(instance);
        }
    }

    @Override
    public View getView(int position, View convertView, final ViewGroup parent) {
        View view;
        if (convertView == null) {
            view = _inflater.inflate(R.layout.fragment_instance_anomaly_chart, parent, false);
        } else {
            view = convertView;
        }
        if (parent.isShown()) {
            bindView(view, position);
        }
        return view;
    }

    public void setAggregation(AggregationType aggregation) {
        this._aggregation = aggregation;
    }

    public static Comparator<InstanceAnomalyChartData> getComparator() {
        if (YOMPApplication.getSort() == SortOrder.Name) {
            return InstanceAnomalyChartData.SORT_BY_NAME;
        }
        return InstanceAnomalyChartData.SORT_BY_ANOMALY;
    }

    void loadData(InstanceAnomalyChartData instance) {

        // Load data in the background
        new AsyncTask<InstanceAnomalyChartData, Void, InstanceAnomalyChartData>() {
            @Override
            protected void onPostExecute(InstanceAnomalyChartData srv) {
                sort(getComparator());
            }

            @Override
            protected InstanceAnomalyChartData doInBackground(InstanceAnomalyChartData... args) {
                InstanceAnomalyChartData srv = args[0];
                if (isCancelled())
                    return null;
                if (srv.load()) {
                    return srv;
                }
                return null;
            }
        }.execute(instance);
    }

    @Override
    public void add(InstanceAnomalyChartData instance) {
        super.add(instance);
        loadData(instance);
    }

    @Override
    public void remove(InstanceAnomalyChartData object) {
        super.remove(object);
        sort(getComparator());
    }

}
