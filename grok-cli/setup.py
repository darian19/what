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
"""
  YOMP CLI
  ========

  Included in the YOMP CLI package is a `YOMP` console script, and a reusable
  `YOMPcli` Python package.  See README.md for usage and additional details.

  Installation notes
  ------------------

  This file (setup.py) is provided to support installation using the native
  python setuptools-based ecosystem, including PyPi, `easy_install` and `pip`.

  Disclaimer:  Your specific environment _may_ require additional arguments to
  pip, setup.py and easy_install such as `--root`, `--install-option`,
  `--script-dir`, `--script-dir`, or you may use `sudo` to install at the system
  level.

  Building source distribution for release
  ----------------------------------------

  The source distribution package is built using the `sdist build` sub-command:

      python setup.py sdist build

  Resulting in the creation of dist/YOMPcli-1.0.tar.gz, which will be uploaded
  to PyPi (or another distribution channel).  The YOMPcli package can be
  installed from the tarball directly using a number of approaches:

      pip install YOMPcli-1.0.tar.gz
      easy_install YOMPcli-1.0.tar.gz

  Or, by using setup.py:

      tar xzvf YOMPcli-1.0.tar.gz
      cd YOMPcli-1.0.tar.gz
      python setup.py install

  Once uploaded to PyPi, YOMPcli can be installed by name:

      pip install YOMPcli
      easy_install YOMPcli

  Alternate installation by `pip wheel`
  -------------------------------------

  Recently, pip has added a new binary distribution format "wheel", which
  simplifies the process somewhat.

  To create a wheel:

      pip wheel .

  Resulting in the creation of wheelhouse/YOMPcli-1.0-py27-none-any.whl along
  with a few other .whl files related to YOMPcli dependencies.

  To install from cached wheel:

      pip install --use-wheel --no-index --find-links=wheelhouse/ wheelhouse/YOMPcli-1.0-py27-none-any.whl

  Or, from PyPi, assuming the wheels have been uploaded to PyPi:

      pip install --use-wheel YOMPcli


  Uploading to PyPi
  -----------------

  Build and upload source, egg, and wheel distributions to PyPi:

      python setup.py sdist bdist_wheel bdist_egg upload
"""
import sys
from setuptools import find_packages, setup



def printTerms():
  print("\nBy using the YOMP CLI, you agree to terms and conditions\n"
        "outlined in the product End User License Agreement (EULA):\n"
        "https://aws.amazon.com/marketplace/agreement?asin=B00I18SNQ6\n")


def printRegisterHint():
  print("If you haven't already registered, please do so by visiting\n"
        "the URL: YOMP_SERVER/YOMP/register, to help us serve you better.\n")



requirements = map(str.strip, open("requirements.txt").readlines())

version = {}
execfile("YOMPcli/__version__.py", {}, version)

setup(
  name = "YOMPcli",
  description = "YOMP Command Line Interface",
  url = "https://YOMPhub.com/numenta/numenta-apps/YOMP-cli",
  classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 2",
    "Topic :: Utilities"],
  keywords = "YOMP, numenta, anomaly detection, monitoring",
  author = "Austin Marshall, Chetan Surpur",
  author_email = "amarshall@numenta.com, csurpur@numenta.com",
  packages = find_packages(),
  entry_points = {"console_scripts": ["YOMP = YOMPcli:main"]},
  install_requires = requirements,
  extras_require = {"docs": ["sphinx"], "samples": ["dogapi"]},
  version = version["__version__"]
)

if "sdist" not in sys.argv:
  # Don't print terms or registration hint when building Python distribution
  printTerms()
  printRegisterHint()
