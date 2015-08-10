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

# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

import os
from pkg_resources import resource_filename, get_distribution

from nta.utils import logging_support_raw
from nta.utils.config import Config

distribution = get_distribution(__name__)

TAURUS_METRIC_COLLECTORS_HOME = os.path.abspath(distribution.location)

CONF_DIR = os.path.join(TAURUS_METRIC_COLLECTORS_HOME, "conf")



logging_support = logging_support_raw
logging_support.setLogDir(
  os.environ.get("TAURUS_METRIC_COLLECTORS_LOG_DIR",
  os.path.join(TAURUS_METRIC_COLLECTORS_HOME, "logs")))



class ApplicationConfig(Config):
  """ Common configration shared by taurus.metric_collectors applications
  """

  # Name of configation object
  CONFIG_NAME = "application.conf"

  # ACTIVE mode: consume datasource, aggregate, forward metrics and non-metric
  # data
  OP_MODE_ACTIVE = "active"

  # HOT STANDBY mode: consume datasource, aggregate and store metrics and
  # non-metric data for forwarding when active mode is resumed, but
  # DO NOT FORWARD metrics/non-metrics
  OP_MODE_HOT_STANDBY = "hot_standby"

  ALL_OP_MODES = tuple([OP_MODE_ACTIVE, OP_MODE_HOT_STANDBY])

  def __init__(self, mode=Config.MODE_LOGICAL):
    super(ApplicationConfig, self).__init__(self.CONFIG_NAME,
                                            CONF_DIR,
                                            mode=mode)

config = ApplicationConfig()

