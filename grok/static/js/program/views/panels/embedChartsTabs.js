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

    var _viewName = 'embed-charts-tabs';

    /**
     * Backbone.View() - Embed: Charts > Tabs
     */
    YOMPUI.EmbedChartsTabsView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#' + _viewName + '-tmpl').html()),

        events: {
            'click .nav-tabs li a': 'handleTabClick'
        },

        // Custom properties

        msgs: YOMPUI.msgs(_viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        api:    null,
        hash:   null,

        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.api =  options.api;
            this.hash = options.hash;
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var data = {
                    baseUrl: NTA.baseUrl,
                    msgs: this.msgs,
                    site: this.site
                };

            this.$el.html(this.template(data));

            // if a Embed Widget view, instead of Web UI view, add logo
            if(this.hash) {
                this.$el.find('.YOMP-embed-charts-tabs').addClass('embed');
            }

            this.trigger('view-ready');
            return this;
        },

        // Custom methods

        /**
         * Handle a tab click, fires 'tab-change' event
         * @param {object} event Target event handle object
         */
        handleTabClick: function(event) {
            var $target =   $(event.currentTarget),
                label =     $target.text().toLowerCase(),
                $tabs =     $target.parent().parent().children();

            event.preventDefault();
            event.stopPropagation();

            $tabs.removeClass('active');
            $target.parent().addClass('active');

            return this.trigger('tab-change', label);
        }

    });

})();
