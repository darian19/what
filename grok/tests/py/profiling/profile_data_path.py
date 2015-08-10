#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""
Collate profiling information of the data path from YOMP logs and output a csv
file to stdout

NOTE: profiling must be enabled in application.conf and model-swapper.conf
"""


from collections import namedtuple
import csv
from datetime import datetime
from datetime import timedelta
import dateutil
import dateutil.tz
from optparse import OptionParser
import os
import pprint
import sys

from YOMP import logging_support



_EPOCH = datetime.utcfromtimestamp(0).replace(tzinfo=dateutil.tz.tzutc())



# This class describes a trace of YOMP Custom metric batches throgh the system
#
# listenerGroup: _CustomMetricListenerGroup object
# storerRxRecord: _CustomMetricStorerRxRecord
# inputBatch: _StreamedToModelBatch object representing the input YOMP custom
#   metric data batch emitted by YOMP-api (uwsgi) or metric storer service
# modelRunnerBatch: _ModelRunnerBatch object representing the batch as it's
#   processed by Model Runner
# anomalyBatch: _AnomalyBatch object representing the batch as it's processed
#   by Anomaly Service
_YOMPCustomMetricTrace = namedtuple(
  "_YOMPCustomMetricTrace",
  ("listenerGroup storerRxRecord inputBatch modelRunnerBatch anomalyBatch"))



# This class describes a metric data group in YOMP Custom MetricListener Service
# NOTE: rows here should match rows in _StreamedToModelBatch, but collation
# may be different in _StreamedToModelBatch, etc.
#
# rowTimestampRange: a two-tuple of datetime objects representing the UTC
#   timestamps of the first and last rows in the batch
_CustomMetricListenerGroup = namedtuple(
  "_CustomMetricListenerGroup",
  "line metricName rowTimestampRange rxTime txEndTime")



# This class describes a metric data sample received by YOMP Custom MetricStorer
# from MetricListener
#
# rowTimestamp: datetime objects representing the metric data sample's
#   timestamp
# rxTime: UTC datetime object representing the time when the sample was received
#   by MetricStorer
# procLatency: seconds between the sample's rxTime and start of processing of
#   the sample
_CustomMetricStorerRxRecord = namedtuple(
  "_CustomMetricStorerRecord",
  "line metricName rowTimestamp rxTime procLatency")



# This class describes a chain of metric data batches that traces a batch
# from MetricCollector to ModelRunner and from ModelRunner to AnomalyService
#
# originatedBatch: _StreamedToModelBatch object
# modelRunnerBatch: _ModelRunnerBatch object
# anomalyBatch: _AnomalyBatch object
_MetricCollectorTrace = namedtuple(
  "_MetricCollectorTrace",
  "metricID rowIDRange originatedBatch modelRunnerBatch anomalyBatch"
)



# This class represents a metric data batch streamed to the model by its
# originating service, such as Metric Collector, Metric Storer, or Aggregator
# Service.
# NOTE: batch rows should match across _StreamedToModelBatch, _ModelRunnerBatch
# and _AnomalyBatch
#
# rowTimestampRange: a two-tuple of datetime objects representing the timestamps
#   of the first and last rows in the batch
_StreamedToModelBatch = namedtuple(
  "_StreamedToModelBatch",
  "line service metricID batchID rowIDRange rowTimestampRange "
  "fwdStartTime fwdEndTime")



# This class represents a metric data batch in ModelRunner Service
_ModelRunnerBatch = namedtuple(
  "_ModelRunnerBatch",
  ("line metricID batchID batchSize tailRowID tailRowTimestamp rxTime "
   "fwdEndTime fwdDuration loadDuration infDuration"))



# This class represents a metric data batch in Anomaly Service
_AnomalyBatch = namedtuple(
  "_AnomalyBatch",
  ("line metricID datasource metricName rowIDRange tailRowTimestamp rxTime "
   "procDuration endTime"))



# source: custom | cw
_CsvRow = namedtuple(
  "_CsvRow",
  ("ds metric name headRow tailRow headTS tailTS batchID batchSize "
   "headToEndSec headToStreamerFwd listenerSec storerProcLatency "
   "streamerFwdSec mrSec modelLoadSec infSec anomSec "
   "streamerToModel modelToAnomaly anomalyToEnd atListener atStorer atStreamer "
   "atModel atAnomaly atEnd streamedBy")
)


_DEBUG = False

class YOMPDataPathProfiler(object):
  def __init__(self, logDir):
    """
    :param logDir: path to YOMP log directory
    """
    self._logDir = logDir


  def run(self):
    originatedBatches = self._scrubBatchOrigination()
    if _DEBUG:
      print "ORIGINANTED BATCHES:\n", pprint.pformat(originatedBatches)

    modeRunnerBatches = self._scrubModelRunnerInferenceProfiling()
    if _DEBUG:
      print "MODELRUNNER-INFERENCES:\n", pprint.pformat(modeRunnerBatches)

    anomalyBatches = self._scrubAnomalyServiceBatches()
    if _DEBUG:
      print "ANOMALY:\n", pprint.pformat(anomalyBatches)

    # Trace YOMP custom metric data
    customMetricTraces = self._traceYOMPCustomData(
      originatedBatches=originatedBatches,
      modeRunnerBatches=modeRunnerBatches,
      anomalyBatches=anomalyBatches)
    if _DEBUG:
      print "YOMP CUSTOM METRIC TRACES:\n", pprint.pformat(customMetricTraces)

    # Trace Cloudwatch (non-Autostack) metric data
    cloudwatchMetricTraces = self._collateMetricCollectorBatches(
      originatedBatches=originatedBatches,
      modeRunnerBatches=modeRunnerBatches,
      anomalyBatches=anomalyBatches,
      datasource="cloudwatch")
    if _DEBUG:
      print "CLOUDWATCH METRIC TRACES:\n", pprint.pformat(
        cloudwatchMetricTraces)

    # Generate a sequence of _CsvRow objects representing output rows for YOMP
    # Custom Metrics data-path profiling
    customRows = self._generateYOMPCustomMetricOutputRows(customMetricTraces)

    # Generate a sequence of _CsvRow objects representing output rows for
    # CloudWatch Metrics data-path profiling
    cloudwatchRows = self._generateCloudwatchModelOutputRows(
      cloudwatchMetricTraces)

    # Output results in CSV format
    self._emitCSV(outputStream=sys.stdout, rows=customRows + cloudwatchRows)


  def _traceYOMPCustomData(self, originatedBatches, modeRunnerBatches,
                           anomalyBatches):
    """
    :param originatedBatches: sequence of _StreamedToModelBatch objects
      representing the initial injections of batches via Model Swapper Interface
    :param modeRunnerBatches: sequence of _ModelRunnerBatch objects
    :param anomalyBatches: sequence of _AnomalyBatch objects

    :returns: sequence of _YOMPCustomMetricTrace objects
    """
    # Trace model batches
    modelBatchTraces = self._collateMetricCollectorBatches(
      originatedBatches=originatedBatches,
      modeRunnerBatches=modeRunnerBatches,
      anomalyBatches=anomalyBatches,
      datasource="custom")
    if _DEBUG:
      print "YOMP CUSTOM MODEL BATCH TRACES:\n", (
        pprint.pformat(modelBatchTraces))

    # Link metric listener groups and metric storer rx records with model batch
    # traces
    metricListenerGroupMap = dict(
      ((g.metricName, g.rowTimestampRange[0]), g)
      for g in self._scrubMetricListenerGroups())
    if _DEBUG:
      print "LISTENER:\n", pprint.pformat(metricListenerGroupMap)

    metricStorerRxRecordsMap = dict(
      ((r.metricName, r.rowTimestamp), r)
      for r in self._scrubMetricStorerRxRecords())
    if _DEBUG:
      print "STORER RX RECORDS:\n", pprint.pformat(metricStorerRxRecordsMap)

    customMetricDataTraces = []
    for modelBatchTrace in modelBatchTraces:
      inputBatch = modelBatchTrace.originatedBatch
      anomalyBatch = modelBatchTrace.anomalyBatch
      # NOTE: we pick the oldest (head) batch row as reference
      lookupKey = (anomalyBatch.metricName, inputBatch.rowTimestampRange[0])
      mlGroup = metricListenerGroupMap.get(lookupKey)
      if mlGroup is None:
        continue
      msRxRecord = metricStorerRxRecordsMap.get(lookupKey)
      if msRxRecord is None:
        continue

      trace = _YOMPCustomMetricTrace(
        listenerGroup=mlGroup,
        storerRxRecord=msRxRecord,
        inputBatch=inputBatch,
        modelRunnerBatch=modelBatchTrace.modelRunnerBatch,
        anomalyBatch=modelBatchTrace.anomalyBatch)

      customMetricDataTraces.append(trace)


    return customMetricDataTraces


  def _generateYOMPCustomMetricOutputRows(self, customMetricTraces):
    """ Generate a sequence of objects representing output rows for YOMP Custom
    Metrics data-path profiling

    :param customMetricTraces: sequence of _YOMPCustomMetricTrace objects

    :returns: a sequence of _CsvRow objects
    """
    result = []
    for customTrace in customMetricTraces:
      listenerGroup = customTrace.listenerGroup
      storerRxRecord = customTrace.storerRxRecord
      inputBatch = customTrace.inputBatch
      modelRunnerBatch = customTrace.modelRunnerBatch
      anomalyBatch = customTrace.anomalyBatch

      csvRow = _CsvRow(
        ds=anomalyBatch.datasource,
        metric=inputBatch.metricID,
        name=listenerGroup.metricName,
        headRow=inputBatch.rowIDRange[0],
        tailRow=inputBatch.rowIDRange[1],
        headTS=self._epochFromUTCDatetime(listenerGroup.rowTimestampRange[0]),
        tailTS=self._epochFromUTCDatetime(listenerGroup.rowTimestampRange[1]),
        batchID=modelRunnerBatch.batchID,
        batchSize=modelRunnerBatch.batchSize,
        headToEndSec=(anomalyBatch.endTime -
                      listenerGroup.rowTimestampRange[0]).total_seconds(),
        headToStreamerFwd=(inputBatch.fwdStartTime -
                           inputBatch.rowTimestampRange[0]).total_seconds(),
        listenerSec=(listenerGroup.txEndTime -
                     listenerGroup.rxTime).total_seconds(),
        storerProcLatency=storerRxRecord.procLatency,
        streamerFwdSec=(
          inputBatch.fwdEndTime -
          inputBatch.fwdStartTime).total_seconds(),
        mrSec=(modelRunnerBatch.fwdEndTime - modelRunnerBatch.rxTime
               ).total_seconds(),
        modelLoadSec=modelRunnerBatch.loadDuration,
        infSec=modelRunnerBatch.infDuration,
        anomSec=anomalyBatch.procDuration,
        streamerToModel=(modelRunnerBatch.rxTime - inputBatch.fwdStartTime
                         ).total_seconds(),
        modelToAnomaly=(
          anomalyBatch.rxTime - modelRunnerBatch.rxTime).total_seconds(),
        anomalyToEnd=(
          anomalyBatch.endTime - anomalyBatch.rxTime).total_seconds(),
        atListener=self._epochFromUTCDatetime(listenerGroup.rxTime),
        atStorer=self._epochFromUTCDatetime(storerRxRecord.rxTime),
        atStreamer=self._epochFromUTCDatetime(inputBatch.fwdStartTime),
        atModel=self._epochFromUTCDatetime(modelRunnerBatch.rxTime),
        atAnomaly=self._epochFromUTCDatetime(anomalyBatch.rxTime),
        atEnd=self._epochFromUTCDatetime(anomalyBatch.endTime),
        streamedBy=inputBatch.service
      )

      result.append(csvRow)


    return result


  def _generateCloudwatchModelOutputRows(self, cloudwatchBatchTraces):
    """ Generate a sequence of objects representing output rows for standalone
    model batch rows

    :param cloudwatchBatchTraces: sequence of _MetricCollectorTrace objects
      representing model batch traces originating from Metric Collector Service

    :returns: a sequence of _CsvRow objects
    """
    result = []
    for chain in cloudwatchBatchTraces:
      inputBatch = chain.originatedBatch
      modelRunnerBatch = chain.modelRunnerBatch
      anomalyBatch = chain.anomalyBatch

      csvRow = _CsvRow(
        ds=anomalyBatch.datasource,
        metric=chain.metricID,
        name=anomalyBatch.metricName,
        headRow=chain.rowIDRange[0],
        tailRow=chain.rowIDRange[1],
        headTS=self._epochFromUTCDatetime(inputBatch.rowTimestampRange[0]),
        tailTS=self._epochFromUTCDatetime(inputBatch.rowTimestampRange[1]),
        batchID=modelRunnerBatch.batchID,
        batchSize=modelRunnerBatch.batchSize,
        headToEndSec=(anomalyBatch.endTime -
                      inputBatch.rowTimestampRange[0]).total_seconds(),
        headToStreamerFwd=(inputBatch.fwdStartTime -
                           inputBatch.rowTimestampRange[0]).total_seconds(),
        listenerSec=None,
        storerProcLatency=None,
        streamerFwdSec=(
          inputBatch.fwdEndTime -
          inputBatch.fwdStartTime).total_seconds(),
        mrSec=(modelRunnerBatch.fwdEndTime -
               modelRunnerBatch.rxTime).total_seconds(),
        modelLoadSec=modelRunnerBatch.loadDuration,
        infSec=modelRunnerBatch.infDuration,
        anomSec=anomalyBatch.procDuration,
        streamerToModel=(modelRunnerBatch.rxTime -
                         inputBatch.fwdStartTime).total_seconds(),
        modelToAnomaly=(anomalyBatch.rxTime -
                        modelRunnerBatch.rxTime).total_seconds(),
        anomalyToEnd=(anomalyBatch.endTime -
                      anomalyBatch.rxTime).total_seconds(),
        atListener=None,
        atStorer=None,
        atStreamer=self._epochFromUTCDatetime(inputBatch.fwdStartTime),
        atModel=self._epochFromUTCDatetime(modelRunnerBatch.rxTime),
        atAnomaly=self._epochFromUTCDatetime(anomalyBatch.rxTime),
        atEnd=self._epochFromUTCDatetime(anomalyBatch.endTime),
        streamedBy=inputBatch.service
      )


      result.append(csvRow)


    return result


  @classmethod
  def _emitCSV(cls, outputStream, rows):
    """ Emit profiling information in CSV format

    :param outputStream: an open file object for CSV output

    :param rows: sequence of _CsvRow objects
    """
    writer = csv.writer(outputStream)

    # Emit header row
    writer.writerow(_CsvRow._fields)  # pylint: disable=W0212,E1101

    # Emit data rows
    writer.writerows(rows)

    # Flush output stream
    outputStream.flush()


  @classmethod
  def _collateMetricCollectorBatches(cls, originatedBatches, modeRunnerBatches,
                                     anomalyBatches, datasource):
    """ Collate sequences of _StreamedToModelBatch, _ModelRunnerBatch and
    _AnomalyBatch objects

    :param originatedBatches: sequence of _StreamedToModelBatch objects
      representing the initial injections of batches via Model Swapper Interface

    :param modeRunnerBatches: sequence of _ModelRunnerBatch objects
    :param anomalyBatches: sequence of _AnomalyBatch objects

    :param datasource: the metric's datasource (e.g., custom, cloudwatch)
    :returns: sequence of _MetricCollectorTrace objects
    """
    originatedBatchMap = dict(
      ((b.metricID, b.rowIDRange[1]), b)
      for b in originatedBatches
    )

    modelRunnerBatchMap = dict(
      ((b.metricID, b.tailRowID), b)
      for b in modeRunnerBatches
    )

    chains = []
    for anomalyBatch in anomalyBatches:
      if anomalyBatch.datasource != datasource:
        continue

      lookupKey = (anomalyBatch.metricID, anomalyBatch.rowIDRange[1])

      oBatch = originatedBatchMap.get(lookupKey)
      if oBatch is None:
        if _DEBUG:
          print >> sys.stderr, "lookupKey", lookupKey, (
            "not found in originatedBatchMap")
        continue

      modelRunnerBatch = modelRunnerBatchMap.get(lookupKey)
      if modelRunnerBatch is None:
        if _DEBUG:
          print >> sys.stderr, "lookupKey", lookupKey, (
            "not found in modelRunnerBatchMap")
        continue

      chain = _MetricCollectorTrace(
        metricID=oBatch.metricID,
        rowIDRange=oBatch.rowIDRange,
        originatedBatch=oBatch,
        modelRunnerBatch=modelRunnerBatch,
        anomalyBatch=anomalyBatch)

      chains.append(chain)

    return chains


  def _scrubMetricListenerGroups(self):
    """ Scrub metric_listener log for profiling info

    :returns: Generator that yields _CustomMetricListenerGroup objects in the
      order of the corresponding log records
    """

    # Example:
    # "2014-05-12 11:33:40,623 - __main__(2929) - INFO - {TAG:CUSLSR.FW.DONE} "
    # "metricName=mycustommetric; timestamp=2013-12-05T00:00:00Z; "
    # "duration=0.0229s"

    forwardSampleDoneTag = "{TAG:CUSLSR.FW.DONE}"
    logFilePath = os.path.join(self._logDir, "metric_listener.log")
    with open(logFilePath) as f:
      for line in f:
        try:
          tagIndex = line.index(forwardSampleDoneTag)
        except ValueError:
          continue

        # Skip past tag
        values = line[tagIndex + len(forwardSampleDoneTag):]

        rowTimestamp = self._parseTokenISOTimestamp(values, "timestamp")
        txEndTime = self._parseLoggingTimestamp(line)

        yield _CustomMetricListenerGroup(
          line=line,
          metricName=self._parseTokenText(values, "metricName"),
          rowTimestampRange=(rowTimestamp, rowTimestamp),
          txEndTime=txEndTime,
          rxTime=txEndTime - timedelta(
            seconds=self._parseTokenSeconds(values, "duration")))


  def _scrubMetricStorerRxRecords(self):
    """ Scrub metric_storer log for data rx records

    :returns: generator that yields _CustomMetricStorerRxRecord objects in the
      order of the corresponding log records
    """
    # Example:
    # "2014-05-12 11:33:40,623 - __main__(2929) - INFO - {TAG:CUSSTR.DATA.RX} "
    # "metricName=mycustommetric; timestamp=2013-12-05T00:00:00Z; "
    # "rxTime=1411974614.6239"

    rxSampleTag = "{TAG:CUSSTR.DATA.RX}"
    logFilePath = os.path.join(self._logDir, "metric_storer.log")
    with open(logFilePath) as f:
      for line in f:
        try:
          tagIndex = line.index(rxSampleTag)
        except ValueError:
          continue

        # Skip past tag
        values = line[tagIndex + len(rxSampleTag):]

        rxTime = self._utcDatetimeFromEpoch(
          self._parseTokenFloat(values, "rxTime"))

        yield _CustomMetricStorerRxRecord(
          line=line,
          metricName=self._parseTokenText(values, "metricName"),
          rowTimestamp=self._parseTokenISOTimestamp(values, "timestamp"),
          rxTime=rxTime,
          procLatency=(
            self._parseLoggingTimestamp(line) - rxTime).total_seconds())


  def _scrubBatchOrigination(self):
    """ Scrub streaming of model swapper model input batches by all
    originating services

    :returns: unordered sequence of _StreamedToModelBatch objects
    """
    # Example:
    # "2014-05-12 18:06:31,950 - MetricStreamer(25131) - INFO - "
    # "<VER=1.4.0, SERVICE=METRIC> {TAG:STRM.DATA.TO_MODEL.DONE} "
    # "Submitted batch=d2138a5eda3a11e39d3e28cfe912e811 to "
    # "model=13751549a4054698b50340394b86cd1e; "numRows=1440; rows=[1..1440]; "
    # "ts=[2013-12-05T00:00:00Z..2013-12-05T00:00:00Z]; duration=0.0799s"
    #
    # rows (identifiers): [4] or [4..7]
    # ts: [2013-12-05T00:00:00Z] or [2013-12-05T00:00:00Z..2013-12-05T00:15:00Z]

    def scrub():
      samplesToModelDoneTag = "{TAG:STRM.DATA.TO_MODEL.DONE}"
      logFileNames = [
        "uwsgi.log", # when a custom metric with data is promoted to model
        "metric_storer.log", # YOMP Custom metrics
        "metrics_collector.log" # Cloudwatch (non-Autostack) metrics
      ]

      for logName in logFileNames:
        logFilePath = os.path.join(self._logDir, logName)
        service = os.path.splitext(logName)[0]
        with open(logFilePath) as f:
          for line in f:
            try:
              tagIndex = line.index(samplesToModelDoneTag)
            except ValueError:
              continue

            # Skip past tag
            values = line[tagIndex + len(samplesToModelDoneTag):]

            fwdEndTime = self._parseLoggingTimestamp(line)
            yield _StreamedToModelBatch(
              line=line,
              service=service,
              batchID=self._parseTokenText(values, "batch"),
              metricID=self._parseTokenText(values, "model"),
              rowIDRange=self._parseTokenIntegerRange(values, "rows"),
              rowTimestampRange=self._parseTokenISOTimestampRange(values, "ts"),
              fwdEndTime=fwdEndTime,
              fwdStartTime=fwdEndTime - timedelta(
                seconds=self._parseTokenSeconds(values, "duration")))


    return tuple(scrub())


  def _scrubModelRunnerInferenceProfiling(self):
    """ Scrub model runner log for inference-processing profiling info

    :returns: sequence of _ModelRunnerBatch objects
    """
    result = []

    # Example:
    # 2014-05-14 22:43:39,479 - YOMP.model_runner(17177) - INFO - <VER=1.4.0,
    # SERVICE=MRUN> {TAG:SWAP.MR.BATCH.DONE}
    # model=13751549a4054698b50340394b86cd1e;
    # batch=2ffb33dedbb911e3bcfd28cfe912e811; numItems= 1; tailRowID=19805;
    # tailRowTS=2014-05-14T22:41:18Z; duration=1.9560s; loadDuration=1.8662s;
    # procDuration=0.0077s; submitDuration=0.0645s; totalBatches=1; totalItems=1
    #
    # NOTE: log entries with tailRowID and tailRowTS of None are from command
    # batches

    samplesToModelDoneTag = "{TAG:SWAP.MR.BATCH.DONE}"
    logFilePath = os.path.join(self._logDir, "model_scheduler.log")
    with open(logFilePath) as f:
      for line in f:
        try:
          tagIndex = line.index(samplesToModelDoneTag)
        except ValueError:
          continue

        # Skip lines related to command batches
        if " tailRowID=None" in line:
          continue

        # Skip past tag
        values = line[tagIndex + len(samplesToModelDoneTag):]

        fwdEndTime = self._parseLoggingTimestamp(line)

        info = _ModelRunnerBatch(
          line=line,
          metricID=self._parseTokenText(values, "model"),
          batchID=self._parseTokenText(values, "batch"),
          batchSize=self._parseTokenInteger(values, "numItems"),
          tailRowID=self._parseTokenInteger(values, "tailRowID"),
          tailRowTimestamp=self._parseTokenISOTimestamp(values, "tailRowTS"),
          fwdEndTime=fwdEndTime,
          fwdDuration=self._parseTokenSeconds(values, "submitDuration"),
          loadDuration=self._parseTokenSeconds(values, "loadDuration"),
          infDuration=self._parseTokenSeconds(values, "procDuration"),
          rxTime=fwdEndTime - timedelta(
            seconds=self._parseTokenSeconds(values, "duration")))

        result.append(info)


    return result


  def _scrubAnomalyServiceBatches(self):
    """ Scrub anomaly service log for profiling info from processing of
    inference results

    :returns: sequence of _AnomalyBatch objects
    """
    result = []

    # Example:
    # "2014-05-13 13:10:49,689 - YOMP.anomaly(48431) - INFO - "
    # "{TAG:ANOM.BATCH.INF.DONE} model=13751549a4054698b50340394b86cd1e; "
    # "numItems=1300; rows=[14602..15901]; tailRowTS=2014-05-18T08:25:11Z; "
    # "duration=2.2201s"

    anomalyBatchDoneTag = "{TAG:ANOM.BATCH.INF.DONE}"
    logFilePath = os.path.join(self._logDir, "anomaly_service.log")
    with open(logFilePath) as f:
      for line in f:
        try:
          tagIndex = line.index(anomalyBatchDoneTag)
        except ValueError:
          continue

        info = dict()
        info["line"] = line

        # Skip past tag
        values = line[tagIndex + len(anomalyBatchDoneTag):]

        endTime = self._parseLoggingTimestamp(line)
        procDuration = self._parseTokenSeconds(values, "duration")

        info = _AnomalyBatch(
          line=line,
          metricID=self._parseTokenText(values, "model"),
          datasource=self._parseTokenText(values, "ds"),
          metricName=self._parseTokenText(values, "name"),
          rowIDRange=self._parseTokenIntegerRange(values, "rows"),
          tailRowTimestamp=self._parseTokenISOTimestamp(values, "tailRowTS"),
          endTime=endTime,
          procDuration=procDuration,
          rxTime=endTime - timedelta(seconds=procDuration))


        result.append(info)


    return result


  @classmethod
  def _epochFromUTCDatetime(cls, dt):
    """ Convert UTC datetime to unix time """
    return (dt - _EPOCH).total_seconds()


  @classmethod
  def _utcDatetimeFromEpoch(cls, secondsSinceEpoch):
    """ Convert seconds since the Epoch to UTC datetime """
    return _EPOCH + timedelta(seconds=secondsSinceEpoch)


  @classmethod
  def _parseLoggingTimestamp(cls, line):
    """ Parse the timestamp from the begging of the log line

    :param line: example
      "2014-05-09 18:33:50,605 - __main__(6169) - INFO - Starting with "
      "host=0.0.0.0"

    :returns: datetime.datetime representation of the log-lines timestamp
    """
    delimIndex = line.index(" - ")

    timestamp = line[:delimIndex]

    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S,%f")
    assert dt.tzinfo is None, repr(dt.tzinfo)
    return dt.replace(tzinfo=dateutil.tz.tzutc())


  @classmethod
  def _parseTokenText(cls, string, tokenName):
    """ Return the value of a token in string.

    :param string: example
      " metricName=customCPUUtilization; timestamp=2014-05-09T18:33:50.605Z"

    :param tokenName: example "metricName"

    :returns: example, given tokenName = "metricName", would return
      "customCPUUtilization"
    """
    tokenName = " " + tokenName + "="
    valueIndex = string.index(tokenName) + len(tokenName)

    try:
      endIndex = string[valueIndex:].index("; ")
    except ValueError:
      value = string[valueIndex:]
    else:
      value = string[valueIndex:valueIndex + endIndex]

    return value.strip()


  @classmethod
  def _parseISOTimestamp(cls, timestampStr):
    """
    :param timestampStr: ISO-formatted timestamp string; e.g.,
      "2014-09-29T09:24:58Z", "2014-09-29T09:24:58.771Z"

    :returns: datetime.datetime object with UTC tzinfo
    """
    if "." in timestampStr:
      dt = datetime.strptime(timestampStr, "%Y-%m-%dT%H:%M:%S.%fZ")
    else:
      dt = datetime.strptime(timestampStr, "%Y-%m-%dT%H:%M:%SZ")

    assert dt.tzinfo is None, repr(dt.tzinfo)
    return dt.replace(tzinfo=dateutil.tz.tzutc())


  @classmethod
  def _parseTokenISOTimestamp(cls, string, tokenName):
    """ Return the datetime representation of the token that was encoded via
    datetime.isoformat

    :param string:
      example:
      " metricName=customCPUUtilization; timestamp=2014-05-09T18:33:50.605Z"

    :param tokenName: example "timestamp"

    :returns: datetime.datetime object with UTC tzinfo
    """
    return cls._parseISOTimestamp(cls._parseTokenText(string, tokenName))


  @classmethod
  def _parseTokenISOTimestampRange(cls, string, tokenName):
    """ Parse a range of two datetime.isoformat-encoded values

    :param string: string containing an isoformat range token; e.g.,
      ts=[2013-12-05T00:00:00Z] or
      ts=[2013-12-05T00:00:00Z..2013-12-05T00:15:00Z]

    :param tokenName: example "ts"

    :returns: a two-tuple (first-datetime, last-datetime) each with UTC tzinfo
    """
    text = cls._parseTokenText(string, tokenName)

    assert text[0] == "[", repr(text)
    assert text[-1] == "]", repr(text)

    text = text[1:-1]

    try:
      delimiterIndex = text.index("..")
    except ValueError:
      value = cls._parseISOTimestamp(text)
      value = (value, value)
    else:
      value = (cls._parseISOTimestamp(text[:delimiterIndex]),
               cls._parseISOTimestamp(text[delimiterIndex + 2:]))

    return value


  @classmethod
  def _parseTokenSeconds(cls, string, tokenName):
    """ Return the floating point value of the token representing duration in
    seconds

    :param string: example
      " duration=1.023s; timestamp=2014-05-09T18:33:50.605Z"

    :param tokenName: example "duration"

    :returns: floating point value
    """
    text = cls._parseTokenText(string, tokenName)

    assert text[-1] == "s", repr(text)

    return float(text[:-1])


  @classmethod
  def _parseTokenFloat(cls, string, tokenName):
    """ Parse a float

    :param string: string containing a float token; e.g., rxTime=1411974614.62

    :param tokenName: example "rxTime"

    :returns: a float value
    """
    return float(cls._parseTokenText(string, tokenName))


  @classmethod
  def _parseTokenInteger(cls, string, tokenName):
    """ Parse an integer

    :param string: string containing an integer token; e.g., tailRowID=4

    :param tokenName: example "tailRowID"

    :returns: an integer value
    """
    return int(cls._parseTokenText(string, tokenName))


  @classmethod
  def _parseTokenIntegerRange(cls, string, tokenName):
    """ Parse an integer range

    :param string: string containing an integer range token; e.g.,
      rows=[4] or rows=[4..7]

    :param tokenName: example "rows"

    :returns: a two-tuple (first-int, last-int); e.g., (4, 4) or (4, 7)
    """
    text = cls._parseTokenText(string, tokenName)

    assert text[0] == "[", repr(text)
    assert text[-1] == "]", repr(text)

    text = text.strip("[]")

    try:
      delimiterIndex = text.index("..")
    except ValueError:
      value = int(text)
      value = (value, value)
    else:
      value = (int(text[:delimiterIndex]), int(text[delimiterIndex + 2:]))

    return value



def _parseArgs():
  helpString = (
    "This script scrubs data-path profiling info from YOMP service logs on "
    "the local host and emits a CSV file to STDOUT.\n"
    "%prog"
  )

  parser = OptionParser(helpString)

  parser.add_option(
    "--logdir",
    action="store",
    type="str",
    default=logging_support.LoggingSupport.getLoggingRootDir(),
    dest="logDir",
    help=("Logging root directory path override. [default: %default]\n"))

  (options, posArgs) = parser.parse_args()

  if len(posArgs) != 0:
    parser.error("Expected no positional args, but got %s: %s" % (
                 len(posArgs), posArgs,))

  if not os.path.isdir(options.logDir):
    parser.error("Log directory doesn't exist or is not a directory: %r"
                 % (options.logDir,))

  return {
    "logDir": options.logDir
  }



if __name__ == "__main__":

  YOMPDataPathProfiler(**_parseArgs()).run()  # pylint: disable=W0142
