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

    YOMPUI.SetupProgressBarView = Backbone.View.extend({

        template: _.template($('#setup-progress-bar-tmpl').html()),

        msgs: YOMPUI.msgs('setup-progress-bar-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
        },

        initialize: function(options) {
            this.current =  options.current;
            this.percent =  options.percent;
            this.total =    options.total;
        },

        render: function() {
            var me = this,
                data = {
                    baseUrl:    NTA.baseUrl,
                    msgs:       me.msgs,
                    site:       me.site,
                    current:    this.current,
                    total:      this.total
                };

            me.$el.html(me.template(data));

            // set progress bar to correct % width color fill
            me.$el.find('.progress-bar').width((this.percent || 1) + '%');

            me.trigger('view-ready');
            return me;
        }

    });

})();
