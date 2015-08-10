#!/usr/bin/env python
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

"""Unit tests for the error-handling utilities"""

import os
import Queue
import unittest

from mock import patch

from nta.utils import error_handling



class ErrorHandlingUtilsTest(unittest.TestCase):
  """ Unit tests for the error-handling utilities """

  def testAbortProgramOnAnyExceptionWithoutException(self):

    @error_handling.abortProgramOnAnyException(exitCode=2)
    def doSomething(*args, **kwargs):
      return args, kwargs


    inputArgs = (1, 2, 3)
    inputKwargs = dict(a="A", b="B", c="C")

    outputArgs, outputKwargs = doSomething(*inputArgs, **inputKwargs)

    # Validate that doSomething got the right inputs
    self.assertEqual(outputArgs, inputArgs)
    self.assertEqual(outputKwargs, inputKwargs)


  def testAbortProgramOnAnyExceptionWithRuntimeErrorException(self):
    @error_handling.abortProgramOnAnyException(exitCode=2)
    def doSomething(*_args, **_kwargs):
      raise RuntimeError()


    # Patch os._exit and run model in SlotAgent
    osExitCodeQ = Queue.Queue()
    with patch.object(os, "_exit", autospec=True,
                      side_effect=osExitCodeQ.put):
      inputArgs = (1, 2, 3)
      inputKwargs = dict(a="A", b="B", c="C")

      with self.assertRaises(RuntimeError):
        doSomething(*inputArgs, **inputKwargs)

      exitCode = osExitCodeQ.get_nowait()
      self.assertEqual(exitCode, 2)


  def testAbortProgramOnAnyExceptionWithSystemExitException(self):
    # Repeat of the other test, but his time with SystemExit exception,
    # which is derived from BaseException

    @error_handling.abortProgramOnAnyException(exitCode=2)
    def doSomething(*_args, **_kwargs):
      raise SystemExit


    # Patch os._exit and run model in SlotAgent
    osExitCodeQ = Queue.Queue()
    with patch.object(os, "_exit", autospec=True,
                      side_effect=osExitCodeQ.put):
      inputArgs = (1, 2, 3)
      inputKwargs = dict(a="A", b="B", c="C")

      with self.assertRaises(SystemExit):
        doSomething(*inputArgs, **inputKwargs)

      exitCode = osExitCodeQ.get_nowait()
      self.assertEqual(exitCode, 2)



if __name__ == '__main__':
  unittest.main()

