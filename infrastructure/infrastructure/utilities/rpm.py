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
We make a lot of RPMs. Utility functions to make building them with Python
scripts less painful.
"""

from infrastructure.utilities import YOMP
from infrastructure.utilities.path import changeToWorkingDir
from infrastructure.utilities.cli import executeCommand, runWithOutput



def bakeRPM(fakeroot,
            rpmName,
            baseVersion,
            artifacts=None,
            iteration="1",
            epoch="1",
            extraFPMarguments=None,
            logger=None,
            debug=False,
            description=None,
            architecture=None,
            postInstall=None):
  """
  Bake an RPM from a fakeroot.

  Generates an fpm command to create the RPM, then calls fpm to do the actual
  RPM build.

  @param fakeroot - The fakeroot to bake

  @param rpmName - Name of RPM

  @param baseVersion - base section of RPM version (the 1.5 in 1.5-101). This
  is a string, not an int. For our RPMs, we should always use semver.org's
  semver format

  @param artifacts - objects in top level of fakeroot to include in the rpm

  @param iteration - iteration portion of the RPM version (the 101 in 1.5-101)

  @param epoch - epoch portion of the RPM. You should never change this

  @param extraFPMarguments - list of extra FPM arguments to include

  @param logger - logger object to use

  @param debug - debug status

  @param description - RPM description

  @param architecture - When present, have fpm force the output RPM's arch
  to this instead of defaulting to using autodetection

  @param postInstall - postinstall script to be included in the RPM
  """

  # Construct the fpm command arguments array.

  # Start with the standard ones for all RPMs
  command = ["fpm",
             "-t", "rpm",
             "-s", "dir",
             "-n", rpmName,
            ]

  if architecture:
    if logger:
      logger.debug("Forcing RPM architecture to %s" % architecture)
    command.append("-a")
    command.append(architecture)

  # Set RPM epoch
  command.append("--epoch")
  command.append(epoch)

  # Set RPM iteration
  command.append("--iteration")
  command.append(iteration)

  # Set RPM version
  command.append("--version")
  command.append(baseVersion)

  # Turn on verbose if we're in debug mode
  if debug:
    if logger:
      logger.debug("Enabling debug mode for fpm...")
    command.append("--verbose")

  # If we were given a description, add it to the RPM
  if description:
    if logger:
      logger.debug("Setting RPM description: %s", description)
    command.append("--description")
    command.append("'" + description + "'")

  # Add a postinstall script if we were given one
  if postInstall:
    if logger:
      logger.debug("Adding --after-install to fpm arguments")
      logger.debug("after-install: %s", postInstall)
    command.append("--after-install")
    command.append(postInstall)

  # Tell fpm where the fakeroot is
  command.append("-C")
  command.append(fakeroot)
  if logger:
    logger.debug("fakeroot: %s", fakeroot)

  # Add any extra fpm arguments
  if extraFPMarguments:
    for fpmArg in extraFPMarguments:
      if logger:
        logger.debug("Adding %s to fpm arguments", fpmArg)
      command.append(fpmArg)

  # Add all the top level artifacts we want included in the RPM
  if artifacts:
    for artifact in artifacts:
      command.append(artifact)
      if logger:
        logger.debug("Including %s in RPM", artifact)

  fpmCommand = " ".join(command)
  if logger:
    logger.debug("fpm command: %s", fpmCommand)
  runWithOutput(command)



def YOMPCloneIntoFakeroot(fakeroot,
                         installDirectory,
                         repoDirectory,
                         YOMPURL,
                         sha=None,
                         logger=None):
  """
  Clone a YOMP repository into a specific path in a fakeroot

  @param fakeroot: path to the directory to use as the root of the RPM's
    install tree

  @param installDirectory: Where to put the new YOMP clone

  @param repoDirectory: what to name the cloned directory

  @param YOMPURL: YOMP URL used to clone

  @param sha (optional): SHA to checkout once we've cloned the repository

  @param logger - Optional logger object, will be used to output more
  debugging information.

  @returns the SHA of the resulting YOMP clone. We may not have been invoked
  with a specific SHA (we normally build tip of master, for example), but we
  always want to include the exact SHA packaged in our RPM descriptions.
  """
  if logger:
    logger.debug("Prepping fakeroot in %s", fakeroot)
  installPath = "%s/%s" % (fakeroot, installDirectory)
  with changeToWorkingDir(installPath):
    if logger:
      logger.debug("Cloning %s into %s/%s/%s",
                   YOMPURL,
                   fakeroot,
                   installDirectory,
                   repoDirectory)
    YOMP.clone(YOMPURL, directory=repoDirectory)
    workDirectory = "%s/%s/%s" % (fakeroot, installDirectory, repoDirectory)
    with changeToWorkingDir(workDirectory):
      if sha:
        YOMP.resetHard()
        logger.debug("Checking out SHA %s in %s", sha, workDirectory)
        YOMP.checkout(sha)
      else:
        logger.debug("No SHA specified, using head of master")
      return YOMP.getCurrentSha()

