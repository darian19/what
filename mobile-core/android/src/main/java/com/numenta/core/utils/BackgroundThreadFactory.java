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


import android.os.Process;
import android.support.annotation.NonNull;

import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Thread factory creating background threads. Give background threads a
 * slightly lower than normal priority, so that it will have less chance of
 * impacting the responsiveness of the UI
 *
 * @see "http://developer.android.com/reference/android/os/Process.html"
 */
public final class BackgroundThreadFactory implements ThreadFactory {

    public static final String TAG = BackgroundThreadFactory.class.getSimpleName();

    private final String _name;

    public BackgroundThreadFactory(String name) {
        super();
        this._name = name;
    }

    private final AtomicInteger threadNumber = new AtomicInteger(1);

    @Override
    public Thread newThread(@NonNull Runnable r) {
        return new Thread(r, _name + " # " + threadNumber.getAndIncrement()) {
            @Override
            public void run() {
                android.os.Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
                android.util.Log.i(TAG, "Starting Thread " + getName());
                super.run();
                android.util.Log.i(TAG, "Stopping Thread " + getName());
            }
        };
    }
}
