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

import com.numenta.core.R;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.AggregationType;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.Paint;
import android.graphics.Paint.Join;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.support.annotation.NonNull;
import android.text.TextPaint;
import android.util.AttributeSet;
import android.util.DisplayMetrics;
import android.util.TypedValue;
import android.view.MotionEvent;
import android.view.View;

import java.util.Arrays;
import java.util.Calendar;
import java.util.List;

/**
 * Anomaly chart view.
 * <p>
 * Display the values as the anomaly bar chart where each value correspond to
 * the anomaly value (0..1) at the specific time.
 * Negative anomaly scores represent values in probation period and will
 * be displayed in grey scale instead of color.
 * <p/>
 * </p>
 * * Usage: </p>
 * <ul>
 * <li>Layout:
 * <p/>
 * <pre>
 *      &lt;com.YOMPsolutions.sandbox.AnomalyChartView
 *         android:id="@+id/line_chart_view"
 *         android:layout_width="fill_parent"
 *         android:layout_height="70dp"
 *         android:background="@android:color/transparent"
 *         android:paddingLeft="15dp"
 *         android:paddingRight="15dp"
 *         app:barDrawable="@drawable/anomaly_bar_gradient"
 *         app:barMarginRight="2sp"
 *         app:textColor="#A4A4A4"
 *         app:textColorBold="#000000"
 *         app:labelHeight="24sp"
 *         app:textSize="12sp" /&gt;
 * </pre>
 * <li>Code:
 * <p/>
 * <pre>
 *
 * <code>
 * AnomalyChartView chart = (AnomalyChartView) findViewById(R.id.line_chart_view);
 * float[] result = new float[24];
 * float offset = 1.0f / result.length;
 * float val = offset;
 * for (int i = 0; i &lt; result.length; i++) {
 *     result[i] = val;
 *     val += offset;
 * }
 * Calendar cal = Calendar.getInstance();
 * cal.set(2013, Calendar.DECEMBER, 20, 9, 50, 0);
 * Date fromDate = cal.getTime();
 * cal.add(Calendar.MINUTE, 5 * (result.length - 1));
 * Date toDate = cal.getTime();
 * chart.setData(fromDate, toDate, result);
 * chart.setDateRange(fromDate, toDate);
 * chart.invalidate();
 * </code>
 * </pre>
 */
public class AnomalyChartView extends View {

    // Week day format
    // FIXME: Internationalize
    private static final char[] WEEKDAYS = {
            'S', 'M', 'T', 'W', 'T', 'F', 'S'
    };

    // Anomaly scores
    private float _data[];

    // Date range
    private long _startDate;

    private long _endDate;

    // Flagged dates
    private long _flags[];

    // Styles
    private Drawable _flagDrawable;

    private Drawable _barDrawable;

    private Paint _emptyBarPaint;

    private int _barMarginLeft;

    private int _barMarginRight;

    private TextPaint _textPaint;

    private TextPaint _textPaintBold;

    private int _labelHeight;

    private ColorMatrixColorFilter _inactiveBarFilter;

    // Layout
    private final Rect _chartArea = new Rect();

    private final Rect _labelsArea = new Rect();

    private final Rect _barRect = new Rect();

    private float _barWidth;

    private int _emptyBarHeight;

    private AggregationType _aggregation;

    private final Calendar _calendar = Calendar.getInstance();

    private final StringBuilder _label = new StringBuilder();

    private float _markerRadius = 3f;

    private int _chartTotalBars;

    private long _selectedTimestamp = -1;

    public AnomalyChartView(Context context) {
        this(context, null);
    }

    public AnomalyChartView(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public AnomalyChartView(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
        TypedArray style = context.getTheme().obtainStyledAttributes(attrs,
                R.styleable.AnomalyChartView, defStyle, defStyle);
        try {
            // Flag Icon
            _flagDrawable = style.getDrawable(R.styleable.AnomalyChartView_flagDrawable);
            if (_flagDrawable == null) {
                _flagDrawable = context.getResources().getDrawable(R.drawable.flag_selector);
            }

            // Anomaly bar drawable
            _barDrawable = style.getDrawable(R.styleable.AnomalyChartView_barDrawable);
            if (_barDrawable == null) {
                _barDrawable = context.getResources().getDrawable(R.drawable.anomaly_bar_gradient);
            }

            _barMarginLeft = style.getDimensionPixelOffset(
                    R.styleable.AnomalyChartView_barMarginLeft, 0);
            _barMarginRight = style.getDimensionPixelOffset(
                    R.styleable.AnomalyChartView_barMarginRight, 0);

            // Inactive filter
            ColorMatrix cm = new ColorMatrix();
            cm.setSaturation(0);
            _inactiveBarFilter = new ColorMatrixColorFilter(cm);

            int textColor = style.getColor(R.styleable.AnomalyChartView_android_textColor, 0);
            float textSize = style.getDimension(R.styleable.AnomalyChartView_android_textSize, 0);
            _labelHeight = style
                    .getDimensionPixelSize(R.styleable.AnomalyChartView_barLabelHeight, 24);

            // Setup text style
            DisplayMetrics displayMetrics = getResources().getDisplayMetrics();

            _markerRadius = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 1.5f,
                    displayMetrics);
            _chartTotalBars = YOMPApplication.getTotalBarsOnChart();

            _textPaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
            _textPaint.density = displayMetrics.density;

            _textPaint.setSubpixelText(true);
            _textPaint.setAntiAlias(true);
            _textPaint.setDither(true);

            _textPaint.setTextSize(textSize);
            _textPaint.setColor(textColor);
            _textPaint.setTypeface(Typeface.DEFAULT_BOLD);
            _textPaint.setTextAlign(Paint.Align.CENTER);

            _textPaintBold = new TextPaint(Paint.ANTI_ALIAS_FLAG);
            _textPaintBold.density = displayMetrics.density;

            _textPaintBold.setSubpixelText(true);
            _textPaintBold.setAntiAlias(true);
            _textPaintBold.setDither(true);

            _textPaintBold.setTextSize(textSize);
            _textPaintBold.setColor(Color.BLACK);
            _textPaintBold.setTypeface(Typeface.DEFAULT_BOLD);
            _textPaintBold.setTextAlign(Paint.Align.CENTER);

            // Empty bar paint
            int emptyBarColor = style.getColor(R.styleable.AnomalyChartView_emptyBarColor,
                    Color.BLACK);
            _emptyBarPaint = new Paint();
            _emptyBarPaint.setStrokeWidth(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 1,
                    displayMetrics));
            _emptyBarPaint.setColor(emptyBarColor);
            _emptyBarPaint.setStrokeJoin(Join.ROUND);
            _emptyBarPaint.setStyle(Paint.Style.STROKE);
            _emptyBarPaint.setAntiAlias(true);

            // Debug paint
            // _paint = new Paint();
            // _paint.setStrokeWidth(1);
            // _paint.setColor(Color.BLACK);
            // _paint.setStrokeJoin(Join.ROUND);
            // _paint.setStyle(Paint.Style.FILL);
            // _paint.setAntiAlias(true);
            if (isInEditMode()) {
                _chartTotalBars = 24;
                // Editor mode, just show some data
                _calendar.set(2014, Calendar.JANUARY, 1, 0, 0);

                long from = (_calendar.getTimeInMillis() / 300000) * 300000;
                long to = from + 23 * AggregationType.Hour.milliseconds();
                setData(from, to, new float[]{
                        0.0f, 0.04f, 0.08f,
                        0.12f, 0.16f, 0.2f,
                        0.24f, 0.28f, 0.32f,
                        0.36f, 0.40f, Float.NaN,
                        0.48f, 0.52f, 0.56f,
                        0.6f, 0.64f, 0.68f,
                        0.72f, 0.76f, 0.8f,
                        0.85f, 0.9f, 1.0f
                });
                setFlags(new long[]{
                        from,
                        from + 1800000,
                        from + 3600000,
                        from + 4800000,
                        to,
                });
                _selectedTimestamp = from;
            }
        } finally {
            style.recycle();
        }
    }

    /**
     * Update the anomaly bar drawable to show as "active (color)" or "inactive (B/W)"
     *
     * @param active {@code true} for active, {@code false} otherwise
     */
    private void setActive(boolean active) {
        if (!active) {
            _barDrawable.setColorFilter(_inactiveBarFilter);
        } else {
            _barDrawable.clearColorFilter();
        }
    }

    /**
     * Return the anomaly scores used by this chart
     *
     * @see #setData(long, long, float[])
     * @see #setData(java.util.List)
     */
    public float[] getData() {
        return this._data;
    }

    /**
     * Change the underlying data shown by this chart
     *
     * @param start The timestamp of the first data point
     * @param end   The timestamp of the last data point
     * @param data  The anomaly scores to plot. Use {@link Float#NaN} for missing value
     */
    public void setData(long start, long end, float data[]) {
        if (data == null || data.length == 0) {
            throw new IllegalArgumentException("Expecting at least 1 point");
        }

        _startDate = start;
        _endDate = end;
        _data = Arrays.copyOf(data, data.length);
        _aggregation = AggregationType.fromInterval((end - start) / data.length);

        invalidate();
    }

    /**
     * Convert data value to desired clip level.
     *
     * @param value A value between 0..1
     * @return The clip level (500..10000)
     * @see android.graphics.drawable.Drawable#setLevel(int)
     */
    private int convertToLevel(float value) {
        if (Float.isNaN(value)) {
            return 0;
        }
        int intVal = (int) Math.abs(value * 10000.0f);
        return Math.max(intVal, 500);
    }

    /**
     * Draw anomaly bars values on the given canvas.
     * <ul>
     * <li>The anomaly value is set as the "app:barDrawable" level.
     * <li>Negative anomaly values represent "inactive" bars.
     * </ul>
     *
     * @see #setData(java.util.List)
     * @see #setData(long, long, float[])
     * @see com.numenta.core.R.attr#barDrawable
     */
    private void drawValues(Canvas canvas) {
        if (_data == null || _data.length == 0) {
            return;
        }

        // Update drawable bounds
        _barRect.top = _chartArea.top;
        _barRect.left = _chartArea.left + _barMarginLeft;
        _barRect.bottom = _chartArea.bottom;
        _barRect.right = (int) (_barRect.left + _barWidth - _barMarginRight);
        _barDrawable.setBounds(_barRect);

        _barRect.top = _chartArea.top;
        if (Float.isNaN(_data[0])) {
            _barRect.top = _emptyBarHeight;
            canvas.drawRect(_barRect, _emptyBarPaint);
        } else {
            setActive(_data[0] > 0);
            _barDrawable.setLevel(convertToLevel(_data[0]));
            _barDrawable.draw(canvas);
        }

        // Get data range
        int start = getDataIndex(_startDate);
        int end = getDataIndex(_endDate);
        float left = _barRect.left;
        float right = _barRect.right;

        for (int i = start + 1; i <= end; i++) {
            // Update drawable bounds
            _barRect.top = _chartArea.top;
            left += _barWidth;
            right += _barWidth;
            _barRect.left = (int) left;
            _barRect.right = (int) right - 1;
            _barDrawable.setBounds(_barRect);

            _barRect.top = _chartArea.top;
            if (Float.isNaN(_data[i])) {
                _barRect.top = _emptyBarHeight;
                canvas.drawRect(_barRect, _emptyBarPaint);
            } else {
                setActive(_data[i] > 0);
                _barDrawable.setLevel(convertToLevel(_data[i]));
                _barDrawable.draw(canvas);
            }
        }
    }

    /**
     * Return the index of the data point represented by the given timestamp
     */
    private int getDataIndex(long date) {
        if (_aggregation == null) {
            return -1;
        }
        return (int) ((date - _startDate) / _aggregation.milliseconds());
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        // Draw data series
        canvas.save();
        canvas.clipRect(_chartArea);
        drawValues(canvas);
        canvas.restore();

        // Draw flags
        canvas.save();
        drawFlags(canvas);
        canvas.restore();

        // Draw label
        if (_labelHeight > 0) {
            canvas.save();
            canvas.clipRect(_labelsArea);
            drawLabels(canvas);
            canvas.restore();
        }
    }

    /**
     * Draw annotation flags on the given canvas.
     *
     * @see #setFlags(long[])
     */
    private void drawFlags(Canvas canvas) {
        if (_flags == null || _flags.length == 0) {
            return;
        }
        // On the "DAY" and "WEEK" views add the aggregation time so we can get the end of the bar
        long endTime = _endDate;
        long startOfSelection = _selectedTimestamp;
        long endOfSelection = startOfSelection + _aggregation.milliseconds();
        if (_aggregation != AggregationType.Hour) {
            endTime += _aggregation.milliseconds();
        }
        // Calculate flag position
        int flagHeight = getPaddingTop();
        int maxHeight = _chartArea.top - flagHeight / 2;
        _barRect.top = Math.max(_chartArea.top - flagHeight + 1, maxHeight);
        _barRect.bottom = _chartArea.bottom;

        for (long flagTime : _flags) {
            // Make sure flag time is within range
            if (flagTime < _startDate || flagTime > endTime) {
                continue;
            }
            int idx = getDataIndex(flagTime);
            if (idx >= _data.length) {
                // Out of scope
                continue;
            }
            _barRect.left = (int) (_barWidth / 2 - _barMarginRight + idx * _barWidth);
            _barRect.right = _barRect.left + flagHeight - _barMarginRight;
            _flagDrawable.setBounds(_barRect);
            _flagDrawable.setLevel(convertToLevel(_data[idx]));
            if (flagTime >= startOfSelection && flagTime < endOfSelection) {
                _flagDrawable.setState(SELECTED_STATE_SET);
            } else {
                _flagDrawable.setState(EMPTY_STATE_SET);
            }
            _flagDrawable.draw(canvas);
        }
    }

    /**
     * Format date label based on UI Design.
     * <p>
     * Put the label in the middle of every 3 bars for the Hour and Day views.
     * Put the label in the beginning of the day for the Week view.
     * </p>
     * <p>
     * Put a 'dot' <i>marker</i> under the bar described by the label. The 'dot'
     * style under the label should match the text style. If the text is
     * <b>bold</b> then the <i>marker</i> should also be <b>bold</b>. The Week
     * view does not have a 'dot' <i>marker</i>.
     * </p>
     * <p>
     * The label should be formatted using the following rules:
     * </p>
     * <ul>
     * <li><b>Weekly view:</b> Hide markers, use 'S M T W T F S' as label. Make
     * 'M' always bold. Show label on the first bar of the day.
     * <li><b>Daily view:</b> Use '11a 12a 1p ...' as label. Make '12a' or '1a'
     * or '2a' bold.
     * <li><b>Hourly view:</b> Use '11:55 12:00 1:00 ...' as label. Make '##:00'
     * or '##:05' or '##:10' bold.
     * </ul>
     */
    private void drawLabels(Canvas canvas) {
        if (_aggregation == null) {
            return;
        }
        // canvas.drawRect(_labelsArea, _paint);

        // Get data range
        int start = getDataIndex(_startDate);
        int end = getDataIndex(_endDate);

        int hour, min;
        float x, y;
        boolean hasMarker;
        boolean bold = false;
        Paint paint;
        x = _labelsArea.left + _barMarginLeft + _barWidth / 2;
        long timestamp = _startDate;

        // Handle the different label behavior between the week view and the
        // other views
        if (_aggregation == AggregationType.Week) {
            // Hide circle marker
            hasMarker = false;
            // Include last label
            end++;
        } else {
            // The label is fixed at the middle bar on the day and hour views,
            // Label mid bar only, skip first bar
            x += _barWidth;
            timestamp += _aggregation.milliseconds();
            // Show circle marker
            hasMarker = true;
        }

        // Calculate Y pos
        y = _labelsArea.top - _textPaint.ascent();

        // Leave room for the marker
        if (hasMarker) {
            y += _markerRadius * 3;
        }

        float offset = 0;
        for (int i = start; i < end; i++) {
            _label.setLength(0);
            _calendar.setTimeInMillis(timestamp);
            switch (_aggregation) {
                case HalfDay:
                    // Format as '11:00a 11:30a 12:00p ...'
                    hour = _calendar.get(Calendar.HOUR);
                    _label.append(hour == 0 ? 12 : hour);
                    _label.append(":");
                    min = _calendar.get(Calendar.MINUTE);
                    _label.append(min / 10).append(min % 10);
                    _label.append(_calendar.get(Calendar.AM_PM) == Calendar.AM ? 'a' : 'p');
                    // Next label offset, 4 bars over
                    offset = _barWidth * 4;
                    timestamp += _aggregation.milliseconds() * 4;
                    break;
                case Hour:
                    // Format as '11:55 12:00 12:05 ...'
                    hour = _calendar.get(Calendar.HOUR);
                    _label.append(hour == 0 ? 12 : hour);
                    _label.append(":");
                    min = _calendar.get(Calendar.MINUTE);
                    _label.append(min / 10).append(min % 10);
                    // Make the first label after the hour bold.
                    bold = _calendar.get(Calendar.MINUTE) < 15;
                    // Next label offset, 3 bars over
                    offset = _barWidth * 3;
                    timestamp += _aggregation.milliseconds() * 3;
                    break;
                case Day:
                    // Format as '11a 12p 1p ...'
                    hour = _calendar.get(Calendar.HOUR);
                    _label.append(hour == 0 ? 12 : hour);
                    _label.append(_calendar.get(Calendar.AM_PM) == Calendar.AM ? 'a' : 'p');
                    // Make 'midnight' bold
                    bold = _calendar.get(Calendar.HOUR) < 3;
                    // Next label offset, 3 bars over
                    offset = _barWidth * 3;
                    timestamp += _aggregation.milliseconds() * 3;
                    break;
                case Week:
                    // Format as 'S M T W T F S'
                    // Only show label at the beginning of the day
                    if (_calendar.get(Calendar.HOUR_OF_DAY) < _aggregation.minutes() / 60) {
                        _label.append(WEEKDAYS[_calendar.get(Calendar.DAY_OF_WEEK) - 1]);
                        // Make 'Mondays' bold
                        bold = _calendar.get(Calendar.DAY_OF_WEEK) == Calendar.MONDAY;
                    }
                    // Next label offset
                    offset = _barWidth;
                    timestamp += _aggregation.milliseconds();
                    break;
                default:
                    break;
            }
            paint = bold ? _textPaintBold : _textPaint;
            if (hasMarker) {
                canvas.drawCircle(x - _markerRadius, _labelsArea.top + _markerRadius * 2,
                        _markerRadius, paint);
            }
            canvas.drawText(_label.substring(0), x, y, paint);
            x += offset;
        }
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        _chartArea.set(
                getPaddingLeft(),
                getPaddingTop(),
                getWidth() - getPaddingRight(),
                getHeight() - getPaddingBottom() - _labelHeight);
        _barWidth = (float) _chartArea.width() / _chartTotalBars;
        // Make empty bar to 20%
        _emptyBarHeight = (int) (_chartArea.bottom - _chartArea.height() * 0.2f);
        _labelsArea.set(
                _chartArea.left,
                _chartArea.bottom,
                _chartArea.right,
                getHeight() - getPaddingBottom());
    }

    /**
     * Place a "flag" at the given timestamps. The flag drawable can be changed using
     * "app:flagDrawable" style
     *
     * @param flags The timestamp where to place the "flag"
     * @see com.numenta.core.R.attr#flagDrawable
     */
    public void setFlags(long flags[]) {
        if (flags == null || flags.length == 0) {
            _flags = null;
            invalidate();
            return;
        }
        _flags = Arrays.copyOf(flags, flags.length);
        invalidate();
    }

    /**
     * Change the underlying data show by this chart
     *
     * @param data The data to display as a list of {@link Pair} objects where {@link Pair#first}
     *             contains the timestamp and {@link Pair#second} contains the anomaly score. Use
     *             {@link Float#NaN} for missing anomaly score
     */
    public void setData(List<Pair<Long, Float>> data) {
        if (data == null || data.size() < 2) {
            return;
        }
        _startDate = data.get(0).first;
        _endDate = data.get(data.size() - 1).first;
        _data = new float[data.size()];
        int i = 0;
        for (Pair<Long, Float> pair : data) {
            if (pair.second == null) {
                _data[i++] = Float.NaN;
            } else {
                // Negative values represent probation value
                _data[i++] = (float) DataUtils.logScale(Math.abs(pair.second))
                        * Math.signum(pair.second);
            }
        }
        long secondDate = data.get(1).first;
        _aggregation = AggregationType.fromInterval(secondDate - _startDate);
        invalidate();
    }


    /**
     * Update the selected timestamp
     *
     * @param timestamp The new selected timestamp or -1 for no selection
     */
    public void setSelectedTimestamp(long timestamp) {
        _selectedTimestamp = timestamp;
        invalidate();
    }

    /**
     * Return the timestamp of the last clicked/selected anomaly 'bar' or first date if nothing is
     *
     * @return time in milliseconds since January 1, 1970 00:00:00.0 UTC or -1 for no selection
     */
    public long getSelectedTimestamp() {
        return _selectedTimestamp;
    }

    /**
     * {@inheritDoc}
     *
     * <p><b>NOTE:</b>
     * When the user touches the Anomaly Chart the last timestamp "clicked" is saved for later use.
     * Call {@link #getSelectedTimestamp()} access the last "clicked" timestamp.
     * </p>
     *
     * @see #getSelectedTimestamp()
     */
    @SuppressLint("ClickableViewAccessibility")
    @Override
    public boolean onTouchEvent(@NonNull MotionEvent event) {
        if (_aggregation != null) {
            int selectedBar = (int) (event.getX() / _barWidth);
            _selectedTimestamp = _startDate + selectedBar * _aggregation.milliseconds();
        }
        return super.onTouchEvent(event);
    }
}
