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

package com.numenta.taurus;

import com.numenta.core.service.DataSyncService;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;
import com.numenta.core.utils.NetUtils;
import com.numenta.taurus.dialog.RefreshDialogFragment;
import com.numenta.taurus.preference.AboutActivity;
import com.numenta.taurus.preference.SettingsActivity;
import com.numenta.taurus.tutorial.TutorialActivity;

import android.annotation.SuppressLint;
import android.app.ActionBar;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.support.v4.app.NavUtils;
import android.support.v4.content.LocalBroadcastManager;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Toast;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ConcurrentLinkedQueue;

import static com.numenta.core.preference.PreferencesConstants.PREF_LAST_CONNECTED_TIME;

/**
 * <p>
 * Base activity showing a common menu and handle all other common functions of a typical activity.
 * All other activities must inherit from this class.
 * This activity will handle the following:
 * <ul>
 * <li>Options Menu (<i>"Refresh", "Settings", "Support", ...</i>)</li>
 * <li>Google Analytics</li>
 * </ul>
 * </p>
 */
public abstract class TaurusBaseActivity extends Activity {

    public static final int RESULT_SETTINGS = 1;

    protected final String TAG = getClass().getCanonicalName();

    private final BroadcastReceiver _isRefreshingReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            updateRefresh();
        }
    };

    private MenuItem _refresh;

    private View _refreshView;

    private ConcurrentLinkedQueue<AsyncTask> _taskList;

    @SuppressLint("AlwaysShowAction")
    private void updateRefresh() {
        if (_refresh != null) {
            if (TaurusApplication.isRefreshing()) {
                _refresh.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
                _refresh.setActionView(_refreshView);

                // Calculate the interval since last connection to the server
                final SharedPreferences pref = PreferenceManager
                        .getDefaultSharedPreferences(getApplicationContext());
                final long now = System.currentTimeMillis();
                final long lastConnected = pref.getLong(PREF_LAST_CONNECTED_TIME, now);
                final long interval = now - lastConnected;

                // Notify the user if the last time we connected was more than one hour ago
                if (interval > DataUtils.MILLIS_PER_HOUR) {
                    final long hour = interval / DataUtils.MILLIS_PER_HOUR;
                    final long minutes = (interval % DataUtils.MILLIS_PER_HOUR)
                            / DataUtils.MILLIS_PER_MINUTE;
                    if (hour > 0) {
                        String title;
                        // Format message: "X hours ago" or "X hours and Y minutes ago"
                        if (minutes > 0) {
                            title = getApplicationContext().getString(
                                    R.string.loading_metrics_title_hours_minutes, hour, minutes);
                        } else {
                            title = getApplicationContext().getString(
                                    R.string.loading_metrics_title_hours, hour);
                        }
                        Toast.makeText(this, title, Toast.LENGTH_LONG).show();
                    }
                }
            } else {
                // Check if we have an error message
                String refreshError = TaurusApplication.getLastError();
                if (refreshError == null) {
                    _refresh.setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
                    // Restore refresh icon
                    _refresh.setIcon(R.drawable.ic_action_refresh);
                } else {
                    _refresh.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
                    // Show error icon
                    _refresh.setIcon(R.drawable.ic_action_connection_error);
                }
                _refresh.setActionView(null);
            }
        }
    }

    @SuppressLint("InflateParams")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.i(TAG, "{TAG:ANDROID.APP.CREATE}");
        final ActionBar actionBar = getActionBar();
        if (actionBar != null) {
            actionBar.setDisplayShowTitleEnabled(false);
        }
        LayoutInflater inflater = getLayoutInflater();

        _refreshView = inflater.inflate(R.layout.actionbar_indeterminate_progress, null);

    }

    @Override
    public void onStart() {
        super.onStart();
        TaurusApplication.setActivityLastUsed();
        TaurusApplication.incrementActivityCount();
    }

    @Override
    public void onStop() {
        super.onStop();
        TaurusApplication.setActivityLastUsed();
        TaurusApplication.decrementActivityCount();
    }

    @Override
    protected void onPostCreate(Bundle savedInstanceState) {
        super.onPostCreate(savedInstanceState);
        validateUserSettings();
    }

    @Override
    protected void onResume() {
        Log.i(TAG, "{TAG:ANDROID.APP.RESUME}");
        super.onResume();
        LocalBroadcastManager.getInstance(this).registerReceiver(
                _isRefreshingReceiver,
                new IntentFilter(DataSyncService.REFRESH_STATE_EVENT));

        updateRefresh();
    }

    @Override
    protected void onPause() {
        Log.i(TAG, "{TAG:ANDROID.APP.PAUSE}");
        super.onPause();
        LocalBroadcastManager.getInstance(this).unregisterReceiver(
                _isRefreshingReceiver);

        // Cancel pending tasks
        if (_taskList != null) {
            AsyncTask task;
            while ((task = _taskList.poll()) != null) {
                if (isFinishing()) {
                    task.cancel(true);
                }
            }
        }
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.main, menu);

        _refresh = menu.findItem(R.id.menu_refresh);
        updateRefresh();
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.menu_settings:
                // Open the User Settings Screen
                Intent settings = new Intent(this, SettingsActivity.class);
                startActivityForResult(settings, RESULT_SETTINGS);
                break;
            case R.id.menu_about:
                // Open the About Screen
                Intent about = new Intent(this, AboutActivity.class);
                startActivity(about);
                break;

            case R.id.menu_tutorial:
                Intent intent = new Intent(getApplicationContext(), TutorialActivity.class);
                startActivity(intent);
                break;

            case R.id.menu_feedback:
                // Take a screenshot and share

                // Pop up a user feedback email view
                AlertDialog.Builder builder = new AlertDialog.Builder(this);
                builder.setMessage(getString(R.string.feedback_dialog_message));
                builder.setTitle(getString(R.string.title_feedback_dialog));
                builder.setPositiveButton(android.R.string.ok,
                        new DialogInterface.OnClickListener() {

                            @Override
                            public void onClick(DialogInterface dialog, int which) {
                                StringBuffer sb = new StringBuffer();
                                sb.append("App Id:").append(BuildConfig.APPLICATION_ID).append("\n");
                                sb.append("Version Name:").append(BuildConfig.VERSION_NAME).append("\n");
                                sb.append("Version Code:").append(BuildConfig.VERSION_CODE).append("\n");
                                TaurusBaseActivity.this.emailFeedback(sb);
                            }
                        }
                );

                builder.setNegativeButton(android.R.string.cancel, null);
                builder.show();
                break;
            case R.id.menu_share:
                // Take a screenshot and share
                this.shareScreenCapture();
                break;
            case R.id.menu_refresh:
                // Refresh
                TaurusApplication.refresh();
                // Show error dialog
                String refreshError = TaurusApplication.getLastError();
                if (refreshError != null) {
                    RefreshDialogFragment.show(refreshError, getFragmentManager());
                }
                break;
            case android.R.id.home:
                NavUtils.navigateUpFromSameTask(this);
                return true;
            default:
                break;
        }
        return super.onOptionsItemSelected(item);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        switch (requestCode) {
            case RESULT_SETTINGS:
                validateUserSettings();
                break;
            default:
                break;
        }
    }

    private void validateUserSettings() {
        // TODO Validate User Settings, for now just validate server connection
        TaurusApplication.checkConnection();
    }

    /**
     * Capture the screen and return the URI of the image
     */
    private Uri takeScreenCapture(boolean isRetryOk) {
        String fileName = "YOMP_" + new SimpleDateFormat(
                "yyyyMMddhhmm'.jpg'",
                Locale.US).format(new Date());

        File screenShot = new File(getCacheDir(), fileName);

        // create bitmap screen capture
        View v1 = getWindow().getDecorView().getRootView();
        v1.setDrawingCacheEnabled(true);
        v1.invalidate();
        v1.buildDrawingCache(true);
        Bitmap bitmap = null;
        FileOutputStream fOut = null;

        try {
            bitmap = Bitmap.createBitmap(v1.getDrawingCache(true));
            v1.setDrawingCacheEnabled(false);
            fOut = new FileOutputStream(screenShot);
            bitmap.compress(Bitmap.CompressFormat.JPEG, 75, fOut);

        } catch (FileNotFoundException e) {
            Log.e(TAG, "Screen shot file not found", e);
        } catch (OutOfMemoryError e) {
            Log.e(TAG, "Out of Memory Error creating screenshot", e);
            // retry one time on out of memory
            if (isRetryOk) {
                return takeScreenCapture(false);
            }
            return writeTextFileToSend("screenshot.txt",
                    "Out of Memory: Failed to generate screenshot");
        } finally {
            // recycle the bitmap on the heap to free up space and help prevent
            // out of memory errors
            if (bitmap != null) {
                bitmap.recycle();
                //noinspection UnusedAssignment
                bitmap = null;
            }
            System.gc();
            try {
                if (fOut != null) {
                    fOut.flush();
                    fOut.close();
                }
            } catch (IOException e) {
                Log.e(TAG, "Error saving the screenshot file", e);
            }
        }

        return Uri.parse("content://" + getApplication().getPackageName() + "/" + fileName);
    }

    private Uri writeTextFileToSend(String fileName, String message) {
        File textFile = new File(getCacheDir(), fileName);
        FileWriter writer = null;

        try {
            writer = new FileWriter(textFile);
            writer.write(message);
        } catch (FileNotFoundException e) {
            Log.e(TAG, "Text file not found", e);
        } catch (IOException e) {
            Log.e(TAG, "I/O Error accessing text file", e);
        } finally {
            try {
                if (writer != null) {
                    writer.flush();
                    writer.close();
                }
            } catch (IOException e) {
                Log.e(TAG, "Error saving the file", e);
            }
        }

        return Uri.parse("content://" + getApplication().getPackageName() + "/" + fileName);
    }

    /**
     * Capture the screen and return the URI of the image
     */
    private Uri writeTextFileToSend(String message) {
        return writeTextFileToSend("report.txt", message);
    }

    /**
     * Share a screen capture via email or another provider
     */
    private void shareScreenCapture() {
        Intent shareIntent = new Intent(Intent.ACTION_SEND);
        Uri uri = this.takeScreenCapture(true);
        shareIntent.putExtra(Intent.EXTRA_STREAM, uri);
        shareIntent.setData(uri);
        shareIntent.setType("image/jpeg");
        shareIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(Intent.createChooser(shareIntent,
                getResources().getText(R.string.title_share)));
    }

    /**
     * Send user feedback via email with pre-populated email address, screen capture and optional
     * upload identifier
     * <p/>
     *
     * @param uploadId the identifier of the uploaded information; null if none
     */
    protected void emailFeedback(final CharSequence uploadId) {
        Intent feedbackIntent = new Intent(Intent.ACTION_SEND_MULTIPLE);
        feedbackIntent.putExtra(
                Intent.EXTRA_EMAIL,
                new String[]{
                        getResources().getText(
                                R.string.feedback_email_address).toString()
                }
        );
        String subject = getResources()
                .getText(R.string.feedback_email_subject).toString();

        feedbackIntent.putExtra(Intent.EXTRA_SUBJECT, subject);
        feedbackIntent.setType("message/rfc822");
        ArrayList<Uri> uris = new ArrayList<Uri>();
        uris.add(takeScreenCapture(true));
        if (uploadId != null) {
            uris.add(writeTextFileToSend(uploadId.toString()));
        }
        feedbackIntent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris);

        startActivity(Intent.createChooser(feedbackIntent, getResources()
                .getText(R.string.title_feedback)));
    }

    /**
     * Track background tasks making sure to synchronize the background task lifecycle with the
     * activity lifecycle.
     *
     * @see #onPause()
     */
    public void trackBackgroundTask(AsyncTask task) {
        if (_taskList == null) {
            _taskList = new ConcurrentLinkedQueue<AsyncTask>();
        }
        _taskList.add(task);
    }

    /**
     * Cancel background task previously tracked via {@link #trackBackgroundTask(android.os.AsyncTask)}
     *
     * @param task The task to cancel
     */
    public void cancelTrackedBackgroundTask(AsyncTask task) {
        if (_taskList != null && task != null) {
            task.cancel(true);
            _taskList.remove(task);
        }
    }

    /**
     * Check if the network status, notifying the user if the network is unavailable.
     * @return {@code true} if network is available, {@code false} otherwise
     */
    public boolean checkNetworkConnection() {
        if (!NetUtils.isConnected()) {
            new AlertDialog.Builder(this)
                    .setMessage(R.string.error_network_unavailable)
                    .setPositiveButton(android.R.string.ok, null)
                    .show();
            return false;
        }
        return true;
    }
}
