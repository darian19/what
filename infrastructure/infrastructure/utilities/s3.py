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
  Helper methods for working with S3
"""
import boto
import json
import os
import sys

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from infrastructure.utilities.exceptions import InvalidParametersError
from infrastructure.utilities.path import changeToWorkingDir

# We only want to apply this patch if we're running on Python 2.7.9 or later.
if sys.version_info >= (2,7,9):
  import ssl

  # If your bucket name has a dot in it (like all our infrastructure ones do),
  # trying to read a key from it raises an ssl certficate error on 2.7.9
  # and later.
  #
  # ssl.CertificateError: hostname 'builds.numenta.com.s3.amazonaws.com' doesn't
  #   match either of '*.s3.amazonaws.com', 's3.amazonaws.com'
  #
  # See: https://YOMPhub.com/boto/boto/issues/2836
  #      https://docs.aws.amazon.com/AmazonS3/latest/dev/VirtualHosting.html
  #
  # Fortunately @oberstet commented on 2836 with a patch to ssl certificate
  # handling to cope with this.

  _old_match_hostname = ssl.match_hostname

  def _new_match_hostname(cert, hostname):
    if hostname.endswith(".s3.amazonaws.com"):
      pos = hostname.find(".s3.amazonaws.com")
      hostname = hostname[:pos].replace(".", "") + hostname[pos:]
    return _old_match_hostname(cert, hostname)

  ssl.match_hostname = _new_match_hostname


def readS3Contents(bucket, path, connection, logger):
  """
  Read an arbitrary S3 object and return the contents.

  :param bucket: Name of S3 bucket to read from. Required.

  :param path: path in S3. Required.

  :param connection: a boto connection object. Required.

  :returns: data for the s3 object pointed to by path

  :rtype data:
  """
  if not bucket:
    raise InvalidParametersError("No bucket object specified.")
  if not connection:
    raise InvalidParametersError("No boto connection argument")
  if not logger:
    raise InvalidParametersError("No logger specified")
  if not path:
    raise InvalidParametersError("No path specified")

  logger.debug("Connecting to S3 bucket %s", bucket)
  bucket = connection.get_bucket(bucket, validate=False)

  key = boto.s3.key.Key(bucket)
  key.key = path
  key.open()

  logger.debug("Reading %s/%s", bucket, path)
  s3value = key.read()
  logger.debug("value: %s", s3value)
  return s3value


def getS3Connection():
  """
    :returns: An S3Connection
  """
  # TODO: TAUR-215 - Add retry decorator
  return S3Connection(os.environ["AWS_ACCESS_KEY_ID"],
                      os.environ["AWS_SECRET_ACCESS_KEY"])


def downloadFileFromS3(bucketName, path, logger):
  """
  This method with downloads a file from S3

    :param bucketName : Name of the bucket where file is loacted
    :param path : The path to the file excluding the bucket name.
    for eg: s3://{bucketName}/{path}
    :param logger: An initialized logger from the calling pipeline.

    :returns : local path of the downloaded file
  """
  try:
    conn = getS3Connection()
    bucket = conn.get_bucket(bucketName)
    key = bucket.get_key(path)
    fileName = os.path.basename(path)
    with open(fileName, "w") as fp:
      key.get_file(fp)
    return os.path.join(os.getcwd(), fileName)
  except:
    if logger:
      logger.exception("Failed to download file from S3")
    raise


def getMappingsFromShaToRpm(repo, sha, s3MappingBucket, logger):
  """
    Connects to specified s3MappingBucket, reads SHA to RPM mapping json file.
    Returns RPM name for given repository and SHA combination.

    :param repo: Repository for which SHA to RPM mapping is expected
    :param sha: SHA for which RPM mapping is expected
    :param s3MappingBucket: Base name for S3 bucket
    :param logger: An initialized logger from the calling pipeline.

    :returns RPM name for given repository and SHA combination.
  """
  logger.debug("Repo %s : " % repo)
  logger.debug("SHA  %s : " % sha)
  try:
    conn = getS3Connection()

    rpmKey = conn.get_bucket(s3MappingBucket).get_key(
      "rpm_sha_mappings/%s/%s.json" % (repo, sha))
    logger.info("rpmKey : %s" % rpmKey)
    if rpmKey:
      mappingDetails = json.loads(rpmKey.get_contents_as_string())
      if mappingDetails["sha"] == sha:
        rpmName = mappingDetails["rpm"]
        return rpmName
      else:
        logger.info("sha details mismatch")
    else:
      logger.info("Failed to map sha to rpm details file")
  except:
    logger.exception("Failed to map SHA to RPM details file")
    raise


def getLastStableAmi(s3MappingBucket, logger):
  """
    :param s3MappingBucket: The name of the S3 bucket to search for the latest
      stable AMI.
    :param logger: An initialized logger from the calling pipeline.

    :returns: A string with the AMI ID of the last stable AMI from the given
      bucket or "" (empty string) if one wasn't found.
  """
  # TODO: TAUR-215 - Add retry decorator
  conn = getS3Connection()
  amiId = ""
  amiIdKey = conn.get_bucket(s3MappingBucket).get_key("stable_ami/ami.txt")
  if amiIdKey:
    amiId = amiIdKey.get_contents_as_string().split(":")[1].strip()
    logger.debug("Found AMI ID: %s", amiId)
  return amiId


def checkIfNuPICCoreInS3(config, nupicCoreSHA):
  """
    :param config: a dict containing values as follows:
      {
        "S3_MAPPING_BUCKET": "value"
      }
    :param nupicCoreSHA: A `String` representing a NuPIC Core SHA

    :returns: True if the NuPIC Core sha is found in S3, else False
    :rtype: bool
  """
  key = "builds_nupic_core/nupic.core-%s.zip" % nupicCoreSHA
  conn = getS3Connection()
  return conn.get_bucket(config["S3_MAPPING_BUCKET"],
                         validate=False).get_key(key)


def uploadToS3(config, filePath, s3Folder, logger):
  """
    Uploads artifacts to S3.

    :param config: A dict containing values as follows:
      {
        "S3_MAPPING_BUCKET": "value"
      }
    :param filePath: The full path of the file to upload
    :param s3Folder: The S3 folder where the file is to be uploaded.
    :param logger: a valid Numenta logger
  """
  try:
    bucket = getS3Connection().get_bucket(config["S3_MAPPING_BUCKET"])
    k = Key(bucket)
    fileName = os.path.basename(filePath)
    k.key = "/%s/%s" % (s3Folder, fileName)
    k.set_contents_from_filename("%s" %filePath)
  except:
    logger.exception("Caught an exception while uploading file to S3")
    raise


def downloadNuPICWheel(sha=None, downloadDirectory="/tmp", logger=None):
  """
    Downloads a NuPIC wheel from S3 for a given SHA.

    If no NuPIC SHA is provided then the wheel version is read from
    "stable_nupic_version/nupic-package-version.txt" and if a SHA is
    provided then the wheel version is read from "stable_nupic_version/<SHA>".

    :param downloadDirectory: The directory to download the wheel into
    :raises InvalidParametersError: If no NuPIC wheel exists for the given SHA
    :returns: The absolute path to the NuPIC wheel.
    :rtype: string
  """
  if sha:
    path = "stable_nupic_version/%s" % sha
  else:
    path = "stable_nupic_version/nupic-package-version.txt"
  bucketName = "builds.numenta.com"

  try:
    with open(downloadFileFromS3(bucketName, path, logger), "r") as fHandle:
      contents = fHandle.readline().strip()
      nupicSHA = contents.split(":")[0].strip()
      wheelFile = contents.split(":")[1].strip()
  except AttributeError:
    if logger:
      g_logger.debug("NuPIC wheel for %s not found in S3", nupicSha)
    raise InvalidParametersError("NuPIC wheel for %s not found" % nupicSha)
  else:
    if logger:
      g_logger.debug("Downloading NuPIC wheel from S3: %s" % wheelFile)
    with changeToWorkingDir(downloadDirectory):
      wheelFilePath = downloadFileFromS3(bucketName = bucketName,
                                         path = "builds_nupic_wheel/%s" % wheelFile,
                                         logger=logger)

  return wheelFilePath
