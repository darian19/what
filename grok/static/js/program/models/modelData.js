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
   * Backbone.js Model for a YOMP Metric/Model's DATA (/_models/data endpoint)
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone, Backbone.Model
   * @returns {Object} Backbone.Model object
   */
  YOMPUI.ModelDataModel = Backbone.Model.extend({

    // Backbone.Model properties

    // Custom properties

    api: null,

    // Backbone.Model methods

    /**
     * Backbone.Model.initalize()
     */
    initialize: function(model, options) {
      this.api = options.api;
    },

    /**
     * Backbone.Model.sync()
     * Custom override for Backbone.sync(), since we're using our own API
     *  library REST calls, and not going to let Backbone do XHR directly.
     */
    sync: function(method, model, options) {
      var options = options || {},
          filters = {},
          result =  null;

      switch(method) {
        case 'create':
          break;

        case 'read':
          [ 'anomaly', 'limit', 'from', 'to' ].forEach(function(key) {
            if(key in options) {
              filters[key] = options[key];
            }
          });

          result = this.api.getModelData(
            model.id,
            filters,
            function(error, response) {
              if(error) return options.error(error);
              return options.success(response);
            }
          );
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
