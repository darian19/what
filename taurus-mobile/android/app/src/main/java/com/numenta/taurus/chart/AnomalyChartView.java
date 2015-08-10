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

import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Pair;
import com.numenta.taurus.TaurusApplication;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;
import android.support.annotation.NonNull;
import android.util.AttributeSet;
import android.util.DisplayMetrics;
import android.util.TypedValue;
import android.view.MotionEvent;
import android.view.View;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.ListIterator;


/**
 * Anomaly chart view.
 * <p>
 * Display the values as the anomaly bar chart where each value correspond to
 * the anomaly value (0..1) at the specific time.
 * <p>Usage:</p>
 * <pre>
 *      &lt;com.numenta.taurus.AnomalyChartView
 *         android:id="@+id/line_chart_view"
 *         android:layout_width="fill_parent"
 *         android:layout_height="70dp"
 *         android:background="@android:color/transparent"
 *         android:paddingLeft="15dp"
 *         android:paddingRight="15dp"
 *         app:barDrawable="@drawable/anomaly_bar_gradient"
 *         app:barMarginRight="2sp" /&gt;
 * </pre>
 */
public class AnomalyChartView extends View {

    // Anomaly scores
    private List<Pair<Long, Float>> _data;

    // Styles
    private Drawable _barDrawable;

    private Paint _emptyBarPaint;

    private int _barMarginLeft;

    private int _barMarginRight;

    // Layout
    private final Rect _viewArea = new Rect();

    private final Rect _barRect = new Rect();

    private float _barWidth;

    private int _emptyBarHeight;

    private long _selectedTimestamp = -1;

    private boolean _drawAnomalyOnClosedBar = false;

    public AnomalyChartView(Context context) {
        this(context, null);
    }

    public AnomalyChartView(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public AnomalyChartView(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
        TypedArray style = context.getTheme().obtainStyledAttributes(attrs,
                com.numenta.core.R.styleable.AnomalyChartView, defStyle, defStyle);
        try {
            // Anomaly bar drawable
            _barDrawable = style
                    .getDrawable(com.numenta.core.R.styleable.AnomalyChartView_barDrawable);
            if (_barDrawable == null) {
                _barDrawable = context.getResources()
                        .getDrawable(com.numenta.core.R.drawable.anomaly_bar_gradient);
            }

            _barMarginLeft = style.getDimensionPixelOffset(
                    com.numenta.core.R.styleable.AnomalyChartView_barMarginLeft, 0);
            _barMarginRight = style.getDimensionPixelOffset(
                    com.numenta.core.R.styleable.AnomalyChartView_barMarginRight, 0);

            // Empty bar paint
            DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
            int emptyBarColor = style
                    .getColor(com.numenta.core.R.styleable.AnomalyChartView_emptyBarColor,
                            Color.BLACK);
            _emptyBarPaint = new Paint();
            _emptyBarPaint.setStrokeWidth(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 1,
                    displayMetrics));
            _emptyBarPaint.setColor(emptyBarColor);
            _emptyBarPaint.setStrokeJoin(Paint.Join.ROUND);
            _emptyBarPaint.setStyle(Paint.Style.STROKE);
            _emptyBarPaint.setAntiAlias(true);

            if (isInEditMode()) {
                long from = (System.currentTimeMillis() / 300000) * 300000;
                float[] testData = new float[]{
                        0.0f, 0.04f, Float.NaN,
                        0.08f, 0.12f, 0.16f,
                        0.2f, 0.24f, 0.28f,
                        0.32f, 0.36f, 0.40f,
                        0.48f, 0.56f, 0.6f,
                        0.7f, 0.8f, 0.9f,
                        0.99f, 0.999f, 0.9999f,
                        0.9999f, 0.99995f, 1.0f};
                ArrayList<Pair<Long, Float>> data = new ArrayList<Pair<Long, Float>>(testData.length);
                for (int i = 0; i < testData.length; i++) {
                    if (i == 10) {
                        data.add(new Pair<Long, Float>(null, testData[i]));
                    } else {
                        data.add(new Pair<Long, Float>(from, testData[i]));
                    }
                }
                setData(data);
            }
        } finally {
            style.recycle();
        }
    }

    /**
     * Change the underlying data shown by this chart
     * Use {@link Float#NaN} or {@code nul} on {@link Pair#second} for missing value and
     * {@code null} on {@link Pair#first} to mark collapsed date ranges
     */
    public void setData(List<Pair<Long, Float>> data) {
        if (data == null || data.isEmpty()) {
            return;
        }
        _data = Collections.unmodifiableList(data);
        _barWidth = (float) _viewArea.width() / TaurusApplication.getTotalBarsOnChart();
        invalidate();
    }

    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        canvas.save();
        canvas.clipRect(_viewArea);
        drawValues(canvas);
        canvas.restore();
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        _viewArea.set(
                getPaddingLeft(),
                getPaddingTop(),
                getWidth() - getPaddingRight(),
                getHeight() - getPaddingBottom());
        if (_data != null && !_data.isEmpty()) {
            _barWidth = (float) _viewArea.width() / TaurusApplication.getTotalBarsOnChart();
        }
        // Make empty bar 20% of total height
        _emptyBarHeight = (int) (_viewArea.bottom - _viewArea.height() * 0.2f);
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
     * </ul>
     *
     * @see #setData
     * @see com.numenta.core.R.attr#barDrawable
     */
    private void drawValues(Canvas canvas) {
        if (_data == null || _data.isEmpty()) {
            return;
        }

        // Draw from right to left
        float right = _viewArea.right;
        float left = (int) (right - _barWidth);
        _barRect.top = _viewArea.top;
        _barRect.bottom = _viewArea.bottom;

        ListIterator<Pair<Long, Float>> iterator = _data.listIterator(_data.size());
        while (right >= _viewArea.left && iterator.hasPrevious()) {
            // Add margins
            _barRect.left = (int) left + _barMarginLeft;
            _barRect.right = (int) right - _barMarginRight;

            Pair<Long, Float> value = iterator.previous();
            // Values without date represent folded bars
            if (value.first == null) {
                if (value.second != null && _drawAnomalyOnClosedBar) {
                    // Plot folded bar value
                    _barRect.top = _viewArea.top;
                    _barRect.left = (int) left;
                    _barRect.right = (int) right;
                    _barDrawable.setBounds(_barRect);
                    _barDrawable.setLevel(convertToLevel((float) DataUtils.logScale(value.second)));
                    _barDrawable.draw(canvas);
                }
            } else if (value.second == null || Float.isNaN(value.second)) {
                // Value with date but no value represents "empty"
                _barRect.top = _emptyBarHeight;
                canvas.drawRect(_barRect, _emptyBarPaint);
            } else {
                // Plot value
                _barRect.top = _viewArea.top;
                _barDrawable.setBounds(_barRect);
                _barDrawable.setLevel(convertToLevel((float) DataUtils.logScale(value.second)));
                _barDrawable.draw(canvas);
            }
            // Move to the next bar
            left -= _barWidth;
            right -= _barWidth;
        }
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
        if (_data != null) {
            int selectedBar = (int) (event.getX() / _barWidth);
            if (selectedBar < _data.size()) {
                Pair<Long, Float> selected = _data.get(selectedBar);
                if (selected.first != null) {
                    _selectedTimestamp = selected.first;
                }
            }
        }
        return super.onTouchEvent(event);
    }

}
