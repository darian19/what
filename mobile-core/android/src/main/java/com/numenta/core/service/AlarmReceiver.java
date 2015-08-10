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

package com.numenta.core.service;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.support.v4.content.WakefulBroadcastReceiver;

/**
 * Wake up {@link YOMPService} every 15 minutes.
 * <p>
 * When the alarm fires, this WakefulBroadcastReceiver receives the broadcast Intent and execute
 * the
 * alarm code {@link YOMPService}
 */
public class AlarmReceiver extends WakefulBroadcastReceiver {

    private static final String TAG = "AlarmReceiver";

    private AlarmManager _alarmMgr;

    private PendingIntent _alarmIntent;

    @Override
    public void onReceive(Context context, Intent intent) {
        Intent service = new Intent(context, YOMPService.class);
        startWakefulService(context, service);
    }

    public void stopAlarm() {
        if (_alarmMgr != null) {
            _alarmMgr.cancel(_alarmIntent);
        }
    }

    public void startAlarm(Context context) {
        _alarmMgr = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        Intent intent = new Intent(context, AlarmReceiver.class);
        _alarmIntent = PendingIntent.getBroadcast(context, 0, intent, 0);

        // Tries to wakeup the phone every 15 minutes to synchronize the data.
        // The 15 minutes interval was chosen because this way this be alarm will be phase-aligned
        // with other alarms to reduce the number of wake ups. See AlarmManager#setInexactRepeating
        _alarmMgr.setInexactRepeating(AlarmManager.RTC,
                System.currentTimeMillis(),
                AlarmManager.INTERVAL_FIFTEEN_MINUTES, _alarmIntent);
    }
}
