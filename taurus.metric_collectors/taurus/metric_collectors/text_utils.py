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

from cStringIO import StringIO


# Question Mark code point U+FFFD
_SUBSTITUTION_UTF8 = '\xef\xbf\xbd'



#def sanitizeUnicode(text):
def sanitize4ByteUnicode(text):
  """ Replace 4-byte and invalid code points with substitution char.

  NOTE: this is necessiated by lack of support for 4-byte code points
  in mysql < v5.5.3 that is deployed on our initial
  tauruspoc.collectors.numenta.com
  """
  # Quick check for all-ascii
  if all(ord(c) < 128 for c in text):
    return text

  def getNextSequence():
    stream = StringIO(text.encode("utf-8", "replace"))
    
    while True:
      sequence = _readSequenceFromUtf8(stream)
      if sequence:
        if len(sequence) <= 3:
          yield sequence
        else:
          yield _SUBSTITUTION_UTF8
      else:
        break

  return "".join(getNextSequence()).decode("utf-8", "replace")


def _readSequenceFromUtf8(stream):
  """
  :returns: a byte string corresponding to the next code point on stream;
    substitutes _SUBSTITUTION_UTF8 byte string for invalid/incomplete code
    points; returns empty string ("") on end of file
  """
  class SequenceError(Exception):
    pass
  class EndOfFile(Exception):
    pass

  def getchar():
    c = stream.read(1)
    if not c:
      raise EndOfFile
    return ord(c)

  unit1 = unit2 = unit3 = unit4 = None

  try:
    unit1 = getchar()
    if unit1 < 0x80:
      return chr(unit1)
    elif unit1 < 0xC2:
      # continuation or overlong 2-byte sequence
      raise SequenceError(0)
    elif unit1 < 0xE0:
      # 2-byte sequence
      unit2 = getchar()
      if (unit2 & 0xC0) != 0x80:
        raise SequenceError(1)
      return chr(unit1) + chr(unit2)
    elif unit1 < 0xF0:
      # 3-byte sequence
      unit2 = getchar()
      if (unit2 & 0xC0) != 0x80:
        raise SequenceError(1)
      if unit1 == 0xE0 and unit2 < 0xA0:
        # overlong
        raise SequenceError(1)
      unit3 = getchar()
      if (unit3 & 0xC0) != 0x80:
        raise SequenceError(2)
      return chr(unit1) + chr(unit2) + chr(unit3)
    elif unit1 < 0xF5:
      # 4-byte sequence
      unit2 = getchar()
      if (unit2 & 0xC0) != 0x80:
        raise SequenceError(1)
      if unit1 == 0xF0 and unit2 < 0x90:
        # overlong
        raise SequenceError(1)
      if unit1 == 0xF4 and unit2 >= 0x90:
        # > U+10FFFF
        raise SequenceError(1)
      unit3 = getchar()
      if (unit3 & 0xC0) != 0x80:
        raise SequenceError(2)
      unit4 = getchar()
      if (unit4 & 0xC0) != 0x80:
        raise SequenceError(3)
      return chr(unit1) + chr(unit2) + chr(unit3) + chr(unit4)
    else:
      # > U+10FFFF
      raise SequenceError(0)
  except EndOfFile:
    if unit1 is not None:
      return _SUBSTITUTION_UTF8
    else:
      return ""
  except SequenceError as e:
    stream.seek(e.args[0] * -1, 1)
    return _SUBSTITUTION_UTF8
