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

    /**
     * Backbone.View() - Embed: Charts > Rows > Row (Metric)
     */
    YOMPUI.EmbedChartsRowMetricView = YOMPUI.EmbedChartsRowView.extend({

        // Backbone.View properties

        className: 'YOMP-embed-charts-row-metric YOMP-embed-charts-row YOMP-panel',


        // Custom properties

        type: 'metric',

        detailExpanded: false,
        modelId:        null,


        // Backbone.View methods

        /**
         * Backbone.View.initialize() METRIC row
         */
        initialize: function(options) {
            YOMPUI.EmbedChartsRowView.prototype.initialize.call(this, options);

            this.modelId = options.modelId;

            this.chartOptions.axisLabelColor =  this.color.gray.med.toHex();
            this.chartOptions.axisLineColor =   this.color.gray.lite.toHex();
        },

        /**
         * Backbone.View.render() METRIC row
         */
        render: function(options) {
            var formattedData = this.getFormattedData(),
                id = this.modelId,
                viewData = {
                    baseUrl:    NTA.baseUrl,
                    unit:       this.msgs.units[this.models[0].get('name')] ,
                    msgs:       this.msgs,
                    site:       this.site,
                    id:         id,
                    display:    this.models[0].get('metric')
                },
                graph = null;

            if (typeof(viewData.unit) == "undefined") { 
                try {
                    // try to get the unit from the metricSpec (mostly for custom metrics)
                    viewData.unit = this.models[0].get('parameters')['metricSpec']['unit']; 
                }
                catch(err) {
                    viewData.unit = "None";
                }
            }

            // render row markup
            this.$el.html(this.template(viewData));

            // Show unit
            this.$el.find('.unit').show();

            // draw row chart
            this.chart = new NuBarGraph(
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
         * Format METRIC MODEL data to be sent to FaceOfYOMP/DyGraphs chart
         * @returns {array} List of datapoints (themselves arrays) ready for
         *  FaceOfYOMP/Dygraphs.
         */
        getFormattedData: function() {
            var metricData = this.datas[this.modelId].get('data'),
                metricDataShaped = this.shapeDataToMinutesPerBar(metricData),
                formattedData = this.formatAnomalyModelOutputData(metricDataShaped);

            return formattedData.data;
        }

    });
})();
