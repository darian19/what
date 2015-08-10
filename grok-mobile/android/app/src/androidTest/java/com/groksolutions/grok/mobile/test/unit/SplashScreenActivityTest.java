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

package com.YOMPsolutions.YOMP.mobile.test.unit;

import android.test.ActivityInstrumentationTestCase2;
import android.test.suitebuilder.annotation.LargeTest;

import com.YOMPsolutions.YOMP.mobile.SplashScreenActivity;

/**
 * This is a simple framework for a test of an Application. See
 * {@link android.test.ApplicationTestCase ApplicationTestCase} for more information on how to write
 * and extend Application tests.
 * <p/>
 * To run this test, you can type: adb shell am instrument -w \ -e class SplashScreenActivityTest \
 * com.YOMPsolutions.YOMP.mobile.tests/android.test.InstrumentationTestRunner
 */
public class SplashScreenActivityTest extends
        ActivityInstrumentationTestCase2<SplashScreenActivity> {

    private SplashScreenActivity splashScreenActivity;

    public SplashScreenActivityTest() {
        super(SplashScreenActivity.class);
    }

    protected void setUp() throws Exception {
        super.setUp();

        splashScreenActivity = getActivity();
    }

    @LargeTest
    public void testSomething() {
        assertNotNull(splashScreenActivity);
    }

}
