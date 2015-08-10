
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

package com.YOMPsolutions.YOMP.mobile.preference;

import android.content.Context;
import android.content.res.TypedArray;
import android.preference.Preference;
import android.util.AttributeSet;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.SeekBar.OnSeekBarChangeListener;
import android.widget.TextView;

import com.YOMPsolutions.YOMP.mobile.R;

public class SliderPreference extends Preference implements OnSeekBarChangeListener {

    private final String TAG = getClass().getName();

    private static final String ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android";
    // TODO: Fixup APPLICATION_NAMESPACE re: TAUR-1044
    private static final String APPLICATION_NAMESPACE = "http://YOMPsolutions.com";
    private static final int DEFAULT_VALUE = 50;

    private int maxValue = 100;
    private int minValue = 0;
    private int interval = 1;
    private int currentValue;
    private String unitPrefix = "";
    private String unitPostfix = "";
    private SeekBar slider;

    private TextView statusText;

    /**
     * Contains a slider with adjustable min, max, and interval values. Also
     * allows units, unit prefixes, and unit postfixes to be attached to the
     * value text display.
     *
     * @param context
     * @param attrs
     */
    public SliderPreference(Context context, AttributeSet attrs) {
        super(context, attrs);
        initializeAttributes(context, attrs);
    }

    public SliderPreference(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
        initializeAttributes(context, attrs);
    }

    private void initializeAttributes(Context context, AttributeSet attrs) {
        setValuesFromXml(attrs);
        slider = new SeekBar(context, attrs);
        slider.setMax(maxValue - minValue);
        slider.setOnSeekBarChangeListener(this);

        setWidgetLayoutResource(R.layout.slider_preference);
    }

    private void setValuesFromXml(AttributeSet attrs) {
        maxValue = attrs.getAttributeIntValue(ANDROID_NAMESPACE, "max", 100);
        minValue = attrs.getAttributeIntValue(APPLICATION_NAMESPACE, "min", 0);
        unitPrefix = getAttributeStringValue(attrs, APPLICATION_NAMESPACE, "unitPrefix", "");
        String units = getAttributeStringValue(attrs, APPLICATION_NAMESPACE, "units", "");
        unitPostfix = getAttributeStringValue(attrs, APPLICATION_NAMESPACE, "unitPostfix", units);

        try {
            String newInterval = attrs.getAttributeValue(APPLICATION_NAMESPACE, "interval");
            if (newInterval != null) {
                interval = Integer.parseInt(newInterval);
            }
        } catch (Exception e) {
            Log.e(TAG, "Invalid interval value", e);
        }
    }

    private String getAttributeStringValue(AttributeSet attrs, String namespace, String name,
            String defaultValue) {
        String value = attrs.getAttributeValue(namespace, name);
        if (value == null) {
            value = defaultValue;
        }
        return value;
    }

    @Override
    protected View onCreateView(ViewGroup parent) {
        View view = super.onCreateView(parent);
        // The basic preference layout puts the widget frame to the right of the
        // title and summary,
        // so we need to change it a bit - the slider should be under them.
        LinearLayout layout = (LinearLayout) view;
        layout.setOrientation(LinearLayout.VERTICAL);
        return view;
    }

    @Override
    public void onBindView(View view) {
        super.onBindView(view);

        try {
            // move our slider to the new view we've been given
            ViewParent oldContainer = slider.getParent();
            ViewGroup newContainer = (ViewGroup) view
                    .findViewById(R.id.sliderPreferenceSliderContainer);

            if (oldContainer != newContainer) {
                // remove the slider from the old view
                if (oldContainer != null) {
                    ((ViewGroup) oldContainer).removeView(slider);
                }
                // remove the existing slider (there may not be one) and add
                // ours
                newContainer.removeAllViews();
                newContainer.addView(slider,
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT);
            }
        } catch (Exception ex) {
            Log.e(TAG, "Error binding view: " + ex.toString());
        }

        // If parent is disabled, disable the slider.
        if (view != null && !view.isEnabled()) {
            slider.setEnabled(false);
        }

        updateView(view);
    }

    /**
     * Update a SeekBarPreference view with our current state
     *
     * @param view
     */
    protected void updateView(View view) {
        try {
            statusText = (TextView) view.findViewById(R.id.sliderPreferenceValue);

            statusText.setText(String.valueOf(currentValue));
            statusText.setMinimumWidth(30);

            slider.setProgress(currentValue - minValue);

            TextView unitPostfixView = (TextView) view
                    .findViewById(R.id.sliderPreferenceUnitPostfix);
            unitPostfixView.setText(unitPostfix);

            TextView unitPrefixView = (TextView) view.findViewById(R.id.sliderPreferenceUnitPrefix);
            unitPrefixView.setText(unitPrefix);

        } catch (Exception e) {
            Log.e(TAG, "Error updating seek bar preference", e);
        }
    }

    @Override
    public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
        int newValue = progress + minValue;

        if (newValue > maxValue) {
            newValue = maxValue;
        } else if (newValue < minValue) {
            newValue = minValue;
        } else if (interval != 1 && newValue % interval != 0) {
            newValue = Math.round((float) newValue / interval) * interval;
        }

        // change rejected, revert to the previous value
        if (!callChangeListener(newValue)) {
            seekBar.setProgress(currentValue - minValue);
            return;
        }

        // change accepted, store it
        currentValue = newValue;
        statusText.setText(String.valueOf(newValue));
        persistInt(newValue);

    }

    @Override
    public void onStartTrackingTouch(SeekBar seekBar) {
        // Do nothing
    }

    @Override
    public void onStopTrackingTouch(SeekBar seekBar) {
        notifyChanged();
    }

    @Override
    protected Object onGetDefaultValue(TypedArray ta, int index) {
        return ta.getInt(index, DEFAULT_VALUE);
    }

    @Override
    protected void onSetInitialValue(boolean restoreValue, Object defaultValue) {
        if (restoreValue) {
            currentValue = getPersistedInt(currentValue);
        } else {
            int temp = 0;
            try {
                temp = (Integer) defaultValue;
            } catch (Exception ex) {
                Log.e(TAG, "Invalid default value: " + defaultValue.toString());
            }
            persistInt(temp);
            currentValue = temp;
        }
    }

    /**
     * Make sure that the slider is disabled if the preference is disabled
     */
    @Override
    public void setEnabled(boolean enabled) {
        super.setEnabled(enabled);
        slider.setEnabled(enabled);
    }

    @Override
    public void onDependencyChanged(Preference dependency, boolean disableDependent) {
        super.onDependencyChanged(dependency, disableDependent);
        // Disable movement of seek bar when dependency is false
        if (slider != null) {
            slider.setEnabled(!disableDependent);
        }
    }

}
