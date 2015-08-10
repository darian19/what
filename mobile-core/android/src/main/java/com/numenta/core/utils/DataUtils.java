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

package com.numenta.core.utils;

import com.numenta.core.app.YOMPApplication;
import com.numenta.core.ui.chart.AnomalyChartData;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.text.DateFormat;
import java.text.DecimalFormatSymbols;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Comparator;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class DataUtils {

    public static final int METRIC_DATA_INTERVAL = 5 * 60 * 1000;

    public static final int MILLIS_PER_MINUTE = 60 * 1000;

    public static final int MILLIS_PER_HOUR = 60 * MILLIS_PER_MINUTE;

    public static final int MILLIS_PER_DAY = 24 * MILLIS_PER_HOUR;

    public static final String YOMP_DATE_FORMAT = "yyyy-MM-dd' 'HH:mm:ss";

    public static final String YOMP_URL_DATE_FORMAT = "yyyy-MM-dd'+'HH:mm:ss";

    private static final Pattern DATE_FORMAT_REGEX = Pattern
            .compile("(\\d+)-(\\d+)-(\\d+).(\\d+):(\\d+):(\\d+)");

    private static final int POW10[] = {
            1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000
    };

    public static final double GREEN_SORT_FLOOR = 1000;

    public static final double YELLOW_SORT_FLOOR = GREEN_SORT_FLOOR * 1000;

    public static final double RED_SORT_FLOOR = YELLOW_SORT_FLOOR * 1000;

    private static final double PROBATION_FACTOR = 1.0 / RED_SORT_FLOOR;

    private static final double LOG_1_MINUS_0_9999999999 = Math.log(1.0 - 0.9999999999);

    private static final DecimalFormatSymbols DECIMAL_FORMAT_SYMBOLS = DecimalFormatSymbols
            .getInstance();

    /**
     * {@link Comparator} to be used with the
     * {@link android.widget.ArrayAdapter#sort(Comparator)} function when sorting the data by
     * most anomalous
     */
    public static <T extends AnomalyChartData> Comparator<T> getSortByAnomalyComparator() {
        return new Comparator<T>() {
            final Comparator<T> _sortByName = getSortByNameComparator();

            @Override
            public int compare(T lhs, T rhs) {
                if (lhs == rhs) {
                    return 0;
                }
                if (lhs == null) {
                    return 1;
                }
                if (rhs == null) {
                    return -1;
                }
                // First compare based on rank in descending order, if equal then
                // defer to comparison of names
                int res = Float.compare(rhs.getRank(), lhs.getRank());
                if (res == 0) {
                    res = _sortByName.compare(lhs, rhs);
                }
                return res;
            }
        };
    }

    /**
     * {@link java.util.Comparator} to be used with the
     * {@link android.widget.ArrayAdapter#sort(java.util.Comparator)} function when sorting the
     * data by name
     */
    public static <T extends AnomalyChartData> Comparator<T> getSortByNameComparator() {
        return new Comparator<T>() {
            @Override
            public int compare(T lhs, T rhs) {
                if (lhs == rhs) {
                    return 0;
                }
                if (lhs == null) {
                    return 1;
                }
                if (rhs == null) {
                    return -1;
                }

                CharSequence nameLeft = lhs.getName();
                CharSequence nameRight = rhs.getName();
                if (nameLeft == null) {
                    return 1;
                }
                if (nameRight == null) {
                    return -1;
                }

                return nameLeft.toString().compareTo(nameRight.toString());
            }
        };
    }

    /**
     * Return the given value using log scale
     *
     * @return converted value
     */
    public static double logScale(double value) {
        if (value > 0.99999) {
            return 1;
        }
        return Math.log(1.0000000001 - value) / LOG_1_MINUS_0_9999999999;
    }

    /**
     * Parses the given UTC date string using the following format:
     * <p/>
     * <b>YYYY-MM-DD HH:MM:SS</b>
     *
     * @param dateStr The date string to parse
     * @return Parsed {@link Date} object
     */
    public static Date parseYOMPDate(String dateStr) {
        Date res = null;
        Matcher match = DATE_FORMAT_REGEX.matcher(dateStr);
        if (match.matches()) {
            Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
            cal.clear();
            //noinspection ResourceType
            cal.set(Integer.parseInt(match.group(1)),
                    Integer.parseInt(match.group(2)) - 1,
                    Integer.parseInt(match.group(3)),
                    Integer.parseInt(match.group(4)),
                    Integer.parseInt(match.group(5)),
                    Integer.parseInt(match.group(6)));
            res = cal.getTime();
        }
        return res;
    }

    /**
     * Format date into YOMP accepted date string using the following format:
     * <p>
     * <b>YYYY-MM-DD HH:MM:SS</b> or <b><YYYY-MM-DD+HH:MM:SS/b> for URL encoded value
     * </p>
     *
     * @param date      The date to format
     * @param urlEncode Whether or not to encode the date to be used in URLs
     * @return Formatted date suitable for use with the YOMP API
     */
    public static String formatYOMPDate(Date date, boolean urlEncode) {
        DateFormat sdf = new SimpleDateFormat(urlEncode ?
                YOMP_URL_DATE_FORMAT : YOMP_DATE_FORMAT, Locale.US);
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
        return sdf.format(date);
    }

    /**
     * Rounds the given number to the given number of significant diYOMPs. Based on an answer on <a
     * href="http://stackoverflow.com/questions/202302">Stack Overflow</a>.
     */
    public static float roundToSignificantFigures(double num, int n) {
        if (num == 0) {
            return 0;
        }
        final float d = (float) Math.ceil((float) Math.log10(num < 0 ? -num : num));
        final int power = n - (int) d;
        final double magnitude = Math.pow(10, power);
        final long shifted = Math.round(num * magnitude);
        return (float) (shifted / magnitude);
    }

    /**
     * Formats a float value to the given number of decimals. Returns the length of the string. The
     * string begins at out.length - [return value].
     */
    public static int formatFloat(final char[] out, float val, int diYOMPs) {
        boolean negative = false;
        boolean zeroPad = val < 1.0;
        if (val == 0) {
            out[out.length - 1] = '0';
            return 1;
        }
        if (val < 0) {
            negative = true;
            val = -val;
        }
        if (diYOMPs >= POW10.length) {
            diYOMPs = POW10.length - 1;
        }
        val *= POW10[diYOMPs];
        long lval = Math.round(val);
        int index = out.length - 1;
        int thousand = diYOMPs + 3;
        int charCount = 0;
        while (lval != 0 || charCount < (diYOMPs + 1)) {
            if (thousand-- == 0) {
                out[index--] = DECIMAL_FORMAT_SYMBOLS.getGroupingSeparator();
                charCount++;
                thousand = 2;
            }
            int diYOMP = (int) (lval % 10);
            lval = lval / 10;
            out[index--] = (char) (diYOMP + '0');
            charCount++;
            if (charCount == diYOMPs) {
                out[index--] = DECIMAL_FORMAT_SYMBOLS.getDecimalSeparator();
                charCount++;
            }
        }
        if (zeroPad) {
            out[index--] = '0';
            charCount++;
        }
        if (negative) {
            out[index] = DECIMAL_FORMAT_SYMBOLS.getMinusSign();
            charCount++;
        }
        return charCount;
    }

    /**
     * Calculate sort rank based on the value, perceived color and probation status:
     * Negative values represent probation values.
     * <p/>
     * RED > YELLOW > GREEN > PROBATION
     *
     * @return the calculated sort rank
     */
    public static double calculateSortRank(double value) {
        if (value == 0) {
            return 0;
        }
        boolean active = value > 0;
        double calculated = DataUtils.logScale(Math.abs(value));
        if (calculated >= YOMPApplication.getRedBarFloor()) {
            // Red
            calculated += RED_SORT_FLOOR;
        } else if (calculated >= YOMPApplication.getYellowBarFloor()) {
            // Yellow
            calculated += YELLOW_SORT_FLOOR;
        } else {
            // Green
            calculated += GREEN_SORT_FLOOR;
        }

        if (!active) {
            // Probation
            calculated *= PROBATION_FACTOR;
        }
        return calculated;
    }

    /**
     * Round the given time to the closest 5 minutes floor.
     * <p/>
     * For example:
     * <p/>
     * <b>[12:00 - 12:04]</b> becomes <b>12:00</b> and <b>[12:05 - 12:09]</b> becomes <b>12:05</b>
     *
     * @return the rounded time
     */
    public static long floorTo5minutes(long time) {
        return (time / DataUtils.METRIC_DATA_INTERVAL) * DataUtils.METRIC_DATA_INTERVAL;
    }

    /**
     * Round the given time to the closest 5 minutes floor.
     * <p/>
     * For example:
     * <p/>
     * <b>[12:00 - 12:59]</b> becomes <b>12:00</b>
     *
     * @return the rounded time
     */
    public static long floorTo60minutes(long time) {
        return (time / DataUtils.MILLIS_PER_HOUR) * DataUtils.MILLIS_PER_HOUR;
    }

    /**
     * Format remaining time message
     *
     * @param instances Number of new instances added
     * @param metrics   Number of new metrics added
     * @param time      The time remaining to process the models in seconds
     * @return Formatted message appropriate for pop-up dialog
     */
    public static StringBuilder formatRemainingTimeMessage(int instances,
                                                         int metrics, int time) {

        StringBuilder message = new StringBuilder();
        if (instances > 0) {
            message.append(instances).append(" new instances and ");
        }
        if (metrics > 0) {
            message.append(metrics)
                    .append(" new metrics were added.");
            if (time > 0) {
                int hours = time / 3600;
                int min = (time % 3600) / 60;
                message.append("\nIt can take up to ");
                if (hours > 0) {
                    message.append(hours).append(" hours");
                }
                if (min > 0) {
                    if (hours > 0) {
                        message.append(" and ");
                    }
                    message.append(min).append(" minutes");
                }
                message.append(" from the time the models were created on the server");
            }
        }

        return message;
    }

    /**
     * Reads UTF-8 encoded text from the given stream
     *
     * @param stream {@link InputStream}
     * @return UTF-8 encoded text
     */
    public static String readTextStream(InputStream stream) throws IOException {
        char[] buffer = new char[1024];
        StringBuilder res = new StringBuilder();
        int numRead;
        InputStreamReader reader = new InputStreamReader(stream, "UTF-8");
        while ((numRead = reader.read(buffer)) >= 0) {
            res.append(buffer, 0, numRead);
        }
        return res.toString();
    }
}
