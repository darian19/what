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

    var _viewName = 'embed-charts-markers';

    /**
     * Backbone.View() - Embed: Charts > Rows > Markers
     */
    YOMPUI.EmbedChartsMarkersView = Backbone.View.extend({

        // Backbone.View properties

        template: _.template($('#' + _viewName + '-tmpl').html()),

        events: {
        },


        // Custom properties

        msgs: YOMPUI.msgs(_viewName + '-tmpl'),
        site: YOMPUI.msgs('site'),

        api:            null,
        minutesPerBar:  null,
        range:          null,
        width:          null,


        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.api =              options.api;
            this.minutesPerBar =    options.minutesPerBar;
            this.range =            options.range;
            this.width =            options.width;
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

            this.update();

            this.trigger('view-ready');
            return this;
        },


        // Custom methods

       /**
         * Draw markers for Days view
         */
        drawMarkersDays: function() {
            var config =        this.getDrawMarkersConfig(),
                previousDay =   config.start.getDay(),
                previousDate =  config.start.getDate();

            // Round time to interval
            var startInterval = Math.floor(config.start.getTime()/config.iteration) * config.iteration;
            var endInterval = Math.floor(config.end.getTime()/config.iteration) * config.iteration;
            for(i=startInterval; i<endInterval; i+=config.iteration) {
                var current =       new Date(i),
                    currentDay =    current.getDay(),
                    currentDate =   current.getDate(),
                    output =        null;

                if(
                    (currentDay !== previousDay) &&
                    (currentDate !== previousDate)
                ) {
                    output =
                        config.days[currentDay] + ' ' +
                        config.months[current.getMonth()] + ' ' +
                        currentDate;

                    config.drawMarker(output, current);

                    previousDay = currentDay;
                    previousDate = currentDate;
                }
            }
        },

        /**
         * Draw markers for Hours view
         */
        drawMarkersHours: function() {
            var config =    this.getDrawMarkersConfig(),
                previous =  config.start.getHours(),
                first =     true;

            // Round time to interval
            var startInterval = Math.floor(config.start.getTime()/config.iteration) * config.iteration;
            var endInterval = Math.floor(config.end.getTime()/config.iteration) * config.iteration;
            for(i=startInterval; i<endInterval; i+=config.iteration) {
                var current =       new Date(i),
                    currentHour =   current.getHours(),
                    prefix =        '',
                    postfix =       '',
                    output =        '';

                if(
                    (!(currentHour % 2)) &&                 // even hours only
                    (currentHour !== previous)              // unique hour #
                ) {
                    if(first) {
                        first = false;
                        prefix =
                            config.days[current.getDay()] + ' ' +
                            config.months[current.getMonth()] + ' ' +
                            current.getDate() + ' ';
                    }
                    postfix = (currentHour >= 12) ? 'PM' : 'AM';
                    output = currentHour;
                    if(currentHour > 12) {
                        output = currentHour - 12;
                    }
                    if(currentHour === 0) {
                        output = 12;
                    }
                    output = prefix + ' ' + output + ':00 ' + ' ' + postfix;

                    config.drawMarker(output, current);

                    previous = currentHour;
                }
            }
        },

        /**
         * Draw markers for Weeks view
         */
        drawMarkersWeeks: function() {
            var config =    this.getDrawMarkersConfig(),
                occurance = 0;
            // Round time to interval
            var startInterval = Math.floor(config.start.getTime()/config.iteration) * config.iteration;
            var endInterval = Math.floor(config.end.getTime()/config.iteration) * config.iteration;
            for(i=startInterval; i<endInterval; i+=config.iteration) {
                var current =       new Date(i),
                    currentDay =    current.getDay(),
                    currentHour =   current.getHours(),
                    output =        null;

                if(
                    (currentDay === 0) &&
                    (occurance === 0)
                ) {
                    output =
                        config.days[currentDay] + ' ' +
                        config.months[current.getMonth()] + ' ' +
                        current.getDate();

                    config.drawMarker(output, current);

                    occurance++;
                }
                else if(currentDay !== 0) {
                    occurance = 0;
                }
            }
        },

        /**
         * Return a single config hash for the indivudal drawing methods to use.
         * @returns {object}
         */
        getDrawMarkersConfig: function() {
            var $rows =     $('.YOMP-embed-charts-rows'),
                $target =   this.$el.find('div'),
                padding =   10,
                height =    $rows.height(),
                left =      $rows.offset().left - padding,
                viewStart = this.range.view.start,
                viewEnd =   this.range.view.end,
                pixelWidth = this.width - 25,
                /**
                 * Convert a datetime into a dom x coord relative to view width
                 */
                toDomXCoord = function(inputDate) {
                    var viewTimeWidth =     viewEnd.getTime() - viewStart.getTime(),
                        inputTimeWidth =    inputDate.getTime() - viewStart.getTime(),
                        timeRatio =         inputTimeWidth / viewTimeWidth,
                        xCoord =            parseInt(timeRatio * pixelWidth)

                    return xCoord;
                }.bind(this);

            return {
                days:       [ 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat' ],
                months:     [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ],
                iteration:  this.minutesPerBar * 60 * 1000,
                start:      new Date(viewStart),
                end:        new Date(viewEnd),
                /**
                 * Put a pink marker into action on the screen
                 */
                drawMarker: function(content, when) {
                    var $newEl =    $('<span><aside></aside>' + content + '</span>'),
                        x =         toDomXCoord(when),
                        boundary =  (pixelWidth > 990) ? 0.95 : 0.90;

                    // marker far-right boundary overrun protection
                    if(x > (pixelWidth * boundary)) return;

                    // marker left boundary overrun protection
                    if(x < padding) return;

                    $newEl.css('left', left + x);
                    $newEl.find('aside').height(height);
                    $target.append($newEl);
                }
            };
        },

        /**
         * Allow other modules to hide vertical 1-pixel wide lines for each
         *  marker (usually to hide them before the Rows box height will change)
         *  to prevent an ugly UI experience, later calls to this.update() will
         *  re-draw them.
         */
        hideLines: function() {
            this.$el.find('aside').hide();
        },

        /**
         * Clear and redraw markers
         */
        update: function(options) {
            var perBar = this.site.charts.instance.anomaly.minutesPerBar,
                $target = this.$el.find('div');

            if(options && options.minutesPerBar) {
                this.minutesPerBar = options.minutesPerBar;
            }

            // remove all previous markers before redraw
            $target.children().remove();

            switch(this.minutesPerBar) {
                case perBar.hours:
                    this.drawMarkersHours();
                    break;
                case perBar.days:
                    this.drawMarkersDays();
                    break;
                case perBar.weeks:
                    this.drawMarkersWeeks();
                    break;
            }
        }

    });

})();
