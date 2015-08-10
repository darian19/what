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

package com.numenta.taurus.test.unit;

import com.numenta.core.utils.Pair;
import com.numenta.taurus.data.MarketCalendar;

import junit.framework.TestCase;

import java.util.Calendar;
import java.util.List;
import java.util.TimeZone;

public class MarketCalendarTest extends TestCase {

    public void testIsOpenUS() {
        // Test "MarketCalendar#isOpen"
        //
        //  1) Closed on weekends
        //  2) Closed after hours (after 4pm)
        //  3) Closed before opening hours (before 9:00am)
        //  4) Open on regular working day during opening hours
        //  5) Open on the morning of a half-day holiday (Christmas Eve)
        //  6) Closed on the afternoon of half-day holiday (Christmas Eve after 1pm)
        //  7) Closed on holidays (Christmas Day)

        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));

        // Closed on weekends
        calendar.set(2015, Calendar.JANUARY, 3, 10, 0, 0);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        calendar.set(2015, Calendar.JANUARY, 4, 10, 0, 0);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Closed after hours (after 4pm)
        calendar.set(2015, Calendar.JANUARY, 2, 16, 0, 1);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Closed before opening hours (before 9:00am)
        calendar.set(2015, Calendar.JANUARY, 2, 8, 0, 0);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Open on regular working day during opening hours
        calendar.set(2015, Calendar.JANUARY, 2, 9, 0, 1);
        assertTrue(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Open on the morning of a half-day holiday (Christmas Eve)
        calendar.set(2015, Calendar.DECEMBER, 24, 12, 0, 0);
        assertTrue(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Closed on the afternoon of half-day holiday (Christmas Eve after 1pm)
        calendar.set(2015, Calendar.DECEMBER, 24, 13, 0, 1);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();

        // Closed on holidays (Christmas Day)
        calendar.set(2015, Calendar.DECEMBER, 25, 10, 0, 0);
        assertFalse(MarketCalendar.US.isOpen(calendar.getTimeInMillis()));
        calendar.clear();
    }

    public void testGetClosedHoursForPeriodUS() {
        // Test closed hours
        //
        // From 1/1/15 : 00:00:00 - 1/7/15 : 12:00:00
        // The expected closed hours are ("America/New_York" timezone):
        //
        //  1) 12/31/14 : 16:00:01 - 1/2/15 : 08:59:59 (1420059601000, 1420207199000)
        //  2) 1/2/15   : 16:00:01 - 1/5/15 : 08:59:59 (1420232401000, 1420466399000)
        //  3) 1/5/15   : 16:00:01 - 1/6/15 : 08:59:59 (1420491601000, 1420552799000)
        //  4) 1/6/15   : 16:00:01 - 1/7/15 : 08:59:59 (1420578001000, 1420639199000)

        Pair<Long, Long> range;
        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 1, 0, 0, 0);
        long from = calendar.getTimeInMillis();
        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 7, 12, 0, 0);
        long to = calendar.getTimeInMillis();
        calendar.clear();

        // Closed hours for First week of january
        List<Pair<Long, Long>> closedHours = MarketCalendar.US.getClosedHoursForPeriod(from, to);
        assertEquals(4, closedHours.size());
        //  1) 12/31/14 : 16:00:01 - 1/2/15 : 08:59:59 (1420059601000, 1420207199000)
        range = closedHours.get(0);
        assertEquals(1420059601000l, range.first.longValue());
        assertEquals(1420207199000l, range.second.longValue());
        //  2) 1/2/15 : 16:00:01 - 1/5/15 : 08:59:59 (1420232401000, 1420466399000)
        range = closedHours.get(1);
        assertEquals(1420232401000l, range.first.longValue());
        assertEquals(1420466399000l, range.second.longValue());
        //  3) 1/5/15 : 16:00:01 - 1/6/15 : 08:59:59 (1420491601000, 1420552799000)
        range = closedHours.get(2);
        assertEquals(1420491601000l, range.first.longValue());
        assertEquals(1420552799000l, range.second.longValue());
        //  4) 1/6/15 : 16:00:01 - 1/7/15 : 08:59:59 (1420578001000, 1420639199000)
        range = closedHours.get(3);
        assertEquals(1420578001000l, range.first.longValue());
        assertEquals(1420639199000l, range.second.longValue());

        // Test closed hours ending on weekend
        //
        // From 1/4/15 : 00:00:00 - 1/11/15 : 12:00:00
        // The expected closed hours are ("America/New_York" timezone):
        //
        //  1) 1/2/15 : 16:00:01 - 1/5/15 : 08:59:59 (Friday)
        //  2) 1/5/15 : 16:01:00 - 1/6/15 : 08:59:59
        //  3) 1/6/15 : 16:01:00 - 1/7/15 : 08:59:59
        //  4) 1/7/15 : 16:01:00 - 1/8/15 : 08:59:59
        //  5) 1/8/15 : 16:01:00 - 1/9/15 : 08:59:59
        //  6) 1/9/15 : 16:01:00 - 1/12/15 : 08:59:59 (Monday)

        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 4, 0, 0, 0);
        from = calendar.getTimeInMillis();
        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 11, 12, 0, 0);
        to = calendar.getTimeInMillis();
        calendar.clear();
        closedHours = MarketCalendar.US.getClosedHoursForPeriod(from, to);
        assertEquals(6, closedHours.size());

        //  1) 1/2/15 : 16:00:01 - 1/5/15 : 08:59:59
        range = closedHours.get(0);
        assertEquals(1420232401000l, range.first.longValue());
        assertEquals(1420466399000l, range.second.longValue());
        //  2) 1/5/15 : 16:01 - 1/6/15 : 08:59:59
        range = closedHours.get(1);
        assertEquals(1420491601000l, range.first.longValue());
        assertEquals(1420552799000l, range.second.longValue());
        //  3) 1/6/15 : 16:01 - 1/7/15 : 08:59:59
        range = closedHours.get(2);
        assertEquals(1420578001000l, range.first.longValue());
        assertEquals(1420639199000l, range.second.longValue());
        //  4) 1/7/15 : 16:01 - 1/8/15 : 08:59:59
        range = closedHours.get(3);
        assertEquals(1420664401000l, range.first.longValue());
        assertEquals(1420725599000l, range.second.longValue());
        //  5) 1/8/15 : 16:01 - 1/9/15 : 08:59:59
        range = closedHours.get(4);
        assertEquals(1420750801000l, range.first.longValue());
        assertEquals(1420811999000l, range.second.longValue());
        //  6) 1/9/15 : 16:01 - 1/12/15 : 08:59:59
        range = closedHours.get(5);
        assertEquals(1420837201000l, range.first.longValue());
        assertEquals(1421071199000l, range.second.longValue());


        // Test Single day
        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 5, 12, 0, 0);
        from = calendar.getTimeInMillis();
        calendar.clear();
        calendar.set(2015, Calendar.JANUARY, 6, 12, 0, 0);
        to = calendar.getTimeInMillis();
        calendar.clear();
        closedHours = MarketCalendar.US.getClosedHoursForPeriod(from, to);
        assertEquals(1, closedHours.size());
        //  1) 1/5/15 : 16:01 - 1/6/15 : 08:59:59
        range = closedHours.get(0);
        assertEquals(1420491601000l, range.first.longValue());
        assertEquals(1420552799000l, range.second.longValue());

    }
}
