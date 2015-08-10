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
   * Backbone.js Model for an AWS Metric
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone, Backbone.Model
   * @returns {Object} Backbone.Model object
   */
  YOMPUI.AwsMetricModel = Backbone.Model.extend({

    // Backbone.Model properties

    // Custom properties

    // Backbone.Model methods

    /**
     * Backbone.Model.parse()
     */
    parse: function(response, options)  {
      var dimension = null;

      // pretty display name defaults
      if(
        ('name' in response) &&
        (response.name.length > 0)
      ) {
        response.display = response.name + ' (' + response.identifier + ')';
      }
      else {
        response.name = response.display = response.identifier;
      }

      if('dimensions' in response) {
        // rewrite dimensions a little so that model creator can use them
        Object.keys(response.dimensions).forEach(function(dimension) {
          if(typeof(response.dimensions[dimension]) === 'object') {
            response.dimensions[dimension] = response.dimensions[dimension][0];
          }
        });

        dimension = Object.keys(response.dimensions)[0];
        if(
          dimension &&
          dimension.match(this.collection.site.instances.types.autoscale)
        ) {
          // pretty display name - YOMP Autostack
          response.display = response.name +
            ' (' + this.collection.site.instances.types.autoscale + ')';
        }
      }

      return response;
    }

    // Custom methods

  });

}());
