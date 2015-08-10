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

package com.numenta.taurus.chart;

import com.numenta.core.data.AggregationType;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.text.TextPaint;
import android.util.AttributeSet;
import android.util.DisplayMetrics;
import android.view.View;

import java.text.DateFormatSymbols;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;

/**
 * Display a time slider view showing the time broken into fixed intervals at the top and at the
 * bottom of the view using alternating background color aligned on every interval.
 * <p>You can customize the look and feel using the following styled attributes:
 * <ul>
 * <li><b>labelHeight</b>: Label area Height. The label will be vertically aligned based on this
 * value. Default <em>48</em> pixels</li>
 * <li><b>labelTextColor</b>: Text Color for top and bottom labels. Default {@link
 * Color#DKGRAY}</li>
 * <li><b>labelTextSize</b>: Text Size for top and bottom labels. Default <em>24</em> pixes</li>
 * <li><b>showLabel</b>: Whether or not to show the labels. Possible values are <em>"none", "top",
 * "bottom" or "top|bottom"</em>. Default <em>"top|bottom"</em></li>
 * <li><b>showBackground</b>: Whether or not to show the background. Default true.</li>
 * <li><b>backgroundColorLight:</b> Light background color. Default {@link Color#WHITE}</li>
 * <li><b>backgroundColorDark:</b> Dark background color. Default {@link Color#LTGRAY}</li>
 * </ul>
 * </p>
 * <p><b>Usage:</b>
 * <code><pre>
 *      &lt;com.numenta.taurus.chart.TimeSliderView
 *              android:id="@+id/time_slider"
 *              android:layout_width="fill_parent"
 *              android:layout_height="fill_parent"
 *              android:background="#e0e0e0"
 *              app:labelHeight="24sp"
 *              app:labelTextSize="14sp"
 *              app:labelTextColor="#777777"
 *              app:backgroundColorDark="#FFFFFF"
 *              app:backgroundColorLight="#F5F5F5"/&gt;
 * </pre></code>
 * </p>
 */
public class TimeSliderView extends View {

    private static final int SHOW_TOP_LABEL = 1;

    private static final int SHOW_BOTTOM_LABEL = 2;

    private static final int SHOW_ALL_LABELS = 3;

    private final int _labelHeight;

    private final TextPaint _textPaint;

    private final Paint _strokePaint;

    private final Paint _lightPaint;

    private final Paint _darkPaint;

    private final int _labelCenterTop;

    private final int _labelCenterBottom;

    private long _endDate;

    private List<Pair<Long, Long>> _closedHours;

    private final Rect _viewArea = new Rect();

    private final RectF _labelRect = new RectF();

    private final RectF _barRect = new RectF();

    private int _chartTotalBars;

    private float _barWidth;

    private final boolean _showTopLabel;

    private final boolean _showBottomLabel;

    private final boolean _showBackGround;

    private final Calendar _calendar = Calendar.getInstance();

    private AggregationType _aggregation ;

    private SimpleDateFormat _sdf;

    private boolean _collapsed = true;

    public TimeSliderView(Context context) {
        this(context, null);
    }

    public TimeSliderView(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public TimeSliderView(Context context, AttributeSet attrs,
            int defStyle) {
        super(context, attrs, defStyle);
        _chartTotalBars = TaurusApplication.getTotalBarsOnChart();

        // Get styleable attributes
        TypedArray style = context.getTheme()
                .obtainStyledAttributes(attrs, R.styleable.TimeSliderView, defStyle, defStyle);

        // Setup text style
        DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
        float size = style.getDimension(R.styleable.TimeSliderView_labelTextSize, 24);
        int color = style.getColor(R.styleable.TimeSliderView_labelTextColor, Color.DKGRAY);
        _textPaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
        _textPaint.density = displayMetrics.density;
        _textPaint.setSubpixelText(true);
        _textPaint.setAntiAlias(true);
        _textPaint.setDither(true);
        _textPaint.setTextSize(size);
        _textPaint.setColor(color);
        _textPaint.setTypeface(Typeface.DEFAULT_BOLD);
        _textPaint.setTextAlign(Paint.Align.LEFT);

        _labelHeight = style.getDimensionPixelSize(R.styleable.TimeSliderView_labelHeight, 48);

        // Label center position
        _labelCenterTop = (int) (_labelHeight / 2
                - (_textPaint.descent() + _textPaint.ascent()) / 2);
        _labelCenterBottom = (int) (_labelHeight / 2
                + (_textPaint.descent() + _textPaint.ascent()) / 2);

        // Setup background style
        color = style.getColor(R.styleable.TimeSliderView_backgroundColorLight, 0);
        _lightPaint = new Paint();
        _lightPaint.setColor(color);
        _lightPaint.setStrokeJoin(Paint.Join.ROUND);
        _lightPaint.setStyle(Paint.Style.FILL);
        _lightPaint.setAntiAlias(true);

        color = style.getColor(R.styleable.TimeSliderView_backgroundColorDark, 0);
        _darkPaint = new Paint();
        _darkPaint.setColor(color);
        _darkPaint.setStrokeJoin(Paint.Join.ROUND);
        _darkPaint.setStyle(Paint.Style.FILL);
        _darkPaint.setAntiAlias(true);

        // Make default stroke color a little darker then _darkPaint
        color = style
                .getColor(R.styleable.TimeSliderView_strokeColor, _darkPaint.getColor() - 0x202020);
        _strokePaint = new Paint();
        _strokePaint.setStrokeWidth(1);
        _strokePaint.setColor(color);
        _strokePaint.setStrokeJoin(Paint.Join.ROUND);
        _strokePaint.setStyle(Paint.Style.STROKE);
        _strokePaint.setAntiAlias(true);

        // Get flags
        _showBackGround = style.getBoolean(R.styleable.TimeSliderView_showBackground, true);
        int showLabel = style.getInteger(R.styleable.TimeSliderView_showLabel, SHOW_ALL_LABELS);
        _showTopLabel = (showLabel & SHOW_TOP_LABEL) == SHOW_TOP_LABEL;
        _showBottomLabel = (showLabel & SHOW_BOTTOM_LABEL) == SHOW_BOTTOM_LABEL;

        setAggregation(TaurusApplication.getAggregation());

        // Preview in edit mode
        if (isInEditMode()) {
            _chartTotalBars = 24;
            setAggregation(AggregationType.Day);
            Calendar cal = Calendar.getInstance();
            setEndDate(cal.getTimeInMillis());
        }
    }

    /**
     * End Date, in milliseconds (Unix time)
     */
    public void setEndDate(long endDate) {
        _endDate = DataUtils.floorTo5minutes(endDate);
        _closedHours = null;
        invalidate();
    }

    /**
     * Get the current aggregation type based on the date range
     */
    @SuppressLint("SimpleDateFormat")
    public void setAggregation(AggregationType aggregation) {
        _aggregation = aggregation;
        // Update date format symbols converting "AM/PM" to "a/p"
        DateFormatSymbols symbols = new DateFormatSymbols(Locale.US);
        symbols.setAmPmStrings(new String[]{"a", "p"});
        // Configure date formatter based on new aggregation type
        switch (_aggregation) {
            case Hour:
                _sdf = new SimpleDateFormat("h:mm", symbols);
                break;
            case HalfDay:
                _sdf = new SimpleDateFormat("h:mma", symbols);
                break;
            case Day:
                _sdf = new SimpleDateFormat("ha", symbols);
                break;
            case Week:
                _sdf = new SimpleDateFormat("E", symbols);
                break;
        }
        invalidate();
    }

    /**
     * Draw the given time at the given position
     *
     * @param canvas the canvas on which the background will be drawn
     * @param time   The timestamp in milliseconds to draw
     */
    private void drawLabel(Canvas canvas, long time, float left, float top, float right,
            float bottom) {

        if (_showBottomLabel || _showTopLabel) {
            _calendar.setTimeInMillis(time);
            String labelStr = _sdf.format(_calendar.getTime());
            _labelRect.set(left, top, right, bottom);
            // Draw  top label
            if (_showTopLabel) {
                canvas.drawText(labelStr, _labelRect.left, _labelRect.top + _labelCenterTop,
                        _textPaint);
            }
            // Draw  bottom label
            if (_showBottomLabel) {
                canvas.drawText(labelStr, _labelRect.left, _labelRect.bottom - _labelCenterBottom,
                        _textPaint);
            }
        }
    }

    /**
     * Draw labels top and bottom background on the given canvas
     */
    private void drawLabelsBackground(Canvas canvas, long time, float left, float top, float right,
            float bottom) {

        if (_showBottomLabel || _showTopLabel) {
            // Check for next bar therefore add one interval to time
            boolean isClosed = !TaurusApplication.getMarketCalendar().isOpen(time + DataUtils.METRIC_DATA_INTERVAL);
            if (_showBottomLabel) {
                _labelRect.set(left, bottom - _labelHeight, right, top + getHeight());
                canvas.drawRect(_labelRect, isClosed ? _darkPaint : _lightPaint);
                // Draw label divider lines
                if (!_collapsed || !isClosed) {
                    _labelRect.bottom = _labelRect.top + 1;
                    canvas.drawRect(_labelRect, _strokePaint);
                }
            }
            if (_showTopLabel) {
                _labelRect.set(left, top, right, top + _labelHeight);
                canvas.drawRect(_labelRect, isClosed ? _darkPaint : _lightPaint);
                // Draw label divider lines
                if (!_collapsed || !isClosed) {
                    _labelRect.top = _labelRect.bottom - 1;
                    canvas.drawRect(_labelRect, _strokePaint);
                }
            }
        }
    }


    /**
     * Draw a bar representing the "collapsed" time ranges
     *
     * @param canvas the canvas on which the bar will be drawn
     * @param left   The X coordinate of the left side of the bar
     * @param top    The Y coordinate of the top of the bar
     * @param right  The X coordinate of the right side of the bar
     * @param bottom The Y coordinate of the bottom of the bar
     * @see #getCollapseTimeRange(long)
     */
    private void drawCollapsedBar(Canvas canvas, float left, float top, float right, float bottom) {
        _labelRect.set(left, top, right, bottom);
        canvas.drawRect(_labelRect, _darkPaint);
        canvas.drawRect(_labelRect, _strokePaint);
    }


    /**
     * Draw alternating background and time labels on the given canvas.
     * Start at midnight (00:00) and switch every 3 hours.
     * For example:
     * |12a     |3a     |6a     |9a ...
     * |        |xxxxxxx|       |xxxxxxx
     */
    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (_endDate == 0 || _aggregation == null) {
            // Nothing to draw
            return;
        }
        canvas.save();

        // Initialize the the bar rect for each bar starting from the right most bar
        // Use float vars for calculations to avoid rounding errors
        float left = _viewArea.right - _barWidth;
        float right = _viewArea.right;
        float top = _viewArea.top;
        float bottom = _viewArea.bottom;

        // Time rounded to the aggregation
        long interval = _aggregation.milliseconds();
        long time = (_endDate / interval) * interval;

        // Draw one bar at the time starting from the right most bar
        int bar = _chartTotalBars;
        boolean previousCollapsed = false;
        while (bar > 0) {
            if (_showBackGround) {
                // Draw bar background leaving room for labels
                _barRect.set(left, top + (_showTopLabel ? _labelHeight : 0),
                        right, bottom - (_showBottomLabel ? _labelHeight : 0));
                // Switch Color on market closed hours. Check for next bar therefore add one interval to time
                Paint color = TaurusApplication.getMarketCalendar().isOpen(time + DataUtils.METRIC_DATA_INTERVAL)
                        ? _lightPaint : _darkPaint;
                canvas.drawRect(_barRect, color);
            }
            // Skip labels if the previous bar was collapsed.
            if (!previousCollapsed) {
                _calendar.setTimeInMillis(time);
                // Draw label background
                drawLabelsBackground(canvas, time, left, top, right, bottom);

                //  Draw label every 4 hours
                if ((_calendar.get(Calendar.HOUR_OF_DAY) % 3) == 0) {
                    // Draw Labels
                    drawLabel(canvas, time, left, top, right, bottom);
                }
            }

            // Check if this view should show collapsed time range
            previousCollapsed = false;
            if (_collapsed) {
                // Check for collapsed time ranges
                Pair<Long, Long> range = getCollapseTimeRange(time);
                if (range != null) {
                    // Draw folded bar
                    drawCollapsedBar(canvas, left, top, right, bottom);

                    // Update time to beginning of the range
                    time = range.first - interval;

                    // Move one bar to the left
                    left -= _barWidth;
                    right -= _barWidth;
                    bar--;

                    // Draw label to the left of the collapsed bar
                    previousCollapsed = true;
                    // Draw label background occupying 2 bars
                    drawLabelsBackground(canvas, time, left - _barWidth, top, right, bottom);
                    // Draw Label outside collapsed bar
                    drawLabel(canvas, time, left - _barWidth / 2, top, right, bottom);
                }
            }

            // Offset to previous bar
            left -= _barWidth;
            right -= _barWidth;
            time -= interval;
            bar--;

        }
        canvas.restore();
    }

    /**
     * Set whether or not to collapse the time for this view. If {@code true} the view will
     * collapse the the time based on the results of {@link #getCollapseTimeRange}.
     */
    public void setCollapsed(boolean collapsed) {
        _collapsed = collapsed;
        invalidate();
    }

    /**
     * Check whether or not time will be collapsed for this view
     */
    public boolean isCollapsed() {
        return _collapsed;
    }

    /**
     * Returns the collapsed time range containing the given time if any.
     *
     * @param time The timestamp in milliseconds to get the collapsed range
     * @return A {@link Pair} containing the collapsed time range, {@link Pair#first} for the
     * beginning of the range and {@link Pair#second} for the end of the range. If the given time
     * does not belong to any configured collapsed time range return {@code null}
     * @see com.numenta.taurus.TaurusApplication#getMarketCalendar()
     * @see com.numenta.taurus.data.MarketCalendar#getClosedHoursForPeriod
     */
    private Pair<Long, Long> getCollapseTimeRange(long time) {
        if (_closedHours == null) {
            _calendar.setTimeInMillis(_endDate);
            _calendar.add(Calendar.DATE, -7);
            _closedHours = TaurusApplication.getMarketCalendar()
                    .getClosedHoursForPeriod(_calendar.getTimeInMillis(), _endDate);
        }
        for (Pair<Long, Long> pair : _closedHours) {
            if (time >= pair.first && time <= pair.second) {
                return pair;
            }
        }
        return null;
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        _viewArea.set(
                getPaddingLeft(),
                getPaddingTop(),
                getWidth() - getPaddingRight(),
                getHeight() - getPaddingBottom());
        _barWidth = (float) _viewArea.width() / _chartTotalBars;
    }
}
