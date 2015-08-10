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

package com.YOMPsolutions.YOMP.mobile.service;

import org.json.JSONObject;

/**
 * Represents the notification settings stored in the server for this device.
 */
public class NotificationSettings {

    private final String _email;
    private final int _frequency;

    public NotificationSettings(String email, int frequency) {
        this._email = email;
        this._frequency = frequency;
    }

    /**
     * Construct notification settings from its JSON object returned by the server in the following
     * format:<code><pre>
     * {
     *    "email_addr": "mail@host.tld",
     *    "windowsize": 3600,
     *    "sensitivity": 0.99999,
     *    "last_timestamp": "2014-02-06 00:00:00",
     *    "uid": "9a90eaf2-6374-4230-aa96-0830c0a737fe"
     * }
     * </pre></code> <b>NOTE:</b> Only <i>email_addr</i> and <i>windowsize</i> are being used by the
     * client
     *
     * @param json JSON Object returned by the server
     * @see com.numenta.core.service.YOMPClient#getNotificationSettings()
     */
    public NotificationSettings(JSONObject json) {
        this._email = json.optString("email_addr");
        this._frequency = json.optInt("windowsize", 3600);
    }

    /**
     * Target email address associated with device
     */
    public String getEmail() {
        return this._email;
    }

    /**
     * Notification window in seconds during which no other notifications for a given instance
     * should be sent to a given device
     */
    public int getFrequency() {
        return this._frequency;
    }
}
