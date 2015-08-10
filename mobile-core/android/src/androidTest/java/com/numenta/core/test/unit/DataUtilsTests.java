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

package com.numenta.core.test.unit;

import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.YOMPAndroidTestCase;
import com.numenta.core.utils.mock.MockAnomalyChartData;

import junit.framework.Assert;

import android.test.suitebuilder.annotation.SmallTest;

import java.util.Calendar;
import java.util.Comparator;
import java.util.TimeZone;

public class DataUtilsTests extends YOMPAndroidTestCase {

    @SmallTest
    public void testLogScale() {
        Assert.assertEquals(0.03, DataUtils.logScale(0.5), 0.01);
        assertEquals(0.1, DataUtils.logScale(0.9), 0.01);
        assertEquals(0.13, DataUtils.logScale(0.95), 0.01);
        assertEquals(0.2, DataUtils.logScale(0.99), 0.01);
        assertEquals(0.23, DataUtils.logScale(0.995), 0.01);
        assertEquals(0.29, DataUtils.logScale(0.999), 0.01);
        assertEquals(0.33, DataUtils.logScale(0.9995), 0.01);
        assertEquals(0.39, DataUtils.logScale(0.9999), 0.01);
        assertEquals(0.43, DataUtils.logScale(0.99995), 0.01);
        assertEquals(0.49, DataUtils.logScale(0.99999), 0.01);
        assertEquals(1, DataUtils.logScale(0.999995), 0.01);
        assertEquals(1, DataUtils.logScale(0.999999), 0.01);
        assertEquals(1, DataUtils.logScale(0.9999995), 0.01);
        assertEquals(1, DataUtils.logScale(1), 0.01);
    }

    @SmallTest
    public void testFormatYOMPDate() {
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
        cal.set(2014, Calendar.JANUARY, 25, 9, 0, 0);
        assertEquals("2014-01-25 09:00:00", DataUtils.formatYOMPDate(cal.getTime(), false));
        assertEquals("2014-01-25+09:00:00", DataUtils.formatYOMPDate(cal.getTime(), true));
    }


    @SmallTest
    public void testCalculateSortRank() {

        // RED > YELLOW > GREEN > RED_PROBATION > YELLOW_PROBATION > GREEN_PROBATION > EMPTY

        // Red > 0.99999
        double red = 0.999991;
        // Yellow > 0.9999
        double yellow = 0.99991;
        // Green <= 0.9999
        double green = 0.9999;
        // Empty = 0
        double empty = 0;

        // Red should be greater than yellow
        double rank2 = DataUtils.calculateSortRank(red);
        double rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(yellow);
        }
        assertTrue(rank2 > rank1);

        // Yellow should be greater than green
        rank2 = DataUtils.calculateSortRank(yellow);
        rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(green);
        }
        assertTrue(rank2 > rank1);

        // Green should be greater than red probation
        rank2 = DataUtils.calculateSortRank(green);
        rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(-red);
        }
        assertTrue(rank2 > rank1);

        // Red probation should be greater than yellow probation
        rank2 = DataUtils.calculateSortRank(-red);
        rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(-yellow);
        }
        assertTrue(rank2 > rank1);

        // Yellow probation should be greater than green probation
        rank2 = DataUtils.calculateSortRank(-yellow);
        rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(-green);
        }
        assertTrue(rank2 > rank1);

        // Green probation should be greater than empty
        rank2 = DataUtils.calculateSortRank(-green);
        rank1 = 0;
        for (int i = 0; i < 24; i++) {
            rank1 += DataUtils.calculateSortRank(empty);
        }
        assertTrue(rank2 > rank1);
    }

    @SmallTest
    public void testGetSortByAnomalyComparator() {
        Comparator<AnomalyChartData> comparator = DataUtils.getSortByAnomalyComparator();

        //Test the comparator contract.
        // Let A < B and B < C then A < C, B > A, C > B, C > A

        MockAnomalyChartData A0 =  new MockAnomalyChartData(0, "a");
        MockAnomalyChartData A1 =  new MockAnomalyChartData(1, "a");
        MockAnomalyChartData A2 =  new MockAnomalyChartData(2, "a");
        MockAnomalyChartData B0 =  new MockAnomalyChartData(0, "b");
        MockAnomalyChartData B1 =  new MockAnomalyChartData(1, "b");
        MockAnomalyChartData C0 =  new MockAnomalyChartData(0, "c");
        MockAnomalyChartData N0 =  new MockAnomalyChartData(0, null);

        assertTrue("Test A == A", comparator.compare(A0, A0) == 0);
        // Test comparison by value
        assertTrue("Test A(1) < A(0)", comparator.compare(A1, A0) < 0);
        assertTrue("Test A(0) > A(1)", comparator.compare(A0, A1) > 0);
        assertTrue("Test A(2) < A(1)", comparator.compare(A2, A1) < 0);
        assertTrue("Test A(2) < A(0)", comparator.compare(A2, A0) < 0);
        assertTrue("Test A(0) > A(2)", comparator.compare(A0, A2) > 0);
        assertTrue("Test B(1) < A(0)", comparator.compare(B1, A0) < 0);
        assertTrue("Test A(0) > B(1)", comparator.compare(A0, B1) > 0);

        // Test comparison by name
        assertTrue("Test A < B", comparator.compare(A0, B0) < 0);
        assertTrue("Test B > A", comparator.compare(B0, A0) > 0);
        assertTrue("Test B < C", comparator.compare(B0, C0) < 0);
        assertTrue("Test A < C", comparator.compare(A0, C0) < 0);
        assertTrue("Test C > A", comparator.compare(C0, A0) > 0);

        assertTrue("Test null == null", comparator.compare(N0, N0) == 0);
        assertTrue("Test A < null", comparator.compare(A0, N0) < 0);
        assertTrue("Test A > null", comparator.compare(N0, A0) > 0);

    }

}
