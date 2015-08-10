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
Applies the given rabbitmq login information as overrides for
rabbitmq.conf.

NOTE: this script may be configured as "console script" by the package
installer.
"""

from nta.utils.tools.set_rabbitmq_login_impl import setRabbitmqLoginScriptImpl

from taurus.engine import logging_support



def main():
  logging_support.LoggingSupport().initTool()

  setRabbitmqLoginScriptImpl()



if __name__ == "__main__":
  main()
