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

import com.google.android.gms.analytics.HitBuilders;
import com.google.android.gms.analytics.Tracker;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.HourDayWeekActivity;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Metric;
import com.numenta.core.utils.Log;

import org.json.JSONException;
import org.json.JSONObject;

import android.app.ActionBar.Tab;
import android.app.AlertDialog;
import android.app.FragmentTransaction;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.preference.PreferenceManager;
import android.support.v4.app.Fragment;
import android.view.MenuItem;

import java.util.Date;

import static java.util.concurrent.TimeUnit.DAYS;
import static java.util.concurrent.TimeUnit.MILLISECONDS;
import static java.util.concurrent.TimeUnit.MINUTES;

public class MetricDetailActivity extends HourDayWeekActivity {

    public static final String EXTRA_METRIC = "com.YOMPsolutions.YOMP.mobile.metric";

    public static final String EXTRA_DATE = "com.YOMPsolutions.YOMP.mobile.metric.date";

    private static final String TAG = MetricDetailActivity.class.getCanonicalName();

    private Date _currentDate;

    private AggregationType _oldAggregation;

    private AggregationType _aggregation;

    /*
     * (non-Javadoc)
     * @see com.YOMPsolutions.YOMP.mobile.BaseActivity#getResourceView()
     */
    @Override
    protected int getResourceView() {
        return R.layout.activity_metric_detail;
    }

    /*
     * (non-Javadoc)
     * @see
     * com.YOMPsolutions.YOMP.mobile.BaseActivity#createTabFragment(android.
     * app.ActionBar.Tab)
     */
    @Override
    protected Fragment createTabFragment(Tab tab) {
        MetricDetailFragment fragment = new MetricDetailFragment();
        AggregationType type = (AggregationType) tab.getTag();
        Metric metric = getMetric();
        MetricAnomalyChartData metricData = new MetricAnomalyChartData(metric, type);
        Date endDate = new Date();
        if (getDate() != null) {
            final long currentSpan = endDate.getTime() - getDate().getTime();
            final int halfWeekMinutes =
                    (AggregationType.Week.minutes() * YOMPApplication.getTotalBarsOnChart()) / 2;
            int numMinutes = AggregationType.Hour.minutes() * YOMPApplication.getTotalBarsOnChart()
                    / 4;
            if (AggregationType.Day.equals(type)) {
                numMinutes = AggregationType.Day.minutes() * YOMPApplication.getTotalBarsOnChart()
                        / 2;
            } else if (AggregationType.Week.equals(type)) {
                long maxWeekSpan = MINUTES.convert(YOMPApplication.getNumberOfDaysToSync(), DAYS) -
                        AggregationType.Week.minutes() * YOMPApplication.getTotalBarsOnChart();
                if (MINUTES.convert(currentSpan, MILLISECONDS) > maxWeekSpan) {
                    numMinutes = (int) maxWeekSpan;
                } else if (MINUTES.convert(currentSpan, MILLISECONDS) > halfWeekMinutes) {
                    numMinutes = (int) MINUTES.convert(currentSpan, MILLISECONDS);
                } else {
                    numMinutes = halfWeekMinutes;
                }
            }
            final long maxSpan = MILLISECONDS.convert(numMinutes, MINUTES);
            if (currentSpan > maxSpan) {
                endDate.setTime(getDate().getTime() + maxSpan);
            }
        }
        if (YOMPApplication.getAggregation().equals(type)) {
            metricData.setEndDate(endDate);
            setCurrentDate(endDate);
        }
        fragment.setMetricAnomalyData(metricData);

        // Google Analytics: Track metric name as first Custom Dimension for
        // this App.
        Tracker tracker = YOMPApplication.getInstance().getGoogleAnalyticsTracker();
        tracker.send(
                new HitBuilders.AppViewBuilder().setCustomDimension(1, metric.getName()).build());
        return fragment;
    }

    public Date getDate() {
        Date date = null;
        try {
            Long timestamp = (Long) getIntent().getExtras().getSerializable(EXTRA_DATE);
            if (timestamp != null) {
                date = new Date(timestamp);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get date from Intent");
        }
        return date;
    }

    public void setCurrentDate(Date date) {
        this._currentDate = date;
    }

    public Date getCurrentDate() {
        return _currentDate;
    }

    public Metric getMetric() {
        Metric metric = null;
        try {
            String id = (String)getIntent().getExtras().getSerializable(EXTRA_METRIC);
            if (id != null) {
                metric = YOMPApplication.getDatabase().getMetric(id);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get Metric from Intent");
        }
        return metric;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.menu_feedback:
                // Create remote feedback data and start an email message with
                // a screenshot to support
                Log.i(TAG, "{TAG:ANDROID.ACTION.TAB.FEEDBACK} Feedback tab selected.");
                // NOTE: this request completes asynchronously

                AlertDialog.Builder builder = new AlertDialog.Builder(MetricDetailActivity.this);
                builder.setMessage(getString(R.string.feedback_dialog_message));
                builder.setTitle(getString(R.string.title_feedback_dialog));
                builder.setPositiveButton(android.R.string.ok,
                        new DialogInterface.OnClickListener() {

                            @Override
                            public void onClick(DialogInterface dialog, int which) {
                                MetricDetailActivity.this.submitUserFeedbackAsync();
                            }
                        });

                builder.setNegativeButton(android.R.string.cancel, null);
                builder.show();
                break;
            default:
                return super.onOptionsItemSelected(item);
        }

        return true;
    }

    /**
     * Submit user feedback; completes asynchronously
     */
    private void submitUserFeedbackAsync() {
        // Wrap network I/O in AsyncTask to avoid
        // android.os.NetworkOnMainThreadException
        new AsyncTask<Void, Void, String>() {
            @Override
            protected String doInBackground(Void... params) {
                String uploadId = uploadFeedbackDataFromYOMP();
                if (uploadId == null) {
                    uploadId = "Error uploading log file to S3";
                }
                return uploadId;
            }

            @Override
            protected void onPostExecute(String uploadId) {
                emailFeedback(uploadId);
            }
        }.execute();

    }

    /**
     * Request YOMP API to upload feedback data for the user feedback feature
     * <p>
     * <b>NOTE</b>: this method performs network I/O and therefore MUST be
     * wrapped in AsyncTask or similar to avoid
     * {@link android.os.NetworkOnMainThreadException}.
     * </p>
     *
     * @return id string of the uploaded feedback data; null on error
     */
    private String uploadFeedbackDataFromYOMP() {
        String uploadId;

        // Connect to YOMP
        YOMPClientImpl YOMP = null;
        final SharedPreferences prefs = PreferenceManager
                .getDefaultSharedPreferences(YOMPApplication.getContext());
        String serverUrl = prefs.getString(PreferencesConstants.PREF_SERVER_URL, null);
        if (serverUrl != null) {
            serverUrl = serverUrl.trim();
            String password = prefs.getString(PreferencesConstants.PREF_PASSWORD, null);
            try {
                YOMP = (YOMPClientImpl) YOMPApplication.getInstance().connectToYOMP(serverUrl, password);
                YOMP.login();
                Log.d(TAG, "Service connected to " + serverUrl);
            } catch (Exception e) {
                YOMP = null;
                Log.e(TAG, "Unable to connect to YOMP.", e);
            }
        } else {
            Log.e(TAG, "Unable to connect to YOMP. Missing server URL.");
        }

        if (YOMP == null) {
            return "Connection failed while uploading log file to S3";
        }

        // Create the request
        //
        // The request data is a JSON object; the uid property is the metric
        // uid;
        // additional properties are optional; e.g.:
        // {
        // "uid": "2a123bb1dd4d46e7a806d62efc29cbb9",
        // "otherInfo": "Some arbitrary info."
        // }
        //
        // The response body is the uploadId string
        JSONObject request;
        try {
            request = new JSONObject();
            request.put("uid", getMetric().getId());
        } catch (JSONException e) {
            Log.e(TAG, "JSON error.", e);
            return "Failed to parse log information for uploading to S3";
        }

        // Send the request to YOMP
        try {
            uploadId = YOMP.post(serverUrl + "/_logging/feedback", request.toString());
        } catch (Exception e) {
            Log.e(TAG, "YOMP _logging/feedback request failed.", e);
            return "Received an HTTP error while uploading log data to S3";
        }
        if (uploadId == null) {
            uploadId = "Received null HTTP response from feedback upload request.";
            Log.e(TAG, uploadId);
        }
        return uploadId;
    }

    /*
     * (non-Javadoc)
     * @see
     * com.YOMPsolutions.YOMP.mobile.HourDayWeekActivity#onTabSelected(android
     * .app.ActionBar.Tab, android.app.FragmentTransaction)
     */
    @Override
    public void onTabSelected(Tab tab, FragmentTransaction fragmentTransaction) {
        this._oldAggregation = YOMPApplication.getAggregation();
        super.onTabSelected(tab, fragmentTransaction);
        this._aggregation = YOMPApplication.getAggregation();
    }

    /**
     * @return the oldAggregation
     */
    public AggregationType getOldAggregation() {
        return this._oldAggregation;
    }

    /**
     * @return the aggregation
     */
    public AggregationType getAggregation() {
        return this._aggregation;
    }
}
