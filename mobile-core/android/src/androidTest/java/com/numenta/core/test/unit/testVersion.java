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

package com.numenta.core.test.unit;

import com.numenta.core.utils.YOMPAndroidTestCase;
import com.numenta.core.utils.Version;

import android.test.suitebuilder.annotation.SmallTest;

public class testVersion extends YOMPAndroidTestCase {
    @SmallTest
    public void testMajorMinorMaintBuildShaQualifier() {
        Version ver = new Version("1.2.3-272-gbbeb635-alpha");
        assertEquals(1, ver.getMajor());
        assertEquals(2, ver.getMinor());
        assertEquals(3, ver.getMaintenance());
        assertEquals(272, ver.getBuild());
        assertEquals("gbbeb635", ver.getSHA());
        assertEquals("alpha", ver.getQualifier());
        assertEquals("1.2.3-272-gbbeb635-alpha", ver.toString());
    }

    @SmallTest
    public void testMajorMinorMaint() {
        Version ver = new Version("1.2.3");
        assertEquals(1, ver.getMajor());
        assertEquals(2, ver.getMinor());
        assertEquals(3, ver.getMaintenance());
        assertEquals(0, ver.getBuild());
        assertEquals("", ver.getSHA());
        assertEquals("", ver.getQualifier());
        assertEquals("1.2.3", ver.toString());
    }

    @SmallTest
    public void testMajorMinor() {
        Version ver = new Version("1.2");
        assertEquals(1, ver.getMajor());
        assertEquals(2, ver.getMinor());
        assertEquals(0, ver.getMaintenance());
        assertEquals(0, ver.getBuild());
        assertEquals("", ver.getSHA());
        assertEquals("", ver.getQualifier());
        assertEquals("1.2.0", ver.toString());
    }

    @SmallTest
    public void testCompare() {
        Version ver1_1 = new Version("1.1");
        Version ver1_1_same = new Version("1.1");
        Version ver1_2 = new Version("1.2");
        Version ver1_2_3 = new Version("1.2.3");
        Version ver1_2_3_272_qa = new Version("1.2.3-272-gbbeb635-qa");

        assertTrue(ver1_1.equals(ver1_1_same));
        assertTrue(ver1_1.equals(ver1_1));
        //noinspection EqualsBetweenInconvertibleTypes
        assertFalse(ver1_1.equals("1.1"));
        //noinspection ObjectEqualsNull
        assertFalse(ver1_1.equals(null));
        assertFalse(ver1_1.equals(ver1_2));
        assertTrue(ver1_1.compareTo(ver1_2) < 0);
        assertTrue(ver1_2_3_272_qa.compareTo(ver1_2_3) > 0);
    }
}
