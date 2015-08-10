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

package com.YOMPsolutions.YOMP.mobile.service;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.Instance;
import com.numenta.core.data.Metric;
import com.numenta.core.data.MetricData;
import com.numenta.core.data.Notification;
import com.numenta.core.service.AuthenticationException;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.service.YOMPUnauthorizedException;
import com.numenta.core.service.ObjectNotFoundException;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.NetUtils;
import com.numenta.core.utils.Version;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.msgpack.MessagePack;
import org.msgpack.unpacker.Unpacker;

import android.util.Base64;
import android.util.JsonReader;
import android.util.JsonWriter;
import android.webkit.URLUtil;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLConnection;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManagerFactory;


/**
 * <code>YOMPClient</code> class wraps a connection to the YOMP REST API
 */
public class YOMPClientImpl implements YOMPClient {
    @Deprecated
    public static final Version YOMP_SERVER_1_0 = new Version("1.0");
    @Deprecated
    public static final Version YOMP_SERVER_1_1 = new Version("1.1");
    @Deprecated
    public static final Version YOMP_SERVER_1_2 = new Version("1.2");

    public static final Version YOMP_SERVER_1_3 = new Version("1.3");
    public static final Version YOMP_SERVER_1_4 = new Version("1.4");
    public static final Version YOMP_SERVER_1_5 = new Version("1.5");
    public static final Version YOMP_SERVER_1_6 = new Version("1.6");
    public static final Version YOMP_SERVER_OLDEST = YOMP_SERVER_1_3;
    public static final Version YOMP_SERVER_LATEST = YOMP_SERVER_1_6;

    private static final String TAG = YOMPClientImpl.class.getSimpleName();
    // Replace "storepass" with stronger password and update "keys/genkeystore.sh" with the new value
    private static final char KEYSTORE_PASS[] = {
            's', 't', 'o', 'r', 'e', 'p', 'a', 's', 's'
    };
    private static final int CONNECTION_TIMEOUT = 60 * 1000;

    private final String _serverUrl;
    private final String _password;
    private static final String USER_AGENT = System.getProperty("http.agent")
            + " " + YOMPApplication.getApplicationName() + "/" + YOMPApplication.getVersion();
    private static final String SERVER_NAME = YOMPApplication.getApplicationName();
    private Version _serverVersion = YOMP_SERVER_OLDEST;
    /**
     * Custom {@link SSLSocketFactory} adding all the certificates embedded with
     * the application in the {@link KeyStore} located at
     * "res/raw/certificates.bks"
     */
    private static final SSLSocketFactory SSL_FACTORY = createSSLFactory();

    // Do not verify host names. We Allow secure requests from all hosts. Rely
    // on server certificate alone.
    private static final HostnameVerifier ACCEPT_ALL_HOSTS = new HostnameVerifier() {
        @Override
        public boolean verify(String hostname, SSLSession session) {
            return true;
        }
    };

    /**
     * Construct YOMP API client to the the given server.
     *
     * @param serverUrl Server URL to connect
     * @param password Password/API Key to use. May be {@code null} for open
     *            server
     * @throws MalformedURLException
     */
    public YOMPClientImpl(String serverUrl, String password)
            throws MalformedURLException {
        if (!URLUtil.isHttpsUrl((serverUrl))) {
            throw new MalformedURLException("Invalid Server URL:" + serverUrl);
        }
        this._serverUrl = serverUrl;
        if (password != null) {
            String auth = password + ":";
            this._password = "Basic " + new String(Base64.encode(auth.getBytes(), Base64.NO_WRAP));
        } else {
            this._password = null;
        }
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.service.YOMPClient#isOnline()
     */
    @Override
    public boolean isOnline() {
        if (NetUtils.isConnected()) {
            // TODO: User real heart beat API, for now just check if the server
            // is responding
            try {
                // If the server is not responding the HEAD request will fail
                Map<String, List<String>> headers = head(this._serverUrl);
                return headers != null;
            } catch (Exception e) {
                Log.e(TAG, "Failed to access server " + this._serverUrl, e);
            }
        }
        return false;

    }

    protected void processServerHeaders(Map<String, List<String>> headers) {
        if (headers != null) {
            if (headers.containsKey("Server")) {
                String version = headers.get("Server").get(0);
                if (version.startsWith(getServerName())) {
                    _serverVersion = new Version(version.substring(5));
                } else {
                    _serverVersion = YOMP_SERVER_OLDEST;
                }
                YOMPApplication.getInstance().setServerVersion(_serverVersion);
                Log.i(TAG, "Server Version:" + _serverVersion);
            }
        }
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.service.YOMPClient#login()
     */
    @Override
    public void login() throws IOException, YOMPException {
        if (NetUtils.isConnected()) {
            // Try to access secure end point
            Map<String, List<String>> headers = head(this._serverUrl + "/_models");
            processServerHeaders(headers);
        }
    }

    @Override
    public void getMetricData(String modelId, Date from, Date to,
            DataCallback<MetricData> callback) throws YOMPException, IOException {
        getMetricDataAsync(modelId, from, to, -1, 0, callback);

    }

    /**
     * Get model data
     *
     * @param modelId Model ID
     * @param from return records from this date
     * @param to return records up to this date
     * @param limit max number of records to return. -1 for all records.
     * @param score anomaly score to filter
     * @throws YOMPException
     * @throws IOException
     */
    private void getMetricDataAsync(String modelId, Date from, Date to,
            int limit, float score, DataCallback<MetricData> callback) throws YOMPException,
            IOException {

        StringBuilder url = new StringBuilder();
        url.append(this._serverUrl).append("/_models");
        // Check if we are getting data for a specific model or all models
        if (modelId != null) {
            url.append("/").append(modelId);
        }
        url.append("/data?");

        // Add filters
        StringBuilder query = new StringBuilder();
        if (from != null) {
            String val = DataUtils.formatYOMPDate(from, true);
            query.append("from=").append(val);
        }
        if (to != null) {
            if (query.length() > 0) {
                query.append("&");
            }
            String val = DataUtils.formatYOMPDate(to, true);
            query.append("to=").append(val);
        }
        if (limit > 0) {
            if (query.length() > 0) {
                query.append("&");
            }
            query.append("limit=").append(limit);
        }
        if (score > 0) {
            if (query.length() > 0) {
                query.append("&");
            }
            query.append("anomaly=").append(score);
        }
        url.append(query);
        Log.d(TAG, "Getting model data from " + url);

        HttpURLConnection connection = null;
        try {
            // Open connection to the server and
            // negotiate protocol (JSON or Binary)
            connection = openConnection(url.toString(), "GET");
            connection.setRequestProperty("Accept", "application/octet-stream");
            processServerHeaders(connection.getHeaderFields());
            if ("application/octet-stream".equals(connection.getContentType())) {
                // The server supports binary output
                processMetricDataBin(connection.getInputStream(), callback);
            } else {
                // TODO: Remove in future releases
                // The server does not support binary output.
                // Fall back to JSON
                processMetricDataJSON(modelId, connection.getInputStream(), callback);
            }
        } catch (FileNotFoundException ex) {
            // Check for Authentication and other YOMP errors
            handleHttpError(connection, ex);
        }
        Log.d(TAG, "Done getting model data from " + url);
    }

    /**
     * Process the metric data stream using {@link MessagePack} parser
     *
     * @param stream
     * @param callback
     * @throws IOException
     * @throws YOMPException
     */
    private void processMetricDataBin(InputStream stream, DataCallback<MetricData> callback)
            throws IOException, YOMPException {
        Unpacker unpacker = null;
        try {
            if (stream != null) {
                MessagePack msgpack = new MessagePack();
                unpacker = msgpack.createUnpacker(stream);

                MetricDataParser parser = new MetricDataParser(unpacker);
                parser.parseAsync(callback);
            }
        } finally {
            if (unpacker != null) {
                unpacker.close();
            }
        }
    }

    /**
     * Process the metric data stream using JSON parser
     *
     * @param stream
     * @param callback
     * @throws IOException
     */
    private void processMetricDataJSON(String modelId, InputStream stream,
            DataCallback<MetricData> callback) throws IOException, YOMPException {
        JsonReader reader = null;
        try {
            if (stream != null) {
                reader = new JsonReader(new InputStreamReader(stream, "UTF-8"));
                MetricDataParser parser = new MetricDataParser(modelId, reader);
                parser.parseAsync(callback);
            }
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
    }

    /*
     * (non-Javadoc)
     * @see com.numenta.core.service.YOMPClient#getMetrics()
     */
    @Override
    public List<Metric> getMetrics() throws YOMPException, IOException {
        String url = this._serverUrl + "/_models";
        JsonReader reader = null;
        try {
            Log.d(TAG, "Getting metrics from " + url);
            InputStream in = getStream(url);
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                MetricParser parser = new MetricParser(reader);
                return parser.parse();
            }
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return null;
    }

    @Override
    public List<Notification> getNotifications() throws YOMPException, IOException {
        StringBuilder url = new StringBuilder();
        // Get notification history for device
        url.append(this._serverUrl).append("/_notifications/")
                .append(YOMPApplication.getDeviceId()).append("/history");
        Log.d(TAG, "Getting notifications: " + url);

        JsonReader reader = null;
        try {
            InputStream in = getStream(url.toString());
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                NotificationParser parser = new NotificationParser(reader);
                List<Notification> result =  parser.parse();
                if (result != null && !result.isEmpty()) {
                    // Make sure the server return notifications.
                    // - Version 1.5 and below will return an empty array if
                    // there are no notifications for this device.
                    // - Version 1.6 and above will
                    // throw "FileNotFoundException" exception instead
                    return  result;
                }
            }
        } catch (FileNotFoundException e) {
            // No notifications found for this device
            return null;
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return null;
    }

    @Override
    public List<Annotation> getAnnotations(Date from, Date to) throws YOMPException, IOException {

        //TODO:FEATURE_FLAG: Annotations were introduced in version 1.6
        if (_serverVersion.compareTo(YOMP_SERVER_1_6) < 0) {
            return null;
        }

        StringBuilder url = new StringBuilder();
        // Get notification history for device
        url.append(this._serverUrl).append("/_annotations");
        boolean append = false;
        if (from != null) {
            url.append("?from=").append(DataUtils.formatYOMPDate(from, true));
            append = true;
        }
        if (to != null) {
            if (append) {
                url.append('&');
            } else {
                url.append('?');
            }
            url.append("to=").append(DataUtils.formatYOMPDate(to, true));
        }
        Log.d(TAG, "Getting annotations: " + url);

        JsonReader reader = null;
        try {
            InputStream in = getStream(url.toString());
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                AnnotationParser parser = new AnnotationParser(reader);
                return parser.parse();
            }
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return null;
    }

    @Override
    public void deleteAnnotation(Annotation annotation) throws YOMPUnauthorizedException, YOMPException, IOException {
        //TODO:FEATURE_FLAG: Annotations were introduced in version 1.6
        if (_serverVersion.compareTo(YOMP_SERVER_1_6) < 0) {
            return;
        }
        // Verify device ID before deleting
        if (!annotation.getDevice().equals(YOMPApplication.getDeviceId())) {
            throw  new YOMPUnauthorizedException("Cannot delete annotations created on a different device");
        }
        StringBuilder url = new StringBuilder();
        url.append(this._serverUrl).append("/_annotations/").append(annotation.getId());
        Log.d(TAG, "Delete annotation: " + url);
        delete(url.toString());
    }

    @Override
    public Annotation addAnnotation(Date timestamp, String server, String message, String user) throws YOMPException, IOException {
        //TODO:FEATURE_FLAG: Annotations were introduced in version 1.6
        if (_serverVersion.compareTo(YOMP_SERVER_1_6) < 0) {
            return null;
        }
        JsonReader reader = null;
        Annotation annotation = null;
        try {
            // Prepare 'Add Annotation' request. See YOMP API for reference.
            JSONObject json = new JSONObject();
            json.put("device", YOMPApplication.getDeviceId());
            json.put("timestamp", DataUtils.formatYOMPDate(timestamp, false));
            json.put("user", user);
            json.put("server", server);
            json.put("message", message);
            json.put("data", null);
            InputStream in = postStream(this._serverUrl + "/_annotations", json.toString());
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                AnnotationParser parser = new AnnotationParser(reader);
                List<Annotation> result = parser.parse();
                if (result != null && result.size() == 1) {
                    annotation = result.get(0);
                }
            }
        } catch (JSONException e) {
            Log.e(TAG, "Failed to add annotation", e);
            throw new YOMPException(e);
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return annotation;
    }

    /**
     * Acknowledge notifications on the server. The server may decide to keep or delete acknowledged
     * notifications, however acknowledged notifications will not be returned by {@link #getNotifications()}
     *
     * @param notifications Array of notification IDs to be acknowledged
     * @throws IOException
     */
    @Override
    public void acknowledgeNotifications(String[] notifications) throws YOMPException, IOException {

        // Get notification history for device
        Log.d(TAG, "Acknowledging notifications: " + Arrays.toString(notifications));
        JSONArray json = new JSONArray(Arrays.asList(notifications));
        post(this._serverUrl + "/_notifications/" + YOMPApplication.getDeviceId() + "/acknowledge", json.toString());
    }

    /**
     * Opens a HTTP connection to the the given URL using the client credentials
     * and YOMP SSL keys
     *
     * @param url The URL to connect
     * @param method The HTTP Method to use: "OPTIONS","GET", "HEAD", "POST",
     *            "PUT", "DELETE", "TRACE"
     * @return The new {@link HttpURLConnection}
     * @throws IOException
     */
    protected HttpURLConnection openConnection(String url, String method) throws IOException {
        URL urlObject = new URL(url);
        HttpURLConnection connection = (HttpURLConnection) urlObject.openConnection();
        if (connection instanceof HttpsURLConnection) {
            HttpsURLConnection secureConnection = (HttpsURLConnection) connection;
            secureConnection.setSSLSocketFactory(SSL_FACTORY);
            secureConnection.setHostnameVerifier(ACCEPT_ALL_HOSTS);
        }
        connection.setConnectTimeout(CONNECTION_TIMEOUT);
        connection.setReadTimeout(CONNECTION_TIMEOUT);
        connection.setRequestMethod(method);
        if (_password != null) {
            connection.setRequestProperty("Authorization", _password);
        }
        connection.setRequestProperty("User-Agent", USER_AGENT);
        connection.setRequestProperty("X-YOMP-DeviceId", YOMPApplication.getDeviceId());
        return connection;
    }

    /**
     * Send "HEAD" request and retrieve all HTTP headers
     *
     * @param url The url to send the "HEAD" request
     * @return Returns an unmodifiable map of the response-header fields and
     *         values. The response-header field names are the key values of the
     *         map. The map values are lists of header field values associated
     *         with a particular key name. HTTP status line is mapped to the
     *         {@code null} key.
     * @throws YOMPException
     * @throws IOException
     * @see URLConnection#getHeaderFields()
     */
    private Map<String, List<String>> head(String url) throws IOException, YOMPException {
        HttpURLConnection connection = openConnection(url, "HEAD");
        // HACK: Android Calls GZIPInputStream when getting the HTTP
        // response code causing the HTTP HEAD call crash with
        // java.io.EOFException.
        // See https://code.google.com/p/android/issues/detail?id=24672
        // For now we disable "gzip" encoding for HEAD calls.
        connection.setRequestProperty("Accept-Encoding", "");
        // Check status code.
        handleHttpError(connection, null);
        return connection.getHeaderFields();
    }

    private InputStream getStream(String url) throws IOException, YOMPException {
        HttpURLConnection connection = openConnection(url, "GET");
        try {
            processServerHeaders(connection.getHeaderFields());
            return connection.getInputStream();
        } catch (FileNotFoundException ex) {
            // Check for Authentication and other YOMP errors and throw new
            // Exception.
            handleHttpError(connection, ex);
        }
        return null;
    }

    /**
     * Handles YOMP Server response codes.
     * <p>
     * Should be called when the HTTP operation results in {@link IOException}
     *
     * @param connection
     * @throws YOMPException
     * @throws IOException
     * @throws com.numenta.core.service.AuthenticationException
     */
    private void handleHttpError(HttpURLConnection connection,
            IOException ioException) throws YOMPException, IOException {
        if (connection != null) {
            int httpStatus;
            httpStatus = connection.getResponseCode();
            switch (httpStatus) {
                case HttpURLConnection.HTTP_INTERNAL_ERROR:
                    String error = readStream(connection.getErrorStream());
                    if (error != null && error.startsWith("ObjectNotFoundError")) {
                        throw new ObjectNotFoundException();
                    }
                    throw new YOMPException(connection.getResponseMessage() + " - " + error,
                            ioException);
                case HttpURLConnection.HTTP_BAD_REQUEST:
                case HttpURLConnection.HTTP_FORBIDDEN:
                case HttpURLConnection.HTTP_UNAUTHORIZED:
                    throw new AuthenticationException(connection.getResponseMessage(), ioException);
                default:
                    // Throw original exception if it is not handled.
                    if (ioException != null) {
                        throw ioException;
                    }
            }
        }
    }

    private String readStream(InputStream in) throws IOException {

        if (in == null)
            return null;

        Reader reader = null;
        try {
            // json is UTF-8 by default
            reader = new InputStreamReader(in, "UTF-8");
            StringBuilder sb = new StringBuilder();

            char[] buffer = new char[4096];
            int count;
            while ((count = reader.read(buffer)) > 0) {
                sb.append(buffer, 0, count);
            }
            return sb.toString();
        } finally {
            try {
                if (reader != null) {
                    reader.close();
                }
            } catch (Exception ignore) {
                // Ignore
            }
        }

    }

    /**
     * Posts the given JSON Object to the server and returns the
     * response {@link java.io.InputStream}
     * @param url The  URL to post the JSON object
     * @param jsonData JSON Data
     * @return  The response {@link java.io.InputStream} or
     *          {@code null} if the response code was not valid
     * @throws IOException
     * @throws YOMPException
     */
    private InputStream postStream(String url, String jsonData) throws IOException, YOMPException {
        InputStream response = null;
        OutputStream os = null;
        HttpURLConnection conn = null;
        try {
            conn = openConnection(url, "POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            os = conn.getOutputStream();
            os.write(jsonData.getBytes());
            os.flush();

            processServerHeaders(conn.getHeaderFields());

            switch (conn.getResponseCode()) {
                case HttpURLConnection.HTTP_OK:
                case HttpURLConnection.HTTP_CREATED:
                case HttpURLConnection.HTTP_NO_CONTENT:
                    response = conn.getInputStream();
                    break;
                default:
                    Log.e(TAG, "Failed : HTTP error code : " + conn.getResponseCode());
            }
        } catch (FileNotFoundException ex) {
            // Check for Authentication and other YOMP errors and throw new
            // Exception.
            handleHttpError(conn, ex);
        } finally {
            try {
                if (os != null) {
                    os.close();
                }
            } catch (IOException e) {
                // Ignore
            }
        }
        return response;
    }

    /**
     * Posts data to the given URL
     *
     * @param url
     * @param data
     * @return Response text, or null if the response code was not 200
     * @throws YOMPException
     * @throws IOException
     */
    public String post(String url, String data) throws YOMPException, IOException {
        return readStream(postStream(url, data));
    }

    /**
     * Creates a new {@link SSLSocketFactory} adding all the certificates
     * embedded with the application in the {@link KeyStore} located at
     * "res/raw/certificates.bks"
     *
     * @return {@link SSLSocketFactory}
     */
    private static SSLSocketFactory createSSLFactory() {
        // Initialize SSL Factory with embedded certificates
        try {
            final KeyStore trustStore = KeyStore.getInstance("BKS");
            final InputStream inputStream = YOMPApplication.getContext()
                    .getResources().openRawResource(R.raw.certificates);
            trustStore.load(inputStream, KEYSTORE_PASS);
            inputStream.close();
            TrustManagerFactory tmf = TrustManagerFactory
                    .getInstance(TrustManagerFactory.getDefaultAlgorithm());
            tmf.init(trustStore);
            SSLContext ctx = SSLContext.getInstance("TLS");
            ctx.init(null, tmf.getTrustManagers(), null);
            return ctx.getSocketFactory();
        } catch (Exception e) {
            Log.wtf(TAG, e);
        }
        return null;
    }

    @Override
    public String getServerUrl() {
        return this._serverUrl;
    }

    @Override
    public Version getServerVersion() {
        return this._serverVersion;
    }

    public void updateNotifications(String email, int frequency)
            throws YOMPException, IOException {

        StringBuilder url = new StringBuilder();
        // Get notification history for device
        url.append(this._serverUrl).append("/_notifications/")
                .append(YOMPApplication.getDeviceId()).append("/settings");
        Log.d(TAG, "Updating notification settings ");

        HttpURLConnection conn = null;
        JsonWriter writer = null;
        try {
            conn = openConnection(url.toString(), "PUT");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            writer = new JsonWriter(new OutputStreamWriter(conn.getOutputStream(),
                    "UTF-8"));
            writer.beginObject();
            writer.name("email_addr").value(email);
            writer.name("windowsize").value(frequency);
            writer.endObject();
            writer.flush();

            handleHttpError(conn, null);

            // Read response
            readStream((conn.getInputStream()));

        } catch (FileNotFoundException ex) {
            // Check for Authentication and other YOMP errors and throw new
            // Exception.
            handleHttpError(conn, ex);
        } finally {
            if (writer != null) {
                try {
                    writer.close();
                } catch (IOException ignore) {
                    // Ignore
                }
            }
        }
    }

    /**
     * Get notification settings for device.
     *
     * @return {@link NotificationSettings}
     * @throws IOException
     * @throws YOMPException
     */
    public NotificationSettings getNotificationSettings() throws YOMPException, IOException {
        StringBuilder url = new StringBuilder();
        // Get notification history for device
        url.append(this._serverUrl).append("/_notifications/")
                .append(YOMPApplication.getDeviceId()).append("/settings");
        Log.d(TAG, "Updating notification settings ");
        HttpURLConnection conn = null;
        try {
            conn = openConnection(url.toString(), "GET");
            conn.setRequestProperty("Content-Type", "application/json");
            processServerHeaders(conn.getHeaderFields());
            JSONObject json = new JSONObject(readStream(conn.getInputStream()));
            handleHttpError(conn, null);
            return new NotificationSettings(json);
        } catch (FileNotFoundException ex) {
            // Check for Authentication and other YOMP errors and throw new
            // Exception.
            handleHttpError(conn, null);
            // No settings found for this device
            return null;
        } catch (JSONException e) {
            Log.e(TAG, "Failed to parse Notification Settings", e);
        }
        return null;
    }

    /**
     * Returns a list of instances from the server
     */
    public List<Instance> getInstances() throws YOMPException, IOException {
        String url = this._serverUrl + "/_instances";
        JsonReader reader = null;
        try {
            Log.d(TAG, "Getting instances from " + url);
            InputStream in = getStream(url);
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                InstanceParser parser = new InstanceParser(reader, getServerVersion());
                return parser.parse();
            }
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return null;
    }

    /**
     * Returns the time remaining to process data for all models
     *
     * @return The remaining time in seconds
     * @throws YOMPException
     * @throws IOException
     */
    public int getProcessingTimeRemaining() throws YOMPException, IOException {
        int seconds = 0;
        String url = this._serverUrl + "/_models/data/stats";
        JsonReader reader = null;
        try {
            Log.d(TAG, "Getting stats from " + url);
            InputStream in = getStream(url);
            if (in != null) {
                reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
                reader.beginObject();
                while (reader.hasNext()) {
                    String property = reader.nextName();
                    if (property.equals("processing_time_remaining")) {
                        seconds = reader.nextInt();
                    } else {
                        reader.skipValue();
                    }
                }
                reader.endObject();
            }
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // ignore
                }
            }
        }
        return seconds;
    }

    /**
     * Client's user agent to send to the server on every HTTP request
     * using the "User-Agent" HTTP header
     *
     * @return The user agent sent on every HTTP request to the server
     */
    public String getUserAgent() {
        return USER_AGENT;
    }

    @Override
    public String getServerName() {
        return SERVER_NAME;
    }


    /**
     * Get data from the given URL
     *
     * @param url
     * @return Response text, or null if the response code was not 200
     * @throws YOMPException
     * @throws IOException
     */
    public String get(String url) throws YOMPException, IOException {
        return readStream(getStream(url));
    }

    /**
     * Delete the given URL
     *
     * @param url
     * @throws YOMPException
     * @throws IOException
     */
    public void delete(String url) throws YOMPException, IOException {
        HttpURLConnection connection = openConnection(url, "DELETE");
        handleHttpError(connection, null);
    }
}
