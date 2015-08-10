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

package com.numenta.taurus.service;

import com.amazonaws.AmazonClientException;
import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.AWSCredentialsProvider;
import com.amazonaws.internal.StaticCredentialsProvider;
import com.amazonaws.regions.Region;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClient;
import com.amazonaws.services.dynamodbv2.model.AttributeValue;
import com.amazonaws.services.dynamodbv2.model.ComparisonOperator;
import com.amazonaws.services.dynamodbv2.model.Condition;
import com.amazonaws.services.dynamodbv2.model.QueryRequest;
import com.amazonaws.services.dynamodbv2.model.QueryResult;
import com.amazonaws.services.dynamodbv2.model.ScanRequest;
import com.amazonaws.services.dynamodbv2.model.ScanResult;
import com.numenta.core.data.AggregationType;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.InstanceData;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.ObjectNotFoundException;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.NetUtils;
import com.numenta.core.utils.Version;
import com.numenta.taurus.BuildConfig;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.TaurusDataFactory;
import com.numenta.taurus.data.Tweet;
import com.numenta.taurus.metric.MetricType;

import org.json.JSONException;
import org.json.JSONObject;

import android.support.annotation.NonNull;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentNavigableMap;
import java.util.concurrent.ConcurrentSkipListMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * {@inheritDoc}
 *
 * <p><b>Taurus Client API</b></p>
 * This class is used to access taurus data from DynamoDB.
 */
public class TaurusClient implements YOMPClient {

    /**
     * Used by the client to notify the caller the when a new metric data value is ready
     */
    public interface MetricValuesCallback {

        /**
         * Called on every new data value
         *
         * @param metricId  The metric id
         * @param timestamp The value timestamp
         * @param value     The metric raw value for the timestamp
         * @param anomaly   The metric anomaly value for the timestamp
         * @return false to stop loading
         */

        boolean onData(String metricId, long timestamp, float value, float anomaly);
    }

    final class CachedMetricValue {

        float value;

        float anomaly;
    }

    // Cache metric values
    final ConcurrentHashMap<String, ConcurrentSkipListMap<Long, CachedMetricValue>>
            _cachedMetricValues = new ConcurrentHashMap<String, ConcurrentSkipListMap<Long, CachedMetricValue>>();

    private static final String TAG = TaurusClient.class.getSimpleName();

    private static final Pattern DATE_HOUR_FORMAT_REGEX = Pattern
            .compile("(\\d+)-(\\d+)-(\\d+).(\\d+)");

    public static final String METRIC_TABLE = "taurus.metric" + BuildConfig.TABLE_SUFFIX;

    public static final String METRIC_DATA_TABLE = "taurus.metric_data" + BuildConfig.TABLE_SUFFIX;

    public static final String INSTANCE_DATA_HOURLY_TABLE =
            "taurus.instance_data_hourly" + BuildConfig.TABLE_SUFFIX;

    public static final String TWEETS_TABLE = "taurus.metric_tweets" + BuildConfig.TABLE_SUFFIX;

    final AmazonDynamoDBClient _awsClient;

    final String _server;


    /**
     * Construct Taurus API client.
     *
     * @param provider The AWS credential provider to use.
     *                 Usually {@link TaurusApplication#getAWSCredentialProvider()}
     */
    public TaurusClient(AWSCredentialsProvider provider) {
        // DynamoDB Server. Use "http://10.0.2.2:8300" for local server or null for AWS
        this(provider, BuildConfig.SERVER_URL);
    }

    /**
     * Construct Taurus API client.
     *
     * @param provider  The AWS credential provider to use.
     *                  Usually {@link TaurusApplication#getAWSCredentialProvider()}
     * @param serverUrl DynamoDB Server. Use "http://10.0.2.2:8300" for local server or
     *                  null for AWS
     */
    public TaurusClient(AWSCredentialsProvider provider, String serverUrl) {
        _server = serverUrl;
        AWSCredentialsProvider credentialsProvider = provider;
        if (credentialsProvider == null) {
            // Use Dummy credentials for local server
            credentialsProvider = new StaticCredentialsProvider(new AWSCredentials() {
                public String getAWSAccessKeyId() {
                    // Returns dummy value
                    return "taurus";
                }

                @Override
                public String getAWSSecretKey() {
                    // Returns dummy value
                    return "taurus";
                }
            });
        }
        _awsClient = new AmazonDynamoDBClient(credentialsProvider);
        if (BuildConfig.REGION != null) {
            // Override default region
            _awsClient.setRegion(Region.getRegion(Regions.fromName(BuildConfig.REGION)));
        }
        if (_server != null) {
            // Override server endpoint, Usually the local DynamoDB server
            _awsClient.setEndpoint(_server);
        }
    }

    /**
     * Get list of tweets for the given metric filtered by the given time range returning the
     * results as they become available asynchronously.
     *
     * @param metricName The metric name to retrieve the tweets from
     * @param from       The start time (aggregated) inclusive.
     * @param to         The end time (aggregated) inclusive.
     * @param callback   Callback for asynchronous call. It will be called on every {@link Tweet}
     */
    public void getTweets(String metricName, Date from, Date to,
            DataCallback<Tweet> callback) throws YOMPException, IOException {
        getTweets(metricName, from, to, -1, callback);
    }

    /**
     * Get list of tweets for the given metric filtered by the given time range returning the
     * results as they become available asynchronously.
     *
     * @param metricName The metric name to retrieve the tweets from
     * @param from       The start time (aggregated) inclusive.
     * @param to         The end time (aggregated) inclusive.
     * @param limit      Maximum number of items to return. -1 for unlimited.
     * @param callback   Callback for asynchronous call. It will be called on every {@link Tweet}
     */
    public void getTweets(String metricName, Date from, Date to, int limit,
            DataCallback<Tweet> callback) throws YOMPException, IOException {
        if (metricName == null) {
            throw new ObjectNotFoundException("Cannot get tweets without metric name");
        }

        final TaurusDataFactory dataFactory = TaurusApplication.getInstance().getDataFactory();
        final SimpleDateFormat timestampFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss",
                Locale.US);
        timestampFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        // Key conditions
        Map<String, Condition> keyConditions = new HashMap<String, Condition>();

        // uid = modelId
        Condition modelIdCond = new Condition()
                .withComparisonOperator(ComparisonOperator.EQ)
                .withAttributeValueList(new AttributeValue(metricName));
        keyConditions.put("metric_name", modelIdCond);

        Condition timestampCondition;
        if (from != null && to != null) {
            // timestamp >= from and timestamp <=to
            timestampCondition = new Condition()
                    .withComparisonOperator(ComparisonOperator.BETWEEN)
                    .withAttributeValueList(
                            new AttributeValue().withS(timestampFormat.format(from)),
                            new AttributeValue().withS(timestampFormat.format(to)));
            keyConditions.put("agg_ts", timestampCondition);
        } else if (from != null) {
            // timestamp >= from
            timestampCondition = new Condition()
                    .withComparisonOperator(ComparisonOperator.GT)
                    .withAttributeValueList(new AttributeValue()
                            .withS(timestampFormat.format(from)));
            keyConditions.put("agg_ts", timestampCondition);
        } else if (to != null) {
            // timestamp <= to
            timestampCondition = new Condition()
                    .withComparisonOperator(ComparisonOperator.LT)
                    .withAttributeValueList(new AttributeValue()
                            .withS(timestampFormat.format(to)));
            keyConditions.put("agg_ts", timestampCondition);
        }

        // Prepare query request
        QueryRequest query = new QueryRequest()
                .withTableName(TWEETS_TABLE)
                .withAttributesToGet("tweet_uid", "userid", "text", "username",
                        "agg_ts", "created_at", "retweet_count")
                .withKeyConditions(keyConditions)
                .withScanIndexForward(false)
                .withIndexName("taurus.metric_data-metric_name_index");
        if (limit != -1) {
            query.setLimit(limit);
        }

        QueryResult result;
        String tweetId;
        String userId;
        String userName;
        String text;
        Date created;
        Date aggregated;
        AttributeValue retweet;
        int retweetCount;
        Map<String, AttributeValue> lastKey;
        try {
            do {
                // Get results
                result = _awsClient.query(query);
                for (Map<String, AttributeValue> item : result.getItems()) {
                    tweetId = item.get("tweet_uid").getS();
                    userId = item.get("userid").getS();
                    text = item.get("text").getS();
                    userName = item.get("username").getS();
                    aggregated = DataUtils.parseYOMPDate(item.get("agg_ts").getS());
                    created = DataUtils.parseYOMPDate(item.get("created_at").getS());

                    // "retweet_count" is optional
                    retweet = item.get("retweet_count");
                    if (retweet != null && retweet.getN() != null) {
                        retweetCount = Integer.parseInt(retweet.getN());
                    } else {
                        retweetCount = 0;
                    }
                    if (!callback
                            .onData(dataFactory.createTweet(tweetId, aggregated, created, userId,
                                    userName, text, retweetCount))) {
                        // Canceled by the user
                        break;
                    }
                }
                // Make sure to get all pages
                lastKey = result.getLastEvaluatedKey();
                query.setExclusiveStartKey(lastKey);
            } while (lastKey != null);
        } catch (AmazonClientException e) {
            // Wraps Amazon's unchecked exception as IOException
            throw new IOException(e);
        }
    }

    @Override
    public boolean isOnline() {
        return NetUtils.isConnected();
    }

    @Override
    public void login() throws IOException, YOMPException {
        // Do nothing
    }

    @Override
    public void getMetricData(String modelId, Date from, Date to,
            final DataCallback<MetricData> callback)
            throws YOMPException, IOException {
        throw new YOMPException("Not Implemented");
    }

    /**
     * Get Metric values only from DynamoDB
     *
     * @param modelId   The model to get the data from
     * @param from      The starting timestamp
     * @param to        The ending timestamp
     * @param ascending Specifies ascending (true) or descending (false)
     * @param callback  User defined callback to receive data
     */
    public void getMetricValues(@NonNull String modelId, @NonNull Date from, @NonNull Date to,
            boolean ascending, @NonNull MetricValuesCallback callback)
            throws YOMPException, IOException {

        // Get metric from cache
        ConcurrentSkipListMap<Long, CachedMetricValue> cache = _cachedMetricValues.get(modelId);
        if (cache == null) {
            cache = new ConcurrentSkipListMap<Long, CachedMetricValue>();
            ConcurrentSkipListMap<Long, CachedMetricValue> oldValues =
                    _cachedMetricValues.putIfAbsent(modelId, cache);
            if (oldValues != null) {
                // Found old cached values
                cache = oldValues;
            }
        }

        // Try to get metric values from cache
        ConcurrentNavigableMap<Long, CachedMetricValue> cached =
                cache.subMap(from.getTime(), true, to.getTime(), true);
        if (!cached.isEmpty()) {
            Log.d(TAG, "from=" + from.getTime() + ", firstKey=" + cache.firstKey());
            Log.d(TAG, "to=" + to.getTime() + ", lastKey=" + cache.lastKey());
            // Check if we found the values in the cache
            if (!cached.isEmpty()) {
                // Return cached values sorted based on "ascending" order
                Set<Map.Entry<Long, CachedMetricValue>> values;
                if (ascending) {
                    values = cached.entrySet();
                } else {
                    values = cached.descendingMap().entrySet();
                }
                for (Map.Entry<Long, CachedMetricValue> metricValue : values) {
                    if (!callback.onData(modelId, metricValue.getKey(),
                            metricValue.getValue().value, metricValue.getValue().anomaly)) {
                        // Canceled by the user
                        break;
                    }
                }
                return;
            }
        }
        final SimpleDateFormat timestampFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss",
                Locale.US);
        timestampFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        // Key conditions
        Map<String, Condition> keyConditions = new HashMap<String, Condition>();

        // uid = modelId
        keyConditions.put("uid", new Condition()
                .withComparisonOperator(ComparisonOperator.EQ)
                .withAttributeValueList(new AttributeValue(modelId)));

        // timestamp >= from and timestamp <=to
        Condition timestampCondition = new Condition()
                .withComparisonOperator(ComparisonOperator.BETWEEN);
        if (from.compareTo(to) <= 0) {
            timestampCondition.withAttributeValueList(
                    new AttributeValue().withS(timestampFormat.format(from)),
                    new AttributeValue().withS(timestampFormat.format(to)));
        } else {
            // FIXME This should not happen.
            Log.e(TAG,
                    "TaurusClient#getMetricValues: 'from date' should not be greater than 'to date");
            timestampCondition.withAttributeValueList(
                    new AttributeValue().withS(timestampFormat.format(to)),
                    new AttributeValue().withS(timestampFormat.format(from)));

        }
        keyConditions.put("timestamp", timestampCondition);

        // Prepare query request
        QueryRequest query = new QueryRequest()
                .withTableName(METRIC_DATA_TABLE)
                .withAttributesToGet("timestamp", "metric_value", "anomaly_score")
                .withKeyConditions(keyConditions)
                .withScanIndexForward(ascending);

        QueryResult result;
        Map<String, AttributeValue> lastKey;
        try {
            do {
                long timestamp;
                // Get results
                result = _awsClient.query(query);
                for (Map<String, AttributeValue> item : result.getItems()) {
                    CachedMetricValue metricValue = new CachedMetricValue();
                    timestamp = DataUtils.parseYOMPDate(item.get("timestamp").getS()).getTime();
                    metricValue.value = Float.parseFloat(item.get("metric_value").getN());
                    metricValue.anomaly = Float.parseFloat(item.get("anomaly_score").getN());
                    cache.put(timestamp, metricValue);
                    if (!callback
                            .onData(modelId, timestamp, metricValue.value, metricValue.anomaly)) {
                        // Canceled by the user
                        break;
                    }
                }
                // Make sure to get all pages
                lastKey = result.getLastEvaluatedKey();
                query.setExclusiveStartKey(lastKey);
            } while (lastKey != null);
        } catch (AmazonClientException e) {
            // Wraps Amazon's unchecked exception as IOException
            throw new IOException(e);
        }
    }

    /**
     * Get hourly aggregated data for all instances for a single day for the given time range
     *
     * @param date      The date to get the data from
     * @param fromHour  The start hour
     * @param toHour    The end hour
     * @param ascending Specifies ascending (true) or descending (false)
     * @param callback  User defined callback to receive instance data
     */
    public void getAllInstanceDataForDate(@NonNull Date date, int fromHour, int toHour,
            boolean ascending, @NonNull DataCallback<InstanceData> callback)
            throws YOMPException, IOException {

        Map<String, Condition> keyConditions = new HashMap<String, Condition>();

        // Use "date" as hash key
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        keyConditions.put("date", new Condition()
                .withComparisonOperator(ComparisonOperator.EQ)
                .withAttributeValueList(new AttributeValue(dateFormat.format(date))));

        String start = fromHour > 9 ? Integer.toString(fromHour) : "0" + fromHour;
        if (fromHour == toHour) {
            // One single hour
            keyConditions.put("hour", new Condition()
                    .withComparisonOperator(ComparisonOperator.EQ)
                    .withAttributeValueList(new AttributeValue(start)));
        } else {
            // Use "hour" as range key
            String end = toHour > 9 ? Integer.toString(toHour) : "0" + toHour;
            keyConditions.put("hour", new Condition()
                    .withComparisonOperator(ComparisonOperator.BETWEEN)
                    .withAttributeValueList(new AttributeValue(start), new AttributeValue(end)));
        }

        // Prepare query request
        QueryRequest query = new QueryRequest()
                .withTableName(INSTANCE_DATA_HOURLY_TABLE)
                .withAttributesToGet("instance_id", "date_hour", "anomaly_score")
                .withKeyConditions(keyConditions)
                .withScanIndexForward(ascending)
                .withIndexName("taurus.instance_data_hourly-date_hour_index");

        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        QueryResult result;
        String instanceId;
        float anomalyScore;
        float score;
        Map<String, AttributeValue> scores;
        Map<String, AttributeValue> lastKey;
        Matcher match;
        EnumSet<MetricType> metricMask;
        TaurusDataFactory dataFactory = TaurusApplication.getInstance().getDataFactory();
        try {
            do {
                // Get data from DynamoDB
                result = _awsClient.query(query);
                for (Map<String, AttributeValue> item : result.getItems()) {
                    // Convert "date_hour" to java milliseconds time
                    match = DATE_HOUR_FORMAT_REGEX.matcher(item.get("date_hour").getS());
                    if (match.matches()) {
                        calendar.clear();
                        calendar.set(Integer.parseInt(match.group(1)),
                                Integer.parseInt(match.group(2)) - 1,
                                Integer.parseInt(match.group(3)),
                                Integer.parseInt(match.group(4)), 0, 0);
                        instanceId = item.get("instance_id").getS();

                        // Get max anomaly scores
                        scores = item.get("anomaly_score").getM();
                        anomalyScore = 0;
                        double scaledScore;
                        metricMask = EnumSet.noneOf(MetricType.class);
                        for (Map.Entry<String, AttributeValue> entry : scores.entrySet()) {
                            score = Float.parseFloat(entry.getValue().getN());
                            scaledScore = DataUtils.logScale(Math.abs(score));
                            if (scaledScore >= TaurusApplication.getYellowBarFloor()) {
                                metricMask.add(MetricType.valueOf(entry.getKey()));
                            }
                            anomalyScore = Math.max(score, anomalyScore);
                        }

                        if (!callback.onData(dataFactory.createInstanceData(
                                instanceId, AggregationType.Day, calendar.getTimeInMillis(),
                                anomalyScore, metricMask))) {
                            // Canceled by the user
                            break;
                        }
                    }
                }
                // Make sure to get all pages
                lastKey = result.getLastEvaluatedKey();
                query.setExclusiveStartKey(lastKey);
            } while (lastKey != null);
        } catch (AmazonClientException e) {
            // Wraps Amazon's unchecked exception as IOException
            throw new IOException(e);
        }
    }

    /**
     * Get hourly aggregated data for all instances for the given date range
     *
     * @param from      The starting timestamp
     * @param to        The ending timestamp
     * @param ascending Specifies ascending (true) or descending (false)
     * @param callback  User defined callback to receive instance data
     */
    public void getAllInstanceData(@NonNull Date from, @NonNull Date to, Boolean ascending,
            final @NonNull DataCallback<InstanceData> callback) throws YOMPException, IOException {

        Calendar fromDate = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        fromDate.clear();
        fromDate.setTime(from);
        int fromDay = fromDate.get(Calendar.DAY_OF_YEAR);

        Calendar toDate = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        toDate.clear();
        toDate.setTime(to);
        int toDay = toDate.get(Calendar.DAY_OF_YEAR);
        Calendar date = toDate;

        // Check if "from" date and "to" date falls on the same day
        if (fromDay == toDay) {
            // Get latest hours from the same day
            getAllInstanceDataForDate(from, fromDate.get(Calendar.HOUR_OF_DAY),
                    toDate.get(Calendar.HOUR_OF_DAY), ascending, callback);
        } else {
            // Get Multiple days
            int totalDays = toDay - fromDay;
            int interval = -1;

            // Check if loading in reverse order
            if (ascending) {
                date = fromDate;
                interval = 1;
            }

            for (int i = 0; i <= totalDays; i++) {
                getAllInstanceDataForDate(date.getTime(), 0, 23, ascending, callback);
                date.add(Calendar.DAY_OF_YEAR, interval);
            }
        }
    }

    @Override
    public List<Metric> getMetrics() throws YOMPException, IOException {
        String uid;
        String name;
        String server;
        String metricType;
        String metricTypeName;
        String symbol;
        JSONObject parameters;
        ArrayList<Metric> metrics = new ArrayList<Metric>();

        TaurusDataFactory dataFactory = TaurusApplication.getInstance().getDataFactory();

        // Scan all metrics
        ScanRequest request = new ScanRequest()
                .withTableName(METRIC_TABLE)
                .withAttributesToGet("uid", "name", "server", "metricType", "metricTypeName",
                        "symbol");
        ScanResult result;
        Map<String, AttributeValue> lastKey;
        try {
            do {
                result = _awsClient.scan(request);
                for (Map<String, AttributeValue> item : result.getItems()) {
                    uid = item.get("uid").getS();
                    name = item.get("name").getS();
                    server = item.get("server").getS();
                    metricType = item.get("metricType").getS();
                    metricTypeName = item.get("metricTypeName").getS();
                    symbol = item.get("symbol").getS();
                    // FIXME: TAUR-817: Create taurus specific "metric" table
                    parameters = new JSONObject(
                            "{\"metricSpec\":{\"userInfo\": {\"symbol\": \"" + symbol
                                    + "\",\"metricType\": \"" + metricType
                                    + "\",\"metricTypeName\": \"" + metricTypeName + "\"}}}");
                    metrics.add(dataFactory.createMetric(uid, name, server, server, 0, parameters));
                }
                // Make sure to get all pages
                lastKey = result.getLastEvaluatedKey();
                request.setExclusiveStartKey(lastKey);
            } while (lastKey != null);
        } catch (JSONException e) {
            throw new YOMPException("JSON Parser error", e);
        } catch (AmazonClientException e) {
            // Wraps Amazon's unchecked exception as IOException
            throw new IOException(e);
        }
        return metrics;
    }

    @Override
    public String getServerUrl() {
        return _server;
    }

    @Override
    public Version getServerVersion() {
        return Version.UNKNOWN;
    }

    /**
     * Generate a list of Notifications based on user preferences using the anomaly scores from the
     * local database
     */
    @Override
    public List<Notification> getNotifications() throws YOMPException, IOException {
        return null;
    }

    @Override
    public List<Annotation> getAnnotations(Date from, Date to) throws YOMPException, IOException {
        return null;
    }

    @Override
    public void deleteAnnotation(Annotation annotation) throws YOMPException, IOException {
    }

    @Override
    public Annotation addAnnotation(Date timestamp, String server, String message, String user)
            throws YOMPException, IOException {
        return null;
    }

    /**
     * Do nothing in Taurus since Notifications are all local
     */
    @Override
    public void acknowledgeNotifications(String[] notifications) throws YOMPException, IOException {
        // do nothing, taurus notifications are managed by the client
    }

    @Override
    public String getServerName() {
        return "Taurus";
    }


    /**
     * Clears all cached data
     */
    public void clearCache() {
        _cachedMetricValues.clear();
    }
}
