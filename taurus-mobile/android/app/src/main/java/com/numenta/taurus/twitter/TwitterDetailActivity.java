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

package com.numenta.taurus.twitter;

import com.numenta.core.data.Metric;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.ui.chart.LineChartView;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.TaurusBaseActivity;
import com.numenta.taurus.chart.TimeSliderView;
import com.numenta.taurus.data.Tweet;
import com.numenta.taurus.instance.InstanceAnomalyChartData;
import com.numenta.taurus.instance.InstanceAnomalyChartFragment;
import com.numenta.taurus.metric.MetricAnomalyChartData;
import com.numenta.taurus.service.TaurusClient;

import android.app.ActionBar;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.widget.AbsListView;
import android.widget.AdapterView;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.ListView;
import android.widget.TextView;

import java.io.IOException;
import java.util.Comparator;
import java.util.Date;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 * Show a list of tweets for a specific company/instance.
 * <p>
 * Use {@link android.content.Intent} data to select the company and initial timestamp.
 * </p>
 * The <i>Intent</i> parameters are:
 * <ul>
 * <li>{@link #METRIC_ID_ARG}: Metric ID for the twitter volume metric to display</li>
 * <li>{@link #TIMESTAMP_ARG}: Only show tweets for this timestamp</li>
 * </ul>
 * <p>
 * Usage:
 * <code><pre>
 *     Calendar cal = Calendar.getInstance();
 *     cal.set(2014, 1, 1, 1, 1);
 *     Intent twitterIntent = new Intent(ctx, TwitterDetailActivity.class);
 *     twitterIntent.putExtra(InstanceDetailActivity.METRIC_ID_ARG, metric.getId());
 *     twitterIntent.putExtra(InstanceDetailActivity.TIMESTAMP_ARG, cal.getTimeInMillis());
 *     startActivity(twitterIntent);
 * </pre></code>
 * </p>
 */
public class TwitterDetailActivity extends TaurusBaseActivity {

    /** The twitter volume metric to display */
    public static final String METRIC_ID_ARG = "metric_id";

    /** The timestamp to filter the tweets by */
    public static final String TIMESTAMP_ARG = "timestamp";

    /** The selected timestamp to position */
    public static final String SELECTED_TIMESTAMP_ARG = "selected";

    /** Sort tweets by time > retweet count > retweet total > id */
    public static Comparator<Tweet> SORT_BY_DATE = new Comparator<Tweet>() {
        @Override
        public int compare(Tweet lhs, Tweet rhs) {
            if (lhs.equals(rhs)) {
                return 0;
            }

            // First Sort by time
            int res = (int) (rhs.getAggregated() - lhs.getAggregated());
            if (res == 0) {
                // Second Sort by retweet count
                res = rhs.getRetweetCount() - lhs.getRetweetCount();
            }
            if (res == 0) {
                // Second Sort by retweet total
                res = rhs.getRetweetTotal() - lhs.getRetweetTotal();
            }
            if (res == 0) {
                // Last Sort by ID
                res = lhs.getId().compareTo(rhs.getId());
            }
            return res;
        }
    };

    /** Sort tweets by text and filter retweets */
    public static Comparator<Tweet> SORT_BY_TEXT = new Comparator<Tweet>() {
        @Override
        public int compare(Tweet lhs, Tweet rhs) {
            // Compare tweets based on text
            if (lhs.equals(rhs)) {
                return 0;
            }
            // Make sure it is the same period
            int res = (int) (rhs.getAggregated() - lhs.getAggregated());
            if (res == 0) {
                String leftText = lhs.getCanonicalText();
                String rightText = rhs.getCanonicalText();
                return leftText.compareTo(rightText);
            }
            return res;
        }
    };

    private TimeSliderView _timeView;

    // Instance Chart
    private InstanceAnomalyChartFragment _instanceChartFragment;

    private InstanceAnomalyChartData _chartData;

    // Metric Chart
    private MetricAnomalyChartData _metricData;

    private LineChartView _lineChartView;

    private Metric _metric;

    // Twitter group header
    private View _groupHeader;

    // Loading tweets message
    private View _loadingMessage;

    // Condensed checkbox
    private CheckBox _condensedCheckbox;


    // Date field on group header
    private TextView _date;

    // Tweet count field on the group header
    private TextView _tweetCount;

    // Twitter list view
    private ListView _listView;

    private Drawable _normalDivider;

    private Drawable _condensedDivider;

    private TwitterListAdapter _twitterListAdapter;

    // Whether or not the list view is currently in the middle of a scroll operation
    public boolean _isScrolling;

    // Initial timestamp passed to the activity
    private long _timestampArg;

    // Whether or not the list view is currently loading twitter data
    volatile boolean _loading;

    private AsyncTask<Void, Object, Void> _instanceLoader;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_twitter_detail);
        // Configure the action bar showing the title and home button
        ActionBar actionBar = getActionBar();
        if (actionBar != null) {
            actionBar.setDisplayHomeAsUpEnabled(true);
            actionBar.setDisplayShowTitleEnabled(true);
        }

        // Cache views and fragments
        View chartView = findViewById(R.id.instance_anomaly_chart);
        _instanceChartFragment = (InstanceAnomalyChartFragment) chartView.getTag();

        _timeView = (TimeSliderView) findViewById(R.id.time_slider);
        _timeView.setCollapsed(false);

        _lineChartView = (LineChartView) findViewById(R.id.line_chart_view);
        _lineChartView.setOnSelectionChangeListener(new LineChartView.OnSelectionChangeListener() {
            @Override
            public void onSelectionChange(View view, int selection) {
                if (!_isScrolling) {
                    // Synchronize list selection with chart selection
                    long timestamp = getTimeRange().first
                            + selection * DataUtils.METRIC_DATA_INTERVAL;
                    scrollTo(timestamp);
                }
            }
        });

        _loadingMessage = findViewById(R.id.loading_tweets_message);

        _groupHeader = findViewById(R.id.group_header);
        _date = (TextView) _groupHeader.findViewById(R.id.date);
        _tweetCount = (TextView) _groupHeader.findViewById(R.id.tweet_count);

        _listView = (ListView) findViewById(R.id.twitter_list);

        // Add "grey" filler as list footer. This footer will allow us to scroll to the last tweet.
        _listView.addFooterView(getLayoutInflater().inflate(R.layout.twitter_list_footer, null));
        _twitterListAdapter = new TwitterListAdapter(this);
        _listView.setAdapter(_twitterListAdapter);
        _listView.setOnItemLongClickListener(new AdapterView.OnItemLongClickListener() {
            @Override
            public boolean onItemLongClick(AdapterView<?> parent, View view, int position,
                    long id) {
                // Open tweet on long click
                final Tweet tweet = (Tweet) _listView.getItemAtPosition(position);
                if (tweet != null) {
                    // Ask user before opening twitter application
                    new AlertDialog.Builder(TwitterDetailActivity.this)
                            .setIcon(android.R.drawable.ic_dialog_alert)
                            .setTitle(R.string.open_twitter_title)
                            .setMessage(R.string.open_twitter_message)
                            .setPositiveButton(android.R.string.yes,
                                    new DialogInterface.OnClickListener() {
                                        @Override
                                        public void onClick(DialogInterface dialog, int which) {
                                            Intent intent = new Intent(Intent.ACTION_VIEW,
                                                    Uri.parse(
                                                            "http://twitter.com/" + tweet
                                                                    .getUserName()
                                                                    + "/status/" + tweet.getId()));
                                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                            startActivity(intent);
                                        }
                                    })
                            .setNegativeButton(android.R.string.no, null)
                            .show();
                }
                return true;
            }
        });
        _listView.setOnScrollListener(new AbsListView.OnScrollListener() {

            @Override
            public void onScrollStateChanged(AbsListView view, int scrollState) {
                _isScrolling = scrollState != SCROLL_STATE_IDLE;
            }

            @Override
            public void onScroll(AbsListView view, int firstVisibleItem, int visibleItemCount,
                    final int totalItemCount) {
                // Synchronize chart and group header on scroll
                if (_isScrolling) {
                    // The last 2 items are the "grey" filler and the last tweet
                    if (visibleItemCount <= 2) {
                        _listView.post(new Runnable() {
                            @Override
                            public void run() {
                                _listView.setSelection(totalItemCount - 2);
                            }
                        });
                    }
                }

                // The last item is the "grey" filler
                if (visibleItemCount > 1) {
                    Tweet item = _twitterListAdapter.getItem(firstVisibleItem);
                    if (item != null) {
                        updateTwitterMark(item.getAggregated());
                    }
                    updateGroupHeader(item);
                }
            }
        });

        // Handle "condensed" checkbox event
        _condensedCheckbox = (CheckBox) findViewById(R.id.condensed_tweets_checkbox);
        _condensedCheckbox.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                // Force refresh
                _twitterListAdapter.setShowCondensedView(isChecked);
                if (isChecked) {
                    // Use black line as divider for condensed view
                    _listView.setDivider(_condensedDivider);
                } else {
                    // Restore original divider
                    _listView.setDivider(_normalDivider);
                }
            }
        });
        _twitterListAdapter.setShowCondensedView(_condensedCheckbox.isChecked());
        _normalDivider = _listView.getDivider();
        // Use black line as divider for condensed view
        _condensedDivider = getResources().getDrawable(R.drawable.twitter_list_divider);
        if (_condensedCheckbox.isChecked()) {
            _listView.setDivider(_condensedDivider);
        }

        //Get the timestamp parameter passed to the activity
        _timestampArg = getIntent().getLongExtra(TIMESTAMP_ARG, 0);

        // Load initial data
        loadData();
    }

    /**
     * Scroll the twitter list to the given timestamp
     *
     * @param timestamp The timestamp to position the top of the list
     */
    private void scrollTo(long timestamp) {
        if (_listView != null) {
            int position = _twitterListAdapter.getPositionByTimestamp(timestamp);
            _listView.setSelection(position < 0 ? 0 : position);
        }
    }

    /**
     * Update Instance header part of this view.
     * The instance header is composed of the instance anomaly chart and
     * the time slider view.
     */
    private void updateInstanceHeader() {
        if (_chartData == null) {
            return;
        }
        // Update server header
        _instanceChartFragment.setChartData(_chartData);

        // Update time slider
        Pair<Long, Long> range = getTimeRange();
        _timeView.setAggregation(_chartData.getAggregation());
        _timeView.setEndDate(range.second - DataUtils.MILLIS_PER_HOUR);
    }


    /**
     * Return the current time range
     *
     * @return {@link com.numenta.core.utils.Pair} with the current time range:<br>
     * <em>Pair.first</em> = start time and <em>Pair.second</em> = end time
     */
    private Pair<Long, Long> getTimeRange() {
        long endTime;
        long start;
        if (_metricData != null) {
            start = _metricData.getStartTimestamp();
            endTime = _metricData.getEndTimestamp() + DataUtils.MILLIS_PER_HOUR;
        } else {
            endTime = _timestampArg + DataUtils.MILLIS_PER_HOUR;
            start = endTime - DataUtils.MILLIS_PER_HOUR * TaurusApplication.getTotalBarsOnChart();
        }
        return new Pair<Long, Long>(start, endTime);
    }

    /**
     * Update the twitter volume chart/metric detail chart part of this view.
     */
    private void updateTwitterChart() {
        if (_metricData == null) {
            return;
        }
        _lineChartView.setData(_metricData.getRawData());
        _lineChartView.setAnomalies(_metricData.getAnomalies());
    }

    /**
     * Update Twitter selection mark from the given timestamp
     *
     * @param timestamp the selected timestamp to position the mark. If the timestamp is outside
     *                  the data time range the selection will be cleared
     */
    private void updateTwitterMark(long timestamp) {
        int position = -1;
        // Make sure timestamp is within data range
        Pair<Long, Long> range = getTimeRange();
        if (timestamp >= range.first && timestamp <= range.second) {
            // Calculate data position based on timestamp
            position = Math.round((timestamp - range.first) / DataUtils.METRIC_DATA_INTERVAL);
        }
        _lineChartView.setSelection(position);
    }

    /**
     * Update group header using information from the given tweet
     *
     * @param tweet Tweet object to get header information from, {@code null} to hide the header
     */
    private void updateGroupHeader(Tweet tweet) {
        if (tweet != null) {
            // Make sure it is visible
            if (_groupHeader.getVisibility() != View.VISIBLE) {
                _groupHeader.setVisibility(View.VISIBLE);
            }

            _date.setText(String.format("%1$tl:%1$tM%1$tp", tweet.getAggregated()));
            _tweetCount.setText(Integer.toString(tweet.getAggregatedCount()));
        } else {
            _groupHeader.setVisibility(View.GONE);
        }
    }

    /**
     * Load all the data in the background
     */
    private void loadData() {
        if (_loading) {
            return;
        }
        synchronized (this) {
            if (_loading) {
                return;
            }
            // Cancel previous task
            if (_instanceLoader != null) {
                cancelTrackedBackgroundTask(_instanceLoader);
            }
            _loading = true;
        }

        _instanceLoader = new AsyncTask<Void, Object, Void>() {

            long _bucketTimestamp = Long.MAX_VALUE;

            long _initialTimestamp = getIntent().getLongExtra(SELECTED_TIMESTAMP_ARG, 0);

            // Group tweets with the same text and re-tweets into buckets
            TreeMap<Tweet, Integer> _buckets = new TreeMap<Tweet, Integer>(SORT_BY_TEXT);

            // Aggregated tweet count by time based on metric raw data
            TreeMap<Long, Integer> _tweetCountByDate = new TreeMap<Long, Integer>();

            @Override
            protected Void doInBackground(Void... params) {
                if (_chartData == null || _metricData == null) {
                    String metricId = getIntent().getStringExtra(METRIC_ID_ARG);
                    _metric = TaurusApplication.getDatabase().getMetric(metricId);
                    if (_metric != null) {
                        // Load instance header data
                        _chartData = new InstanceAnomalyChartData(_metric.getInstanceId(),
                                TaurusApplication.getAggregation());
                        _chartData.setEndDate(new Date(_timestampArg));
                        if (_chartData.load()) {
                            publishProgress(_chartData);
                        }

                        // Load metric data
                        _metricData = new MetricAnomalyChartData(_metric, _timestampArg);
                        if (_metricData.load()) {
                            publishProgress(_metricData);
                        }

                        // Load twitter data
                        loadTwitterData();
                    }
                }
                return null;
            }

            @Override
            protected void onProgressUpdate(Object... values) {
                // Publishing empty progress only flushes the current bucket
                if (values == null || values.length == 0) {
                    flushBucket();
                    return;
                }
                Object data = values[0];
                if (data instanceof Tweet) {
                    // One tweet at the time, see "onTweetData" below
                    Tweet tweet = (Tweet) data;

                    // Bucket repeated tweets into time buckets
                    long tweetDate = tweet.getAggregated();
                    if (tweetDate <= _bucketTimestamp) {
                        // Empty old buckets
                        flushBucket();

                        // Round to prev bucket
                        _bucketTimestamp = (tweetDate / DataUtils.METRIC_DATA_INTERVAL - 1)
                                * DataUtils.METRIC_DATA_INTERVAL;
                    }

                    // Update count
                    Integer count = _buckets.get(tweet);
                    _buckets.put(tweet, count == null ? 1 : count + 1);
                } else if (data instanceof InstanceAnomalyChartData) {
                    updateInstanceHeader();
                } else if (data instanceof MetricAnomalyChartData) {
                    updateTwitterChart();
                }
            }

            @Override
            protected void onCancelled(Void aVoid) {
                _loading = false;
                _loadingMessage.setVisibility(View.GONE);
            }

            @Override
            protected void onPostExecute(Void param) {
                // Make sure to flush last tweets
                flushBucket();
                _loading = false;
                _loadingMessage.setVisibility(View.GONE);
            }

            /**
             * Flush tweets staged in bucket
             */
            void flushBucket() {
                if (_buckets.isEmpty()) {
                    return;
                }
                Tweet tweet;
                Integer count;
                _twitterListAdapter.setNotifyDataSetChanged(false);
                for (Map.Entry<Tweet, Integer> entry : _buckets.entrySet()) {
                    tweet = entry.getKey();
                    // Ignore empty tweets
                    if (tweet.getCanonicalText().isEmpty()) {
                        continue;
                    }

                    // Update retweet count
                    count = entry.getValue();
                    tweet.setRetweetCount(count);

                    // Update aggregate count
                    count = _tweetCountByDate.get(tweet.getAggregated());
                    if (count != null) {
                        tweet.setAggregatedCount(count);
                    }

                    _twitterListAdapter.add(tweet);
                }
                _twitterListAdapter.sort(SORT_BY_DATE);
                _twitterListAdapter.notifyDataSetChanged();
                _buckets.clear();

                // Find selected timestamp
                final int position = _twitterListAdapter.getPositionByTimestamp(_initialTimestamp);
                if (position >= 0) {
                    _listView.post(new Runnable() {
                        @Override
                        public void run() {
                            _listView.setSelection(position);
                        }
                    });
                }
            }

            /**
             * Load Raw tweets from backend
             */
            void loadTwitterData() {
                try {
                    // Get tweets from the server
                    TaurusClient connection = TaurusApplication.connectToTaurus();
                    if (connection != null && _metric != null && _metricData != null) {
                        // Get current time range
                        Pair<Long, Long> range = getTimeRange();
                        long time = range.first - DataUtils.METRIC_DATA_INTERVAL;

                        // Calculate total number of tweets based on the metric values
                        float[] values = _metricData.getRawData();
                        if (values == null) {
                            return; // No data
                        }
                        int total = 0;
                        long selectedTimestamp = 0;
                        for (float val : values) {
                            if (selectedTimestamp == 0 && time >= _initialTimestamp) {
                                selectedTimestamp = time;
                            }
                            if (!Float.isNaN(val) && val > 0) {
                                total += val;
                                _tweetCountByDate.put(time, (int) val);
                            }
                            time += DataUtils.METRIC_DATA_INTERVAL;
                        }

                        // Find max count value within time tolerance
                        SortedMap<Long, Integer> valuesInRange = _tweetCountByDate
                                .subMap(selectedTimestamp - _twitterListAdapter.TIMESTAMP_TOLERANCE,
                                        selectedTimestamp + _twitterListAdapter.TIMESTAMP_TOLERANCE + 1);
                        int max = -1;
                        for (SortedMap.Entry<Long, Integer> entry : valuesInRange.entrySet()) {
                            if (entry.getValue() > max) {
                                max = entry.getValue();
                                selectedTimestamp = entry.getKey();
                            }
                        }

                        // When the total number of tweets is very large (500+),
                        // break loading task into smaller chunks to avoid long wait time on the UI
                        if (total > 500) {

                            // Show "loading" message
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    _loadingMessage.setVisibility(View.VISIBLE);
                                }
                            });
                            // First load data from the user selected date.
                            connection.getTweets(_metric.getName(),
                                    new Date(selectedTimestamp),
                                    new Date(selectedTimestamp + DataUtils.METRIC_DATA_INTERVAL),
                                    new YOMPClient.DataCallback<Tweet>() {
                                        @Override
                                        public boolean onData(Tweet tweet) {
                                            publishProgress(tweet);
                                            return !isCancelled();
                                        }
                                    });
                            // Force flush current bucket
                            publishProgress();

                            // Load rest of the data
                            if (range.first < selectedTimestamp) {
                                // Get lower half
                                connection.getTweets(_metric.getName(),
                                        new Date(range.first),
                                        new Date(selectedTimestamp),
                                        new YOMPClient.DataCallback<Tweet>() {
                                            @Override
                                            public boolean onData(Tweet tweet) {
                                                publishProgress(tweet);
                                                return !isCancelled();
                                            }
                                        });
                                // Force flush current bucket
                                publishProgress();
                            }
                            // Load upper half, skip selection because it was load already
                            selectedTimestamp += DataUtils.METRIC_DATA_INTERVAL;
                            if (range.second > selectedTimestamp) {
                                connection.getTweets(_metric.getName(),
                                        new Date(selectedTimestamp),
                                        new Date(range.second),
                                        new YOMPClient.DataCallback<Tweet>() {
                                            @Override
                                            public boolean onData(Tweet tweet) {
                                                publishProgress(tweet);
                                                return !isCancelled();
                                            }
                                        });
                            }
                        } else {
                            // Load everything, no need to load selection first
                            connection.getTweets(_metric.getName(),
                                    new Date(range.first), new Date(range.second),
                                    new YOMPClient.DataCallback<Tweet>() {
                                        @Override
                                        public boolean onData(Tweet tweet) {
                                            publishProgress(tweet);
                                            return !isCancelled();
                                        }
                                    });
                        }
                    }
                } catch (IOException e) {
                    Log.e(TAG, "Failed to get tweets from the server", e);
                } catch (YOMPException e) {
                    Log.e(TAG, "Failed to get tweets from the server", e);
                }
            }
        };
        _instanceLoader.executeOnExecutor(TaurusApplication.getWorkerThreadPool());
        trackBackgroundTask(_instanceLoader);

    }
}
