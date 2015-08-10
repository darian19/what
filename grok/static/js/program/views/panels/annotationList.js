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

    YOMPUI.AnnotationListView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#annotation-list-tmpl').html()),

        events: {
        },


        // Custom properties

        msgs: YOMPUI.msgs('annotation-list-tmpl'),
        site: YOMPUI.msgs('site'),

        api:         null,
        instance:    null,
        tagName:     null,
        annotations: null,
        flag:        null,


        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.api =         options.api;
            this.instance =    options.instance;
            this.tagName =     options.tagName;
            this.annotations = options.annotations;
            this.flag =        options.flag;
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var me = this;

            // show dialog
            var dialog = bootbox.dialog({
                animate:    false,
                message:    'Loading...',
                show:       false,
                backdrop:   false,
                title:      this.tagName || this.instance//this.msgs.title
            });
            dialog.on('hidden.bs.modal', function(event) {
                this.trigger('view-closed');
                // Restore original flag
                this.flag.div.className = this.flag.cssClass;
            }.bind(this));
            dialog.modal('show');


            var data = {
                baseUrl:        NTA.baseUrl,
                msgs:           this.msgs,
                site:           this.site,
                instance:       this.instance,
                tagName:        this.tagName,
                annotations:    this.annotations
            };
            var rendered = this.template(data);
            var body = dialog.find('.bootbox-body').html(rendered);
            var header = dialog.find('.modal-header').attr('title', this.instance);
            dialog.find('.modal-content').draggable({
                handle: ".modal-header"
            })

            this.trigger('view-ready');
            return this;
        },


        // Custom methods

    });

})();
