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

package com.numenta.taurus.data;

import com.numenta.core.data.AggregationType;
import com.numenta.core.data.CoreDataFactoryImpl;
import com.numenta.taurus.metric.MetricType;

import android.database.Cursor;

import java.util.Date;
import java.util.EnumSet;

/**
 * Factory used to create Taurus Data model Objects
 */
public class TaurusDataFactory extends CoreDataFactoryImpl {

    public Tweet createTweet(String tweetId, Date aggregated, Date created, String userId,
            String userName, String text, int retweetCount) {
        return new Tweet(tweetId, aggregated.getTime(), created.getTime(), userId, userName, text,
                retweetCount);

    }

    @Override
    public InstanceData createInstanceData(Cursor cursor) {
        return new InstanceData(cursor);
    }

    public InstanceData createInstanceData(String instanceId, AggregationType aggregation,
            long timestamp, float anomalyScore, EnumSet<MetricType> metricMask) {
        return new InstanceData(instanceId, aggregation.minutes(), timestamp, anomalyScore,
                metricMask);
    }

    public InstanceData createInstanceData(String instanceId, AggregationType aggregation,
            long timestamp, float anomalyScore, int metricMask) {
        return new InstanceData(instanceId, aggregation.minutes(), timestamp, anomalyScore,
                metricMask);
    }

    public Notification createNotification(String instanceId, long timestamp, String description) {
        return new Notification(instanceId, timestamp, description);
    }
}
