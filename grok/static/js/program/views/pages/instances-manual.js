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

    var viewName = 'instances-manual';

    /**
     * YOMP Manual Instance Selection Backbone.View
     */
    YOMPUI.InstancesManualView = Backbone.View.extend({

        // Backbone.View properties

        name:       viewName,
        template:   _.template($('#' + viewName + '-tmpl').html()),

        events: {
            'click #done': 'handleDone'
        },

        // Custom properties

        msgs: YOMPUI.msgs(viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        // complex internal data tree: AWS Regions > Namespaces > Instances > Metrics
        regions: {},
        // simple external data structure for jqTree jQuery plugin
        tree: [],
        // backbone view for instance list
        instanceListView: null,

        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            var api = options.api,
                collectOpts = {
                    api:    api,
                    site:   this.site
                },
                fetchOpts = {
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(response);
                    }
                };

            this.api = collectOpts.api;
            this.data = {
                monitored: {
                    instances:  new YOMPUI.InstancesCollection([], collectOpts),
                    models:     new YOMPUI.ModelsCollection([], collectOpts)
                },
                source: {
                    aws: {
                        metrics:    new YOMPUI.AwsMetricsCollection([], collectOpts),
                        namespaces: new YOMPUI.AwsNamespacesCollection([], collectOpts),
                        regions:    new YOMPUI.AwsRegionsCollection([], collectOpts)
                    },
                    YOMP: {
                        autostacks: new YOMPUI.YOMPAutostacksCollection([], collectOpts),
                        customs:    new YOMPUI.YOMPCustomMetricsCollection([], collectOpts)
                    }
                }
            };

            YOMPUI.utils.title(this.msgs.title);

            // go setup if they have not yet
            if(! YOMPUI.utils.isAuthorized()) {
                YOMPUI.utils.go(this.site.paths.welcome);
                return;
            }

            YOMPUI.utils.throb.start(this.site.state.loading);

            // get all the data in parallel
            $.when.apply($, [
                this.data.monitored.instances.fetch(fetchOpts),
                this.data.monitored.models.fetch(fetchOpts),
                this.data.source.aws.regions.fetch(fetchOpts),
                this.data.source.aws.namespaces.fetch(fetchOpts),
                this.data.source.YOMP.autostacks.fetch(fetchOpts),
                this.data.source.YOMP.customs.fetch(fetchOpts)
            ]).done(function() {
                // now we have all the data

                // map data into UI data structures
                this.processYOMPCustomMetrics(this.data.source.YOMP.customs);
                this.processAwsRegionsNamespaces(
                    this.data.source.aws.regions,
                    this.data.source.aws.namespaces
                );

                YOMPUI.utils.throb.stop();
                this.render();
            }.bind(this));
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    button: {
                        done: me.site.buttons.done
                    }
                },
                $tree,
                instanceList;

            me.$el.html(me.template(data));

            // left/top side - tree nav
            $tree = $('#network-tree');
            $tree.tree({
                data: me.tree,
                autoEscape: false,
                useContextMenu: false,
                onCreateLi: function(node, $li) {
                    $li.find('.jqtree-title').addClass('truncate');
                },
                onCanSelectNode: function(node) {
                    return node.children.length === 0;
                }
            });
            $tree.bind('tree.click', function(event) {
                var node = event.node,
                    children = node.children;

                if(children.length > 0) {
                    // this makes full titles function just like toggle switches
                    event.preventDefault();
                    $tree.tree('toggle', node);
                }
            });
            $tree.bind('tree.open', function(event) {
                var node = event.node;
                if(
                    node.parent &&
                    ('parent' in node.parent) &&
                    node.parent.parent
                ) {
                    if(node.parent.type === me.site.regions.type.aws) {
                        me.getAWSRegionNamespaceDetails(
                            node.parent.id,
                            node.id,
                            node,
                            $tree
                        );
                    }
                }
            });
            $tree.bind('tree.select', function(event) {
                var node =      event.node,
                    name =      node.name,
                    instance =  node.id.split('/').pop(),
                    namespace = node.parent.name,
                    region =    node.parent.parent.id;

                // start monitoring real aws instance
                if(namespace.match(me.site.namespaces.aws.real)) {
                    var id = [region, namespace, node.id].join('/'),
                        data = {
                            location:   region,
                            namespace:  namespace,
                            _server:    id
                        };

                    YOMPUI.utils.throb.start(me.site.state.instance.start);

                    if(me.data.monitored.instances.where(_.chain(data)
                                                          .omit("_server")
                                                          .extend({"server": id})
                                                          .value()).length > 0) {
                        $tree.tree('selectNode', null);
                        return YOMPUI.utils.modalError('This instance is already being monitored.');
                    }

                    // add features to model before creation
                    data.instance = node.id;
                    data.name =     name;

                    // monitor new instance (metric models)
                    me.data.monitored.instances.create(data, {
                        error: function(model, response, options) {
                            $tree.tree('selectNode', null);
                            return YOMPUI.utils.modalError(response);
                        },
                        success: function(model, response, options) {
                            $tree.tree('selectNode', null);
                            YOMPUI.utils.throb.stop();
                        }
                    });
                }
                // or, start monitoring YOMP custom metric
                else if(namespace.match(me.site.namespaces.YOMP.custom)) {
                    var metrics =
                            me.regions[region].
                            namespaces[namespace].
                            instances[instance].
                            metrics,
                        metric = Object.keys(metrics)[0],
                        creator = metrics[metric],
                        newModel = {
                            datasource: creator.get('datasource'),
                            metric:     metric
                        },
                        filter = {
                            display:    metric,
                            server:     metric
                        };

                    YOMPUI.utils.throb.start(me.site.state.metric.start);

                    if(me.data.monitored.instances.where(filter).length > 0) {
                        $tree.tree('selectNode', null);
                        return YOMPUI.utils.modalError('This instance is already being monitored.');
                    }

                    // create new metric model
                    me.data.monitored.models.create(newModel, {
                        error: function(model, response, options) {
                            $tree.tree('selectNode', null);
                            return YOMPUI.utils.modalError(response);
                        },
                        success: function(model, response, options) {
                            $tree.tree('selectNode', null);
                            me.data.monitored.instances.fetch({
                                error: function(collection, response, options) {
                                    return YOMPUI.utils.modalError(error);
                                },
                                success: function(collection, response, options) {
                                    YOMPUI.utils.throb.stop();
                                }
                            });
                        }
                    });
                }
            });

            // right/bottom side - instance list
            this.instanceListView = new YOMPUI.InstanceListView({
                el:     $('#instance-list'),
                api:    this.api,
                site:   this.site,
                data: {
                    autostacks: this.data.source.YOMP.autostacks,
                    customs:    this.data.source.YOMP.customs,
                    instances:  this.data.monitored.instances,
                    metrics:    this.data.source.aws.metrics,
                    models:     this.data.monitored.models,
                    namespaces: this.data.source.aws.namespaces
                }
            });
            this.instanceListView.render();

            this.trigger('view-ready');
            return me;
        },

        // Custom methods

        /**
         * Map AWS Region+Namespace data into UI data structures
         */
        processAwsRegionsNamespaces: function(regions, namespaces) {
            var me = this;

            // hide autostack namespace
            namespaces = namespaces.without(namespaces.get('Autostacks'));

            // post-process aws region data
            regions.forEach(function(region) {
                // populate regions in internal data structure
                me.regions[region.id] = {
                    name:       region.get('name'),
                    type:       me.site.regions.type.aws,
                    namespaces: {}
                };

                // populate namespaces in internal data structure
                namespaces.forEach(function(namespace) {
                    me.regions[region.id].namespaces[namespace.id] =
                        namespace.toJSON();
                    me.regions[region.id].namespaces[namespace.id].instances = {};
                });

                // populate regions in external data structure for jqTree
                me.tree.push({
                    label:  region.get('name'),
                    id:     region.id,
                    type:   me.site.regions.type.aws,
                    children: namespaces.map(function(namespace) {
                        return {
                            label:      namespace.id,
                            id:         namespace.id,
                            children: [{
                                label: '<em class="text-muted">' +
                                    me.site.state.loading + '…</em>'
                            }]
                        };
                    })
                });
            });
        },

        /**
         * Map YOMP Custom Metric data into UI data structures
         */
        processYOMPCustomMetrics: function(metrics) {
            var me = this,
                displayName = '<strong>' + me.site.name + '</strong>: ' +
                    me.site.regions.YOMP.custom,
                namespaces,
                instances;

            if(metrics.length) {
                // top-level "YOMP" Custom Metrics pseudo-Region
                me.regions[me.site.name] = {
                    name: me.site.regions.YOMP.custom,
                    type: me.site.regions.type.YOMP,
                    namespaces: {}
                };

                // "Custom YOMP" namespace below that
                namespaces = me.regions[me.site.name].namespaces;
                namespaces[me.site.namespaces.YOMP.custom] = {
                    instances: {}
                };

                // YOMP Custom Metrics are the Instances in this case
                instances = namespaces[me.site.namespaces.YOMP.custom].instances;
                metrics.forEach(function(metric) {
                    var name = metric.get('name');
                    instances[name] = {
                        metrics: {}
                    };
                    instances[name].metrics[name] = metric;
                });

                // populate YOMP custom metrics in external data structure for jqTree
                me.tree.push({
                    label: displayName,
                    id: me.site.name,
                    type: me.site.regions.type.YOMP,
                    children: [{
                        label: me.site.namespaces.YOMP.custom,
                        children: metrics.map(function(metric) {
                            return {
                                label:  metric.get('name'),
                                id:     metric.get('name')
                            };
                        })
                    }]
                });
            }
        },

        /**
         *
         */
        getAWSRegionNamespaceDetails: function(region, namespace, node, $tree) {
            var me = this,
                newTree = [],
                parent = me.regions[region].namespaces[namespace].instances,
                regionNamespaceFilter = {
                    region:     region,
                    namespace:  namespace
                },
                regionNamespaceMetrics = me.data.source.aws.metrics.where(regionNamespaceFilter),
                collapseDataToTree = function(collection) {
                    YOMPUI.utils.throb.stop();

                    collection = collection.where(regionNamespaceFilter);

                    if(collection.length > 0) {
                        collection.forEach(function(result) {
                            var namespace = result.get('namespace'),
                                dimension = Object.keys(result.get('dimensions'))[0],
                                instance = dimension + "/" + result.get('identifier'),
                                name = result.get('name'),
                                metric = result.get('metric'),
                                display = result.get('display'),
                                origin = {
                                    instance:   {},
                                    metric:     {}
                                };

                            // populate instances in internal data structure
                            origin.instance = parent;
                            if(!(instance in origin.instance)) {
                                origin.instance[instance] = {
                                    id:         instance,
                                    display:    display,
                                    name:       name,
                                    metrics:    {}
                                };
                            }

                            // populate metrics in internal data structure
                            origin.metric = origin.instance[instance].metrics;
                            if(!(metric in origin.metric)) {
                                origin.metric[metric] = result;
                            }
                        });

                        // transform instances to external data structure
                        if(Object.keys(parent).length > 0) {
                            Object.keys(parent).forEach(function(instance) {
                                newTree.push({
                                    id:         instance,
                                    name:       parent[instance].display,
                                    label:      parent[instance].display,
                                    instance:   parent[instance].name
                                });
                            });
                        }
                    }
                    else {
                        newTree.push({
                            label: '<em class="flash-danger">' +
                                    'No Services Found</em>'
                        });
                    }

                    newTree.sort(function(a, b) {
                        if(a.label > b.label) return 1;
                        if(a.label < b.label) return -1;
                        return 0;
                    });

                    YOMPUI.utils.throb.stop();

                    $tree.tree('loadData', newTree, node);
                };

            if(Object.keys(parent).length > 0) { return; }

            YOMPUI.utils.throb.start(me.site.state.loading);

            if(regionNamespaceMetrics.length <= 0) {
                // Metric data for this region not loaded yet, do so.

                YOMPUI.utils.throb.start(me.site.state.loading);

                me.data.source.aws.metrics.fetch({
                    region:     region,
                    namespace:  namespace,
                    remove:     false,
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(response);
                    },
                    success: collapseDataToTree
                });
            }
            else {
                // Metric data for this region already loaded, continue.
                collapseDataToTree(me.data.source.aws.metrics);
            }
        },

        /**
         *
         */
        handleDone: function(event) {
            var destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        }

    });

})();
