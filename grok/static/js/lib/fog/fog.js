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
/*
 * requires: jquery
 */
(function() {

    var PALETTE = {
        blue: '#29aae1',
        green: '#e80e89',
        red: '#e31a1c'
    };

    var DEFAULT_OPTIONS = {
        width: 800,
        height: 600
    };

    var DYGRAPH_CALLBACKS = [
        'click', 'draw', 'highlight', 'pointClick',
        'underlay', 'unhighlight', 'zoom'
    ];

    /**
     * NuGraph is an extension of Dygraph, with some sensible defaults for
     * Numenta's use cases as well as one major variation from the Dygraph use
     * case: creating a NuGraph object will not render a chart. It will
     * construct a chart object, but the Dygraph constructor will not be called
     * until the render() function is called.
     *
     * Another ability of NuGraph the Dygraph lacks is the ability to specify
     * multiple callback functions for each event a chart might emit. The
     * Dygraph only allows one callback to be specified for each event that it
     * might emit. NuGraph provides an 'on' function so users can register
     * multiple functions as callbacks.
     *
     * This standard implementation uses the default Dygraph plotter. For other
     * graphs other than line graphs, you must provide a 'plotter' function
     * within the options. You can also use the NuBarGraph class for bar charts.
     *
     * @param elementId
     * @param data
     * @param options
     * @constructor
     */
    function NuGraph(elementId, data, options) {
        var me = this,
            mainCallbacks = {},
            cutStart = 0,
            cutStop = data.length,
            index;

        this._listeners = {};
        this._drawn = false;

        // trim data by date, either at beginning or end of data array
        if(options['dateStart'] || options['dateStop']) {
            for(index=0; index<data.length; index++) {
                if(
                    options['dateStart'] &&
                    (options['dateStart'] > new Date(data[index][0])) &&
                    (cutStart < index)
                ) {
                    cutStart = index;
                }
                if(
                    options['dateStop'] &&
                    (options['dateStop'] < new Date(data[index][0])) &&
                    (cutStop > index)
                ) {
                    cutStop = index;
                }
            }
            data.splice(0, cutStart);
            data.splice(cutStop - cutStart, data.length);
        }

        DYGRAPH_CALLBACKS.forEach(function(CB) {
            // For each dygraph callback, we'll create a function that will emit
            // an event for the callback type, allowing users to use the on()
            // function on NuGraph instances to register multiple event
            // listeners.
            var cbName = CB + 'Callback';
            mainCallbacks[cbName] = function() {
                var args = Array.prototype.slice.call(arguments, 0);
                args.unshift(CB);
                // Keeping track of whether this graph has been rendered yet or
                // not.
                if (CB === 'draw') {
                    me._drawn = true;
                }
                me._emit.apply(me, args);
            };
            // We'll also handle the case where users have specified a callback
            // directly like options.zoomCallback, which is the typical dygraph
            // way of specifying one callback.
            if (options[cbName]) {
                me.on(CB, options[cbName]);
            }
        });

        // Stash options so we can use them for Dygraph construction when we
        // render().
        this._args = [
            document.getElementById(elementId),
            data,
            $.extend({}, DEFAULT_OPTIONS, options, mainCallbacks)
        ];
    }
    NuGraph.prototype = YOMP.util.heir(Dygraph.prototype);
    NuGraph.prototype.constructor = Dygraph;

    /**
     * Currently emits all Dygraph callback events: 'click', 'draw',
     * 'highlight', 'pointClick', 'underlay', 'unhighlight', and 'zoom'.
     * @param event
     * @param callback
     */
    NuGraph.prototype.on = function(event, callback) {
        if (! callback || ! event) { return; }
        if (! this._listeners[event]) {
            this._listeners[event] = [];
        }
        this._listeners[event].push(callback);
    };

    NuGraph.prototype._emit = function() {
        var me = this,
            args = Array.prototype.slice.call(arguments, 0),
            event = args.shift();
        if (this._listeners[event]) {
            this._listeners[event].forEach(function(listener) {
                listener.apply(me, args);
            });
        }
    };

    NuGraph.parseYOMPDateString = function(dateTimeString) {
        var dateOut, dateTimeParts, dateParts, timeParts;
        // if the date string is parse-able, it will not return NaN,
        // and we can just create a Date normally
        if (! isNaN(Date.parse(dateTimeString))) {
            dateOut = new Date(dateTimeString);
        } else {
            dateTimeParts = dateTimeString.split(' ');
            dateParts = dateTimeParts.shift().split('-');
            timeParts = dateTimeParts.shift().split(':');
            dateOut = new Date(
                parseInt(dateParts[0], 10),     // year
                parseInt(dateParts[1], 10) - 1, // month
                parseInt(dateParts[2], 10),     // day
                parseInt(timeParts[0], 10),     // hours
                parseInt(timeParts[1], 10),     // minutes
                parseInt(timeParts[2], 10)      // seconds
            );
        }
        return dateOut;
    };

    /**
     * Syncs one NuGraph to another. When the x or y axis changes, this will
     * sync the charts together.
     * @param otherNuGraph
     * @param options
     */
    NuGraph.prototype.syncTo = function(otherNuGraph, options) {
        var me = this;
        options = options || {};
        otherNuGraph.on('draw', function() {
            var updatedOptions;
            // In case the chart I'm syncing to is also synced with me
            if (me.blockRedraw) { return; }
            this.blockRedraw = true;
            updatedOptions = {
                dateWindow: otherNuGraph.xAxisRange()
            };
            if (options.syncY) {
                updatedOptions.valueRange = otherNuGraph.yAxisRange()
            }
            // If this chart has not been drawn yet, we need to wait until then
            // before we can update our options.
            if (! me._drawn) {
                me.on('draw', function(graph, isInitial) {
                    if (isInitial) { me.updateOptions(updatedOptions); }
                });
            } else {
                me.updateOptions(updatedOptions);
            }
            this.blockRedraw = false;
        });
    };

    /**
     * Syncs the highlighted points between to charts. When one point is
     * highlighted, the other will set the same selected point as highlighted,
     * which displays both graph legends at once.
     * @param otherNuGraph
     */
    NuGraph.prototype.syncLegendTo = function(otherNuGraph) {
        var me = this;
        var highlightTimeoutId;
        otherNuGraph.on('highlight', function(event, x, points, row) {
            me.setSelection(me._dataIndexOf(x));
            if (highlightTimeoutId) {
                clearTimeout(highlightTimeoutId);
                highlightTimeoutId = undefined;
            }
        });
        otherNuGraph.on('unhighlight', function() {
            // Only unhighlight if there is a short period without another
            // highlight event, which means that the user has moused off the
            // chart entirely.
            highlightTimeoutId = setTimeout(function() {
                me.clearSelection();
            }, 10);
        });
    };

    /**
     * When you call getSelection() on a dygraph, it gives you the row indexed
     * off the current zoom, when you really might want the row index from the
     * beginning of the data. This allows me to pass the x value into this
     * function to get the actual data index outside the zoomed window.
     * @param x
     * @return {Number}
     * @private
     */
    NuGraph.prototype._dataIndexOf = function(x) {
        var i = 0;
        var index = -1;
        for (; i < this.rawData_.length; i++) {
            if (x === this.rawData_[i][0]) {
                index = i;
                break;
            }
        }
        return index;
    };

    /**
     * Draws the chart by calling the Dygraph constructor.
     */
    NuGraph.prototype.render = function(options) {
        var renderOptions = $.extend({}, this._args[2], (options || {}));
        Dygraph.apply(this, [this._args[0], this._args[1], renderOptions]);
    };

    /**
     * Standard Numenta HTML color palette for charts.
     * @type {Object}
     */
    NuGraph.PALETTE = PALETTE;

    window.NuGraph = NuGraph;

})();
/*
 * requires:    jquery
 *              nugraph.js
 */
(function(){

    function barChartPlotter(e) {
        var ctx = e.drawingContext;
        var points = e.points;
        var y_bottom = e.dygraph.toDomYCoord(0);
        var i;
        var color = new RGBColor(e.color);
        ctx.fillStyle = color.toRGB();
        // Find the minimum separation between x-values.
        // This determines the bar width.
        var min_sep = Infinity;
        for (i = 1; i < points.length; i++) {
            var sep = points[i].canvasx - points[i - 1].canvasx;
            if (sep < min_sep) min_sep = sep;
        }
        var bar_width = Math.floor(2.0 / 3 * min_sep);

        // Do the actual plotting.
        for (i = 0; i < points.length; i++) {
            var p = points[i];
            var center_x = p.canvasx;
            // The RGBColor class is provided by rgbcolor.js, which is
            // packed in with dygraphs.

            ctx.fillRect(center_x - bar_width / 2, p.canvasy,
                bar_width, y_bottom - p.canvasy);

            ctx.strokeRect(center_x - bar_width / 2, p.canvasy,
                bar_width, y_bottom - p.canvasy);
        }
    }
    /**
     * Standard bar chart.
     * @param elementId
     * @param data
     * @param options
     * @constructor
     */
    function NuBarGraph(elementId, data, options) {
        NuGraph.call(this, elementId, data,
            $.extend({}, {
                plotter: barChartPlotter
            }, options));
    }
    NuBarGraph.prototype = YOMP.util.heir(NuGraph.prototype);
    NuBarGraph.prototype.constructor = NuGraph;

    window.NuBarGraph = NuBarGraph;

})();/*
 * requires: jquery
 *           nugraph.js
 */

(function(){

    var DEFAULT_OPTIONS = {
        showRangeSelector: true,
        colors: [NuGraph.PALETTE.blue, NuGraph.PALETTE.green],
        rightGap: 0
    };

    /**
     * Prediction graph.
     * @param elementId
     * @param modelOutput
     * @param options
     * @constructor
     */
    function PredictionGraph(elementId, modelOutput, options) {
        var formattedOutput = this._formatModelOutputData(modelOutput);
        var nugraphOptions = $.extend({
            labels: formattedOutput.labels
        }, DEFAULT_OPTIONS, options);
        NuGraph.call(this, elementId, formattedOutput.data, nugraphOptions);
    }
    PredictionGraph.prototype = YOMP.util.heir(NuGraph.prototype);
    PredictionGraph.prototype.constructor = NuGraph;

    PredictionGraph.prototype._formatModelOutputData = function(modelOutput) {
        var meta = modelOutput.meta,
            outputData = [],
            outputLabels = [],
            temporalIndex,
            predictedFieldIndex,
            predictedFieldPredictionIndex,
            predictedFieldName,
            predictedFieldLabel,
            predictionSteps,
            extraRows = 1;

        temporalIndex = meta.timestampIndex;
        predictedFieldIndex = meta.predictedFieldIndex;
        predictedFieldPredictionIndex = meta.predictedFieldPredictionIndex;
        predictedFieldName = modelOutput.names[predictedFieldIndex];
        predictedFieldLabel = predictedFieldName.charAt(0).toUpperCase() +
                              predictedFieldName.slice(1);
        predictionSteps = meta.predictionSteps;

        // If there are predictionSteps, then there will be extra rows at the
        // end of the output, so we need to keep track of how many there will be.
        if (predictionSteps) {
            // The number of extra rows is the same as the max value within the
            // predictionSteps array.
            extraRows = predictionSteps.reduce(function(previous, current) {
                if (current > previous) {
                    return current;
                } else {
                    return previous;
                }
            }, 0);
        }

        // build the labels
        outputLabels.push('Time');
        outputLabels.push(predictedFieldLabel || 'Actual ');
        outputLabels.push('Predicted ' + predictedFieldLabel);

        // build the data
        modelOutput.data.forEach(function(dataRow, i) {
            var outputRow = [],
                value, prediction;

            // Ignores the first point and any extra points at the end of the
            // model output, which are data for dangling predictions (including
            // possible multi-step predictions, or step-ahead predictions when
            // the predictionSteps take us more than one time-step into the
            // future
            if (i === 0 || i >= modelOutput.data.length - extraRows) {
                return;
            }

            value = dataRow[predictedFieldIndex];
            prediction = parseFloat(dataRow[predictedFieldPredictionIndex]);

            outputRow.push(NuGraph.parseYOMPDateString(dataRow[temporalIndex]));
            outputRow.push(value === "" ? null : parseFloat(value));
            outputRow.push(prediction === "" ? null : parseFloat(prediction));
            outputData.push(outputRow);
        });
        return {
            labels: outputLabels,
            data: outputData
        };
    };

    window.PredictionGraph = PredictionGraph;
})();
/*
 * requires:    jquery
 *              nugraph.js
 *              nubargraph.js
 */
(function(){

    var DEFAULT_OPTIONS = {
        colors: [NuGraph.PALETTE.blue],
        valueRange: [0, 1],
        rightGap: 0
    };

    /*
     * API model output rows prediction details should be keyed by the prediction
     * value, but the floating point precision is unpredictable. So this function
     * tries all precisions from 12 to 3.
     */
    function findValueByFloatKey(map, keyFloat) {
        var precisionCountdown = 12,
            confidence;
		if (map[keyFloat]) {
			return map[keyFloat];
		}
        while (! confidence && precisionCountdown > 2) {
            confidence = map[keyFloat.toFixed(precisionCountdown--)];
        }
        return confidence;
    }

    function findConfidenceValueHack(details, predictionSteps, prediction) {
        var confidence;
        if (details) {
            if (predictionSteps) {
                confidence = findValueByFloatKey(details[predictionSteps[0]], prediction);
            } else {
                // assume one step when no predictionSteps are defined
                confidence = details[1][prediction];
            }
        }
        return confidence;
    }

    /**
     * Prediction confidence graph.
     * @param elementId
     * @param modelOutput
     * @param options
     * @constructor
     */
    function PredictionConfidenceGraph(elementId, modelOutput, options) {
        var formattedOutput = this._formatModelOutputData(modelOutput);
        var nugraphOptions = $.extend({
            labels: formattedOutput.labels
        }, DEFAULT_OPTIONS, options);
        NuBarGraph.call(this, elementId, formattedOutput.data, nugraphOptions);
    }
    PredictionConfidenceGraph.prototype = YOMP.util.heir(NuBarGraph.prototype);
    PredictionConfidenceGraph.prototype.constructor = NuBarGraph;

    PredictionConfidenceGraph.prototype._formatModelOutputData = function(modelOutput) {
        var predictionDetailsLabel = 'Prediction Details',
            meta = modelOutput.meta,
            outputData = [],
            outputLabels = ['Time', 'Confidence'],
            temporalIndex = meta.timestampIndex,
            predictedFieldPredictionIndex = meta.predictedFieldPredictionIndex,
            predictionDetailsIndex = modelOutput.names.indexOf(predictionDetailsLabel),
            predictionSteps = meta.predictionSteps,
            extraRows = 1;

        // If there are predictionSteps, then there will be extra rows at the
        // end of the output, so we need to keep track of how many there will be.
        if (predictionSteps) {
            // The number of extra rows is the same as the max value within the
            // predictionSteps array.
            extraRows = predictionSteps.reduce(function(previous, current) {
                if (current > previous) {
                    return current;
                } else {
                    return previous;
                }
            }, 0);
        }

        modelOutput.data.forEach(function(dataRow, i) {
            var details, hackedDetails;
            var prediction;
            var rawConfidence, confidence;

            // Ignores the first point and any extra points at the end of the
            // model output, which are data for dangling predictions (including
            // possible multi-step predictions, or step-ahead predictions when
            // the predictionSteps take us more than one time-step into the
            // future
            if (i === 0 || i >= modelOutput.data.length - extraRows) {
                return;
            }

            // The replace gets rid of the double quotes put into place by the
            // CSV formatting.
            details = dataRow[predictionDetailsIndex];
            prediction = parseFloat(dataRow[predictedFieldPredictionIndex]);

            // Conjure up the confidence number from the prediction details in a
            // hacky and magical way!
            confidence = findConfidenceValueHack(details, predictionSteps, prediction);

            outputData.push([
                NuGraph.parseYOMPDateString(dataRow[temporalIndex]),
                confidence
            ]);
        });
        return {
            labels: outputLabels,
            data: outputData
        };
    };

    window.PredictionConfidenceGraph = PredictionConfidenceGraph;

})();
/*
 * requires:    jquery
 *              nugraph.js
 *              nubargraph.js
 */
(function(){

    var DEFAULT_OPTIONS = {
        colors: [NuGraph.PALETTE.blue],
        valueRange: [0, 1],
        rightGap: 0
    };

    /**
     * Anomaly score graph.
     * @param elementId
     * @param modelOutput
     * @param options
     * @constructor
     */
    function AnomalyScoreGraph(elementId, modelOutput, options) {
        var formattedOutput = this._formatModelOutputData(modelOutput);
        var nugraphOptions = $.extend({
            labels: formattedOutput.labels
        }, DEFAULT_OPTIONS, options);
        NuBarGraph.call(this, elementId, formattedOutput.data, nugraphOptions);
    }
    AnomalyScoreGraph.prototype = YOMP.util.heir(NuBarGraph.prototype);
    AnomalyScoreGraph.prototype.constructor = NuBarGraph;

    AnomalyScoreGraph.prototype._formatModelOutputData = function(modelOutput) {
        var meta = modelOutput.meta,
            outputData = [],
            outputLabels = ['Time', 'Anomaly'],
            temporalIndex = meta.timestampIndex,
            anomalyIndex = meta.anomalyScoreFieldIndex,
            predictionSteps = meta.predictionSteps,
            extraRows = 1;

        // If there are predictionSteps, then there will be extra rows at the
        // end of the output, so we need to keep track of how many there will be.
        if (predictionSteps) {
            // The number of extra rows is the same as the max value within the
            // predictionSteps array.
            extraRows = predictionSteps.reduce(function(previous, current) {
                if (current > previous) {
                    return current;
                } else {
                    return previous;
                }
            }, 0);
        }

        modelOutput.data.forEach(function(dataRow, i) {
            // Ignores the first point and any extra points at the end of the
            // model output, which are data for dangling predictions (including
            // possible multi-step predictions, or step-ahead predictions when
            // the predictionSteps take us more than one time-step into the
            // future
            if (i === 0 || i >= modelOutput.data.length - extraRows) {
                return;
            }

            outputData.push([
                NuGraph.parseYOMPDateString(dataRow[temporalIndex]),
                parseFloat(dataRow[anomalyIndex])
            ]);
        });
        return {
            labels: outputLabels,
            data: outputData
        };
    };

    window.AnomalyScoreGraph = AnomalyScoreGraph;

})();
(function(){
    var DEFAULT_OPTIONS = {
        drawYAxis: false
    };

    /**
     * Prediction graph.
     * @param elementId
     * @param modelOutput
     * @param options
     * @constructor
     */
    function DanglingPredictionGraph(elementId, modelOutput, options) {
        PredictionGraph.call(this, elementId, modelOutput,
            $.extend({}, DEFAULT_OPTIONS, options));
    }
    DanglingPredictionGraph.prototype = YOMP.util.heir(PredictionGraph.prototype);
    DanglingPredictionGraph.prototype.constructor = PredictionGraph;

    DanglingPredictionGraph.prototype._getCopyOfOptionsWithUpdatedDateWindow = function(options) {
        var endDate,
            optionsCopy = $.extend({}, options);

        // adjust the dateWindow to only show the last two points in the data
        if (optionsCopy.dateWindow) {
            endDate = options.dateWindow[1];
            optionsCopy.dateWindow = [
                endDate, endDate + (this._timeInterval * 2)
            ];
        }
        return optionsCopy;
    };

    DanglingPredictionGraph.prototype._formatModelOutputData = function(modelOutput) {
        var formattedOutput, data, onePointBackTime, twoPointsBackTime;
        var danglingPredictionData = modelOutput.data[modelOutput.data.length - 1];
        var danglingPredictionValue = danglingPredictionData[modelOutput.meta.predictedFieldPredictionIndex];
        formattedOutput = this.constructor.prototype._formatModelOutputData.call(this, modelOutput);
        data = formattedOutput.data;
        // add one last point to the data, including the calculated time
        onePointBackTime = data[data.length - 1][0].getTime();
        twoPointsBackTime = data[data.length - 2][0].getTime();
        this._timeInterval = onePointBackTime - twoPointsBackTime;
        data.push([new Date(onePointBackTime + this._timeInterval), null, danglingPredictionValue]);
        return formattedOutput;
    };

    DanglingPredictionGraph.prototype.updateOptions = function(options, blockRedraw) {
        var optionsCopy = this._getCopyOfOptionsWithUpdatedDateWindow(options);
        this.constructor.prototype.updateOptions.call(this, optionsCopy, blockRedraw);
    };

    window.DanglingPredictionGraph = DanglingPredictionGraph;

})();/*
 * requires:    jquery,
 *              nugraph.js
 *              nubargraph.js
 *              predictiongraph.js
 *              danglingpredictiongraph.js
 *              predictionconfidencegraph.js
 *              anomalyscoregraph.js
 */

(function() {

    var JSON_CAP_REGEX = /,"{|}",/;
    // TODO: make these user-configurable
    var PREDICTION_HEIGHT_PERCENTAGE = 0.80;
    var PREDICTION_WIDTH_PERCENTAGE = 0.80;

    var DEFAULT_OPTIONS = {
        width: 800,
        height: 600
    };

    // Builds up the listeners array.
    function addListener(listeners, name, callback) {
        if (! listeners[name]) {
            listeners[name] = [];
        }
        listeners[name].push(callback);
    }

    // Emits an event to the appropriate listeners
    function emit(listeners, name, payload) {
        if (listeners[name]) {
            listeners[name].forEach(function(listener) {
                listener(payload);
            });
        }
    }

    // Checks to see if a model is valid. This function is asynchronous because
    // I'm not sure if we'll need to go to the network or file system to find
    // out.
    function modelIsValid(model, callback) {
        // This is here for future validations. For now we just assert that the
        // model object exists.
        var err = null;
        if (! model) {
            err = new Error('Model given to FaceOfYOMP does not exist.');
        }
        callback(err);
    }

    function thereAreNoOutputRows(rows) {
        return (! rows.meta || rows.data.length === 0 || rows.data.names === 0);
    }

    function getPredictedFieldTitle(rows) {
        var title = 'Unknown';
        if (typeof rows !== 'string') {
            title = 'Predicted ' + rows.names[rows.meta.predictedFieldIndex];
        }
        return title;
    }

    // Essentially applies shift=true to CSV data. Does not touch anything
    // except the column specified.
    function shiftColumnDownOne(array, columnIndexToShift) {
        // tempSave is only used inside the for block, but JS can't scope within
        // a block, so it's declared here.
        var tempSave, lastValue = '', rowIndex = 0, row;
        for (; rowIndex < array.length; rowIndex++) {
            row = array[rowIndex];
            tempSave = row[columnIndexToShift];
            array[rowIndex][columnIndexToShift] = lastValue;
            lastValue = tempSave;
        }
        return array;
    }

    // Constructs a meta data object like what is attached to model output
    // coming from the API by inspecting column names. Certain patterns in the
    // names like "(temporal)" and "(predicted)" are the hints we need.
    function interpolateMetaData(names) {
        var bestPredictionName = 'Best Prediction',
            predictedFieldIndex, predictedFieldPredictionIndex, timestampIndex;
        names.forEach(function(name, nameIndex) {
            if (name === bestPredictionName) {
                predictedFieldPredictionIndex = nameIndex;
            } else if (name.indexOf('(temporal)') > -1) {
                timestampIndex = nameIndex;
            } else if (name.indexOf('(predicted)') > -1) {
                predictedFieldIndex = nameIndex;
            }
        });
        return {
            predictedFieldPredictionIndex: predictedFieldPredictionIndex,
            predictedFieldIndex: predictedFieldIndex,
            timestampIndex: timestampIndex
        }
    }

    // A little bit of a hacky way to parse a line of CSV output that contains
    // prediction details, which is a JSON string. So it could include commas.
    function splitCsvLine(line) {
        var pieces, start, predictionDetails, end, output;
        // If this is the "names" line, we ignore it.
        if (! JSON_CAP_REGEX.test(line)) {
            return line.split(',');
        }
        // There is probably a better way to do this, but it works. We split the
        // line around the JSON prediction details string, then reconstructed
        // the output array by splitting the parts of the line around it.
        pieces = line.split(JSON_CAP_REGEX);
        start = pieces[0];
        predictionDetails = '{' + pieces[1] + '}';
        // The replace gets rid of the double quotes put into place by the
        // CSV formatting.
        predictionDetails = predictionDetails.replace(/""/g,'"');
        predictionDetails = JSON.parse(predictionDetails);
        end = pieces[2];
        output = start.split(',');
        output.push(predictionDetails);
        output = output.concat(end.split(','));
        return output;
    }

    // Convert a CSV clob into a modelOutput object just like you might get from
    // the API.
    function csvToModelOutput(inputString) {
        var csvArray = inputString.split('\n').map(function(line) {
            return splitCsvLine(line);
        });
        var names = csvArray.shift();
        var meta = interpolateMetaData(names);
        return {
            data: shiftColumnDownOne(csvArray, meta.predictedFieldPredictionIndex),
            names: names,
            meta: meta
        }
    }

    // Looks up a CSV file and converts it into the same format as the API
    // returns for model output so FOG can understand it.
    function translateCsvToModelOutputRows(csvUri, callback) {
        $.ajax(csvUri, {
            success: function(resp) {
                callback(null, csvToModelOutput(resp))
            },
            failure: function(err) {
                callback(new Error('Failure getting CSV from ' + csvUri));
            }
        });
    }

    /**
     * Face of YOMP main component.
     * @param element
     * @param input YOMP.Model object or CSV URI
     * @param options
     * @constructor
     */
    function FaceOfYOMP(element, input, options) {
        if (typeof element === 'string') {
            this.rootId = element;
            this.$fog = $('#' + element);
        } else {
            this.$fog = element;
            this.rootId = this.$fog.attr('id') || 'fog-' + new Date().getTime()
        }
        this.allGraphs = [];
        this.predictionGraphId = this.rootId + '-predictions';
        this.confidenceGraphId = this.rootId + '-confidence';
        this.danglingPredictionGraphId = this.rootId + '-dangling';
        this.legendHeight = 44;     // 22px * 2, fog.css, .fog-legend-*
        this.legendKey = new Date().getTime();
        this.cachedData = (options && options.cachedData) ? options.cachedData : null;
        this.dynamic = (options && options.dynamic) ? options.dynamic : false;
        this.autoScroll = this.dynamic ? true : false;
        this.rangeXwidth = null;  // chart range selector X width, used for auto-scroll

        // Input may be:
        //  (a) a path for a CSV file to load
        //  (b) a YOMP.Model object (optionally accompanied by cachedData)
        if (typeof input === 'string') {
            // input is CSV
            this.csvUri = input;
        } else if (input.constructor &&
                   input.constructor.NAMESPACE &&
                   input.constructor.NAMESPACE === 'models') {
            // input is a YOMP.Model instance
            this.model = input;
        } else {
            throw new Error('FaceOfYOMP expected a Model Instance or CSV');
        }

        this.options = $.extend({}, DEFAULT_OPTIONS, options);
        this.listeners = {};
        this.renderedGraphs = 0;
    }

    FaceOfYOMP.prototype.on = function(name, callback) {
        addListener(this.listeners, name, callback);
    };

    FaceOfYOMP.prototype.render = function() {
        var me = this,
            predictionSteps = me.model.get('predictionSteps');

        if (me.model) {
            modelIsValid(me.model, function(err) {
                if (err) {
                    return me._reportFatalError('render', err);
                }
                
                if(me.cachedData) {
                    // use cached data from localStorage
                    me._modelOutput = me.cachedData;
                    me._createAndRenderGraphs(me.cachedData, predictionSteps);
                } else {
                    // no cached data, get fresh data
                    var dataCallOptions = { shift: true };
                    
                    if (me.options.maxOutputRows) {
                        dataCallOptions.limit = me.options.maxOutputRows;
                    }
                    me.model.getOutputData(dataCallOptions, function(err, rows) {
                        if(err) {
                            return me._reportFatalError('render', err);
                        }
                        if(rows.meta.timestampIndex < 0) {
                            return me._reportFatalError('render', new Error('Cannot display, model does not have timestamps.'));
                        }
                        me._modelOutput = rows;
                        me._createAndRenderGraphs(rows, predictionSteps);
                    });
                }
            });
        } else if (me.csvUri) {
            translateCsvToModelOutputRows(me.csvUri, function(err, rows) {
                if (err) {
                    return me._reportFatalError('render', err);
                }
                me._createAndRenderGraphs(rows);
            });
        } else {
            throw new Error('Cannot execute Face of YOMP without a model or a csv URI!');
        }
    };

    FaceOfYOMP.prototype._createAndRenderGraphs = function(rows, predictionSteps) {
        var me = this,
            predictionGraph,
            danglingPredictionGraph,
            confidenceGraph,
            predictionGraphOptions,
            danglingPredictionGraphOptions,
            confidenceGraphOptions,
            anomalyGraphOptions;
        
        // make sure there is data
        if (thereAreNoOutputRows(rows)) {
            return this._reportFatalError(
                'render',
                new Error('Model ' + this.model.getId() + ' has no output data.')
            );
        }

        function mainDrawCallback(graph, isInitial) {
            if (isInitial) {
                me.renderedGraphs++;
            }
            me._graphDrawn.apply(me, arguments);
        }

        // If predictionSteps is provided, attach to the output data and we'll
        // use it later.
        if (predictionSteps) {
            rows.meta.predictionSteps = predictionSteps;
        }

        // prepare the prediction graph options
        predictionGraphOptions = {
            title: 'Predictions',
            height: Math.floor((this.options.height * PREDICTION_HEIGHT_PERCENTAGE) - this.legendHeight),
            width: Math.floor(this.options.width * PREDICTION_WIDTH_PERCENTAGE),
            labelsShowZeroValues: false,
            labelsDiv: 'fog-legend-top-' + this.legendKey
        };
        // provides the proper stroke pattern for the prediction line
        predictionGraphOptions[getPredictedFieldTitle(rows)] = {
            strokePattern: Dygraph.DASHED_LINE
        };

        // prepare the dangling prediction graph options
        danglingPredictionGraphOptions = {
            title: 'Next Prediction',
            interactionModel: null,
            height: Math.floor((this.options.height * PREDICTION_HEIGHT_PERCENTAGE) - this.legendHeight),
            width: Math.floor(this.options.width * (1 - PREDICTION_WIDTH_PERCENTAGE)),
            labelsDiv: 'fog-legend-top-' + this.legendKey
        };
        // provides the proper stroke pattern for the prediction line
        danglingPredictionGraphOptions[getPredictedFieldTitle(rows)] = {
            strokePattern: Dygraph.DASHED_LINE
        };

        // prepare the average error graph data and options
        confidenceGraphOptions = {
            title: 'Prediction confidence',
            height: Math.floor(this.options.height * (1 - PREDICTION_HEIGHT_PERCENTAGE)),
            width: Math.floor(this.options.width * PREDICTION_WIDTH_PERCENTAGE),
            labelsDiv: 'fog-legend-bottom-' + this.legendKey
        };
        // prepare the anomaly score graph data and options
        anomalyGraphOptions = {
            title: 'Anomaly score',
            height: Math.floor(this.options.height * (1 - PREDICTION_HEIGHT_PERCENTAGE)),
            width: Math.floor(this.options.width * PREDICTION_WIDTH_PERCENTAGE),
            labelsDiv: 'fog-legend-bottom-' + this.legendKey
        };

        this._prepareDomForFogCharts();

        // Create prediction graph.
        this.predictionGraph = predictionGraph = new PredictionGraph(
            this.predictionGraphId, rows, predictionGraphOptions
        );
        predictionGraph.on('draw', mainDrawCallback);
        this.allGraphs.push(predictionGraph);

        // Create dangling prediction graph.
        danglingPredictionGraph = new DanglingPredictionGraph(
            this.danglingPredictionGraphId, rows, danglingPredictionGraphOptions
        );
        danglingPredictionGraph.on('draw', mainDrawCallback);
        this.allGraphs.push(danglingPredictionGraph);

        if(me.model.get('modelType') === 'anomalyDetector') {
            // put anomaly score graph on top
            confidenceGraph = new AnomalyScoreGraph(
                this.confidenceGraphId, rows, anomalyGraphOptions
            );
        } 
        else {
            // put prediction confidence graph on top
            confidenceGraph = new PredictionConfidenceGraph(
                this.confidenceGraphId, rows, confidenceGraphOptions
            );
        }
        confidenceGraph.on('draw', mainDrawCallback);
        this.allGraphs.push(confidenceGraph);

        // Sync the graphs to each other.
        danglingPredictionGraph.syncTo(predictionGraph, {syncY: true});
        confidenceGraph.syncTo(predictionGraph);
        predictionGraph.syncTo(confidenceGraph);
        confidenceGraph.syncLegendTo(predictionGraph);
        predictionGraph.syncLegendTo(confidenceGraph);

        predictionGraph.render();
        danglingPredictionGraph.render();
        confidenceGraph.render();
        
        me._handleDynamicCharts(); 
    };

    /**
     * Handle dynamic chart updates
     */    
    FaceOfYOMP.prototype._handleDynamicCharts = function() {
        var me = this,
            index,
            predictMonitor,
            graph,
            newData,
            graphX, graphXmin, graphXmax, graphXrange, graphXdiff;

        // dynamic self-updating chart
        if(me.dynamic) {
            predictMonitor = new YOMP.PredictionMonitor(me.model, {
                lastRowIdSeen: me._modelOutput.data[me._modelOutput.data.length - 2][0]
            });
           
            predictMonitor.onData(function(input) {
                if(! input || ! input.data || input.data.length <= 0) return;

                // clear out last prediction field
                me._modelOutput.data.pop(); 
                // concat old data + new data 
                me._modelOutput.data = me._modelOutput.data.concat(input.data); 
             
                // for all 3 graphs 
                for(index=0; index<me.allGraphs.length; index++) { 
                    graph = me.allGraphs[index];
                    // reformat modelOutput to DyGraph-ready input
                    newData = graph._formatModelOutputData(me._modelOutput); 
                    // update and redraw chart
                    graph.updateOptions({ file: newData.data });
                    // if user changes zoom, turn off auto-scroll-to-right 
                    graph.updateOptions({
                        clickCallback: function() {
                            me.autoScroll = false;
                        },
                        zoomCallback: function(rangeXmin, rangeXmax, yRanges) {
                            me.autoScroll = false;
                            
                            // if range slider is moved far to the right, re-enable auto scroll 
                            graphX = graph.xAxisExtremes();
                            graphXmin = graphX[0];
                            graphXmax = graphX[1];
                            graphXrange = graphXmax - graphXmin;
                            graphXdiff = graphXmax - rangeXmax;
                            if(graphXdiff < (graphXrange * .01)) {
                                me.rangeXwidth = Math.floor(rangeXmax - rangeXmin);
                                me.autoScroll = true;
                            }
                        }
                    });
                    
                    // auto-scroll to the right
                    if(me.autoScroll) {
                        graphX = graph.xAxisExtremes();
                        graphXmin = graphX[0];
                        graphXmax = graphX[1];
                        if(! me.rangeXwidth) {
                            me.rangeXwidth = Math.floor((graphXmax - graphXmin) * 0.2);
                        }
                        graph.updateOptions({ 'dateWindow': [ graphXmax - me.rangeXwidth, graphXmax ] });
                    }
                }
            });
            
            predictMonitor.onError(function(error) {
                console.log('Error:', error);
            });
            
            predictMonitor.start();
        }
    };

    FaceOfYOMP.prototype._prepareDomForFogCharts = function() {
        var tableString = '<table class="fog"><tbody>';
        tableString += '<tr class="fog-top"><td id="' + this.confidenceGraphId + '" class="fog-left confidence-graph"></td><td class="fog-right"></td></tr>';
        tableString += '<tr class="fog-bottom"><td id="' + this.predictionGraphId + '" class="fog-left prediction-graph"></td>';
        tableString += '<td id="' + this.danglingPredictionGraphId + '" class="fog-right dangling-prediction-graph"></td></tr>';
        tableString += '<tr class="fog-legend"><td colspan="2"><div id="fog-legend-top-' + this.legendKey + '" class="fog-legend-top" /><div id="fog-legend-bottom-' + this.legendKey + '" class="fog-legend-bottom" /></td></tr>';
        tableString += '</tbody></table>';
        this.$fog.html(tableString);
    };

    FaceOfYOMP.prototype._reportFatalError = function(eventName, err) {
        // find listeners for the event
        var listeners = this.listeners[eventName];
        // if there are no listeners for this error, we will throw the error
        if (! listeners) {
            throw err;
        }
        // otherwise, we'll just emit it
        emit(this.listeners, eventName, err);
    };

    FaceOfYOMP.prototype._graphDrawn = function(graph, isInitialDraw) {
        var $danglingGraph,
            me = this,
            pointsToDisplay = this.options.initialPointsToDisplay;
        if (isInitialDraw && this.renderedGraphs === this.allGraphs.length) {
            // Hack to hide the range selector in the dangling chart.
            $danglingGraph = $('#' + this.danglingPredictionGraphId);
            $danglingGraph.find('.dygraph-rangesel-bgcanvas').hide();
            $danglingGraph.find('.dygraph-rangesel-fgcanvas').hide();
            $danglingGraph.find('.dygraph-rangesel-zoomhandle').hide();
            // apply the initial data window
            if (pointsToDisplay) {
                setTimeout(function() {
                    var data = me.predictionGraph.rawData_;
                    me.predictionGraph.updateOptions({
                        dateWindow: [
                            data[data.length - pointsToDisplay][0],
                            data[data.length - 1][0]
                        ]
                    });
                }, 10);
            }

            emit(this.listeners, 'render');
        }
    };

    FaceOfYOMP.prototype.destroy = function() {
        this.allGraphs.forEach(function(dygraph) {
            dygraph.destroy();
        });
    };

    FaceOfYOMP.prototype.__version__ = '0.4';

    window.FaceOfYOMP = FaceOfYOMP;

})();
