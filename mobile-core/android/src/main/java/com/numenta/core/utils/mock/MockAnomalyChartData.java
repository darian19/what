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

package com.numenta.core.utils.mock;

import com.numenta.core.data.AggregationType;
import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.Pair;

import java.util.Date;
import java.util.List;

/**
 * See com.numenta.core.test.unit.DataUtilsTests
 */
public class MockAnomalyChartData implements AnomalyChartData {

    private float _rank;
    private String _name;

    public MockAnomalyChartData(float rank, String name) {
        _rank = rank;
        _name = name;
    }

    @Override
    public float getRank() {
        return _rank;
    }

    @Override
    public String getName() {
        return _name;
    }

    @Override
    public boolean hasData() {
        return false;
    }

    @Override
    public List<Pair<Long, Float>> getData() {
        return null;
    }

    @Override
    public AggregationType getAggregation() {
        return null;
    }

    @Override
    public boolean load() {
        return false;
    }

    @Override
    public void clear() {

    }

    @Override
    public void setEndDate(Date endDate) {

    }

    @Override
    public Date getEndDate() {
        return null;
    }

    @Override
    public String getId() {
        return null;
    }

    @Override
    public String getUnit() {
        return null;
    }

    @Override
    public char getType() {
        return 0;
    }

    @Override
    public long[] getAnnotations() {
        return new long[0];
    }

    public void setName(String n) {
        _name = n;
    }


}
