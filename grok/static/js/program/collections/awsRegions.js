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
   * Backbone.js Collection for a group of AWS Regions
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone.js, YOMP AwsRegionModel class
   * @returns {Object} Backbone.js Collection object
   */
  YOMPUI.AwsRegionsCollection = Backbone.Collection.extend({

    // Backbone.Collection properties

    model: YOMPUI.AwsRegionModel,

    // Custom properties

    api: null,

    // Backbone.Collection methods

    /**
     *
     */
    initialize: function(models, options) {
      this.api = options.api;
    },

    /**
     * Handle the fetch/sync response, repack to Backbone.Model format
     * @returns {Array} List of Backbone.Model objects to create
     */
    parse: function(regions) {
      var result = Object.keys(regions).sort().map(function(region) {
        var name = regions[region].replace(' Region', ''),
            display = '<strong>' + region + '</strong>: ' + name,
            model = {
              id:   region,
              name: display
            };

        return model;
      });

      return result;
    },

    /**
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
          result = this.api.getRegions(function(error, regions) {
            if(error) return options.error(error);
            return options.success(regions);
          });
          break;

        case 'update':
          break;

        case 'delete':
          break;
      }

      return result;
    }

  });

}());
