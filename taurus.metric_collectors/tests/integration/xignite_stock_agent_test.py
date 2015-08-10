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
import datetime
import json
from mock import call, Mock, patch
import StringIO
import sys
import unittest
import urlparse

import pytz

from taurus.metric_collectors import logging_support
from taurus.metric_collectors.xignite import xignite_stock_agent


def setUpModule():
  logging_support.LoggingSupport.initTestApp()


@patch(
  "taurus.metric_collectors.xignite.xignite_stock_agent.metricDataBatchWrite",
  spec_set=xignite_stock_agent.metricDataBatchWrite)
@patch(
  "taurus.metric_collectors.xignite.xignite_stock_agent.urllib2",
  autospec=True)
class XigniteStockAgentTestCase(unittest.TestCase):

  @patch("taurus.metric_collectors.xignite.xignite_stock_agent.Pool",
    autospec=True)
  @patch("taurus.metric_collectors.xignite.xignite_stock_agent.time",
  autospec=True)
  def testMain(self, time, Pool, urllib2, metricDataBatchWriter):
    # Load metric specs from metric configuration
    symbolToMetricSpecs = defaultdict(list)
    for spec in xignite_stock_agent.loadMetricSpecs():
      symbolToMetricSpecs[spec.symbol].append(spec)

    symbolIter = symbolToMetricSpecs.itervalues()

    time.sleep.side_effect = [None, None, KeyboardInterrupt()]
    Pool.return_value.imap_unordered.return_value = iter([
      ({"Symbol": next(symbolIter)[0].symbol}, [Mock()]),
      ({"Symbol": next(symbolIter)[0].symbol}, [Mock()]),
      ({"Symbol": next(symbolIter)[0].symbol}, [Mock()])
    ])
    with patch.object(sys, "argv", [None, "--apitoken=foobar"]):
      xignite_stock_agent.main()

    self.assertTrue(Pool.called)
    self.assertEqual(Pool.return_value.imap_unordered.call_count, 3)
    self.assertEqual(Pool.return_value.apply_async.call_count, 6)


  def testGetEasternLocalizedTimestampFromSample(self,
                                                 urllib2,
                                                 metricDataBatchWriter):
    timestamp = xignite_stock_agent.getEasternLocalizedTimestampFromSample(
      "12/30/2014", "4:00:00 PM", "-5.0")
    self.assertIsInstance(timestamp, datetime.datetime)
    self.assertEqual(timestamp.hour, 16)
    self.assertEqual(timestamp.minute, 0)
    self.assertEqual(timestamp.second, 0)
    self.assertEqual(timestamp.year, 2014)
    self.assertEqual(timestamp.month, 12)
    self.assertEqual(timestamp.day, 30)
    self.assertEqual(timestamp.tzname(), "EST")


  def testGetEasternLocalizedEndTimestampFromSampleRow(self,
                                                       urllib2,
                                                       metricDataBatchWriter):

    rowproxy = Mock(EndDate=datetime.date(2014, 12,30),
                    EndTime=datetime.time(16, 0, 0))

    timestamp = (
      xignite_stock_agent.getEasternLocalizedEndTimestampFromSampleRow(
        rowproxy))
    self.assertEqual(timestamp.hour, 16)
    self.assertEqual(timestamp.minute, 0)
    self.assertEqual(timestamp.second, 0)
    self.assertEqual(timestamp.year, 2014)
    self.assertEqual(timestamp.month, 12)
    self.assertEqual(timestamp.day, 30)
    self.assertEqual(timestamp.tzname(), "EST")


  def testLoadMetricSpecs(self, urllib2, metricDataBatchWriter):
    metricSpecs = xignite_stock_agent.loadMetricSpecs()

    for spec in metricSpecs:
      self.assertIsInstance(spec, xignite_stock_agent.StockMetricSpec)

    self.assertEqual(len(metricSpecs), len(set(metricSpecs)))


  def testGetData(self, urllib2, metricDataBatchWriter):
    apiResponse = {
      "Outcome": "Success",
      "Message": None,
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
          }
      ],
      "Security": {
          "CIK": "0000789019",
          "CUSIP": None,
          "Symbol": "MSFT",
          "ISIN": None,
          "Valoren": "951692",
          "Name": "Microsoft Corp",
          "Market": "NASDAQ",
          "MarketIdentificationCode": "XNAS",
          "MostLiquidExchange": True,
          "CategoryOrIndustry": "InformationTechnologyServices"
      }
    }

    urllib2.urlopen.return_value = StringIO.StringIO(json.dumps(apiResponse))

    endTime = (datetime.datetime.now(pytz.timezone("UTC"))
                                .astimezone(pytz.timezone("US/Eastern")))

    startTime = endTime + datetime.timedelta(days=1)

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

    result = xignite_stock_agent.getData(
      "foo",
      "bar",
      5,
      startTime.strftime(xignite_stock_agent.DATE_FMT),
      endTime.strftime(xignite_stock_agent.DATE_FMT),
      fields)

    self.assertDictEqual(result, apiResponse)

    self.assertTrue(urllib2.urlopen.called)
    args, _ = urllib2.urlopen.call_args_list[0]
    parseResult = urlparse.urlparse(args[0])
    query = urlparse.parse_qs(parseResult.query)
    self.assertSequenceEqual(query["_fields"][0].split(","), fields)
    self.assertEqual(
      startTime.replace(tzinfo=None, microsecond=0),
      datetime.datetime.strptime(query["StartTime"][0],
                                 xignite_stock_agent.DATE_FMT))
    self.assertEqual(
      endTime.replace(tzinfo=None, microsecond=0),
      datetime.datetime.strptime(query["EndTime"][0],
                                 xignite_stock_agent.DATE_FMT))
    self.assertEqual(query["Identifier"][0], "foo")
    self.assertEqual(query["_Token"][0], "bar")
    self.assertEqual(query["Period"][0], "5")


  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent.getData",
    autospec=True)
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent._getLatestSample",
    autospec=True)
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent.collectorsdb",
    autospec=True)
  def testPoll(self, collectorsdb, _getLatestSample, getData, urllib2,
               metricDataBatchWriter):

    getData.return_value = {
      "Outcome": "Success",
      "Message": None,
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
          }
      ],
      "Security": {
          "CIK": "0000789019",
          "CUSIP": None,
          "Symbol": "MSFT",
          "ISIN": None,
          "Valoren": "951692",
          "Name": "Microsoft Corp",
          "Market": "NASDAQ",
          "MarketIdentificationCode": "XNAS",
          "MostLiquidExchange": True,
          "CategoryOrIndustry": "InformationTechnologyServices"
      }
    }

    mockSample = Mock(EndDate=datetime.date(2015, 1, 15),
                      EndTime=datetime.time(9, 30, 0))
    _getLatestSample.return_value=mockSample

    msft = xignite_stock_agent.StockMetricSpec(
      metricName="XIGNITE.MSFT.VOLUME",
      symbol="MSFT",
      stockExchange="NASDAQ",
      sampleKey="Volume")
    result = xignite_stock_agent.poll((msft,),
                                      apitoken="apitoken",
                                      barlength=5,
                                      days=21)
    self.assertIsInstance(result, tuple)
    self.assertDictEqual(getData.return_value["Security"], result[0])
    self.assertSequenceEqual(getData.return_value["Bars"], result[1])

    # Check that exceptions raised in getData are handled gracefully

    getData.reset_mock()
    getData.side_effect = Exception("Test exception")

    result = xignite_stock_agent.poll((msft,),
                                      apitoken="apitoken",
                                      barlength=5,
                                      days=21)

    self.assertIsInstance(result, tuple)
    self.assertDictEqual({"Symbol": "MSFT"}, result[0])
    self.assertIsInstance(result[1], list)
    self.assertFalse(result[1])


  @unittest.skip("TAUR-1335")
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent._getLatestSample",
    autospec=True)
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent.collectorsdb",
    autospec=True)
  def testForward(self, collectorsdb, _getLatestSample,
                  urllib2, metricDataBatchWriter):

    mockSample = Mock(EndDate=datetime.date(2015, 1, 15),
                      EndTime=datetime.time(9, 30, 0))
    _getLatestSample.return_value=mockSample

    data = [
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
      }
    ]

    security = {
      "CIK": "0000789019",
      "CUSIP": None,
      "Symbol": "MSFT",
      "ISIN": None,
      "Valoren": "951692",
      "Name": "Microsoft Corp",
      "Market": "NASDAQ",
      "MarketIdentificationCode": "XNAS",
      "MostLiquidExchange": True,
      "CategoryOrIndustry": "InformationTechnologyServices"
    }


    collectorsdb.retryOnTransientErrors.side_effect = [
      Mock(),
      Mock(),
      Mock(return_value = [Mock(StartDate=datetime.date(2015, 1, 15),
                                StartTime=datetime.time(9, 30),
                                EndDate=datetime.date(2015, 1, 15),
                                EndTime=datetime.time(9, 35),
                                UTCOffset=-5.0,
                                Volume=504494,
                                Close=45.96,
                                Close_sent=None,
                                Volume_sent=None,
                                __getitem__ = Mock(side_effect = {
                                  "Close_sent": None,
                                  "Volume_sent": None,
                                  "Volume": 504494}.__getitem__),
                                __contains__ = Mock(side_effect={
                                  "Volume": None
                                  }.__contains__)),
                           Mock(StartDate=datetime.date(2015, 1, 15),
                                StartTime=datetime.time(9, 35),
                                EndDate=datetime.date(2015, 1, 15),
                                EndTime=datetime.time(9, 40),
                                UTCOffset=-5.0,
                                Volume=492621,
                                Close=45.79,
                                Close_sent=None,
                                Volume_sent=None,
                                __getitem__ = Mock(side_effect = {
                                  "Close_sent": None,
                                  "Volume_sent": None,
                                  "Volume": 492621}.__getitem__),
                                __contains__ = Mock(side_effect={
                                  "Volume": None
                                  }.__contains__))
                          ])
    ]


    msft = xignite_stock_agent.StockMetricSpec(
      metricName="XIGNITE.MSFT.VOLUME",
      symbol="MSFT",
      stockExchange="NASDAQ",
      sampleKey="Volume")

    xignite_stock_agent.forward((msft,), data, security)

    metricDataBatchWriter.return_value.__enter__.return_value.call_args_list
    self.assertEqual(
      metricDataBatchWriter.return_value.__enter__.return_value.call_count, 2)
    metricDataBatchWriter.return_value.__enter__.return_value.assert_has_calls(
      [call(metricName="XIGNITE.MSFT.VOLUME",
            value=504494,
            epochTimestamp=1421332200.0),
       call(metricName="XIGNITE.MSFT.VOLUME",
            value=492621,
            epochTimestamp=1421332500.0)])


  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent._getLatestSample",
    autospec=True)
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent.collectorsdb",
    autospec=True)
  def testForwardAfterHours(self, collectorsdb, _getLatestSample,
                  urllib2, metricDataBatchWriter):

    mockSample = Mock(EndDate=datetime.date(2015, 1, 15),
                      EndTime=datetime.time(17, 30, 0))
    _getLatestSample.return_value = mockSample

    data = [
      {
          "StartDate": "1/15/2015",
          "StartTime": "5:30:00 PM",
          "EndDate": "1/15/2015",
          "EndTime": "5:35:00 PM",
          "UTCOffset": -5,
          "Open": 46.225,
          "High": 46.38,
          "Low": 45.955,
          "Close": 45.96,
          "Volume": 504494,
          "Trades": 2414,
          "TWAP": 46.1765,
          "VWAP": 46.1756
      }
    ]

    security = {
      "CIK": "0000789019",
      "CUSIP": None,
      "Symbol": "MSFT",
      "ISIN": None,
      "Valoren": "951692",
      "Name": "Microsoft Corp",
      "Market": "NASDAQ",
      "MarketIdentificationCode": "XNAS",
      "MostLiquidExchange": True,
      "CategoryOrIndustry": "InformationTechnologyServices"
    }


    collectorsdb.retryOnTransientErrors.side_effect = [
      Mock(),
      Mock(),
      Mock(return_value = [Mock(StartDate=datetime.date(2015, 1, 15),
                                StartTime=datetime.time(17, 30),
                                EndDate=datetime.date(2015, 1, 15),
                                EndTime=datetime.time(17, 35),
                                UTCOffset=-5.0,
                                Volume=504494,
                                Close=45.96,
                                Close_sent=None,
                                Volume_sent=None,
                                __getitem__ = Mock(side_effect = {
                                  "Close_sent": None,
                                  "Volume_sent": None,
                                  "Volume": 504494}.__getitem__),
                                __contains__ = Mock(side_effect={
                                  "Volume": None
                                  }.__contains__))
                          ])
    ]


    msft = xignite_stock_agent.StockMetricSpec(
      metricName="XIGNITE.MSFT.VOLUME",
      symbol="MSFT",
      stockExchange="NASDAQ",
      sampleKey="Volume")

    xignite_stock_agent.forward((msft,), data, security)

    #import pdb; pdb.set_trace()


  @unittest.skip("TAUR-1335")
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent._getLatestSample",
    autospec=True)
  @patch(
    "taurus.metric_collectors.xignite.xignite_stock_agent.collectorsdb",
    autospec=True)
  def testForwardNoLastSample(self, collectorsdb, _getLatestSample,
                              urllib2, metricDataBatchWriter):

    _getLatestSample.return_value = None

    data = [
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
      }
    ]

    security = {
      "CIK": "0000789019",
      "CUSIP": None,
      "Symbol": "MSFT",
      "ISIN": None,
      "Valoren": "951692",
      "Name": "Microsoft Corp",
      "Market": "NASDAQ",
      "MarketIdentificationCode": "XNAS",
      "MostLiquidExchange": True,
      "CategoryOrIndustry": "InformationTechnologyServices"
    }


    collectorsdb.retryOnTransientErrors.side_effect = [
      Mock(),
      Mock(),
      Mock(return_value = [Mock(StartDate=datetime.date(2015, 1, 15),
                                StartTime=datetime.time(9, 30),
                                EndDate=datetime.date(2015, 1, 15),
                                EndTime=datetime.time(9, 35),
                                UTCOffset=-5.0,
                                Volume=504494,
                                Close=45.96,
                                Close_sent=None,
                                Volume_sent=None,
                                __getitem__ = Mock(side_effect = {
                                  "Close_sent": None,
                                  "Volume_sent": None,
                                  "Volume": 504494}.__getitem__),
                                __contains__ = Mock(side_effect={
                                  "Volume": None
                                  }.__contains__)),
                           Mock(StartDate=datetime.date(2015, 1, 15),
                                StartTime=datetime.time(9, 35),
                                EndDate=datetime.date(2015, 1, 15),
                                EndTime=datetime.time(9, 40),
                                UTCOffset=-5.0,
                                Volume=492621,
                                Close=45.79,
                                Close_sent=None,
                                Volume_sent=None,
                                __getitem__ = Mock(side_effect = {
                                  "Close_sent": None,
                                  "Volume_sent": None,
                                  "Volume": 492621}.__getitem__),
                                __contains__ = Mock(side_effect={
                                  "Volume": None
                                  }.__contains__))
                          ])
    ]


    msft = xignite_stock_agent.StockMetricSpec(
      metricName="XIGNITE.MSFT.VOLUME",
      symbol="MSFT",
      stockExchange="NASDAQ",
      sampleKey="Volume")

    xignite_stock_agent.forward((msft,), data, security)

    metricDataBatchWriter.return_value.__enter__.return_value.call_args_list
    self.assertEqual(
      metricDataBatchWriter.return_value.__enter__.return_value.call_count, 2)
    metricDataBatchWriter.return_value.__enter__.return_value.assert_has_calls(
      [call(metricName="XIGNITE.MSFT.VOLUME",
            value=504494,
            epochTimestamp=1421332200.0),
       call(metricName="XIGNITE.MSFT.VOLUME",
            value=492621,
            epochTimestamp=1421332500.0)])
