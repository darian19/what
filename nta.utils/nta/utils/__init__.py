from pkg_resources import get_distribution
import os


# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
  __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
  from pkgutil import extend_path
  __path__ = extend_path(__path__, __name__)



CONF_DIR = os.path.join(get_distribution(__name__).location, "conf")



def makeDirectoryFromAbsolutePath(absDirPath):
  """ Makes directory for the given directory path with default permissions.
  If the directory already exists, it is treated as success.

  absDirPath:   absolute path of the directory to create.

  Returns:      absDirPath arg

  Exceptions:         OSError if directory creation fails
  """

  assert os.path.isabs(absDirPath)

  try:
    os.makedirs(absDirPath)
  except OSError, e:
    if e.errno != os.errno.EEXIST:
      raise

  return absDirPath


import logging_support_raw
import config
