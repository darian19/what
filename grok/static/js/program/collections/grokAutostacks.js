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

(function() {

  /**
   * Backbone.Collection for a group of YOMP Autostacks
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone, Backbone.Collection, YOMPUI.YOMPAutostackModel
   * @returns {Object} Backbone.Collection object
   */
  YOMPUI.YOMPAutostacksCollection = Backbone.Collection.extend({

    // Backbone.Collection properties

    model: YOMPUI.YOMPAutostackModel,

    // Custom properties

    api: null,
    site: null,

    // Backbone.Collection methods

    /**
     * Backbone.Collection.initalize()
     */
    initialize: function(models, options) {
      this.api = options.api;
      this.site = options.site;
    },

    /**
     * Backbone.Collection.sync()
     * Custom override for Backbone.sync(), since we're using our own API
     *  library REST calls, and not going to let Backbone do XHR directly.
     */
    sync: function(method, collection, options) {
      var options = options || {},
          result = null;

      switch(method) {
        case 'create':
          break;

        case 'read':
          result = this.api.getAutostacks(function(error, autostacks) {
            if(error) return options.error(error);
            return options.success(autostacks);
          });
          break;

        case 'update':
          break;

        case 'delete':
          break;
      }

      return result;
    }

    // Custom methods

  });

}());
