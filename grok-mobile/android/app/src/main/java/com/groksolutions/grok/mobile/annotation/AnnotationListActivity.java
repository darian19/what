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

package com.YOMPsolutions.YOMP.mobile.annotation;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.AsyncTask;
import android.os.Bundle;
import android.text.Annotation;
import android.text.SpannedString;
import android.text.TextUtils;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import com.numenta.core.data.AggregationType;
import com.YOMPsolutions.YOMP.mobile.YOMPActivity;
import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.numenta.core.ui.chart.AnomalyChartView;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartFragment;
import com.numenta.core.utils.Log;

import java.util.Date;

/**
 * This activity display all the annotations for a specific server filtered by a time period
 */
public class AnnotationListActivity extends YOMPActivity {

    /**
     * Annotation timestamp. The timestamp will be rounded to the correct
     * time window based on the aggregation type: HOUR (5 min), DAY (1 hour), WEEK (8 hours)
     */
    public static final String EXTRA_TIMESTAMP = "com.YOMPsolutions.YOMP.mobile.annotation.timestamp";
    /**
     * The {@link com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData} for the instance
     * containing the annotations. The instance chart data must be preloaded.
     *
     * @see com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData#load()
     */
    public static final String EXTRA_INSTANCE_DATA = "com.YOMPsolutions.YOMP.mobile.annotation.instanceData";
    private static final int REQUEST_ADD_ANNOTATION = 1;

    private long _timestamp;
    private InstanceAnomalyChartData _instanceData;
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_annotation_list);
        // Get Intent Arguments
        _instanceData = (InstanceAnomalyChartData) getIntent().getExtras().getSerializable(EXTRA_INSTANCE_DATA);
        _timestamp = getIntent().getExtras().getLong(EXTRA_TIMESTAMP);

        // Update list when user selects another flag
        View instanceChartView = getWindow().findViewById(R.id.instance_anomaly_chart);
        final InstanceAnomalyChartFragment chartFrag = (InstanceAnomalyChartFragment) instanceChartView
                .getTag();
        chartFrag.getBarChart().setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                AnomalyChartView chartView = (AnomalyChartView) view.findViewById(R.id.anomaly_chart_view);
                long selectedTimestamp = chartView.getSelectedTimestamp();
                if (selectedTimestamp != -1) {
                    boolean needUpdate = false;
                    // Make sure the user clicked on a flag
                    // The bar selection will be flexible, accepting user click on the bar with annotation
                    // or any neighbouring bars.
                    if (_instanceData.hasAnnotationsForTime(selectedTimestamp)) {
                        // The user clicked exactly on the bar with annotation
                        _timestamp = selectedTimestamp;
                        needUpdate = true;
                    } else if (_instanceData.hasAnnotationsForTime(selectedTimestamp - _instanceData.getAggregation().milliseconds())) {
                        // The user clicked on the previous bar
                        _timestamp = selectedTimestamp - _instanceData.getAggregation().milliseconds();
                        needUpdate = true;
                    } else if (_instanceData.hasAnnotationsForTime(selectedTimestamp + _instanceData.getAggregation().milliseconds())) {
                        // The user clicked on the next bar
                        _timestamp = selectedTimestamp + _instanceData.getAggregation().milliseconds();
                        needUpdate = true;
                    }
                    if (needUpdate) {
                        _timestamp = selectedTimestamp;
                        chartFrag.setSelectedTimestamp(_timestamp);
                        update();
                    }
                }
            }
        });

        update();
    }

    protected void update() {
        AnnotationListFragment annotationListFragment =
                (AnnotationListFragment) getSupportFragmentManager().
                        findFragmentById(R.id.fragment_annotation_list);
        updateHeader();
        // Get all annotations falling within the current aggregation period (HOUR/DAY/WEEK)
        long period = _instanceData.getAggregation().milliseconds();
        long from = (_timestamp / period) * period;
        long to = from ;
        // For DAY and WEEK view get all annotation up to the end of the period
        if (!_instanceData.getAggregation().equals(AggregationType.Hour)) {
            to += period - 1;
        }

        annotationListFragment.updateList(_instanceData.getId(), new Date(from), new Date(to));
    }

    /**
     * Update Anomaly Chart header part of this fragment with the given data
     *
     */
    public void updateHeader() {
        if (_instanceData== null) {
            return;
        }
        View instanceChartView = getWindow().findViewById(R.id.instance_anomaly_chart);
        InstanceAnomalyChartFragment chartFrag = (InstanceAnomalyChartFragment) instanceChartView
                .getTag();
        _instanceData.clear();
        chartFrag.setChartData(_instanceData);
        long period = _instanceData.getAggregation().milliseconds();
        chartFrag.setSelectedTimestamp((_timestamp / period) * period);
    }

    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_ADD_ANNOTATION) {
            update();
        }
    }

    /**
     * Return the annotation {@link android.widget.TextView} from the annotation line item related
     * to the given button (Add/Delete). See "R.layout.annotation_item"
     *
     * @param button The button in the same line item as the annotation
     *
     * @return The annotation TextView or {@code null} if there is no annotation
     */
    private TextView getAnnotationMessageTextFromButton(View button) {
        // Find the annotation message from the annotation line item. See "R.layout.annotation_item"
        TextView message = null;
        View parent = (View) button.getParent();
        while (parent != null) {
            message = (TextView) parent.findViewById(R.id.txt_annotation_message);
            if (message != null)
                break;
            // Traverse layout
            parent = (View) parent.getParent();
        }
        return message;
    }

    /**
     * Return the annotation ID related to the given button (Add/Delete)
     *
     * @param button The button in the same line item as the annotation
     *
     * @return The annotation ID or {@code null} if there is no annotation
     */
    private String getAnnotationIdFromButton(View button) {
        // Find the annotation message from the annotation line item. See "R.layout.annotation_item"
        TextView message = getAnnotationMessageTextFromButton(button);
        if (message != null) {
            // Get the Spannable text from the message text view. See "AnnotationListFragment"
            final SpannedString text = (SpannedString) message.getText();
            Annotation spans[] = text.getSpans(0, 1, Annotation.class);
            if (spans.length > 0) {
                // There should be only one Annotation span with the annotation "id". See "AnnotationListFragment"
                return spans[0].getValue();
            }
        }
        return null;
    }

    /**
     * Called by the 'Add' button.
     * Open {@link com.YOMPsolutions.YOMP.mobile.annotation.AddAnnotationActivity} for the current
     * list item. Initializing the activity with the current instance ID and selected list item
     * timestamp
     *
     * @param view The clicked button (Add)
     */
    public void addAnnotation(View view) {

        // Default timestamp to initial timestamp passed to the activity
        long timestamp = _timestamp;

        String id = getAnnotationIdFromButton(view);
        if (id != null) {
            AnnotationListFragment annotationListFragment =
                    (AnnotationListFragment) getSupportFragmentManager()
                            .findFragmentById(R.id.fragment_annotation_list);

            // Get annotation from text span
            com.numenta.core.data.Annotation annotation = annotationListFragment
                    .getAnnotationById(id);
            if (annotation != null) {
                // Use selected annotation timestamp
                timestamp = annotation.getTimestamp();
            } else {
                Log.w(TAG, "Could not find annotation associated with 'Add' button");
            }
        } else {
            Log.w(TAG, "Could not find annotation associated with 'Add' button");
        }

        // Open "Add  Annotation" activity
        Intent addAnnotation = new Intent(this, AddAnnotationActivity.class);
        addAnnotation.putExtra(AddAnnotationActivity.EXTRA_INSTANCE_ID, _instanceData.getId());
        addAnnotation.putExtra(AddAnnotationActivity.EXTRA_TIMESTAMP, timestamp);
        addAnnotation.putExtra(AddAnnotationActivity.EXTRA_SHOW_TIME, false);
        startActivityForResult(addAnnotation, REQUEST_ADD_ANNOTATION);
    }

    /**
     * Called by the 'Delete' button.
     * Delete the annotation associated with this list item
     *
     * @param view The clicked button (Delete)
     */
    public void deleteAnnotation(View view) {

        TextView message = getAnnotationMessageTextFromButton(view);
        if (message != null) {
            // Get the Spannable text from the message text view. See "AnnotationListFragment"
            final SpannedString text = (SpannedString) message.getText();
            // Show a dialog confirming the user wants to delete his annotation
            AlertDialog.Builder builder = new AlertDialog.Builder(this);
            builder.setTitle(getString(R.string.title_delete_annotation))
                    .setMessage(TextUtils.ellipsize(text, message.getPaint(), message.getWidth() * 3, TextUtils.TruncateAt.MIDDLE))
                    .setPositiveButton(android.R.string.yes, new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialog, int which) {
                            // Look for the Annotation Span. See "android.text.Annotation" and "AnnotationListFragment"
                            Annotation spans[] = text.getSpans(0, 1, Annotation.class);
                            if (spans.length > 0) {

                                // There should be only one Annotation span with the annotation "id". See "AnnotationListFragment"
                                new AsyncTask<String, Void, Boolean>() {
                                    @Override
                                    protected void onPostExecute(Boolean deleted) {
                                        if (!deleted) {
                                            // Failed to delete annotation. Notify the user
                                            Toast.makeText(AnnotationListActivity.this,
                                                    getString(R.string.error_delete_annotation_failed),
                                                    Toast.LENGTH_LONG).show();
                                        }
                                        // Refresh list
                                        update();
                                    }

                                    @Override
                                    protected Boolean doInBackground(String... id) {
                                        return YOMPApplication.deleteAnnotation(id[0]);
                                    }
                                }.execute(spans[0].getValue());
                            }
                        }
                    })
                    .setNegativeButton(android.R.string.no, new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialog, int which) {
                            // do nothing
                        }
                    })
                    .show();

        }
    }
}
