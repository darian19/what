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
import datetime
import json
import math
import msgpack
import time
import uuid
import validictory
from functools import partial



class Singleton(object):
  """Creates a Singleton object for the class."""
  @classmethod
  def instance(cls, *args, **kwgs):
    if not hasattr(cls, "_instance"):
      cls._instance = cls(*args, **kwgs)
    return cls._instance



def createGuid():
  """Get a new globally unique identifier."""
  return uuid.uuid4().hex



def _jsonDecodeListUTF8(data):
  """
  object_hook for json decoder used to decode unicode strings as UTF8 strings
  """
  rv = []
  for item in data:
    if isinstance(item, unicode):
      item = item.encode('utf-8')
    elif isinstance(item, list):
      item = _jsonDecodeListUTF8(item)
    elif isinstance(item, dict):
      item = _jsonDecodeDictUTF8(item)
    rv.append(item)
  return rv



def _jsonDecodeDictUTF8(data):
  """
  object_hook for json decoder used to decode unicode strings as UTF8 strings
  """
  rv = {}
  for key, value in data.iteritems():
    if isinstance(key, unicode):
      key = key.encode('utf-8')
    if isinstance(value, unicode):
      value = value.encode('utf-8')
    elif isinstance(value, list):
      value = _jsonDecodeListUTF8(value)
    elif isinstance(value, dict):
      value = _jsonDecodeDictUTF8(value)
    rv[key] = value
  return rv



class _JSONEncoder(json.JSONEncoder):
  def default(self, o):  # pylint: disable=E0202
    # Try converting iterables into list
    try:
      iterable = iter(o)
    except TypeError:
      pass
    else:
      return list(iterable)
    if isinstance(o, datetime.datetime):
      return str(o)
    if hasattr(o, "_jsonEncoder"):
      return o._jsonEncoder()

    return json.JSONEncoder.default(self, o)



def roundUpDatetime(dt, periodSec):
  """ Round up datetime to the nearest period seconds

  e.g., if period is 300 seconds (i.e., 5 minutes), then then 1:55:00.0 remains
  as is, while 1:51:xx becomes 1:55:00.0; 1:55:00.1 and 1:56:xx become 2:00:00.0

  :param dt: datetime.datetime object
  :param periodSec: the rounding period in seconds
  :returns: the rounded-up datetime
  :rtype: datetime.datetime object
  """
  seconds = dt.minute * 60 + dt.second + dt.microsecond/1000000.0
  seconds = math.ceil(seconds/float(periodSec)) * periodSec
  dt = (dt.replace(minute=0, second=0, microsecond=0) +
           datetime.timedelta(seconds=seconds))
  return dt



# Convenience function to specify default/standard arguments to json.loads
jsonDecode = partial(json.loads, object_hook=_jsonDecodeDictUTF8)

# Serializes a Python dictionary into a JSON string.
jsonEncode = partial(json.dumps, cls=_JSONEncoder, indent=2)



def msgpack_pack(obj):
  """
  Serialize an Object using "msgpack".

  :see: :func:`_msgpack_encode` for special data type handling
  """
  return msgpack.packb(obj, default=_msgpack_encode)



def msgpack_unpack(msg):
  """Deserialize an Object serialized with "msgpack_pack" """

  return msgpack.unpackb(msg, object_hook=_msgpack_decode, use_list=True)



def _msgpack_decode(obj):
  if b'\x01' in obj:
    obj = datetime.datetime.fromtimestamp(obj["\x01"])
  return obj



def _msgpack_encode(obj):
  """
  Special data types serialization hooks:

      '\x01' : datetime.datetime
  """
  if isinstance(obj, datetime.datetime):
    return {'\x01': time.mktime(obj.timetuple())}
  return obj



def validate(obj, schema):
  validictory.validate(obj, schema,
    required_by_default=False,
    validator_cls=validictory.SchemaValidator
  )
