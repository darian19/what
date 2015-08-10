
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

import com.YOMPsolutions.YOMP.mobile.instance.InstanceListActivity;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.numenta.core.service.AuthenticationException;
import com.numenta.core.service.YOMPClient;
import com.numenta.core.service.YOMPException;
import com.numenta.core.utils.Log;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.Editor;
import android.os.AsyncTask;
import android.os.AsyncTask.Status;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.preference.PreferenceManager;
import android.text.TextUtils;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.URLUtil;
import android.widget.EditText;
import android.widget.TextView;

import java.io.IOException;
import java.net.MalformedURLException;
import java.util.Locale;


/**
 * Activity which displays a login screen to the user
 */
public class LoginActivity extends Activity {

    private static final String TAG = LoginActivity.class.getCanonicalName();

    /**
     * Keep track of the login task to ensure we can cancel it if requested.
     */
    private UserLoginTask _authTask;

    // Values for server and password at the time of the login attempt.
    private String _password;
    private String _serverUrl;

    // UI references.
    private EditText _passwordView;
    private EditText _serverView;
    private View _loginFormView;
    private View _loginStatusView;
    private TextView _loginStatusMessageView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Check if we have valid credentials
        if (hasCredentials()) {
            openInstanceListActivity();
            return;
        }

        setContentView(R.layout.activity_login);

        // Set up the login form.
        _serverView = (EditText) findViewById(R.id.serverUrl);
        _passwordView = (EditText) findViewById(R.id.password);
        _serverUrl = PreferenceManager.getDefaultSharedPreferences(
                getApplicationContext()).getString(PreferencesConstants.PREF_SERVER_URL, null);
        _serverView.setText(_serverUrl);
        _passwordView
                .setOnEditorActionListener(new TextView.OnEditorActionListener() {
                    @Override
                    public boolean onEditorAction(final TextView textView, final int id,
                            final KeyEvent keyEvent) {
                        if (id == R.id.login || id == EditorInfo.IME_NULL) {
                            attemptLogin();
                            return true;
                        }
                        return false;
                    }
                });

        _loginFormView = findViewById(R.id.login_form);
        _loginStatusView = findViewById(R.id.login_status);
        _loginStatusMessageView = (TextView) findViewById(R.id.login_status_message);

        findViewById(R.id.sign_in_button).setOnClickListener(
                new View.OnClickListener() {
                    @Override
                    public void onClick(final View view) {
                        attemptLogin();
                    }
                });
    }

    @Override
    public void onStart() {
        super.onStart();
        YOMPApplication.setActivityLastUsed();
        YOMPApplication.incrementActivityCount();
    }

    @Override
    public void onStop() {
        super.onStop();
        YOMPApplication.setActivityLastUsed();
        YOMPApplication.decrementActivityCount();
    }

    /**
     * Opens InstanceListActivity and closes LoginActivity
     */
    private void openInstanceListActivity() {
        final Intent myIntent = new Intent(LoginActivity.this, InstanceListActivity.class);
        startActivity(myIntent);
        finish();
        YOMPApplication.refresh();
    }

    /**
     * @return
     */
    private boolean hasCredentials() {
        final SharedPreferences pref = PreferenceManager
                .getDefaultSharedPreferences(getApplicationContext());
        final String server = pref.getString(PreferencesConstants.PREF_SERVER_URL, null);
        final String password = pref.getString(PreferencesConstants.PREF_PASSWORD, null);
        return server != null && password != null;
    }

    /**
     * Attempts to sign in. If there are form errors (invalid server, etc.), the errors are
     * presented and no actual login attempt is made.
     */
    public void attemptLogin() {
        if (_authTask != null && _authTask.getStatus() != Status.FINISHED) {
            return;
        }

        // Reset errors.
        _passwordView.setError(null);
        _serverView.setError(null);

        // Store values at the time of the login attempt.
        _password = _passwordView.getText().toString();
        _serverUrl = _serverView.getText().toString();

        Log.i(TAG, "{TAG:ANDROID.ACTION.LOGIN} Login attempt for server: " + _serverUrl);

        boolean cancel = false;
        View focusView = null;

        // Check for a valid server.
        if (TextUtils.isEmpty(_serverUrl)) {
            _serverView.setError(getString(R.string.error_field_required));
            focusView = _serverView;
            cancel = true;
        } else if (!URLUtil.isHttpsUrl(_serverUrl)) {
            // Try to guess the URL
            final String guessedUrl = URLUtil.guessUrl(_serverUrl);
            if (URLUtil.isValidUrl(guessedUrl)) {
                _serverUrl = guessedUrl.toLowerCase(Locale.US);
                if (URLUtil.isHttpUrl(_serverUrl)) {
                    _serverUrl = _serverUrl.replaceFirst("http", "https");
                }
            } else {
                _serverView.setError(getString(R.string.error_invalid_server_url));
                focusView = _serverView;
                cancel = true;
            }
        }
        if (cancel) {
            Log.i(TAG, "Invalid login info.");
            // There was an error; don't attempt login and focus the first
            // form field with an error.
            if (focusView != null) {
                focusView.requestFocus();
            }
        } else {
            Log.i(TAG,
                    "Valid login info, attempting authentication with server.");
            // Show a progress spinner, and kick off a background task to
            // perform the user login attempt.
            _loginStatusMessageView.setText(R.string.login_progress_signing_in);
            showProgress(true);
            _authTask = new UserLoginTask();
            _authTask.execute((Void) null);
        }
    }

    /**
     * Shows the progress UI and hides the login form.
     */
    private void showProgress(final boolean show) {
        final int shortAnimTime = getResources().getInteger(
                android.R.integer.config_shortAnimTime);

        _loginStatusView.setVisibility(View.VISIBLE);
        _loginStatusView.animate().setDuration(shortAnimTime)
                .alpha(show ? 1 : 0).setListener(new AnimatorListenerAdapter() {
                    @Override
                    public void onAnimationEnd(final Animator animation) {
                        _loginStatusView.setVisibility(show ? View.VISIBLE
                                : View.GONE);
                    }
                });

        _loginFormView.setVisibility(View.VISIBLE);
        _loginFormView.animate().setDuration(shortAnimTime).alpha(show ? 0 : 1)
                .setListener(new AnimatorListenerAdapter() {
                    @Override
                    public void onAnimationEnd(final Animator animation) {
                        _loginFormView.setVisibility(show ? View.GONE
                                : View.VISIBLE);
                    }
                });
    }

    /**
     * Represents an asynchronous login/registration task used to authenticate the user.
     */
    public class UserLoginTask extends AsyncTask<Void, Void, Boolean> {
        private String _errorMessage;

        @Override
        protected Boolean doInBackground(final Void... params) {
            try {
                final YOMPClient YOMP = YOMPApplication.getInstance().connectToYOMP(_serverUrl,
                        _password);
                if (!YOMP.isOnline()) {
                    _errorMessage = getString(R.string.error_server_unavailable);
                    new Handler(Looper.getMainLooper()).post(new Runnable() {
                        @Override
                        public void run() {
                            _serverView.setError(getString(R.string.error_server_unavailable));
                            _serverView.requestFocus();
                        }
                    });
                    return false;
                }
                try {
                    YOMP.login();
                } catch (AuthenticationException e) {
                    _errorMessage = getString(R.string.error_login_failed_message);
                    new Handler(Looper.getMainLooper()).post(new Runnable() {
                        @Override
                        public void run() {
                            _passwordView.setError(_errorMessage);
                            _passwordView.setText(null);
                            _passwordView.requestFocus();
                        }
                    });
                    return false;
                } catch (IOException e) {
                    Log.e(TAG, "Failed to connect to YOMP", e);
                }
                return true;
            } catch (MalformedURLException e) {
                Log.e(TAG, "Failed to connect to YOMP", e);
            } catch (YOMPException e) {
                Log.e(TAG, "Failed to connect to YOMP", e);
            }
            return false;
        }

        @Override
        protected void onPostExecute(final Boolean success) {
            showProgress(false);

            if (success) {
                Log.i(TAG, "Server authentication successful.");
                // Update preferences and start main activity
                final Editor prefs = PreferenceManager.getDefaultSharedPreferences(
                        getApplicationContext()).edit();
                prefs.putString(PreferencesConstants.PREF_SERVER_URL, _serverUrl);
                prefs.putString(PreferencesConstants.PREF_PASSWORD, _password);
                prefs.apply();
                openInstanceListActivity();
            } else {
                Log.i(TAG, "Server authentication failed. "
                        + R.string.error_login_failed_title + ": "
                        + R.string.error_login_failed_message);
                if (!isFinishing()) {
                    new AlertDialog.Builder(LoginActivity.this)
                            .setTitle(getString(R.string.error_login_failed_title))
                            .setMessage(_errorMessage).setCancelable(true).show()
                            .setCanceledOnTouchOutside(true);
                }
            }
        }

        @Override
        protected void onCancelled() {
            showProgress(false);
        }
    }
}
