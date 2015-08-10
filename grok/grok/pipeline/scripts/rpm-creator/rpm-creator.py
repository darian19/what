#!/usr/bin/env python2.7
# ----------------------------------------------------------------------
# Copyright (C) 2013-2014, Numenta, Inc.  Unless you have purchased from
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

import argparse
import os
import sys
import tempfile
import time

from shutil import rmtree

from infrastructure.utilities import YOMP
from infrastructure.utilities import logger as log
from infrastructure.utilities.exceptions import MissingDirectoryError
from infrastructure.utilities.path import changeToWorkingDir
from infrastructure.utilities.cli import runWithOutput



# Use a global for the timestamp, we will need to use it several times in
# the course of creating an RPM and it needs to be consistent.
VERSION_TIMESTAMP = time.strftime("%Y%m%d.%H.%M.%S")


def packageDirectory(fakeroot,
                     packageName,
                     baseVersion,
                     afterInstall,
                     sha=None,
                     workDir=None,
                     depends=None,
                     arch=None,
                     description=None,
                     epoch=0,
                     release=0,
                     directoriesOwned=None
                     ):
  """
  Package a directory into an rpm. Generates rpms named in the following
  format:

    packageName-baseVersion-release.arch.rpm

  or

    packageName_sha-baseVersion-release.arch.rpm

  :param fakeroot: path to the directory to use as the root of the RPM's
    install tree
  :param packageName: This is the base name for the package. yum install
    packageName will pull the latest version
  :param baseVersion: The base version.
  :param sha: if passed, we include it in the package name as packageName_sha
  :param workDir: directory path, passed to fpm.
  :param depends: comma separated list of packages required before this can
    be installed.
  :param arch: architecture. Either noarch or x86_64.
  :description: description to include in the rpm.
  :epoch: passed to fpm for use as the rpm epoch. Typically 0.
  :release: String. We either use commits since the release tag,
    or YYYY.MM.DD.HH.MM.SS.
  :directoriesOwned: comma separated list of directories that the rpm should
    tag as owned by the rpm. Directories in this list will be removed when
    the rpm is uninstalled if they are empty after the package's files are
    removed.
  """

  command = "fpm --verbose "
  if not arch:
    if sys.platform.startswith("darwin"):
      # We're running on OS X, force noarch
      rpmType = "noarch"
      command += "-a noarch "
    else:
      rpmType = "x86_64"
  else:
    rpmType = arch
  if release > 0:
    rpmRelease = release
  else:
    rpmRelease = VERSION_TIMESTAMP
  if sha:
    rpmName = "%s_%s-%s-%s.%s.rpm" % (packageName,
                                      sha,
                                      baseVersion,
                                      rpmRelease,
                                      rpmType)
  else:
    rpmName = "%s-%s-%s.%s.rpm" % (packageName,
                                   baseVersion,
                                   rpmRelease,
                                   rpmType)
  command += "--epoch %s -s dir -t rpm --architecture %s " % (epoch, rpmType)

  if description:
    command += "--description '%s' " % (description)
  command += "--name %s " % (packageName)

  if depends:
    for dependency in depends.split(","):
      command += "-d %s " % (dependency)

  command += "--version %s --iteration %s --package %s -C %s " % (baseVersion,
                                                                  rpmRelease,
                                                                  rpmName,
                                                                  fakeroot)

  if directoriesOwned != None:
    command += "--directories %s " % directoriesOwned

  if workDir:
    command += "--workdir %s " % (workDir)

  if afterInstall:
    command += "--after-install %s " % (afterInstall)

  # Find the top level files/dirs in the fakeroot and add them explicitly
  # to fpm's argument list
  fakerootFiles = os.listdir(fakeroot)
  for rpmEntry in fakerootFiles:
    command += "%s " % (rpmEntry)
  g_logger.debug("Running %s ... ", command)
  runWithOutput(command)
  return rpmName


def cleanseFakeroot(fakeroot, installDirectory, repoDirectory):
  """Clean up a fakeroot by running prepare_repo_for_packaging if present in
  the repoDirectory. Will be called by prepFakerootFromGit and
  prepFakerootFromDirectory for each of their subdirectories.

  :param fakeroot: path to the directory to use as the root of the RPM's
    install tree
  :param installDirectory: To construct the path relative to fakeroot for
    cleanup.
  :param repoDirectory: It also used to construct the path relative to fakeroot
    for cleanup.
  """

  # Don't count on prepare_repo_for_packaging coping well if it is not run
  # from the root of the repo checkout, so store the pwd and cd into the repo
  # checkout before running cleaner or removing .YOMP
  g_logger.debug("Cleaning fakeroot: %s", fakeroot)
  workpath = "%s/%s/%s" % (fakeroot, installDirectory, repoDirectory)
  if os.path.isdir(workpath):
    with changeToWorkingDir(workpath):
      cleanerScript = "%s/%s/%s/prepare_repo_for_packaging" % (fakeroot,
                                                               installDirectory,
                                                               repoDirectory)
      if os.path.isfile(cleanerScript):
        if os.path.isfile("/tmp/noclean.rpms"):
          g_logger.info("Found /tmp/noclean.rpms, skipping cleanup script")
        else:
          g_logger.info("Found %s, executing", cleanerScript)
          runWithOutput("%s --destroy-all-my-work" % cleanerScript)
      else:
        g_logger.debug("Optional cleanup script %s not found, skipping",
                       cleanerScript)


def commonFakerootPrep(fakeroot, installDirectory):
  """Common prep work which means creating install directory
     for both YOMP checkouts and other directories.

  :param fakeroot: Will be used as the root of the RPM's installed files.
  :param installDirectory: the subdirectory to prepare of the fakeroot
  """

  installPath = "%s/%s" % (fakeroot, installDirectory)
  os.makedirs(installPath)
  return installPath


def loadGitDescribeFromDirectory(YOMPDirectory):
  """
  Load & parse YOMP describe data from YOMPDirectory

  :param YOMPDirectory: path to a YOMP clone.
  """

  versionData = {}
  with changeToWorkingDir(YOMPDirectory):
    try:
      rawVersion = runWithOutput("YOMP describe --long --tags --abbrev=40")\
                                 .strip().split("-")
      versionData["version"] = rawVersion[0]
      versionData["commitsSinceTag"] = rawVersion[1]
      versionData["sha"] = rawVersion[2]
    except RuntimeError:
      versionData = None
  return versionData


def prepFakerootFromGit(fakeroot,
                        installDirectory,
                        repoDirectory,
                        YOMPURL,
                        sha=None):
  """Clone a YOMP repository and make a fakeroot out of it.

  :param fakeroot: path to the directory to use as the root of the RPM's
    install tree
  :param installDirectory: Where to put the new YOMP clone
  :param repoDirectory: what to name the cloned directory
  :param YOMPURL: YOMP URL used to clone
  :param sha (optional): SHA to checkout once we've cloned the repository
  """

  g_logger.debug("Prepping fakeroot in %s", fakeroot)
  installPath = commonFakerootPrep(fakeroot, installDirectory)
  with changeToWorkingDir(installPath):
    g_logger.info("Cloning %s into %s/%s/%s",
                                        YOMPURL,
                                        fakeroot,
                                        installDirectory,
                                        repoDirectory)
    YOMP.clone(YOMPURL, directory=repoDirectory)
    workDirectory = "%s/%s/%s" % (fakeroot, installDirectory, repoDirectory)
    if sha:
      with changeToWorkingDir(workDirectory):
        g_logger.info("Checking out SHA %s in %s", sha, workDirectory)
        YOMP.checkout(sha)
        YOMP.resetHard()
    else:
      g_logger.info("No sha specified, using head of master")
    YOMPVersionData = loadGitDescribeFromDirectory(workDirectory)
    sourceFiles = os.listdir("%s/%s/%s" % (fakeroot,
                                           installDirectory,
                                           repoDirectory))
    for directoryEntry in sourceFiles:
      cleanseFakeroot(fakeroot,
                      installDirectory,
                      "%s/%s" % (repoDirectory, directoryEntry))
    cleanseFakeroot(fakeroot, installDirectory, repoDirectory)
  return YOMPVersionData


def prepFakerootFromDirectory(fakeroot,
                              sourceDirectory,
                              installDirectory,
                              baseDirectory):
  """
  Prepare a fakeroot from a directory by cloning a source directory to its
  top level.
  :param fakeroot: path to the directory to use as the root of the RPM's
    install tree
  :param sourceDirectory: Directory to copy from
  :param baseDirectory: Where to copy the files to create the fakeroot
  :param installDirectory: Where to create the baseDirectory
  :raises: infrastructure.utilities.exceptions.MissingDirectoryError
    if the given sourceDirectory is not found.
  """

  g_logger.info("Prepping fakeroot in %s from %s", fakeroot, sourceDirectory)
  installPath = commonFakerootPrep(fakeroot, installDirectory)
  with changeToWorkingDir(installPath):
    if not os.path.isdir(sourceDirectory):
      g_logger.error("%s is not a directory!", sourceDirectory)
      raise MissingDirectoryError("Directory not found!")
    targetDirectory = "%s/%s/%s" % (fakeroot, installDirectory, baseDirectory)
    os.makedirs(targetDirectory)
    # Find the top level files/dirs in the source directory and copy them to
    # the fakeroot
    sourceFiles = os.listdir(sourceDirectory)
    for eachFile in sourceFiles:
      g_logger.info("Copying %s to %s...", eachFile, targetDirectory)
      runWithOutput("rsync --exclude '.*.un~' -av %s/%s %s" % (sourceDirectory,
                                                               eachFile,
                                                               targetDirectory))
      cleanseFakeroot(fakeroot,
                      installDirectory,
                      "%s/%s" % (baseDirectory, eachFile))

def parseArgs():
  """
    Parse the command line arguments

    :return: Parsed arguments
    :rtype argparse.Namespace
  """
  parser = argparse.ArgumentParser(description="RPM Creator")
  parser.add_argument("--source-dir", action="store", dest="source_dir")
  parser.add_argument("--YOMP-url",
                      action="store",
                      dest="YOMPURL",
                      help="YOMP repository to package")
  parser.add_argument("--depends",
                      action="store",
                      dest="depends",
                      help="comma separated dependency list",
                      default=None)
  parser.add_argument("--package-name",
                      action="store",
                      dest="package_name",
                      help="rpm package name - don't include SHA or version")
  parser.add_argument("--repo-directory",
                      action="store",
                      dest="repo_directory",
                      help="name you want repo checked out as")
  parser.add_argument("--install-directory",
                      action="store",
                      dest="install_directory",
                      default='/opt',
                      help="where to install on target systems - default /opt")
  parser.add_argument("--sha", action="store", dest="sha", default=None)
  parser.add_argument("--base-version",
                      action="store",
                      dest="base_version",
                      default="0.1")
  parser.add_argument("--debug", action="store", dest="debug", default=0)
  parser.add_argument("--epoch", action="store", dest="epoch", default=0)
  parser.add_argument("--no-clean",
                      action="store",
                      dest="no_clean",
                      default=None)
  parser.add_argument("--arch", action="store", dest="arch", default=None)
  parser.add_argument("--desc",
                      action="store",
                      nargs='+',
                      dest="desc",
                      default=None)
  parser.add_argument("--directory-purge-list",
                      action="store",
                      dest="directory_purge_list",
                      default=None)
  parser.add_argument("--timestamp", action="store", dest="timestamp")
  parser.add_argument("--use-YOMP-tags", action="store", dest="useGitTag",
                      help="read version data from the repo's YOMP tags")
  parser.add_argument("--release", action="store", dest="release", default=0)
  parser.add_argument("--rpm-directory",
                      action="store",
                      dest="rpm_directory",
                      help="directory to put output rpm in")
  parser.add_argument("--workdir", action="store", dest="work_dir",
                      default="/opt/numenta/scratch",
                      help="The directory you want fpm to do its work in, where"
                           "'work' is any filecopying, downloading, etc."
                           "Roughly any scratch space fpm needs to build "
                           "your package.")
  parser.add_argument("--after-install", action="store",
                      dest="after_install", default=None,
                      help="post install script after rpm is installed")
  parser.add_argument("--log", dest="logLevel", type=str, default="debug",
                      help="Logging level")
  args = parser.parse_args()

  global g_logger
  # Intializing logger
  g_logger = log.initPipelineLogger("rpm-creator", logLevel=args.logLevel)

  if (not args.YOMPURL) and (not args.source_dir):
    parser.error("You must specify a repo to clone with --clone-source, or a"
                   "source directory with --source-directory")
  if not args.install_directory:
    parser.error("Specify a directory to install the repo into with"
                 "--install-directory, e.g. /opt")
  if not args.repo_directory:
    parser.error("Please specify a base directory with --repo-directory,"
                 "e.g. YOMP")
  if not args.package_name:
    parser.error("You must specify a package name with --package-name")
  if not args.base_version and not args.useGitTag:
    parser.error("Either specify a base version or --use-YOMP-tags to load"
                 "from the, repo YOMP tags")
  if args.YOMPURL and args.source_dir:
    parser.error("--clone-source and --source-dir are incompatible "
                 "with each other")
  if args.useGitTag and args.source_dir:
    parser.error("--use-YOMP-tags and --source-dir are incompatible "
                 "with each other")
  if args.timestamp:
    VERSION_TIMESTAMP = args.timestamp
  else:
    VERSION_TIMESTAMP = time.strftime("%Y%m%d.%H.%M.%S")

  return args


def main(args):

  scratchDirectory = tempfile.mkdtemp(prefix="rpm-creator", dir=args.work_dir)

  # Prepare a fakeroot directory
  if args.YOMPURL:
    versionData = prepFakerootFromGit(fakeroot=scratchDirectory,
                                      installDirectory=args.install_directory,
                                      repoDirectory=args.repo_directory,
                                      YOMPURL=args.YOMPURL,
                                      sha=args.sha)
  if args.source_dir:
    prepFakerootFromDirectory(fakeroot=scratchDirectory,
                              sourceDirectory=args.source_dir,
                              installDirectory=args.install_directory,
                              baseDirectory=args.repo_directory)


  if args.desc:
    rpmDescription = ' '.join(args.desc)
  else:
    if args.sha:
      rpmDescription = "Build SHA: %s" % (args.sha)
    else:
      rpmDescription = None
  if args.useGitTag and args.YOMPURL:
    if versionData:
      packageVersion = versionData["version"]
      packageRelease = versionData["commitsSinceTag"]
      if rpmDescription:
        packageDescription = "%s %s" % (rpmDescription, versionData["sha"])
      else:
        packageDescription = "%s %s" % (args.YOMPURL, versionData["sha"])
    else:
      packageDescription = "%s %s" % (args.YOMPURL, versionData["sha"])
  else:
    packageVersion = args.base_version
    packageRelease = args.release
    packageDescription = rpmDescription
  packagePath = packageDirectory(fakeroot=scratchDirectory,
                                 packageName=args.package_name,
                                 baseVersion=packageVersion,
                                 afterInstall=args.after_install,
                                 sha=args.sha,
                                 workDir=args.work_dir,
                                 depends=args.depends,
                                 arch=args.arch,
                                 description=packageDescription,
                                 epoch=args.epoch,
                                 release=packageRelease,
                                 directoriesOwned=args.directory_purge_list)
  g_logger.debug("packagePath: %s", packagePath)

  if args.rpm_directory:
    os.rename(packagePath, "%s/%s" % (args.rpm_directory, packagePath))

  if not args.no_clean:
    g_logger.debug("Removing fakeroot from %s", scratchDirectory)
    rmtree(scratchDirectory)
  else:
    g_logger.debug("Skipping scratch dir cleanup in %s", scratchDirectory)



if __name__ == "__main__":
  main(parseArgs())
