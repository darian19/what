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
Common utilities for sqlalchemy-based repositories
"""

import inspect
import logging
import socket

from MySQLdb.constants import ER, CR
import MySQLdb.converters

import sqlalchemy.dialects.mysql
from sqlalchemy.exc import InternalError, OperationalError, DBAPIError
import sqlalchemy.sql.compiler

from nta.utils import error_handling


# Client mysql error codes of interest;
# (per https://dev.mysql.com/doc/refman/5.5/en/error-messages-client.html)

# Lost connection to MySQL server at '%s', system error: %d
# NOTE: This one was not available in MySQLdb.constants.CR at the time of this
# writing
_CR_SERVER_LOST_EXTENDED = 2055


# Client-side mysql errors that warrant transaction retry
_RETRIABLE_CLIENT_ERROR_CODES = (
  CR.CONNECTION_ERROR,
  CR.CONN_HOST_ERROR,
  CR.UNKNOWN_HOST,
  CR.SERVER_GONE_ERROR,
  CR.TCP_CONNECTION,
  CR.SERVER_HANDSHAKE_ERR,
  CR.SERVER_LOST,
  _CR_SERVER_LOST_EXTENDED,
)


# Server-side mysql errors that warrant a transaction retry
_RETRIABLE_SERVER_ERROR_CODES = (
  ER.TABLE_DEF_CHANGED,
  ER.LOCK_WAIT_TIMEOUT,
  ER.LOCK_DEADLOCK,

  #Maybe these also?
  #  ER_TOO_MANY_DELAYED_THREADS
  #  ER_BINLOG_PURGE_EMFILE
  #  ER_TOO_MANY_CONCURRENT_TRXS
  #  ER_CON_COUNT_ERROR
  #  ER_OUTOFMEMORY
)


# Server-side and client-side mysql error codes that warrent a transaction retry
_ALL_RETRIABLE_ERROR_CODES = set(_RETRIABLE_CLIENT_ERROR_CODES +
                                 _RETRIABLE_SERVER_ERROR_CODES)


_RETRY_TIMEOUT = 10



def retryOnTransientErrors(execute):
  """Decorator that makes engine retry on transient db failures

  :param execute: Callable to be retried upon transient database failures
  :type execute: function
  :returns: Decorated function
  """

  def retrySQL():
    def retryFilter(e, *_args, **_kwargs):
      if isinstance(e, (InternalError, OperationalError)):
        if e.orig.args and e.orig.args[0] in _ALL_RETRIABLE_ERROR_CODES:
          return True

      elif isinstance(e, DBAPIError):
        if (e.orig.args and inspect.isclass(e.orig.args[0]) and
            issubclass(e.orig.args[0], socket.error)):
          return True

      return False

    retryExceptions = tuple([
      InternalError,
      OperationalError,
      DBAPIError,
    ])

    return error_handling.retry(
      timeoutSec=_RETRY_TIMEOUT, initialRetryDelaySec=0.1, maxRetryDelaySec=10,
      retryExceptions=retryExceptions, retryFilter=retryFilter,
      logger=logging.getLogger("sql-retry"))


  @retrySQL()
  def executeWrapper(*args, **kwargs):
    return execute(*args, **kwargs)

  return executeWrapper



def compileMysqlQuery(query):
  """ For debugging only! Given a sqlalchemy-core statement, return the
  corresponding SQL statement in the mysql dialect

  :param query: sqlalchemy-core statement
  :returns: corresponding SQL statement string in the mysql dialect
  """
  dialect = sqlalchemy.dialects.mysql.dialect()
  compiledObj = sqlalchemy.sql.compiler.SQLCompiler(dialect, query)
  compiledObj.compile()
  encoding = dialect.encoding
  params = []
  for k in compiledObj.positiontup:
    v = compiledObj.params[k]
    if isinstance(v, unicode):
      v = v.encode(encoding)
    params.append(MySQLdb.converters.escape(v, MySQLdb.converters.conversions))
  return (compiledObj.string.encode(encoding) % tuple(params)).decode(encoding)
