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

import java.io.Serializable;

/**
 * Represents an anomaly value composed of the aggregated anomaly value and a mask indicating the
 * metric types with anomalous values if any.
 *
 * @see com.numenta.taurus.metric.MetricType#flag()
 * @see com.numenta.taurus.metric.MetricType#fromMask(int)
 */
public class AnomalyValue implements Serializable {

    public float anomaly;

    public int metricMask;

    public AnomalyValue(float anomaly, int metricMask) {
        this.anomaly = anomaly;
        this.metricMask = metricMask;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }

        AnomalyValue that = (AnomalyValue) o;

        if (Float.compare(that.anomaly, anomaly) != 0) {
            return false;
        }
        return metricMask == that.metricMask;

    }

    @Override
    public int hashCode() {
        int result = (anomaly != +0.0f ? Float.floatToIntBits(anomaly) : 0);
        result = 31 * result + metricMask;
        return result;
    }
}
