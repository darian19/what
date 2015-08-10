
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

package com.numenta.core.utils;

import com.numenta.core.app.YOMPApplication;

import android.os.Build;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.io.Writer;
import java.util.Collection;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;


public class Log {
    private static final String DEVICE_ID = "deviceID=" + YOMPApplication.getDeviceId();
    private static final String SERIAL = " SERIAL=" + Build.SERIAL;

    private static final String DEVICE_INFO =
            "APP_VERSION=" + YOMPApplication.getVersion()
                    + " OS_VERSION=" + Build.VERSION.RELEASE
                    + " SDK_VERSION=" + Build.VERSION.SDK_INT
                    + " OS_BUILD=" + Build.ID
                    + " DEVICE=" + Build.MODEL + "-" + Build.MANUFACTURER + "(" + Build.DEVICE
                    + ")";
    private static final String TAG = Log.class.getCanonicalName();
    // Max logs to keep in memory. 10k uses about 1MB memory.
    public static final int MAX_LOGS_TO_KEEP = 10000;
    public static final BlockingQueue<String> _queue = new LinkedBlockingQueue<String>(
            MAX_LOGS_TO_KEEP);

    protected static void queueLog(String msg) {
        if (YOMPApplication.shouldUploadLog()) {
            // Discard oldest log when the queue is full.
            if (!_queue.offer(msg)) {
                _queue.poll();
                _queue.offer(msg);
            }
        }
    }

    protected static void queueLog(String type, String tag, String msg) {
        if (YOMPApplication.shouldUploadLog()) {
            // Server Logging API requires the following fields separate by space:
            // DEVICE_ID EVENT_TYPE TIMESTAMP TAG MESSAGE

            final StringBuilder sb = new StringBuilder(DEVICE_ID)
                    .append(" eventType=").append(type)
                    .append(" timestamp=").append(System.currentTimeMillis() / 1000L)
                    .append(" tag=").append(tag)
                    .append(" message=").append(DEVICE_INFO).append(SERIAL).append(" ")
                    .append(msg);
            queueLog(sb.toString());
        }
    }

    protected static void queueLog(String type, String tag, String msg,
            Throwable tr) {
        if (YOMPApplication.shouldUploadLog()) {
            Writer result = new StringWriter();
            PrintWriter printWriter = new PrintWriter(result);
            tr.printStackTrace(printWriter);
            // Server Logging API requires the following fields separate by space:
            // DEVICE_ID EVENT_TYPE TIMESTAMP TAG MESSAGE
            final StringBuilder sb = new StringBuilder(DEVICE_ID)
                    .append(" eventType=").append(type)
                    .append(" timestamp=").append(System.currentTimeMillis() / 1000L)
                    .append(" tag=").append(tag)
                    .append(" message=").append(DEVICE_INFO).append(" ")
                    .append(SERIAL).append(" ").append(msg)
                    .append(" (").append(result.toString()).append(")");
            queueLog(sb.toString());
        }
    }


    /**
     * Drains the entries logged to the given collection
     *
     * @param logs The collection to drain the logs to
     */
    public static void drainTo(Collection<String> logs) {
        BlockingQueue<String> queue = Log._queue;
        if (queue.isEmpty()) {
            return;
        }
        queue.drainTo(logs);
    }

    public static int d(String tag, String msg) {
        queueLog("DEBUG", tag, msg);
        return android.util.Log.d(tag, msg);
    }

    public static int e(String tag, String msg) {
        queueLog("ERROR", tag, msg);
        return android.util.Log.e(tag, msg);
    }

    public static int e(String tag, String msg, Throwable tr) {
        queueLog("ERROR", tag, msg, tr);
        return android.util.Log.e(tag, msg, tr);
    }

    public static int i(String tag, String msg) {
        queueLog("INFO", tag, msg);
        return android.util.Log.i(tag, msg);
    }

    public static int v(String tag, String msg) {
        queueLog("DEBUG", tag, msg);
        return android.util.Log.v(tag, msg);
    }

    public static int w(String tag, String msg) {
        queueLog("WARN", tag, msg);
        return android.util.Log.w(tag, msg);
    }

    public static int wtf(String tag, Throwable tr) {
        queueLog("CRITICAL", tag, "", tr);
        return android.util.Log.wtf(tag, tr);
    }

    public static int wtf(String tag, String msg) {
        queueLog("CRITICAL", tag, msg);
        return android.util.Log.wtf(tag, msg);
    }

    public static int wtf(String tag, String msg, Throwable tr) {
        queueLog("CRITICAL", tag, msg, tr);
        return android.util.Log.wtf(tag, msg, tr);
    }

}
