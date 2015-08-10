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
        indexAnomaly =      _site.charts.instance.anomaly.index.anomaly;

    /**
     * Backbone.View() - Embed: Charts > Rows > Row (Instance)
     */
    YOMPUI.EmbedChartsRowInstanceView = YOMPUI.EmbedChartsRowView.extend({

        // Backbone.View properties

        className: 'YOMP-embed-charts-row-instance YOMP-embed-charts-row YOMP-panel',


        // Custom properties

        type: 'instance',

        instanceId: null,
        displayName: null,

        // Backbone.View methods

        /**
         * Backbone.View.initialize() INSTANCE row
         */
        initialize: function(options) {
            YOMPUI.EmbedChartsRowView.prototype.initialize.call(this, options);

            this.chartOptions.axisLabelColor =  this.color.gray.lite.toHex();
            this.chartOptions.axisLineColor =   this.color.white.toHex();

            // Get Fully qualified Instance ID from the first model.
            // Use this value when referencing instances using the API.
            this.instanceId =  this.models[Object.keys(this.models)[0]].get('server');

            // Get instance display name
            this.displayName = this.models[Object.keys(this.models)[0]].get('display_name');
            
            // Get instance tag name if exists
            this.tagName =  this.models[Object.keys(this.models)[0]].get('tag_name');
        },

        /**
         * Backbone.View.render() INSTANCE row
         */
        render: function(options) {
            var formattedData = this.getFormattedData(),
                instance = this.instance,
                id = 'chart-' + instance,
                $chart = null,
                viewData = {
                    baseUrl:    NTA.baseUrl,
                    msgs:       this.msgs,
                    unit:       null,
                    site:       this.site,
                    id:         instance,
                    display:    this.displayName
                },
                graph = null;

            // render row markup
            this.$el.html(this.template(viewData));

            // draw row chart
            this.chart = new NuBarGraph(id, formattedData, this.chartOptions);
            this.chart.render();

            if (this.annotations) {
                this.chart.setAnnotations(this.getFormattedAnnotations());
            }
            YOMPUI.EmbedChartsRowView.prototype.render.call(this, options);
            return this;
        },


        // Custom methods

        /**
         * Handle annotation click event. Called whenever the user clicks on an
         * annotation
         * @param {object} annotation: the native dygraph annotation
         * @param {object} point: the point associated with the annotation
         * @param {object} chart: the reference dygraph
         * @param {object} event: the mouse event
         * See http://dygraphs.com/options.html#Annotations
         */
        handleAnnotation: function(annotation, point, chart, event) {
            // Show annotation list for the clicked annotation timestamp
            var from = YOMPUI.utils.getUTCTimestamp(new Date(annotation.x));
            var to = YOMPUI.utils.getUTCTimestamp(new Date(annotation.x + this.minutesPerBar * 60000));
            var server = this.instanceId;
            var filteredAnnotations = this.annotations.filter(function(model) {
                return model.get('server') == server &&
                       model.get('timestamp') >= from &&
                       model.get('timestamp') < to;
            });

            // Open Annotation List
            var view = new YOMPUI.AnnotationListView({
                api:          this.api,
                instance:     this.instanceId,
                tagName:      this.tagName,  
                annotations:  filteredAnnotations,
                flag:         annotation
            });
            view.render();
            // Update annotation flag to use "selected" class
            annotation.div.className = annotation.cssClass + "-selected";
            return view;
        },

        /**
         * Format annotations to be sent to Dygraph chart.
         * @see http://dygraphs.com/annotations.html
         * @see http://dygraphs.com/jsdoc/symbols/Dygraph.html#setAnnotations
         * @returns {array} List of annotations ready for Dygraph's
         *                  "setAnnotations" method.
         */
        getFormattedAnnotations: function() {
            // Filter annotations by instance id
            var filteredAnnotations = this.annotations.where({ server: this.instanceId });

            // Group annotations by minutes per bar
            var msPerBar = this.minutesPerBar * 60000;
            var groupedAnnotations = _.groupBy(filteredAnnotations,
                    function(ann) {
                        var timestamp = YOMPUI.utils.getUTCDateFromTimestamp(ann.get('timestamp'));
                        return Math.floor(timestamp.getTime() / msPerBar) * msPerBar;
                    });

            var output = [];

            // Create dygraph annotation for each grouped time
            for(var timestamp in groupedAnnotations) {
                output.push({
                  x: parseInt(timestamp), // Annotation timestamp value
                  series: "Y1", // Default Y series
                  tickHeight: 0, // Don't draw tick line.
                  cssClass: "YOMP-embed-charts-row-annotation",
                  text:"",
                  clickHandler: this.handleAnnotation.bind(this)
                });
            }
            return output;
        },

        /**
         * Format INSTANCE data to be sent to FaceOfYOMP/DyGraphs chart
         * @returns {array} List of datapoints (themselves arrays) ready for
         *  FaceOfYOMP/Dygraphs.
         */
        getFormattedData: function() {
            var instanceData = this.getInstancesFromMetrics(),
                instanceDataShaped = this.shapeDataToMinutesPerBar(instanceData),
                formattedData = this.formatAnomalyModelOutputData(instanceDataShaped);

            return formattedData.data;
        },

        /**
         * Flatten multiple metric rows down to single instance rows.
         *  Also handle differing minutes-per-bar that comes from
         *  Hours/Days/Weeks tabs.
         * @returns {array} List of instance data points (combined metric data
         *  points).
         */
        getInstancesFromMetrics: function() {
            var output = [];

            // Combine Metric data into a single Instance data
            Object.keys(this.datas).forEach(function(modelId) {
                var model = this.datas[modelId],
                    data = model.get('data');

                for(i=0; i<data.length; i++) {
                    if(! output[i]) {
                        output[i] = [];
                    }

                    // metric timestamp
                    if(! output[i][indexTimestamp]) {
                        output[i][indexTimestamp] = data[i][indexTimestamp];
                    }

                    // metric value
                    if(! output[i][indexValue]) {
                        output[i][indexValue] = 0;
                    }
                    if(data[i][indexValue] > output[i][indexValue]) {
                        output[i][indexValue] = data[i][indexValue];
                    }

                    // metric anom score
                    if(! output[i][indexAnomaly]) {
                        output[i][indexAnomaly] = 0;
                    }
                    if(data[i][indexAnomaly] > output[i][indexAnomaly]) {
                        output[i][indexAnomaly] = data[i][indexAnomaly];
                    }
                }
            }.bind(this));

            return output;
        }

    });
})();
