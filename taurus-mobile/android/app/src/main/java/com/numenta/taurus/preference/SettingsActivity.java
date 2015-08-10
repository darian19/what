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

package com.numenta.taurus.preference;

import com.numenta.core.preference.PreferencesConstants;
import com.numenta.core.utils.Log;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.tutorial.TutorialActivity;

import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.OnSharedPreferenceChangeListener;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Bundle;
import android.preference.EditTextPreference;
import android.preference.ListPreference;
import android.preference.Preference;
import android.preference.PreferenceActivity;
import android.preference.PreferenceFragment;
import android.preference.PreferenceManager;
import android.preference.RingtonePreference;
import android.provider.Settings;

/**
 * Application Settings Activity. This activity is used to configure all user
 * settings
 *
 * @deprecated TODO: Convert to new {@link PreferenceFragment} format
 */
@Deprecated
public class SettingsActivity extends PreferenceActivity implements
        OnSharedPreferenceChangeListener {

    /* (non-Javadoc)
     * @see android.preference.PreferenceActivity#onStop()
     */
    @Override
    protected void onStop() {
        super.onStop();
        TaurusApplication.setActivityLastUsed();
        TaurusApplication.decrementActivityCount();
        // Unregister the listener whenever a key changes
        getPreferenceScreen().getSharedPreferences()
                .unregisterOnSharedPreferenceChangeListener(this);
    }

    @Override
    protected void onStart() {
        super.onStart();
        TaurusApplication.incrementActivityCount();
        TaurusApplication.setActivityLastUsed();
        // Set up a listener whenever a key changes
        getPreferenceScreen().getSharedPreferences()
                .registerOnSharedPreferenceChangeListener(this);
    }

    private static final String TAG = SettingsActivity.class.getCanonicalName();

    /*
     * (non-Javadoc)
     * @see android.preference.PreferenceActivity#onCreate(android.os.Bundle)
     */
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Load the preferences from an XML resource
        addPreferencesFromResource(R.xml.preferences);
        PreferenceManager.setDefaultValues(this, R.xml.preferences, false);
        SharedPreferences prefs = getPreferenceScreen().getSharedPreferences();
        for (String key : prefs.getAll().keySet()) {
            updatePreferenceSummary(key);
        }
        updatePreferenceSummary(PreferencesConstants.PREF_VERSION);
    }

    /*
     * (non-Javadoc)
     * @see android.content.SharedPreferences.OnSharedPreferenceChangeListener#
     * onSharedPreferenceChanged(android.content.SharedPreferences,
     * java.lang.String)
     */
    @Override
    public void onSharedPreferenceChanged(SharedPreferences sharedPreferences,
            String key) {
        updatePreferenceSummary(key);
    }

    /**
     * Update preference Summary field with current value
     *
     * @param key - Preference Key
     */
    private void updatePreferenceSummary(String key) {
        Preference preference = findPreference(key);
        // Update preferences Summary with current value
        if (key.equals(PreferencesConstants.PREF_VERSION)) {
            preference.setSummary(TaurusApplication.getVersion().toString());
        } else if (preference instanceof EditTextPreference) {
            EditTextPreference pref = (EditTextPreference) preference;
            String text = pref.getText();
            Log.i(TAG, "{TAG:ANDROID.ACTION.SETTINGS.CHANGE} " + key + ": " + text);
            if (text != null && !text.trim().isEmpty()) {
                pref.setSummary(text);
            } else {
                pref.setSummary(null);
            }
        } else if (preference instanceof ListPreference) {
            ListPreference pref = (ListPreference) preference;
            String value = pref.getValue();
            Log.i(TAG, "{TAG:ANDROID.ACTION.SETTINGS.CHANGE} " + key + ": " + value);
            if (value != null && !value.trim().isEmpty()) {
                pref.setSummary(pref.getEntry());
            } else {
                pref.setSummary(null);
            }
        } else if (preference instanceof RingtonePreference) {
            // Get Ringtone name
            SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(this);
            String ringUrlStr = prefs.getString(preference.getKey(), null);
            String name = null;
            if (ringUrlStr != null && !ringUrlStr.trim().isEmpty()) {
                Uri ringtoneUri = Uri.parse(ringUrlStr);
                Ringtone ringtone = RingtoneManager.getRingtone(this, ringtoneUri);
                name = ringtone.getTitle(this);
            }
            preference.setSummary(name);
        }
    }
}
