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

    var _viewName = 'embed-charts-row',
        _site =     YOMPUI.msgs('site'),

        WEEKDAY = ['S', 'M', 'T', 'W', 'T', 'F', 'S'],

        indexTimestamp =    _site.charts.instance.anomaly.index.timestamp,
        indexValue =        _site.charts.instance.anomaly.index.value,
        indexAnomaly =      _site.charts.instance.anomaly.index.anomaly,

        minutesPerRecord = _site.charts.instance.anomaly.minutesPerBar.hours,

        // constants
        barWidth =          10,
        barHeight =         30,
        dotHeight =         6,
        labelHeight =       20,
        graphWidthPadding = 25,
        longClickInterval = 1000,   // 1 sec for long click

        // dynamic vars
        graphHeight = barHeight + labelHeight + dotHeight,

        // sync these colors with mobile app
        color = {
            green:  new RGBColor('#0f8300'),
            gray:   {
                lite:   new RGBColor('#ccc'),
                med:    new RGBColor('#aaa'),
                dark:   new RGBColor('#666')
            },
            red:    new RGBColor('#cb0000'),
            yellow: new RGBColor('#d6ce03'),
            white:  new RGBColor('#fff'),
            black:  new RGBColor('#000'),
            blue:   new RGBColor('#2A99CE')
        };


    /**
     * Backbone.View() - Embed: Charts > Rows > Row
     */
    YOMPUI.EmbedChartsRowView = Backbone.View.extend({

        // Backbone.View properties

        events: {
        },
        tagName: 'li',
        template: _.template($('#' + _viewName + '-tmpl').html()),


        // Custom properties

        msgs: YOMPUI.msgs(_viewName + '-tmpl'),
        site: _site,

        annotations:        null,
        api:                null,
        axesOptions:        null,
        chart:              null,
        chartInteraction:   null,
        chartOptions:       null,
        color:              null,
        instance:           null,
        datas:              null,
        minutesPerBar:      null,
        models:             null,
        range:              null,
        type:               null, // 'instance' || 'metric', set in subclasses
        width:              null,


        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            this.annotations = options.annotations;
            this.api =      options.api;
            this.datas =    options.datas;
            this.instance = options.instance;
            this.models =   options.models;
            this.range =    options.range;
            this.width =    options.width;

            this.minutesPerBar = options.minutesPerBar || minutesPerRecord;

            this.color = color;

            this.axesOptions = {
                x: {
                    axisLabelFormatter: this.formatXLabel.bind(this),
                    axisLabelOverflow:  true,
                    ticker:             this.dateTicker.bind(this)
                }
            };
            this.chartInteraction = {
                'click':        this.handleClick.bind(this),
                'dblclick':     this.handleDblClick.bind(this),
                'mousedown':    this.handleMouseDown.bind(this),
                'mousemove':    this.handleMouseMove.bind(this),
                'mouseup':      this.handleMouseUp.bind(this),
                'mouseout':     this.handleMouseOut.bind(this),
                'mousewheel':   this.handleMouseWheel.bind(this),
                'touchstart':   this.handleTouchStart.bind(this),
                'touchmove':    this.handleTouchMove.bind(this),
                'touchend':     this.handleTouchEnd.bind(this)
            };

            this.chartOptions = {
                axes:                   this.axesOptions,
                axisLabelColor:         this.color.gray.lite.toHex(),
                axisLineColor:          this.color.white.toHex(),
                dateWindow:             [ this.range.view.start, this.range.view.end ],
                drawYAxis:              false,
                drawXGrid:              false,
                drawYGrid:              false,
                height:                 graphHeight,
                highlightCircleSize:    0,      // Remove highlight circle
                interactionModel:       this.chartInteraction,
                showLabelsOnHighlight:  false,  // Remove highlight label
                plotter:                this.anomalyBarChartPlotter.bind(this),
                valueRange:             [ 0.0, 1.0 ],
                width:                  this.width - graphWidthPadding
            };
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            // Row* (Instance, Metric, MetricDetail, etc.) .render() called here

            // Shared render() for all Rows
            this.trigger('view-ready');
            return this;
        },


        // Custom methods

        /**
         * DyGraphs custom plotter function to draw Anomaly bar charts
         * @method
         * @param {object} e Dygraph object reference
         */
        anomalyBarChartPlotter: function(e) {
            var ctx =           e.drawingContext,
                points =        e.points,
                y_bottom =      e.dygraph.toDomYCoord(0),
                gradientMap =   YOMPUI.utils.makeGradientMap(barHeight, [
                    color.red, color.yellow, color.green
                ]),
                perBar =        _site.charts.instance.anomaly.minutesPerBar,
                self =          this;

            points.forEach(function(p) {
                var height =    y_bottom - p.canvasy - dotHeight,
                    center_x =  p.canvasx,
                    xStart =    (center_x - barWidth / 2),
                    xEnd =      (center_x + barWidth / 2),
                    h =         0,
                    drawLine =  function(ctx, xs, xe, y, color) {
                        ctx.strokeStyle = color;
                        ctx.beginPath();
                        ctx.moveTo(xs, y);
                        ctx.lineTo(xe, y);
                        ctx.stroke();
                    },
                    drawDot = function(ctx,x,y,r,color) {
                        ctx.fillStyle = color;
                        ctx.beginPath();
                        ctx.arc(x, y, r, 0, 2*Math.PI);
                        ctx.fill();
                    };

                // every bar has a basic 1px placeholder green line
                // TODO: needs to be a gray box for null data vs a 0 value
                drawLine(ctx, xStart, xEnd, y_bottom - dotHeight, gradientMap[0].toRGB());

                for(h=0; h<height-1; h++) {
                    var y = y_bottom - h - dotHeight;
                    drawLine(ctx, xStart, xEnd, y, gradientMap[h].toRGB());
                }

                // Draw 'dot' under the bar
                var timestamp = (p.xval instanceof Date) ? p.xval.getTime() : p.xval,
                    hasDot =    false,
                    dotColor = color.gray.med;

                var date;
                switch(self.minutesPerBar) {
                    case perBar.hours:
                        // Draw a 'dot' every 15 minutes, hilighting every hour
                        timestamp = Math.ceil(timestamp/300000) * 300000;
                        date = new Date(timestamp);
                        hasDot = date.getMinutes() % 15 == 0;
                        dotColor = date.getMinutes() == 0 ? color.black : dotColor;
                        break;
                    case perBar.days:
                        // Draw a 'dot' every 3 hours, hilighting every 12 hours
                        date = new Date(timestamp);
                        hasDot = date.getHours() % 3 == 0;
                        dotColor = date.getHours() % 12 == 0 ? color.black : dotColor;
                        break;
                    case perBar.weeks:
                        // Dont show 'dot' on week view
                        hasDot = false;
                        break;
                }
                if (hasDot) {
                    drawDot(ctx, center_x, y_bottom - dotHeight / 3, dotHeight / 4, dotColor.toRGB());
                }
            });
        },

        /**
         * Format Model data from API for DyGraphs to display Anomaly charts
         * @param {object} modelOutput Object of YOMP metric model data output
         * @returns {object} Object formatted for FaceOfYOMP/Dygraphs display
         */
        formatAnomalyModelOutputData: function(modelOutput) {
            var outputData =    [],
                outputLabels =  [ 'Time', 'Anomaly' ];

            modelOutput.forEach(function(dataRow, i) {
                var scaled = YOMPUI.utils.logScale(dataRow[indexAnomaly]),
                    datum = parseFloat(scaled);

                // Round time stamp to closest 5 min interval
                var timestamp = YOMPUI.utils.getUTCDateFromTimestamp(dataRow[indexTimestamp]).getTime();
                timestamp = Math.ceil(timestamp/300000) * 300000;
                outputData.push([
                    timestamp,
                    datum
                ]);
            });

            return {
                labels: outputLabels,
                data: outputData
            };
        },

        /**
         * Overridden in embedChartsRow* (Instance, Metric, etc.)
         * Format data to be sent to FaceOfYOMP/DyGraphs chart
         * @returns {array} List of datapoints (themselves arrays) ready for
         *  FaceOfYOMP/Dygraphs.
         */
        // getFormattedData: function() {},

        /**
         * Overridden in embedChartsRow* (Instance, Metric, etc.)
         * Format annotations to be sent to Dygraph chart.
         * @see http://dygraphs.com/annotations.html
         * @see http://dygraphs.com/jsdoc/symbols/Dygraph.html#setAnnotations
         * @returns {array} List of annotations ready for Dygraph's
         *                  "setAnnotations" method.
         */
        getFormattedAnnotations: function() {},

        /**
         *
         */
        handleClick: function(event, graph, context) {
            if (context._active) {
                this.trigger('click', this);
                context._active = false;
            }
        },

        /**
         *
         */
        handleDblClick: function(event, graph, context) {
        },

        /**
         *
         */
        handleMouseDown: function(event, graph, context) {
            var $mouse = this.$el.find('.charts');

            $mouse.css('cursor', 'move');
            $mouse.css('cursor', '-moz-grab');
            $mouse.css('cursor', '-webkit-grab');

            context.initializeMouseDown(event, graph, context);
            context._active = true;
            context._longClickTimer = window.setTimeout(function() {
                if(context.isPanning) {
                    Dygraph.endPan(event, graph, context);
                }

                $mouse.css('cursor', '-moz-zoom-in');
                $mouse.css('cursor', '-webkit-zoom-in');

                this.trigger('longclick', this);
                context._active = false;
            }.bind(this), longClickInterval);
        },

        /**
         *
         */
        handleMouseMove: function(event, graph, context) {
            var $mouse = this.$el.find('.charts');

            // Horizontal scrolling only
            context.is2DPan = false;

            // Handle scrolling
            if(context.isPanning) {
                var range = graph.xAxisRange(),
                    direction = null;

                $mouse.css('cursor', 'move');
                $mouse.css('cursor', '-moz-grab');
                $mouse.css('cursor', '-webkit-grab');

                // panning side-scroll boundaries
                if(context.dragStartX > context.dragEndX) {
                    // drag charts from right to left, stop if out of boundary
                    direction = 'left';
                    if(range[1] > this.range.data.end) {
                        return $mouse.css('cursor', 'not-allowed');
                    }
                }
                else {
                    // drag charts from left to right, stop if out of boundary
                    direction = 'right';
                    if(range[0] < this.range.data.start) {
                        return $mouse.css('cursor', 'not-allowed');
                    }
                }

                Dygraph.movePan(event, graph, context);
                range = graph.xAxisRange();
                this.trigger('scroll', {
                    range: {
                        start:  range[0],
                        end:    range[1]
                    },
                    direction: direction
                });
            }
            else if(context._active) {
                // Cancel click
                context._active = false;
                if (context._longClickTimer) {
                    clearTimeout(context._longClickTimer);
                    context._longClickTimer = null;
                }
                // Start scrolling
                Dygraph.startPan(event, graph, context);
            }
        },

        /**
         *
         */
        handleMouseOut: function(event, graph, context) {
            // Cancel click
            context._active = false;
            if (context._longClickTimer) {
                clearTimeout(context._longClickTimer);
                context._longClickTimer = null;
            }
            // Stop scrolling
            if(context.isPanning){
                Dygraph.endPan(event, graph, context);
            }
        },

        /**
         *
         */
        handleMouseUp: function(event, graph, context) {
            var $mouse = this.$el.find('.charts');

            $mouse.css('cursor', 'pointer');

            // Cancel long click
            if (context._longClickTimer) {
                clearTimeout(context._longClickTimer);
                context._longClickTimer = null;
            }
            // Stop scrolling
            if(context.isPanning) {
                Dygraph.endPan(event, graph, context);
            }
        },

        /**
         *
         */
        handleMouseWheel: function(event, graph, context) {
        },

        /**
         *
         */
        handleTouchEnd: function(event, graph, context) {
        },

        /**
         *
         */
        handleTouchMove: function(event, graph, context) {
        },

        /**
         *
         */
        handleTouchStart: function(event, graph, context) {
        },

        /**
         * Shape data according to minutesPerBar setting before Charting.
         *  Handle differing minutes-per-bar, data comes in 5-min intervals
         *  by default, but need to combine other intervals (Hours/Weeks).
         * @param {array} List/Row of input records
         * @returns {array} List of output records, correctly shaped based on
         *  minutesPerBar property.
         */
        shapeDataToMinutesPerBar: function(input) {
            var divider =       this.minutesPerBar / minutesPerRecord,
                msPerBar =      this.minutesPerBar * 60000, // milliseconds per
                output =        [],
                startIndex =    0,
                startData =     YOMPUI.utils.getUTCDateFromTimestamp(input[startIndex][indexTimestamp]),
                startBucket =   new Date(Math.ceil(startData.getTime() / msPerBar) * msPerBar),
                i =             0;

            if(divider > 1) {
                // shape/combine data for DAYS and WEEKS view

                // Skip over data that occured before our first bar start time
                while(
                    (startData < startBucket) &&
                    (startIndex < input.length) &&
                    (input[startIndex + 1])
                ) {
                    startIndex++;
                    startData = YOMPUI.utils.getUTCDateFromTimestamp(input[startIndex][indexTimestamp]);
                }

                // now shape into buckets based on divider
                for(i=startIndex; i<input.length; i+=divider) {
                    var maxValue =      0,
                        maxAnomaly =    0,
                        timestamp =     0,
                        j =             0;

                    for(j=0; j<divider; j++) {
                        var index = i + j;

                        if(input[index]) {
                            if(maxValue < input[index][indexValue]) {
                                maxValue = input[index][indexValue];
                            }
                            if(maxAnomaly < input[index][indexAnomaly]) {
                                maxAnomaly = input[index][indexAnomaly];
                            }
                        }
                    }

                    if(input[i - 1]) {
                        timestamp = YOMPUI.utils.getUTCDateFromTimestamp(input[i - 1][indexTimestamp]).getTime();
                        timestamp = new Date(Math.ceil(timestamp / msPerBar) * msPerBar);

                        output.push([
                            YOMPUI.utils.getUTCTimestamp(timestamp),
                            maxValue,
                            maxAnomaly
                        ]);
                    }
                }
                // return shaped data for DAYS/WEEKS views
                return output;
            }
            // data for HOURS view requires no shaping
            return input;
        },

        /**
         * Redraw FaceOfYOMP/DyGraphs Chart with new Data, Ranges, etc.
         */
        updateChart: function() {
            var annotations = null;
            if(this.chart && this.chart.updateOptions) {
                if(annotations = this.getFormattedAnnotations()) {
                    this.chart.setAnnotations(annotations, true);
                }
                this.chart.updateOptions({
                    dateWindow: [ this.range.view.start, this.range.view.end ],
                    file:       this.getFormattedData()
                });
            }
        },

        /**
         * Update minutes-per-bar for this row and redraw.
         * @param {number} minutes Minutes per bar.
         */
        updateMinutesPerBar: function(minutes) {
            this.minutesPerBar = minutes;
            this.updateChart();
        },

        /**
         * Dygraph callback used to format X axis label according to minutesPerBar.
         *
         * @param {Date} date date value to be formatted
         * @return {string} Formatted label
         * @see http://dygraphs.com/options.html#axisLabelFormatter
         */
        formatXLabel: function(date) {
            var perBar = this.site.charts.instance.anomaly.minutesPerBar;
            var label = "";
            switch(this.minutesPerBar) {
                case perBar.hours:
                    // Format date as '12:05'
                    var min = date.getMinutes();
                    var hour =  date.getHours() % 12;
                    label = (hour == 0 ? 12 : hour) + ":" + (min < 10 ? '0' + min : min);
                    // Make every round hour bold
                    if (min == 0) {
                        label = '<span class="YOMP-embed-charts-label-bold">'+label+"</span>";
                    }
                    break;
                case perBar.days:
                    // Format date as '3p'
                    var am = date.getHours() >= 12 ? 'p' : 'a';
                    var hour = date.getHours() % 12;
                    label = (hour == 0 ? 12 : hour) + am;
                    // Make noon and midnight bold
                    if (hour == 0) {
                        label = '<span class="YOMP-embed-charts-label-bold">'+label+"</span>";
                    }
                    break;
                case perBar.weeks:
                    // Format date as 'S M T W T F S'
                    label = WEEKDAY[date.getDay()];
                    // Make mondays bold
                    if (label == 'M') {
                        label = '<span class="YOMP-embed-charts-label-bold">'+label+"</span>";
                    }
                    break;
            }
            return label;
        },

        /**
         * Dygraph callback used to generate date tick marks on X axis.
         *
         * @param  {Date or Number} fromDate
         * @param  {Date or Number} toDate
         * @param  {number} pixels   length of the axis in pixels
         * @param {function(string):*} opts Function mapping from option name
         *                                  to value, e.g. opts('labelsKMB')
         * @param {Dygraph} graph
         * @param  {[Array]} vals generate labels for these data values
         *
         * @return {[Array]}     [ { v: tick1_v, label: tick1_label[, label_v: label_v1] },
         *                         { v: tick2_v, label: tick2_label[, label_v: label_v2] },
         *                                ...
         *                      ]
         * @see dygraph-tickers.js
         */
        dateTicker: function(fromDate, toDate, pixels, opts, dygraph, vals) {
            var results =   [],
                start =     (fromDate instanceof Date) ?
                                fromDate.getTime() : fromDate,
                end =       (toDate instanceof Date) ?
                                toDate.getTime() : toDate,
                // Used to set start time
                tzoffset =  new Date().getTimezoneOffset() * 60000,
                perBar =    this.site.charts.instance.anomaly.minutesPerBar,
                interval =  300000;

            switch(this.minutesPerBar) {
                case perBar.hours:
                    // 15 minutes
                    interval = 900000;
                    // Round to the next 15 minutes
                    start = Math.floor(start/900000) * 900000;
                    break;
                case perBar.days:
                    // 3 hours
                    interval = 10800000;
                    // Round to the day
                    start = Math.floor(start/86400000) * 86400000 + tzoffset;
                    break;
                case perBar.weeks:
                    // 24 hours
                    interval = 86400000;
                    // Round to the day
                    start = Math.floor(start/86400000) * 86400000 + tzoffset;
                    break;
            }

            for(i=start; i<end; i+=interval) {
                results.push({
                    v:      i,
                    label:  this.formatXLabel(new Date(i))
                });
            };

            return results;
        } /* this.dateTicker() */

    });

})();
