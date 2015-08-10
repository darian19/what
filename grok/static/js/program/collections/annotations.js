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
   * Backbone.js Collection for a group of YOMP Annotations, from the
   *  the /_annotations API endpoint.
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone.js, YOMP AnnotationModel class
   * @returns {Object} Backbone.js Collection object
   */
  YOMPUI.AnnotationsCollection = Backbone.Collection.extend({

    // Backbone.Collection properties

    model: YOMPUI.AnnotationModel,

    // Custom properties
    
    api: null,
    
    // Backbone.Collection methods
    
    initialize: function(models, options) {
        this.api = options.api;
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
          result = this.api.getAnnotations(function(error, models) {
            if(error) return options.error(error);
            return options.success(models);
          });
          break;

        case 'update':
          break;

        case 'delete':
          break;
      }

      return result;
    },
    
    comparator : function(item) {
        return [item.get('timestamp'), item.get('created')]; 
    }
    // Custom methods

  });

}());