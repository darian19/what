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

  var CONST = {
    STATUS: {
      UNMONITORED: {
        CODE: 0,
        NAME: 'Unmonitored',
        _WEIGHT: 1
      },
      ACTIVE: {
        CODE: 1,
        NAME: 'Active',
        _WEIGHT: 2
      },
      CREATE: {
        CODE: 2,
        NAME: 'Creating',
        _WEIGHT: 3
      },
      ERROR: {
        CODE: 4,
        NAME: 'Error',
        _WEIGHT: 5
      },
      PENDING: {
        CODE: 8,
        NAME: 'Pending',
        _WEIGHT: 4
      }
    }
  };

  /**
   * Backbone.js Model for a YOMP Monitored Instance (/_instances API endpoint)
   * @constructor
   * @copyright © 2014 Numenta
   * @public
   * @requires Backbone.js
   * @returns {Object} Backbone.js Model object
   */
  YOMPUI.InstanceModel = Backbone.Model.extend({

    // Backbone.Model properties

    idAttribute: 'server',

    defaults: {
      status:       CONST.STATUS.CREATE.CODE,
      statusName:   CONST.STATUS.CREATE.NAME
    },

    // Custom properties

    CONST: CONST,

    // Backbone.Model methods

    /**
     * Backbone.Model.parse()
     */
    parse: function(response, options) {
      if(
        (!('server' in response)) &&
        ('_server' in response)
      ) {
        response.server = response._server;
      }

      response = this.parseLocation(response);
      response = this.parseDisplayName(response);
      response = this.parseStatusName(response);
      response = this.parseStatusMessage(response);
      return response;
    },

    /**
     * Backbone.Model.sync()
     */
    sync: function(method, model, options) {
      var options = options || {},
          result = null;

      switch(method) {
        case 'create':
          result = this.collection.api.createMonitoredInstance(
            model.get('location'),
            model.get('namespace'),
            model.get('instance'),
            function(error) {
              if(error) return options.error(error);
              return options.success(model.toJSON());
            }
          );
          break;

        case 'read':
          break;

        case 'update':
          break;

        case 'delete':
          result = this.collection.api.deleteMonitoredInstances(
            [ model.id ],
            function(error) {
              if(error) return options.error(error);
              return options.success();
            }
          );
          break;
      }

      return result;
    },

    // Custom methods

    /**
     *
     */
    parseDisplayName: function(instance) {
      var site = this.collection.site,
          id = instance.server.split('/').pop(),
          isAutoScaleGroup = function(value) {
            return value.match(site.instances.types.autoscale);
          };

      if((instance.namespace.match(site.namespaces.aws.real) ||
          instance.namespace.match("Autostacks/")) &&
         instance.server.match(site.instances.types.autostack)) {
        // YOMP Autostack pretty display name
        instance.display =
          instance.name + ' (' +
          site.name + ' ' +
          site.instances.types.autostack +
          ')';
        instance.namespace = "AWS/EC2"
      }
      else if(instance.name && (instance.name !== id)) {
        // regular display name
        instance.display = instance.name + ' (' + id + ')';
      }
      else if(
        ('parameters' in instance) &&
        ('metricSpec' in instance.parameters) &&
        ('dimensions' in instance.parameters.metricSpec) &&
        Object.keys(instance.parameters.metricSpec.dimensions).some(isAutoScaleGroup)
      ) {
        // AutoScalingGroup pretty dipslay name
        instance.display =
          instance.server.split('/').pop() +
          ' (' + site.instances.types.autoscale + ')';
      }
      else {
        instance.display = id;
      }
      return instance;
    },

    /**
     *
     */
    parseLocation: function(instance) {
      if(! instance.location) {
        instance.location = this.collection.site.name;
        instance.namespace = this.collection.site.namespaces.YOMP.custom;
      }
      return instance;
    },

    /**
     *
     */
    parseStatusName: function(instance) {
      var highestWeightedStatus = this.CONST.STATUS.UNMONITORED.NAME;
      var highestWeightedStatusWeight = this.CONST.STATUS.UNMONITORED._WEIGHT;

      Object.keys(this.CONST.STATUS).forEach(function(status) {
        if(this.CONST.STATUS[status].CODE && ((instance.status & this.CONST.STATUS[status].CODE) == this.CONST.STATUS[status].CODE)) {
          if (this.CONST.STATUS[status]._WEIGHT >= highestWeightedStatusWeight) {
            highestWeightedStatus = this.CONST.STATUS[status].NAME;
            highestWeightedStatusWeight = this.CONST.STATUS[status]._WEIGHT;
          }
        }
      }.bind(this));

      instance.statusName = highestWeightedStatus;

      return instance;
    },

    /**
     *
     */
    parseStatusMessage: function(instance) {
      // strip errors of tags
      if(instance.message && instance.message.match(/<.*?>/)) {
        instance.message = instance.message.replace(/<.*?>/g, '');
      }
      return instance;
    }

  });

}());
