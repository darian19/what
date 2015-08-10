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
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;

import android.animation.AnimatorSet;
import android.animation.ValueAnimator;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Paint.Join;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;
import android.support.annotation.NonNull;
import android.util.AttributeSet;
import android.util.TypedValue;
import android.view.MotionEvent;
import android.view.View;

/**
 * Simple Line chart view used to display the metric raw data.
 * <p>
 * Usage:
 * </p>
 * <ul>
 * <li>Layout:
 *
 * <pre>
 *     &lt;com.numenta.core.ui.chart.LineChartView
 *         xmlns:android="http://schemas.android.com/apk/res/android"
 *         xmlns:app="http://schemas.android.com/apk/res-auto"
 *         android:id="@+id/line_chart_view"
 *         android:layout_width="fill_parent"
 *         app:axisColor="@android:color/dark_grey"
 *         app:axisThickness="3dp"
 *         app:dataColor="android:color/white"
 *         app:dataThickness="2dp"
 *         app:shadowColor="@android:color/black"
 *         app:shadowDx="1"
 *         app:shadowDy="1"
 *         app:shadowRadius="0.6"
 *         app:textColor="@android:color/white"
 *         app:textSize="14sp" /&gt;
 * </pre>
 * <li>Code:
 *
 * <pre>
 * <code>
 *      // Sample Data
 *      float[] result = new float[] {
 *         0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
 *         10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
 *         20, 21, 22, 23
 *      };
 *      // Populate chart
 *      LineChartView chart = (LineChartView) findViewById(R.id.line_chart_view);
 *      chart.setData(result);
 *      chart.invalidate();
 * </code>
 * </pre>
 * <li>Style:
 * <ul>
 * <li>Label Style:<ul>
 * <li>textColor (color)
 * <li>textSize (dimension)
 * <li>shadowDx (float)
 * <li>shadowDy (float)
 * <li>shadowRadius (float)
 * <li>shadowColor (color)
 * </ul>
 * </li>
 * <li>Axis Style:<ul>
 * <li>axisThickness(dimension)
 * <li>axisColor(color)
 * <li>numberOfYLabels(integer)
 * </ul></li>
 * <li>Line Style<ul>
 * <li>dataThickness(dimension)
 * <li>dataColor(color)
 * </ul></li>
 * <li>Anomaly Style<ul>
 * <li>barDrawable(drawable)
 * <li>barMarginLeft
 * <li>barMarginRight
 * </ul></li>
 * </ul>
 */

public class LineChartView extends View {

    private final Rect _contentArea = new Rect();

    private final char[] _chars = new char[100];

    private final int _barMarginLeft;

    private final int _barMarginRight;

    private final int _chartTotalBars;

    private final int _markerWidth;

    private Drawable _barDrawable;

    private Drawable _markerDrawable;

    private float _data[];

    private Pair<Integer, Float>[] _anomalies;

    private int _labelHeight;

    private int _charWidth;

    private float _maxValue;

    private float _minValue;

    private float _points[];

    private float _numberOfYLabels;

    private float _emptyChartTextWidth;

    private float _axisInterval;

    private boolean _isEmpty;

    private boolean _refreshScale = true;

    private String _emptyChartText;

    private Paint _dataPaint;

    private Paint _textPaint;

    private Paint _axisPaint;

    private float _barWidth;

    private final Rect _rect = new Rect();

    private float _pointWidth;

    private int _selection;

    private float _paddingBottom;

    private float _minPadding;

    private OnSelectionChangeListener _onSelectionChangeListener;

    public boolean _floatLabels = false;


    /**
     * Interface definition for a callback to be invoked when
     * an point in this view has been selected.
     */
    public interface OnSelectionChangeListener {

        /**
         * <p>Callback method to be invoked when a new point in this view has been
         * selected. This callback is invoked only when the newly selected
         * point is different from the previously selected point</p>
         *
         * @param view      The clicked {@link LineChartView} view
         * @param selection The selected item
         */
        void onSelectionChange(View view, int selection);
    }

    /**
     * @see android.view.View(Context, AttributeSet)
     */
    public LineChartView(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    /**
     * @see android.view.View(Context, AttributeSet, int)
     */
    public LineChartView(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);

        // Get styleable attributes
        TypedArray style = context.getTheme().obtainStyledAttributes(attrs,
                R.styleable.LineChartView, defStyle, defStyle);
        try {
            int textColor = style.getColor(R.styleable.LineChartView_android_textColor, 0);
            float textSize = style.getDimension(R.styleable.LineChartView_android_textSize, 0);
            float axisThickness = style.getDimension(R.styleable.LineChartView_axisThickness, 0);
            int axisColor = style.getColor(R.styleable.LineChartView_axisColor, 0);
            float dataThickness = style.getDimension(R.styleable.LineChartView_dataThickness, 0);
            int dataColor = style.getColor(R.styleable.LineChartView_dataColor, 0);
            float shadowDx = style.getFloat(R.styleable.LineChartView_android_shadowDx, 0);
            float shadowDy = style.getFloat(R.styleable.LineChartView_android_shadowDy, 0);
            float shadowRadius = style.getFloat(R.styleable.LineChartView_android_shadowRadius, 0);
            int shadowColor = style.getColor(R.styleable.LineChartView_android_shadowColor, 0);
            _numberOfYLabels = style.getInteger(R.styleable.LineChartView_numberOfYLabels, 4);

            // Anomaly bar drawable
            _barDrawable = style.getDrawable(R.styleable.LineChartView_barDrawable);
            if (_barDrawable == null) {
                _barDrawable = context.getResources().getDrawable(R.drawable.anomaly_bar_gradient);
            }
            _barMarginLeft = style
                    .getDimensionPixelOffset(R.styleable.LineChartView_barMarginLeft, 0);
            _barMarginRight = style
                    .getDimensionPixelOffset(R.styleable.LineChartView_barMarginRight, 0);
            _chartTotalBars = YOMPApplication.getTotalBarsOnChart();

            // Setup text style
            _textPaint = new Paint();
            _textPaint.setAntiAlias(true);
            _textPaint.setTextSize(textSize);
            _textPaint.setColor(textColor);
            _textPaint.setShadowLayer(shadowRadius, shadowDx, shadowDy, shadowColor);
            _textPaint.setTextAlign(Paint.Align.LEFT);
            Rect bounds = new Rect();
            _textPaint.getTextBounds("0", 0, 1, bounds);
            _labelHeight = bounds.height();
            _charWidth = (int) _textPaint.measureText("0");
            _emptyChartText = getContext().getString(R.string.chart_empty);
            _emptyChartTextWidth = _textPaint.measureText(_emptyChartText);

            // Setup axis  style
            _axisPaint = new Paint();
            _axisPaint.setStrokeWidth(axisThickness);
            _axisPaint.setColor(axisColor);
            _axisPaint.setStyle(Paint.Style.STROKE);

            // Setup data lines style
            _dataPaint = new Paint();
            _dataPaint.setStrokeWidth(dataThickness);
            _dataPaint.setColor(dataColor);
            _dataPaint.setStrokeJoin(Join.ROUND);
            _dataPaint.setStyle(Paint.Style.STROKE);
            _dataPaint.setAntiAlias(true);
            _markerDrawable = style.getDrawable(R.styleable.LineChartView_marker);
            _markerWidth = (int) (style.getDimension(R.styleable.LineChartView_markerWidth, 3)
                    + 0.5);

            // Padding to the bottom of the chart when min vale > 0. Default to 5dp
            Resources r = getResources();
            _minPadding = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 5,
                    r.getDisplayMetrics());
            // Clear selection
            _selection = -1;
            if (isInEditMode()) {
                // Editor mode, just show some data
                float values[] = new float[288];
                for (int i = 0; i < values.length; i++) {
                    if (i == 100) {
                        values[i] = 1;
                    } else {
                        values[i] = (float) Math.sin((float) (i * 10 / 180f * Math.PI));
                    }
                }
                setData(values);
                // Anomalies

                Pair<Integer, Float>[] anomalies = new Pair[3];
                // Green
                anomalies[0] = new Pair<Integer, Float>(100, 0.1f);
                // Yellow
                anomalies[1] = new Pair<Integer, Float>(120, 0.6f);
                // Green
                anomalies[2] = new Pair<Integer, Float>(140, 1.0f);
                setAnomalies(anomalies);
                // Show selection
                setSelection(100);
            }
        } finally {
            style.recycle();
        }
    }

    /**
     * Set new selection marker
     *
     * @param marker Drawable used to highlight the current selection or {@code null} to hide the
     *               selection
     */
    public void setSelectionMarker(Drawable marker) {
        _markerDrawable = marker;
        invalidate();
    }

    /**
     * Get the data being displayed by this chart
     */
    public float[] getData() {
        return this._data;
    }

    /**
     * Sets the data to display in the chart. It should have at least 2 points
     *
     * @param data An array of floats containing all the data to plot
     */
    public void setData(float data[]) {
        // At least 2 points
        if (data == null || data.length < 2) {
            throw new IllegalArgumentException("Expecting at least 2 points");
        }

        _data = data;
        _points = new float[_data.length * 4];
        _isEmpty = true;
        for (float element : _data) {
            if (!Float.isNaN(element)) {
                _isEmpty = false;
            }
        }
        _pointWidth = (float) _contentArea.width() / _data.length;

        if (_refreshScale) {
            refreshScale();
        }
    }

    /**
     * Set the current selected point.
     *
     * @param point The index of the point to select. Must be between [0..data.length]. Use -1 to
     *              clear the selection
     */
    public void setSelection(int point) {
        if (point != _selection) {
            _selection = _data == null || point > _data.length ? -1 : point;
            invalidate();
            if (_onSelectionChangeListener != null) {
                _onSelectionChangeListener.onSelectionChange(this, _selection);
            }
        }
    }

    /**
     * Get the current selected point.
     *
     * @return The index of the selected point between [0..data.length] or -1 for no selection
     */
    public int getSelection() {
        return _selection;
    }

    /**
     * Register a callback to be invoked when this view selection has changed.
     *
     * @param listener The callback that will run
     */
    public void setOnSelectionChangeListener(OnSelectionChangeListener listener) {
        _onSelectionChangeListener = listener;
    }

    /**
     * Set anomalous data points
     *
     * @param anomalies An array of {@link com.numenta.core.utils.Pair} with anomalous values.
     *                  The first value contains the index to the "rawData" value containing the
     *                  anomaly, the second value contains the anomaly score
     */
    public void setAnomalies(Pair<Integer, Float>[] anomalies) {
        _anomalies = anomalies;
    }

    /**
     * Controls whether or not we should update the min/max based on the data
     *
     * @param refresh {@code true} to always refresh the min/max, {@code false} otherwise
     */
    public void setRefreshScale(boolean refresh) {
        _refreshScale = refresh;
        if (_refreshScale) {
            refreshScale();
        }
    }

    /**
     * Refresh the data scale based on the min/max values from the current data being displayed.
     * Animating the transition between the old and new values.
     */
    private void refreshScale() {
        if (_data == null) {
            return;
        }
        // Get Max/Min values
        float max = Float.MIN_VALUE;
        float min = Float.MAX_VALUE;

        for (float val : _data) {
            // Ignore points with no data
            if (!Float.isNaN(val)) {
                min = Math.min(min, val);
                max = Math.max(max, val);
            }
        }
        // Check if values were changed
        if (min == Float.MAX_VALUE && max == Float.MIN_VALUE) {
            // This usually means we don't have any data to display
            max = min = 0;
        } else if (min == max) {
            // If the data is flat (min == max) move min to X axis
            min = 0;
        }

        float newMax = _maxValue;
        float range = _maxValue - _minValue;
        if (max > _maxValue) {
            newMax = max;
        } else if (max < _minValue + range / 2) {
            // Only shrink the range if max shrank by at least half of the previous range
            newMax = max;
        }

        float newMin = _minValue;
        if (min < _minValue) {
            newMin = min;
        } else if (min > _minValue + range / 2) {
            // Only shrink the range if min grew by at least half of the previous range
            newMin = min;
        }

        // Animate transition between the old and new values
        AnimatorSet animator = new AnimatorSet();
        ValueAnimator minAnimator = ValueAnimator.ofFloat(_minValue, newMin);
        minAnimator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                _minValue = (Float) animation.getAnimatedValue();
                if (_floatLabels) {
                    _axisInterval = (_maxValue - _minValue) / _numberOfYLabels;
                } else{
                    _axisInterval = (int) Math.ceil((_maxValue - _minValue) / _numberOfYLabels);
                }

                // Add padding to the bottom of the chart if min value is greater than 0
                _paddingBottom = _minValue == 0 ? 0 : _minPadding;

                invalidate();
            }
        });
        ValueAnimator maxAnimator = ValueAnimator.ofFloat(_maxValue, newMax);
        maxAnimator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                // Max of y-axis can go no smaller than 2
                _maxValue = Math.max((Float) animation.getAnimatedValue(), 2);
                if (_floatLabels) {
                    _axisInterval = (_maxValue - _minValue) / _numberOfYLabels;
                } else {
                    _axisInterval = (int) Math.ceil((_maxValue - _minValue) / _numberOfYLabels);
                }

                invalidate();
            }
        });
        animator.playTogether(minAnimator, maxAnimator);
        animator.start();
    }

    /**
     * Convert the given value into a valid pixel within the view content area
     *
     * @param value The value to convert
     * @return the pixel value
     */
    private float convertToPixel(float value) {
        if (Float.isNaN(value)) {
            // Put invalid numbers outside the content area
            return _contentArea.bottom + 100;
        }

        // The data is flat
        if (_maxValue - _minValue == 0) {
            return _contentArea.bottom - _paddingBottom;
        }
        return _contentArea.bottom - _paddingBottom
                - (_contentArea.height() - _paddingBottom) * (value - _minValue)
                / (_maxValue - _minValue);
    }

    /**
     * Draws the chart axes.
     */
    private void drawAxes(Canvas canvas) {

        if (_data == null || _data.length == 0) {
            return;
        }

        // Draws axis lines

        // Y Axis
        _points[0] = _contentArea.left + 1;
        _points[1] = 0;
        _points[2] = _contentArea.left + 1;
        _points[3] = _contentArea.bottom - 1;

        // X Axis
        _points[4] = _contentArea.left + 1;
        _points[5] = _contentArea.bottom - 1;
        _points[6] = _contentArea.right - 1;
        _points[7] = _contentArea.bottom - 1;

        canvas.drawLines(_points, 0, 8, _axisPaint);

    }

    /**
     * Draw Y axis labels
     *
     * @param canvas The canvas on which the labels should be drawn
     */
    private void drawYLabels(Canvas canvas) {
        int offset;
        int len;
        float y;
        int decimals;
        if (_axisInterval < 1) {
            decimals = (int) Math.ceil(-Math.log10(_axisInterval));
        } else {
            decimals = 0;
        }
        float labelTop;
        // Check if we have any values to chart.
        if (_isEmpty) {
            canvas.drawText(
                    _emptyChartText,
                    _contentArea.left + _contentArea.width() / 2 - _emptyChartTextWidth / 2,
                    _contentArea.bottom - _contentArea.height() / 2,
                    _textPaint);

        } else {
            for (int i = 0; i <= _numberOfYLabels; i++) {
                y = _minValue + _axisInterval * i;
                len = DataUtils.formatFloat(_chars, y, decimals);
                offset = _chars.length - len;
                labelTop = convertToPixel(y) + _labelHeight / 2;

                if (labelTop > _contentArea.bottom - _paddingBottom / 2) {
                    labelTop = _contentArea.bottom  - _paddingBottom / 2 - _labelHeight / 4;
                }

                canvas.drawText(
                        _chars, offset, len,
                        _contentArea.left + _charWidth / 4,
                        labelTop,
                        _textPaint);
            }
        }
    }

    /**
     * Plot the anomaly values
     *
     * @param canvas The canvas on which the values should be plotted
     */
    private void drawAnomalies(Canvas canvas) {
        if (_data == null || _data.length == 0) {
            return;
        }
        if (_anomalies != null && _anomalies.length > 0) {
            _rect.top = _contentArea.top + _contentArea.height() / 2;
            _rect.bottom = _contentArea.bottom;
            for (Pair<Integer, Float> value : _anomalies) {
                if (value.first >= _data.length) {
                    continue; // Out of range
                }
                _rect.left = (int) (_contentArea.left + _barMarginLeft + _pointWidth * value.first);
                _rect.right = (int) (_rect.left + _barWidth - _barMarginRight);
                _barDrawable.setBounds(_rect);
                _barDrawable.setLevel((int) Math.abs(value.second * 10000.0f));
                _barDrawable.draw(canvas);
            }
        }
    }


    /**
     * Plot the data values
     *
     * @param canvas The canvas on which the values should be plotted
     */
    private void drawValues(Canvas canvas) {
        if (_data == null || _data.length == 0) {
            return;
        }
        float x1, y1, x2, y2, y0;

        // First point (left most). Draw line (0, Y) to (half bar, Y)
        _points[0] = _contentArea.left;
        _points[1] = convertToPixel(_data[0]);
        _points[2] = _contentArea.left + _pointWidth / 2.0f; // Mid point
        _points[3] = _points[1]; // Straight line from the axis

        // From second point to the end
        for (int i = 1; i < _data.length; i++) {
            // Previous point
            x1 = _points[(i - 1) * 4 + 2];
            y1 = _points[(i - 1) * 4 + 3];

            // Current point
            x2 = _contentArea.left + _pointWidth / 2.0f + i * _pointWidth; // Mid point
            y2 = convertToPixel(_data[i]);

            // Handle empty data points
            if (Float.isNaN(_data[i])) {
                // Don't move the Y axis. The line will not be drawn, see #convertToPixel
                y1 = y2;
            } else if (Float.isNaN(_data[i - 1])) {
                // If the previous point was empty, then try to guess where the line should be by
                // putting the Y half way trough the current point and the previous one
                if (i == 1) {
                    // Special case for first data point
                    y0 = y2;
                } else {
                    // Two consecutive missing values
                    if (Float.isNaN(_data[i - 2])) {
                        y0 = y2;
                    } else {
                        // Get previous data point
                        y0 = _points[(i - 2) * 4 + 3];
                    }
                }
                // The new Y value will be half way between the current point and the previous
                y1 = y0 + (y2 - y0) / 2.0f;
            }
            // Draw line from (x1,y1) to (x2,y2)
            _points[i * 4 + 0] = x1;
            _points[i * 4 + 1] = y1;
            _points[i * 4 + 2] = x2;
            _points[i * 4 + 3] = y2;
        }
        canvas.drawLines(_points, 0, _points.length, _dataPaint);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        // Clips the next few drawing operations to the content area
        int clipRestoreCount = canvas.save();
        canvas.clipRect(_contentArea);
        // Draw anomalies
        drawAnomalies(canvas);
        // Draw selection marker
        drawMarker(canvas);
        // Draw data series
        drawValues(canvas);
        // Draws axes
        drawAxes(canvas);
        // Removes clipping rectangle
        canvas.restoreToCount(clipRestoreCount);
        // Draws text labels
        drawYLabels(canvas);
    }

    /**
     * Draw selection marker if necessary.
     * The selection marker will only be drawn if the current data point selection is valid and the
     * <b>marker</b> styleable attribute is set
     *
     * @see com.numenta.core.R.styleable#LineChartView_marker
     */
    private void drawMarker(Canvas canvas) {
        if (_markerDrawable == null || _selection < 0) {
            return;
        }
        _rect.top = _contentArea.top;
        _rect.bottom = _contentArea.bottom;
        if (_selection == 0) {
            _rect.left = _contentArea.left;
        } else {
            _rect.left = Math.round(_contentArea.left + _selection * _pointWidth - _markerWidth / 2f);
        }
        _rect.right = Math.round(_rect.left + _markerWidth);
        _markerDrawable.setBounds(_rect);
        _markerDrawable.draw(canvas);
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        _contentArea.set(
                getPaddingLeft(),
                getPaddingTop(),
                getWidth() - getPaddingRight(),
                getHeight() - getPaddingBottom());
        _barWidth = (float) _contentArea.width() / _chartTotalBars;
        if (_data != null && _data.length > 0) {
            _pointWidth = (float) _contentArea.width() / _data.length;
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    @Override
    public boolean onTouchEvent(@NonNull MotionEvent event) {

        if (_data != null && _data.length > 0) {
            int selection = (int) ((event.getX() - _contentArea.left) / _pointWidth);
            // Make sure selection is within the data boundaries
            if (selection < 0) {
                selection = 0;
            } else if (selection >= _data.length) {
                selection = _data.length - 1;
            }
            setSelection(selection);
        }
        return super.onTouchEvent(event);
    }

    /**
     * Controls whether or not the chart should display labels as float numbers.
     * Default is {@code false}
     *
     * @param value {@code false} to display labels as whole numbers, {@code true} for decimals.
     */
    public void setDisplayWholeNumbers(boolean value) {
        if (_floatLabels != value) {
            _floatLabels = value;
            invalidate();
        }
    }
    /**
     * Sets the label to display when the chart has no data.
     * Default value {@link com.numenta.core.R.string#chart_empty}
     *
     * @param text The new text to use
     */
    public void setEmptyChartText(String text) {
        if (text != null && !text.equals(_emptyChartText)) {
            _emptyChartText = text;
            _emptyChartTextWidth = _textPaint.measureText(_emptyChartText);
            invalidate();
        }
    }
}
