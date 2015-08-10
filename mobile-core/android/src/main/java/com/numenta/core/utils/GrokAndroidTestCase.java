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

import android.content.Context;
import android.test.AndroidTestCase;

import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Method;

public class YOMPAndroidTestCase extends AndroidTestCase {

    protected Context _getTestContext() {
        try {
            // For some reason the method {@link AndroidTestCase#getTestContext}
            // was marked as "hidden" therefore use reflection to call it.
            Method getTestContext = AndroidTestCase.class.getMethod("getTestContext");
            return (Context) getTestContext.invoke(this);
        } catch (final Exception exception) {
            //noinspection CallToPrintStackTrace
            exception.printStackTrace();
            return null;
        }
    }
    protected InputStream getTestData(Version version, String fileName) throws IOException {
        return getTestData(version.toString(), fileName);
    }

    protected InputStream getTestData(String version, String fileName) throws IOException {
        return _getTestContext().getResources().getAssets()
                .open(version + "/" + fileName);
    }
}
