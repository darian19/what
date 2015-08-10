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
Generate content for products/taurus.metric_collectors/conf/metrics.json from
the given csv input file and output the json object to stdout. Does not
overwrite metrics.json.

The first line of the input csv file is the header with column names, expected
to contain "Symbol", "Resource" and "Twitter" column headings (possibly among
additional other columns that shall be ignored by the script). The "Twitter"
column heading is expected to be the last column heading, with the column value
containing an optional Twitter screen name preceded by the '@' char. Additional
Twitter screen names, if any, are specified one each in subsequent columns.
"""

import csv
import json
import logging
from optparse import OptionParser
import sys

from taurus.metric_collectors import logging_support



_STOCK_EXCHANGES = ("NYSE", "NASDAQ")



gLog = logging.getLogger("gen_metrics_config")


def getTweetVolumeMetricName(stockSymbol):
  """ Generate Tweet Volume metric name, given the stock symbol

  :param str stockSymbol: stock symbol
  """
  return "TWITTER.TWEET.HANDLE.%s.VOLUME" % (stockSymbol.upper(),)


def _addXigniteStockVolumeMetric(metricsDict, stockSymbol):
  """ Add an xignite stock volume metric to the given metrics dict for the given
  stock symbol
  """
  metricName = "XIGNITE.%s.VOLUME" % (stockSymbol.upper(),)
  metricsDict[metricName] = {
    "provider": "xignite",
    "metricType": "StockVolume",
    "metricTypeName": "Stock Volume",
    "sampleKey": "Volume",
    "modelParams": {
      "minResolution": 0.2
    }
  }



def _addXigniteStockClosingPriceMetric(metricsDict, stockSymbol):
  """ Add an xignite stock price metric to the given metrics dict for
  the given stock symbol
  """
  metricName = "XIGNITE.%s.CLOSINGPRICE" % (stockSymbol.upper(),)
  metricsDict[metricName] = {
    "provider": "xignite",
    "metricType": "StockPrice",
    "metricTypeName": "Stock Price",
    "sampleKey": "Close",
    "modelParams": {
      "minResolution": 0.2
    }
  }



def _addXigniteNewsVolumeMetric(metricsDict, stockSymbol):
  """ Add an xignite security news volume (security headlines + releases)
  metric to the given metrics dict for the given stock symbol
  """
  metricName = "XIGNITE.NEWS.%s.VOLUME" % (stockSymbol.upper(),)
  metricsDict[metricName] = {
    "provider": "xignite-security-news",
    "metricType": "NewsVolume",
    "metricTypeName": "News Volume",
    "modelParams": {
      "minResolution": 0.2
    }
  }



def _addTweetVolumeMetric(metricsDict, stockSymbol, screenNames):
  """ Add a Tweet Volume metric to the given metrics dict for the given stock
  symbol and screen names
  """
  metricName = getTweetVolumeMetricName(stockSymbol)
  metricsDict[metricName] = {
    "provider": "twitter",
    "metricType": "TwitterVolume",
    "metricTypeName": "Twitter Volume",
    "screenNames": list(screenNames),
    "modelParams": {
      "minResolution": 0.6
    }
  }



def main(inputCsvPath):
  """
  :param inputCsvPath: path to input CSV file
  """
  metricsConfig = dict()

  with open(inputCsvPath, "rU") as inputCsv:
    inputReader = csv.reader(inputCsv)

    inputHeader = inputReader.next()
    symbolColumnIndex = inputHeader.index("Symbol")
    stockExchangeColumnIndex = inputHeader.index("Stock Exchange")
    resourceColumnIndex = inputHeader.index("Resource")
    twitterColumnIndex = inputHeader.index("Twitter")

    twitterHandleSet = set()
    symbolSet = set()

    for inputRow in inputReader:
      symbol = inputRow[symbolColumnIndex].strip().upper()
      stockExchange = inputRow[stockExchangeColumnIndex].strip().upper()
      resource = inputRow[resourceColumnIndex].strip()

      if symbol in symbolSet:
        gLog.warn("Multiple occurrences of symbol=%s", symbol)
      else:
        symbolSet.add(symbol)

      if stockExchange not in _STOCK_EXCHANGES:
        gLog.warn("stockExchange=%s not one of %s", stockExchange,
                  _STOCK_EXCHANGES)

      companyObj = {
        "symbol": symbol,
        "stockExchange": stockExchange,
        "metrics": dict()
      }
      metricsConfig[resource] = companyObj

      _addXigniteStockVolumeMetric(companyObj["metrics"], symbol)

      _addXigniteStockClosingPriceMetric(companyObj["metrics"], symbol)

      # NOTE: xignite news volume metrics are suppressed intentionally until we
      # figure out the client GUI for displaying news Summaries, etc.
      #_addXigniteNewsVolumeMetric(companyObj["metrics"], symbol)

      # Create list of twitter handles
      twitterHandles = [
        handle.strip() for handle in inputRow[twitterColumnIndex:] if handle
      ]
      # Validate and remove the "@" prefix from each handle
      screenNames = []
      for handle in twitterHandles:
        assert handle.startswith("@"), (repr(handle), inputRow)
        if handle.lower() in twitterHandleSet:
          gLog.warn("Multiple occurrences of twitterHandle=%s", handle)
        else:
          twitterHandleSet.add(handle.lower())
        screenNames.append(handle[1:])
        assert screenNames[-1], repr(screenNames[-1])
      _addTweetVolumeMetric(companyObj["metrics"], symbol, screenNames)

  json.dump(metricsConfig, sys.stdout, indent=2, sort_keys=True)
  sys.stdout.flush()



def _parseArgs():
  """ Parses command-line args

  :returns: a dict:
    {"inputCsvPath": <inputCsvPath>}
  """
  helpString = (
    "%prog <INPUT_CSV_PATH>\n\n"
    "Generate content for products/taurus.metric_collectors/conf/metrics.json "
    "from the given csv input file and output the json object to stdout. Does "
    "not overwrite metrics.json.\n\n"
    "The first line of the input csv file is the header with column names, "
    "expected to contain \"Symbol\", \"Resource\" and \"Twitter\" column "
    "headings (possibly among additional other columns that shall be ignored "
    "by the script). The \"Twitter\" column heading is expected to be the last "
    "column heading, with the column value containing an optional Twitter "
    "screen name preceded by the '@' char. Additional Twitter screen names, if "
    "any, are specified one each in subsequent columns.")

  parser = OptionParser(helpString)

  (_options, posArgs) = parser.parse_args()

  if len(posArgs) != 1:
    parser.error("Expected one positional args, but got %s: %s" % (
                 len(posArgs), posArgs,))

  inputCsvPath, = posArgs

  return dict(inputCsvPath=inputCsvPath)



if __name__ == "__main__":
  logging_support.LoggingSupport.initTool()

  try:
    main(**_parseArgs())
  except Exception:
    gLog.exception("Failed")
    raise
