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

from collections import defaultdict
from collections import namedtuple
import copy
import datetime
from functools import partial
import itertools
import json
from multiprocessing import Pool
from optparse import OptionParser
import os
import Queue
import time
import urllib
import urllib2

# Needed only temporarily to facilitate migration from file-based approach
# to collectorsdb
import csv
from StringIO import StringIO

import pytz
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from nta.utils.extended_logger import ExtendedLogger
from nta.utils.date_time_utils import epochFromLocalizedDatetime

from taurus.metric_collectors import ApplicationConfig
from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors import logging_support
from taurus.metric_collectors.metric_utils import (getMetricsConfiguration,
                                                   metricDataBatchWrite)
from taurus.metric_collectors.collectorsdb.schema import (xigniteSecurity,
                                                          xigniteSecurityBars,
                                                          emittedStockPrice,
                                                          emittedStockVolume)
from taurus.metric_collectors.xignite import xignite_agent_utils



DATE_FMT = "%m/%d/%Y %I:%M:%S %p"
DEFAULT_BARLENGTH = 5
DEFAULT_SERVER = os.environ.get("TAURUS_HTM_SERVER", "127.0.0.1")
DEFAULT_PORT = 2003
DEFAULT_DAYS = 20
DEFAULT_DRYRUN = False

NAIVE_MARKET_OPEN_TIME = datetime.time(9, 30)    # 9:30 AM
NAIVE_MARKET_CLOSE_TIME = datetime.time(16, 00)  # 4 PM
RETAIN_DAYS = 30 # Retain records for 30 days

# XIgnite API credentials
DEFAULT_API_TOKEN = os.environ.get("XIGNITE_API_TOKEN")

HISTORY_PATH = ".history/xignite"

# Columns in symbol history csv files; must match up with keys returned by
# fetchData()
_COLS = ("StartDate",
         "StartTime",
         "EndDate",
         "EndTime",
         "UTCOffset",
         "Open",
         "High",
         "Low",
         "Close",
         "Volume",
         "Trades")

# Initialize logging
_LOG = ExtendedLogger.getExtendedLogger(__name__)

# xignite bar data API URL
_API_URL = "http://globalquotes.xignite.com/v3/xGlobalQuotes.json/GetBars?"
_URL_KEYS = {"IdentifierType": "Symbol",
             "Identifier": None,
             "StartTime": None,
             "EndTime": None,
             "Precision": "Minutes",
             "Period": None,
             "_Token": None}



_UTC_TZ = pytz.timezone("UTC")
_EASTERN_TZ = pytz.timezone("US/Eastern") # XIgnite API assumes US/Eastern
_EASTERN_LOCALIZED_EPOCH = (_UTC_TZ
                            .localize(datetime.datetime.utcfromtimestamp(0))
                            .astimezone(_EASTERN_TZ))

StockMetricSpec = namedtuple(
  "StockMetricSpec",
  "metricName symbol stockExchange sampleKey"
)

# See OP_MODE_ACTIVE, etc. in ApplicationConfig
g_opMode = ApplicationConfig().get("xignite_stock_agent", "opmode")



def getEasternLocalizedTimestampFromSample(date, time, offset):
  """ Get a timestamp localized to US/Eastern from XIgnite GetBars sample

  :param date: Date from XIgnite sample (e.g., "12/30/2014")
  :type date: str
  :param time: Time from XIgnite sample (e.g., "4:00:00 PM")
  :type time: str
  :param offset: Offset from UTC in XIgnite sample (e.g., -5.0)
  :type offset: str
  :returns: Timestamp in the requested timezone
  :rtype: localized datetime object
  """
  naiveTimestamp = datetime.datetime.strptime("%s %s" % (date, time), DATE_FMT)

  # Convert naive timestamp to utc by subtracting UTCOffset
  utcTimestamp = naiveTimestamp - datetime.timedelta(hours=float(offset))
  localizedUTCTimestamp = _UTC_TZ.localize(utcTimestamp)

  # Return localized timestamp in desired timezone
  return localizedUTCTimestamp.astimezone(_EASTERN_TZ)



def getEasternLocalizedEndTimestampFromSampleRow(sample):
  """ Get a timestamp localized to US/Eastern from non-localized
  EndDate/EndTime in database RowProxy

  :param sqlalchemy.engine.RowProxy sample: Sample from database
  :returns: Timestamp
  :rtype: localized datetime object
  """
  return _EASTERN_TZ.localize(datetime.datetime.combine(sample.EndDate,
                                                        sample.EndTime))



def loadMetricSpecs():
  """ Load metric specs for the xignite stock provider

  :returns: a sequence of StockMetricSpec objects

  Excerpt from metrics.json:
  {
    "Accenture": {
      "stockExchange": "NYSE",
      "symbol": "ACN",
      "metrics": {
        "XIGNITE.ACN.CLOSINGPRICE": {
          "metricTypeName": "Stock Price",
          "provider": "xignite",
          "sampleKey": "Close"
        },
        "XIGNITE.ACN.VOLUME": {
          "metricTypeName": "Stock Volume",
          "provider": "xignite",
          "sampleKey": "Volume"
        },
        . . .
      }
    },
    . . .
  }
  """
  return tuple(
    StockMetricSpec(
      metricName=metricName,
      symbol=resVal["symbol"].upper(),
      stockExchange=resVal["stockExchange"],
      sampleKey=metricVal["sampleKey"])
    for resVal in getMetricsConfiguration().itervalues()
    for metricName, metricVal in resVal["metrics"].iteritems()
    if metricVal["provider"] == "xignite" and "sampleKey" in metricVal)



def getData(symbol, apitoken, barlength, startTime, endTime, fields):
  """ Request data from XigniteGlobalQuotes GetBars API

  See https://www.xignite.com/product/global-stock-quote-data/api/GetBars/ for
  details.

  :param symbol: Stock symbol
  :param apitoken: XIgnite API Token
  :param barlength: Aggregation time period (in minutes)
  :param startTime: Period start time
  :type startTime: str (%m/%d/%Y %I:%M:%S %p)
  :param endTime: Period end time
  :type endTime: str (%m/%d/%Y %I:%M:%S %p)
  :param fields: XIgnite API field names

  :returns: XIgnite GetBars API Response
  :rtype: dict

  Sample JSON response:

    {
      "Outcome": "Success",
      "Message": null,
      "Identity": "Request",
      "Delay": 0.3652289,
      "Bars": [
          {
              "StartDate": "1/15/2015",
              "StartTime": "9:30:00 AM",
              "EndDate": "1/15/2015",
              "EndTime": "9:35:00 AM",
              "UTCOffset": -5,
              "Open": 46.225,
              "High": 46.38,
              "Low": 45.955,
              "Close": 45.96,
              "Volume": 504494,
              "Trades": 2414,
              "TWAP": 46.1765,
              "VWAP": 46.1756
          },
          {
              "StartDate": "1/15/2015",
              "StartTime": "9:35:00 AM",
              "EndDate": "1/15/2015",
              "EndTime": "9:40:00 AM",
              "UTCOffset": -5,
              "Open": 45.97,
              "High": 46.025,
              "Low": 45.64,
              "Close": 45.79,
              "Volume": 492621,
              "Trades": 2621,
              "TWAP": 45.8574,
              "VWAP": 45.8569
          },
          ...
      ],
      "Security": {
          "CIK": "0000789019",
          "CUSIP": null,
          "Symbol": "MSFT",
          "ISIN": null,
          "Valoren": "951692",
          "Name": "Microsoft Corp",
          "Market": "NASDAQ",
          "MarketIdentificationCode": "XNAS",
          "MostLiquidExchange": true,
          "CategoryOrIndustry": "InformationTechnologyServices"
      }
    }
  """

  query = copy.deepcopy(_URL_KEYS)
  query.update({"Identifier": symbol,
                "StartTime": startTime,
                "EndTime": endTime,
                "Period": barlength,
                "_Token": apitoken,
                "_fields": ",".join(fields)})

  queryString = urllib.urlencode(query)

  response = urllib2.urlopen(_API_URL + queryString)

  return json.loads(response.read())



# TODO: TAUR-779 Remove getSymbolFilename() once we've successfully migrated
# away from file-based approach.
def getSymbolFilename(symbol):
  return os.path.join(HISTORY_PATH, "%s.txt" % symbol)



def _getLatestSample(engine, symbol):
  """ Get Latest sample from xignite_security_bars table for a given stock
  symbol

  :param engine: SQLAlchemy engine object
  :param str symbol: Stock symbol
  :returns: Latest sample for given stock symbol
  :rtype: sqlalchemy.engine.RowProxy
  """

  sel = (xigniteSecurityBars
         .select(xigniteSecurityBars.c.symbol==symbol)
         .order_by(xigniteSecurityBars.c.EndDate.desc())
         .order_by(xigniteSecurityBars.c.EndTime.desc())
         .limit(1))


  @collectorsdb.retryOnTransientErrors
  def queryWithRetries():
    return engine.execute(sel).first()


  return queryWithRetries()


def poll(metricSpecs, apitoken, barlength, days):
  """ Poll XIgnite data for given metricspecs associated with the same symbol,
  returning only new data relative to previously fetched data

  :param metricSpecs: Sequence of one or more StockMetricSpec objects
    associated with the same stock symbol for which to conduct polling
  :param apitoken: XIgnite API Token
  :param barlength: Aggregation time period (in minutes)
  :param days: Number of days to request
  :type days: int
  :returns: security details (dict), and new data as a sequence of dicts
  :rtype: 2-tuple
  """
  try:
    symbol = metricSpecs[0].symbol

    now = datetime.datetime.now(_UTC_TZ) # Now, in UTC time
    now -= datetime.timedelta(minutes=(barlength + now.minute % barlength),
                              seconds=now.second) # Align and pad end time to
                                         # prevent too recent of a bucket from
                                         # being returned

    engine = collectorsdb.engineFactory()
    lastSample = _getLatestSample(engine, symbol)

    if lastSample:
      localizedLastEndTime = (
        getEasternLocalizedEndTimestampFromSampleRow(lastSample))

    else:
      # Need to bootstrap from existing file-based .history/ approach
      symbolFilename = getSymbolFilename(symbol)
      if os.path.isfile(symbolFilename):
        # TODO: TAUR-779 Remove this case once we've successfully migrated
        # away from file-based approach.
        with open(symbolFilename, "r+") as symbolFile:
          try:
            # Seek to end of file for latest sample
            lastline = StringIO(symbolFile.readlines()[-1])
            csvin = csv.reader(lastline)
            lastSample = dict(zip(_COLS, next(csvin)))
            localizedLastEndTime = (
              getEasternLocalizedTimestampFromSample(lastSample["EndDate"],
                                                     lastSample["EndTime"],
                                                     lastSample["UTCOffset"]))

          except IndexError:
            # File is empty
            lastSample = {}
            localizedLastEndTime = (
              ((now - datetime.timedelta(days=days)).astimezone(_EASTERN_TZ)))
      else:
        localizedLastEndTime = (
          ((now - datetime.timedelta(days=days)).astimezone(_EASTERN_TZ)))


    # Set start time to match last end, and end to be now
    # Use Eastern because that's what XIgnite assumes in the API
    localizedStartTime = localizedLastEndTime
    localizedEndTime = now.astimezone(_EASTERN_TZ)

    # Fetch XIgnite data

    fields = ["Outcome",
              "Message",
              "Identity",
              "Delay",
              "Security",
              "Security.CIK",
              "Security.CUSIP",
              "Security.Symbol",
              "Security.ISIN",
              "Security.Valoren",
              "Security.Name",
              "Security.Market",
              "Security.MarketIdentificationCode",
              "Security.MostLiquidExchange",
              "Security.CategoryOrIndustry",
              "Bars",
              "Bars.StartDate",
              "Bars.StartTime",
              "Bars.EndDate",
              "Bars.EndTime",
              "Bars.UTCOffset",
              "Bars.Open",
              "Bars.High",
              "Bars.Low",
              "Bars.Trades"]

    for spec in metricSpecs:
      fields.append("Bars.%s" % (spec.sampleKey,))

    try:
      data = getData(symbol=symbol,
                     apitoken=apitoken,
                     barlength=barlength,
                     startTime=localizedStartTime.strftime(DATE_FMT),
                     endTime=localizedEndTime.strftime(DATE_FMT),
                     fields=fields)
    except Exception as e:
      _LOG.exception("Unexpected error while retrieving data from XIgnite.")
      return {"Symbol": symbol}, []

    if (data and "Bars" in data and "Outcome" in data and
        data["Outcome"] == "Success"):
      # Return only the new data


      def sampleStartIsGreaterThanOrEqualToLastEndTime(sample):
        # Compare w/ consistent timezones.
        return (
          getEasternLocalizedTimestampFromSample(sample["StartDate"],
                                                 sample["StartTime"],
                                                 sample["UTCOffset"])
          >= localizedLastEndTime)


      return (data["Security"],
              [sample for sample in data["Bars"]
               if (not lastSample or
                   sampleStartIsGreaterThanOrEqualToLastEndTime(sample))])

    else:
      return {"Symbol": symbol}, []
  except Exception:
    _LOG.exception("poll failed for metricSpecs=%s", metricSpecs)
    raise


def forward(metricSpecs, data, security, server=DEFAULT_SERVER,
            port=DEFAULT_PORT,
            dryrun=DEFAULT_DRYRUN):
  """ Forward stock data to YOMP/Taurus instance via custom metric

  :param metricSpecs: Sequence of one or more StockMetricSpec objects associated
    with the same stock symbol for which polling was conducted
  :param list data: List of sample dicts
  :param dict security: Details of security from XIgnite API
  """
  try:
    symbol = security["Symbol"]

    engine = collectorsdb.engineFactory()

    lastSample = _getLatestSample(engine, symbol)
    if lastSample:
      localizedLastEndTime = (
        getEasternLocalizedEndTimestampFromSampleRow(lastSample))
    else:
      localizedLastEndTime = None

    # Implemented in two phases:
    #
    # 1. Buffer records to collectorsdb

    for sample in data:
      localizedSampleStartTime = (
        getEasternLocalizedTimestampFromSample(sample["StartDate"],
                                               sample["StartTime"],
                                               sample["UTCOffset"]))

      if localizedSampleStartTime.time() < NAIVE_MARKET_OPEN_TIME:
        # Ignore samples that preceed market open
        _LOG.info("Skipping data before market hours: %s @ %s sample=%s",
                  symbol, localizedSampleStartTime, sample)
        continue

      if localizedSampleStartTime.time() >= NAIVE_MARKET_CLOSE_TIME:
        # Ignore a quirk of the xignite API that duplicates some data at
        # end of trading day. This also excludes the closing auction on
        # NYSE.
        _LOG.info("Skipping data after market hours: %s @ %s sample=%s",
                  symbol, localizedSampleStartTime, sample)
        continue

      if not lastSample or (localizedSampleStartTime >= localizedLastEndTime):
        # Current sample starts at, or after last recorded timestamp ends
        localizedSampleEndTime = (
          getEasternLocalizedTimestampFromSample(sample["EndDate"],
                                                 sample["EndTime"],
                                                 sample["UTCOffset"]))

        ins = (xigniteSecurityBars
               .insert()
               .values(symbol=symbol,
                       StartDate=localizedSampleStartTime.date(),
                       StartTime=localizedSampleStartTime.time(),
                       EndDate=localizedSampleEndTime.date(),
                       EndTime=localizedSampleEndTime.time(),
                       UTCOffset=sample["UTCOffset"],
                       Open=sample["Open"],
                       High=sample["High"],
                       Low=sample["Low"],
                       Close=sample["Close"],
                       Volume=sample["Volume"],
                       Trades=sample["Trades"]))

        @collectorsdb.retryOnTransientErrors
        def _insertBar():
          engine.execute(ins)

        try:
          _insertBar()
        except IntegrityError:
          # Most likely foreign key constraint violation against the
          # xignite_security table
          _LOG.info("Inserting security row for symbol=%s", symbol)
          xignite_agent_utils.insertSecurity(engine, security)

          # Re-insert after resolving IntegrityError
          _insertBar()

    #  2. If in active mode, send ALL un-sent records to Taurus

    if g_opMode != ApplicationConfig.OP_MODE_ACTIVE:
      return

    transmitMetricData(metricSpecs=metricSpecs, symbol=symbol, engine=engine)

  except Exception:
    _LOG.exception("forward failed for metricSpecs=%s", metricSpecs)
    raise



def transmitMetricData(metricSpecs, symbol, engine):
  """ Send unsent metric data samples for the given symbol to Taurus

  NOTE: this is also used externally by friends of the agent; e.g.,
  `resymbol_metrics.py`.

  :param metricSpecs: Sequence of one or more StockMetricSpec objects associated
    with the same stock symbol for which polling was conducted
  :param symbol: stock symbol
  :param sqlalchemy.engine.Engine engine:
  """
  try:
    @collectorsdb.retryOnTransientErrors
    def _fetchUnsentSamples():
      # Select only records that haven't been sent to BOTH
      fields = [
        xigniteSecurityBars.c.StartDate,
        xigniteSecurityBars.c.StartTime,
        xigniteSecurityBars.c.EndDate,
        xigniteSecurityBars.c.EndTime,
        xigniteSecurityBars.c.UTCOffset,
        xigniteSecurityBars.c.Volume,
        xigniteSecurityBars.c.Close,
        emittedStockPrice.c.sent.label("Close_sent"),
        emittedStockVolume.c.sent.label("Volume_sent")
      ]

      sel = (select(fields)
             .select_from(xigniteSecurityBars
                          .outerjoin(emittedStockPrice)
                          .outerjoin(emittedStockVolume))
             .where(xigniteSecurityBars.c.symbol == symbol)
             .where((emittedStockPrice.c.sent == None) |
                    (emittedStockVolume.c.sent == None))
             .order_by(xigniteSecurityBars.c.EndDate.asc(),
                       xigniteSecurityBars.c.EndTime.asc())
      )

      return engine.execute(sel)


    # Process samples in chunks to facilitate more efficient error recovery
    # during backlog processing
    samplesIter = iter(_fetchUnsentSamples())
    while True:
      specSymbolSampleList = []
      sample = None
      for sample in itertools.islice(samplesIter, 0, 1000):
        for spec in metricSpecs:
          if not sample[spec.sampleKey + "_sent"]:
            specSymbolSampleList.append((spec, symbol, sample))

      if sample is None:
        # No more unsent samples
        break

      # Send samples to Taurus
      with metricDataBatchWrite(log=_LOG) as putSample:
        for spec, symbol, sample in specSymbolSampleList:
          if spec.sampleKey in sample:
            epochTs = epochFromLocalizedDatetime(
              _EASTERN_TZ.localize(
                datetime.datetime.combine(sample.StartDate, sample.StartTime)))
            value = sample[spec.sampleKey]

            _LOG.info("Sending: %s %r %d", spec.metricName, value, epochTs)
            putSample(metricName=spec.metricName,
                      value=value,
                      epochTimestamp=epochTs)

      # Update history of emitted samples
      #
      # NOTE: If this fails once in a while and we end up resending the samples,
      # htmengine's Metric Storer will discard duplicate-timestamp and
      # out-of-order samples
      for spec, symbol, sample in specSymbolSampleList:
        _updateMetricDataHistory(spec=spec, symbol=symbol, sample=sample,
                                 engine=engine)
  except Exception:
    _LOG.exception("Unexpected error while attempting to send metric "
                   "data sample(s) to remote Taurus instance.")



@collectorsdb.retryOnTransientErrors
def _updateMetricDataHistory(spec, symbol, sample, engine):
  """ Update history of emitted samples, designating the given sample as sent.

  :param StockMetricSpec spec: metric spec object associated
    with the emitted sample
  :param symbol: stock symbol associated with the data sample
  :param sample: RowProxy object containing the sample's StartDate/Time,
    EndDate/Time and UTCOffset fields
  :param sqlalchemy.engine.Engine engine:
  """
  if spec.sampleKey == "Close":
    target = emittedStockPrice
  elif spec.sampleKey == "Volume":
    target = emittedStockVolume
  else:
    _LOG.error("Unexpected sampleKey (%r).  Not recording record (%r)"
               " as being sent.", spec.sampleKey, sample)
    return

  sentTs = datetime.datetime.utcnow().replace(microsecond=0)

  ins = (target.insert()
         .values(symbol=symbol,
                 StartDate=sample.StartDate,
                 StartTime=sample.StartTime,
                 EndDate=sample.EndDate,
                 EndTime=sample.EndTime,
                 UTCOffset=sample.UTCOffset,
                 sent=sentTs))

  engine.execute(ins)



def _purgeOldRecords():
  """ Purge old rows from xigniteSecurityBars, emittedStockPrice and
  emittedStockVolume tables.

  :param sqlalchemy.engine.Engine engine:
  """
  try:
    deleteBeforeDatetime = datetime.datetime.now(_UTC_TZ).astimezone(
      _EASTERN_TZ)
    deleteBeforeDatetime -= datetime.timedelta(days=RETAIN_DAYS)
    # NOTE: old emittedStockPrice and emittedStockVolume get removed as the
    # result of the foreign key relationships with xigniteSecurityBars
    cleanupQuery = (
      xigniteSecurityBars.delete()
      .where(xigniteSecurityBars.c.EndDate < deleteBeforeDatetime.date())
    )

    @collectorsdb.retryOnTransientErrors
    def runQueryWithRetries():
      return collectorsdb.engineFactory().execute(cleanupQuery).rowcount

    deletedRowCount = runQueryWithRetries()
    if deletedRowCount > 0:
      _LOG.info("Garbage-collected numRows=%d from table=%s",
                deletedRowCount, xigniteSecurityBars)
  except Exception:
    _LOG.exception("_purgeOldRecords failed")
    raise



def main():
  logging_support.LoggingSupport.initService()

  options = _parseArgs()

  # Bind poll() kwargs to CLI options
  pollFn = partial(poll,
                   apitoken=options.apitoken,
                   barlength=options.barlength,
                   days=options.days)

  # Bind forward() kwargs to CLI options
  forwardFn = partial(forward,
                      server=options.server,
                      port=options.port,
                      dryrun=options.dryrun)

  pool = Pool()

  sleepDuration = 60 * options.barlength

  # Load metric specs from metric configuration
  symbolToMetricSpecs = defaultdict(list)
  for spec in loadMetricSpecs():
    symbolToMetricSpecs[spec.symbol].append(spec)
  _LOG.info("Collecting stock data for %s", symbolToMetricSpecs.keys())


  try:
    while True:
      # Run poll() for each symbol in the process pool
      pendingAsyncResults = []
      for security, data in pool.imap_unordered(
          pollFn,
          symbolToMetricSpecs.itervalues()):
        # Forward result (if available) to YOMP/Taurus instance
        if data:
          pendingAsyncResults.append(
            pool.apply_async(
              forwardFn,
              (symbolToMetricSpecs[security["Symbol"]], data, security)))
        else:
          _LOG.info("No new data for %s", security["Symbol"])


      # Run garbage collection on our tables
      pendingAsyncResults.append(pool.apply_async(_purgeOldRecords))

      _LOG.info("Sleeping for %d seconds. zzzzzzzz....", sleepDuration)
      time.sleep(sleepDuration)

      # Wait for all async tasks to complete to avoid out-of-order metric data
      if pendingAsyncResults:
        for r in pendingAsyncResults:
          try:
            r.get()
          except Exception:
            # Async task failed - log and suppress
            _LOG.exception("Async task failed.")

        _LOG.info("Async numTasks=%d completed", len(pendingAsyncResults))

  except KeyboardInterrupt:
    # Log the traceback to help with debugging in case we were deadlocked
    _LOG.info("KeyboardInterrupt detected, exiting...", exc_info=True)
    pass

  finally:
    pool.close()
    pool.join()



def _parseArgs():
  helpString = (
    "./%prog [options]\n\n"
    "This queries XIgnite using the bundled CLI client, feeds the"
    " data into YOMP, and continues to feed in new stock data as it arrives.")

  parser = OptionParser(helpString)

  parser.add_option(
      "--barlength",
      action="store",
      type="int",
      dest="barlength",
      default=DEFAULT_BARLENGTH,
      help="Number of minutes per bar (aggregation period) [default: %default]")

  parser.add_option(
      "--server",
      action="store",
      type="string",
      default=DEFAULT_SERVER,
      help="Server running YOMP to send data to [default: %default]")

  parser.add_option(
      "--port",
      action="store",
      type="string",
      default=DEFAULT_PORT,
      help="Server running YOMP to send data to [default: %default]")

  parser.add_option(
      "--days",
      action="store",
      type="int",
      default=DEFAULT_DAYS,
      dest="days",
      help="Historical backlog data period in days [default: %default]")

  parser.add_option(
      "--dryrun",
      action="store_true",
      default=DEFAULT_DRYRUN,
      dest="dryrun",
      help="Use this flag to do a dry run [default: %default]")

  parser.add_option(
      "--apitoken",
      action="store",
      type="string",
      default=DEFAULT_API_TOKEN,
      dest="apitoken",
      help="XIgnite API Token [default: %default]")

  options, _ = parser.parse_args()

  if not options.apitoken:
    parser.error("Missing required XIgnite API Token")

  return options



if __name__ == "__main__":
  main()
