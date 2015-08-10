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

/**
 * Aggregation Type used to get aggregated metric data.
 */
public enum AggregationType {
    /** Hourly aggregation into 5 minutes buckets */
    Hour(5),
    /** Half day aggregation into 30 minutes buckets */
    HalfDay(30),
    /** Daily aggregations into 60 minutes buckets */
    Day(60),
    /** Weekly aggregations into 8 hours buckets */
    Week(480);

    private final int _period;

    /**
     * Returns the closest {@link AggregationType} matching the given interval
     *
     * @param interval The interval value in milliseconds
     * @return The {@link AggregationType} that best matches the interval.
     */
    public static AggregationType fromInterval(long interval) {
        if (interval <= AggregationType.Hour.milliseconds()) {
            return AggregationType.Hour;
        } else if (interval <= AggregationType.HalfDay.milliseconds()) {
            return AggregationType.HalfDay;
        } else if (interval <= AggregationType.Day.milliseconds()) {
            return AggregationType.Day;
        } else {
            return AggregationType.Week;
        }
    }

    AggregationType(int period) {
        this._period = period;
    }

    /**
     * Aggregation period in milliseconds
     */
    public long milliseconds() {
        return 60 * 1000 * _period;
    }

    /**
     * Aggregation period in seconds
     */
    public int seconds() {
        return _period * 60;
    }

    /**
     * Aggregation period in minute
     */
    public int minutes() {
        return _period;
    }
}
