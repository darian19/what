/* ----------------------------------------------------------------------
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
 * ---------------------------------------------------------------------- */

window.NTA = {};

// for FaceOfYOMP FOG Dygrpahs module
window.YOMP = {
    util: {
        /**
         * Straight from the Definitive Guide to JavaScript (5th Ed.), by
         * David Flanagan.
         * @param {Object} p Prototype object to create an heir from.
         */
        heir: function(p) {
            function F() {}   // A dummy constructor function
            F.prototype = p;  // Specify the prototype object we want
            return new F();   // Invoke the constructor to create new object
        }
    }
};

// add a helper function to Backbone.View()
$.extend(Backbone.View.prototype, {
    /**
     * Sane way to add sub-views to a view
     * http://ianstormtaylor.com/rendering-views-in-backbonejs-isnt-always-simple/
     */
    assign: function(view, selector) {
       view.setElement(this.$(selector));
    }
});
