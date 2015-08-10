
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

package com.YOMPsolutions.YOMP.mobile.notification;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.data.YOMPDatabase;
import com.YOMPsolutions.YOMP.mobile.dialog.ConfirmDialogFragment;
import com.numenta.core.data.Metric;
import com.numenta.core.data.Notification;
import com.numenta.core.service.NotificationService;
import com.numenta.core.utils.Log;

import android.annotation.SuppressLint;
import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.DialogFragment;
import android.support.v4.app.FragmentActivity;
import android.support.v4.content.LocalBroadcastManager;
import android.support.v4.widget.SimpleCursorAdapter;
import android.support.v4.widget.SimpleCursorAdapter.ViewBinder;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.View;
import android.view.View.OnTouchListener;
import android.widget.AdapterView;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

@SuppressLint("ClickableViewAccessibility")
public class NotificationListActivity extends FragmentActivity implements
        ConfirmDialogFragment.ConfirmDialogListener,
        GestureDetector.OnGestureListener {

    private static final float DELETION_FLING_THRESHOLD = 20f;
    static final String TAG = NotificationListActivity.class.getCanonicalName();

    private YOMPDatabase YOMPDb;
    private int doomedNotificationIndex = -1;
    private BroadcastReceiver _notificationsReceiver;
    private SimpleCursorAdapter adapter;
    private final DateFormat sdf = new SimpleDateFormat("HH:mm a EEE MM/dd/yy", Locale.US);
    private ListView listView;
    private Button dismissButton;
    private Button closeButton;
    private TextView noNotificationsText;
    private GestureDetector gestureDetector;
    private int notificationSize;
    private long unreadNotificationSize;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        gestureDetector = new GestureDetector(getApplicationContext(), this);
        setContentView(R.layout.activity_notification_list);
        setVisible(false);

        listView = (ListView) findViewById(R.id.notification_list_view);
        dismissButton = (Button) findViewById(R.id.action_dismiss_all_notifications);
        closeButton = (Button) findViewById(R.id.action_close_notifications);
        noNotificationsText = (TextView) findViewById(R.id.no_notifications_text);

        // For the cursor adapter, specify which columns go into which views
        String[] fromColumns = {
                "timestamp", "description", "metric_id", "read"
        };
        int[] toViews = {
                R.id.notification_time,
                R.id.notification_description,
                R.id.notification_delete,
                R.id.notification_unread
        }; // The TextView in simple_list_item_1
        YOMPDb = YOMPApplication.getDatabase();
        adapter = new SimpleCursorAdapter(this,
                R.layout.fragment_notification_list_item, null,
                fromColumns, toViews, 0);

        new AsyncTask<Void, Void, Cursor>() {
            @Override
            protected Cursor doInBackground(Void... params) {
                unreadNotificationSize = YOMPDb.getUnreadNotificationCount();
                return YOMPDb.getNotificationCursor();
            }

            @Override
            protected void onPostExecute(Cursor cursor) {
                setVisible(true);
                adapter.changeCursor(cursor);
                notificationSize = cursor.getCount();
                updateButtons();
            }
        }.execute();

        _notificationsReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (adapter != null) {
                    new AsyncTask<Void, Void, Cursor>() {
                        @Override
                        protected Cursor doInBackground(Void... params) {
                            if (isCancelled())
                                return null;
                            return YOMPDb.getNotificationCursor();
                        }

                        @Override
                        protected void onPostExecute(Cursor cursor) {
                            adapter.changeCursor(cursor);
                            updateButtons();
                        }
                    }.execute();
                }
            }
        };

        adapter.setViewBinder(new ViewBinder() {

            @Override
            public boolean setViewValue(View view, Cursor cursor, int columnIndex) {
                final int viewId = view.getId();

                switch (viewId) {
                    case R.id.notification_time:
                        // Converts the timestamp to a readable time.
                        final int timeIndex = cursor.getColumnIndex("timestamp");
                        Date date = new Date(cursor.getLong(timeIndex));
                        ((TextView) view).setText(sdf.format(date));
                        break;
                    case R.id.notification_unread:
                        // Hides notification icon if already read.
                        if (cursor.getInt(cursor.getColumnIndex("read")) < 1) {
                            view.setVisibility(View.VISIBLE);
                        } else {
                            view.setVisibility(View.INVISIBLE);
                        }
                        break;
                    case R.id.notification_delete:
                        // Adds click handler for notification deletions
                        view.setOnClickListener(new View.OnClickListener() {
                            @Override
                            public void onClick(View v) {
                                Log.i(TAG,
                                        "{TAG:ANDROID.ACTION.NOTIFICATION.DELETE} Delete notification clicked");
                                View layout = (View) v.getParent();
                                int position = listView.getPositionForView(layout);
                                NotificationListActivity.this.removeNotificationAt(position);
                            }
                        });
                        break;
                    default:
                        return false;
                }
                return true;
            }
        });

        listView.setAdapter(adapter);

        // Clicks on the notifications themselves navigates to the detail view.
        listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, final View view, int position, long id) {
                Log.i(TAG,
                        "{TAG:ANDROID.ACTION.NOTIFICATION.SELECT} Notification navigation should occur here to notification "
                                + position);
                Cursor cursor = (Cursor) adapter.getItem(position);
                int localIdx = cursor.getColumnIndex("_id");
                final int localId = cursor.getInt(localIdx);

                new AsyncTask<Void, Void, Intent>() {
                    @Override
                    protected Intent doInBackground(Void... v) {
                        // Get the metric necessary for the new intent to view
                        // the metric detail
                        // page.
                        Notification notification = YOMPDb.getNotificationByLocalId(localId);
                        if (notification == null) {
                            // The notification or metric was deleted as the
                            // user view the list
                            return null;
                        }
                        Metric metric = YOMPDb.getMetric(notification.getMetricId());
                        if (metric == null) {
                            // the metric was deleted, so nowhere to go
                            YOMPDb.deleteNotification(localId);
                            return null;
                        }
                        Intent metricDetail = NotificationUtils.createMetricDetailIntent(
                                NotificationListActivity.this, notification);
                        // Mark the notification as read

                        if (!notification.isRead()) {
                            YOMPDb.markNotificationRead(localId);
                        }
                        ((NotificationManager) getSystemService(NOTIFICATION_SERVICE))
                                .cancelAll();

                        return metricDetail;
                    }

                    @Override
                    protected void onPostExecute(Intent metricDetail) {
                        if (metricDetail == null) {
                            Toast.makeText(NotificationListActivity.this,
                                    R.string.notification_expired, Toast.LENGTH_LONG).show();
                            NotificationListActivity.this.finish();
                            return;
                        }
                        // Show detail page
                        startActivity(metricDetail);
                        // Hide the 'unread' indication.
                        view.findViewById(R.id.notification_unread).setVisibility(View.INVISIBLE);
                    }
                }.execute();

            }
        });

        // This catches "fling" events on items to delete notifications within
        // the list.
        // Defers touch events to a GestureDetector, which isolates fling events
        // from touch events.
        listView.setOnTouchListener(new OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                return gestureDetector.onTouchEvent(event);
            }
        });

        dismissButton.setOnClickListener(
                new View.OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        Log.i(TAG, "{TAG:ANDROID.ACTION.NOTIFICATION.DELETE_ALL}");
                        deleteAllNotifications();
                    }
                });

        closeButton.setOnClickListener(
                new View.OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        cancelNotifications();
                    }
                }
                );
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

    protected void removeNotificationAt(int position) {
        doomedNotificationIndex = position;
        String question = getString(R.string.confirm_dismiss_notification);
        String yes = getString(R.string.confirm_dialog_positive);
        String no = getString(R.string.confirm_dialog_negative);
        ConfirmDialogFragment dialog = ConfirmDialogFragment.newInstance(question, yes, no);
        dialog.show(getSupportFragmentManager(), "dismissNotification");
        // See the onDialogPositiveClick() and onNegativeClick() functions for
        // confirm dialog handling.
    }

    protected void deleteAllNotifications() {
        String question = getString(R.string.confirm_dismiss_all);
        String yes = getString(R.string.confirm_dialog_positive);
        String no = getString(R.string.confirm_dialog_negative);
        ConfirmDialogFragment dialog = ConfirmDialogFragment.newInstance(question, yes, no);
        dialog.show(this.getSupportFragmentManager(), "dismissAllNotifications");
    }

    protected void cancelNotifications() {
        finish();
    }

    private void updateButtons() {
        if (notificationSize == 0) {
            dismissButton.setVisibility(View.GONE);
            noNotificationsText.setVisibility(View.VISIBLE);
        } else {
            dismissButton.setVisibility(View.VISIBLE);
            closeButton.setVisibility(View.VISIBLE);
            noNotificationsText.setVisibility(View.GONE);
        }
    }

    @Override
    public void onDialogPositiveClick(final DialogFragment dialog) {
        String tag = dialog.getTag();
        if (tag.equals("dismissAllNotifications")) {
            // Remove in background.
            new AsyncTask<Void, Void, Void>() {
                @Override
                protected Void doInBackground(Void... v) {
                    NotificationService.deleteAllNotifications();
                    // Also cancel any pending OS notifications.
                    ((NotificationManager) getSystemService(NOTIFICATION_SERVICE)).cancelAll();
                    return null;
                }

                @Override
                protected void onPostExecute(Void v) {
                    dialog.dismiss();
                    NotificationListActivity.this.finish();
                    finish();
                }
            }.execute();
        } else if (tag.equals("dismissNotification")) {
            removeDoomedNotification();
            dialog.dismiss();
        } else {
            Log.d(TAG, "Unknown dialog click: " + tag);
        }
    }

    @Override
    public void onDialogNegativeClick(DialogFragment dialog) {
        dialog.dismiss();
    }

    private void removeDoomedNotification() {
        if (doomedNotificationIndex > -1) {
            Cursor doomed = (Cursor) adapter.getItem(doomedNotificationIndex);
            int notificationId = doomed.getInt(0);
            final int isRead = doomed.getInt(doomed.getColumnIndex("read"));

            new AsyncTask<Integer, Void, Cursor>() {
                @Override
                protected Cursor doInBackground(Integer... params) {
                    int id = params[0];
                    long deleted = NotificationService.deleteNotification(id);
                    Log.d(TAG, "Deleted notification " + doomedNotificationIndex + "? : " + deleted);
                    return YOMPDb.getNotificationCursor();
                }

                @Override
                protected void onPostExecute(Cursor cursor) {
                    adapter.changeCursor(cursor);
                    adapter.notifyDataSetChanged();
                    notificationSize = cursor.getCount();
                    if (isRead == 0) {
                        unreadNotificationSize--;
                    }

                    if (unreadNotificationSize > 1) {
                        // if the notification size is greater than 1, we really
                        // only care about
                        // the notification size. The rest of the data is
                        // unused.
                        NotificationUtils.createOSNotification("", System.currentTimeMillis(), 0,
                                unreadNotificationSize);
                    } else if (unreadNotificationSize == 1) {
                        // need to pull out the data from the cursor because we
                        // don't want to
                        // access the database from here.
                        int localId = cursor.getInt(cursor.getColumnIndex("_id"));
                        String description = cursor.getString(cursor.getColumnIndex("description"));
                        long timestamp = cursor.getLong(cursor.getColumnIndex("timestamp"));
                        NotificationUtils.createOSNotification(description, timestamp,
                                localId, 1);
                    } else if (unreadNotificationSize == 0) {
                        ((NotificationManager) getSystemService(NOTIFICATION_SERVICE)).cancelAll();
                    }

                    updateButtons();
                }
            }.execute(notificationId);
        }
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onPause()
     */
    @Override
    protected void onPause() {
        super.onPause();
        LocalBroadcastManager.getInstance(this).registerReceiver(
                _notificationsReceiver,
                new IntentFilter(NotificationService.NOTIFICATION_CHANGED_EVENT));
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onResume()
     */
    @Override
    protected void onResume() {
        super.onResume();
        LocalBroadcastManager.getInstance(this).unregisterReceiver(_notificationsReceiver);
    }

    @Override
    public boolean onFling(MotionEvent downEvent, MotionEvent moveEvent, float velocityX,
            float velocityY) {
        // Only fling horizontally for delete, ignore vertical flings, which
        // should scroll through the list.
        float yDelta = Math.abs(downEvent.getY() - moveEvent.getY());
        if (yDelta < DELETION_FLING_THRESHOLD) {
            int position = listView.pointToPosition((int) downEvent.getX(), (int) downEvent.getY());
            Log.i(TAG, "{TAG:ANDROID.ACTION.NOTIFICATION.FLING} Notification deleted by fling.");
            NotificationListActivity.this.removeNotificationAt(position);
            return true;
        }
        return false;
    }

    /*
     * See below for unimplemented methods of OnGestureListener. This is one
     * thing that sucks about Java.
     */

    @Override
    public boolean onDown(MotionEvent e) {
        return false;
    }

    @Override
    public void onShowPress(MotionEvent e) {
        // Do nothing
    }

    @Override
    public boolean onSingleTapUp(MotionEvent e) {
        return false;
    }

    @Override
    public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX,
            float distanceY) {
        return false;
    }

    @Override
    public void onLongPress(MotionEvent e) {
        // Do nothing
    }
}
