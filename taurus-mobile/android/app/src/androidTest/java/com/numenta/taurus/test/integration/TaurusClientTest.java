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

package com.numenta.taurus.test.integration;

import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.internal.StaticCredentialsProvider;
import com.amazonaws.regions.Region;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClient;
import com.amazonaws.services.dynamodbv2.model.AttributeDefinition;
import com.amazonaws.services.dynamodbv2.model.AttributeValue;
import com.amazonaws.services.dynamodbv2.model.BatchWriteItemRequest;
import com.amazonaws.services.dynamodbv2.model.BatchWriteItemResult;
import com.amazonaws.services.dynamodbv2.model.CreateTableRequest;
import com.amazonaws.services.dynamodbv2.model.GlobalSecondaryIndex;
import com.amazonaws.services.dynamodbv2.model.KeySchemaElement;
import com.amazonaws.services.dynamodbv2.model.KeyType;
import com.amazonaws.services.dynamodbv2.model.ListTablesResult;
import com.amazonaws.services.dynamodbv2.model.Projection;
import com.amazonaws.services.dynamodbv2.model.ProjectionType;
import com.amazonaws.services.dynamodbv2.model.ProvisionedThroughput;
import com.amazonaws.services.dynamodbv2.model.PutRequest;
import com.amazonaws.services.dynamodbv2.model.ResourceInUseException;
import com.amazonaws.services.dynamodbv2.model.ScalarAttributeType;
import com.amazonaws.services.dynamodbv2.model.WriteRequest;
import com.amazonaws.services.dynamodbv2.util.Tables;
import com.numenta.core.data.InstanceData;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.service.YOMPException;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.taurus.BuildConfig;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.data.TaurusDataFactory;
import com.numenta.taurus.data.Tweet;
import com.numenta.taurus.metric.MetricType;
import com.numenta.taurus.service.TaurusClient;

import junit.framework.TestCase;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Suite;

import android.content.Context;
import android.content.res.Resources;
import android.support.test.runner.AndroidJUnit4;

import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Queue;
import java.util.TimeZone;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@RunWith(AndroidJUnit4.class)
public class TaurusClientTest extends TestCase {

    static final String TAG = TaurusClientTest.class.getSimpleName();

    // Use Dummy credentials. Maje sure to use the same user as "TaurusClient"
    static final AWSCredentials _awsCredentials = new AWSCredentials() {
        public String getAWSAccessKeyId() {
            return "taurus";
        }

        @Override
        public String getAWSSecretKey() {
            return "taurus";
        }
    };

    // URL to local dynamodb test tool.
    private static final java.lang.String SERVER_URL = BuildConfig.SERVER_URL == null ?
            "http://10.0.2.2:8000" : BuildConfig.SERVER_URL;

    private static boolean _deleteTestTables;

    private TaurusClient _taurusClient;

    // Number of instances to create for the tests
    static final int INSTANCES = 2;

    // Number of days to create data for the tests
    static final int NUM_OF_DAYS = 1;

    // Test date range
    static final long TEST_START_TIMESTAMP = 1429488000000l;

    static final long TEST_END_TIMESTAMP =
            TEST_START_TIMESTAMP + DataUtils.MILLIS_PER_DAY * NUM_OF_DAYS;


    /**
     * Write all items to the given dynamo db table resending unprocessed items as necessary
     *
     * @param table  The table to write the items to
     * @param values All items enqueued for writing
     */
    static void batchWrite(AmazonDynamoDBClient awsClient, String table, Queue<PutRequest> values) {

        // Process 25 items per batch
        ArrayList<WriteRequest> batch = new ArrayList<WriteRequest>();
        boolean pending = !values.isEmpty();
        while (pending) {
            // Fill batch with 25 items from the queue
            while (batch.size() < 25 && !values.isEmpty()) {
                batch.add(new WriteRequest(values.poll()));
            }
            // Create request with batched items
            BatchWriteItemRequest request = new BatchWriteItemRequest();
            request.addRequestItemsEntry(table, batch);
            BatchWriteItemResult result = awsClient.batchWriteItem(request);
            batch.clear();
            // Add unprocessed items to batch
            if (result.getUnprocessedItems().isEmpty()) {
                // All batched items were processed. Add pending values.
                pending = !values.isEmpty();
            } else {
                // Add unprocessed items to next pending batch
                batch.addAll(result.getUnprocessedItems().get(table));
                pending = true;
            }
        }
    }

    /**
     * Populate metric table
     *
     * Mimic metric item as defined in taurus dynamodb service.
     * <p>
     * See "/products/taurus/taurus/runtime/dynamodb/definitions/metric_dynamodbdefinition.py"
     * </p>
     * <code><pre>
     * ...
     *
     *  schema=[HashKey("uid")],
     *
     * ...
     *
     *  def Item(self):
     *      return namedtuple(
     *          "MetricItem",
     *              field_names=(
     *                  "display_name",
     *                  "name",
     *                  "server",
     *                  "uid",
     *                  "metricTypeName",
     *                  "symbol"
     *              )
     *          )
     * ...
     * </pre></code>
     */
    static void populateMetricTable(AmazonDynamoDBClient awsClient) {

        try {
            // Create metric table
            awsClient.createTable(new CreateTableRequest()
                    .withTableName(TaurusClient.METRIC_TABLE)
                    .withAttributeDefinitions(new AttributeDefinition("uid", ScalarAttributeType.S))
                    .withKeySchema(new KeySchemaElement("uid", KeyType.HASH))
                    .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l)));
            Tables.waitForTableToBecomeActive(awsClient, TaurusClient.METRIC_TABLE);

            Queue<PutRequest> values = new ArrayDeque<PutRequest>();
            String metricName;
            MetricType[] types = MetricType.values();
            for (int i = 0; i < INSTANCES; i++) {
                for (MetricType m : types) {
                    metricName = m.name() + "." + i;
                    values.add(new PutRequest()
                            .addItemEntry("display_name", new AttributeValue(metricName))
                            .addItemEntry("name", new AttributeValue(metricName))
                            .addItemEntry("server", new AttributeValue("id." + i))
                            .addItemEntry("uid",
                                    new AttributeValue("id." + (i * types.length + m.ordinal())))
                            .addItemEntry("metricType", new AttributeValue(m.name()))
                            .addItemEntry("metricTypeName", new AttributeValue(m.name()))
                            .addItemEntry("symbol", new AttributeValue("symbol." + i)));
                }
            }
            batchWrite(awsClient, TaurusClient.METRIC_TABLE, values);
        } catch (ResourceInUseException e) {
            Log.e(TAG, "Failed to create table " + TaurusClient.METRIC_TABLE, e);
        }
    }

    /**
     * Populate metric data table
     *
     * Mimic metric data item as defined in taurus dynamodb service.
     * <p>
     * See "/products/taurus/taurus/runtime/dynamodb/definitions/metric_data_dynamodbdefinition.py"
     * </p>
     * <code><pre>
     * ...
     *      schema=[
     *          HashKey("uid"),
     *          RangeKey("timestamp")
     *      ]
     * ...
     *
     *  def Item(self):
     *      return namedtuple(
     *          "MetricDataItem",
     *              field_names=(
     *                  "uid",
     *                  "timestamp",
     *                  "anomaly_score",
     *                  "metric_value",
     *              )
     *          )
     * ...
     * </pre></code>
     */
    static void populateMetricDataTable(AmazonDynamoDBClient awsClient) {
        SimpleDateFormat timestampFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US);
        timestampFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        try {
            // Create metric data table
            awsClient.createTable(new CreateTableRequest()
                    .withTableName(TaurusClient.METRIC_DATA_TABLE)
                    .withAttributeDefinitions(
                            new AttributeDefinition("uid", ScalarAttributeType.S),
                            new AttributeDefinition("timestamp", ScalarAttributeType.S))
                    .withKeySchema(
                            new KeySchemaElement("uid", KeyType.HASH),
                            new KeySchemaElement("timestamp", KeyType.RANGE))
                    .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l)));
            Tables.waitForTableToBecomeActive(awsClient, TaurusClient.METRIC_DATA_TABLE);

            Queue<PutRequest> values = new ArrayDeque<PutRequest>();
            String score;
            String date;
            int row;
            MetricType[] types = MetricType.values();
            int total = (int) (
                    (TEST_END_TIMESTAMP - TEST_START_TIMESTAMP) / DataUtils.METRIC_DATA_INTERVAL);
            for (int i = 0; i < INSTANCES; i++) {
                for (MetricType m : types) {
                    row = 0;
                    for (long timestamp = TEST_START_TIMESTAMP;
                            timestamp <= TEST_END_TIMESTAMP;
                            timestamp += DataUtils.METRIC_DATA_INTERVAL) {
                        score = Float.toString((float) row / total);
                        row++;
                        date = timestampFormat.format(new Date(timestamp));
                        values.add(new PutRequest()
                                .addItemEntry("uid", new AttributeValue(
                                        "id." + (i * types.length + m.ordinal())))
                                .addItemEntry("timestamp", new AttributeValue(date))
                                .addItemEntry("anomaly_score", new AttributeValue().withN(score))
                                .addItemEntry("metric_value",
                                        new AttributeValue().withN(Float.toString(row))));
                    }
                    batchWrite(awsClient, TaurusClient.METRIC_DATA_TABLE, values);
                    values.clear();
                }
            }
        } catch (ResourceInUseException e) {
            Log.e(TAG, "Failed to create table " + TaurusClient.METRIC_DATA_TABLE, e);
        }
    }


    /**
     * Populate instance data table
     *
     * Mimic data item as defined in taurus dynamodb service.
     * <p>
     * See "/products/taurus/taurus/runtime/dynamodb/definitions/instance_data_hourly_dynamodbdefinition.py"
     * </p>
     * <code><pre>
     * ...
     *  schema=[
     *      HashKey("instance_id"),
     *      RangeKey("date_hour"),
     *  ],
     *  throughput={
     *      "read": taurus.config.getint("dynamodb",
     *                                   "instance_data_hourly_throughput_read"),
     *      "write": taurus.config.getint("dynamodb",
     *                                    "instance_data_hourly_throughput_write")
     *  },
     *
     *  global_indexes=[
     *      GlobalAllIndex(
     *          "taurus.instance_data_hourly-date_hour_index",
     *          parts=[
     *              HashKey("date"),
     *              RangeKey("hour")
     *          ],
     *          throughput={
     *              "read": taurus.config.getint(
     *                  "dynamodb",
     *                  "instance_data_hourly_throughput_read"),
     *              "write": taurus.config.getint(
     *                  "dynamodb",
     *                  "instance_data_hourly_throughput_write")
     *          }
     *      )
     *   ]
     * )
     *
     * ...
     *
     *  def Item(self):
     *      return namedtuple(
     *          "InstanceDataHourlyItem",
     *          field_names=(
     *              "instance_id",
     *              "date_hour",
     *              "date",
     *              "hour",
     *              "anomaly_score",
     *              # Map fields: {"StockVolume", "StockPrice", "TwitterVolume"}
     *          )
     *        )
     * ...
     * </pre></code>
     */
    static void populateInstanceDataTable(AmazonDynamoDBClient awsClient) {

        try {
            // Create metric data table
            awsClient.createTable(new CreateTableRequest()
                    .withTableName(TaurusClient.INSTANCE_DATA_HOURLY_TABLE)
                    .withAttributeDefinitions(
                            new AttributeDefinition("instance_id", ScalarAttributeType.S),
                            new AttributeDefinition("date", ScalarAttributeType.S),
                            new AttributeDefinition("hour", ScalarAttributeType.S),
                            new AttributeDefinition("date_hour", ScalarAttributeType.S))
                    .withKeySchema(
                            new KeySchemaElement("instance_id", KeyType.HASH),
                            new KeySchemaElement("date_hour", KeyType.RANGE))
                    .withGlobalSecondaryIndexes(new GlobalSecondaryIndex()
                            .withIndexName("taurus.instance_data_hourly-date_hour_index")
                            .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l))
                            .withKeySchema(
                                    new KeySchemaElement("date", KeyType.HASH),
                                    new KeySchemaElement("hour", KeyType.RANGE))
                            .withProjection(
                                    new Projection().withProjectionType(ProjectionType.ALL)))
                    .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l)));
            Tables.waitForTableToBecomeActive(awsClient, TaurusClient.INSTANCE_DATA_HOURLY_TABLE);

            SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
            dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

            int total = (int) (
                    (TEST_END_TIMESTAMP - TEST_START_TIMESTAMP) / DataUtils.MILLIS_PER_HOUR);
            Calendar timestamp = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
            String hour;
            String date;
            String instanceId;
            String score;
            int hourOfDay;
            int row;
            Queue<PutRequest> values = new ArrayDeque<PutRequest>();

            for (int i = 0; i < INSTANCES; i++) {
                instanceId = "id." + i;

                row = 0;
                for (long time = TEST_START_TIMESTAMP;
                        time <= TEST_END_TIMESTAMP;
                        time += DataUtils.MILLIS_PER_HOUR) {

                    score = Float.toString((float) row / total);
                    row++;
                    timestamp.clear();
                    timestamp.setTimeInMillis(time);
                    hourOfDay = timestamp.get(Calendar.HOUR_OF_DAY);
                    hour = hourOfDay > 9 ? Integer.toString(hourOfDay) : "0" + hourOfDay;
                    date = dateFormat.format(timestamp.getTime());

                    Map<String, AttributeValue> anomalyScore
                            = new HashMap<String, AttributeValue>();
                    anomalyScore.put("StockPrice", new AttributeValue().withN(score));
                    anomalyScore.put("StockVolume", new AttributeValue().withN(score));
                    anomalyScore.put("TwitterVolume", new AttributeValue().withN(score));

                    values.add(new PutRequest()
                            .addItemEntry("instance_id", new AttributeValue(instanceId))
                            .addItemEntry("date_hour", new AttributeValue(date + "T" + hour))
                            .addItemEntry("date", new AttributeValue(date))
                            .addItemEntry("hour", new AttributeValue(hour))
                            .addItemEntry("anomaly_score",
                                    new AttributeValue().withM(anomalyScore)));
                }
                batchWrite(awsClient, TaurusClient.INSTANCE_DATA_HOURLY_TABLE, values);
                values.clear();
            }
        } catch (ResourceInUseException e) {
            Log.e(TAG, "Failed to create table " + TaurusClient.INSTANCE_DATA_HOURLY_TABLE, e);
        }
    }


    /**
     * Populate metric tweets table
     *
     * Mimic metric tweet as defined in taurus dynamodb service.
     * <p>
     * See "/products/taurus/taurus/runtime/dynamodb/definitions/metric_tweets_dynamodbdefinition.py"
     * </p>
     * <code><pre>
     * ...
     *      schema=[
     *          HashKey("metric_name_tweet_uid"),
     *          RangeKey("agg_ts")
     *      ],
     *      global_indexes=[
     *          GlobalAllIndex(
     *              "taurus.metric_data-metric_name_index",
     *               parts=[
     *                  HashKey("metric_name"),
     *                  RangeKey("agg_ts")
     *               ]
     *          )
     *      ]
     *
     * ...
     *
     *  def Item(self):
     *      return namedtuple(
     *              "MetricTweetsItem",
     *              field_names=(
     *                  "metric_name_tweet_uid",
     *                  "metric_name",
     *                  "tweet_uid",
     *                  "created_at",
     *                  "agg_ts",
     *                  "text",
     *                  "userid",
     *                  "username",
     *                  "retweet_count"
     *              )
     *          )
     * ...
     * </pre></code>
     */
    static void populateTweetsTable(AmazonDynamoDBClient awsClient) {
        SimpleDateFormat timestampFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US);
        timestampFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        try {
            // Create tweets table
            awsClient.createTable(new CreateTableRequest()
                    .withTableName(TaurusClient.TWEETS_TABLE)
                    .withAttributeDefinitions(
                            new AttributeDefinition("metric_name_tweet_uid", ScalarAttributeType.S),
                            new AttributeDefinition("agg_ts", ScalarAttributeType.S),
                            new AttributeDefinition("metric_name", ScalarAttributeType.S))
                    .withKeySchema(
                            new KeySchemaElement("metric_name_tweet_uid", KeyType.HASH),
                            new KeySchemaElement("agg_ts", KeyType.RANGE))
                    .withGlobalSecondaryIndexes(new GlobalSecondaryIndex()
                            .withIndexName("taurus.metric_data-metric_name_index")
                            .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l))
                            .withKeySchema(
                                    new KeySchemaElement("metric_name", KeyType.HASH),
                                    new KeySchemaElement("agg_ts", KeyType.RANGE))
                            .withProjection(
                                    new Projection().withProjectionType(ProjectionType.ALL)))
                    .withProvisionedThroughput(new ProvisionedThroughput(5l, 5l)));
            Tables.waitForTableToBecomeActive(awsClient, TaurusClient.TWEETS_TABLE);

            Queue<PutRequest> values = new ArrayDeque<PutRequest>();
            int tweetId = 0;
            String metricName;
            String dateStr;
            String tweetIdStr;
            for (int i = 0; i < INSTANCES; i++) {

                for (long timestamp = TEST_START_TIMESTAMP;
                        timestamp <= TEST_END_TIMESTAMP;
                        timestamp += DataUtils.METRIC_DATA_INTERVAL) {
                    tweetId++;
                    tweetIdStr = "id." + tweetId;
                    metricName = MetricType.TwitterVolume.name() + "." + i;
                    dateStr = timestampFormat.format(new Date(timestamp));
                    values.add(new PutRequest()
                            .addItemEntry("metric_name_tweet_uid",
                                    new AttributeValue(metricName + "-" + tweetIdStr))
                            .addItemEntry("metric_name", new AttributeValue(metricName))
                            .addItemEntry("tweet_uid", new AttributeValue(tweetIdStr))
                            .addItemEntry("created_at", new AttributeValue(dateStr))
                            .addItemEntry("agg_ts", new AttributeValue(dateStr))
                            .addItemEntry("text",
                                    new AttributeValue("Lorem ipsum for " + tweetIdStr))
                            .addItemEntry("userid", new AttributeValue("user." + tweetId))
                            .addItemEntry("username", new AttributeValue("user." + tweetId))
                            .addItemEntry("retweet_count",
                                    new AttributeValue().withN(Integer.toString(1))));
                }
                batchWrite(awsClient, TaurusClient.TWEETS_TABLE, values);
                values.clear();
            }
        } catch (ResourceInUseException e) {
            Log.e(TAG, "Failed to create table " + TaurusClient.TWEETS_TABLE, e);
        }
    }


    private static AmazonDynamoDBClient getAWSClient(AWSCredentials credentials) {
        AmazonDynamoDBClient awsClient = new AmazonDynamoDBClient(credentials);
        if (BuildConfig.REGION != null) {
            awsClient.setRegion(Region.getRegion(Regions.fromName(BuildConfig.REGION)));
        }
        // Only run tests against localhost
        awsClient.setEndpoint(SERVER_URL);
        ListTablesResult result = awsClient.listTables();
        assertTrue("Database is not empty", result.getTableNames().isEmpty());
        return awsClient;

    }

    @BeforeClass
    public static void populateTestData() {
        AmazonDynamoDBClient awsClient = getAWSClient(_awsCredentials);

        // Make sure the database is clean
        _deleteTestTables = false;
        ListTablesResult result = awsClient.listTables();
        assertTrue("Database is not empty", result.getTableNames().isEmpty());
        _deleteTestTables = true;

        // Populate DynamoDB with fake data
        populateMetricTable(awsClient);
        populateMetricDataTable(awsClient);
        populateInstanceDataTable(awsClient);
        populateTweetsTable(awsClient);
    }

    @AfterClass
    public static void deleteTestData() {
        if (_deleteTestTables) {
            AmazonDynamoDBClient awsClient = getAWSClient(_awsCredentials);

            // Delete test tables
            awsClient.deleteTable(TaurusClient.METRIC_TABLE);
            awsClient.deleteTable(TaurusClient.METRIC_DATA_TABLE);
            awsClient.deleteTable(TaurusClient.INSTANCE_DATA_HOURLY_TABLE);
            awsClient.deleteTable(TaurusClient.TWEETS_TABLE);
        }
    }

    @Before
    public void setUp() throws Exception {

        //FIXME: HACK: work around bug https://code.google.com/p/dexmaker/issues/detail?id=2
        System.setProperty("dexmaker.dexcache",
                "/data/data/" + BuildConfig.APPLICATION_ID + "/cache");

        _taurusClient = new TaurusClient(new StaticCredentialsProvider(_awsCredentials),
                SERVER_URL);

        // Mock android classes
        Context context = mock(Context.class);
        Resources resources = mock(Resources.class);
        when(resources.getStringArray(com.numenta.core.R.array.aggregation_type_options))
                .thenReturn(new String[]{"Day"});
        when(context.getResources()).thenReturn(resources);
        TaurusApplication application = mock(TaurusApplication.class);
        when(application.getDataFactory()).thenReturn(new TaurusDataFactory());

        TaurusApplication.setStaticInstanceForUnitTestsOnly(application);
    }

    @After
    public void tearDown() throws Exception {

    }

    @Test
    public void testGetTweets() throws Exception {
        final ArrayList<Tweet> results = new ArrayList<Tweet>();
        String metricId = MetricType.TwitterVolume.name() + ".0";
        _taurusClient.getTweets(metricId,
                new Date(TEST_START_TIMESTAMP),
                new Date(TEST_END_TIMESTAMP), new TaurusClient.DataCallback<Tweet>() {
                    @Override
                    public boolean onData(Tweet tweet) {
                        results.add(tweet);
                        return true;
                    }
                });
        int totalRecords = (int) (
                (TEST_END_TIMESTAMP - TEST_START_TIMESTAMP) / DataUtils.METRIC_DATA_INTERVAL) + 1;
        assertEquals("Failed to get all tweets for " + metricId, totalRecords, results.size());

        Tweet first = results.get(0);
        Tweet last = results.get(results.size() - 1);

        assertEquals("Wrong sort order", TEST_START_TIMESTAMP, last.getAggregated());
        assertEquals("Wrong sort order", TEST_END_TIMESTAMP, first.getAggregated());

        assertEquals("Invalid Created Date", TEST_END_TIMESTAMP, first.getCreated());
        assertEquals("Invalid Aggregated Date", TEST_END_TIMESTAMP, first.getAggregated());
        String expectedUser = "user." + totalRecords;
        assertEquals("Invalid User ID", expectedUser, first.getUserId());
        assertEquals("Invalid User Name", expectedUser, first.getUserName());
        assertEquals("Invalid Text", "Lorem ipsum for " + first.getId(), first.getText());
        assertEquals("Invalid Retweet Total", 1, first.getRetweetTotal());
        assertEquals("Invalid Retweet Count", 0, first.getRetweetCount());
        assertEquals("Invalid Aggregate Count", 0, first.getAggregatedCount());

    }

    @Test(expected = YOMPException.class)
    public void testGetMetricData() throws Exception {
        _taurusClient.getMetricData("id.0",
                new Date(TEST_START_TIMESTAMP),
                new Date(TEST_END_TIMESTAMP), new TaurusClient.DataCallback<MetricData>() {
                    @Override
                    public boolean onData(MetricData data) {
                        return true;
                    }
                });

    }

    /**
     * Helper class used to store metric values
     */
    static class MetricValue {

        MetricValue(long timestamp, float anomaly, float value) {
            this.timestamp = timestamp;
            this.anomaly = anomaly;
            this.value = value;
        }

        long timestamp;

        float anomaly;

        float value;
    }

    @Test
    public void testGetMetricValues() throws Exception {
        final ArrayList<MetricValue> results = new ArrayList<MetricValue>();
        String metricId = "id.0";
        _taurusClient.getMetricValues(metricId,
                new Date(TEST_START_TIMESTAMP),
                new Date(TEST_END_TIMESTAMP), true, new TaurusClient.MetricValuesCallback() {
                    @Override
                    public boolean onData(String metricId, long timestamp, float value,
                            float anomaly) {
                        results.add(new MetricValue(timestamp, anomaly, value));
                        return true;
                    }
                });
        int totalRecords = (int) (
                (TEST_END_TIMESTAMP - TEST_START_TIMESTAMP) / DataUtils.METRIC_DATA_INTERVAL) + 1;
        assertEquals("Failed to get all data for " + metricId, totalRecords, results.size());

        MetricValue first = results.get(0);
        MetricValue last = results.get(results.size() - 1);

        assertEquals("Wrong sort order", TEST_START_TIMESTAMP, first.timestamp);
        assertEquals("Wrong sort order", TEST_END_TIMESTAMP, last.timestamp);

        assertEquals("Wrong value", totalRecords, last.value, 0.001);
        assertEquals("Wrong anomaly", 1.0, last.anomaly, 0.001);
    }

    @Test
    public void testGetAllInstanceData() throws Exception {
        final ArrayList<InstanceData> results = new ArrayList<InstanceData>();

        _taurusClient.getAllInstanceData(new Date(TEST_START_TIMESTAMP),
                new Date(TEST_END_TIMESTAMP), true, new TaurusClient.DataCallback<InstanceData>() {
                    @Override
                    public boolean onData(InstanceData data) {
                        results.add(data);
                        return true;
                    }
                });
        InstanceData first = results.get(0);
        InstanceData last = results.get(results.size() - 1);

        assertEquals("Wrong sort order", TEST_START_TIMESTAMP, first.getTimestamp());
        assertEquals("Wrong sort order", TEST_END_TIMESTAMP, last.getTimestamp());
        assertEquals("Wrong id", "id.1", first.getInstanceId());
        assertEquals("Wrong anomaly", 0, first.getAnomalyScore(), 0.001);
        assertEquals("Wrong anomaly", 1, last.getAnomalyScore(), 0.001);
    }

    @Test
    public void testGetMetrics() throws Exception {
        final List<Metric> results = _taurusClient.getMetrics();
        int total = INSTANCES * MetricType.values().length;
        assertEquals("Failed to get all metrics", total, results.size());
        Metric first = results.get(0);
        assertEquals("Invalid id", "id.3", first.getId());
        assertEquals("Invalid Instance", "id.0", first.getInstanceId());
        assertEquals("Invalid Name", "NewsVolume.0", first.getName());

        // FIXME Android JUnit test runner is mocking "org.json" classes.
        //assertEquals("Invalid Symbol", "symbol.0", first.getUserInfo("symbol"));
        //assertEquals("Invalid Metric Type Name", "NEWS_VOLUME", first.getUserInfo("metricTypeName"));
    }
}
