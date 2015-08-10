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

import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.OnSharedPreferenceChangeListener;
import android.os.Bundle;
import android.preference.EditTextPreference;
import android.preference.ListPreference;
import android.preference.Preference;
import android.preference.Preference.OnPreferenceChangeListener;
import android.preference.PreferenceActivity;
import android.preference.PreferenceFragment;
import android.preference.PreferenceManager;
import android.webkit.URLUtil;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.tutorial.TutorialActivity;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.numenta.core.utils.Log;

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
        YOMPApplication.setActivityLastUsed();
        YOMPApplication.decrementActivityCount();
    }

    @Override
    protected void onStart() {
        super.onStart();
        YOMPApplication.incrementActivityCount();
        YOMPApplication.setActivityLastUsed();
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
        updatePreferenceSummary(PreferencesConstants.PREF_SERVER_VERSION);

        // Validate Server URL
        EditTextPreference server = (EditTextPreference) getPreferenceScreen()
                .findPreference(PreferencesConstants.PREF_SERVER_URL);
        if (server != null) {
            server.setOnPreferenceChangeListener(new OnPreferenceChangeListener() {
                @Override
                public boolean onPreferenceChange(Preference preference, Object newValue) {
                    String url = (String) newValue;
                    if (URLUtil.isHttpsUrl(url)) {
                        return true;
                    }
                    AlertDialog.Builder builder = new AlertDialog.Builder(SettingsActivity.this);
                    builder.setMessage(getString(R.string.error_invalid_server_url));
                    builder.setTitle(getString(R.string.title_error_dialog));
                    builder.setPositiveButton(android.R.string.ok, null);
                    builder.show();
                    return false;
                }
            });
        }

        // Validate notification email
        EditTextPreference emailPref = (EditTextPreference) getPreferenceScreen()
                .findPreference(PreferencesConstants.PREF_NOTIFICATIONS_EMAIL);
        if (emailPref != null) {
            emailPref.setOnPreferenceChangeListener(new OnPreferenceChangeListener() {
                @Override
                public boolean onPreferenceChange(Preference preference, Object newValue) {
                    String email = (String) newValue;
                    if (android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                        return true;
                    }
                    AlertDialog.Builder builder = new AlertDialog.Builder(SettingsActivity.this);
                    builder.setMessage(getString(R.string.error_invalid_email));
                    builder.setTitle(getString(R.string.title_error_dialog));
                    builder.setPositiveButton(android.R.string.ok, null);
                    builder.show();
                    return false;
                }
            });
        }


        Preference button = findPreference(PreferencesConstants.PREF_SHOW_TUTORIAL);
        button.setOnPreferenceClickListener(new Preference.OnPreferenceClickListener() {
            @Override
            public boolean onPreferenceClick(Preference preference) {
                Log.i(TAG, "{TAG:ANDROID.SETTINGS} Show tutorial selected.");
                Intent intent = new Intent(getApplicationContext(), TutorialActivity.class);
                startActivity(intent);
                finish();
                return true;
            }
        });
    }

    /*
     * (non-Javadoc)
     * @see android.app.Activity#onResume()
     */
    @Override
    protected void onResume() {
        super.onResume();
        // Set up a listener whenever a key changes
        getPreferenceScreen().getSharedPreferences()
                .registerOnSharedPreferenceChangeListener(this);
    }

    /*
     * (non-Javadoc)
     * @see android.app.Activity#onPause()
     */
    @Override
    protected void onPause() {
        super.onPause();
        // Unregister the listener whenever a key changes
        getPreferenceScreen().getSharedPreferences()
                .unregisterOnSharedPreferenceChangeListener(this);
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
            preference.setSummary(YOMPApplication.getInstance().getServerVersion() + " : "
                    + YOMPApplication.getVersion());
        } else if (preference instanceof EditTextPreference) {
            EditTextPreference pref = (EditTextPreference) preference;
            String text = pref.getText();
            Log.i(TAG, "{TAG:ANDROID.ACTION.SETTINGS.CHANGE} " + key + ": " + text);
            if (text != null && text.trim().length() > 0) {
                pref.setSummary(text);
            } else {
                pref.setSummary(null);
            }
        } else if (preference instanceof ListPreference) {
            ListPreference pref = (ListPreference) preference;
            String value = pref.getValue();
            Log.i(TAG, "{TAG:ANDROID.ACTION.SETTINGS.CHANGE} " + key + ": " + value);
            if (value != null && value.trim().length() > 0) {
                pref.setSummary(pref.getEntry());
            } else {
                pref.setSummary(null);
            }
        }
    }
}
