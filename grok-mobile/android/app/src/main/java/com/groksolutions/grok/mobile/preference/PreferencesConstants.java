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

/**
 * Preference constants, the values of this file should be synchronized with the contents of the
 * file in /res/xml/preferences.xml
 */
public final class PreferencesConstants extends com.numenta.core.preference.PreferencesConstants {
    public static final String PREF_SHOW_TUTORIAL = "show_tutorial";
    public static final String PREF_SKIP_TUTORIAL = "skip_tutorial";

    /** YOMP Server URL **/
    public static final String PREF_SERVER_URL = "server_url";
    /** YOMP Server Password */
    public static final String PREF_PASSWORD = "password";
    /** Whether or not the local notifications settings need to be sent to the server */
    public static final String PREF_NOTIFICATION_NEED_UPDATE = "notification_need_update";
    /** Whether or not "email" notifications are enabled */
    public static final String PREF_EMAIL_NOTIFICATIONS_ENABLE = "email_notifications_enable";
    /** The email to send notifications */
    public static final String PREF_NOTIFICATIONS_EMAIL = "notification_email";
    /** User name used  for annotations */
    public static final String PREF_USER_NAME = "user_name";

}
