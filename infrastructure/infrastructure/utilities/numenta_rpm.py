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

from distutils.dir_util import copy_tree, mkpath
from tempfile import mkdtemp

from infrastructure.utilities import YOMP
from infrastructure.utilities import logger as log
from infrastructure.utilities import rpm
from infrastructure.utilities.cli import runWithOutput
from infrastructure.utilities.exceptions import InvalidParametersError
from infrastructure.utilities.path import (
  changeToWorkingDir,
  purgeDirectory,
  rmrf)


class NumentaRPM(object):
  """
  Class for creating Numenta RPMs.
  """


  def __init__(self, config):
    # convert dict to object
    if isinstance(config, dict):
      tmpConfig = type('Config', (), {})()
      for k, v in config.items():
        setattr(tmpConfig, k, v)
      config = tmpConfig
    failmsg = None
    if config.sitePackagesTarball:
      if config.flavor != "YOMP":
        failmsg = "--site-packages is only used for YOMP packages."
    if config.flavor == None:
      failmsg = "You must set a type of rpm to create with --rpm-flavor"
    if config.artifacts == []:
      failmsg = "You must specify artifacts in the fakeroot to package."
      if config.flavor == "YOMP":
        failmsg = failmsg + " YOMP rpms should specify opt"
      if config.flavor == "infrastructure":
        failmsg = failmsg + " Infrastructure rpms should specify opt"
      if config.flavor == "saltcellar":
        failmsg = failmsg + " Saltcellar rpms should specify srv"
    if failmsg:
      raise InvalidParametersError(failmsg)
    self.config = config
    self.environment = dict(os.environ)
    self.fakeroot = None
    self.logger = log.initPipelineLogger(name="create-numenta-rpm",
                                         logLevel=config.logLevel)
    self.productsDirectory = None


  def cleanupDirectories(self):
    """
    Nuke any temp files unless preserveFakeroot is set in the configuration.
    """

    config = self.config
    logger = self.logger
    fakeroot = self.fakeroot

    if not config.preserveFakeroot:
      if logger:
        logger.debug("Scrubbing fakeroot in %s", fakeroot)
      rmrf(fakeroot, logger=logger)
    else:
      if logger:
        logger.debug("Skipping fakeroot scrub, leaving %s intact.", fakeroot)


  def sanitizeSrvSalt(self, saltpath):
    """
    Ensure only whitelisted files & directories are installed to /srv/salt by
    the RPM.

    Numenta convention is to only include explicitly whitelisted formulas
    and files in RPMs deployed to customer machines.

    We add a PUBLIC file at the top level of a formula's directory tree
    to add it to the whitelist.

    This prevents us from accidentally publishing internal-only files to
    customer machines.

    :param saltpath: Path to /srv/salt in the fakeroot
    """

    logger = self.logger
    fileWhitelist = ["bootstrap.sh",
                     "top.sls"
                    ]

    logger.debug("Sanitizing %s", saltpath)
    for artifact in os.listdir(saltpath):
      artifactPath = "%s/%s" % (saltpath, artifact)
      if os.path.isfile(artifactPath):
        if artifact not in fileWhitelist:
          logger.debug("Purging %s", artifact)
          rmrf(artifactPath)
      if os.path.isdir(artifactPath):
        # Formula directories have to be explicitly whitelisted by having
        # a PUBLIC file or they will be purged from the salt tree.
        if not os.path.isfile("%s/PUBLIC" % artifactPath):
          logger.debug("Purging %s", artifact)
          rmrf(artifactPath)
        else:
          logger.info("packaging formula %s", artifact)

    # AWS requires that we don't include keys in marketplace AMIs.
    # Purge any pubkeys in the salt tree
    # Note that we _don't_ quote the wildcard here so that check_call
    # passes it to find correctly when it is called by runWithOutput.
    # Same for the {} and ;
    findPubkeys = """find %s -name *.pub -exec rm -fv {} ;""" % saltpath
    logger.debug("**************************************************")
    logger.debug("Sanitizing %s with %s", saltpath, findPubkeys)
    runWithOutput(findPubkeys, logger=logger)

    # Purge pemfiles
    findPemFiles = """find %s -name *.pem -exec rm -fv {} ;""" % saltpath
    logger.debug("**************************************************")
    logger.debug("Sanitizing %s with %s", saltpath, findPubkeys)
    runWithOutput(findPemFiles, logger=logger)


  def constructFakeroot(self):
    """
    Construct a fakeroot.

    :returns: (iteration, fakerootSHA) where iteration is the total commit count
    in the repository and fakerootSHA is the SHA in the fakeroot. If we're
    packaging a branch or tip of master, we're still going to want to know what
    the SHA was so we can include it in the RPM description.

    :rtype: tuple
    """

    flavor = self.config.flavor
    config = self.config
    logger = self.logger

    logger.debug("RPM flavor: %s", config.flavor)

    if flavor == "YOMP":
      return self.constructYOMPFakeroot()

    if flavor == "infrastructure":
      return self.constructInfrastructureFakeroot()

    if flavor == "saltcellar":
      return self.constructSaltcellarFakeroot()

    if flavor == "prebuiltYOMP":
      return self.constructPreBuiltYOMPFakeroot()


  def constructPreBuiltYOMPFakeroot(self):
    """
    Construct fakeroot from prebuilt YOMP

    :returns: SHA of the products repo in the fakeroot
    :rtype: tuple
    """

    config = self.config
    logger = self.logger
    productsDirectory = self.productsDirectory
    logger.debug("Creating %s", productsDirectory)
    mkpath(productsDirectory)
    copy_tree(config.productsDir, productsDirectory)
    iteration = YOMP.getCommitCount(productsDirectory)

    with changeToWorkingDir(productsDirectory):
      actualSHA = YOMP.getCurrentSha()

    # Set extra python path
    self.setPythonPath()

    # Clean YOMP Scripts
    self.cleanScripts()

    # Purge anything not whitelisted
    self.purgeBlacklistedStuff()

    return (iteration, actualSHA)


  def constructSaltcellarFakeroot(self):
    """
    Make a saltcellar fakeroot

    :returns: (iteration, fakerootSHA) where iteration is the total commit count
    in the repository and fakerootSHA is the SHA in the fakeroot. If we're
    packaging a branch or tip of master, we're still going to want to know what
    the SHA was so we can include it in the RPM description.

    :rtype: tuple
    """

    config = self.config
    fakeroot = self.fakeroot
    logger = self.logger
    srvPath = os.path.join(fakeroot, "srv")
    logger.debug("Creating saltcellar fakeroot in %s", srvPath)
    productsPath = os.path.join(fakeroot, "products")
    mkpath(srvPath)

    logger.debug("Cloning...")

    # Collect the SHA from the fakeroot. This way we can put the SHA into
    # the RPM information even if we are packaging tip of a branch and not
    # a specific SHA
    fakerootSHA = rpm.YOMPCloneIntoFakeroot(fakeroot=fakeroot,
                                           installDirectory="/",
                                           repoDirectory="products",
                                           YOMPURL=config.YOMPURL,
                                           logger=logger,
                                           sha=config.sha)

    # Capture the commit count since we're going to trash products once we pull
    # out the saltcellar
    iteration = YOMP.getCommitCount(productsPath)
    logger.debug("Commit count in %s is %s", productsPath, iteration)

    # Move the saltcellar to /srv/salt
    logger.debug("Moving saltcellar to %s/salt", srvPath)
    logger.debug("srvPath: %s", srvPath)
    logger.debug("productsPath: %s", productsPath)
    logger.debug("%s/infrastructure/saltcellar", productsPath)

    logger.debug("Checking for %s/infrastructure/saltcellar",
                   productsPath)
    logger.debug(os.path.exists("%s/infrastructure/saltcellar" %
                                  productsPath))

    os.rename(os.path.join(productsPath, "infrastructure",
                           "saltcellar"),
              os.path.join(srvPath, "salt"))

    # Now that we have the salt formulas, nuke the rest of products out of
    # the fakeroot
    logger.debug("Deleting products from fakeroot")
    rmrf(productsPath)

    # Finally, scrub the private data out of /srv/salt
    if not config.numenta_internal_only:
      logger.debug("Sanitizing /srv/salt")
      self.sanitizeSrvSalt("%s/srv/salt" % fakeroot)
    else:
      logger.critical("Baking numenta-internal rpm, not sanitizing /srv/salt")
    return (iteration, fakerootSHA)


  def constructInfrastructureFakeroot(self):
    """
    Construct our fakeroot directory tree

    :returns: (iteration, fakerootSHA) where iteration is the total commit count
    in the repository and fakerootSHA is the SHA in the fakeroot. If we're
    packaging a branch or tip of master, we're still going to want to know what
    the SHA was so we can include it in the RPM description.

    :rtype: tuple
    """

    config = self.config
    fakeroot = self.fakeroot
    logger = self.logger
    productsDirectory = self.productsDirectory
    srvPath = os.path.join(fakeroot, "opt", "numenta")
    logger.debug("Creating %s", srvPath)
    mkpath(srvPath)

    logger.debug("Cloning %s into %s...", fakeroot, config.YOMPURL)

    # Collect the SHA from the fakeroot. This way we can put the SHA into
    # the RPM information even if we are packaging tip of a branch and not
    # a specific SHA
    installDirectory = os.path.join("opt", "numenta")
    fakerootSHA = rpm.YOMPCloneIntoFakeroot(fakeroot=fakeroot,
                                           installDirectory=installDirectory,
                                           repoDirectory="products",
                                           YOMPURL=config.YOMPURL,
                                           logger=logger,
                                           sha=config.sha)

    # Capture the commit count since we're going to trash products once we pull
    # out the saltcellar
    iteration = YOMP.getCommitCount(productsDirectory)
    logger.debug("Commit count in %s is %s", productsDirectory, iteration)
    logger.debug("SHA in %s is %s", productsDirectory, fakerootSHA)

    # Clean everything not whitelisted out of products so we don't conflict
    # with YOMP or taurus rpms
    purgeDirectory(path=productsDirectory,
                   whitelist=["__init__.py",
                              "infrastructure" ],
                   logger=logger)

    # Clean out infrastructure, too - we only want the utilities
    infraPath = os.path.join(productsDirectory, "infrastructure")
    purgeDirectory(path=infraPath,
                   whitelist=["__init__.py",
                              "DEPENDENCIES.md",
                              "infrastructure",
                              "LICENSE",
                              "README.md",
                              "requirements.txt",
                              "setup.py"],
                   logger=logger)

    return (iteration, fakerootSHA)


  def constructYOMPFakeroot(self):
    """
    Construct a YOMP fakeroot directory tree.

    1. Add any directories specified with --extend-pythonpath to the PYTHONPATH
       we will be using for setup.py, build scripts and the cleanup scripts.

    2. Install any wheels that have been specied by --use-wheel

    3. Run setup.py in any directories that have been specified with
       --setup-py-dir. Uses the arguments specfied by --setup-py-arguments.

    4. Run any build scripts specified by --build-script

    5. Run any cleanup scripts specified by --cleanup-script

    6. Purge any files or directories at the top level of the checkout that were
       not whitelisted with --whitelist.

    :returns: (iteration, actualSHA) where iteration is the total commit count
    in the repository and fakerootSHA is the SHA in the fakeroot. If we're
    packaging a branch or tip of master, we're still going to want to know what
    the SHA was so we can include it in the RPM description.

    :rtype: tuple
    """

    config = self.config
    fakeroot = self.fakeroot
    logger = self.logger

    logger.info("Preparing YOMP fakeroot in %s\n", fakeroot)

    actualSHA = self.installProductsIntoYOMPFakeroot()

    productsDirectory = self.productsDirectory
    YOMPPath = os.path.join(productsDirectory, "YOMP")
    iteration = YOMP.getCommitCount(productsDirectory)

    # Extend PYTHONPATH for setup.py, build & cleanup scripts
    # pythonpathExtensions
    logger.debug("**************************************************")
    logger.info("Phase 1: Preparing PYTHONPATH and installing wheels")
    # Set extra python path
    self.setPythonPath()
    environment = self.environment
    sitePackagesDirectory = "%s/YOMP/lib/python2.7/site-packages" % \
                            productsDirectory

    # Install wheels if any have been specified
    with changeToWorkingDir(YOMPPath):
      for wheel in config.wheels:
        logger.info("Installing %s", os.path.basename(wheel))
        if not os.path.exists(wheel):
          raise InvalidParametersError("%s does not exist!" % wheel)
        pipCommand = "pip install %s --no-deps --target=%s" % \
          (wheel, sitePackagesDirectory)
        logger.debug("pip command: %s", pipCommand)
        runWithOutput(pipCommand)
        logger.debug("wheel install complete")

    # Run setup.py if specified
    logger.info("Phase 2: Running setup.py commands")

    for pyDir in config.setupPyDirs:
      pyDirPath = "%s/%s" % (productsDirectory, pyDir)
      logger.debug("Changing to %s", pyDirPath)
      with changeToWorkingDir(pyDirPath):
        setupCommand = "python setup.py develop --prefix=%s/YOMP" % \
                       productsDirectory
        logger.debug("Running %s", setupCommand)
        runWithOutput(setupCommand, env=environment)

    # Run any build scripts. We assume that they should be run in the
    # directory they're in.
    logger.info("Phase 3: Running build scripts...")
    for builder in config.buildScripts:
      builderPath = "%s/%s" % (fakeroot, builder)
      logger.debug("Attempting to run %s", builderPath)
      if not os.path.exists(builderPath):
        raise InvalidParametersError("%s does not exist!" % builderPath)
      workDirectory = os.path.dirname(builderPath)
      logger.debug("Changing to %s", workDirectory)
      with changeToWorkingDir(workDirectory):
        runWithOutput(builderPath, env=environment)

    # Run any cleanup scripts. We assume that they should be run in the
    # directory they're in.
    logger.info("Phase 4: Running cleanup scripts...")
    # Clean Scripts
    self.cleanScripts()

    logger.info("Phase 5: Purge anything not whitelisted.")
    # Purge anything not whitelisted
    self.purgeBlacklistedStuff()

    return (iteration, actualSHA)


  def purgeBlacklistedStuff(self):
    """
    Purges anything not whitelisted.
    """

    config = self.config
    logger = self.logger
    productsDirectory = self.productsDirectory
    logger.info("Purge anything not whitelisted.")
    for thing in os.listdir(productsDirectory):
      if thing not in config.whitelisted:
        rmrf("%s/%s" % (productsDirectory, thing))


  def cleanScripts(self):
    """
    Cleans the YOMP directory before packaging.
    """

    productsDirectory = self.productsDirectory
    config = self.config
    environment = self.environment
    logger = self.logger

    logger.info("Running cleanup scripts...")
    for cleaner in config.cleanupScripts:
      cleanerPath = os.path.join(productsDirectory, cleaner)
      workDirectory = os.path.dirname(cleanerPath)
      logger.debug("Changing to %s", workDirectory)
      logger.debug("Attempting to run %s", cleanerPath)
      if not os.path.exists(cleanerPath):
        raise InvalidParametersError("%s does not exist!" % cleanerPath)
      with changeToWorkingDir(workDirectory):
        runWithOutput("%s %s" % (cleanerPath, "--destroy-all-my-work"),
                      env=environment)


  def setPythonPath(self):
    """
    Set any extra pythonpath.
    """

    config = self.config
    fakeroot = self.fakeroot
    environment = self.environment
    logger = self.logger

    pythonpath = ""
    logger.debug("Previous: %s", pythonpath)
    for extraPythonpath in config.pythonpathExtensions:
      pythonpath = "%s:%s/opt/numenta/products/%s" % (environment["PYTHONPATH"],
                                                      fakeroot,
                                                      extraPythonpath)
      logger.debug("Setting PYTHONPATH to %s", pythonpath)
    self.environment["PYTHONPATH"] = pythonpath
    logger.debug("New PYTHONPATH: %s", pythonpath)


  def installProductsIntoYOMPFakeroot(self):
    """
    Clone our YOMP repo into the fakeroot directory tree.

    If we're configured to use a site-packages tarball; burst it.

    :returns: SHA of the products repo in the fakeroot
    """

    config = self.config
    fakeroot = self.fakeroot
    logger = self.logger
    numentaPath = os.path.join(fakeroot, "opt", "numenta")
    logger.debug("Creating %s", numentaPath)
    mkpath(numentaPath)

    logger.debug("Cloning...")
    realSHA = rpm.YOMPCloneIntoFakeroot(fakeroot=fakeroot,
                                       installDirectory="opt/numenta",
                                       repoDirectory="products",
                                       YOMPURL=config.YOMPURL,
                                       logger=logger,
                                       sha=config.sha)

    logger.debug("Creating site-packages if required")
    libPython = os.path.join(fakeroot,
                             "opt",
                             "numenta",
                             "products",
                             "YOMP",
                             "lib",
                             "python2.7")

    mkpath(os.path.join(libPython, "site-packages"))

    # Burst site-packages tarball if set on command line
    if config.sitePackagesTarball:
      with changeToWorkingDir(libPython):
        logger.debug("Bursting %s in %s",
                       config.sitePackagesTarball,
                       libPython)
        runWithOutput("tar xf %s" % config.sitePackagesTarball)

    return realSHA


  def create(self):
    config = self.config
    fakeroot = mkdtemp(prefix=config.tempdir)
    self.fakeroot = fakeroot
    logger = self.logger
    self.productsDirectory = os.path.join(fakeroot, "opt", "numenta", "products")
    logger.debug("Creating fakeroot in %s", fakeroot)
    (iteration, fakerootSHA) = self.constructFakeroot()

    # Add YOMP URL & SHA to description
    rpmDescription = "%s\nGit origin: %s\nRequested commitish: %s\nSHA %s" % \
                     (config.description,
                      config.YOMPURL,
                      config.sha,
                      fakerootSHA)

    # Force architecture to x86_64 for YOMP rpms if an arch hasn't been set
    if config.flavor == "YOMP":
      architecture = "x86_64"

    architecture = config.architecture

    # Bake the RPM
    rpm.bakeRPM(fakeroot=fakeroot,
                rpmName=config.rpmName,
                baseVersion=config.baseVersion,
                architecture=architecture,
                artifacts=config.artifacts,
                iteration=iteration,
                epoch=config.epoch,
                logger=logger,
                debug=config.debug,
                description=rpmDescription,
                postInstall=config.postinstallScript)

    # Zap our fakeroot
    self.cleanupDirectories()

