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

    var _viewName = 'embed-charts-rows',
        _site =     YOMPUI.msgs('site'),

        _defaultTab = 'days',

        indexAnomaly =      _site.charts.instance.anomaly.index.anomaly,
        indexTimestamp =    _site.charts.instance.anomaly.index.timestamp,
        indexValue =        _site.charts.instance.anomaly.index.value,

        NOW =       new Date(),
        SECONDS =   1000,
        MINUTES =   SECONDS * 60,
        HOURS =     MINUTES * 60,
        DAYS =      HOURS * 24,
        WEEKS =     DAYS * 7;


    /**
     * Backbone.View() - Embed: Charts > Rows
     */
    YOMPUI.EmbedChartsRowsView = Backbone.View.extend({

        // Backbone.View properties

        events:     {},
        template:   _.template($('#' + _viewName + '-tmpl').html()),


        // Custom properties

        msgs: YOMPUI.msgs(_viewName + '-tmpl'),
        site: _site,

        api: null,
        collections: {
            models: null,
            annotations: null
        },
        interval: null,
        isLoading: null,
        isBusy: null,
        minutesPerBar: null,
        models: {
            datas: {}
        },
        range: {
            data: {
                start:  null,
                end:    null
            },
            view: {
                start:  null,
                end:    null
            }
        },
        state: null,
        views: {
            markers:    null,
            rows:       []
        },
        width: null,


        // Backbone.View methods

        /**
         * Backbone.View.initalize()
         */
        initialize: function(options) {
            var minutesPerBar = this.site.charts.instance.anomaly.minutesPerBar,
                tab =           YOMPUI.utils.getUrlParam('tab') || _defaultTab,
                initDataSize =  {
                    hours:  10 * HOURS,
                    days:   5 * DAYS,
                    weeks:  5 * WEEKS
                };

            if(!(tab in minutesPerBar)) {
                tab = _defaultTab;
            }

            // init
            this.api =      options.api;
            this.width =    options.width;

            // 'instance' or 'metric' view
            this.state = 'instance';

            this.isLoading = false;

            // charts date ranges - init defaults
            //  start with 5 days of data for the DAYS view
            this.range.data.start = new Date(NOW);
            this.range.data.start.setTime(NOW.getTime() - initDataSize[tab]);
            this.range.data.end = NOW;
            // view range will be set intelligently later
            this.range.view.start = new Date(NOW);
            this.range.view.end = NOW;

            this.collections.annotations = new YOMPUI.AnnotationsCollection(
                [], {api : this.api}
            );

            // set minutes-per-bar default & update Ranges
            this.updateMinutesPerBar(
                options.minutesPerBar || minutesPerBar[tab]
            );

            // collections
            this.collections.models = options.collections.models;
        },

        /**
         * Backbone.View.render()
         */
        render: function() {
            var minutesPerBar = this.site.charts.instance.anomaly.minutesPerBar,
                tab =           YOMPUI.utils.getUrlParam('tab') || _defaultTab,
                dataHandles =   [],
                promises =      [],
                instances =     this.collections.models.groupByInstance(),
                $tabs =         null,
                data =          {
                    baseUrl:    NTA.baseUrl,
                    msgs:       this.msgs,
                    site:       this.site
                };

            if(!(tab in minutesPerBar)) {
                tab = _defaultTab;
            }

            YOMPUI.utils.throb.start(this.site.state.loading);
            this.$el.html(this.template(data));

            // css switch to correct tab here
            $tabs = $('.YOMP-embed-charts-tabs > .nav-tabs');
            $tabs.find('li').removeClass('active');
            $tabs.find('li.' + tab).addClass('active');

            // create data handles
            Object.keys(instances).forEach(function(instance) {
                instances[instance].forEach(function(model) {
                    var data = new YOMPUI.ModelDataModel(
                            { id: model.id },
                            {
                                api:    this.api,
                                site:   this.site
                            }
                        );

                    if(!(instance in this.models.datas)) {
                        this.models.datas[instance] = {};
                    }
                    this.models.datas[instance][model.id] = data;
                }.bind(this));
            }.bind(this));

            // init instance row views
            Object.keys(instances).forEach(function(instance) {
                var view = new YOMPUI.EmbedChartsRowInstanceView({
                        annotations:    this.collections.annotations,
                        api:            this.api,
                        instance:       instance,
                        minutesPerBar:  this.minutesPerBar,
                        models:         instances[instance],
                        datas:          this.models.datas[instance],
                        range:          this.range,
                        width:          this.width
                    });

                // Handle events
                this.listenTo(view, 'click',     this.handleClick);
                this.listenTo(view, 'longclick', this.handleLongClick);
                this.listenTo(view, 'scroll',    this.handleScroll);

                // store view
                this.views.rows.push(view);

                // prep initial row data fetch
                Object.keys(this.models.datas[instance]).forEach(
                    function(modelId) {
                        var modelObject =   this.models.datas[instance][modelId],
                            promise = modelObject.fetch({
                                from:   YOMPUI.utils.getUTCTimestamp(this.range.data.start),
                                to:     YOMPUI.utils.getUTCTimestamp(this.range.data.end),
                                error:  this.modelRefetchError
                            });

                        dataHandles.push(modelObject);
                        promises.push(promise);
                    }.bind(this)
                );
            }.bind(this));

            // Fetch annotations
            promises.push(
                this.collections.annotations.fetch({
                    from: YOMPUI.utils.getUTCTimestamp(this.range.data.start),
                    to:   YOMPUI.utils.getUTCTimestamp(this.range.data.end)
                })
            );

            // fetch initial row data
            $.when.apply($, promises).done(function() {
                var $rows =         this.$el.find('ul'),
                    dataRow =       this.getValidDataRowFromHandle(dataHandles),
                    seed =          (dataRow && (dataRow.length > 0));

                // if no data, show an error
                if(! seed) {
                    YOMPUI.utils.throb.stop();
                    this.$el.parent().html(this.msgs.empty);
                    return;
                }

                // render each row
                this.views.rows.forEach(function(row) {
                    var key = Object.keys(row.datas)[0],
                        data = row.datas[key].get('data');

                    // only render each collapsed instance row if it has data
                    if(data.length) {
                        $rows.append(row.$el);
                        row.render();
                    }
                    else {
                        row.remove();
                        // remove row from tracking list
                        this.views.rows = this.views.rows.filter(function(current) {
                            if(current !== row) return true;
                        });
                    }
                }.bind(this));

                // init and draw pink top markers/lines view
                this.views.markers = new YOMPUI.EmbedChartsMarkersView({
                    api:            this.api,
                    minutesPerBar:  this.minutesPerBar,
                    range:          this.range,
                    width:          this.width
                });
                this.assign(this.views.markers, '.markers');
                this.views.markers.render();

                // show init help
                this.showToolTip();

                // auto-reload newer data every 5 minutes
                this.interval = setInterval(
                    this.autoReloadNewData.bind(this),
                    (5 * MINUTES)
                );

                YOMPUI.utils.throb.stop();
            }.bind(this));

            // done
            this.trigger('view-ready');
            return this;
        },


        // Custom methods

        /**
         * Look for and get newer data that has come into existance in the
         *  past 5 minutes. This is probably run automatically every 5 minutes.
         */
        autoReloadNewData: function() {
            var promises = [];

            this.views.rows.forEach(function(row) {
                Object.keys(row.datas).forEach(function(modelId) {
                    var modelObject =   row.datas[modelId],
                        previousData =  modelObject.get('data'),
                        lastPoint =     previousData[previousData.length - 1],
                        fromDate =      null,
                        toDate =        new Date(),
                        promise =       null;

                    if(lastPoint && lastPoint[indexTimestamp]) {
                        fromDate = YOMPUI.utils.getUTCDateFromTimestamp(lastPoint[indexTimestamp]);
                    }
                    else {
                        fromDate = new Date(this.range.data.end);
                        // small overlap to make sure not miss any data points
                        fromDate.setTime(fromDate.getTime() - (5 * MINUTES));
                    }

                    // Fetch new data
                    promise = modelObject.fetch({
                        from:    YOMPUI.utils.getUTCTimestamp(fromDate),
                        to:      YOMPUI.utils.getUTCTimestamp(toDate),
                        error:   this.modelRefetchError,
                        success: function(model, response, options) {
                            this.modelFetchNewerSuccess(
                                row,
                                previousData,
                                model,
                                response,
                                options
                            );
                        }.bind(this)
                    });

                    promises.push(promise);
                }.bind(this));
            }.bind(this));

            // Fetch annotations
            promises.push(this.collections.annotations.fetch({
                        from: YOMPUI.utils.getUTCTimestamp(this.range.data.end)
                    }));

            // when loaded
            $.when.apply($, promises).done(function() {
                var buffer =    (this.minutesPerBar * MINUTES) * 2,
                    trigger =   this.range.data.end.getTime() - buffer;

                // if view-far-right was aligned with data-far-right,
                //  perform scroll to preserve alignment.
                if(this.range.view.end.getTime() >=  trigger) {
                    this.range.view.end = this.range.data.end;
                    this.range.view.start.setTime(
                        this.range.view.end.getTime() -
                        this.getViewRangeWidth(this.minutesPerBar)
                    );
                }

                this.updateCharts();
            }.bind(this));
        },

        /**
         * Take a list of data handles (rows of data), and return a single one
         *  that seems valid (has a start date and an end date)
         * @param {array} dataHandles List of data handle objects (rows of data)
         * @returns {object} Single validated datahandle object
         */
        getValidDataRowFromHandle: function(dataHandles) {
            var filter = function(handle) {
                    var keep = (
                                handle
                            &&  handle.get
                            &&  handle.get('data')
                            &&  (handle.get('data').length > 0)
                        ),
                        data = keep ? handle.get('data') : null,
                        valid = data ? (
                                data[0][indexTimestamp]
                            &&  $.isNumeric(data[0][indexAnomaly])
                            &&  $.isNumeric(data[0][indexValue])
                            &&  data[data.length - 1][indexTimestamp]
                            &&  $.isNumeric(data[data.length - 1][indexAnomaly])
                            &&  $.isNumeric(data[data.length - 1][indexValue])
                        ) : false;

                    return valid;
                },
                dataRows = dataHandles.filter(filter),
                dataRow = (dataRows.length > 0) ? dataRows[0].get('data') : null;

            return dataRow;
        },

        /**
         * Get the range of width of the View, depending on minutesPerBar.
         * @param {number} minutesPerBar Number of minutes per bar on chart.
         * @returns {number} Width of range of the view, in miliseconds.
         */
        getViewRangeWidth: function(minutesPerBar) {
            var multiplier =    (this.width / 12),
                width =         multiplier * (minutesPerBar * MINUTES);

            return width;
        },

        /**
         * Handle a click on a single chart row.
         *  Many complex combos:
         *      [ InstanceView, MetricView ] x [ InstanceClick, MetricClick, DetailClick ] x [ Open, Closed ]
         */
        handleClick: function(rowView) {
            var $rows =     this.$el.find('ul'),
                promises =  [],
                promise =   null;

            if(this.isBusy) return;

            this.views.markers.hideLines();

            if(
                    (this.state === 'instance')
                &&  (rowView.type === 'instance')
            ) {
                this.isBusy = true;

                // currently in the Instance View and clicked on an Instance row
                var instance = rowView.instance;

                // remove other instances in prep for Metric View
                this.views.rows.forEach(function(row) {
                    if(row.instance !== instance) {
                        promise = row.$el.slideUp().promise();
                        promises.push(promise);
                    }
                });

                // after removal animation is done
                $.when.apply($, promises).done(function() {
                    promises = [];

                    // show metrics below instance
                    Object.keys(this.models.datas[instance]).forEach(
                        function(modelId) {
                            var dataModel = this.models.datas[instance][modelId],
                                data =      dataModel.get('data'),
                                view =      null;

                            if(data.length <= 0) return;  // no data, no draw.

                            view = new YOMPUI.EmbedChartsRowMetricView({
                                api:            this.api,
                                modelId:        modelId,
                                instance:       instance,
                                minutesPerBar:  this.minutesPerBar,
                                models:         this.collections.models.where({ uid: modelId }),
                                datas:          this.models.datas[instance],
                                range:          this.range,
                                width:          this.width
                            });

                            // Handle events
                            this.listenTo(view, 'click',     this.handleClick);
                            this.listenTo(view, 'longclick', this.handleLongClick);
                            this.listenTo(view, 'scroll',    this.handleScroll);

                            // store view
                            this.views.rows.push(view);

                            // render
                            view.$el.hide();
                            $rows.append(view.$el);
                            view.render();

                            promise = view.$el.slideDown().promise();
                            promises.push(promise);
                        }.bind(this)
                    );

                    // after addition animation is done
                    $.when.apply($, promises).done(function() {
                        this.views.markers.update();

                        this.state = 'metric';  // switch to Metric View

                        this.isBusy = false;
                    }.bind(this));
                }.bind(this));
            }
            else if(this.state === 'metric') {
                // currently in the Metric View

                if(rowView.type === 'instance') {
                    // clicked on an Instance row
                    var instance =  rowView.instance,
                        newRows =   [],
                        promises =  [],
                        promise =   null;

                    this.isBusy = true;

                    // remove non-instance (metric, detail) rows, show all instance rows
                    this.views.rows.forEach(function(row, index) {
                        if(row.type === 'instance') {
                            newRows.push(row);
                        }
                        else {
                            promise = row.$el.slideUp().promise();
                            $.when(promise).done(function() {
                                row.remove();
                            });
                            promises.push(promise);
                        }
                    });
                    this.views.rows = newRows;

                    // when removal animations are finished
                    $.when.apply($, promises).done(function() {
                        promises = [];

                        this.views.rows.forEach(function(row) {
                            promise = row.$el.slideDown().promise();
                            promises.push(promise);
                        });

                        // when addition animations are finished
                        $.when.apply($, promises).done(function() {
                            this.views.markers.update();

                            // switch to Instance View
                            this.state = 'instance';

                            this.isBusy = false;
                        }.bind(this));
                    }.bind(this));
                }
                else if(rowView.type === 'metric') {
                    // clicked on a Metric row

                    if(rowView.detailExpanded) {
                        // if metric details are already shown, close them
                        this.isBusy = true;

                        // clean details view out of view list
                        this.views.rows = this.views.rows.filter(function(row) {
                            if(row !== rowView.detailExpanded) return true;
                        });

                        // remove and unset detail view
                        rowView.detailExpanded.$el.slideUp(function() {
                            rowView.detailExpanded.remove();
                            rowView.detailExpanded = false;

                            this.views.markers.update();

                            this.isBusy = false;
                        }.bind(this));
                    }
                    else {
                        this.isBusy = true;

                        // no metric details shown, so shown them above metric
                        var instance =  rowView.instance,
                            model =     rowView.models[0],
                            modelId =   model.id,
                            metric =    model.get('metric'),
                            view =      new YOMPUI.EmbedChartsRowMetricDetailView({
                                api:            this.api,
                                modelId:        modelId,
                                instance:       instance,
                                minutesPerBar:  this.minutesPerBar,
                                models:         this.collections.models.where({ uid: modelId }),
                                datas:          this.models.datas[instance],
                                range:          this.range,
                                width:          this.width
                            });

                        // Handle events
                        this.listenTo(view, 'click',     this.handleClick);
                        this.listenTo(view, 'longclick', this.handleLongClick);
                        this.listenTo(view, 'scroll',    this.handleScroll);

                        // store view
                        this.views.rows.push(view);

                        // render - above metric view chart
                        rowView.detailExpanded = view;
                        view.$el.hide();
                        rowView.$el.before(view.$el);
                        view.render();
                        view.$el.slideDown(function() {
                            this.views.markers.update();
                            this.isBusy = false;
                        }.bind(this));
                    }
                }
            }
        },

        /**
         * Event handler method for a Long Click (+1s) on a single row
         */
        handleLongClick: function(rowView) {
            console.log("Long:" +rowView.instance);
        },

        /**
         * Event handle method for a row drag/scroll
         *  (click, hold, move left or right).
         */
        handleScroll: function(payload) {
            var start =         payload.range.start,
                end =           payload.range.end,
                direction =     payload.direction,
                loadPoint =     new Date(this.range.data.start),
                dataHandles =   [],
                promises =      [],
                rowFilter = function(row) {
                    return(row.type === 'instance');
                };

            // update chart range view tracking
            this.range.view.start = new Date(start);
            this.range.view.end = new Date(end);

            // Synchronize charts - not using row.updateCharts() here on purpose
            //  because that also worries about data, not just dateWindow, this
            //  should be faster.
            this.views.rows.forEach(function(row) {
                if(row.chart && row.chart.updateOptions) {
                    row.chart.updateOptions({ dateWindow: [ start, end ] });
                }
            });
            this.views.markers.update();

            // only pass this point if we're scrolling to the left/past
            if(direction !== 'right') return;

            // load more data if needed, when within X hours of current data start
            loadPoint.setTime(loadPoint.getTime() + (this.minutesPerBar * HOURS));

            if(this.range.view.start < loadPoint) {
                // don't make duplicate calls
                if(this.isLoading) return;
                this.isLoading = true;

                // fetch even older data
                var pastDate = new Date(this.range.data.start);
                // load further into the past
                pastDate.setTime(pastDate.getTime() - (2 * this.minutesPerBar * HOURS));

                this.views.rows.filter(rowFilter).forEach(function(row) {
                    Object.keys(row.datas).forEach(function(modelId) {
                        var modelObject = row.datas[modelId],
                            promise = null,
                            previousData = modelObject.get('data');

                        promise = modelObject.fetch({
                            from:       YOMPUI.utils.getUTCTimestamp(pastDate),
                            to:         YOMPUI.utils.getUTCTimestamp(this.range.data.start),
                            error:      this.modelRefetchError,
                            success:    function(model, response, options) {
                                this.modelFetchOlderSuccess(
                                    previousData,
                                    model,
                                    response,
                                    options
                                );
                            }.bind(this)
                        });

                        dataHandles.push(modelObject);
                        promises.push(promise);
                    }.bind(this));
                }.bind(this));

                // Fetch annotations
                promises.push(this.collections.annotations.fetch({
                            from: YOMPUI.utils.getUTCTimestamp(pastDate),
                            to:   YOMPUI.utils.getUTCTimestamp(this.range.data.start)
                        }));

                // when data is fetched
                $.when.apply($, promises).done(function() {
                    this.isLoading = false;
                    this.updateCharts();
                }.bind(this));
            }
        },

        /**
         * Merge model data by lining up dates and concat'ing arrays.
         * @param {array} start List of data points that should come at the
         *  start of the newly returned array.
         * @param {array} end List of data points that will be at the end of
         *  the newly returned array.
         * @returns {array} Merged list [ start, end ] with dates lined up
         */
         mergeModelData: function(start, end) {
            var startIndex =        0,
                endIndex =          0,
                startFinalDate =    null,
                endFirstDate =      null;

            if((! start) ||  (start.length <= 0)) {
                return end;
            }
            if((! end) ||  (end.length <= 0)) {
                return start;
            }

            startIndex = start.length - 1;
            if(startIndex >= 0) {
                startFinalDate = start[startIndex][indexTimestamp];
                endFirstDate = end[endIndex][indexTimestamp];

                while(startFinalDate >= endFirstDate) {
                    // we've got overlapping data, give new data the edge here.
                    start.pop();
                    startIndex--;

                    if((startIndex < 0) || (! start[startIndex])) {
                        break;
                    }

                    startFinalDate = start[startIndex][indexTimestamp];
                }
            }
            return start.concat(end);
         },

        /**
         * Backbone.Model.fetch() ERROR callback handler - for Model
         *  re-fetch()ing (scrolling, or loading a bigger tab needing more data)
         */
        modelRefetchError: function(model, response, options) {
            return YOMPUI.utils.modalError(response);
        },

        /**
         * Backbone.Model.fetch() Success callback handler - for Model
         *  fetch()ing of NEWER data (most recent historically) - for
         *  auto-update that happens every 5 min.
         * @param {object} row Row view object so we can update it
         * @param {array} previousData Data from row from previous step
         * @param {object} model Backbone.Model.fetch() success callback param
         * @param {object} response Backbone.Model.fetch() success callback param
         * @param {object} options Backbone.Model.fetch() success callback param
         */
        modelFetchNewerSuccess: function(
            row, previousData, model, response, options
        ) {
            var newData =   model.get('data'),
                timeEnd =   null,
                end =       null;

            if(newData.length > 0) {
                timeEnd =   model.get('data')[model.get('data').length - 1][indexTimestamp];
                end =       YOMPUI.utils.getUTCDateFromTimestamp(timeEnd);

                // if loaded new older data, set new range for data start
                if(end > this.range.data.end) {
                    this.range.data.end = end;
                }

                // append newly loaded data to old data
                model.set('data', this.mergeModelData(previousData, newData));
            }
            else {
                // keep previous data
                model.set('data', previousData);
            }
        },

        /**
         * Backbone.Model.fetch() Success callback handler - for Model
         *  re-fetch()ing of older data (historical in the past) - for actions
         *  like scrolling, or loading a bigger tab needing more data, etc.
         * @param {array} previousData Data from row from previous step
         * @param {object} model Backbone.Model.fetch() success callback param
         * @param {object} response Backbone.Model.fetch() success callback param
         * @param {object} options Backbone.Model.fetch() success callback param
         */
        modelFetchOlderSuccess: function(previousData, model, response, options) {
            var newData =   model.get('data'),
                timeStart = null,
                start =     null;

            if(newData.length > 0) {
                timeStart = model.get('data')[0][indexTimestamp];
                start =     YOMPUI.utils.getUTCDateFromTimestamp(timeStart);

                // if loaded new older data, set new range for data start
                if(start < this.range.data.start) {
                    this.range.data.start = start;
                }

                // prepend newly loaded data to old data
                model.set('data', this.mergeModelData(newData, previousData));
            }
            else {
                // keep previous data
                model.set('data', previousData);
            }
        },

        /**
         * Show a tooltip on first instance row for startup help
         */
        showToolTip: function() {
            var $toolTip =  null,
                destroyFn = function() { $toolTip.tooltip('destroy'); },
                tipText =   [
                    'Click chart for details.',
                    'Drag chart left or right to move in time.',
                    'Click chart again to return.'
                    // 'Hold a Long Click on chart to Zoom In.'
                ].join(' ');

            if((! this.views.rows) || (this.views.rows.length <= 0)) return;

            $toolTip = this.views.rows[0].$el;
            $toolTip.tooltip({
                placement:  'bottom',
                title:      tipText,
                trigger:    'manual'
            });
            $toolTip.tooltip('show');

            $('body').off('click').on('click', destroyFn);
            // not sure why prev line doesn't cover next line.
            $('ul.nav-tabs > li > a').off('click').on('click', destroyFn);
        },

        /**
         * Update rows sort order
         */
        updateSortOrder : function(models) {
            this.collections.models = models;
            var instances =  Object.keys(this.collections.models.groupByInstance());

            // Filter all instance rows
            var rows = [];
            this.views.rows.forEach(function(row) {
                if (row.type == 'instance') {
                    row.remove();
                    var idx = instances.indexOf(row.instance);
                    rows[idx] = row;
                }
            });

            // Rows are positioned after the Marker
            var curEl = this.views.markers.$el;

            // Reorder instance rows matching models order
            rows.forEach(function(row){
                curEl.after(row.$el);
                curEl = row.$el;
            });
        },

        /**
         * Update charts on all children rows
         */
        updateCharts: function() {
            this.views.rows.forEach(function(row) {
                row.updateChart();
            });
            this.views.markers.update();
        },

        /**
         * Update minutes-per-bar for all rows.
         * @param {number} minutes Minutes per bar.
         */
        updateMinutesPerBar: function(minutes) {
            var minutesHash =   this.site.charts.instance.anomaly.minutesPerBar,
                dataHandles =   [],
                promises =      [],
                rowFilter = function(row) {
                    return(row.type === 'instance');
                },
                viewStart = (
                    this.range.view.end.getTime() -
                    this.getViewRangeWidth(minutes)
                );

            this.minutesPerBar = minutes;
            this.range.view.start.setTime(viewStart);

            // load missing data to fill out the chart for the current tab view
            if(this.range.view.start < this.range.data.start) {
                YOMPUI.utils.throb.start(this.site.state.loading);

                // load further into the past
                var pastDate = new Date(this.range.view.start);
                pastDate.setTime(pastDate.getTime() - (2 * this.minutesPerBar * HOURS));

                this.views.rows.filter(rowFilter).forEach(function(row) {
                    Object.keys(row.datas).forEach(function(modelId) {
                        var modelObject =   row.datas[modelId],
                            promise =       null,
                            previousData =  modelObject.get('data');

                        // prep fetch
                        promise = modelObject.fetch({
                            from:       YOMPUI.utils.getUTCTimestamp(pastDate),
                            to:         YOMPUI.utils.getUTCTimestamp(this.range.data.start),
                            error:      this.modelRefetchError,
                            success:    function(model, response, options) {
                                this.modelFetchOlderSuccess(
                                    previousData,
                                    model,
                                    response,
                                    options
                                );
                            }.bind(this)
                        });

                        dataHandles.push(modelObject);
                        promises.push(promise);
                    }.bind(this));
                }.bind(this));

                // Fetch annotations
                promises.push(this.collections.annotations.fetch({
                            from: YOMPUI.utils.getUTCTimestamp(pastDate),
                            to:   YOMPUI.utils.getUTCTimestamp(this.range.data.start)
                        }));
            }

            // when data is fetched
            $.when.apply($, promises).done(function() {
                // Make sure edges of View and edges of data line up, nudge
                //  back in any boundary issues.
                if(
                    (this.range.view.start < this.range.data.start) ||
                    (this.range.view.end > this.range.data.end)
                ) {
                    this.range.view.end = this.range.data.end;
                    this.range.view.start.setTime(
                        this.range.view.end.getTime() -
                        this.getViewRangeWidth(this.minutesPerBar)
                    );
                }

                YOMPUI.utils.throb.stop();

                // update each row with new minutesPerBar and Ranges, and redraw
                this.views.rows.forEach(function(row) {
                    row.updateMinutesPerBar(minutes);
                });
                if(this.views.markers) {
                    this.views.markers.update({
                        minutesPerBar: minutes
                    });
                }
            }.bind(this));
        }

    });
})();
