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

    YOMPUI.ManageCustomMetricsView = Backbone.View.extend({

        template: _.template($('#manage-custom-metrics-tmpl').html()),

        msgs: YOMPUI.msgs('manage-custom-metrics-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'click #done':                  'handleDone',
            'click td button.close':        'handleDeleteOne',
            'click .delete':            'handleDeleteAll'
        },

        initialize: function(options) {
            var me = this,
                collectOpts = {
                    api:    options.api,
                    site:   me.site
                };
            me.fetchOpts = {
                error: function(collection, response, options) {
                    return YOMPUI.utils.modalError(response);
                }
            }; 
            me.api = collectOpts.api;
            me.customMetrics = new YOMPUI.YOMPCustomMetricsCollection([], collectOpts);

            YOMPUI.utils.title(me.msgs.title);

            // Redirect user to setup if they haven't done so yet.
            if(! YOMPUI.utils.isAuthorized()) {
                YOMPUI.utils.go(me.site.paths.welcome);
                return;
            };


            YOMPUI.utils.throb.start(me.site.state.loading);

            // get all the data in parallel
            $.when.apply($, [
                me.customMetrics.fetch(me.fetchOpts)
            ]).done(function() {
                YOMPUI.utils.throb.stop();
                me.render();
            }.bind(me));


        },

        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    metrics: me.customMetrics,
                    opacityMsg: ''
                };

            if(me.customMetrics.length > 0) {
                data.opacityMsg = 'opacity:1'
                $('.tablesorter').tablesorter();
            }
            else {
                // no metrics, mute listing
                data.opacityMsg = 'opacity:0.5'
            }

            me.$el.html(me.template(data));

            me.trigger('view-ready');
            return me;
        }, 

        /**
         * User clicked done button. Send user back to manage page.
         */
        handleDone: function(event) {
            var destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        },

        /**
         * User clicked delete button on 1 metric
         */
        handleDeleteOne: function(event) {
            var me = this,
                $row = $(event.currentTarget).parents('tr'),
                name = $row.data('name');

            event.stopPropagation();
            event.preventDefault();

            $row.addClass('bg-danger');

            display = '<code class="truncate">' + name + '</code>';

            // ask user to confirm metric delete
            bootbox.confirm({
                animate:    false,
                message:    '<div>Delete this custom metric from YOMP?</div>' + display + '<br/><div>WARNING: This will also delete any models associated with this data.</div>',
                title:      'Delete',
                callback:   function(result) {
                    if(result) {
                        $row.fadeOut();
                        YOMPUI.utils.throb.start(me.site.state.metric.remove);
                        handler = me.api.deleteYOMPCustomMetric(
                            name,
                            function(error, results) {
                                if(error) {
                                    if (handler.status != 404) return YOMPUI.utils.modalError(error);
                                }
                                $.when.apply($, [
                                                me.customMetrics.fetch(me.fetchOpts)
                                            ]).done(function() {
                                                YOMPUI.utils.throb.stop();
                                                me.render();
                                            });
                            }
                        );


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
                $rows = me.$el.find('.metrics > tr'),
                metricList = [],
                metricCount = 0;

            event.stopPropagation();
            event.preventDefault();

            $rows.addClass('bg-danger');

            $rows.each(function() {
                var metricName = $(this).data('name');
                if(metricName) {
                    metricList.push(metricName);
                }
            });
            
            if(metricList.length > 0) {
                // ask user to confirm delete all metrics
                bootbox.confirm({
                    animate:    false,
                    message:    'Delete all custom metrics from YOMP?<br/><br/>WARNING: This will also delete any models associated with this data.',
                    title:      'Delete All',
                    callback:   function(result) {
                        if(result) {
                            $rows.fadeOut();
                            YOMPUI.utils.throb.start(me.site.state.metric.remove);

                            metricList.forEach(function(metricName) {
                                handler = me.api.deleteYOMPCustomMetric(
                                    metricName,
                                    function(error, results) {
                                        if(error) {
                                            if (handler.status != 404) return YOMPUI.utils.modalError(error);
                                        }

                                        metricCount++;

                                        // update % in throbber
                                        percent = Math.round((metricCount / metricList.length) * 100);
                                        YOMPUI.utils.throb.message(
                                            me.site.state.metric.remove +
                                            ' (' + percent + '%)'
                                        );

                                        // got through all regions
                                        if(metricCount === metricList.length) {
                                            $.when.apply($, [
                                                me.customMetrics.fetch(me.fetchOpts)
                                            ]).done(function() {
                                                YOMPUI.utils.throb.stop();
                                                me.render();
                                            });
                                        }
                                    }
                                );
                            });
                        }
                        else {
                            $rows.removeClass('bg-danger');
                        }
                    }
                });
            }
        }

    });

})();
