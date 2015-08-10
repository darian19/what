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
HTTP API endpoint for sending logs from a mobile client. The logs are re-logged
on the server. This way all logs reside in the same location and can be stored
or processed in the same way.

Each handler should use a unique prefix tag to make log processing easier.
"""

# pylint: disable=C0103

import csv
import datetime
import json
import os
import shutil
import tarfile
import tempfile
import uuid

import boto
import web

import YOMP
import YOMP.app
from YOMP.app import config, repository
from htmengine import utils
from YOMP.app.repository import schema
from YOMP.app.aws import s3_utils
from YOMP import YOMP_logging

from nta.utils.file_lock import ExclusiveFileLock



# Path format for writing Android logs.
_LOG_FORMAT_ANDROID = os.path.join(os.path.dirname(YOMP.__file__), "..",
                                   "logs", "android.log")
_LOGGER = YOMP_logging.getExtendedLogger(__name__)

_AWS_ACCESS_KEY = config.get("aws", "aws_access_key_id")
_AWS_SECRET_KEY = config.get("aws", "aws_secret_access_key")
_BUCKET = "YOMP.logs"
_MACHINE_ID = uuid.getnode()
_KEY_PREFIX = "metric_dumps/%s-" % _MACHINE_ID
_UPLOAD_ATTEMPTS = 3

urls = (
  # /_logging/android
  "/android", "AndroidHandler",
  # /_logging/feedback
  "/feedback", "FeedbackHandler",
)



class AndroidHandler(object):


  @staticmethod
  def POST():
    """
      Submit Android logs to the server (POST handler for /_logging/android)

      ::

          POST /_logging/android

          [
            {
              "timestamp":"1393310538",
              "deviceID":"DEVICE_ID=6cdb56113bc772e9",
              "eventType":"INFO",
              "message":"APP_VERSION=1.1.1-dev OS_VERSION=4.3 SDK_VERSION=18
                OS_BUILD=JSS15J DEVICE=Android SDK built for
                x86-unknown(generic_x86) SERIAL=unknown Service started",
              "tag":"YOMPService"
            },
            {
              "timestamp":"1393310539",
              "deviceID":"DEVICE_ID=6cdb56113bc772e9",
              "eventType":"INFO",
              "message":"APP_VERSION=1.1.1-dev OS_VERSION=4.3 SDK_VERSION=18
                OS_BUILD=JSS15J DEVICE=Android SDK built for
                x86-unknown(generic_x86) SERIAL=unknown Service started",
              "tag":"YOMPService"
            },
            ...
          ]

      Returns 200 message when successful
    """
    data = web.data()
    try:
      logs = utils.jsonDecode(data)
    except ValueError:
      # failed to parse JSON for some reason
      raise web.badrequest("Invalid JSON sent to logger")

    if not logs:
      return
    # Write separate log files for each device.
    deviceID = logs[0]["deviceID"]
    with open(_LOG_FORMAT_ANDROID, "a") as logFile:
      # Lock the file to avoid write conflicts.
      with ExclusiveFileLock(logFile):
        for line in logs:
          timestamp = datetime.datetime.fromtimestamp(
            int(line["timestamp"])).isoformat()
          logFile.write("%s [%s] [%s] MOBILE.ANDROID.%s %s\n" %
            (timestamp, line["eventType"], line["tag"], deviceID,
              line["message"]))



class FeedbackHandler(object):


  @classmethod
  def POST(cls):
    """Upload the metric info and metric data as a compressed tarfile to S3.

    The request must include the uid of the metric and may include other JSON
    keys as well. For instance, it is likely that a request from the mobile
    application will include information about the current view and data
    being displayed when the feedback request is sent. Any fields in addition
    to uid will be stored with the feedback archive file that is uploaded to
    S3.
    """
    inputData = json.loads(web.data())
    # Get the metric uid
    uid = inputData["uid"]
    del inputData["uid"]

    inputData["server_id"] = _MACHINE_ID

    # Data is written to a temporary directory before uploading
    path = tempfile.mkdtemp()

    try:
      # Retrieve the metric table record and add it to the other input
      # parameters
      metricFields = [schema.metric.c.uid,
                      schema.metric.c.datasource,
                      schema.metric.c.name,
                      schema.metric.c.description,
                      schema.metric.c.server,
                      schema.metric.c.location,
                      schema.metric.c.parameters,
                      schema.metric.c.status,
                      schema.metric.c.message,
                      schema.metric.c.last_timestamp,
                      schema.metric.c.poll_interval,
                      schema.metric.c.tag_name,
                      schema.metric.c.last_rowid]

      with repository.engineFactory().connect() as conn:
        metricRow = repository.getMetric(conn,
                                         uid,
                                         metricFields)
      metric = dict([(col.name, utils.jsonDecode(getattr(metricRow, col.name))
                      if col.name == "parameters"
                      else getattr(metricRow, col.name))
                      for col in metricFields])
      if metric["tag_name"]:
        metric["display_name"] = "%s (%s)" % (metric["tag_name"],
                                               metric["server"])
      else:
        metric["display_name"] = metric["server"]

      inputData["metric"] = utils.jsonEncode(metric)

      metricPath = os.path.join(path, "metric.json")
      with open(metricPath, "w") as f:
        json.dump(inputData, f)

      # Retrieve the metric data
      with repository.engineFactory().connect() as conn:
        metricDataRows = repository.getMetricData(conn, uid)
      metricData = [dict([(col.name, getattr(metricData, col.name))
                          for col in schema.metric_data.columns])
                    for metricData in metricDataRows]

      metricDataPath = os.path.join(path, "metric_data.csv")
      with open(metricDataPath, "w") as f:
        writer = csv.writer(f)
        if len(metricData) > 0:
          header = metricData[0].keys()
          # Write the field names first
          writer.writerow(header)
          # Then write out the data for each row
          for dataDict in metricData:
            row = [dataDict[h] for h in header]
            writer.writerow(row)

      # Create a tarfile to upload
      ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
      filename = "metric_dump_%s_%s.tar.gz" % (uid, ts)
      tfPath = os.path.join(path, filename)
      with tarfile.open(tfPath, "w:gz") as tf:
        tf.add(metricPath, arcname=os.path.basename(metricPath))
        tf.add(metricDataPath, arcname=os.path.basename(metricDataPath))

      # Upload the tarfile
      return cls._uploadTarfile(filename, tfPath)

    finally:
      shutil.rmtree(path)


  @staticmethod
  @s3_utils.retryOnBotoS3TransientError()
  def _uploadTarfile(filename, tarfilePath):
    conn = boto.connect_s3(_AWS_ACCESS_KEY, _AWS_SECRET_KEY)
    bucket = conn.get_bucket(_BUCKET, validate=False)
    key = bucket.new_key(_KEY_PREFIX + filename)
    _LOGGER.info("Attempting upload to %s", key.key)
    key.set_contents_from_filename(tarfilePath)
    return key.name



app = web.application(urls, globals())
