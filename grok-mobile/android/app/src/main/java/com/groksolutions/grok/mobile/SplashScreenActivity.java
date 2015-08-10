
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

package com.YOMPsolutions.YOMP.mobile;

import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences.Editor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.preference.PreferenceManager;
import android.webkit.URLUtil;

import java.util.Locale;


public class SplashScreenActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Handle "https://m.numenta.com/YOMP" URL
        Intent intent = getIntent();
        if (intent != null && intent.getAction().equals(Intent.ACTION_VIEW)) {
            handleYOMPUrl(intent.getData());
        }

        setContentView(R.layout.activity_splash_screen);
        new Handler().postDelayed(new Runnable() {

            @Override
            public void run() {
                Intent myIntent = new Intent(SplashScreenActivity.this,
                        LoginActivity.class);
                startActivity(myIntent);
                finish();
                overridePendingTransition(0, R.anim.fadeout_animation);
            }
        }, 1000);
    }

    /**
     * Handles "https://m.numenta.com/YOMP" URLs.
     * <p>
     * The URL format is:
     * <ol>
     * <li><b>/login</b> : Used to configure login parameters from a URL.
     *
     *      <br><b>Arguments:</b>
     *      <ul>
     *      <li><b>serverUrl</b>: YOMP serer host name or URL
     *      <li><b>apiKey</b>: YOMP API key
     *      </ul>
     *
     *      For example: <code>https://m.numenta.com/YOMP/login?serverUrl=hostname&apiKey=PASSW</code>
     * </ol>
     * </p>
     * @param YOMPUrl
     */
    private void handleYOMPUrl(Uri YOMPUrl) {
        if (YOMPUrl == null) {
            return;
        }
        String host = YOMPUrl.getHost();
        if (host == null || !host.equalsIgnoreCase("m.numenta.com")) {
            return;
        }
        /*
         * https://m.numenta.com/YOMP/login?serverUrl=hostname&apiKey=PASSW
         */
        String path = YOMPUrl.getPath();
        if (path != null && path.equalsIgnoreCase("/YOMP/login")) {
            String serverUrl = YOMPUrl.getQueryParameter("serverUrl");
            String apiKey = YOMPUrl.getQueryParameter("apiKey");
            if (!URLUtil.isHttpsUrl(serverUrl)) {
                // Try to guess the URL
                final String guessedUrl = URLUtil.guessUrl(serverUrl);
                if (URLUtil.isValidUrl(guessedUrl)) {
                    serverUrl = guessedUrl.toLowerCase(Locale.US);
                    if (URLUtil.isHttpUrl(serverUrl)) {
                        serverUrl = serverUrl.replaceFirst("http", "https");
                    }
                } else {
                    // Invalid URL
                    return;
                }
            }
            // Update preferences and start main activity
            final Editor prefs = PreferenceManager.getDefaultSharedPreferences(
                    getApplicationContext()).edit();
            prefs.putString(PreferencesConstants.PREF_SERVER_URL, serverUrl);
            prefs.putString(PreferencesConstants.PREF_PASSWORD, apiKey);
            prefs.apply();
        }
    }
}
