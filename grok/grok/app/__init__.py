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
import os

from nta.utils.config import Config



if "YOMP_HOME" in os.environ:
  # Get YOMP_HOME from environment
  YOMP_HOME = os.environ["YOMP_HOME"]

else:
  # Calculate default YOMP_HOME based on relative path
  YOMP_HOME = os.path.abspath(os.path.dirname(__file__) + '../../..')



class YOMPAppConfig(Config):

  CONFIG_NAME = "application.conf"

  def __init__(self, mode=Config.MODE_LOGICAL):
    super(YOMPAppConfig, self).__init__(self.CONFIG_NAME,
                                        os.path.join(YOMP_HOME, "conf"),
                                        mode=mode)



class YOMPProductConfig(Config):

  CONFIG_NAME = "product.conf"

  def __init__(self, mode=Config.MODE_LOGICAL):
    super(YOMPProductConfig, self).__init__(self.CONFIG_NAME,
                                            os.path.join(YOMP_HOME, "conf"),
                                            mode=mode)



config = YOMPAppConfig()
product = YOMPProductConfig()

DEBUG_LEVEL = 0
if config.has_option('web', 'debug_level'):
  DEBUG_LEVEL = config.get('web', 'debug_level')
