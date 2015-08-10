#!/usr/bin/python
#------------------------------------------------------------------------------
# Copyright 2013-2014 Numenta Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#------------------------------------------------------------------------------
""" YOMP Custom Metrics sample data collector.  Run this periodically using
    a scheduler such as cron to report open file descriptors (the total number
    of files open by all processes).
"""
import datetime
import subprocess
import time

from YOMPcli.api import YOMPSession
try:
  from sample_credentials import (YOMP_API_KEY,
                                  YOMP_SERVER,
                                  METRIC_NAME)
except (SyntaxError, ImportError):
  print ("\nERROR: You must update YOMP credentials in sample_credentials.py "
         "before you can continue.\n")
  import sys
  sys.exit(1)



if __name__ == "__main__":
  # YOMP client
  YOMP = YOMPSession(server=YOMP_SERVER, apikey=YOMP_API_KEY)

  # Add custom metric data
  with YOMP.connect() as sock:
    print 'Collecting "Open file descriptors" sample...',
    count = subprocess.check_output("/usr/sbin/lsof | /usr/bin/wc -l",
                                    shell=True).strip()
    print count
    print 'Sending sample to YOMP Metric named "%s"' % METRIC_NAME
    ts =  time.mktime(datetime.datetime.utcnow().timetuple())
    sock.sendall("%s %s %d\n" % (METRIC_NAME, count, ts))
    print "Done!"

