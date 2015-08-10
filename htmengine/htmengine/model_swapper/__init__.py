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
from htmengine import raiseExceptionOnMissingRequiredApplicationConfigPath



class ModelSwapperConfig(Config):
  """ Model Swapper layer's configuration parser.

  This layer includes model_swapper_interface_bus, model_scheduler_service,
  swap_controller, slot_agent, and model_runner
  """


  CONFIG_NAME = "model-swapper.conf"


  @raiseExceptionOnMissingRequiredApplicationConfigPath
  def __init__(self):
    super(ModelSwapperConfig, self).__init__(
      self.CONFIG_NAME,
      os.environ["APPLICATION_CONFIG_PATH"]
    )

