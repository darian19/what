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

package com.numenta.core.ui.chart;

import com.numenta.core.data.AggregationType;
import com.numenta.core.utils.Pair;

import java.util.Date;
import java.util.List;

/**
 * Instance or metric data used by the AnomalyChart
 */
public interface AnomalyChartData {

    /**
     * @return {@code true} if we have data, {@code false} otherwise
     */
    boolean hasData();

    /**
     * @return Display Name
     */
    CharSequence getName();

    /**
     * Aggregated metric data, should be called after {@link #load()}
     */
    List<Pair<Long, Float>> getData();

    /**
     * @return The {@link AggregationType} used on this instance data
     */
    AggregationType getAggregation();

    /**
     * Load metric data from the database
     *
     * @return {@code true} if got new data {@code false} otherwise
     */
    boolean load();

    /**
     * Clears memory cache, call {@link #load()} to reload data from the
     * database
     */
    void clear();

    /**
     * Load data up to this date, {@code null} for last known date
     *
     * @param endDate the endDate to set
     */
    void setEndDate(Date endDate);

    /**
     * Load data up to this date, {@code null} for last known date
     *
     * @return the endDate
     */
    Date getEndDate();

    /**
     * Instance or Metric ID represented by this data
     */
    String getId();

    /**
     * Get Metric Unit if available
     */
    String getUnit();

    /**
     * This chart data type, "I" for instance or "M" for metric
     */
    char getType();

    /**
     * Get all timestamps with annotations
     */
    long[] getAnnotations();

    /**
     * Return the overall rank for the data represented by this class.
     * Usually the rank is calculated as the sum of all anomaly score values
     */
    float getRank();
}
