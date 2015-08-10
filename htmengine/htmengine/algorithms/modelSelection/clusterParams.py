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

import numpy as np
import csv
import os
import json

def setRandomEncoderParams(params, minVal, maxVal, minResolution):
  """
  Given model params, figure out the correct parameters for the 
  RandomDistributed encoder. Modifies params in place.
  """
  encodersDict= (
    params['modelConfig']['modelParams']['sensorParams']['encoders']
    )
  for v in encodersDict.itervalues():
    if v is not None:
      if v['type'] == 'RandomDistributedScalarEncoder':
        resolution = max(minResolution,
                         (maxVal - minVal) / v.pop('numBuckets')
                        )
        encodersDict['c1']['resolution'] = resolution
        
  

def getScalarMetricWithTimeOfDayParams(metricData,
                                       minVal=None,
                                       maxVal=None,
                                       minResolution=None,
                                       useRandomEncoder=True):
  """
    Return an ordered list of JSON strings that can be used to create an
    anomaly model for OPF's ModelFactory.


    Args:
        metricData:  numpy array of metric data. Used to calculate minVal 
                     and maxVal if either is unspecified

        minVal:      minimum value of metric. Used to set up encoders. If None 
                     will be derived from metricData.

        maxVal:      minimum value of metric. Used to set up input encoders. If
                     None will be derived from metricData
                     
        minResolution: minimum resolution of metric. Used to set up encoders.
                       If None, will use default value of 0.001.

        useRandomEncoder: if True, use RandomDistributedScalarEncoder instead
                     of ScalarEncoder

    Assumptions:
        The timeStamp field corresponds to c0
        The predicted field corresponds to c1   
  """
  # Default values
  if minResolution is None:
    minResolution = 0.001

  # Read a sorted list of parameters from the appropriate directory
  currDirectory= os.path.dirname(os.path.realpath(__file__))
  if useRandomEncoder:
    paramsDirectory = 'anomaly_params_random_encoder'
  else:
    # This will go away soon MER-1442
    paramsDirectory = 'scalarMetricWithTimeOfDayAnomalyParams'

  reader = csv.reader(
    open(
      os.path.join(currDirectory, paramsDirectory, 'paramOrder.csv'),
      'r'))
  paramFiles=reader.next()
  paramSets=[]

  # Compute min and/or max from the data if not specified
  if minVal is None or maxVal is None:
    compMinVal, compMaxVal = rangeGen(metricData)
    if minVal is None:
      minVal = compMinVal
    if maxVal is None:
      maxVal = compMaxVal
      
  # Handle the corner case where the incoming min and max are the same
  if minVal == maxVal:
    maxVal = minVal + 1

  # Iterate over the parameters for each model and replace the appropriate
  # min/max values to the computed ones.
  for p in paramFiles:
    with open(os.path.join(currDirectory, paramsDirectory, p), 'r') as infile:
      paramSet=json.load(infile)
      
    encodersDict= (
      paramSet['modelConfig']['modelParams']['sensorParams']['encoders']
      )

    if useRandomEncoder:
      setRandomEncoderParams(paramSet, minVal, maxVal, minResolution)
    else:
      # TODO Update per MER-1442
      encodersDict['c1']['maxval'] = maxVal
      encodersDict['c1']['minval'] = minVal
    
    paramSets.append(paramSet)
    
  return paramSets



def rangeGen(data, std=1):
  """
  Return reasonable min/max values to use given the data. 
  """
  dataStd = np.std(data)
  if dataStd==0:
    dataStd=1
  minval = np.min(data) -  std * dataStd
  maxval = np.max(data) +  std * dataStd
  return minval, maxval
