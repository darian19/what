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

    YOMPUI.EmbedFormView = Backbone.View.extend({

        template: _.template($('#embed-form-tmpl').html()),

        msgs: YOMPUI.msgs('embed-form-tmpl'),
        site: YOMPUI.msgs('site'),

        events: {
            'input #domain': 'handleInputChange',
            'input #height': 'handleInputChange',
            'input #width':  'handleInputChange'
        },

        initialize: function() {
            ZeroClipboard.config({
                moviePath: NTA.baseUrl +
                    "/static/bower_components/zeroclipboard/ZeroClipboard.swf"
            });
        },

        render: function() {
            var data = {
                    baseUrl:    NTA.baseUrl,
                    msgs:       this.msgs,
                    site:       this.site
                };

            this.$el.html(this.template(data));

            $('#form').submit(function(e) {
               return false;
            });

            this.enableCopy();

            this.trigger('view-ready');
            return this;
        },

        enableCopy: function() {
            var $copied = $("#copied"),
                $code = $("#code"),
                client = new ZeroClipboard($(".btn-copy"));

            client.on("complete", function(client, args) {
                $code.focus();
                $code.select();
                $copied.show();
            });
        },

        handleInputChange: function(event) {
            var me = this,
                $domain =   $('#domain'),
                $form =     $('#form'),
                $width =    $('#width'),
                $height =   $('#height'),
                $code =     $('#code'),
                $copy =     $('#copy'),
                domain =    $domain.val(),
                width =     $width.val(),
                height =    $height.val();

            $code.val('');
            $copy.attr('disabled', 'disabled');

            // Check validity
            if($form[0].checkValidity) {
                if(!(
                        $form[0].checkValidity()
                    &&  $domain[0].checkValidity()
                    &&  $width[0].checkValidity()
                    &&  $height[0].checkValidity()
                )) {
                    // Force HTML5 Form validation by clicking on the submit button
                    $copy.removeAttr('disabled');
                    $copy.click();
                    $copy.attr('disabled', 'disabled');
                    return;
                }
            }

            if (domain.length && width.length && height.length) {
                $code.val(me.generateCode(domain, width, height));
                $copy.removeAttr('disabled');

                /* From http://stackoverflow.com/a/106223 */
                var validIpAddressRegex = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/,
                    validHostnameRegex = /^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/;

                if (validIpAddressRegex.test(domain) || validHostnameRegex.test(domain)) {
                    $domain.tooltip('destroy');
                }
                else {
                    $domain.tooltip({"title": "This doesn't look like a valid hostname."});
                    $domain.tooltip('show');
                }
            }
        },

        generateCode: function(domain, width, height) {
            var me = this,
                apiKey = YOMPUI.utils.store.get('apiKey'),
                hash = Crypto.SHA1(apiKey + domain),
                serverURL = 'http://' + window.location.hostname +
                            "/YOMP/embed/charts",
                code = "<iframe width=\"" + width + "\" " +
                        "height=\"" + height + "\" " +
                        "style=\"border:0\" " +
                        "src=\"" + serverURL +
                        "?hash=" + hash +
                        "&width=" + width + "&height=" + height +
                        "\"></iframe>";

            return code;
        }

    });

})();
