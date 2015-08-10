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

    /* TODO: Rename this view to modalInstanceSelect or something cause it's a modal */

    YOMPUI.InstanceSelectView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#instance-select-tmpl').html()),

        events: {
        },

        // Custom properties

        msgs: YOMPUI.msgs('instance-select-tmpl'),
        site: YOMPUI.msgs('site'),

        api:        null,
        instances:  null,

        data: {
            instances:  null,
            models:     null
        },

        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.api =          options.api;
            this.instances =    options.instances;

            this.data.instances =   options.data.instances;
            this.data.models =      options.data.models;

            this.initModal();
            this.render();
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var me = this,
                data = {
                    baseUrl: NTA.baseUrl,
                    msgs: me.msgs,
                    site: me.site,
                    instances: me.instances
                };

            me.$modal.modal('show');
            me.$modal.find('.bootbox-body').html(me.template(data));

            me.trigger('view-ready');
            return me;
        },

        // Custom methods

        /**
         *
         */
        initModal: function() {
            var me = this;

            me.$modal = bootbox.dialog({
                animate:    false,
                message:    'Loading...',
                show:       false,
                title:      'Instances Found',
                buttons: {
                    cancel: {
                        label:      'Cancel',
                        className:  'btn-default'
                    },
                    done: {
                        label:      'Continue',
                        className:  'btn-primary',
                        callback: function(event) {
                            me.handleModalAction(event);
                        }
                    }
                },
            });
            me.$modal.on('hidden.bs.modal', function(event) {
                me.trigger('view-closed');
            });
        },

        /**
         * the GO button action on the modal layer popup
         */
        handleModalAction: function(event) {
            var me = this,
                $form = me.$modal.find('form'),
                $checkboxes = $form.find('input[type=checkbox]'),
                instances = [];

            event.preventDefault();
            event.stopPropagation();

            YOMPUI.utils.throb.start(me.site.state.instance.starts);

            $checkboxes.each(function() {
                var $row = $(this).parents('tr'),
                    id = {
                        region:     $row.data('region'),
                        namespace:  $row.data('namespace'),
                        instance:   $row.data('instance'),
                        creator:    $row.data('creator')
                    };

                if($(this).is(':checked')) {
                    instances.push(id);
                }
            });

            // kick off creation loop
            me.createInstances(instances);
        },

        /**
         * Create instance models. Use recursion so if there is a
         *  problem the loop won't keep dumbly running forever.
         */
        createInstances: function(list, index) {
            index = index || 0;

            var me = this,
                percent = 0;

            if(index < list.length) {
                // continue recursive loop

                if(list[index].namespace.match(me.site.namespaces.aws.real)) {
                    // AWS Instance
                    me.api.createMonitoredInstance(
                        list[index].region,
                        list[index].namespace,
                        list[index].instance,
                        function(error, result) {
                            if(error) {
                                me.trigger('view-models-created');
                                return YOMPUI.utils.modalError(error);
                            }

                            me.data.instances.add({
                                name:       list[index].instance,
                                location:   list[index].region,
                                namespace:  list[index].namespace,
                                instance:   list[index].instance,
                                server:     list[index].instance
                            });

                            // update % in throbber
                            percent = Math.round((index / list.length) * 100);
                            YOMPUI.utils.throb.message(
                                me.site.state.instance.starts +
                                ' (' + percent + '%)'
                            );

                            // next recursion
                            me.createInstances(list, index + 1);
                        }
                    );
                }
                else {
                    // TODO: Expired code?

                    // Other Entity (AutoStack, YOMP Custom Metric, etc.)
                    me.api.createModels(
                        list[index].creator,
                        function(error, results) {
                            if(error) {
                                me.trigger('view-models-created');
                                return YOMPUI.utils.modalError(error);
                            }

                            me.data.models.add({
                                datasource: list[index].creator.get('datasource'),
                                location:   list[index].creator.get('region'),
                                metric:     list[index].creator.get('metric'),
                                server:     list[index].instance,
                                id:         '',
                                uid:        ''
                            });

                            // update % in throbber
                            percent = Math.round((index / list.length) * 100);
                            YOMPUI.utils.throb.message(
                                me.site.state.instance.starts +
                                ' (' + percent + '%)'
                            );

                            // next recursion
                            me.createInstances(list, index + 1);
                        }
                    );
                }
            }
            else {
                // all done with recursive loop
                me.$modal.modal('hide');
                me.trigger('view-models-created');
                YOMPUI.utils.throb.stop();
            }
        }

    });

})();
