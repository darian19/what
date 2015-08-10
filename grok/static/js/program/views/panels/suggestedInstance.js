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

    YOMPUI.SuggestedInstancesListView = Backbone.View.extend({

        template: _.template($('#suggested-instances-tmpl').html()),

        site: YOMPUI.msgs('site'),

        events: {
            'click input[type="checkbox"]': 'handleCheckboxClick'
        },

        initialize: function(options) {
            this.instance =   options.instance
            this.region =     options.region
            this.checked =    options.checked
        },

        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    site: me.site,
                    instance: me.instance,
                    region: me.region,
                    checked: me.checked
                };

            me.$el.append(me.template(data));

            me.trigger('view-ready');

            return me;
        },

        handleCheckboxClick: function(event) {
            var $el = $(event.currentTarget);
            this.trigger('click', $el.prop('checked'));
        }

    });

})();
