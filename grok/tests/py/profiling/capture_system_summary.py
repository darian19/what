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
Captures system summary periodically and outputs as CSV file to stdout.
The information is along the lines of the Summary of the `top` command.
"""

from collections import namedtuple
import csv
import logging
from optparse import OptionParser
import os
import psutil
import sys
import time

from YOMP import logging_support



gLog = logging.getLogger(__name__)



# Default interval between iterations
_DEFAULT_INTERVAL_SEC = 300



#top - 20:48:21 up  4:51,  1 user,  load average: 0.00, 0.00, 0.00
#Tasks:  82 total,   1 running,  81 sleeping,   0 stopped,   0 zombie
#Cpu(s):  0.3%us,  0.4%sy,  0.0%ni, 98.8%id,  0.4%wa,  0.0%hi,  0.0%si,  0.1%st
#Mem:   7513704k total,   951432k used,  6562272k free,    35712k buffers
#Swap:        0k total,        0k used,        0k free,   623092k cached
_CsvRow = namedtuple(
  "_CsvRow",
  "timestamp loadAvg1 loadAvg5 loadAvg15 "
  "cpuUserPct cpuSystemPct cpuNicePct  cpuIdlePct "
  "memTotalB memAvailB memUsageB memUsagePct memBuffersB memCachedB "
  "swapTotalB swapUsedB swapFreeB swapUsedPct swapInsB swapOutsB"
)



def _getSummary():
  """
  :returns: a _CsvRow object
  """
  timestamp = time.time()
  loadAvg1, loadAvg5, loadAvg15 = os.getloadavg()
  cpuTimesPct = psutil.cpu_times_percent(interval=0)
  virtualMem = psutil.virtual_memory()
  swapMem = psutil.swap_memory()

  row = _CsvRow(
    timestamp=timestamp,
    loadAvg1=loadAvg1,
    loadAvg5=loadAvg5,
    loadAvg15=loadAvg15,
    cpuUserPct=cpuTimesPct.user,
    cpuSystemPct=cpuTimesPct.system,
    cpuNicePct=cpuTimesPct.nice,
    cpuIdlePct=cpuTimesPct.idle,
    memTotalB=virtualMem.total,
    memUsageB=virtualMem.total - virtualMem.available,
    memAvailB=virtualMem.available,
    memUsagePct=virtualMem.percent,
    memBuffersB=virtualMem.buffers if hasattr(virtualMem, "buffers") else None,
    memCachedB=virtualMem.cached if hasattr(virtualMem, "cached") else None,
    swapTotalB=swapMem.total,
    swapUsedB=swapMem.used,
    swapFreeB=swapMem.free,
    swapUsedPct=swapMem.percent,
    swapInsB=swapMem.sin,
    swapOutsB=swapMem.sout
  )

  return row



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
    csvRow = _getSummary()
    writer.writerow(csvRow)
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
    "Captures system summary periodically and outputs as CSV file to stdout. "
    "The information is along the lines of the Summary of the `top` command.\n"
    "%prog [OPTIONS]"
    )

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
