import platform
import sys

from setuptools import setup, find_packages

setup_requirements = []
install_requirements = []
for req in open("requirements.txt").readlines():
  req = req.strip()
  if req.startswith("numpy"):
    setup_requirements.append(req)
  install_requirements.append(req)

depLinks = []
if "linux" in sys.platform and platform.linux_distribution()[0] == "CentOS":
  depLinks = [ "https://pypi.numenta.com/pypi/nupic", ]

setup(
  name = "htmengine",
  description = "HTM Engine",
  packages = find_packages(),
  include_package_data=True,
  setup_requires = setup_requirements,
  install_requires = install_requirements,
  dependency_links = depLinks,
)
