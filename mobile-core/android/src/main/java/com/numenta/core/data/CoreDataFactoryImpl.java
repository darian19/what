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

import org.json.JSONObject;

import android.database.Cursor;

/**
 * Default Data factory used to create standard CoreDatabase Objects
 */
public class CoreDataFactoryImpl implements CoreDataFactory {

    @Override
    public Annotation createAnnotation(Cursor cursor) {
        return new Annotation(cursor);
    }

    @Override
    public Annotation createAnnotation(String annotationId, long timestamp, long created,
            String device, String user, String instanceId, String message, String data) {
        return new Annotation(annotationId, timestamp, created, device, user, instanceId, message,
                data);
    }

    @Override
    public Metric createMetric(Cursor cursor) {
        return new Metric(cursor);
    }

    @Override
    public Metric createMetric(String metricId, String name, String instanceId, String serverName,
            int lastRowId, JSONObject parameters) {
        return new Metric(metricId, name, instanceId, serverName, lastRowId, parameters);
    }

    @Override
    public MetricData createMetricData(Cursor cursor) {
        return new MetricData(cursor);
    }

    @Override
    public MetricData createMetricData(String metricId, long timestamp, float metricValue,
            float anomalyScore, long rowid) {
        return new MetricData(metricId, timestamp, metricValue, anomalyScore, rowid);
    }

    @Override
    public Instance createInstance(String id, String name, String namespace, String location,
            String message, int status) {
        return new Instance(id, name, namespace, location, message, status);
    }

    @Override
    public InstanceData createInstanceData(Cursor cursor) {
        return new InstanceData(cursor);
    }

    @Override
    public InstanceData createInstanceData(String instanceId, AggregationType aggregation,
            long timestamp, float anomalyScore) {
        return new InstanceData(instanceId, aggregation.minutes(), timestamp, anomalyScore);
    }

    @Override
    public Notification createNotification(Cursor cursor) {
        return new Notification(cursor);
    }

    @Override
    public Notification createNotification(String notificationId, String metricId, long timestamp,
            boolean read, String description) {
        return new Notification(notificationId, metricId, timestamp, read, description);
    }
}
