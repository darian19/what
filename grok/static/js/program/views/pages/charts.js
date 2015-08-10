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

    /**
     * Backbone.View() - Embed: Charts
     */
    YOMPUI.ChartsView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#charts-tmpl').html()),

        events: {
        },

        // Custom properties

        msgs: YOMPUI.msgs('charts-tmpl'),
        site: YOMPUI.msgs('site'),

        api:    null,
        hash:   null,
        height: null,
        width:  null,

        collections: {
            models: null
        },
        views: {
            tabs:   null,
            sort:   null,
            rows:   null,
            slider: null
        },

        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            var collectionOpts = null,
                fetchOpts = {
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(response);
                    }
                };

            // init

            this.api = options.api;

            this.hash =   YOMPUI.utils.getUrlParam('hash');
            this.height = YOMPUI.utils.getUrlParam('height');
            this.width =  YOMPUI.utils.getUrlParam('width') ||
                            ($('body section#content').width() + 25);

            // collections
            collectionOpts = {
                api:    this.api,
                site:   this.site,
                period: 2
            };
            this.collections.models =
                new YOMPUI.SortedModelsCollection([], collectionOpts);

            // page

            YOMPUI.utils.title(this.msgs.title);
            YOMPUI.utils.throb.start(this.site.state.loading);

            // no hash = web ui view (not direct embed)
            if(! this.hash) {
                // since web ui view, make sure aws authed
                if(! YOMPUI.utils.isAuthorized()) {
                    YOMPUI.utils.go(this.site.paths.welcome);
                    return;
                }
            }

            // fetch data and render

            $.when(
                this.collections.models.fetch(fetchOpts)
            ).done(this.render.bind(this));
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var data = {
                    baseUrl:    NTA.baseUrl,
                    msgs:       this.msgs,
                    site:       this.site
                },
                viewOpts = {
                    api:            this.api,
                    hash:           this.hash,
                    width:          this.width,
                    collections: {
                        models: this.collections.models
                    }
                };

            YOMPUI.utils.throb.stop();
            this.$el.html(this.template(data));

            // no results
            if(this.collections.models.length <= 0) {
                this.$el.find('.rows').html(this.msgs.empty);
                this.trigger('view-ready');
                return this;
            }

            // init views
            this.views.tabs =   new YOMPUI.EmbedChartsTabsView(viewOpts);
            this.views.sort =   new YOMPUI.EmbedChartsSortView(viewOpts);
            this.views.rows =   new YOMPUI.EmbedChartsRowsView(viewOpts);
            this.views.slider = new YOMPUI.EmbedChartsSliderView(viewOpts);

            // Assign all views to DOM
            this.assign(this.views.tabs, '.tabs');
            this.assign(this.views.sort, '.sort');
            this.assign(this.views.rows, '.rows');
            this.assign(this.views.slider, '.slider');

            // Render all views
            this.views.tabs.render();
            this.views.sort.render();
            this.views.rows.render();
            this.views.slider.render();

            // Handle inter-module communication

            this.listenTo(this.views.tabs, 'tab-change', this.handleTabChange);
        },

        // Custom methods

        /**
         * When switching between tabs, change the minutes-per-bar of the Rows
         */
        handleTabChange: function(tab) {
            var minutesPerBar = this.site.charts.instance.anomaly.minutesPerBar,
                updateRows = function() {
                    this.views.rows.updateMinutesPerBar(minutesPerBar[tab]);
                    this.views.rows.updateSortOrder(this.collections.models);
                },
                fetchOpts = {
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(response);
                    }
                },
                // Convert minutes per bar into hours for the period API
                // Assumes 24 bars to match mobile app view.
                collectionOpts = {
                    api:    this.api,
                    site:   this.site,
                    period: (minutesPerBar[tab] * 24) / 60
                };

            YOMPUI.utils.throb.start(this.site.state.loading);

            this.collections.models =
                new YOMPUI.SortedModelsCollection([], collectionOpts);

            $.when(
                this.collections.models.fetch(fetchOpts)
            ).done(updateRows.bind(this));
        }

    });

})();
