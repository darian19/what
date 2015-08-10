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
import unittest
import metrics_api_test
import cloudwatch_api_test
import settings_api_test
import models_api_test
import webapp_test
import messagemanager_test


loader = unittest.TestLoader()

suite = loader.loadTestsFromModule(models_api_test)
suite.addTests(loader.loadTestsFromModule(metrics_api_test))
suite.addTests(loader.loadTestsFromModule(cloudwatch_api_test))
suite.addTests(loader.loadTestsFromModule(settings_api_test))
suite.addTests(loader.loadTestsFromModule(cloudwatch_api_test))
suite.addTests(loader.loadTestsFromModule(webapp_test))
suite.addTests(loader.loadTestsFromModule(messagemanager_test))


if __name__ == '__main__':
  unittest.TextTestRunner(verbosity=2).run(suite)
