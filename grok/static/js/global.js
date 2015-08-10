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

    $(document).ready(function() {

        // kick off backbone client side routing
        YOMPUI.router = new YOMPUI.Router();
        Backbone.history.start({
            hashChange: false,
            pushState:  'pushState' in window.history,
            root:       NTA.baseUrl
        });

        // preload necessary ui images
        ['/static/img/mark.svg'].forEach(function(img) {
            $('<img />').attr('src', img).addClass('off').appendTo('body');
        });

        // when views are finished rendering
        YOMPUI.loader.on('finished', function() {

            // only once, not after
            YOMPUI.loader.off('finished');

            // Add handler for Help header link
            $('.navbar .nav > .help').click(YOMPUI.utils.help.show);

            // if this is an embeddable widget request
            if(
                window.location.pathname.match(/\/embed/) &&
                YOMPUI.utils.getUrlParam('hash')
            ) {
                // skip everything else after this point, not necessary
                return;
            }

            // not setup flow, not welcome page, so...
            if(
                (! YOMPUI.utils.isSetupFlow()) &&
                (! window.location.href.match(/welcome/))
            ) {
                // ...so show full header
                $('.navbar .nav > .hidden').removeClass('hidden');
            }

            // make sure they can use api
            if(YOMPUI.utils.isAuthorized()) {
                var apiOpts = {
                        apiKey: YOMPUI.utils.store.get('apiKey')
                    },
                    api = new YOMPAPI(apiOpts);

                // warn user if updates are available
                api.getUpdate(function(error, results) {
                    if(error) return YOMPUI.utils.modalError(error);
                    if(results.result) {
                        YOMPUI.loader.loadResources(
                            {
                                scripts:    [
                                    NTA.baseUrl + '/static/js/program/views/panels/alertUpdate.js'
                                ],
                                css: [
                                    NTA.baseUrl + '/static/css/panels/alertUpdate.css'
                                ],
                                templates: {
                                    'alert-update-tmpl': NTA.baseUrl + '/static/js/program/templates/panels/alertUpdate.html'
                                },
                                msgs: ['site']
                            },
                            function() {
                                var view = new YOMPUI.AlertUpdateView({
                                    el: $('#alert .text'),
                                    api: new YOMPAPI({
                                        apiKey: YOMPUI.utils.store.get('apiKey')
                                    })
                                });
                            }
                        ); // YOMPUI.loader.loadResources
                    } // if
                }); // api.getUpdate()

                // user can allow/revoke tech support access from menu
                api.getSupportAccess(function(error, results) {
                    var $target = $('header .nav ul.dropdown-menu'),
                        $enable = $target.find('#support-access-enable');
                        doEnable = function() {
                            $enable.parent().addClass('off');
                            $disable.parent().removeClass('off');
                        },
                        $disable = $target.find('#support-access-disable'),
                        doDisable = function() {
                            $enable.parent().removeClass('off');
                            $disable.parent().addClass('off');
                        };

                    if(error) return YOMPUI.utils.modalError(error);

                    if(results.result) doEnable();
                    else doDisable();

                    $enable.on('click', function(event) {
                        api.setSupportAccess(function(error) {
                            if(error) return YOMPUI.utils.modalError(error);
                            doEnable();
                        });
                    });
                    $disable.on('click', function(event) {
                        api.removeSupportAccess(function(error) {
                            if(error) return YOMPUI.utils.modalError(error);
                            doDisable();
                        });
                    });
                }); // api.getSupportAccess()

            } // if authed user

        }); // YOMPUI loader on finished

    }); // document ready

})();
