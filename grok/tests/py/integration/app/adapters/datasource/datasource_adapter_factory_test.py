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

""" Integration tests for Datasource Adapter factory """

# Disable W0212 - Access to a protected member
# pylint: disable=W0212

import unittest

# TODO: Remove reference to YOMP (TAUR-708)
import YOMP.app.adapters.datasource as datasource_adapter_factory

from nta.utils.logging_support_raw import LoggingSupport



def setUpModule():
  LoggingSupport.initTestApp()



class DatasourceAdapterFactoryTest(unittest.TestCase):


  EXPECTED_DATASOURCE_NAMES = ("custom", "autostack", "cloudwatch")


  def testListDatasourceNames(self):
    """ Make sure listDatasourceNames returns the expected datasource names """
    self.assertItemsEqual(datasource_adapter_factory.listDatasourceNames(),
                          self.EXPECTED_DATASOURCE_NAMES)


  def testCreateAutostackDatasourceAdapter(self):
    """ Make sure createAutostackDatasourceAdapter returns the expected adapter
    """
    adapter = datasource_adapter_factory.createAutostackDatasourceAdapter()
    self.assertEqual(adapter._DATASOURCE, "autostack")
    self.assertEqual(adapter.__class__.__name__, "_AutostackDatasourceAdapter")


  def testCreateCloudwatchDatasourceAdapter(self):
    """ Make sure createCloudwatchDatasourceAdapter returns the expected adapter
    """
    adapter = datasource_adapter_factory.createCloudwatchDatasourceAdapter()
    self.assertEqual(adapter._DATASOURCE, "cloudwatch")
    self.assertEqual(adapter.__class__.__name__, "_CloudwatchDatasourceAdapter")


  def testCreateCustomDatasourceAdapter(self):
    """ Make sure createCustomDatasourceAdapter returns the expected adapter
    """
    adapter = datasource_adapter_factory.createCustomDatasourceAdapter()
    self.assertEqual(adapter._DATASOURCE, "custom")
    self.assertEqual(adapter.__class__.__name__, "_CustomDatasourceAdapter")


  def testCreateDatasourceAdapter(self):
    """ Make sure createDatasourceAdapter is able to create all expected
    adapters
    """
    for datasourceName in self.EXPECTED_DATASOURCE_NAMES:
      adapter = datasource_adapter_factory.createDatasourceAdapter(
        datasourceName)
      self.assertEqual(adapter._DATASOURCE, datasourceName)
      self.assertEqual(adapter.__class__.__name__,
                       "_" + datasourceName.capitalize() + "DatasourceAdapter")



if __name__ == "__main__":
  unittest.main()
