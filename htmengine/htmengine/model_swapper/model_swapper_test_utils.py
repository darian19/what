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

""" Model Swapper utilities for tests """

import contextlib
import functools
import logging
import types


from mock import patch

from nta.utils import amqp
from nta.utils.test_utils.amqp_test_utils import RabbitmqVirtualHostPatch


from htmengine.model_swapper.model_swapper_interface import (
    ModelSwapperInterface)

from htmengine.model_checkpoint_mgr.model_checkpoint_test_utils import (
    ModelCheckpointStoragePatch)



# Disable warning: Access to a protected member
# pylint: disable=W0212



class ModelSwapperIsolationPatch(object):
  """ An instance of this class may be used as a decorator, class decorator or
  Context Manager for redirecting ModelSwapperInterface input, result and
  notification endpoints as well as model checkpoints both in-proc and in
  subprocesses. Deletes the redirected endpoints and model checkpoints on stop.
  """

  def __init__(self, clientLabel, kw=None, logger=logging):
    """
    clientLabel: this string will be used to construct the temporary endpoint
      names. The following characters are permitted, and it shouldn't be too
      long: [._a-zA-Z]. This may be helpful with diagnostics. A specific test
      class name (or similar) would make a reasonable clientLabel.
    kw: name of keyword argument to add to the decorated function(s). Its value
      will be a reference to this instance of ModelSwapperIsolationPatch.
      Ignored when this instance is used as context manager. Defaults to kw=None
      to avoid having it added to the keyword args.
    """
    self.active = False
    """ True when applied successfully; False after successfully removed or not
    applied """

    self._clientLabel = clientLabel
    self._kw = kw
    self._logger = logger

    self._vhostPatch = None
    """ RabbitMQ virtual host patch """

    self._modelCheckpointPatch = None
    """ Model checkpoint storage patch """


  def __enter__(self):
    self.start()
    return self


  def __exit__(self, *args):
    self.stop()
    return False


  def __call__(self, f):
    """ Implement the function or class decorator """
    if isinstance(f, types.TypeType):
      return self._decorateClass(f)

    @functools.wraps(f)
    def applyModelSwapperIsolationPatch(*args, **kwargs):
      self.start()
      try:
        if self._kw is not None:
          kwargs[self._kw] = self
        return f(*args, **kwargs)
      finally:
        self.stop()

    return applyModelSwapperIsolationPatch


  def _decorateClass(self, targetClass):
    """ Decorate the test methods in the given class. Honors
    `mock.patch.TEST_PREFIX` for choosing which methods to wrap
    """
    for attrName in dir(targetClass):
      if attrName.startswith(patch.TEST_PREFIX):
        f = getattr(targetClass, attrName)
        if callable(f):
          decoratedFunc = ModelSwapperIsolationPatch(
            self._clientLabel, self._kw, self._logger)(f)
          setattr(targetClass, attrName, decoratedFunc)
    return targetClass


  def start(self):
    assert not self.active

    try:
      # Apply the RabbitMQ virtual host patch
      self._vhostPatch = RabbitmqVirtualHostPatch(clientLabel=self._clientLabel,
                                                  kw=None, logger=self._logger)
      self._vhostPatch.start()
      # Apply Model Checkpoint Manager patch
      self._modelCheckpointPatch = ModelCheckpointStoragePatch(
        kw=None, logger=self._logger)
      self._modelCheckpointPatch.start()

      # Self-validation
      actualVhost = (
          amqp.connection.getRabbitmqConnectionParameters().vhost)
      assert actualVhost == self._vhostPatch._vhost, (
        "Expected vhost=%r, but got vhost=%r") % (
        self._vhost, actualVhost)
    except Exception:
      self._logger.exception("patch failed, removing sub-patches")
      self._removePatches()
      raise

    self.active = True
    self._logger.info("%s: applied patch", self.__class__.__name__)


  def stop(self):
    assert self.active

    self._removePatches()

    self.active = False


  def _removePatches(self):
    """ NOTE: may be called intenrally to clean-up mid-application of patch
    """
    try:
      if (self._modelCheckpointPatch is not None
          and self._modelCheckpointPatch.active):
        self._modelCheckpointPatch.stop()
      else:
        assert not self.active
    finally:
      if self._vhostPatch is not None and self._vhostPatch.active:
        self._vhostPatch.stop()
      else:
        assert not self.active

    self._logger.info("%s: removed patch", self.__class__.__name__)
