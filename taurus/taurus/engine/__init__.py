import os
from pkg_resources import get_distribution

from nta.utils import logging_support_raw
from nta.utils.config import Config



# TODO: TAUR-1209 use __name__ or "taurus.engine"
distribution = get_distribution("taurus")

__version__ = distribution.version # See setup.py for constant

TAURUS_HOME = distribution.location

logging_support = logging_support_raw
logging_support.setLogDir(os.environ.get("APPLICATION_LOG_DIR",
                          os.path.join(TAURUS_HOME, "logs")))

appConfigPath = os.environ.get("APPLICATION_CONFIG_PATH")
if appConfigPath is None:
  raise KeyError("APPLICATION_CONFIG_PATH environment variable must be set for "
                 "Taurus")

config = Config("application.conf", appConfigPath)
