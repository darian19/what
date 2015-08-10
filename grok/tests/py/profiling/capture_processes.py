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
Captures process information periodically and outputs as CSV file to stdout.
The information is along the lines of the `ps aux` command.
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



#USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
_CsvRow = namedtuple(
  "_CsvRow",
  "timestamp user pid ppid cpuPct cpuU cpuS cpuT memPct vszB rssB tty status "
  "nice created threads fds reads writes readB writeB cmdline"
)



def _getProcesses():
  """
  :returns: sequence of _CsvRow objects
  """
  rows = []

  timestamp = time.time()

  for p in psutil.process_iter():
    try:
      memInfo = p.get_memory_info()

      if hasattr(p, "get_io_counters"):
        ioCounters = p.get_io_counters()
        reads = ioCounters.read_count
        writes = ioCounters.write_count
        readB = ioCounters.read_bytes
        writeB = ioCounters.write_bytes
      else:
        reads = writes = readB = writeB = None

      cpuTimes = p.get_cpu_times()

      row = _CsvRow(
        timestamp=timestamp,
        user=p.username,
        pid=p.pid,
        ppid=p.ppid,
        cpuPct=p.get_cpu_percent(interval=0),
        cpuU=cpuTimes.user,
        cpuS=cpuTimes.system,
        cpuT=cpuTimes.user + cpuTimes.system,
        memPct=p.get_memory_percent(),
        vszB=memInfo.vms,
        rssB=memInfo.rss,
        tty=p.terminal,
        status=p.status,
        nice=p.get_nice(),
        created=p.create_time,
        threads=p.get_num_threads(),
        fds=p.get_num_fds(),
        reads=reads,
        writes=writes,
        readB=readB,
        writeB=writeB,
        cmdline=' '.join(p.cmdline)[:200],
      )
    except (psutil.AccessDenied, psutil.NoSuchProcess):
      continue

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
    csvRows = _getProcesses()
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
    "Captures process information periodically and outputs as CSV file to "
    "stdout. The information is along the lines of the `ps aux` command.\n"
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
