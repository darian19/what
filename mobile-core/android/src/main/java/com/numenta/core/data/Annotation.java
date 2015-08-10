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

package com.numenta.core.data;

import android.content.ContentValues;
import android.database.Cursor;

import java.io.Serializable;

/**
 * Helper class representing one "annotation" record
 */
public class Annotation implements Serializable {

    private static final long serialVersionUID = 1716827545720177068L;

    public static final String TABLE_NAME = "annotation";

    private final String id;
    private final long timestamp;
    private final long created;
    private final String device;
    private final String user;
    private final String instanceId;
    private final String message;
    private final String data;

    protected Annotation(Cursor cursor) {
        this.id = cursor.getString(cursor.getColumnIndex("annotation_id"));
        this.timestamp = cursor.getLong(cursor.getColumnIndex("timestamp"));
        this.created = cursor.getLong(cursor.getColumnIndex("created"));
        this.device = cursor.getString(cursor.getColumnIndex("device"));
        this.user = cursor.getString(cursor.getColumnIndex("user"));
        this.instanceId = cursor.getString(cursor.getColumnIndex("instance_id"));
        this.message = cursor.getString(cursor.getColumnIndex("message"));
        this.data = cursor.getString(cursor.getColumnIndex("data"));
    }

    /**
     * Convert {@link Annotation} to {@link ContentValues}
     *
     * @return {@link ContentValues} to be used by the {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = new ContentValues();
        values.put("annotation_id", this.id);
        values.put("timestamp", this.timestamp);
        values.put("created", this.created);
        values.put("device", this.device);
        values.put("user", this.user);
        values.put("instance_id", this.instanceId);
        values.put("message", this.message);
        values.put("data", this.data);
        return values;
    }

    protected Annotation(String annotationId, long timestamp, long created,
                      String device, String user, String instanceId, String message,
                      String data) {
        this.id = annotationId;
        this.timestamp = timestamp;
        this.created = created;
        this.device = device;
        this.user = user;
        this.instanceId = instanceId;
        this.message = message;
        this.data = data;
    }

    /**
     * @return the annotationId
     */
    public String getId() {
        return this.id;
    }

    /**
     * @return the timestamp
     */
    public long getTimestamp() {
        return this.timestamp;
    }

    /**
     * @return the created
     */
    public long getCreated() {
        return this.created;
    }

    /**
     * @return the device
     */
    public String getDevice() {
        return this.device;
    }

    /**
     * @return the message
     */
    public String getMessage() {
        return this.message;
    }

    /**
     * @return the data
     */
    public String getData() {
        return this.data;
    }

    /**
     * @return the user
     */
    public String getUser() {
        return this.user;
    }

    /**
     * @return the instanceId
     */
    public String getInstanceId() {
        return this.instanceId;
    }

}
