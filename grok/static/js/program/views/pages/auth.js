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

    YOMPUI.AuthView = Backbone.View.extend({

        template: _.template($('#auth-tmpl').html()),

        msgs: YOMPUI.msgs('auth-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'click #back' : 'handleBack',
            'submit':       'handleFormSubmit'
        },

        ids: {
            back:   '#back',
            button: '#next',
            key:    '#key',
            secret: '#secret'
        },
        previousKey: '',

        initialize: function(options) {
            var me = this,
                settings = {};

            me.api = options.api;

            YOMPUI.utils.title(me.msgs.title);

            // setup? deactive header logo link & hide header setup menu
            if(YOMPUI.utils.isSetupFlow()) {
                $('.navbar-brand').attr('href', '#');
            }

            if(YOMPUI.utils.isAuthorized()) {
                // if logged in with apikey, get previous settings
                me.api.getSettings(
                    me.api.CONST.SETTINGS.SECTIONS.AWS,
                    function(error, settings) {
                        if(error) return YOMPUI.utils.modalError(error);
                        me.previousKey = settings[me.api.CONST.SETTINGS.AWS.KEY];
                        me.render(settings);
                    }
                );
            }
            else {
                // otherwise render empty
                settings[me.api.CONST.SETTINGS.AWS.KEY] = '';
                settings[me.api.CONST.SETTINGS.AWS.SECRET] = '';
                me.render(settings);
            }
        },

        render: function(settings) {
            var me = this,
                step = 2,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    isSetup: YOMPUI.utils.isSetupFlow(),
                    button: {
                        back: me.site.buttons.back,
                        next: YOMPUI.utils.isSetupFlow() ?
                            me.site.buttons.next : (
                                settings[me.api.CONST.SETTINGS.AWS.KEY] ?
                                    me.site.buttons.done : me.site.buttons.save
                            )
                    },
                    values: {
                        key: settings[me.api.CONST.SETTINGS.AWS.KEY],
                        secret: settings[me.api.CONST.SETTINGS.AWS.SECRET]
                    },
                    step: step
                },
                $key,
                setupProgressBar;

            me.$el.html(me.template(data));

            if(YOMPUI.utils.isSetupFlow()) {
                setupProgressBar = YOMPUI.utils.getSetupProgressBar(
                    step, $('#progress-bar-container'));
            }

            // if no data on load, give focus to first field
            $key = $(me.ids.key);
            if(! $key.val()) {
                $key.focus();
            }

            me.trigger('view-ready');
            return me;
        },

        handleBack: function(event) {
            event.stopPropagation();
            event.preventDefault();
            YOMPUI.utils.go(this.site.paths.register + window.location.search);
        },

        handleFormSubmit: function(event) {
            var me = this,
                $key = $(me.ids.key),
                $secret = $(me.ids.secret),
                settings = {},
                destination = null;

            if(YOMPUI.utils.isSetupFlow()) {
                // setup flow
                if(YOMPUI.utils.isExpert()) {
                    // expert setup flow
                    destination = me.site.paths.complete;
                }
                else {
                    // easy setup flow
                    destination = me.site.paths.confirm;
                }
            }
            else {
                // not a setup flow, probably a re-auth, go home after login
                destination = me.site.paths.manage;
            }
            destination += window.location.search;

            event.stopPropagation();
            event.preventDefault();

            $key.parents('.form-group').removeClass('has-error');
            $secret.parents('.form-group').removeClass('has-error');

            // if already entered a key, no form, just next page simply
            if(me.previousKey) {
                YOMPUI.utils.go(destination);
                return;
            }

            YOMPUI.utils.throb.start(me.site.state.auth);

            settings[me.api.CONST.SETTINGS.AWS.KEY] = $key.val();
            settings[me.api.CONST.SETTINGS.AWS.SECRET] = $secret.val();

            // test out creds, see if they work
            me.api.auth(settings, function(error, results) {
                if(error) {
                    if(error.match(/AWS Secret Access Key/)) {
                        // aws auth problem: secret error
                        $secret.parents('.form-group').addClass('has-error');
                        $secret.val('');
                    }
                    else if(error.match(/provided access credentials/)) {
                        // aws auth problem: key error
                        $key.parents('.form-group').addClass('has-error');
                        $key.val('');
                        $secret.parents('.form-group').addClass('has-error');
                        $secret.val('');
                    }
                    return YOMPUI.utils.modalError(error);
                }

                // "login"
                YOMPUI.utils.store.set('apiKey', results.apikey);

                // update API instance with key
                me.api.setApiKey(results.apikey);

                // now that user creds are authed, save them
                me.api.putSettings(
                    settings,
                    me.api.CONST.SETTINGS.SECTIONS.AWS,
                    function(error) {
                        if(error) return YOMPUI.utils.modalError(error);
                        YOMPUI.utils.go(destination);
                    }
                );
            });
        }

    });

})();
