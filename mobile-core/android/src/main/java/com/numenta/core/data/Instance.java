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

package com.numenta.core.data;

import java.io.Serializable;

public class Instance implements Serializable {

    private static final long serialVersionUID = 3843336684219539713L;

    private String _id;
    private String _name;
    private String _namespace;
    private String _location;
    private String _message;
    private int _status;

    /**
     * @param id
     * @param name
     * @param namespace
     * @param location
     * @param message
     * @param status
     */
    protected Instance(String id, String name, String namespace, String location, String message,
            int status) {
        this._id = id;
        this._name = name != null ? name : id;
        this._namespace = namespace;
        this._location = location;
        this._message = message;
        this._status = status;
    }

    /**
     * @return the instance id
     */
    public String getId() {
        return this._id;
    }

    /**
     * @return the name
     */
    public String getName() {
        return this._name;
    }

    /**
     * @return the namespace
     */
    public String getNamespace() {
        return this._namespace;
    }

    /**
     * @return the location
     */
    public String getLocation() {
        return this._location;
    }

    /**
     * @return the message
     */
    public String getMessage() {
        return this._message;
    }

    /**
     * @return the status
     */
    public int getStatus() {
        return this._status;
    }
}
