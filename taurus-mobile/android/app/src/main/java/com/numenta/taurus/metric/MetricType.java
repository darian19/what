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

package com.numenta.taurus.metric;

import com.numenta.core.data.Metric;
import com.numenta.core.utils.Log;

import java.util.EnumSet;

/**
 * This enum converts "metricTypeName" user info field into valid comparable values with also
 * controls the metric list sort order.
 */
public enum MetricType {
    StockPrice, StockVolume, TwitterVolume, NewsVolume;


    /**
     * Stock metric types
     */
    public static final EnumSet<MetricType> STOCK_TYPES = EnumSet.of(
            MetricType.StockVolume, MetricType.StockPrice);

    /**
     * Extract the metric type from the given metric
     *
     * @param metric The metric object
     * @return One of the valid {@link MetricType} values or {@code null} for invalid type
     */
    public static MetricType valueOf(Metric metric) {
        if (metric == null) {
            return null;
        }
        String metricType = metric.getUserInfo("metricType");
        if (metricType == null || metricType.isEmpty()) {
            Log.w("MetricType", metric.getName() + " does not contain field 'metricType'");
            return null;
        }
        try {
            return MetricType.valueOf(metricType);
        } catch (IllegalArgumentException e) {
            Log.e(MetricListAdapter.class.getSimpleName(), "Unknown metric type: " + metricType, e);
            return null;
        }
    }

    /**
     * Return the Enum as a bitwise flag
     */
    public int flag() {
        return 1 << ordinal();
    }

    /**
     * Convert bitwise flags combination of this enum back into EnumSet
     */
    public static EnumSet<MetricType> fromMask(int bitmask) {
        EnumSet<MetricType> set = EnumSet.noneOf(MetricType.class);
        int flag = MetricType.StockPrice.flag();
        if ((bitmask & flag) != 0) {
            set.add(MetricType.StockPrice);
        }
        flag = MetricType.StockVolume.flag();
        if ((bitmask & flag) != 0) {
            set.add(MetricType.StockVolume);
        }
        flag = MetricType.TwitterVolume.flag();
        if ((bitmask & flag) != 0) {
            set.add(MetricType.TwitterVolume);
        }
        flag = MetricType.NewsVolume.flag();
        if ((bitmask & flag) != 0) {
            set.add(MetricType.NewsVolume);
        }
        return set;
    }
}
