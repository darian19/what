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
  Utility methods for handling the environment.
"""

import os
import platform
import sys



def prependPath(prefix, suffix):
  """
    Prepends the given prefix (path) to the suffix (path)

    :param prefix: The path to be added before suffix
    :param suffix: The tailing bit of the path.

    :returns: A `String` representing the path
    :rtype: string
  """
  path = [prefix]

  if suffix is not None:
    path.append(suffix)

  return os.pathsep.join(path)



def prepareEnv(workspace, nupicBuildDir=None, environ=None):
  """
    Return dict defining the environment variables to be used during build.

    :returns: A ```dict``` representing the environment required to build
    NuPIC and other products. It consists of HOME, USER, NUPIC, NTA,
    PYTHONPATH, BUILD_WORKSPACE, APPLICATION_CONFIG_PATH and some other
    variables required for building NuPIC.

    :rtype: dict
    {
        "HOME": "/path/to/home",
        "USER": "ec2-user",
        "BUILD_WORKSPACE": "path/to/workspace",
        "REPOSITORY": "path/to/nupic/repository",
        "PY_VERSION": "python version",
        "YOMP_HOME": "path/to/YOMP/home",
        "LD_LIBRARY_PATH": "path/to/lib",
        "NUPIC": "/path/to/nupic",
        "NTA": "/path/to/nupic/build/release",
        "PATH": "path/to/nupic/build/release/bin",
        "PYTHONPATH": "path/to/nupic/build/release/lib/python",
        "NTA_ROOT_DIR": "/path/to/nupic/build/release",
        "NTA_DATA_PATH": "/path/to/nupic/build/release/share/prediction/data",
        "APPLICATION_CONFIG_PATH": "path/to/YOMP/home/conf",
        "ARCHFLAGS": "-arch x86_64",
        "MACOSX_DEPLOYMENT_TARGET": "version of OS X",
    }
  """

  environ = environ or {}

  env = dict(
    HOME=environ.get("HOME"),
    USER=environ.get("USER"),
    BUILD_WORKSPACE=workspace,
    REPOSITORY=os.path.join(nupicBuildDir or workspace, "nupic"),
    PY_VERSION=sys.version[:3],
    PRODUCTS=os.path.join(workspace, "products"),
    YOMP_HOME=os.path.join(workspace, "products", "YOMP"),
    LD_LIBRARY_PATH=environ.get("LD_LIBRARY_PATH")
  )

  env.update(
    NUPIC=env["REPOSITORY"]
  )

  env.update(
    NTA=os.path.join(env["NUPIC"], "build/release")
  )

  env.update(
    PATH=prependPath(os.path.join(env["NTA"], "bin"), environ.get("PATH")),
    PYTHONPATH=prependPath(os.path.join(env["NTA"], "lib/python%s/site-packages"
                                                    % env["PY_VERSION"]),
                                                    environ.get("PYTHONPATH")),
    NTA_ROOT_DIR=env["NTA"],
    NTA_DATA_PATH=os.path.join(env["NTA"], "share/prediction/data"),
    APPLICATION_CONFIG_PATH=os.path.join(env["YOMP_HOME"], "conf")
  )

  env.update(
    PYTHONPATH=prependPath(env["NTA"], env["PYTHONPATH"])
  )

  env.update(
    PATH=prependPath(os.path.join(env["YOMP_HOME"], "bin"), env["PATH"]),
    PYTHONPATH=prependPath(os.path.join(env["YOMP_HOME"],
                           "lib/python%s/site-packages" % env["PY_VERSION"]),
                           env["PYTHONPATH"])
  )

  if "darwin" in sys.platform:
    env.update(
      ARCHFLAGS="-arch x86_64",
      MACOSX_DEPLOYMENT_TARGET="10.10"
  )

  if "centos" in platform.platform():
    env.update(
      CPP="/opt/rh/devtoolset-2/root/usr/bin/cpp",
      CXX="/opt/rh/devtoolset-2/root/usr/bin/c++",
      CC="/opt/rh/devtoolset-2/root/usr/bin/gcc"
    )
  return env



def addNupicCoreToEnv(env, nupicCoreDir):
  """
    Updates the environment variables.

    :param env: The environment dict that needs to be updated
    :param nupicCoreDir: The directory of the nupic.core to be updated.

    :return: Updated environment

    :rtype: dict
  """
  env.update(
    NUPIC_CORE_DIR=nupicCoreDir,
  )
