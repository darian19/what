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

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Instance;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.utils.Version;

import android.util.JsonReader;
import android.util.JsonToken;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Internal class used to parse Instance JSON format as follow. <code><pre>
 * [
 *      {
 *          "status": 1,
 *          "name": "AS_36",
 *          "parameters": {
 *              "region": "us-west-2",
 *              "uid": "00946e31ebb34cff9125ba89f8fa7dee",
 *              "filters": {
 *                  "tag:Name": [
 *                      "subdomain.domain.tld"
 *                  ]
 *              },
 *              "name": "AS_36"
 *          },
 *          "namespace": "AWS/EC2",
 *          "server": "Autostacks/00946e31ebb34cff9125ba89f8fa7dee",
 *          "location": "us-west-2",
 *          "message": null
 *      }, ...
 * ]
 * </pre></code>
 *
 * @see com.numenta.core.service.YOMPClient#getMetrics()
 * @see JsonReader
 */
final public class InstanceParser {

    private final JsonReader _reader;

    private final Version _version;

    private final List<Instance> _results;

    // FIXME: HACK for server 1.4 and 1.5 where the instances API is inconsistent with the other APIs
    // The instance API returns AWS server ID in the following format:
    // "region/AWS/Service/Dimension/ID" for example:
    // "us-west-2/AWS/EC2/InstanceId/i-8928311"
    // The other APIs expect server IDs in the following format:
    // "region/AWS/Service/ID" for example:
    // "us-west-2/AWS/EC2/i-8928311"
    // Use this regex to convert from one format to the other.
    public static final Pattern SERVER_ID_HACK_1_4_SEARCH_PATTERN = Pattern
            .compile("([^/]*)/(AWS)/([^/]*)/([^/]*)/([^/]*)");

    public static final String SERVER_ID_HACK_1_4_REPLACE_PATTERN = "$1/$2/$3/$5";

    /*
     * FIXME: HACK for server 1.4 and higher.
     */
    public static String MER2764InstanceIdHACK(Version version, String instanceId) {
        String server = instanceId;
        if (version.compareTo(YOMPClientImpl.YOMP_SERVER_1_4) >= 0) {
            // Remove Dimension ID from server field
            Matcher regex = SERVER_ID_HACK_1_4_SEARCH_PATTERN.matcher(server);
            if (regex.matches()) {
                server = regex.replaceAll(SERVER_ID_HACK_1_4_REPLACE_PATTERN);
            }
        }
        return server;
    }

    public InstanceParser(JsonReader reader, Version version) {
        this._reader = reader;
        _results = new ArrayList<>();
        _version = version;
    }

    /**
     * Peeks at the next token and returns a {@link String} or {@code null}
     */
    String nextStringOrNull() throws IOException {
        if (_reader.peek() == JsonToken.NULL) {
            _reader.nextNull();
            return null;
        }
        return _reader.nextString();
    }

    void parseBody() throws IOException {

        // reset values
        int status = 0;
        String name = null;
        String namespace = null;
        String server = null;
        String location = null;
        String message = null;

        _reader.beginObject();
        while (_reader.hasNext()) {
            String property = _reader.nextName();
            switch (property) {
                case "status":
                    status = _reader.nextInt();
                    break;
                case "name":
                    name = nextStringOrNull();
                    break;
                case "namespace":
                    namespace = nextStringOrNull();
                    break;
                case "server":
                    server = nextStringOrNull();
                    // FIXME: HACK for server 1.4 and higher. See MER-2764
                    server = MER2764InstanceIdHACK(_version, server);
                    break;
                case "location":
                    location = nextStringOrNull();
                    break;
                case "message":
                    message = nextStringOrNull();
                    break;
                default:
                    _reader.skipValue();
                    break;
            }
        }
        _reader.endObject();

        Instance instance = YOMPApplication.getDatabase().getDataFactory()
                .createInstance(server, name, namespace, location, message, status);
        _results.add(instance);
    }

    void parseArray() throws IOException {
        _reader.beginArray();
        while (_reader.hasNext()) {
            parseBody();
        }
        _reader.endArray();
    }

    public List<Instance> parse() throws IOException {
        parseArray();
        return _results;
    }
}
