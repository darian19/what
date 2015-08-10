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

    var BASE_URL = NTA.baseUrl;

    // global messages to load on every page
    var _messages = ['site'];

    // global view options
    var _viewOpts = {
        el: $('#content'),
        api: new YOMPAPI({
            apiKey: YOMPUI.utils.store.get('apiKey') || YOMPUI.apiKey
        })
    };


    YOMPUI.routes = {

        urls: {
            // first time user Setup flow
            'YOMP/auth':                'auth',
            'YOMP/complete':            'complete',
            'YOMP/confirm':             'confirm',
            'YOMP/instances/auto':      'instances-auto',
            'YOMP/instances/autostack': 'autostack',
            'YOMP/instances/import':    'instances-import',
            'YOMP/instances/manual':    'instances-manual',
            'YOMP/custom':              'manage-custom-metrics',
            'YOMP/complete':            'complete',
            'YOMP/notify':              'notify',
            'YOMP/register':            'register',
            'YOMP/terms':               'terms',
            'YOMP/welcome':             'welcome',

            // returning user home page Manage Instances
            'YOMP': 'manage',

            // embed widgets
            'YOMP/embed/charts': 'charts',

            // problems
            '404':  'notFound',
            '*url': 'notFound'
        },

        deps: {

            pages: {

                // first time user Setup flow

                auth: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/auth.js',
                        BASE_URL + '/static/js/program/views/panels/setupProgressBar.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/auth.css',
                        BASE_URL + '/static/css/panels/setupProgressBar.css'
                    ],
                    templates: {
                        'auth-tmpl':                BASE_URL + '/static/js/program/templates/pages/auth.html',
                        'setup-progress-bar-tmpl':  BASE_URL + '/static/js/program/templates/panels/setupProgressBar.html'
                    }
                },

                'autostack': {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/autostack.js',

                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/autostack.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css'
                    ],
                    templates: {
                        'autostack-tmpl':           BASE_URL + '/static/js/program/templates/pages/autostack.html',
                        'instance-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':   BASE_URL + '/static/js/program/templates/panels/modalMetricList.html'
                    }
                },

                complete: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/complete.js',
                        BASE_URL + '/static/js/program/views/panels/setupProgressBar.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/complete.css',
                        BASE_URL + '/static/css/panels/setupProgressBar.css'
                    ],
                    templates: {
                        'complete-tmpl':            BASE_URL + '/static/js/program/templates/pages/complete.html',
                        'setup-progress-bar-tmpl':  BASE_URL + '/static/js/program/templates/panels/setupProgressBar.html'
                    }
                },

                confirm: {
                    scripts: [
                        // Page script
                        BASE_URL + '/static/js/program/views/pages/confirm.js',
                        BASE_URL + '/static/js/program/views/panels/suggestedInstance.js',
                        BASE_URL + '/static/js/program/views/panels/noSuggestedInstances.js',

                        // Progress bar module
                        BASE_URL + '/static/js/program/views/panels/setupProgressBar.js',

                        // Instance List module
                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        // Modal Metric list module
                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js'
                    ],
                    css: [
                        // Page style
                        BASE_URL + '/static/css/pages/confirm.css',

                        // Instance List module style
                        BASE_URL + '/static/css/panels/setupProgressBar.css',
                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        // Modal Metric List module style
                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css'
                    ],
                    templates: {
                        'confirm-tmpl':                 BASE_URL + '/static/js/program/templates/pages/confirm.html',

                        'suggested-instances-tmpl':     BASE_URL + '/static/js/program/templates/panels/suggestedInstance.html',
                        'no-suggested-instances-tmpl':  BASE_URL + '/static/js/program/templates/panels/noSuggestedInstances.html',

                        'setup-progress-bar-tmpl':      BASE_URL + '/static/js/program/templates/panels/setupProgressBar.html',

                        'instance-list-tmpl':           BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/modalMetricList.html'
                    }
                },

                'instances-auto': {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/instances-auto.js',

                        BASE_URL + '/static/js/program/views/panels/instanceSelect.js',

                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/instances-auto.css',

                        BASE_URL + '/static/css/panels/instanceSelect.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css'
                    ],
                    templates: {
                        'instances-auto-tmpl':      BASE_URL + '/static/js/program/templates/pages/instances-auto.html',
                        'instance-select-tmpl':     BASE_URL + '/static/js/program/templates/panels/instanceSelect.html',
                        'instance-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':   BASE_URL + '/static/js/program/templates/panels/modalMetricList.html'
                    }
                },

                'instances-import': {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/instances-import.js',

                        // module:instanceList and requirements
                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        // module:modalMetricList and requirements
                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/instances-import.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css'
                    ],
                    templates: {
                        'instances-import-tmpl':    BASE_URL + '/static/js/program/templates/pages/instances-import.html',
                        'instance-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':   BASE_URL + '/static/js/program/templates/panels/modalMetricList.html'
                    }
                },

                'instances-manual': {
                    scripts: [
                        BASE_URL + '/static/bower_components/jqtree/tree.jquery.min.js',
                        BASE_URL + '/static/js/program/views/pages/instances-manual.js',

                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js'
                    ],
                    css: [
                        BASE_URL + '/static/bower_components/jqtree/jqtree.css',
                        BASE_URL + '/static/css/pages/instances-manual.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css'
                    ],
                    templates: {
                        'instances-manual-tmpl':    BASE_URL + '/static/js/program/templates/pages/instances-manual.html',
                        'instance-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':   BASE_URL + '/static/js/program/templates/panels/modalMetricList.html'
                    }
                },

                'manage-custom-metrics': {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/manage-custom-metrics.js',

                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/manage-custom-metrics.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css'
                    ],
                    templates: {
                        'manage-custom-metrics-tmpl':    BASE_URL + '/static/js/program/templates/pages/manage-custom-metrics.html'
                    }
                },

                mobile: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/mobile.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/mobile.css'
                    ],
                    templates: {
                        'mobile-tmpl': BASE_URL + '/static/js/program/templates/pages/mobile.html'
                    }
                },

                notify: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/notify.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/notify.css'
                    ],
                    templates: {
                        'notify-tmpl': BASE_URL + '/static/js/program/templates/pages/notify.html'
                    }
                },

                register: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/register.js',
                        BASE_URL + '/static/js/program/views/panels/setupProgressBar.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/register.css',
                        BASE_URL + '/static/css/panels/setupProgressBar.css'
                    ],
                    templates: {
                        'register-tmpl':            BASE_URL + '/static/js/program/templates/pages/register.html',
                        'setup-progress-bar-tmpl':  BASE_URL + '/static/js/program/templates/panels/setupProgressBar.html'
                    }
                },

                welcome: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/welcome.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/welcome.css'
                    ],
                    templates: {
                        'welcome-tmpl': BASE_URL + '/static/js/program/templates/pages/welcome.html'
                    }
                },


                // returning user home page Manage Instances

                manage: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/manage.js',

                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',
                        BASE_URL + '/static/bower_components/blob/Blob.min.js',
                        BASE_URL + '/static/bower_components/file-saver/FileSaver.min.js',
                        BASE_URL + '/static/js/program/views/panels/instanceList.js',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/js/bootstrap-switch.min.js',
                        BASE_URL + '/static/js/program/views/panels/modalMetricList.js',

                        BASE_URL + '/static/bower_components/cryptojs/lib/Crypto.js',
                        BASE_URL + '/static/bower_components/cryptojs/lib/SHA1.js',
                        BASE_URL + '/static/bower_components/zeroclipboard/ZeroClipboard.min.js',
                        BASE_URL + '/static/js/program/views/panels/embedForm.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/manage.css',

                        BASE_URL + '/static/css/lib/jquery.tablesorter.theme.YOMP.css',
                        BASE_URL + '/static/css/panels/instanceList.css',

                        BASE_URL + '/static/bower_components/bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.min.css',
                        BASE_URL + '/static/css/panels/modalMetricList.css',

                        BASE_URL + '/static/css/panels/embedForm.css'
                    ],
                    templates: {
                        'manage-tmpl':              BASE_URL + '/static/js/program/templates/pages/manage.html',
                        'instance-list-tmpl':       BASE_URL + '/static/js/program/templates/panels/instanceList.html',
                        'modal-metric-list-tmpl':   BASE_URL + '/static/js/program/templates/panels/modalMetricList.html',
                        'embed-form-tmpl':          BASE_URL + '/static/js/program/templates/panels/embedForm.html'
                    }
                },


                // embed widgets

                charts: {
                    scripts: [
                        BASE_URL + '/static/bower_components/jquery-ui/jquery-ui.min.js',
                        BASE_URL + '/static/bower_components/rgb-color/rgb-color.min.js',
                        BASE_URL + '/static/js/lib/custom.dygraphs/dygraph-combined.js',
                        BASE_URL + '/static/js/lib/fog/fog.min.js',
                        BASE_URL + '/static/bower_components/jquery.tablesorter/js/jquery.tablesorter.min.js',

                        BASE_URL + '/static/js/program/views/panels/embedChartsTabs.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsSort.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsRows.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsMarkers.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsRow.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsRowInstance.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsRowMetric.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsRowMetricDetail.js',
                        BASE_URL + '/static/js/program/views/panels/embedChartsSlider.js',
                        BASE_URL + '/static/js/program/views/panels/annotationList.js',

                        BASE_URL + '/static/js/program/views/pages/charts.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/panels/embedChartsTabs.css',
                        BASE_URL + '/static/css/panels/embedChartsSort.css',
                        BASE_URL + '/static/css/panels/embedChartsRows.css',
                        BASE_URL + '/static/css/panels/embedChartsMarkers.css',
                        BASE_URL + '/static/css/panels/embedChartsRow.css',
                        BASE_URL + '/static/css/panels/embedChartsSlider.css',

                        BASE_URL + '/static/css/panels/annotationList.css',

                        BASE_URL + '/static/css/pages/charts.css'
                    ],
                    templates: {
                        'embed-charts-tabs-tmpl':       BASE_URL + '/static/js/program/templates/panels/embedChartsTabs.html',
                        'embed-charts-sort-tmpl':       BASE_URL + '/static/js/program/templates/panels/embedChartsSort.html',
                        'embed-charts-rows-tmpl':       BASE_URL + '/static/js/program/templates/panels/embedChartsRows.html',
                        'embed-charts-markers-tmpl':    BASE_URL + '/static/js/program/templates/panels/embedChartsMarkers.html',
                        'embed-charts-row-tmpl':        BASE_URL + '/static/js/program/templates/panels/embedChartsRow.html',
                        'embed-charts-slider-tmpl':     BASE_URL + '/static/js/program/templates/panels/embedChartsSlider.html',
                        'annotation-list-tmpl':         BASE_URL + '/static/js/program/templates/panels/annotationList.html',

                        'charts-tmpl': BASE_URL + '/static/js/program/templates/pages/charts.html'
                    }
                },


                // problems

                notFound: {
                    scripts: [
                        BASE_URL + '/static/js/program/views/pages/notFound.js'
                    ],
                    css: [
                        BASE_URL + '/static/css/pages/notFound.css'
                    ],
                    templates: {
                        'not-found-tmpl': BASE_URL + '/static/js/program/templates/pages/notFound.html'
                    }
                },

            }

        },

        initialize: function() {
        },

        handlers: {

            // first time user Setup flow

            auth: function() {
                var me = this,
                    templates = me.deps.pages.auth.templates,
                    css = me.deps.pages.auth.css,
                    scripts = me.deps.pages.auth.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.AuthView(_viewOpts);
                });
            },

            autostack: function() {
                var me = this,
                    templates = me.deps.pages['autostack'].templates,
                    css = me.deps.pages['autostack'].css,
                    scripts = me.deps.pages['autostack'].scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.AutostackView(_viewOpts);
                });
            },

            complete: function() {
                var me = this,
                    templates = me.deps.pages.complete.templates,
                    css = me.deps.pages.complete.css,
                    scripts = me.deps.pages.complete.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.CompleteView(_viewOpts);
                });
            },

            confirm: function() {
                var me = this,
                    templates = me.deps.pages.confirm.templates,
                    css = me.deps.pages.confirm.css,
                    scripts = me.deps.pages.confirm.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.ConfirmView(_viewOpts);
                });
            },

            'instances-auto': function() {
                var me = this,
                    templates = me.deps.pages['instances-auto'].templates,
                    css = me.deps.pages['instances-auto'].css,
                    scripts = me.deps.pages['instances-auto'].scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.InstancesAutoView(_viewOpts);
                });
            },

            'instances-import': function() {
                var me = this,
                    templates = me.deps.pages['instances-import'].templates,
                    css = me.deps.pages['instances-import'].css,
                    scripts = me.deps.pages['instances-import'].scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.InstancesImportView(_viewOpts);
                });
            },

            'instances-manual': function() {
                var me = this,
                    templates = me.deps.pages['instances-manual'].templates,
                    css = me.deps.pages['instances-manual'].css,
                    scripts = me.deps.pages['instances-manual'].scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.InstancesManualView(_viewOpts);
                });
            },

            'manage-custom-metrics': function() {
                var me = this,
                    templates = me.deps.pages['manage-custom-metrics'].templates,
                    css = me.deps.pages['manage-custom-metrics'].css,
                    scripts = me.deps.pages['manage-custom-metrics'].scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.ManageCustomMetricsView(_viewOpts);
                });
            },


            mobile: function() {
                var me = this,
                    templates = me.deps.pages.mobile.templates,
                    css = me.deps.pages.mobile.css,
                    scripts = me.deps.pages.mobile.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.MobileView(_viewOpts);
                });
            },

            notify: function() {
                var me = this,
                    templates = me.deps.pages.notify.templates,
                    css = me.deps.pages.notify.css,
                    scripts = me.deps.pages.notify.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.NotifyView(_viewOpts);
                });
            },

            register: function() {
                var me = this,
                    templates = me.deps.pages.register.templates,
                    css = me.deps.pages.register.css,
                    scripts = me.deps.pages.register.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.RegisterView(_viewOpts);
                });
            },

            terms: function() {
                var me = this,
                    templates = me.deps.pages.terms.templates,
                    css = me.deps.pages.terms.css,
                    scripts = me.deps.pages.terms.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.TermsView(_viewOpts);
                });
            },

            welcome: function() {
                var me = this,
                    templates = me.deps.pages.welcome.templates,
                    css = me.deps.pages.welcome.css,
                    scripts = me.deps.pages.welcome.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.WelcomeView(_viewOpts);
                });
            },


            // returning user home page Manage Instances

            manage: function() {
                var me = this,
                    templates = me.deps.pages.manage.templates,
                    css = me.deps.pages.manage.css,
                    scripts = me.deps.pages.manage.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.ManageView(_viewOpts);
                });
            },


            // embed widgets

            charts: function() {
                var me = this,
                    templates = me.deps.pages.charts.templates,
                    css = me.deps.pages.charts.css,
                    scripts = me.deps.pages.charts.scripts,
                    // JQuery UI conflicts with bootstrap and the following
                    // functions are overriden after JQuery UI is loaded:
                    // See https://YOMPhub.com/twbs/bootstrap/issues/393
                    $bstooltip = $.fn.tooltip,
                    $bsbutton = $.fn.button;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    // Restore Bootstrap functions and rename JQuery UI ones
                    $.widget.bridge('uitooltip', $.ui.tooltip);                    
                    $.widget.bridge('uibutton', $.ui.button);     
                    $.fn.tooltip = $bstooltip;
                    $.fn.button = $bsbutton;                    
                    new YOMPUI.ChartsView(_viewOpts);
                });
            },


            // problems

            notFound: function(query) {
                var me = this,
                    templates = me.deps.pages.notFound.templates,
                    css = me.deps.pages.notFound.css,
                    scripts = me.deps.pages.notFound.scripts;

                me.loader.loadResources({
                    templates: templates,
                    css: css,
                    scripts: scripts,
                    msgs: _messages
                }, function() {
                    new YOMPUI.NotFoundView(_viewOpts);
                });
            }

        }

    };

})();
