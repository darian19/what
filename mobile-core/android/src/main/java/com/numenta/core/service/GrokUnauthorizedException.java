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

package com.numenta.core.service;

/**
 * This exception is thrown when the user is not authorized to perform the YOMP Operation
 */
public class YOMPUnauthorizedException extends YOMPException {
    private static final long serialVersionUID = 1809635266016612517L;

    public YOMPUnauthorizedException() {
    }

    public YOMPUnauthorizedException(String detailMessage) {
        super(detailMessage);
    }

    public YOMPUnauthorizedException(Throwable throwable) {
        super(throwable);
    }

    public YOMPUnauthorizedException(String detailMessage, Throwable throwable) {
        super(detailMessage, throwable);
    }
}
