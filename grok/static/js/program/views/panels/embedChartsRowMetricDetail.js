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

    var _site = YOMPUI.msgs('site'),

        indexTimestamp =    _site.charts.instance.anomaly.index.timestamp,
        indexValue =        _site.charts.instance.anomaly.index.value,
        indexAnomaly =      _site.charts.instance.anomaly.index.anomaly,
        NUMBER_OF_Y_LABELS =4;

    /**
     * Backbone.View() - Embed: Charts > Rows > Row (Metric Detail)
     */
    YOMPUI.EmbedChartsRowMetricDetailView = YOMPUI.EmbedChartsRowView.extend({

        // Backbone.View properties

        className: 'YOMP-embed-charts-row-metric-detail YOMP-embed-charts-row YOMP-panel',


        // Custom properties

        type: 'detail',

        modelId: null,


        // Backbone.View methods

        /**
         * Backbone.View.initialize() METRIC row
         */
        initialize: function(options) {
            YOMPUI.EmbedChartsRowView.prototype.initialize.call(this, options);

            this.modelId = options.modelId;

            // override default anomaly chart options for a value data detail row

            delete this.chartOptions.plotter;
            delete this.chartOptions.valueRange;

            var axesOptions = {
                    x: {
                        axisLabelFontSize:  0
                    },
                    y: {
                        axisLabelColor:     '#fff',
                        axisLabelFontSize:  14,
                        axisLabelOverflow:  true,
                        axisLabelWidth:     20,
                        ticker:             this.valueTicker.bind(this)
                    }
                };

            $.extend(this.chartOptions, {
                axes:               axesOptions,
                axisLabelColor:     this.color.white.toHex(),
                axisLineColor:      this.color.gray.lite.toHex(),
                axisTickSize:       0,
                colors:             [this.color.blue.toHex()],
                drawXAxis:          true,
                drawYAxis:          true,
                height:             this.chartOptions.height + 40,  // detail graphs are taller
                strokeWidth:        2,
                yAxisLabelWidth:    0,
                yRangePad:          0
            });
        },

        /**
         * Backbone.View.render() METRIC row
         */
        render: function(options) {
            var formattedData = this.getFormattedData(),
                id = 'detail-' + this.modelId,
                viewData = {
                    baseUrl:    NTA.baseUrl,
                    msgs:       this.msgs,
                    site:       this.site,
                    unit:       null,
                    id:         id,
                    display:    this.models[0].get('metric')
                },
                graph = null;

            // render row markup
            this.$el.html(this.template(viewData));

            // Hide name
            this.$el.find('.name').hide();

            // draw row chart
            this.chart = new NuGraph(
                'chart-' + id,
                formattedData,
                this.chartOptions
            );
            this.chart.render();

            YOMPUI.EmbedChartsRowView.prototype.render.call(this, options);
            return this;
        },


        // Custom methods

        /**
         * Format Model data from API for DyGraphs to display charts
         * @param {object} modelOutput Object of YOMP metric model data output
         * @returns {object} Object formatted for FaceOfYOMP/Dygraphs display
         */
        formatModelOutputData: function(modelOutput) {
            var outputData =    [],
                outputLabels =  [ 'Time', 'Value' ];

            modelOutput.forEach(function(dataRow, i) {
                outputData.push([
                    YOMPUI.utils.getUTCDateFromTimestamp(dataRow[indexTimestamp]),
                    dataRow[indexValue]
                ]);
            });

            return {
                labels: outputLabels,
                data: outputData
            };
        },

        /**
         * Format METRIC MODEL data to be sent to FaceOfYOMP/DyGraphs chart
         * @returns {array} List of datapoints (themselves arrays) ready for
         *  FaceOfYOMP/Dygraphs.
         */
        getFormattedData: function() {
            var metricData = this.datas[this.modelId].get('data'),
                formattedData = this.formatModelOutputData(metricData);

            return formattedData.data;
        },

        /**
         * Dygraph callback used to generate value tick marks on Y axis.
         *
         * @param  {Number} fromValue
         * @param  {Number} toValue
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
        valueTicker: function(fromValue, toValue, pixels, opts, dygraph, vals) {
            var ticks =     [],
                interval =  (toValue - fromValue) / NUMBER_OF_Y_LABELS;
                decimals =  0,
                i =         0;

            if(interval > 0) {
                if(interval < 1) {
                    decimals = Math.ceil(-Math.log(interval)/Math.LN10);
                }

                for(i=0; i<=NUMBER_OF_Y_LABELS; i++) {
                    var val = fromValue + (i * interval),
                        label = new Number(val.toFixed(decimals)).toLocaleString();

                    ticks.push({
                        v: val,
                        label: label
                    });
                }
            }
            else {
                var label = new Number(fromValue.toFixed(decimals)).toLocaleString();

                ticks.push({
                    v: fromValue,
                    label: label
                });
            }

            return ticks;
        }

    });
})();
