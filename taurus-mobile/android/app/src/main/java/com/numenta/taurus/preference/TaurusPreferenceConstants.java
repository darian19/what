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

public class TaurusPreferenceConstants extends PreferencesConstants {

    /** State of the last view: favorites or all */
    public static final String PREF_LAST_VIEW_STATE = "last_view_state";
    /** Last time the notifications were checked */
    public static final String PREF_NOTIFICATION_LAST_RUN_TIME = "notification_last_run_time";
    /** Ringtone used for taurus notifications */
    public static final String PREF_NOTIFICATIONS_RINGTONE = "notifications_ringtone";
    /** Whether or not taurus notifications vibrates the phone */
    public static final String PREF_NOTIFICATIONS_VIBRATE = "notifications_vibrate";
    /** The last time the metric list was downloaded from the server */
    public static final String PREF_LAST_METRIC_SYNC_TIME = "last_metric_sync_time";
    /** When to force update the previous hour bucket */
    public static final String PREF_PREVIOUS_HOUR_THRESHOLD = "previous_hour_threshold";
}
