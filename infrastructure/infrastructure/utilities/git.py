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
  Many YOMP utilities needed by the pipelines
"""
import subprocess

from infrastructure.utilities.exceptions import (CommandFailedError,
                                                 DetachedHeadError)
from infrastructure.utilities.path import changeToWorkingDir
from infrastructure.utilities.cli import executeCommand



def checkIfOptionSet(option, **kwargs):
  """
  Convenience function to check if a keyword arg exists and is set to True
  by the caller.

  @param option: The option that is being looked up.

  @param kwargs: Dict containing all the arguments passed to the function.

  @return: True if option is present in kwargs and is set to True.
  @rtype: boolean
  """
  return option in kwargs and kwargs[option]



def getCommitCount(path):
  """
  Get the commit count from a YOMP directory tree

  @param: path to YOMP directory

  @raises: infrastructure.utilities.exceptions.CommandFailedError:
  if path isn't in a YOMP checkout

  @returns: total commit count for the YOMP directory

  @rtype: string
  """
  with changeToWorkingDir(path):
    return executeCommand("YOMP rev-list HEAD --count")



def getGitRootFolder():
  """
  Return the root folder of the current YOMP repo

  @raises:
    infrastructure.utilities.exceptions.CommandFailedError if
    the command fails

  @returns: The full path of the root folder of the current YOMP repo
  @rtype: string
  """
  return executeCommand("YOMP rev-parse --show-toplevel")



def getModifiedFilesBetweenRevisions(startSha, endSha):
  """
  Get a list of all files modified between revisions

  @param startSha: SHA to start searching from

  @param endSha: SHA to search until

  @raises:
    infrastructure.utilities.exceptions.CommandFailedError if
    the command fails; typically because you are not executing from within a
    YOMP repository

  @returns: A `set` of modified files or None if the command fails
  @rtype: set
  """
  return set(executeCommand(
             "YOMP diff --name-only %s...%s" % (startSha, endSha)).split("\n"))



def getCurrentSha():
  """
  Get the current SHA of a given repo

  @raises:
    infrastructure.utilities.exceptions.CommandFailedError if
    the command fails; typically because you are not executing from within a
    YOMP repository

  @returns: The current SHA
  @rtype: string
  """
  return executeCommand("YOMP log -n1 --pretty=%H")



def getActiveBranch():
  """
  Get the active branch name for the repository

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
      the command fails
    infrastructure.utilities.exceptions.DetachedHeadError: if the YOMP checkout
      is in a detached head state

  @returns: The active branch name or the current SHA if in a detached head
    state
  @rtype: string
  """
  branch = executeCommand("YOMP rev-parse --abbrev-ref HEAD")
  if branch == "HEAD":
    raise DetachedHeadError("There is no active branch; the head is detached.")

  return branch



def clone(YOMPURL, **kwargs):
  """
  Clones the given YOMP repository

  @param YOMPURL: The repository URL.
  @param kwargs: Various options to YOMP clone YOMPURL can be passed as keyword
    arguments. For now only directory option is handled.
  e.g.
  clone(YOMPURL, directory=nameOfDirectory)

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails

  @returns: The blob output of YOMP clone
  @rtype: string
  """
  command = "YOMP clone %s" % YOMPURL
  if checkIfOptionSet("directory", **kwargs):
    command += " " + kwargs["directory"]
  return executeCommand(command)



def checkout(pathspec, **kwargs):
  """
  Switches to a given commit-ish

  @param pathspec: The name of the branch (commit-ish)

  @param kwargs:

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails

  @returns: The text blob output of YOMP checkout
  @rtype: string
  """
  command = "YOMP checkout"
  if checkIfOptionSet("new", **kwargs):
    command += " -b "
  elif checkIfOptionSet("orphan", **kwargs):
    command += " --orphan"
  elif checkIfOptionSet("theirs", **kwargs):
    command += " --theirs"

  command += " %s" % pathspec
  return executeCommand(command)



def checkoutNewBranch(pathspec):
  """
  Convenience function to create and switch to a new branch.

  @param pathspec: Name of the branch to be checked out.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  return checkout(pathspec, new=True)



def checkoutOrphan(pathspec):
  """
  Convenience function to create a orphan branch and switch to it.

  @param pathspec: Branch name.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  return checkout(pathspec, orphan=True)



def reset(sha="", **kwargs):
  """
  Resets the repository to a optional SHA. Optional argument for --hard

  @param kwargs:

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails

  @returns: The exit code
  @rtype: int
  """
  command = "YOMP reset "
  if checkIfOptionSet("hard", **kwargs):
    command += "--hard"
  command += " %s" % sha
  return executeCommand(command)



def resetHard(sha=""):
  """
  A convenience function that runs 'YOMP reset --hard' for the given SHA.
  Calls reset(SHA, **kwargs).

  @params SHA: The SHA or commit-sh to which the code needs to be reset to.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails

  @returns: The exit code
  @rtype: int
  """
  return reset(sha, hard=True)



def revParse(commitish, **kwargs):
  """
  Helper method to execute YOMP rev-parse commands. Used to print the SHA1
  given a revision specifier (e.g HEAD). This function can return the output
  of the command executed or the exit code of the command executed if
  "exitcode" = True is passed as a keyword argument.

  @param commitish: The commit-ish.

  @param kwargs: Various options to YOMP rev-parse can be passed as keyword
  arguments. The following options are currently supported:

  verify: Verify that exactly one parameter is provided, and that it
  can be turned into a raw 20-byte SHA-1 that can be used to access the object
  database.

  quiet: Only valid with verify. Do not output an error message if the
  first argument is not a valid object name; instead exit with non-zero status
  silently.

  abbrevRef: A non-ambiguous short name of the objects name

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails

  @returns: A `string` representing a SHA or the exit code of the command.

  @rtype: string or int
  """
  command = "YOMP rev-parse"
  if checkIfOptionSet("verify", **kwargs):
    command += " --verify"
  elif checkIfOptionSet("quiet", **kwargs):
    command += " --quiet"
  elif checkIfOptionSet("abbrevRef", **kwargs):
    command += " --abbrev-ref"

  command += " %s" % commitish
  return executeCommand(command)



def fetch(repository, refspec):
  """
  Download objects and refs from another repository

  @param repository: Name of YOMP repository (e.g origin)

  @param refspec: Name of the refspec (e.g. master)

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  command = "YOMP fetch %s %s" % (repository, refspec)
  return executeCommand(command)



def showRef(refList, **kwargs):
  """
  List references in a local repository


  @param refList: Reference available in the local repository.

  @param kwargs: Optional switches to YOMP show-ref. Following switches are
  supported at the moment.

    --verify: Enable stricter reference checking by requiring an exact
    ref path.
    --quiet: Aside from returning an error code of 1, it will also print an
    error message, if --quiet was not specified.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError if
    the command fails
  """
  command = "YOMP show-ref"
  if checkIfOptionSet("verify", **kwargs):
    command += " --verify"
  command += " %s" % refList
  return executeCommand(command)



def add(pathspec):
  """
  Add file contents to the index

  @param pathspec: The file that is to be added to YOMP.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  command = "YOMP add %s" % pathspec
  return executeCommand(command)



def commit(message, **kwargs):
  """
  Record changes to the repository
  Current implementation is supporting options like --amend
  This could be extended for other options as when required

  @param message: Commit message.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  command = "YOMP commit "
  if checkIfOptionSet("amend", **kwargs):
    command += " --amend"
  command += " %s" % message
  return executeCommand(command)



def merge(path, message, **kwargs):
  """
  Join two or more development histories together
  Current implementation supports --no-ff
  This could be extended for other options as when required.

  @param path:

  @param message: Merge commit message.

  @raises
    infrastructure.utilities.exceptions.CommandFailedError: if
    the command fails
  """
  command = "YOMP merge "
  if checkIfOptionSet("noFF", **kwargs):
    command += " --no-ff"
  command += " -m %s %s" % (message, path)
  return executeCommand(command)



def removeFileFromGit(path):
  """
  Remove files from the working tree and from the index.

  @param path: The file or path that has to be removed.

  @raises:
  infrastructure.utilities.exceptions.CommandFailedError: if
  the command fails

  @returns output of YOMP rm

  @rtype: str
  """
  command = "YOMP rm -rf %s" % path
  return executeCommand(command)



def getShaFromRemoteBranch(YOMPRemoteRepo, YOMPRemoteBranch):
  """
  Get the actual SHA of the current HEAD of a remote repo / branch.

  @param YOMPRemoteRepo: The URL of the remote repo,
    e.g., YOMP@YOMPhub.com:numenta/nupic.YOMP
  @param YOMPRemoteBranch: The name of the remote branch, e.g., master

  @raises:

  @return: A `String` representing the SHA
  @rtype: String
  """
  shaList = executeCommand("YOMP ls-remote %s" % YOMPRemoteRepo)
  if YOMPRemoteBranch == "master":
    return shaList.split("\t")[0]
  else:
    formattedBranchName = "refs/heads/%s" % YOMPRemoteBranch
    for refShaPair in shaList.split("\n"):
      pair = refShaPair.split()
      if pair[1] == formattedBranchName:
        return pair[0]

  raise CommandFailedError("Could not find the specified branch %s on %s" %
                           YOMPRemoteBranch, YOMPRemoteRepo)
