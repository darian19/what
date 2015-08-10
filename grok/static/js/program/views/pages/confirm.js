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

    YOMPUI.ConfirmView = Backbone.View.extend({

        template: _.template($('#confirm-tmpl').html()),

        msgs: YOMPUI.msgs('confirm-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'click #back' : 'handleBack',
            'click #next':  'handleNext'
        },

        ids: {
            back:   '#back',
            button: '#next'
        },

        initialize: function(options) {
            var me = this,
                region = YOMPUI.utils.getUrlParam('region');

            me.api = options.api;

            YOMPUI.utils.title(me.msgs.title);

            // setup? deactive header logo link & hide header setup menu
            if(YOMPUI.utils.isSetupFlow()) {
                $('.navbar-brand').attr('href', '#');
            }

            YOMPUI.utils.throb.start(this.site.state.instance.find);

            // Next, get suggested instances from instances API
            me.api.getInstanceSuggestions(region, function(error, result) {
                if(error) return YOMPUI.utils.modalError(error);
                YOMPUI.utils.throb.stop();
                suggestions = JSON.parse(result);

                var clickHandler = function(checked) {
                    // Enable/Disable next button conditional upon selected instances
                    if (!checked) {
                        if (!$('#confirmed-instances input:checked').length) {
                            $('#next').prop('disabled', true);
                        }
                    } else {
                        $('#next').prop('disabled', false);
                    }
                };

                // Add suggested (checked)
                Object.keys(suggestions.suggested).forEach(function(idx) {
                    var $parent = $('#'+suggestions.suggested[idx].namespace.split('/')[1]+'-instances'),
                        view = new YOMPUI.SuggestedInstancesListView({
                            instance: suggestions.suggested[idx],
                            region:   suggestions.suggested[idx].region,
                            checked:  'checked'
                        });

                    view.on('click', clickHandler);
                    view.render();
                    $parent.append(view.$el);
                    $('#next').prop('disabled', false);
                });

                // Add alternates (unchecked)
                Object.keys(suggestions.alternates).forEach(function(idx) {
                    var $parent = $('#'+suggestions.alternates[idx].namespace.split('/')[1]+'-instances'),
                        view = new YOMPUI.SuggestedInstancesListView({
                            instance: suggestions.alternates[idx],
                            region:   suggestions.alternates[idx].region,
                            checked:  ''
                        });

                    view.on('click', clickHandler);

                    view.render();
                    $parent.append(view.$el);
                });

                $("div[id$=-instances]").each(function(idx, section) {
                    if (!$(section).children().length) {
                        var view = new YOMPUI.NoSuggestedInstancesView().render();
                        $(section).append(view.$el);
                    }

                });
            });

            me.render();
        },

        render: function(settings) {
            var me = this,
                step = 3,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    isSetup: YOMPUI.utils.isSetupFlow(),
                    button: {
                        back: me.site.buttons.back,
                        next: me.site.buttons.next
                    },
                    values: {},
                    step: step,
                    region: YOMPUI.utils.getUrlParam('region')
                },
                setupProgressBar;

            me.$el.html(me.template(data));

            if(YOMPUI.utils.isSetupFlow()) {
                setupProgressBar = YOMPUI.utils.getSetupProgressBar(
                    step,
                    $('#progress-bar-container'));
            }

            me.trigger('view-ready');

            return me;
        },

        handleBack: function(event) {
            event.stopPropagation();
            event.preventDefault();
            YOMPUI.utils.go(this.site.paths.auth + window.location.search);
        },

        handleNext: function(event) {
            var me = this,
                settings = {},
                counter = 0,
                destination = YOMPUI.utils.isSetupFlow() ?
                    me.site.paths.register + me.site.urltag.setup :
                    me.site.paths.manage;

            YOMPUI.utils.throb.start(this.site.state.instance.starts);

            event.stopPropagation();
            event.preventDefault();

            var lastError = false;
            var requests = [];

            // Group instances by namespace to batch up requests
            var instancesGroupedByNamespace = _.groupBy($('#confirmed-instances input:checked'), function(input) {
                var instance = $(input).val();
                return instance.substring(0, instance.lastIndexOf('/'));
            });

            // Select instances in batches
            _.each(_.keys(instancesGroupedByNamespace), function(key) {
                // Extract only the instance ids for the request body
                var instanceIds = _.map(instancesGroupedByNamespace[key], function(input) {
                    var instance = $(input).val();
                    return instance.substring(instance.lastIndexOf('/') + 1);
                });

                // Partition key into region, and namespace
                var partitionAt = key.indexOf('/');
                var region = key.substring(0, partitionAt),
                    namespace = key.substring(partitionAt + 1);

                // FIXME: MER-3135 - Avoid sending more than 1 instance per request
                _.each(instanceIds, function(instance) {
                    requests.push(
                        me.api.selectInstances(region,
                            namespace,
                            [instance],
                            null
                        )
                    );
                });
            });

            // Use jQuery "when" to force request callbacks to be called synchronously.
            $.when.apply($, requests).
                done(function(args) {
                    YOMPUI.utils.go(me.site.paths.complete + window.location.search);
                }).
                fail(function(args) {
                    YOMPUI.utils.throb.stop();
                    var res = args.responseJSON.result;
                    if (res) {
                        var quota = /Server limit exceeded;.*edition=(\w+);.+limit=(\d+)\./;
                        var edition = res.match(quota)[1],
                            capacity = res.match(quota)[2];
                        return YOMPUI.utils.modalWarning("Sorry!",
                                                         _.template(me.msgs.errors[edition.toLowerCase()])({capacity: capacity}),
                                                         _.bind(YOMPUI.utils.go, me, me.site.paths.complete + window.location.search));
                    }
                });
        }

    });

})();
