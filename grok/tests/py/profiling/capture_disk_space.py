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
Captures disk space periodically and outputs as CSV file to stdout
"""

from collections import namedtuple
import csv
import logging
from optparse import OptionParser
import psutil
import sys
import time

from YOMP import logging_support



gLog = logging.getLogger(__name__)



# Default interval between iterations
_DEFAULT_INTERVAL_SEC = 300



_CsvRow = namedtuple(
  "_CsvRow",
  "timestamp mount device totalB usedB freeB usedPct"
)



def _getDiskUsage():
  """
  :returns: sequence of _CsvRow objects
  """
  rows = []

  timestamp = time.time()

  physicalPartitions = psutil.disk_partitions(all=True)

  for partition in physicalPartitions:
    usage = psutil.disk_usage(partition.mountpoint)

    row = _CsvRow(
      timestamp=timestamp,
      mount=partition.mountpoint,
      device=partition.device,
      totalB=usage.total,
      usedB=usage.used,
      freeB=usage.free,
      usedPct=usage.percent
    )

    rows.append(row)


  return rows



def main(delay, iterations):
  """
  :param delay: Interval between iterations in seconds

  :param iterations: Limit on number of iterations; None for no limit.
  """
  gLog.info("Args: delay=%fs; iterations=%s", delay, iterations)

  csvStream = sys.stdout
  writer = csv.writer(csvStream)

  # Emit CSV header
  writer.writerow(_CsvRow._fields)
  csvStream.flush()

  def forever():
    while True:
      yield None

  if iterations is None:
    limit = forever()
  else:
    limit = xrange(iterations)

  for i in limit:
    csvRows = _getDiskUsage()
    writer.writerows(csvRows)
    sys.stdout.flush()

    if i is None or i < (iterations - 1):
      time.sleep(delay)



def _parseArgs():
  """ Parses command-line args

  :returns: a dict:
    {"delay": <delay-seconds-floating-point>,
     "iterations": <iteration-limit>}
  """
  helpString = (
    "Captures disk space periodically and outputs as CSV file to stdout.\n"
    "%prog [OPTIONS]")

  parser = OptionParser(helpString)

  parser.add_option(
    "--delay",
    action="store",
    type="float",
    default=_DEFAULT_INTERVAL_SEC,
    dest="delay",
    help=("Interval, in seconds, between iterations [default: %default]"))

  parser.add_option(
    "--iterations",
    action="store",
    type="int",
    default=None,
    dest="iterations",
    help=("Maximum number of iterations before exiting [default: %default]"))

  (options, posArgs) = parser.parse_args()

  if len(posArgs) != 0:
    parser.error("Expected zero positional args, but got %s: %s" % (
                 len(posArgs), posArgs,))

  return dict(delay=options.delay, iterations=options.iterations)



if __name__ == "__main__":
  logging_support.LoggingSupport.initTool()

  try:
    main(**_parseArgs())
  except Exception:
    gLog.exception("Failed")
    raise
