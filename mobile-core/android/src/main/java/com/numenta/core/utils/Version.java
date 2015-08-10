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

import android.support.annotation.NonNull;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Helper class used to parse and compare YOMP Server versions
 */
public class Version implements Comparable<Version> {

    // 1.1.0-852-g731d51e-alpha
    // major.minor.maintenance-build-sha-qualifier
    public static final Pattern VERSION_REGEX = Pattern
            .compile("(\\d+)\\.(\\d+)\\.?(\\d*)-?(\\d*)-?(\\w*)-?(\\w*)");

    /** Represents unknown version */
    public static Version UNKNOWN = new Version(null);

    int _major;
    int _minor;
    int _maintenance;
    int _build;
    String _sha;
    String _qualifier;

    public Version(String version) {
        if (version != null) {
            final Matcher match = VERSION_REGEX.matcher(version);
            String val;
            if (match.find()) {
                val = match.group(1);
                _major = !val.isEmpty() ? Integer.parseInt(val) : 0;
                val = match.group(2);
                _minor = !val.isEmpty() ? Integer.parseInt(val) : 0;
                val = match.group(3);
                _maintenance = !val.isEmpty() ? Integer.parseInt(val) : 0;
                val = match.group(4);
                _build = !val.isEmpty() ? Integer.parseInt(val) : 0;
                _sha = match.group(5);
                _qualifier = match.group(6);
            }
        }
    }

    public int getMajor() {
        return this._major;
    }

    public int getMinor() {
        return this._minor;
    }

    public int getMaintenance() {
        return this._maintenance;
    }

    public int getBuild() {
        return this._build;
    }

    public String getSHA() {
        return this._sha;
    }

    @Override
    public String toString() {
        final StringBuilder sb = new StringBuilder();
        sb.append(_major).append('.').append(_minor).append('.').append(_maintenance);
        if (_build > 0)
            sb.append('-').append(_build);
        if (_sha != null && !_sha.isEmpty())
            sb.append("-").append(_sha);
        if (_qualifier != null && !_qualifier.isEmpty())
            sb.append("-").append(_qualifier);
        return sb.toString();
    }

    @Override
    public int compareTo(@NonNull Version another) {
        if (another == this)
            return 0;
        int res = _major - another._major;
        if (res == 0) {
            res = _minor - another._minor;
        }
        if (res == 0) {
            res = _maintenance - another._maintenance;
        }
        if (res == 0) {
            res = _build - another._build;
        }
        // Ignore SHA
        return res;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof Version && compareTo((Version) o) == 0;
    }

    @Override
    public int hashCode() {
        return (((((_major * 37) + _minor) * 37) + _maintenance) * 37) + _build;
    }

    /**
     * @return the qualifier
     */
    public String getQualifier() {
        return this._qualifier;
    }
}
