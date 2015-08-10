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

    YOMPUI.ModalMetricListView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#modal-metric-list-tmpl').html()),

        events: {
        },


        // Custom properties

        msgs: YOMPUI.msgs('modal-metric-list-tmpl'),
        site: YOMPUI.msgs('site'),

        $modal: null,

        api:        null,
        instance:   null,
        id:         null,
        name:       null,
        namespace:  null,
        region:     null,

        data: {
            autostacks: null,
            customs:    null,
            metrics:    null,
            models:     null,
            namespaces: null
        },

        autostackData:  null,
        creators:       null,
        metrics:        null,


        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.api =        options.api;
            this.instance =   options.instance;
            this.id =         options.instance.split('/').pop();

            this.name =       options.name;
            this.namespace =  options.namespace;
            this.region =     options.region;

            this.data.autostacks =  options.data.autostacks;
            this.data.customs =     options.data.customs;
            this.data.metrics =     options.data.metrics;
            this.data.models =      options.data.models;
            this.data.namespaces =  options.data.namespaces;

            this.autostackData =    {};
            this.creators =         {};
            this.metrics =          {};
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var me = this,
                id = this.instance.split('/').pop(),
                autostackDataHandle = null;

            if(this.isYOMPAutostack()) {
                // Prep data - get possible YOMP Autostacks
                var YOMPAutostackNamespace =    this.data.namespaces.get('Autostacks'),
                    YOMPAutostackMetrics =      YOMPAutostackNamespace.get('metrics'),
                    awsEc2Namespace =           this.data.namespaces.get('AWS/EC2'),
                    awsEc2Metrics =             awsEc2Namespace.get('metrics');

                for(var i=0; i<YOMPAutostackMetrics.length; i++) {
                    var metric = YOMPAutostackMetrics[i];
                    me.metrics[metric] = false;
                    me.creators[metric] = new YOMPUI.AwsMetricModel({
                        metric:     metric,
                        region:     me.region,
                        namespace:  YOMPAutostackNamespace.id,
                        identifier: me.instance
                    });
                }
                for(var i=0; i<awsEc2Metrics.length; i++) {
                    var metric = awsEc2Metrics[i];
                    me.metrics[metric] = false;
                    me.creators[metric] = new YOMPUI.AwsMetricModel({
                        metric:     metric,
                        region:     me.region,
                        namespace:  awsEc2Namespace.id,
                        identifier: me.instance
                    });
                }

                var matchedAutostacks = this.data.autostacks.filter(
                    function(autostack) {
                        return(
                            (autostack.get('region') === me.region) &&
                            (autostack.id == id)
                        );
                    }
                );

                if (!matchedAutostacks.length) {
                    return YOMPUI.utils.modalError("Autostack not found.");
                }

                var autostack = matchedAutostacks[0];

                this.autostackData.name =    autostack.get('name');
                this.autostackData.region =  autostack.get('region');
                this.autostackData.filters = JSON.stringify(autostack.get('filters'));

                autostackDataHandle = this.api.getAutostackPreview(
                    autostack.get('region'),
                    autostack.get('filters'),
                    function(error, instances) {
                        if(error) return YOMPUI.utils.modalError(error);

                        var members = instances.map(function(instance) {
                            var name = instance.tags.Name,
                                id = instance.instanceID;

                            return name ? (name + " (" + id + ")") : id;
                        });

                        this.autostackData.members = members;
                    }.bind(this)
                );
            }
            else if(this.isYOMPCustomMetric()) {
                // Prep data - get possible YOMP Custom Metrics
                me.region = me.site.name + ' ' + me.site.regions.YOMP.custom;
                me.namespace = me.site.namespaces.YOMP.custom;

                me.data.customs.forEach(function(metric) {
                    // only want single current YOMP Custom Metric
                    if(me.name === metric.get('name')) {
                        var key = metric.get('name');
                        me.metrics[key] = false;
                        me.creators[key] = metric;
                    }
                });
            }
            else {
                // Prep data - get possible regular Metrics
                var filter = {
                    region:     this.region,
                    namespace:  this.namespace,
                    identifier: id
                };

                this.data.metrics.where(filter).forEach(function(metric) {
                    var key = metric.get('metric');
                    this.metrics[key] = false;
                    this.creators[key] = metric;
                }.bind(this));
            }

            // got all the data, now mark which metrics are "on"
            this.data.models.forEach(function(model) {
                var instance = (this.isYOMPAutostack() || this.isYOMPCustomMetric()) ?
                        this.instance :
                        [ this.region, this.namespace, this.id ].join('/');

                if(
                    (instance === model.get('server')) &&
                    (Object.keys(this.metrics).indexOf(model.get('metric')) > -1)
                ) {
                    this.metrics[model.get('metric')] = model.id;
                }
            }.bind(this));

            // show dialog
            this.$modal = bootbox.dialog({
                animate:    false,
                message:    'Loading...',
                show:       false,
                title:      "Select Metrics to Monitor",
                buttons: {
                    done: {
                        label:      'Done',
                        className:  'btn-primary'
                    }
                }
            });
            this.$modal.on('hidden.bs.modal', function(event) {
                this.trigger('view-closed');
            }.bind(this));
            this.$modal.modal('show');

            var data = {
                baseUrl:        NTA.baseUrl,
                msgs:           this.msgs,
                site:           this.site,
                region:         this.region,
                namespace:      this.namespace,
                display:        this.name,
                metrics:        this.metrics
            };
            var rendered = this.template(data);

            this.$modal.find('.bootbox-body').html(rendered);

            this.$modal.find('input[type="checkbox"]').each(function() {
                // dialog content into on/off switches
                var $el = $(this);
                $el.bootstrapSwitch();
                $el.on(
                    'switchChange.bootstrapSwitch',
                    me.handleCheckBoxClick.bind(me)
                );
            });

            // if autostacks, put more details
            $.when(autostackDataHandle).done(function() {
                var $el =       this.$modal.find('.autostack'),
                    wrapTerm =  function(str) { return '<dt>' + str + '</dt>'; },
                    wrapDef =   function(str) { return '<dd>' + str + '</dd>'; },
                    details =   [];

                if(
                        (! this.autostackData.members)
                    ||  (this.autostackData.members.length <= 0)) {
                    return;
                }

                details = [
                    wrapTerm(this.msgs.autostack.name),
                    wrapDef(this.autostackData.name),
                    wrapTerm(this.msgs.autostack.region),
                    wrapDef(this.autostackData.region),
                    wrapTerm(this.msgs.autostack.filters),
                    wrapDef(this.autostackData.filters),
                    wrapTerm(this.msgs.autostack.numMembers),
                    wrapDef(this.autostackData.members.length),
                    wrapTerm(this.msgs.autostack.members),
                    wrapDef(this.autostackData.members.join('<br/>')),
                ];

                $el.removeClass('hidden');
                $el.find('dl').append(details.join(''));
            }.bind(this));

            this.trigger('view-ready');
            return this;
        },


        // Custom methods

        /**
         * Is this a YOMP Autostack?
         * @returns {boolean}
         */
        isYOMPAutostack: function() {
            return this.instance.match(this.site.instances.types.autostack);
        },

        /**
         * Is this a YOMP Custom Metric?
         * @returns {boolean}
         */
        isYOMPCustomMetric: function() {
            return this.namespace.match(this.site.namespaces.YOMP.custom);
        },

        /**
         * Handle a Metric toggle
         */
        handleCheckBoxClick: function(event, state) {
            var me = this,
                $node = $(event.currentTarget),
                metric = $node.data('metric'),
                checked = state,
                id = this.instance.split("/").pop(),
                modelFilter = {},
                models = null,
                modelId = null,
                newModel = (this.creators[metric].get('datasource') === 'custom') ?
                            {
                                datasource: this.creators[metric].get('datasource'),
                                metric: metric
                            } : this.creators[metric].toJSON();

            if(this.isYOMPAutostack()) {
                modelFilter = {
                    location:   this.region,
                    server:     this.instance,
                    metric:     metric
                };
            }
            else if(this.isYOMPCustomMetric()) {
                modelFilter = {
                    server: metric,
                    metric: metric
                };
            }
            else {
                modelFilter = {
                    location:   this.region,
                    server:     [ me.region, me.namespace, id ].join('/'),
                    metric:     metric
                };
            }

            models = this.data.models.where(modelFilter);

            modelId = (models.length > 0) ? models[0].id : null;

            if(checked && (metric in me.creators)) {
                YOMPUI.utils.throb.start(me.site.state.metric.start);
                if(this.isYOMPAutostack()) {
                    // create autostack
                    me.api.createAutostackMetrics(
                        id,
                        [{
                            metric:     this.creators[metric].get('metric'),
                            namespace:  this.creators[metric].get('namespace')
                        }],
                        function(error, response) {
                            if(error) return YOMPUI.utils.modalError(error);
                            me.data.models.add({
                                datasource: me.creators[metric].get('datasource'),
                                location:   me.creators[metric].get('region'),
                                metric:     me.creators[metric].get('metric'),
                                server:     me.instance,
                                id:         response.metric.uid,
                                uid:        response.metric.uid
                            });
                            return YOMPUI.utils.throb.stop();
                        }
                    );
                } else {
                    // create regular model
                    me.data.models.create(newModel, {
                        error: function(model, response, options) {
                            return YOMPUI.utils.modalError(response);
                        },
                        success: function(model, response, options) {
                            return YOMPUI.utils.throb.stop();
                        }
                    });
                }
            }
            else if((! checked) && modelId) {
                YOMPUI.utils.throb.start(me.site.state.metric.stop);

                if (me.isYOMPAutostack()) {
                    me.api.deleteAutostackMetric(id, modelId, function(error) {
                        if(error) return YOMPUI.utils.modalError(error);
                        me.data.models.remove(me.data.models.get(modelId));
                        return me.data.models.fetch({
                            error: function(model, response, options) {
                                return YOMPUI.utils.modalError(response);
                            },
                            success: function(model, response, options) {
                                return YOMPUI.utils.throb.stop();
                            }
                        });
                    });
                } else {
                    me.data.models.get(modelId).destroy({
                        error: function(model, response, options) {
                            return YOMPUI.utils.modalError(response);
                        },
                        success: function(model, response, options) {
                            return YOMPUI.utils.throb.stop();
                        }
                    });
                }
            }
        }

    });

})();
