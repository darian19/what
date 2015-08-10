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

import com.YOMPsolutions.YOMP.mobile.YOMPActivity;
import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartData;
import com.YOMPsolutions.YOMP.mobile.instance.InstanceAnomalyChartFragment;
import com.numenta.core.data.AggregationType;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.numenta.core.ui.chart.AnomalyChartView;
import com.numenta.core.utils.Log;

import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.text.format.DateFormat;
import android.view.View;
import android.widget.DatePicker;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.TimePicker;

import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

/**
 * This activity will open a form used to create new annotations. The caller should pass the
 * following arguments:
 * <ul>
 * <li>Instance ID</li>
 * <li>Annotation Timestamp</li>
 * </ul>
 */
public class AddAnnotationActivity extends YOMPActivity implements TimePickerDialog.OnTimeSetListener, DatePickerDialog.OnDateSetListener {
    /**
     * Annotation timestamp. The timestamp will be rounded to closest 5 min interval
     */
    public static final String EXTRA_TIMESTAMP = "com.YOMPsolutions.YOMP.mobile.annotation.timestamp";
    /**
     * The instance id to add annotation to
     */
    public static final String EXTRA_INSTANCE_ID = "com.YOMPsolutions.YOMP.mobile.annotation.instanceId";
    public static final String EXTRA_SHOW_TIME = "com.YOMPsolutions.YOMP.mobile.annotation.showTime";
    private String _instanceId;
    private long _timestamp;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_annotation);

        // Get instance id and timestamp passed to the intent
        _instanceId = getIntent().getStringExtra(EXTRA_INSTANCE_ID);
        _timestamp = getIntent().getLongExtra(EXTRA_TIMESTAMP, -1);
        if (_timestamp == -1) {
            Log.w(TAG, "Failed to get annotation timestamp from chart view. Using current time instead");
            _timestamp = System.currentTimeMillis();
            // Round to closest time
            _timestamp = (long) (Math.ceil(_timestamp/AggregationType.Hour.milliseconds()) * AggregationType.Hour.milliseconds());
        }
        // Show or Hide time
        boolean showTime = getIntent().getBooleanExtra(EXTRA_SHOW_TIME, true);
        if (showTime) {
            // If we are showing time then we allow the user to change it as well.
            // Add callback to allow time to change when the user clicks on the chart
            View instanceChartView = findViewById(R.id.instance_anomaly_chart);
            InstanceAnomalyChartFragment chartFrag = (InstanceAnomalyChartFragment) instanceChartView
                    .getTag();
            chartFrag.getBarChart().setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    AnomalyChartView chartView = (AnomalyChartView) view.findViewById(R.id.anomaly_chart_view);
                    long selectedTimestamp = chartView.getSelectedTimestamp();
                    if (selectedTimestamp != -1) {
                        _timestamp = selectedTimestamp;
                        updateHeader();
                    } else {
                        chartView.setSelectedTimestamp(_timestamp);
                    }
                }
            });
        } else {
            // Hide date/time related fields
            View view = findViewById(R.id.txt_time_label);
            view.setVisibility(View.GONE);
            view = findViewById(R.id.txt_date);
            view.setVisibility(View.GONE);
            view = findViewById(R.id.txt_time);
            view.setVisibility(View.GONE);
        }

        // Update user name
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(this);
        EditText txtUserName = (EditText) findViewById(R.id.txt_name);
        String userName = prefs.getString(PreferencesConstants.PREF_USER_NAME, "");
        txtUserName.setText(userName);

        // Update focus
        TextView txtMessage = (TextView) findViewById(R.id.txt_annotation_message);
        if (userName.isEmpty()) {
            txtUserName.requestFocus();
        } else {
            txtMessage.requestFocus();
        }

        // Update Anomaly Chart header
        updateHeader();
    }

    /**
     * Update Anomaly Chart header
     */
    private void updateHeader() {
        // Format time
        java.text.DateFormat timeFormat = java.text.DateFormat.getTimeInstance(
                java.text.DateFormat.SHORT, Locale.getDefault());
        TextView view = (TextView) findViewById(R.id.txt_time);
        view.setText(timeFormat.format(new Date(_timestamp)));

        // Format date
        java.text.DateFormat dateFormat = java.text.DateFormat.getDateInstance(
                java.text.DateFormat.MEDIUM, Locale.getDefault());
        view = (TextView) findViewById(R.id.txt_date);
        view.setText(dateFormat.format(new Date(_timestamp)));

        // Create Instance Data based on the instance passed to the intent
        InstanceAnomalyChartData data = new InstanceAnomalyChartData(_instanceId, AggregationType.Hour);

        // Put flag on the middle of the chart
        long endDate = _timestamp + YOMPApplication.getTotalBarsOnChart() * AggregationType.Hour.milliseconds() / 2;

        // make sure to not pass the end of the data
        endDate = Math.min(endDate, YOMPApplication.getDatabase().getLastTimestamp());

        endDate = Math.min(endDate, YOMPApplication.getDatabase().getLastTimestamp());
        data.setEndDate(new Date(endDate));

        // Load data
        new AsyncTask<InstanceAnomalyChartData, Void, InstanceAnomalyChartData>() {

            @Override
            protected InstanceAnomalyChartData doInBackground(InstanceAnomalyChartData... params) {
                final InstanceAnomalyChartData chartData = params[0];
                chartData.load();
                return chartData;
            }

            @Override
            protected void onPostExecute(InstanceAnomalyChartData chartData) {
                if (isCancelled()) {
                    return;
                }

                // Update fragment with new data
                View instanceChartView = findViewById(R.id.instance_anomaly_chart);
                InstanceAnomalyChartFragment chartFrag = (InstanceAnomalyChartFragment) instanceChartView
                        .getTag();
                // Prevent fragment from loading annotations from database
                chartFrag.freeze();
                // Update annotation flag with new timestamp
                chartData.setAnnotations(new long[]{_timestamp});
                chartFrag.setChartData(chartData);
            }
        }.execute(data);
    }

    /**
     * Callback from the Save {@link android.widget.Button}.
     * This method will validate, save the annotation on the server and close this activity.
     *
     * @param view The {@link android.widget.Button}
     */
    public void saveAnnotation(View view) {
        // Validate user name
        EditText txtUserName = (EditText) findViewById(R.id.txt_name);
        SharedPreferences.Editor prefs = PreferenceManager.getDefaultSharedPreferences(this).edit();
        final String userName = txtUserName.getText().toString().trim();
        if (userName.isEmpty()) {
            txtUserName.setError(getString(R.string.error_missing_user_name));
            return;
        }
        // Save for next annotation
        prefs.putString(PreferencesConstants.PREF_USER_NAME, userName);
        prefs.apply();

        TextView txtMessage = (TextView) findViewById(R.id.txt_annotation_message);
        final String message = txtMessage.getText().toString().trim();
        if (message.isEmpty()) {
            txtMessage.setError(getString(R.string.error_empty_message));
            return;
        }
        // Disable "Save" button while saving
        view.setEnabled(false);

        // POST annotation to server
        new AsyncTask<Void, Void, Boolean>() {
            @Override
            protected void onPostExecute(Boolean success) {
               if (success) {
                   // The annotation was added
                   finish();
               } else {
                   // Failed to add annotation to server.
                   AlertDialog.Builder builder = new AlertDialog.Builder(AddAnnotationActivity.this);
                   builder.setTitle(getString(R.string.title_activity_annotation_create))
                           .setMessage(getString(R.string.error_failed_to_add_annotation))
                           .setIconAttribute(android.R.attr.alertDialogIcon)
                           .setPositiveButton(android.R.string.ok, new DialogInterface.OnClickListener() {
                               @Override
                               public void onClick(DialogInterface dialog, int which) {
                                   finish();
                               }
                           }).show();
               }
            }

            @Override
            protected Boolean doInBackground(Void... params) {
                return YOMPApplication.addAnnotation(new Date(_timestamp), _instanceId, message, userName);
            }
        }.execute();

    }

    /**
     * Callback from the Time {@link android.widget.TextView} used to open the
     * {@link android.app.TimePickerDialog} allowing the user to select a new time
     *
     * @param view The {@link android.widget.TextView}
     */
    public void pickTimeDialog(View view) {
        final Calendar c = Calendar.getInstance();
        c.setTimeInMillis(_timestamp);
        TimePickerDialog dialog = new TimePickerDialog(this, this,
                c.get(Calendar.HOUR_OF_DAY),
                c.get(Calendar.MINUTE),
                DateFormat.is24HourFormat(this));
        dialog.show();
    }

    /**
     * Callback from {@link android.app.TimePickerDialog} to indicate the user is done filling in
     * the time
     *
     * @param view      The view associated with this listener.
     * @param hourOfDay The hour that was set.
     * @param minute    The minute that was set.
     */
    @Override
    public void onTimeSet(TimePicker view, int hourOfDay, int minute) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(_timestamp);
        cal.set(Calendar.HOUR_OF_DAY, hourOfDay);
        cal.set(Calendar.MINUTE, minute);

        // Round it to the closest 5 min
        _timestamp = (cal.getTimeInMillis() / 300000) * 300000;
        updateHeader();
    }

    /**
     * Callback from the Date {@link android.widget.TextView} used to open the
     * {@link android.app.DatePickerDialog} allowing the user to select a new date
     *
     * @param view The {@link android.widget.TextView}
     */
    public void pickDateDialog(View view) {
        final Calendar c = Calendar.getInstance();
        c.setTimeInMillis(_timestamp);
        DatePickerDialog dialog = new DatePickerDialog(this, this,
                c.get(Calendar.YEAR), c.get(Calendar.MONTH), c.get(Calendar.DAY_OF_MONTH));

        // Make sure the date is not the future
        dialog.getDatePicker().setMaxDate(System.currentTimeMillis());
        dialog.show();
    }

    /**
     * Callback from {@link android.app.DatePickerDialog} to indicate the user is done filling in
     * the date
     *
     * @param view        The view associated with this listener.
     * @param year        The year that was set.
     * @param monthOfYear The month that was set (0-11) for compatibility
     *                    with {@link java.util.Calendar}.
     * @param dayOfMonth  The day of the month that was set.
     */
    @Override
    public void onDateSet(DatePicker view, int year, int monthOfYear, int dayOfMonth) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(_timestamp);
        cal.set(year, monthOfYear, dayOfMonth);

        // Round it to the closest 5 min
        _timestamp = (cal.getTimeInMillis() / 300000) * 300000;
        updateHeader();
    }
}
