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
AMQP connection.

TODO need unit tests
"""
import nta.utils

from nta.utils.config import Config

class RabbitmqConfig(Config):
  """ RabbitMQ configuration access class """

  # Name of rabbitmq config file
  CONFIG_NAME = "rabbitmq.conf"

  def __init__(self, mode=Config.MODE_LOGICAL):
    super(RabbitmqConfig, self).__init__(self.CONFIG_NAME,
                                         nta.utils.CONF_DIR,
                                         mode=mode)



def getRabbitmqConnectionParameters():
  """Get RabbitMQ connection parameters from the RabbitMQ connection config

  :returns: connection parameters for the RabbitMQ broker
  :rtype: ConnectionParams
  """
  config = RabbitmqConfig()

  host = config.get("connection", "host")

  port = config.getint("connection", "port")

  vhost = config.get("connection", "virtual_host")

  credentials = PlainCredentials(config.get("credentials","user"),
                                 config.get("credentials","password"))

  return ConnectionParams(host=host,
                          port=port,
                          vhost=vhost,
                          credentials=credentials)



class RabbitmqManagementConnectionParams(object):
  """RabbitMQ management plugin connection settings"""

  __slots__ = ("host", "port", "vhost", "username", "password")

  def __init__(self):
    connectionParams = getRabbitmqConnectionParameters()

    self.host = connectionParams.host
    self.port = RabbitmqConfig().getint("management", "port")
    self.vhost = connectionParams.vhost
    self.username = connectionParams.credentials.username
    self.password = connectionParams.credentials.password


  def __repr__(self):
    return "%s(host=%r, port=%s, username=%r, password=%r)" % (
      self.__class__.__name__,
      self.host,
      self.port,
      self.username,
      "OBFUSCATED")



class PlainCredentials(object):
  """Credentials for default authentication with RabbitMQ"""

  __slots__ = ("username", "password")


  def __init__(self, username, password):
    """
    :param str username: user name
    :param str password: password
    """
    self.username = username
    self.password = password


  def __repr__(self):
    # NOTE: we obfuscate the password, since we don't want it in the logs
    return "%s(username=%r, password=%r)" % (self.__class__.__name__,
                                             self.username,
                                             "OBFUSCATED")



class ConnectionParams(object):
  """Parameters for connecting to AMQP broker"""

  __slots__ = ("host", "port", "vhost", "credentials")

  DEFAULT_HOST = "localhost"
  DEFAULT_PORT = 5672  # RabbitMQ default
  DEFAULT_VHOST = "/"

  # Default username and password for RabbitMQ
  DEFAULT_USERNAME = "guest"
  DEFAULT_PASSWORD = "guest"


  def __init__(self, host=None, port=None, vhost=None,
               credentials=None):
    """
    :param str host: hostname or IP address; [default="localhost"]
    :param int port: port number; [default=RabbitMQ default port]
    :param str vhost: vhost; [default="/"]
    :param PlainCredentials credentials: authentication credentials;
      [default=RabbitMQ default credentials]
    """
    self.host = host if host is not None else self.DEFAULT_HOST
    self.port = port if port is not None else self.DEFAULT_PORT
    self.vhost = vhost if vhost is not None else self.DEFAULT_VHOST
    self.credentials = (
      credentials if credentials is not None
      else PlainCredentials(self.DEFAULT_USERNAME, self.DEFAULT_PASSWORD))


  def __repr__(self):
    return "%s(host=%r, port=%s, vhost=%r, credentials=%r)" % (
      self.__class__.__name__, self.host, self.port, self.vhost,
      self.credentials)
