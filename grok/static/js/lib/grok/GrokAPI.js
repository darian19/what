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

/**
 * JavaScript library for the YOMP API
 * @class YOMP API Javascript Client
 * @copyright © 2013-2015 Numenta
 * @module
 * @requires jQuery
 * @see YOMP REST API Documentation: products/YOMP/app/webservices/README.md
 */

(function() {

    /**
     * Create a new instance of the YOMPAPI class.
     * @constructor
     * @param {Object} [opts] Options object to pass in.
     * @param {String} [opts.endPoint] API EndPoint to use.
     * @param {String} [opts.dataSource] Data Source to use (cloudwatch,
     *  graphite).
     * @public
     * @returns {Object} New instance object of constructed class.
     */
    var YOMPAPI = function(opts) {
        this.CONST = {

            // see: YOMP/webservices/README.md
            ENDPOINTS: {
                ANNOTATIONS:    '_annotations',
                ANOMALIES:      '_anomalies',
                AUTH:           '_auth',
                AUTOSTACKS:     '_autostacks',
                INSTANCES:      '_instances',
                METRICS:        '_metrics',
                MODELS:         '_models',
                NOTIFICATIONS:  '_notifications',
                SETTINGS:       '_settings',
                SUPPORT:        '_support',
                UPDATE:         '_update',
                WUFOO:          '_wufoo'
            },

            // per endpoint settings

            ANOMALIES: {
                PATHS: {
                    PERIOD: 'period'
                }
            },

            AUTOSTACKS: {
                PATHS: {
                    METRICS:           'metrics',
                    PREVIEW_INSTANCES: 'preview_instances'
                }
            },

            INSTANCES: {
                PATHS: {
                    SUGGESTIONS: 'suggestions'
                }
            },

            METRICS: {
                PATHS: {
                    CUSTOM:     'custom',
                    REGIONS:    'regions',
                    TAGS:       'AWS/Tags',
                    NAMESPACES: 'namespaces'
                }
            },

            MODELS: {
                PATHS: {
                    DATA:   'data',
                    EXPORT: 'export'
                }
            },

            NOTIFICATIONS: {
                PATHS: {
                    HISTORY: 'history'
                }
            },

            SETTINGS: {

                SECTIONS: {
                    AWS:        'aws',
                    NOTIFY:     'notifications',
                    USERTRACK:  'usertrack'
                },

                // per setting section

                AWS: {
                    KEY:    'aws_access_key_id',
                    SECRET: 'aws_secret_access_key',
                    REGION: 'default_region'
                },

                NOTIFY: {
                    SENDER: 'sender'
                },

                USERTRACK: {
                    OPTIN:      'optin',
                    NAME:       'name',
                    COMPANY:    'company',
                    EMAIL:      'email'
                }

            }

        };

        // variable options defaults
        this.opts = {
            apiKey: '',

            // see: /_metrics/datasources endPoint = ('cloudwatch', 'graphite')
            dataSource: 'cloudwatch',

            // endPoint: 'http://localhost:8888'
            endPoint: ''
        };
        // override defaults with user params
        $.extend(this.opts, opts);

        return this;
    };

    /**
     *
     */
    YOMPAPI.prototype.setApiKey = function(key) {
        this.opts.apiKey = key;
    };

    /**
     *
     */
    YOMPAPI.prototype._isFlatJson = function(val) {
        if(typeof val === 'string') {
            try {
                JSON.parse(val);
            }
            catch(error) {
                return false;
            }
            return true;
        }
        return false;
    };

    /**
     *
     */
    YOMPAPI.prototype._formatData = function(data) {
        if(typeof data === 'object') {
            return JSON.stringify(data);
        }
        return data;
    };

    /**
     * Make a HTTP Request via jQuery AJAX
     * @method
     * @param {String|Object} opts URL String to use, or Options Object, passed
     *  directly to jQuery.ajax(opts)
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @private
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype._makeRequest = function(opts, callback) {
        var me = this,
            request;

        if(typeof opts === 'string') {
            opts = { url: opts };
        }
        if(me.opts.apiKey) {
            opts.beforeSend = function(xhr) {
                xhr.setRequestHeader(
                    'Authorization',
                    'Basic ' +
                        YOMPUI.utils.Base64.encode(me.opts.apiKey + ':')
                );
            };
        }

        request = $.ajax(opts);

        if (callback) {
            request.fail(function(jqXHR, textStatus, error) {
                var result = jqXHR.responseText;
                if(me._isFlatJson(result)) {
                    result = JSON.parse(result).result;
                }
                callback(result);
            });

            request.done(function(response, textStatus, jqXHR) {
                callback(null, response);
            });
        }

        return request;
    };


    /**
     * Authorize users AWS creds via YOMP API (EC2 auth check)
     * @method
     * @param {Object} keys Object holding values and keys: 'aws_access_key_id',
     *  and 'aws_secret_access_key'
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.auth = function(keys, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTH
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(keys)
        }, callback);
    };


    /**
     * Create a monitored instance via YOMP API
     * @method
     * @param {String} region Region ID ('us-east-1')
     * @param {String} namespace Namespace Service Type name ('AWS/EC2')
     * @param {String} instance Instance name to monitor ('i-36234323')
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.createMonitoredInstance = function(
        region, namespace, instance, callback
    ) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES,
                region,
                namespace,
                instance
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST'
        }, callback);
    };


    /**
     * Delete monitored instance(s) via YOMP API
     * @method
     * @param {Array} instances List of Instance ID's to delete
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.deleteMonitoredInstances = function(instances, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE',
            data:   this._formatData(instances)
        }, callback);
    };


    /**
     * Get a list of monitored instances via YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getMonitoredInstances = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get a list of autostacks via YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getAutostacks = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get a preview list of instances to be associated with an autostack
     * via YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getAutostackPreview = function(
        region, filters, callback
    ) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS,
                this.CONST.AUTOSTACKS.PATHS.PREVIEW_INSTANCES
            ],
            data = {
                "region": region,
                "filters": this._formatData(filters)
            };

        return this._makeRequest({
            url:  url.join('/'),
            data: data
        }, callback);
    };


    /**
     * Create an autostack via YOMP API
     * @method
     * @param {String} name Autostack name
     * @param {String} region Region ID ('us-east-1')
     * @param {Object} filters List of filters ([ [{tag}, {value}], ... ])
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.createAutostack = function(
        name, region, filters, callback
    ) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS
            ],
            data = {
                "name": name,
                "region": region,
                "filters": filters
            };

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(data)
        }, callback);
    };


    /**
     * Delete an autostack via YOMP API
     * @method
     * @param {String} autostackID Autostack ID
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.deleteAutostack = function(autostackID, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS,
                autostackID
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE'
        }, callback);
    };


    /**
     * Get a list of metrics for an autostack via YOMP API
     * @method
     * @param {String} autostackID Autostack ID
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getAutostackMetrics = function(autostackID, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS,
                autostackID,
                this.CONST.AUTOSTACKS.PATHS.METRICS
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Associate a list of metrics with an autostack via YOMP API
     * @method
     * @param {String} autostackID Autostack ID
     * @param {Object} [metrics] List of metric dictionaries
     *  ([{"namespace": "AWS/EC2", "metric": "CPUUtilization" }, ...])
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.createAutostackMetrics = function(
        autostackID, metrics, callback
    ) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS,
                autostackID,
                this.CONST.AUTOSTACKS.PATHS.METRICS
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(metrics)
        }, callback);
    };


    /**
     * Delete a metric associated with an autostack via YOMP API
     * @method
     * @param {String} autostackID Autostack ID
     * @param {String} metricID Metric ID
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.deleteAutostackMetric = function(autostackID, metricID, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.AUTOSTACKS,
                autostackID,
                this.CONST.AUTOSTACKS.PATHS.METRICS,
                metricID
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE'
        }, callback);
    };


    /**
     * Send settings to YOMP API
     * @method
     * @param {Object} settings Settings object
     * @param {String} [section] Specific Section of config to act upon
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.putSettings = function(settings, section, callback) {
        if(typeof section === 'function') {
            callback = section;
            section = null;
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.SETTINGS
            ];

        if(section) {
            url.push(section);
        }

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(settings)
        }, callback);
    };


    /**
     * Get settings from YOMP API
     * @method
     * @param {String} [section] Specific Section of config to act upon
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getSettings = function(section, callback) {
        if(typeof section === 'function') {
            callback = section;
            section = null;
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.SETTINGS
            ];

        if(section) {
            url.push(section);
        }

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get current Data Source details from YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getDataSource = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get list of Regions from YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getRegions = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                this.CONST.METRICS.PATHS.REGIONS
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get details for a specific Region from YOMP API
     * @method
     * @param {String} region Region to use ('us-east-1')
     * @param {Object} [opts] Options to pass in: 'tags' filter
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getRegionDetails = function(region, opts, callback) {
        if(typeof opts === 'function') {
            callback = opts;
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                this.CONST.METRICS.PATHS.REGIONS,
                region
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   opts
        }, callback);
    };

    /**
     * Get list of all instance metrics for a specific Region and Namespace
     *  from YOMP API.
     * @method
     * @param {String} region Region to use ('us-east-1')
     * @param {String} namespace Namespace to use ('AWS/EC2')
     * @param {Object} [opts] Options to pass in: 'tags' filter
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     */
    YOMPAPI.prototype.getInstanceMetrics = function(region, namespace, opts, callback) {
        if(typeof opts === 'function') {
            callback = opts;
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                region,
                namespace
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   opts
        }, callback);
    };


    /**
     * Get list of Namespaces from YOMP API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getNamespaces = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                this.CONST.METRICS.PATHS.NAMESPACES
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get details for a specific Namespace from YOMP API
     * @method
     * @param {String} namespace Namespace to investigate ('AWS/EC2')
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getNamespaceDetails = function(namespace, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                namespace
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get YOMP Custom Metrics from API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getYOMPCustomMetrics = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.CONST.METRICS.PATHS.CUSTOM
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Deletes a YOMP Custom Metric (uses metricName as in custom_api.py)
     * @method
     * @param {String} Metric name
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.deleteYOMPCustomMetric = function(metricName, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.CONST.METRICS.PATHS.CUSTOM,
                metricName
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE'
        }, callback);
    };

    /**
     * Get tags
     * @method
     * @param {String} region Region to use ('us-east-1')
     * @param {String} res_type Reservation type ('instances')
     * @param {String} index Instance to use ('i-3022352255')
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getTags = function(region, res_type, index, callback) {
        if(typeof res_type === 'function') {
            callback = res_type;
            res_type = null;
        }
        if(typeof index === 'function') {
            callback = index;
            index = null;
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.METRICS,
                this.opts.dataSource,
                region,
                this.CONST.METRICS.PATHS.TAGS
            ];

        if (res_type) { url.push(res_type); }
        if (index) { url.push(index); }

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get a list of created models from the API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getModels = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.MODELS
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get a list of created models from the sorted models API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @param {Number} [range] Time, in seconds over which to sort
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getModelsSortedByAnomaly = function(callback, range) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.ANOMALIES,
                this.CONST.ANOMALIES.PATHS.PERIOD,
                range
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Get data for a specific created model from the API
     * @method
     * @param {String} modelId Model ID to get data for from the API
     * @param {Object} [opts] Options to pass in: from/to/anomaly/limit
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getModelData = function(modelId, opts, callback) {
        if(typeof opts === 'function') {
            callback = opts;
            opts = {};
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.MODELS,
                modelId,
                this.CONST.MODELS.PATHS.DATA
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   opts
        }, callback);
    };


    /**
     * Get Instance suggestions
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     */
    YOMPAPI.prototype.getInstanceSuggestions = function(region, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES,
                this.CONST.INSTANCES.PATHS.SUGGESTIONS
            ];

        if (typeof region != 'undefined') url.push(region);

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Select instance using YOMP API
     * @method
     * @param {String} Instance identifier (<region>/<namespace>/<id>)
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @param {Boolean} Issue call asynchronously
     * @public
     */
    YOMPAPI.prototype.selectInstance = function(instance, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES,
                instance
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST'
        }, callback);
    };


    /**
     * Select instances using YOMP API (batch mode)
     * @method
     * @param {Array} Instance identifiers
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @param {Boolean} Issue call asynchronously
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.selectInstances = function(region, namespace, instances, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.INSTANCES,
                region,
                namespace
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(instances)
        }, callback);
    };


    /**
     * Export models (for later import) from the API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.exportModels = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.MODELS,
                this.CONST.MODELS.PATHS.EXPORT
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Create model(s) via YOMP API, using creation object(s) we got previously.
     * @method
     * @param {Object|Array} modelCreators Model creation data which was
     *  fetched previously from the API, and later sent back to it.
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.createModels = function(modelCreators, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.MODELS
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(modelCreators)
        }, callback);
    };


    /**
     * Delete a single model via YOMP API, using model id.
     * @method
     * @param {String} Model id
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.deleteModel = function(modelId, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.MODELS,
                modelId
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE'
        }, callback);
    };


    /**
     * Get notification settings from API
     * @method
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
     YOMPAPI.prototype.getNotifications = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.NOTIFICATIONS
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Set/Update notification setting via API
     * @method
     * @param {Object} data Notification info used to create object, please see:
     *  YOMP-app/YOMP/webservices/README.md, create/update notification.
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
     YOMPAPI.prototype.setNotification = function(data, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.NOTIFICATIONS
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST',
            data:   this._formatData(data)
        }, callback);
    };


    /**
     * Get notification history from the API
     * @method
     * @param {Object} [opts] Options to pass to the API (like ?limit=100)
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getNotificationHistory = function(opts, callback) {
        if(typeof opts === 'function') {
            callback = opts;
            opts = {};
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.NOTIFICATIONS,
                this.CONST.NOTIFICATIONS.PATHS.HISTORY
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   this._formatData(opts)
        }, callback);
    };


    /**
     * Check API for current support access status
     * @method
     * @param {Function} [callback] function(Object error): Function to run
     *  when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getSupportAccess = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.SUPPORT
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Remove support access via API
     * @method
     * @param {Function} [callback] function(Object error): Function to run
     *  when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.removeSupportAccess = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.SUPPORT
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'DELETE'
        }, callback);
    };


    /**
     * Allow support access via API
     * @method
     * @param {Function} [callback] function(Object error): Function to run
     *  when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.setSupportAccess = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.SUPPORT
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST'
        }, callback);
    };


    /**
     * Check API for a pending system update
     * @method
     * @param {Function} [callback] function(Object error): Function to run
     *  when call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getUpdate = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.UPDATE
            ];

        return this._makeRequest(url.join('/'), callback);
    };


    /**
     * Trigger a system update via API
     * @method
     * @param {Function} [callback] function(Object error): Function to run when
     *  call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.setUpdate = function(callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.UPDATE
            ];

        return this._makeRequest({
            url:    url.join('/'),
            type:   'POST'
        }, callback);
    };


    /**
     * Send user registration to WuFoo form
     * @method
     * @param {Object} opts Options to pass to the API, user info to save
     * @param {Function} [callback] function(Object error): Function to run when
     *  call finishes.
     * @public
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.sendWufooForm = function(opts, callback) {
        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.WUFOO
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   this._formatData(opts),
            type:   'POST'
        }, callback);
    };


    /**
     * Returns all annotations for the given time range
     * @param {Object} [opts] Options to pass in: from/to
     * @param {Function} [callback] function(Object error, Object results):
     *  Function to run when call finishes.
     * @returns {Object} jqXHR object
     */
    YOMPAPI.prototype.getAnnotations = function(opts, callback) {
        if(typeof opts === 'function') {
            callback = opts;
            opts = {};
        }

        var url = [
                this.opts.endPoint,
                this.CONST.ENDPOINTS.ANNOTATIONS
            ];

        return this._makeRequest({
            url:    url.join('/'),
            data:   this._formatData(opts)
        }, callback);
    };


    /***************************************************************************
     * Export module to many platforms
     **************************************************************************/
    if(typeof module !== 'undefined') {
        // Node CommonJS module
        module.exports = YOMPAPI;
    }
    else if(typeof define !== 'undefined') {
        // AMD module
        define('YOMPAPI', function() { return YOMPAPI });
    }
    else {
        // Browser
        window.YOMPAPI = YOMPAPI;
    }

}());
