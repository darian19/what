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

    var viewName = 'instances-import';

    YOMPUI.InstancesImportView = Backbone.View.extend({

        name: viewName,

        template: _.template($('#' + viewName + '-tmpl').html()),

        msgs: YOMPUI.msgs(viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'click #upload':    'handleChoose', // pretty file upload button
            'click #file':      'handleFile',   // real file upload button
            'change #file':     'handleUpload', // what to do after upload
            'click #done':      'handleDone'
        },

        initialize: function(options) {
            var me = this;
            me.api = options.api;
            me.instanceListView = null;

            YOMPUI.utils.title(me.msgs.title);

            // go setup if they have not yet
            if(! YOMPUI.utils.isAuthorized()) {
                location.href = me.site.paths.welcome;
                return;
            }

            me.render();
        },

        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    button: {
                        done: me.site.buttons.done
                    }
                };

            me.$el.html(me.template(data));

            me.instanceListView = new YOMPUI.InstanceListView({
                el:     $('#instance-list'),
                api:    me.api,
                site:   me.site
            });
            me.instanceListView.render();

            me.trigger('view-ready');
            return me;
        },

        // pretty file upload button clicked
        handleChoose: function(event) {
            // trigger real button click (see handleFile())
            $('#file').click();
        },

        // real file upload button clicked
        handleFile: function(event) {
            event.stopPropagation();
        },

        // file chosen, do actual upload
        handleUpload: function(event) {
            var me = this,
                target = event.currentTarget,
                $target = $(target),
                $filename = me.$el.find('.filename'),
                file = target.files[0],
                reader = new FileReader();

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.throb.start(me.site.state.import);

            // de-emphasize Import button
            $target.parent().toggleClass('btn-primary btn-default');

            $filename.html(file.name);
            $filename.removeClass('text-muted');

            reader.onload = function(event) {
                var data = JSON.parse(event.currentTarget.result);
                me.createModels(data);
            };
            reader.readAsText(file, 'UTF-8');
        },

        handleDone: function(event) {
            var destination = this.site.paths.manage;

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.go(destination);
        },

        /**
         * Create models. Use recursion so if there is a
         *  problem the loop won't keep dumbly running forever.
         */
        createModels: function(list, index) {
            index = index || 0;

            var me = this,
                percent = 0;

            if(index < list.length) {
                // continue recursive loop
                me.api.createModels(
                    list[index],
                    function(error, results) {
                        if(error) {
                            return YOMPUI.utils.modalError(error);
                        }

                        me.instanceListView.data.models.add({
                            datasource: list[index].datasource,
                            location:   list[index].region,
                            metric:     list[index].metric,
                            server:     list[index].instance,
                            id:         results[0].uid,
                            uid:        results[0].uid
                        });

                        // update % in throbber
                        percent = Math.round((index / list.length) * 100);
                        YOMPUI.utils.throb.message(
                            me.site.state.instance.starts +
                            ' (' + percent + '%)'
                        );

                        // next recursion
                        me.createModels(list, index + 1);
                    }
                );
            }
            else {
                // all done with recursive loop
                me.instanceListView.data.instances.fetch({
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                });
                me.instanceListView.data.autostacks.fetch({
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                });
                me.instanceListView.data.customs.fetch({
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                });
                me.instanceListView.data.namespaces.fetch({
                    error: function(collection, response, options) {
                        return YOMPUI.utils.modalError(error);
                    }
                });

                YOMPUI.utils.throb.stop();
            }
        }

    });

})();
