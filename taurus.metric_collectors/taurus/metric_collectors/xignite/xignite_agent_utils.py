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

"""
Shared utilities for xignite-feed agents
"""

from taurus.metric_collectors import collectorsdb
from taurus.metric_collectors.collectorsdb import schema



@collectorsdb.retryOnTransientErrors
def insertSecurity(engine, xigniteSecurity):
  """ Insert information about the given security into xignite_security table,
  ignoring duplicate key (resolves race conditions in concurrency situtations)

  :param sqlalchemy.engine.base.Engine engine: engine for executing the query
  :param dict xigniteSecurity: Security info from xignite API results (e.g., global
    security news, security bars, etc.)
  """
  secIns = schema.xigniteSecurity.insert(
    ).prefix_with("IGNORE", dialect="mysql"
    ).values(symbol=xigniteSecurity["Symbol"].upper(),
             cik=xigniteSecurity["CIK"],
             cusip=xigniteSecurity["CUSIP"],
             isin=xigniteSecurity["ISIN"],
             valoren=xigniteSecurity["Valoren"],
             name=xigniteSecurity["Name"],
             market=xigniteSecurity["Market"],
             mic=xigniteSecurity["MarketIdentificationCode"],
             most_liquid_exg=(xigniteSecurity["MostLiquidExchange"]),
             industry=xigniteSecurity["CategoryOrIndustry"])

  engine.execute(secIns)
