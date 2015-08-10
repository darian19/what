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

    var viewName = 'autostack';

    YOMPUI.AutostackView = Backbone.View.extend({

        name: viewName,

        template: _.template($('#' + viewName + '-tmpl').html()),

        msgs: YOMPUI.msgs(viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'submit': 'handleBegin',
            'click #done': 'handleDone'
        },

        initialize: function(options) {
            var me = this;
            me.api = options.api;

            // view refs
            me.instanceListView = null;
            me.instanceSelectView = null;
            me.modalView = null;

            me.regions = {};
            me.namespaces = {
                'AWS/EC2': {
                    metrics: []
                }
            };

            YOMPUI.utils.title(me.msgs.title);

            // go setup if they have not yet
            if(! YOMPUI.utils.isAuthorized()) {
                location.href = me.site.paths.welcome;
                return;
            }

            // prep a list of default AWS/EC2 metrics and dimensions for later
            me.api.getNamespaceDetails('AWS/EC2', function(error, nsdetails) {
                if(error) return YOMPUI.utils.modalError(error);
                me.namespaces['AWS/EC2'].metrics = nsdetails['AWS/EC2'].metrics;
            });

            // next get list of AWS regions
            me.api.getRegions(function(error, regions) {
                if(error) return YOMPUI.utils.modalError(error);
                YOMPUI.utils.throb.stop();

                // rename region for display, get rid of extra text at end
                Object.keys(regions).forEach(function(region) {
                    me.regions[region] = regions[region].replace(' Region', '');
                });
                me.render();
            });
        },

        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    regions: me.regions,
                    button: {
                        start: me.msgs.form.buttons.find,
                        done: me.site.buttons.done
                    }
                },
                $name = null,
                $tags = null,
                $begin = null,
                $region = null;

            me.$el.html(me.template(data));

            $name = $('#name');
            $tags = $('#tags');
            $begin = $('#begin');
            $region = $('#region');

            // Disable name, tags until region is selected
            $name.attr("disabled", "disabled");
            $tags.attr("disabled", "disabled");
            $begin.attr("disabled", "disabled");
            $region.change(function(e) {
                if ($(e.target).find(":selected").text() == me.msgs.form.defaults.region) {
                    $name.attr("disabled", "disabled");
                    $tags.attr("disabled", "disabled");
                    $begin.attr("disabled", "disabled");
                } else {
                    $name.removeAttr("disabled");
                    $tags.removeAttr("disabled");
                    $begin.removeAttr("disabled");
                }
            })

            this.instanceListView = new YOMPUI.InstanceListView({
                el:     $('#instance-list'),
                api:    this.api,
                site:   this.site
            });
            this.instanceListView.render();

            me.trigger('view-ready');
            return me;
        },

        handleDone: function(event) {
            var destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        },

        /**
         * This fires when user clicks "Create" button for making and monitoring
         *  a new AutoStack.
         */
        handleBegin: function(event) {
            var me = this,
                name = $('#name').val(),
                region = $('#region').val(),
                tags = $('#tags').val(),
                filters = tags.split(/\s*&&\s*/).map(function(tag) {

                    var tagName = '';
                    var buffer = '';
                    var values = [];

                    // Partition at : not prefixed with \ to define tag name'
                    for (var i = 0, len = tag.length, previous = ''; i < len; i++) {
                        if (tag[i] == '\\' && (tag[i+1] == ':' || tag[i+1] == ',' || tag[i+1] == '&')) {
                            previous = tag[i];
                            i++;
                        }
                        if (tag[i] === ':' && previous != '\\') {
                            tagName = buffer;
                            buffer = '';
                            previous = tag[i];
                            i++;
                            break;
                        }
                        buffer = buffer + tag[i];
                        previous = tag[i];
                    }

                    if (tagName.length == 0) {
                        tagName = 'Name'; // No tag specified, default to Name
                        i=0; // Reset position in `tag`
                    }

                    // Partition at , not prefixed with \ to create list of values
                    for (var len = tag.length, buffer='', previous = ''; i < len; i++) {
                        if (tag[i] == '\\' && (tag[i+1] == ':' || tag[i+1] == ',' || tag[i+1] == '&')) {
                            previous = tag[i];
                            i++;
                        }
                        if (tag[i] === ',' && previous != '\\') {
                            values.push(buffer);
                            buffer = '';
                            previous = tag[i];
                            continue;
                        }
                        buffer = buffer + tag[i];
                        previous = tag[i];
                    }

                    if (buffer.length > 0) {
                        values.push(buffer);
                    }

                    return ['tag:' + tagName, values];
                }),

                $target = $(event.currentTarget),
                $button = $target.find('button'),
                targetCount = 0,
                percent = 0,
                filterOutput = filters.map(function(filter) {
                    return filter[0] + ':' + filter[1];
                });

            // Reduce filters from list of lists to dictionary
            var collapsedFilters = {};
            filters.forEach(function(filter) {
                if (collapsedFilters[filter[0]] == undefined) {
                    collapsedFilters[filter[0]] = []
                }
                filter[1].forEach(function(value) {
                    collapsedFilters[filter[0]].push(value)
                });
            });

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.throb.start(me.site.state.instance.find);

            me.api.getAutostackPreview(
                region,
                collapsedFilters,
                function(error, results) {
                    if(error) return YOMPUI.utils.modalError(error);

                    var instanceOutput = results.map(function(instance) {
                        var name = instance.tags.Name,
                            id = instance.instanceID;

                        return name ? (name + " (" + id + ")") : id;
                    }),
                    desc = [
                        '<p class="lead">Based on your criteria we found the following servers to include in this Autostack. Do you want to create?</p>',
                        '<dl>',
                        '<dt>' + me.msgs.form.labels.name + '</dt><dd>' + name + '</dd>',
                        '<dt>' + me.msgs.form.labels.region + '</dt><dd>' + region + '</dd>',
                        '<dt>' + me.msgs.form.labels.tags + '</dt><dd>' + filterOutput.join(' <span class="text-muted">&amp;&amp;</span> ') + '</dd>',
                        '<hr>' +
                        '<dt>' + me.msgs.form.labels.instances + '</dt><dd>' + instanceOutput.join(' <br> ') + '</dd>',
                        '</dl>'
                    ].join('');

                    YOMPUI.utils.throb.stop();

                    bootbox.confirm({
                        animate: false,
                        message: desc,
                        title: 'Instances that will be included in the Autostack',
                        buttons: {
                            cancel: {
                                label: me.site.buttons.cancel,
                                className: 'btn-default'
                            },
                            confirm: {
                                label: me.site.buttons.create,
                                className: 'btn-primary'
                            }
                        },
                        callback: function(result) {
                            if(result) {
                                YOMPUI.utils.throb.start(me.site.state.instance.starts);
                                me.createAutostack(name, region, collapsedFilters);
                            }
                        }
                    });
                }
            );

        },

        /**
         * Create autostack
         * TODO: doc
         * @param name
         * @param region
         * @param filters
         */
        createAutostack: function(name, region, filters) {
            var me = this;

            me.api.createAutostack(
                name,
                region,
                filters,
                function(error, results) {
                    if(error) return YOMPUI.utils.modalError(error);

                    var metrics = me.namespaces['AWS/EC2'].metrics.filter(function(metric) {
                        // Select only specific default metrics
                        return (metric == 'CPUUtilization' ||
                                metric == 'DiskWriteBytes' ||
                                metric == 'NetworkIn');
                    }).map(function(metric) {
                        // Map to format expected by Autostack metrics endpoint
                        return  {
                            namespace:  'AWS/EC2',
                            metric:     metric
                        };
                    });

                    // associate default AWS/EC2 metrics to autostack
                    me.api.createAutostackMetrics(
                        results.uid,
                        metrics,
                        function(error) {
                            if(error) return YOMPUI.utils.modalError(error);

                            // clear out entry fields
                            $('#region').val('').focus();
                            $('#name').val('');
                            $('#name').attr("disabled", "disabled");
                            $('#tags').val('');
                            $('#tags').attr("disabled", "disabled");
                            $('#begin').attr("disabled", "disabled");

                            // add manually to clientside collection
                            me.instanceListView.data.autostacks.add({
                                id:         results.uid,
                                filters:    filters,
                                name:       name,
                                region:     region,
                                uid:        results.uid
                            });

                            // all done
                            me.instanceListView.data.instances.fetch({
                                error: function(collection, response, options) {
                                    return YOMPUI.utils.modalError(response);
                                },
                                success: function(collection, response, options) {
                                    YOMPUI.utils.throb.stop();
                                }
                            });
                        }
                    );

                }
            );
        }

    });

})();
