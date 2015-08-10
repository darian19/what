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

    YOMPUI.InstanceListView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#instance-list-tmpl').html()),

        events: {
            'click .metric-link':       'handleMetrics',
            'click td button.close':    'handleDeleteOne',
            'click .delete':            'handleDeleteAll',
            'click .export':            'handleExport'
        },

        // Custom properties

        api:    null,
        msgs:   YOMPUI.msgs('instance-list-tmpl'),
        site:   YOMPUI.msgs('site'),

        data: {
            autostacks: null,
            customs:    null,
            exports:    null,
            instances:  null,
            metrics:    null,
            models:     null,
            namespaces: null
        },

        // Backbone.View methods

        /**
         *
         */
        initialize: function(options) {
            var me = this,
                collectOpts = {
                    api:    options.api,
                    site:   options.site
                },
                fetchOpts = {
                    error: function(model, response, options) {
                        return YOMPUI.utils.modalError(response);
                    }
                },
                dataExists = function(key) {
                    return (key && options.data && options.data[key] && (options.data[key] instanceof Backbone.Collection));
                },
                fetchList = []; // missing data queued here for loading

            this.api = options.api;

            // Prep Collections - data passed in, or create here

            this.data.autostacks = dataExists('autostacks') ?
                options.data.autostacks :
                new YOMPUI.YOMPAutostacksCollection([], collectOpts);

            this.data.customs = dataExists('customs') ?
                options.data.customs :
                new YOMPUI.YOMPCustomMetricsCollection([], collectOpts);

            this.data.exports = dataExists('exports') ?
                options.data.exports :
                new YOMPUI.ModelExportsCollection([], collectOpts);

            this.data.instances = dataExists('instances') ?
                options.data.instances:
                new YOMPUI.InstancesCollection([], collectOpts);

            this.data.metrics = dataExists('metrics') ?
                options.data.metrics :
                new YOMPUI.AwsMetricsCollection([], collectOpts);

            this.data.models = dataExists('models') ?
                options.data.models :
                new YOMPUI.ModelsCollection([], collectOpts);

            this.data.namespaces = dataExists('namespaces') ?
                options.data.namespaces :
                new YOMPUI.AwsNamespacesCollection([], collectOpts);

            // Prep Collections - data passed in, or fetch here

            if(this.data.autostacks.length <= 0) {
                fetchList.push(this.data.autostacks.fetch(fetchOpts));
            }
            if(this.data.customs.length <= 0) {
                fetchList.push(this.data.customs.fetch(fetchOpts));
            }
            if(this.data.instances.length <= 0) {
                fetchList.push(this.data.instances.fetch(fetchOpts));
            }
            if(this.data.namespaces.length <= 0) {
                fetchList.push(this.data.namespaces.fetch(fetchOpts));
            }

            // add listeners to this view

            this.listenTo(this.data.instances, 'sync', function() {
                // reload models if instances change
                this.data.models.fetch({
                    error: function(model, response, options) {
                        return YOMPUI.utils.modalError(response);
                    }
                });

                this.render();
            }.bind(this));

            // fetch if necessary
            if(fetchList.length > 0) {
                $.when.apply($, fetchList).done(function() {
                    // no-op for now
                });
            }
        },

        /**
         *
         */
        render: function() {
            var me = this,
                instances = me.data.instances,
                autostacks = me.data.autostacks,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    instances: instances
                };

            // Copy any autostacks that don't have metrics to list of
            // monitored instances
            newInstancesData = [];
            autostacks.each(function(autostack) {
                if (!instances.find(function(instance) {
                    return instance.id == "Autostacks/" + autostack.id;
                })) {
                    newInstancesData.push({
                        status: 0,
                        name: autostack.get("name"),
                        namespace: "AWS/EC2", 
                        server: "Autostacks/" + autostack.get("uid"), 
                        location: autostack.get("region")
                    });
                }
            });
            _.each(newInstancesData, function(instanceData) {
                var instance = new YOMPUI.InstanceModel();
                instances.add(instance);
                instanceData = instance.parse(instanceData);
                instance.set(instanceData);
            });

            me.$el.html(me.template(data));

            if(me.data.instances.length > 0) {
                me.$el.css('opacity', 1);
                $('.tablesorter').tablesorter();
            }
            else {
                // no instances, mute listing
                me.$el.css('opacity', 0.5);
            }

            me.trigger('view-ready');
            return me;
        },

        // Custom methods

        /**
         * instance title is clicked in order to customize metrics for instance
         */
        handleMetrics: function(event) {
            var $node = $(event.currentTarget),
                $row = $node.parents('tr'),
                region = $row.data('region'),
                namespace = $row.data('namespace'),
                instance = $row.data('instance'),
                regionNamespaceFilter = {
                    region:     region,
                    namespace:  namespace
                },
                regionNamespaceMetrics = this.data.metrics.where(regionNamespaceFilter),
                isYOMPAutostack = namespace.match(this.site.instances.types.autostack),
                isYOMPCustomMetric = namespace.match(this.site.namespaces.YOMP.custom),
                makeView = function() {
                    var modalMetricList = new YOMPUI.ModalMetricListView({
                        api:        this.api,
                        region:     region,
                        namespace:  namespace,
                        instance:   instance,
                        name:       $row.data('name'),
                        data: {
                            autostacks: this.data.autostacks,
                            customs:    this.data.customs,
                            metrics:    this.data.metrics,
                            models:     this.data.models,
                            namespaces: this.data.namespaces
                        }
                    });
                    modalMetricList.bind('view-closed', function() {
                        // if they turned all metrics off, instance will now be gone,
                        //  so reload instance list.
                        this.data.instances.fetch({
                            error: function(model, response, options) {
                                return YOMPUI.utils.modalError(response);
                            },
                            success: function(model, response, options) {
                                YOMPUI.utils.throb.stop();
                            }
                        });
                    }.bind(this));

                    return modalMetricList;
                }.bind(this);

            event.stopPropagation();
            event.preventDefault();

            YOMPUI.utils.throb.start(this.site.state.metric.load);

            if(
                (! isYOMPAutostack) &&
                (! isYOMPCustomMetric) &&
                (regionNamespaceMetrics.length <= 0)
            ) {
                // Metric data for this region not loaded yet, do so.
                // Make sure to fetch all metrics and autostacks collections.
                $.when(this.data.metrics.fetch({
                            region:     region,
                            namespace:  namespace,
                            remove:     false}),
                       this.data.autostacks.fetch({
                            region:     region,
                            namespace:  namespace,
                            remove:     false})
                        ).
                    done(function(model) {
                        YOMPUI.utils.throb.stop();
                        var view = makeView();
                        view.render();
                    }).            
                    fail(function(xhr, error, response) {
                        YOMPUI.utils.throb.stop();
                        return YOMPUI.utils.modalError(response);                        
                    });
            }
            else {
                // Metric data for this region already loaded, continue.
                YOMPUI.utils.throb.stop();
                var view = makeView();
                view.render();
                return view;
            }
        },

        /**
         * Actually remove instance(s) from monitoring (delete models).
         *  Use recursion so if there is a problem the loop won't keep dumbly
         *  running forever.
         */
        performDelete: function(list, index) {
            index = index || 0;

            var percent = 0,
                errorCallback = function(model, response, options) {
                    YOMPUI.utils.throb.stop();
                    return YOMPUI.utils.modalError(response);
                },
                destroyOpts = {
                    error: errorCallback,
                    success: function(model, response, options) {
                        // update % in throbber
                        percent = Math.round((index / list.length) * 100);
                        YOMPUI.utils.throb.message(
                            this.site.state.instance.stop +
                            ' (' + percent + '%)'
                        );

                        // next recursion
                        this.performDelete(list, index + 1);
                    }.bind(this)
                };

            if(index < list.length) {
                // continue recursive loop
                var item = list[index],
                    itemParts = item.split("/"),
                    namespace = itemParts[0],
                    id = itemParts[1];

                if(namespace.match(this.site.instances.types.autostack)) {
                    // destroy autostack
                    this.data.autostacks.get(id).destroy(destroyOpts);
                }
                else {
                    // destroy regular instance
                    this.data.instances.get(item).destroy(destroyOpts);
                }
            }
            else {
                // all done with recursive loop
                this.data.instances.fetch({
                    error: errorCallback,
                    success: function(model, response, options) {
                        YOMPUI.utils.throb.stop();
                    }
                });
            }
        },

        /**
         * User clicked delete button on 1 instance row
         */
        handleDeleteOne: function(event) {
            var me = this,
                $row = $(event.currentTarget).parents('tr'),
                region,
                instance = $row.data('instance'),
                name = $row.data('name'),
                display;

            event.stopPropagation();
            event.preventDefault();

            $row.addClass('bg-danger');

            if($row.data('region')) {
                region = $row.data('region');
                namespace = $row.data('namespace');
            }
            else {
                region = me.site.name + ' ' + me.site.regions.YOMP.custom;
                namespace = me.site.namespaces.YOMP.custom;
            }

            display = '<code class="truncate">' + [
                region,
                namespace,
                name
            ].join(' <span class="text-muted">&gt;</span> ') + '</code>';
            manageCustomMetricsPath = me.site.paths['manage-custom-metrics'];

            if (region != 'YOMP'){
                modalMessage = '<div>Remove this instance from monitoring?</div>' + display;
            }
            else {
                modalMessage = '<div>Stop monitoring this custom metric?</div>' + display +
                '<br /><div>To delete this metric\'s data, use the <a href="' + manageCustomMetricsPath +
                '">Manage Custom Metrics</a> page.</div>';
            }

            // ask user to confirm instance delete
            bootbox.confirm({
                animate:    false,
                message:    modalMessage,
                title:      'Remove',
                callback:   function(result) {
                    if(result) {
                        $row.fadeOut();
                        YOMPUI.utils.throb.start(me.site.state.instance.stop);
                        me.performDelete([instance]);
                    }
                    else {
                        $row.removeClass('bg-danger');
                    }
                }
            });
        },

        /**
         * User clicked Remove All button
         */
        handleDeleteAll: function(event) {
            var me = this,
                $rows = me.$el.find('.instances > tr'),
                instances = [];

            event.stopPropagation();
            event.preventDefault();

            $rows.addClass('bg-danger');

            $rows.each(function() {
                var instance = $(this).data('instance');
                if(instance) {
                    instances.push(instance);
                }
            });

            if(instances.length > 0) {
                // ask user to confirm instance delete
                bootbox.confirm({
                    animate:    false,
                    message:    'Remove all <strong>' + instances.length + '</strong> instances from monitoring?',
                    title:      'Remove All',
                    callback:   function(result) {
                        if(result) {
                            $rows.fadeOut();
                            YOMPUI.utils.throb.start(me.site.state.instance.stop);
                            me.performDelete(instances);
                        }
                        else {
                            $rows.removeClass('bg-danger');
                        }
                    }
                });
            }
        },

        /**
         * User clicked Export All button
         */
        handleExport: function(event) {
            event.stopPropagation();
            event.preventDefault();

            YOMPUI.utils.throb.start(this.site.state.loading);

            this.data.exports.fetch({
                error: function(collection, response, options) {
                    return YOMPUI.utils.modalError(error);
                },
                success: function(collection, response, options) {
                    var blob = new Blob(
                            [ JSON.stringify(collection) ],
                            { type: "text/json;charset=utf-8;" }
                        ),
                        when = (new Date()).toISOString().replace(/[\WT]/g,'').slice(0, 14);

                    YOMPUI.utils.throb.stop();
                    saveAs(blob, 'YOMP-export-' + when + '.json');
                }
            });
        }

    });

})();
