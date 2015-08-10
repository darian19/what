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

    YOMPUI.NotifyView = Backbone.View.extend({

        template: _.template($('#notify-tmpl').html()),

        msgs: YOMPUI.msgs('notify-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'click #back': 'handleBack',
            'submit': 'handleFormSubmit',
        },

        initialize: function(options) {
            var me = this,
                sets = {};

            me.api = options.api;

            YOMPUI.utils.title(me.msgs.title);

            // go setup if they have not yet
            if(! YOMPUI.utils.isAuthorized()) {
                YOMPUI.utils.go(me.site.paths.welcome);
                return;
            }

            // first get notification email addy
            me.api.getSettings(
                me.api.CONST.SETTINGS.SECTIONS.NOTIFY,
                function(error, settings) {
                    if(error) return YOMPUI.utils.modalError(error);

                    sets = settings;

                    // next get AWS default region for SES
                    me.api.getSettings(
                        me.api.CONST.SETTINGS.SECTIONS.AWS,
                        function(error, settings) {
                            if(error) return YOMPUI.utils.modalError(error);

                            $.extend(sets, settings);

                            // last get list of AWS regions for option dropdown list
                            me.api.getRegions(function(error, regions) {
                                if(error) return YOMPUI.utils.modalError(error);

                                // rename region for display, get rid of extra text at end
                                Object.keys(regions).forEach(function(region) {
                                    regions[region] = regions[region].replace(' Region', '');
                                });

                                me.render(sets, regions);
                            });
                        }
                    );
                }
            );
        },

        render: function(settings, regions) {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    button: {
                        back: me.site.buttons.cancel,
                        next: me.site.buttons.save
                    },
                    values: settings,
                    // the following are the only valid SES regions
                    regions: {
                        'eu-west-1': regions['eu-west-1'],
                        'us-east-1': regions['us-east-1'],
                        'us-west-2': regions['us-west-2']
                    }
                };

            me.$el.html(me.template(data));

            me.trigger('view-ready');
            return me;
        },

        handleBack: function(event) {
            var from = YOMPUI.utils.getUrlParam('from') || 'method',
                destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        },

        handleFormSubmit: function(event) {
            var me = this,
                settings = {},
                sender = $('#sender').val(),
                region = $('#region').val(),
                destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            settings[me.api.CONST.SETTINGS.NOTIFY.SENDER] = sender;

            // first, save notification email address for ses
            me.api.putSettings(
                settings,
                me.api.CONST.SETTINGS.SECTIONS.NOTIFY,
                function(error) {
                    if(error) return YOMPUI.utils.modalError(error);

                    settings = {};
                    settings[me.api.CONST.SETTINGS.AWS.REGION] = region;

                    // last, save aws default region for ses
                    me.api.putSettings(
                        settings,
                        me.api.CONST.SETTINGS.SECTIONS.AWS,
                        function(error) {
                            if(error) return YOMPUI.utils.modalError(error);

                            YOMPUI.utils.go(destination);
                        }
                    );
                }
            );
        }

    });

})();
