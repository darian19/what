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
Test utilities concerning AMQP (e.g., RabbitMQ) interaction
"""

import contextlib
import functools
import json
import logging
import types
import uuid

from mock import patch
import requests

from nta.utils import amqp
from nta.utils.test_utils.config_test_utils import ConfigAttributePatch


_LOGGER = logging.getLogger(__name__)



class RabbitmqVirtualHostPatch(object):
  """ An instance of this class may be used as a decorator, class decorator or
  Context Manager for overriding the default virtual host both in-proc and in
  subprocesses.

  On start: creates a temporary virtual host and patches the "virtual_host"
    attribute in the "connection" section of rabbitmq.conf configuration file

  On stop: deletes the temporary virtual host and unpatches the "virtual_host"
    rabbitmq configuraiton attribute.

  NOTE: the patch assumes that the code under test connects to RabbitMQ using
  the virtual_host from "virtual_host" attribute in the "connection" section of
  rabbitmq.conf configuration file.

  NOTE: this decorator will only decorate methods beginning with the
  `mock.patch.TEST_PREFIX` prefix (defaults to "test"). Please keep this in
  mind when decorating entire classes.
  """

  _RABBIT_MANAGEMENT_HEADERS = {"content-type": "application/json"}

  def __init__(self, clientLabel, kw=None, logger=logging):
    """
    clientLabel: this string will be used to construct the temporary endpoint
      names. The following characters are permitted, and it shouldn't be too
      long: [._a-zA-Z]. This may be helpful with diagnostics. A specific test
      class name (or similar) would make a reasonable clientLabel.
    kw: name of keyword argument to add to the decorated function(s). Its value
      will be a reference to this instance of RabbitmqVirtualHostPatch.
      Ignored when this instance is used as context manager. Defaults to kw=None
      to avoid having it added to the keyword args.
    """
    self.active = False
    """ True when applied successfully; False after successfully removed or not
    applied """

    self._clientLabel = clientLabel
    self._kw = kw
    self._logger = logger

    self._cachedVirtualHost = None
    """ Name of override RabbotMQ virtual host """

    self._virtualHostCreated = False

    self._configPatch = None


  @property
  def _vhost(self):
    if self._cachedVirtualHost is None:
      self._cachedVirtualHost = "%s_%s" % (self._clientLabel, uuid.uuid1().hex,)
    return self._cachedVirtualHost


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
    def applyVirtualHostPatch(*args, **kwargs):
      self.start()
      try:
        if self._kw is not None:
          kwargs[self._kw] = self
        return f(*args, **kwargs)
      finally:
        self.stop()

    return applyVirtualHostPatch


  def _decorateClass(self, targetClass):
    """ Decorate the test methods in the given class. Honors
    `mock.patch.TEST_PREFIX` for choosing which methods to wrap
    """
    for attrName in dir(targetClass):
      if attrName.startswith(patch.TEST_PREFIX):
        f = getattr(targetClass, attrName)
        if callable(f):
          decoratedFunc = RabbitmqVirtualHostPatch(
            self._clientLabel, self._kw, self._logger)(f)
          setattr(targetClass, attrName, decoratedFunc)
    return targetClass


  def start(self):
    assert not self.active

    # Use RabbitMQ Management Plugin to create the new temporary vhost
    connectionParams = amqp.connection.RabbitmqManagementConnectionParams()

    url = "http://%s:%s/api/vhosts/%s" % (
      connectionParams.host, connectionParams.port, self._vhost)

    try:
      try:
        response = requests.put(
          url,
          headers=self._RABBIT_MANAGEMENT_HEADERS,
          auth=(
            connectionParams.username,
            connectionParams.password))

        response.raise_for_status()

        self._virtualHostCreated = True
        self._logger.info("%s: created temporary rabbitmq vhost=%s",
                          self.__class__.__name__, self._vhost)
      except Exception:
        self._logger.exception(
          "Attempt to create temporary vhost=%s failed. url=%r",
          self._vhost, url)
        raise

      # Configure permissions on the new temporary vhost
      try:
        url = "http://%s:%s/api/permissions/%s/%s" % (
          connectionParams.host, connectionParams.port,
          self._vhost, connectionParams.username)

        response = requests.put(
          url,
          headers=self._RABBIT_MANAGEMENT_HEADERS,
          data=json.dumps({"configure": ".*", "write": ".*", "read": ".*"}),
          auth=(
            connectionParams.username,
            connectionParams.password))

        response.raise_for_status()

        self._logger.info(
          "%s: Configured persmissions on temporary rabbitmq vhost=%s",
          self.__class__.__name__, self._vhost)
      except Exception:
        self._logger.exception(
          "Attempt to configure premissions on vhost=%s failed. url=%r",
          self._vhost, url)
        raise

      # Apply a config patch to override the rabbitmq virtual host to be
      # used by message_bus_connector and others
      rabbitmqConfig = amqp.connection.RabbitmqConfig()
      self._configPatch = ConfigAttributePatch(
        rabbitmqConfig.CONFIG_NAME,
        rabbitmqConfig.baseConfigDir,
        (("connection", "virtual_host", self._vhost),))

      self._configPatch.start()

      self._logger.info("%s: overrode rabbitmq vhost=%s",
                        self.__class__.__name__, self._vhost)

      # Self-validation
      connectionParams = (
        amqp.connection.getRabbitmqConnectionParameters())
      actualVhost = connectionParams.vhost
      assert actualVhost == self._vhost, (
        "Expected vhost=%r, but got vhost=%r") % (self._vhost, actualVhost)

    except Exception:
      self._logger.exception("patch failed, deleting vhost=%s", self._vhost)
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
      if self._configPatch is not None and self._configPatch.active:
        self._configPatch.stop()
    finally:
      if self._virtualHostCreated:
        self._deleteTemporaryVhost()
        self._virtualHostCreated = False

    self._logger.info("%s: removed patch", self.__class__.__name__)


  def _deleteTemporaryVhost(self):
    """ Delete a RabbitMQ virtual host """
    # Use RabbitMQ Management Plugin to delete the temporary vhost
    connectionParams = (
        amqp.connection.RabbitmqManagementConnectionParams())

    url = "http://%s:%s/api/vhosts/%s" % (
      connectionParams.host, connectionParams.port, self._vhost)

    try:
      response = requests.delete(
        url,
        headers=self._RABBIT_MANAGEMENT_HEADERS,
        auth=(
          connectionParams.username,
          connectionParams.password))

      response.raise_for_status()

      self._logger.info("%s: deleted temporary rabbitmq vhost=%s",
                        self.__class__.__name__, self._vhost)
    except Exception:
      self._logger.exception(
        "Attempt to delete temporary vhost=%s failed. url=%r",
        self._vhost, url)
      raise



@contextlib.contextmanager
def managedExchangeDeleter(exchange):
  """
  :param exchange:: a single message exchange name string or a sequence of
    message exchange names to delete on exit
  """
  try:
    # __enter__ part
    yield
  finally:
    # __exit__ part
    if isinstance(exchange, types.StringTypes):
      messageExchanges = (exchange,)
    else:
      messageExchanges = exchange

    connParams = amqp.connection.getRabbitmqConnectionParameters()

    for exchangeName in messageExchanges:
      try:
        with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
          _LOGGER.info("managedExchangeDeleter: Deleting exchange=%r",
                       exchangeName)
          amqpClient.deleteExchange(exchangeName, ifUnused=False)
      except amqp.exceptions.AmqpChannelError as e:
        if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
          _LOGGER.info("managedExchangeDeleter: exchange=%r not found (%r)",
                       exchangeName, e)
        else:
          _LOGGER.exception("managedExchangeDeleter: Deletion of exchange=%r "
                            "failed", exchangeName)



@contextlib.contextmanager
def managedQueueDeleter(mq):
  """
  mq: a single message queue name string or a sequence of message queue
    names to delete on exit
  """
  try:
    # __enter__ part
    yield
  finally:
    # __exit__ part
    if isinstance(mq, types.StringTypes):
      messageQueues = (mq,)
    else:
      messageQueues = mq

    connParams = amqp.connection.getRabbitmqConnectionParameters()

    for mqName in messageQueues:
      try:
        with amqp.synchronous_amqp_client.SynchronousAmqpClient(connParams) as (
          amqpClient):
          _LOGGER.info("managedQueueDeleter: Deleting mq=%r",
                       mqName)
          amqpClient.deleteQueue(mqName, ifUnused=False, ifEmpty=False)
      except amqp.exceptions.AmqpChannelError as e:
        # Suppress queue_delete error (perhaps queue was never created?)
        if e.code == amqp.constants.AMQPErrorCodes.NOT_FOUND:
          _LOGGER.info("managedQueueDeleter: mq=%r not found (%r)",
                       mqName, e)
        else:
          _LOGGER.exception(
            "managedQueueDeleter: Deletion of mq=%r failed", mqName)
