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

package com.numenta.core.preference;

/**
 * Preference constants, the values of this file should be synchronized with the contents of the
 * file in /res/xml/preferences.xml
 */
public class PreferencesConstants {
    /** Whether or not to skip the tutorial next time the user starts the app */
    public static final String PREF_SKIP_TUTORIAL = "skip_tutorial";
    /** Default Refresh rate in minutes */
    public static final String PREF_DATA_REFRESH_RATE = "data_refresh_rate";
    /** Time of the last successful connection to the server */
    public static final String PREF_LAST_CONNECTED_TIME = "TIME_LAST_CONNECTED";
    /** Whether or not "all" notifications are enabled */
    public static final String PREF_NOTIFICATIONS_ENABLE = "notifications_enable";
    /**
     * Max Notifications Per Instance.
     * Notification window in seconds during which no other notifications for a given instance
     * should be sent to a given device
     */
    public static final String PREF_NOTIFICATIONS_FREQUENCY = "notification_frequency";
    /** Whether or not the to initialize the server notifications */
    public static final String PREF_NOTIFICATION_INITIALIZED = "notification_initialized";
    /** Current application version */
    public static final String PREF_VERSION = "version";
    /** Current server version */
    public static final String PREF_SERVER_VERSION = "server_version";
}
