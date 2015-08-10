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

import com.numenta.core.utils.Pair;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Comparator;
import java.util.List;
import java.util.NavigableSet;
import java.util.TimeZone;
import java.util.TreeSet;

/**
 * Represent Stock market open hours and holidays
 */
public class MarketCalendar {

    /** The US market hours calendar */
    public static final MarketCalendar US = createUSMarketCalendar();

    /** Default timezone used by the Stock Exchange */
    private final TimeZone _timezone;

    /**
     * The hours on which this market is open expressed in 24h format (HHMMSS).
     * For example, the values [93000, 160000] represents the market is open
     * from "9:30:00 AM" to "4:00:00 PM"
     */
    private final Pair<Integer, Integer> _marketHours;

    /** Holiday scheduled. Starting at the marked hour to the end of the marked day */
    private final TreeSet<Long> _holidays;

    /**
     * Represents the days of the week when the market is open.
     * Starting on sunday[0] ending on saturday[6]
     */
    private final boolean _workWeek[];

    /**
     * Construct a new Stock Market Hours calendar given its time zone and hours operation.
     * <p>
     *     Hours of operation (open, close) are expressed in 24h format (HHMMSS). For example, the
     *     values [93000, 160000] represents the market is open from "9:30:00 AM" to "4:00:00 PM"
     * </p>
     *
     * @param timezone The timezone used by the market
     * @param open     The time of the day the market opens expressed in 24h format (HHMMSS).
     * @param close    The time of the day the market closes expressed in 24h format (HHMMSS).
     */
    private MarketCalendar(TimeZone timezone, int open, int close) {
        _timezone = timezone;
        _holidays = new TreeSet<Long>();
        _marketHours = new Pair<Integer, Integer>(open, close);
        // Default Work Weekdays:  Sun  , Mon , Tue , Wed , Thu , Fri , Sat
        _workWeek = new boolean[]{false, true, true, true, true, true, false};
    }

    /**
     * Checks whether the given time fall within the market open hours
     *
     * @param date The date and time to check
     * @return true if the market is open, false otherwise
     */
    public boolean isOpen(Calendar date) {

        // Check for work week
        if (!_workWeek[date.get(Calendar.DAY_OF_WEEK) - 1]) {
            return false;
        }

        // Check for open hours. At second resolution.
        long hhmmss = date.get(Calendar.HOUR_OF_DAY) * 10000
                + date.get(Calendar.MINUTE) * 100
                + date.get(Calendar.SECOND);
        if (hhmmss < _marketHours.first || hhmmss > _marketHours.second) {
            return false;
        }
        // Closed on holiday
        return !isHoliday(date.getTimeInMillis());
    }

    public boolean isOpen(long date) {
        Calendar dateToCheck = Calendar.getInstance(_timezone);
        dateToCheck.setTimeInMillis(date);
        return isOpen(dateToCheck);
    }

    /**
     * Check whether the given date falls on a holiday
     *
     * @param date The date to check (epoch)
     * @return {@code true} if the date falls on a holiday, {@code false} otherwise
     */
    public boolean isHoliday(long date) {
        Long closestHoliday = _holidays.floor(date);
        if (closestHoliday != null) {
            Calendar dateToCheck = Calendar.getInstance(_timezone);
            dateToCheck.setTimeInMillis(date);
            Calendar holiday = Calendar.getInstance(_timezone);
            holiday.setTimeInMillis(closestHoliday);
            // First check if it is the same day as the holiday, then check for partial closed days
            if (holiday.get(Calendar.YEAR) == dateToCheck.get(Calendar.YEAR)
                    && holiday.get(Calendar.DAY_OF_YEAR) == dateToCheck.get(Calendar.DAY_OF_YEAR)
                    && dateToCheck.after(holiday)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Returns an ordered list of all closed hours for the given period
     *
     * @param from The start of the period to check
     * @param to   The end of the period to check
     * @return An ordered list of range for which the market is closed. Each {@link Pair} represents
     * the start and close time in milliseconds.
     * <p><b>Note:</b> The returned range may be larger than the given range as it will include the
     * beginning of the closed period as well as the end of the closed period.
     * </p>
     */
    public List<Pair<Long, Long>> getClosedHoursForPeriod(long from, long to) {

        Calendar current = Calendar.getInstance(_timezone);
        Calendar range = Calendar.getInstance(_timezone);
        List<Pair<Long, Long>> results = new ArrayList<Pair<Long, Long>>();
        long start, end;
        int hour, min, sec;

        // Keep track of closed hours sorted by start time and then by end time in ascending order
        TreeSet<Pair<Long, Long>> closedSet = new TreeSet<Pair<Long, Long>>(new Comparator<Pair<Long, Long>>() {
            @Override
            public int compare(Pair<Long, Long> lhs, Pair<Long, Long> rhs) {
                if (lhs == rhs || lhs.equals(rhs)) {
                    return 0;
                }
                // Priority to lower bound
                if (lhs.first.equals(rhs.first)) {
                    return lhs.second.compareTo(rhs.second);
                }
                return lhs.first.compareTo(rhs.first);
            }
        });

        // Find the beginning of the period
        current.setTimeInMillis(from);
        while(!isOpen(current)) {
            current.add(Calendar.HOUR_OF_DAY, -1);
        }
        long fromDate = current.getTimeInMillis();

        // Find the end of the period
        current.setTimeInMillis(to);
        while(!isOpen(current)) {
            current.add(Calendar.HOUR_OF_DAY, 1);
        }
        long toDate = current.getTimeInMillis();

        // Add all holidays for the period
        NavigableSet<Long> holidaysInPeriod = _holidays.subSet(fromDate, true, toDate, true);
        for (Long holiday : holidaysInPeriod) {
            // Set range from the beginning of the holiday until next day opening hour. "9:29:59" (next day)
            range.setTimeInMillis(holiday);
            range.add(Calendar.DAY_OF_MONTH, 1);
            hour = _marketHours.first / 10000;
            min = (_marketHours.first % 10000) / 100;
            sec = _marketHours.first % 100;
            range.set(Calendar.HOUR_OF_DAY, hour);
            range.set(Calendar.MINUTE, min);
            range.set(Calendar.SECOND, sec);
            range.add(Calendar.SECOND, -1);
            end = range.getTimeInMillis();

            closedSet.add(new Pair<Long, Long>(holiday, end));
        }

        // Find all weekends and closed hours
        current.setTimeInMillis(fromDate);
        while (current.getTimeInMillis() < toDate) {
            if (_workWeek[current.get(Calendar.DAY_OF_WEEK) - 1]) {
                // Add closed hours during workdays, from closing hour to opening hour in the next day
                long time = current.getTimeInMillis();
                range.setTimeInMillis(time);

                // Closing hour plus one second ("16:00:01")
                hour = _marketHours.second / 10000;
                min = (_marketHours.second % 10000) / 100;
                sec = _marketHours.second % 100;
                range.set(Calendar.HOUR_OF_DAY, hour);
                range.set(Calendar.MINUTE, min);
                range.set(Calendar.SECOND, sec);
                range.set(Calendar.MILLISECOND, 0);
                range.add(Calendar.SECOND, 1);
                start = range.getTimeInMillis();

                // Opening hour in the next day minus one second ("09:29:59")
                range.setTimeInMillis(time);
                range.add(Calendar.DAY_OF_MONTH, 1);
                hour = _marketHours.first / 10000;
                min = (_marketHours.first % 10000) / 100;
                sec = _marketHours.first % 100;
                range.set(Calendar.HOUR_OF_DAY, hour);
                range.set(Calendar.MINUTE, min);
                range.set(Calendar.SECOND, sec);
                range.set(Calendar.MILLISECOND, 0);
                range.add(Calendar.SECOND, -1);
                end = range.getTimeInMillis();

                closedSet.add(new Pair<Long, Long>(start, end));
            } else {
                // On weekends add whole day until next day opening hour. From "00:00:00" to "9:29:59" (next day)
                range.setTimeInMillis(current.getTimeInMillis());
                range.set(Calendar.HOUR_OF_DAY, 0);
                range.set(Calendar.MINUTE, 0);
                range.set(Calendar.SECOND, 0);
                range.set(Calendar.MILLISECOND, 0);
                start = range.getTimeInMillis();

                // Opening hour in the next day minus one second ("09:29:59")
                range.setTimeInMillis(current.getTimeInMillis());
                range.add(Calendar.DAY_OF_MONTH, 1);
                hour = _marketHours.first / 10000;
                min = (_marketHours.first % 10000) / 100;
                sec = _marketHours.first % 100;
                range.set(Calendar.HOUR_OF_DAY, hour);
                range.set(Calendar.MINUTE, min);
                range.set(Calendar.SECOND, sec);
                range.set(Calendar.MILLISECOND, 0);
                range.add(Calendar.SECOND, -1);
                end = range.getTimeInMillis();

                closedSet.add(new Pair<Long, Long>(start, end));
            }
            // Next day
            current.add(Calendar.DAY_OF_MONTH, 1);
        }

        // Consolidate closed hours
        start = 0;
        end = 0;
        for (Pair<Long, Long> pair : closedSet) {
            if (pair.first <= end) {
                // Extend range
                end = Math.max(end, pair.second);
            } else if (pair.first > end) {
                // Start a new sequence
                if (start != 0 && end != 0) {
                    results.add(new Pair<Long, Long>(start, end));
                }
                start = pair.first;
                end = pair.second;
            }
        }
        // Add last range if necessary
        if (start < toDate) {
            results.add(new Pair<Long, Long>(start, end));
        }
        return results;
    }

    /**
     * Create US Market hours calendar based on https://www.nyse.com/markets/hours-calendars and
     * http://www.nasdaq.com/about/trading-schedule.aspx
     *
     * @return Market Calendar configure for US market hours
     */
    private static MarketCalendar createUSMarketCalendar() {

        // Open from 9:00am to 4:00pm, New York time.
        // Even though the market actually opens at 9:30am we will use 9:00am as opening time
        MarketCalendar marketCalendar = new MarketCalendar(
                TimeZone.getTimeZone("America/New_York"), 90000, 160000);
        Calendar cal = Calendar.getInstance(marketCalendar._timezone);
        cal.clear();

        // New Years Day
        cal.set(2015, Calendar.JANUARY, 1, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.JANUARY, 1, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Martin Luther King, Jr. Day
        cal.set(2015, Calendar.JANUARY, 19, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.JANUARY, 18, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // President's Day
        cal.set(2015, Calendar.FEBRUARY, 16, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.FEBRUARY, 15, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Good Friday
        cal.set(2015, Calendar.APRIL, 3, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.MARCH, 25, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Memorial Day
        cal.set(2015, Calendar.MAY, 25, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.MAY, 30, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Independence Day
        cal.set(2015, Calendar.JULY, 3, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.JULY, 4, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Labor Day
        cal.set(2015, Calendar.SEPTEMBER, 7, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.SEPTEMBER, 5, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Thanksgiving Day
        cal.set(2015, Calendar.NOVEMBER, 26, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2015, Calendar.NOVEMBER, 27, 13, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.NOVEMBER, 24, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.NOVEMBER, 25, 13, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        // Christmas
        cal.set(2015, Calendar.DECEMBER, 24, 13, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2015, Calendar.DECEMBER, 25, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        cal.set(2016, Calendar.DECEMBER, 26, 0, 0, 0);
        marketCalendar._holidays.add(cal.getTimeInMillis());
        cal.clear();

        return marketCalendar;
    }
}
