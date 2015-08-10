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
Utilities for feeding metric data to models
"""

import time

from htmengine.model_swapper import model_swapper_interface



def sendInputRowsToModel(modelId, inputRows, batchSize,
                         modelSwapper, logger, profiling):
  """ Send input rows to CLA model for processing

  :param modelId: unique identifier of the model

  :param inputRows: sequence of model_swapper_interface.ModelInputRow objects

  :param batchSize: max number of data records per input batch

  :param modelSwapper: model_swapper_interface.ModelSwapperInterface object

  :param logger: logger object

  :param profiling: True if profiling is enabled

  TODO: unit-test
  """
  logger.debug("Streaming numRecords=%d to model=%s", len(inputRows), modelId)

  # Stream data to HTM model in batches
  for batch in (inputRows[i:i+batchSize] for i in
                xrange(0, len(inputRows), batchSize)):
    if profiling:
      submitStartTime = time.time()

    try:
      batchID = modelSwapper.submitRequests(modelId, batch)
    except model_swapper_interface.ModelNotFound as ex:
      # Likely a race-condition with the app layer's model deletion code path
      # TODO: unit-test
      logger.warning("model=%s not found from submitRequests; "
                     "race-condition with model deletion path? %r", modelId, ex)
      return
    except:
      # TODO: unit-test
      logger.exception(
        "Error submitting batch to model=%s; numRows=%d; rows=[%s]",
        modelId,
        len(batch),
        (("%s:%s" % (batch[0].rowID, batch[-1].rowID))
         if len(batch) > 1 else batch[0].rowID))
      raise
    else:
      if profiling:
        headTS = batch[0].data[0]
        tailTS = batch[-1].data[0]
        logger.info(
          "{TAG:STRM.DATA.TO_MODEL.DONE} Submitted batch=%s to "
          "model=%s; numRows=%d; rows=[%s]; ts=[%s]; duration=%.4fs",
          batchID, modelId, len(batch),
          (("%s..%s" % (batch[0].rowID, batch[-1].rowID))
            if len(batch) > 1 else batch[0].rowID),
          (("%sZ..%sZ" % (headTS.isoformat(), tailTS.isoformat()))
            if len(batch) > 1 else (headTS.isoformat() + "Z")),
          time.time() - submitStartTime)
