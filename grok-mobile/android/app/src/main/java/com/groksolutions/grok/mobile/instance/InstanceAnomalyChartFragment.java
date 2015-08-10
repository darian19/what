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

import android.app.Activity;
import android.content.Intent;
import android.content.res.TypedArray;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.ContextMenu;
import android.view.LayoutInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.annotation.AddAnnotationActivity;
import com.YOMPsolutions.YOMP.mobile.annotation.AnnotationListActivity;
import com.YOMPsolutions.YOMP.mobile.chart.AbstractAnomalyChartFragment;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.numenta.core.ui.chart.AnomalyChartView;
import com.numenta.core.service.YOMPClient;

public class InstanceAnomalyChartFragment extends AbstractAnomalyChartFragment {

    private boolean _showAnnotationList;
    private boolean _showAnnotationContextMenu;

    public InstanceAnomalyChartFragment() {

    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = super.onCreateView(inflater, container, savedInstanceState);
        // Show Context menu with "Add Annotation"
        if (_showAnnotationContextMenu) {
            registerForContextMenu(view);
        }
        return view;
    }

    @Override
    public void performClick(final View view) {
        // Check if clicked on annotations
        if (_showAnnotationList) {
            // If bar has annotations on the selected timestamp then open the annotation list
            AnomalyChartView chartView = (AnomalyChartView) view.findViewById(R.id.anomaly_chart_view);
            InstanceAnomalyChartData instance = (InstanceAnomalyChartData) _chartData;
            long timestamp = chartView.getSelectedTimestamp();
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
        }
        super.performClick(view);
    }

    @Override
    public void onCreateContextMenu(ContextMenu menu, View v, ContextMenu.ContextMenuInfo menuInfo) {
        super.onCreateContextMenu(menu, v, menuInfo);
        //TODO:FEATURE_FLAG: Annotations were introduced in version 1.6
        if (YOMPApplication.getInstance().getServerVersion().compareTo(YOMPClientImpl.YOMP_SERVER_1_6) < 0) {
            return;
        }
        // Get timestamp from the selected bar on the anomaly chart
        AnomalyChartView chartView = (AnomalyChartView) getView().findViewById(R.id.anomaly_chart_view);
        long selectedTimestamp = chartView.getSelectedTimestamp();
        if (selectedTimestamp == -1) {
            // The user did not select any anomaly bar. He must have clicked around the chart
            return;
        }

        // Show Context menu with "Add Annotation"
        menu.add(0, R.id.menu_add_annotation, 0, R.string.menu_add_annotation);
    }

    private void openAddAnnotationActivity() {
        // Get instance from context menu position
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) _chartData;
        // Get timestamp from the selected bar on the anomaly chart
        AnomalyChartView chartView = (AnomalyChartView) getView().findViewById(R.id.anomaly_chart_view);
        long selectedTimestamp = chartView.getSelectedTimestamp();
        if (selectedTimestamp == -1) {
             // Nothing selected
            return;
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

    @Override
    public boolean performLongClick(final View view) {
        return view.showContextMenu();
    }

    @Override
    public boolean onContextItemSelected(MenuItem item) {
        if (item.getItemId() == R.id.menu_add_annotation) {
            openAddAnnotationActivity();
            return true;
        }
        return super.onContextItemSelected(item);
    }

    @Override
    protected int getResourceView() {
        return R.layout.fragment_instance_anomaly_chart;
    }

    @Override
    public void onInflate(Activity activity, AttributeSet attrs, Bundle savedInstanceState) {
        super.onInflate(activity, attrs, savedInstanceState);
        // Get fragment arguments
        TypedArray attributes = activity.obtainStyledAttributes(attrs,
                R.styleable.InstanceAnomalyChartFragment);
        // Whether or not to show the annotation list activity
        _showAnnotationList = attributes.getBoolean(
                R.styleable.InstanceAnomalyChartFragment_showAnnotationList, true);
        _showAnnotationContextMenu = attributes.getBoolean(
                R.styleable.InstanceAnomalyChartFragment_showAnnotationContextMenu, true);

    }
}
