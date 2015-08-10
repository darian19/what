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
import time

from nta.utils.config import Config
from nta.utils.extended_logger import ExtendedLogger

from YOMP import CONF_DIR

class YOMPExtendedLogger(ExtendedLogger):
  """ Extends the NuPIC ExtendedLogger by calculating the duration of a YOMP
  instance and adding it as a prefix to the log message.
  """
  cached_YOMP_update_epoch = None

  def __init__(self, name):
    super(YOMPExtendedLogger, self).__init__(name)
    self._logPrefix = ""


  @classmethod
  def getExtendedMsg(cls, msg):
    """ Returns the full message to be included in the log. This method is
    specifically used by the logger.debug(msg), logger.warning(msg), etc. in
    sthe ExtendedLogger class.

    :param msg: The msg to be logged.
    :return: The full log message with added prefix.
    """
    try:
      config = Config("application.conf", CONF_DIR)
      if cls.cached_YOMP_update_epoch:
        duration = time.time() - cls.cached_YOMP_update_epoch
      else:
        cls.cached_YOMP_update_epoch = (
          config.getfloat("usertrack", "YOMP_update_epoch"))
        duration = time.time() - cls.cached_YOMP_update_epoch
      YOMPExtendedMsg = "<DUR=%f, %s>%s" % (duration, cls._logPrefix, msg)
    except (ImportError, ValueError):
      YOMPExtendedMsg = "<DUR=NA, %s>%s" % (cls._logPrefix, msg)
    return YOMPExtendedMsg
