
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

public class Notification implements Serializable {

    private static final long serialVersionUID = -1629911333052969867L;

    public static final String TABLE_NAME = "notification";

    private int id;
    private String notificationId;
    private final String metricId;
    private final long timestamp;
    private boolean read;
    private String description;

    protected Notification(Cursor cursor) {
        // Use "_id" as name so it can be used by the {@link SimpleCursorAdapter}
        this.id = cursor.getInt(cursor.getColumnIndex("_id"));
        this.notificationId = cursor.getString(cursor.getColumnIndex("notification_id"));
        this.metricId = cursor.getString(cursor.getColumnIndex("metric_id"));
        this.timestamp = cursor.getLong(cursor.getColumnIndex("timestamp"));
        this.read = cursor.getInt(cursor.getColumnIndex("read")) == 1;
        this.description = cursor.getString(cursor.getColumnIndex("description"));
    }

    protected Notification(String notificationId, String metricId, long timestamp, boolean read, String description) {
        this.notificationId = notificationId;
        this.metricId = metricId;
        this.timestamp = timestamp;
        this.read = read;
        this.description = description;
    }

    /**
     * Convert to {@link android.content.ContentValues} to be used by the
     * {@link android.database.sqlite.SQLiteDatabase}
     */
    public ContentValues getValues() {
        ContentValues values = new ContentValues();
        // Use "_id" as name so it can be used by the {@link SimpleCursorAdapter}
        values.put("_id", this.id);
        values.put("notification_id", this.notificationId);
        values.put("metric_id", this.metricId);
        values.put("timestamp", this.timestamp);
        values.put("read", this.read ? 1 : 0);
        values.put("description", this.description);
        return values;
    }


    /**
     * Represents the "localId" used by OS notification
     */
    public int getLocalId() {
        return id;
    }

    /**
     * Represents the server notification
     */
    public String getNotificationId() {
        return notificationId;
    }

    public String getMetricId() {
        return metricId;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public String getDescription() {
        return description;
    }

    public boolean isRead() {
        return this.read;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
