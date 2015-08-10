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

    var viewName = 'instances-auto';

    YOMPUI.InstancesAutoView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#' + viewName + '-tmpl').html()),

        events: {
            'click #begin': 'handleBegin',
            'click #done': 'handleDone'
        },

        // Custom properties

        name: viewName,

        msgs: YOMPUI.msgs(viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        instanceListView:       null,
        setupProgressBarView:   null,
        instanceSelectView:     null,
        modalView:              null,
        regions:                {},

        data: {
            instances:  null,
            models:     null
        },

        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            var collectOpts = {
                    api:    options.api,
                    site:   this.site
                },
                fetchOpts = {
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                };

            this.api = options.api;

            this.data.instances =   new YOMPUI.InstancesCollection([], collectOpts);
            this.data.models =      new YOMPUI.ModelsCollection([], collectOpts);

            YOMPUI.utils.title(this.msgs.title);

            // go setup if they have not yet
            if(! YOMPUI.utils.isAuthorized()) {
                location.href = this.site.paths.welcome;
                return;
            }

            // next get list of AWS regions
            this.api.getRegions(function(error, regions) {
                if(error) return YOMPUI.utils.modalError(error);
                YOMPUI.utils.throb.stop();

                // rename region for display, get rid of extra text at end
                Object.keys(regions).forEach(function(region) {
                    this.regions[region] = regions[region].replace(' Region', '');
                }.bind(this));

                $.when.apply($, [
                    this.data.instances.fetch(fetchOpts),
                    this.data.models.fetch(fetchOpts)
                ]).done(function() {
                    this.render();
                }.bind(this));
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
                    regions: me.regions,
                    button: {
                        done: me.site.buttons.done
                    }
                };

            me.$el.html(me.template(data));

            this.instanceListView = new YOMPUI.InstanceListView({
                el:     $('#instance-list'),
                api:    this.api,
                site:   this.site,
                data: {
                    instances:  this.data.instances,
                    models:     this.data.models
                }
            });
            this.instanceListView.render();

            this.trigger('view-ready');
            return me;
        },

        /**
         *
         */
        handleDone: function(event) {
            var destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        },

        /**
         * This fires when user clicks "Start" button for
         *  Auto Instance-Monitoring Selection process.
         */
        handleBegin: function(event) {
            var me = this,
                $target = $(event.currentTarget),
                region = $('#region').val(),
                tag = $('#tags').val(),
                tags = tag ? tag.split(/[\s,]+/) : [],
                // filter a specific region, or use all regions
                targetRegions = region ? [region] : Object.keys(me.regions),
                targetCount = 0,
                percent = 0,
                regionDetails = [],
                opts,
                filter;

            event.preventDefault();
            event.stopPropagation();

            // The user must select a region
            if (!region) {
                return YOMPUI.utils.modalError(me.msgs.errors.selectRegion);
            }

            YOMPUI.utils.throb.start(me.site.state.instance.find);

            // de-emphasize Start button
            $target.toggleClass('btn-primary btn-default');

            opts = {
            };

            // setup AWS Name Tag filter for API call
            if(tags.length > 0) {
                tags = tags.map(function(tag) {
                    return 'Name:' + tag;
                });
                opts.tags = tags.join(',');
            }

            // loop through target regions and get details for each
            targetRegions.forEach(function(targetRegion) {
                me.api.getInstanceMetrics(
                    targetRegion,
                    "AWS/EC2", // We are only interested in EC2 instances here
                    opts,
                    function(error, results) {
                        if(error) return YOMPUI.utils.modalError(error);

                        regionDetails = regionDetails.concat(results);
                        targetCount++;

                        // update % in throbber
                        percent = Math.round((targetCount / targetRegions.length) * 100);
                        YOMPUI.utils.throb.message(
                            me.site.state.instance.find +
                            ' (' + percent + '%)'
                        );

                        // got through all regions
                        if(targetCount === targetRegions.length) {
                            if(! region) {
                                // all regions + YOMP custom metrics
                                me.api.getYOMPCustomMetrics(function(error, metrics) {
                                    if(error) return YOMPUI.utils.modalError(error);
                                    regionDetails = regionDetails.concat(metrics);
                                    me.displaySelectionModal(regionDetails);
                                });
                            }
                            else {
                                // filter for 1 specific region
                                me.displaySelectionModal(regionDetails);
                            }
                        }
                    }
                );
            });
        },

        /**
         *
         */
        displaySelectionModal: function(data) {
            var me = this,
                instances = {}, // hash of unique instances, contians metric(s)
                sortFn = function(a, b) {
                    var aMod = a.name || a.identifier || '',
                        bMod = b.name || b.identifier || '';
                    if(aMod > bMod) return 1;
                    if(aMod < bMod) return -1;
                    return 0;
                };

            YOMPUI.utils.throb.stop();

            if(data.length <= 0) {
                // no results
                return YOMPUI.utils.modalError(me.msgs.errors.empty);
            }

            data.sort(sortFn).forEach(function(metric) {
                var service = metric.namespace ?
                        metric.namespace : me.site.namespaces.YOMP.custom,
                    region = metric.region ?
                        metric.region :
                        me.site.name + ' ' + me.site.regions.YOMP.custom;

                // prettify
                if(metric.name) {
                    display = metric.name;
                    if(metric.identifier) {
                        display += ' (' + metric.identifier + ')';
                    }
                }
                else if(metric.identifier) {
                    display = metric.identifier;
                }

                // tweak data a little for proper model creation
                if('dimensions' in metric) {
                    Object.keys(metric.dimensions).forEach(function(dimension) {
                        var dim = metric.dimensions[dimension];
                        if(dim instanceof Array) {
                            metric.dimensions[dimension] = dim[0];
                        }
                    });
                }

                // Collapse multiple Metrics down to unique Instances
                if(!(metric.identifier in instances)) {
                    instances[metric.identifier] = {
                        display: display,
                        service: service,
                        region: region,
                        creator: YOMPUI.utils.encodeXmlEntities(
                            JSON.stringify(metric)
                        )
                    };
                }
            });

            /* TODO: Refactor InstanceSelectView and InstanceList, they
                should both be prototyped by a single Instance view: one
                variant for simple selection, the other for
                management/customization/removal/export/etc. */

            // modal
            // TODO: prep data before view, or send to view??
            // select view should be general - not specfici to auto model creation here!
            me.instanceSelectView = new YOMPUI.InstanceSelectView({
                api:        me.api,
                instances:  instances,
                data: {
                    instances:  me.data.instances,
                    models:     me.data.models
                }
            });
            me.instanceSelectView.bind('view-models-created', function() {
                YOMPUI.utils.throb.stop();
                me.data.instances.fetch({
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                });
            });
        }

        // Custom methods

    });

})();
