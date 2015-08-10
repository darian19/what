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
Unit tests for Model Swapper's ModelRunner class
"""

import base64
import cPickle
import datetime
import logging
import os
import select
import threading
import unittest


from mock import Mock, patch


from nupic.data.fieldmeta import FieldMetaInfo

from nta.utils.test_utils.config_test_utils import ConfigAttributePatch


from htmengine.model_checkpoint_mgr import model_checkpoint_mgr
from htmengine.model_swapper import model_runner
from htmengine.model_swapper import ModelSwapperConfig
from htmengine.model_swapper.model_swapper_interface import (
  _ConsumedRequestBatch,
  ModelCommand,
  ModelCommandResult,
  ModelInputRow,
  ModelInferenceResult)
from htmengine import htmengineerrno



from nta.utils.logging_support_raw import LoggingSupport



modelSwapperConfig = ModelSwapperConfig()



g_logger = logging.getLogger(
  "htmengine.tests.unit.model_swapper.model_runner_test")



def setUpModule():
  LoggingSupport.initTestApp()



class _FakeConsumer(object):
  def __init__(self, requests):
    """
    requests: iterable that yields _ConsumedRequestBatch instances
    """
    self._requests = requests


  def __enter__(self):
    return self

  def __exit__(self, *args, **kwargs):
    return False

  def __iter__(self):
    for value in self._requests:
      yield value



# Dispable warning: invalid name for variable; because @patch.multiple forces
# kwarg args of the same name as the patched attribute; e.g., ModelCheckpointMgr
# pylint: disable=C0103

# Disable warning: Access to a protected member
# pylint: disable=W0212

# Disable warning: Unused argument; because @patch.multiple inserts kwargs
# even for test methods where we don't need to modify the mock(s)
# pylint: disable=W0613

@patch.object(
  model_runner, "ModelSwapperInterface", autospec=True,
  consumeRequests=Mock(
    spec_set=model_runner.ModelSwapperInterface.consumeRequests))
@patch.object(
  model_runner, "ModelCheckpointMgr", autospec=True,
  loadModelDefinition=Mock(
    spec_set=model_runner.ModelCheckpointMgr.loadModelDefinition),
  define=Mock(
    spec_set=model_runner.ModelCheckpointMgr.define),
  remove=Mock(
    spec_set=model_runner.ModelCheckpointMgr.remove),
  load=Mock(
    spec_set=model_runner.ModelCheckpointMgr.load),
  loadCheckpointAttributes=Mock(
    spec_set=model_runner.ModelCheckpointMgr.loadCheckpointAttributes),
  clone=Mock(
    spec_set=model_runner.ModelCheckpointMgr.clone))
class TestModelRunner(unittest.TestCase):
  """ ModelSwapper's SwapController unit tests """

  def testCreateRunStopCloseModelRunner(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Simple test that instantiates ModelRunner with empty input stream, runs
    # the ModelRunner, then validates that it stopped shortly thereafter, then
    # closes it and validates that output sink was closed
    modelID = "abc"

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = (model_checkpoint_mgr.ModelNotFound)

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer([])

    mr = model_runner.ModelRunner(modelID=modelID)
    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately because input stream is
    # empty
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.consumeRequests.assert_called_once_with(modelID=modelID,
                                                        blocking=False)


  def testDefineAndDeleteModel(self, modelCheckpointMgrClassMock,
                               modelSwapperInterfaceClassMock):
    # Test ModelRunner's command-processing plumbing by sending create-model and
    # delete-model commands with mocking of input stream, output, and model
    # access logic.
    modelID = "abc"
    modelConfig = "a"
    inferenceArgs = "b"
    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]

    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes. \
      return_value = (
      {
        model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
          ["1", "2", "3"]})
    checkpointMgrInstanceMock.loadModelDefinition.side_effect = (
      model_checkpoint_mgr.ModelNotFound("Model not found"))

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(
            commandID=1, method="defineModel",
            args=dict(modelConfig=modelConfig,
                      inferenceArgs=inferenceArgs,
                      inputRecordSchema=inputRecordSchema)),
          ModelCommand(commandID=2, method="deleteModel", args=None)])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two commands
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    self.assertEqual(checkpointMgrInstanceMock.loadModelDefinition.call_count,
                     0)

    # Verify expected saving of model metadata
    expectedModelParams = dict(modelConfig=modelConfig,
                               inferenceArgs=inferenceArgs)
    expectedInputSchema = requests[0].objects[0].args["inputRecordSchema"]
    checkpointMgrInstanceMock.define.assert_called_once_with(
      modelID=modelID,
      definition=dict(
        modelParams=expectedModelParams,
        inputSchema=expectedInputSchema))

    # Verify model-deletion call
    checkpointMgrInstanceMock.remove.assert_called_once_with(modelID=modelID)

    # Verify emitted results
    expectedResults = [
      ModelCommandResult(commandID=requests[0].objects[0].commandID,
                         method=requests[0].objects[0].method, status=0),
      ModelCommandResult(commandID=requests[0].objects[1].commandID,
                         method=requests[0].objects[1].method, status=0),
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  def testDeleteModelThatDoesNotExist(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's "deleteModel" command processing when the model
    # doesn't exist. This might be the case as the result of the side-effect
    # from the at-least-once delivery guarantee in the reliable data path.
    modelID = "abc_non_existing"

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = (model_checkpoint_mgr.ModelNotFound)

    # Configure ModelCheckpointMgr mock
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.remove.side_effect = (
      model_checkpoint_mgr.ModelNotFound)

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(commandID=1, method="deleteModel", args=None)])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing our request
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify the attempted "remove" call
    checkpointMgrInstanceMock.remove.assert_called_once_with(modelID=modelID)

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 1)

    command = requests[0].objects[0]
    self.assertEqual(outputResults[0].commandID, command.commandID)
    self.assertEqual(outputResults[0].status, htmengineerrno.SUCCESS)
    self.assertIsNone(outputResults[0].errorMessage)


  def testDefineModelWithSameCreationMetaInfo(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's command-processing plumbing for attempting to
    # create a model that already exists with same model creation args.
    # This should be successful because it might be the side-effect of the
    # at-least-once delivery guarantee of the reliable data path.
    modelID = "abc_existing_with_same_creation_meta"
    modelConfig = "a"
    inferenceArgs = "b"
    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]

    # Configure model checkpoint manager mock
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes.side_effect = (
      model_checkpoint_mgr.ModelNotFound)
    checkpointMgrInstanceMock.define.side_effect = (
      model_checkpoint_mgr.ModelAlreadyExists)
    checkpointMgrInstanceMock.loadModelDefinition.return_value = dict(
      modelParams=dict(modelConfig=modelConfig, inferenceArgs=inferenceArgs),
      inputSchema=inputRecordSchema)

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(
            commandID=1, method="defineModel",
            args=dict(modelConfig=modelConfig,
                      inferenceArgs=inferenceArgs,
                      inputRecordSchema=inputRecordSchema))])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing our request
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify usage of checkpoint manager loadModelDefinition() call that we
    # configured
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify that meta info wasn't saved
    self.assertEqual(checkpointMgrInstanceMock.define.call_count, 1)

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 1)

    command = requests[0].objects[0]
    self.assertEqual(outputResults[0].commandID, command.commandID)
    self.assertEqual(outputResults[0].status, htmengineerrno.SUCCESS)
    self.assertIsNone(outputResults[0].errorMessage)


  def testDefineModelWithDifferentCreationMetaInfoAndAlreadyExistsError(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's command-processing error plumbing for attempting to
    # create a model that already exists with different model creation args.
    modelID = "abc_existing_with_different_creation_meta"
    modelConfig = "a"
    inferenceArgs = "b"
    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]


    # Configure model checkpoint manager mock
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes.side_effect = (
      model_checkpoint_mgr.ModelNotFound)
    checkpointMgrInstanceMock.define.side_effect = (
      model_checkpoint_mgr.ModelAlreadyExists)
    checkpointMgrInstanceMock.loadModelDefinition.return_value = dict(
      modelParams=dict(modelConfig="otherthan_a", inferenceArgs="otherthan_b"),
      inputSchema=[FieldMetaInfo("otherthan_c1", "float", "")])

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(
            commandID=1, method="defineModel",
            args=dict(modelConfig=modelConfig,
                      inferenceArgs=inferenceArgs,
                      inputRecordSchema=inputRecordSchema))])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing our request
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify checkpoint manager loadModelDefinition() call that we configured
    self.assertEqual(checkpointMgrInstanceMock.loadModelDefinition.call_count,
                     1)

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 1)

    command = requests[0].objects[0]
    self.assertEqual(outputResults[0].commandID, command.commandID)
    self.assertEqual(outputResults[0].status,
                     htmengineerrno.ERR_MODEL_ALREADY_EXISTS)
    self.assertIn("already exists with different",
                  outputResults[0].errorMessage)


  def testCommandPathWithGenericError(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's command-processing error plumbing for emitting result
    # with generic error.
    modelID = "abc"

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = model_checkpoint_mgr.ModelNotFound

    # Configure ModelCheckpointMgr mock
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.remove.side_effect = Exception(
      "Generic deleteModel error")

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(commandID=1, method="deleteModel", args=None)])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing our request
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify the attempted "remove" call
    checkpointMgrInstanceMock.remove.assert_called_once_with(modelID=modelID)

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 1)

    command = requests[0].objects[0]
    self.assertEqual(outputResults[0].commandID, command.commandID)
    self.assertEqual(outputResults[0].status, htmengineerrno.ERR)
    self.assertIn("Generic deleteModel error", outputResults[0].errorMessage)


  def testCommandPathWithUnknownMethod(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's command-processing error plumbing for attempting to
    # delete a model that doesn't exist.
    modelID = "abc"

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = model_checkpoint_mgr.ModelNotFound

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelCommand(commandID=1, method="blahBlahMethod", args=None)])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing our request
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 1)

    command = requests[0].objects[0]
    self.assertEqual(outputResults[0].commandID, command.commandID)
    self.assertEqual(outputResults[0].status, htmengineerrno.ERR_INVALID_ARG)
    self.assertIn("Unknown command method", outputResults[0].errorMessage)


  def testCloneModel(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):

    modelID = "abc"

    destModelID = "def"

    mr = model_runner.ModelRunner(modelID=modelID)

    command = ModelCommand(
      commandID=1, method="cloneModel",
      args=dict(modelID=destModelID))

    result = mr._processModelCommand(command)

    self.assertIsInstance(result, ModelCommandResult)

    self.assertEqual(result.commandID, command.commandID)
    self.assertEqual(result.method, command.method)
    self.assertEqual(result.status, htmengineerrno.SUCCESS)

    modelCheckpointMgrMock = modelCheckpointMgrClassMock.return_value
    modelCheckpointMgrMock.clone.assert_called_with(modelID, destModelID)


  def testCloneModelWithDestinationAlreadyExists(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):

    modelCheckpointMgrMock = modelCheckpointMgrClassMock.return_value
    modelCheckpointMgrMock.clone.side_effect = (
      model_checkpoint_mgr.ModelAlreadyExists)

    modelID = "abc"

    destModelID = "def"

    mr = model_runner.ModelRunner(modelID=modelID)

    command = ModelCommand(
      commandID=1, method="cloneModel",
      args=dict(modelID=destModelID))

    result = mr._processModelCommand(command)

    self.assertIsInstance(result, ModelCommandResult)

    self.assertEqual(result.commandID, command.commandID)
    self.assertEqual(result.method, command.method)
    self.assertEqual(result.status, htmengineerrno.SUCCESS)

    modelCheckpointMgrMock.clone.assert_called_with(modelID, destModelID)


  def testCloneModelWithSourceModelNotFound(
      self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):

    modelCheckpointMgrMock = modelCheckpointMgrClassMock.return_value
    modelCheckpointMgrMock.clone.side_effect = (
      model_checkpoint_mgr.ModelNotFound)

    modelID = "abc"

    destModelID = "def"

    mr = model_runner.ModelRunner(modelID=modelID)

    command = ModelCommand(
      commandID=1, method="cloneModel",
      args=dict(modelID=destModelID))

    result = mr._processModelCommand(command)

    self.assertIsInstance(result, ModelCommandResult)

    self.assertEqual(result.commandID, command.commandID)
    self.assertEqual(result.method, command.method)
    self.assertEqual(result.status, htmengineerrno.ERR_NO_SUCH_MODEL)

    modelCheckpointMgrMock.clone.assert_called_with(modelID, destModelID)


  @patch.object(
    model_runner, "ModelFactory", autospec=True,
    create=Mock(spec_set=model_runner.ModelFactory.create))
  def testLoadFromModelParamsAndSaveFull(
      self, modelFactoryClassMock, modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):
    # Test that loading from model params leads to saving via full checkpoint;
    # also verify the inference path.

    modelID = "abc"
    modelConfig = "a"
    inferenceArgs = "b"
    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
    anomalyScore1 = 1.111111
    anomalyScore2 = 2.222222
    dummyModelParams = dict(modelConfig=modelConfig,
                            inferenceArgs=inferenceArgs)

    # Configure ModelCheckpointMgr mock
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes.side_effect = (
      model_checkpoint_mgr.ModelNotFound)
    checkpointMgrInstanceMock.loadModelDefinition.return_value = dict(
      inputSchema=inputRecordSchema, modelParams=dummyModelParams)
    checkpointMgrInstanceMock.load.side_effect = (
      model_checkpoint_mgr.ModelNotFound)

    # Configure ModelFactory mock
    modelInstanceMock = Mock(
      run=Mock(
        side_effect=[
          Mock(inferences=dict(anomalyScore=anomalyScore1)),
          Mock(inferences=dict(anomalyScore=anomalyScore2))]))

    modelFactoryClassMock.create.return_value = modelInstanceMock

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=1, data=[datetime.datetime.utcnow(), 1.0]),
          ModelInputRow(rowID=2, data=[datetime.datetime.utcnow(), 2.0])])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify loading of "inputSchema" and "modelParams" metadata
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify loading of model from params
    modelFactoryClassMock.create.assert_called_once_with(
      modelConfig=dummyModelParams["modelConfig"])

    # Verify expected saving of model
    self.assertEqual(
      checkpointMgrInstanceMock.updateCheckpointAttributes.call_count, 0)

    expectedCheckpointAttributes = {
      model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
        [requests[0].batchID]
      }
    checkpointMgrInstanceMock.save.assert_called_once_with(
      modelID=modelID,
      model=modelInstanceMock,
      attributes=expectedCheckpointAttributes)

    # Verify emitted results
    requestObjects = requests[0].objects
    expectedResults = [
      ModelInferenceResult(
        rowID=requestObjects[0].rowID, status=0, anomalyScore=anomalyScore1),
      ModelInferenceResult(
        rowID=requestObjects[1].rowID, status=0, anomalyScore=anomalyScore2),
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  def testLoadFromFullAndSaveIncremental(
    self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's inference-processing plumbing by sending
    # input rows with mocking of input stream, output, and model
    # access logic.
    modelID = "abc"

    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
    anomalyScore1 = 1.111111
    anomalyScore2 = 2.222222

    modelInstanceMock = Mock(
      run=Mock(
        side_effect=[
          Mock(inferences=dict(anomalyScore=anomalyScore1)),
          Mock(inferences=dict(anomalyScore=anomalyScore2))]))

    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes. \
      return_value = (
      {
        model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
          ["1", "2", "3"]})
    checkpointMgrInstanceMock.loadModelDefinition.return_value = (
      dict(inputSchema=inputRecordSchema))
    checkpointMgrInstanceMock.load.return_value = modelInstanceMock

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=1, data=[datetime.datetime.utcnow(), 1.0]),
          ModelInputRow(rowID=2, data=[datetime.datetime.utcnow(), 2.0])])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify loading of "inputSchema" metadata
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify loading of model
    checkpointMgrInstanceMock.load.assert_called_once_with(modelID)

    # Verify expected saving of model
    self.assertEqual(checkpointMgrInstanceMock.save.call_count, 0)

    expectedCheckpointAttributes = {
      model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
        [requests[0].batchID],
      model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME:
        base64.standard_b64encode(cPickle.dumps(
          [row.data for row in requests[0].objects],
          cPickle.HIGHEST_PROTOCOL
        ))
      }
    checkpointMgrInstanceMock.updateCheckpointAttributes. \
      assert_called_once_with(modelID, expectedCheckpointAttributes)

    # Verify number of samples passed to model
    self.assertEqual(modelInstanceMock.run.call_count, 2)

    # Verify emitted results
    requestObjects = requests[0].objects
    expectedResults = [
      ModelInferenceResult(
        rowID=requestObjects[0].rowID, status=0, anomalyScore=anomalyScore1),
      ModelInferenceResult(
        rowID=requestObjects[1].rowID, status=0, anomalyScore=anomalyScore2),
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  def testLoadFromFullAndSaveFull(
      self,
      modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):
    # Test loading from a full checkpoint and saving via full checkpoint; also
    # verify the inference path.
    modelID = "abc"

    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
    anomalyScores = [
      float(n) for n in xrange(
        model_runner._ModelArchiver._MAX_INCREMENTAL_CHECKPOINT_DATA_ROWS + 1)]

    modelInstanceMock = Mock(
      run=Mock(
        side_effect=[
          Mock(inferences=dict(anomalyScore=score)) for score in anomalyScores
        ]
      )
    )

    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadCheckpointAttributes. \
      return_value = (
        {
          model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
            ["1", "2", "3"],
        }
      )
    checkpointMgrInstanceMock.loadModelDefinition.return_value = (
      dict(inputSchema=inputRecordSchema))
    checkpointMgrInstanceMock.load.return_value = modelInstanceMock

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=n, data=[datetime.datetime.utcnow(), float(n)])
          for n in xrange(len(anomalyScores))
        ]
      )
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify loading of "inputSchema" metadata
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify loading of model
    checkpointMgrInstanceMock.load.assert_called_once_with(modelID)

    # Verify expected saving of model
    self.assertEqual(
      checkpointMgrInstanceMock.updateCheckpointAttributes.call_count, 0)

    expectedCheckpointAttributes = {
      model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
        [requests[0].batchID]
      }
    checkpointMgrInstanceMock.save.assert_called_once_with(
      modelID=modelID,
      model=modelInstanceMock,
      attributes=expectedCheckpointAttributes)

    # Verify number of samples passed to model
    self.assertEqual(modelInstanceMock.run.call_count, len(anomalyScores))

    # Verify emitted results
    requestObjects = requests[0].objects
    expectedResults = [
      ModelInferenceResult(rowID=rowid, status=0, anomalyScore=score)
      for rowid, score in zip(
        [obj.rowID for obj in requestObjects], anomalyScores)
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  def testLoadFromIncrementalAndSaveIncremental(
      self,
      modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):
    # Test loading from incremental checkpoint and saving via incremental
    # checkpoint; also verify the inference path.
    modelID = "abc"

    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
    # 2 for catch-up from data samples in checkpoint
    # plus 2 more from new input rows
    anomalyScore1 = 1.111111
    anomalyScore2 = 2.222222
    anomalyScore3 = 3.333333
    anomalyScore4 = 4.444444

    modelInstanceMock = Mock(
      run=Mock(
        side_effect=[
          # 2 results for catch-up from data samples in checkpoint
          # plus 2 more from new input rows
          Mock(inferences=dict(anomalyScore=anomalyScore1)),
          Mock(inferences=dict(anomalyScore=anomalyScore2)),
          Mock(inferences=dict(anomalyScore=anomalyScore3)),
          Mock(inferences=dict(anomalyScore=anomalyScore4))
        ]
      )
    )

    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    initialIncrementalSamples = [
      [datetime.datetime.utcnow(), -1.0],
      [datetime.datetime.utcnow(), -2.0]
    ]
    checkpointMgrInstanceMock.loadCheckpointAttributes. \
      return_value = (
        {
          model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
            ["1", "2", "3"],
          model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME:
            base64.standard_b64encode(cPickle.dumps(
              [data for data in initialIncrementalSamples],
              cPickle.HIGHEST_PROTOCOL
            ))
        }
      )
    checkpointMgrInstanceMock.loadModelDefinition.return_value = (
      dict(inputSchema=inputRecordSchema))
    checkpointMgrInstanceMock.load.return_value = modelInstanceMock

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=1, data=[datetime.datetime.utcnow(), 1.0]),
          ModelInputRow(rowID=2, data=[datetime.datetime.utcnow(), 2.0])])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify loading of "inputSchema" metadata
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify loading of model
    checkpointMgrInstanceMock.load.assert_called_once_with(modelID)

    # Verify expected saving of model
    self.assertEqual(checkpointMgrInstanceMock.save.call_count, 0)

    expectedCheckpointAttributes = {
      model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
        [requests[0].batchID],
      model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME:
        base64.standard_b64encode(cPickle.dumps(
          initialIncrementalSamples + [row.data for row in requests[0].objects],
          cPickle.HIGHEST_PROTOCOL
        ))
      }
    checkpointMgrInstanceMock.updateCheckpointAttributes. \
      assert_called_once_with(modelID, expectedCheckpointAttributes)

    # Verify number of samples passed to model
    self.assertEqual(modelInstanceMock.run.call_count,
                     len(initialIncrementalSamples) + len(requests[0].objects))

    # Verify emitted results
    requestObjects = requests[0].objects
    expectedResults = [
      ModelInferenceResult(
        rowID=requestObjects[0].rowID, status=0, anomalyScore=anomalyScore3),
      ModelInferenceResult(
        rowID=requestObjects[1].rowID, status=0, anomalyScore=anomalyScore4),
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  def testLoadFromIncrementalAndSaveFull(
      self,
      modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):
    # Test loading from incremental checkpoint and saving via full
    # checkpoint; also verify the inference path.
    modelID = "abc"

    inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
    # 2 for catch-up from data samples in checkpoint
    # and the rest from new input rows
    anomalyScores = [
      float(n) for n in xrange(
        2 + model_runner._ModelArchiver._MAX_INCREMENTAL_CHECKPOINT_DATA_ROWS)]

    modelInstanceMock = Mock(
      run=Mock(
        side_effect=[
          Mock(inferences=dict(anomalyScore=score)) for score in anomalyScores
        ]
      )
    )

    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    initialIncrementalSamples = [
      [datetime.datetime.utcnow(), -1.0],
      [datetime.datetime.utcnow(), -2.0]
    ]
    checkpointMgrInstanceMock.loadCheckpointAttributes. \
      return_value = (
        {
          model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
            ["1", "2", "3"],
          model_runner._ModelArchiver._INPUT_SAMPLES_SINCE_CHECKPOINT_ATTR_NAME:
            base64.standard_b64encode(cPickle.dumps(
              [data for data in initialIncrementalSamples],
              cPickle.HIGHEST_PROTOCOL
            ))
        }
      )
    checkpointMgrInstanceMock.loadModelDefinition.return_value = (
      dict(inputSchema=inputRecordSchema))
    checkpointMgrInstanceMock.load.return_value = modelInstanceMock

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=n, data=[datetime.datetime.utcnow(), float(n)])
          for n in xrange(
            model_runner._ModelArchiver._MAX_INCREMENTAL_CHECKPOINT_DATA_ROWS)
        ]
      )
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify loading of "inputSchema" metadata
    checkpointMgrInstanceMock.loadModelDefinition.assert_called_once_with(
      modelID)

    # Verify loading of model
    checkpointMgrInstanceMock.load.assert_called_once_with(modelID)

    # Verify expected saving of model
    self.assertEqual(
      checkpointMgrInstanceMock.updateCheckpointAttributes.call_count, 0)

    expectedCheckpointAttributes = {
      model_runner._ModelArchiver._BATCH_IDS_CHECKPOINT_ATTR_NAME:
        [requests[0].batchID]
      }
    checkpointMgrInstanceMock.save.assert_called_once_with(
      modelID=modelID,
      model=modelInstanceMock,
      attributes=expectedCheckpointAttributes)

    # Verify number of samples passed to model
    self.assertEqual(modelInstanceMock.run.call_count,
                     len(initialIncrementalSamples) + len(requests[0].objects))

    # Verify emitted results
    requestObjects = requests[0].objects
    expectedResults = [
      ModelInferenceResult(rowID=rowid, status=0, anomalyScore=score)
      for rowid, score in zip(
        [obj.rowID for obj in requestObjects], anomalyScores[2:])
    ]

    swapperMock.submitResults.assert_called_once_with(
      modelID=modelID, results=expectedResults)


  @patch.object(
    model_runner, "ModelFactory", autospec=True,
    create=Mock(spec_set=model_runner.ModelFactory.create))
  @patch.object(select, "select", autospec=True, return_value=((), (), ()))
  def testMultipleInputBatchesPerCheckpoint(
      self, selectMock, modelFactoryClassMock, modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = model_checkpoint_mgr.ModelNotFound

    requestsPerCheckpoint = 10
    with ConfigAttributePatch(
        modelSwapperConfig.CONFIG_NAME,
        modelSwapperConfig.baseConfigDir,
        (("model_runner", "target_requests_per_checkpoint",
          str(requestsPerCheckpoint)),)):
      modelID = "abc"
      modelConfig = "a"
      inferenceArgs = "b"
      inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
      anomalyScore1 = 1.111111
      dummyModelParams = dict(modelConfig=modelConfig,
                              inferenceArgs=inferenceArgs)

      # Configure ModelCheckpointMgr mock
      checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
      checkpointMgrInstanceMock.loadModelDefinition.return_value = dict(
        inputSchema=inputRecordSchema, modelParams=dummyModelParams)
      checkpointMgrInstanceMock.load.side_effect = (
        model_checkpoint_mgr.ModelNotFound)

      # Configure ModelFactory mock
      modelInstanceMock = Mock(run=Mock(
        return_value=Mock(inferences=dict(anomalyScore=anomalyScore1))))

      modelFactoryClassMock.create.return_value = modelInstanceMock

      # Prepare input requests for ModelRunner
      requests = [
        _ConsumedRequestBatch(
          batchID="foobar_%s" % (i,),
          ack=Mock(),
          objects=[ModelInputRow(rowID=i,
                                 data=[datetime.datetime.utcnow(), 1.0])])
        for i in xrange(requestsPerCheckpoint + requestsPerCheckpoint // 2)
      ]

      swapperMock = modelSwapperInterfaceClassMock.return_value
      swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

      mr = model_runner.ModelRunner(modelID=modelID)

      runnerThread = threading.Thread(target=mr.run)
      runnerThread.setDaemon(True)
      runnerThread.start()

      # It should stop almost immediately after mock-processing all requests
      runnerThread.join(timeout=5)
      self.assertFalse(runnerThread.isAlive())

      mr.close()
      swapperMock.close.assert_called_once_with()

      # Verify loading of model definition
      checkpointMgrInstanceMock.loadModelDefinition.assert_any_call(
        modelID)

      # Verify loading of model from params
      modelFactoryClassMock.create.assert_called_once_with(
        modelConfig=dummyModelParams["modelConfig"])

      # Verify expected saving of model
      totalCheckpoints = (len(requests) // requestsPerCheckpoint +
                          bool(len(requests) % requestsPerCheckpoint))
      self.assertEqual(checkpointMgrInstanceMock.save.call_count, 1)
      self.assertEqual(
        checkpointMgrInstanceMock.updateCheckpointAttributes.call_count,
        totalCheckpoints - 1)

      self.assertEqual(swapperMock.submitResults.call_count, len(requests))


  @patch.object(
    model_runner, "ModelFactory", autospec=True,
    create=Mock(spec_set=model_runner.ModelFactory.create))
  @patch.object(select, "select", autospec=True, return_value=((), (), ()))
  def testExactlyOnceProcessingOfInputBatches(
      self, selectMock, modelFactoryClassMock, modelCheckpointMgrClassMock,
      modelSwapperInterfaceClassMock):
    # With AMQP we can only achieve at-least-once-delivery guarantee, so
    # ModelRunner needs to filter out duplicate input batches for
    # exactly-once-execution

    requestsPerCheckpoint = 10
    with ConfigAttributePatch(
        modelSwapperConfig.CONFIG_NAME,
        modelSwapperConfig.baseConfigDir,
        (("model_runner", "target_requests_per_checkpoint",
          str(requestsPerCheckpoint)),)):
      modelID = "abc"
      modelConfig = "a"
      inferenceArgs = "b"
      inputRecordSchema = [FieldMetaInfo("c1", "float", "")]
      anomalyScore1 = 1.111111
      dummyModelParams = dict(modelConfig=modelConfig,
                              inferenceArgs=inferenceArgs)

      # Configure ModelCheckpointMgr mock
      checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
      checkpointMgrInstanceMock.loadModelDefinition.return_value = dict(
        inputSchema=inputRecordSchema, modelParams=dummyModelParams)
      checkpointMgrInstanceMock.load.side_effect = (
        model_checkpoint_mgr.ModelNotFound)

      checkpointAttributes = dict(
        attributes=None
      )
      checkpointMgrInstanceMock.loadCheckpointAttributes. \
        side_effect = model_checkpoint_mgr.ModelNotFound
      checkpointMgrInstanceMock.save.side_effect = (
        lambda modelID, model, attributes: (
          checkpointAttributes.__setitem__("attributes", attributes)))

      # Configure ModelFactory mock
      modelInstanceMock = Mock(run=Mock(
        return_value=Mock(inferences=dict(anomalyScore=anomalyScore1))))

      modelFactoryClassMock.create.return_value = modelInstanceMock

      # Prepare input requests for ModelRunner
      requests = [
        _ConsumedRequestBatch(
          batchID="foobar_%s" % (i,),
          ack=Mock(),
          objects=[ModelInputRow(rowID=i,
                                 data=[datetime.datetime.utcnow(), 1.0])])
        for i in xrange(requestsPerCheckpoint + requestsPerCheckpoint // 2)
        for _j in xrange(2)
      ]

      swapperMock = modelSwapperInterfaceClassMock.return_value
      swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

      mr = model_runner.ModelRunner(modelID=modelID)

      runnerThread = threading.Thread(target=mr.run)
      runnerThread.setDaemon(True)
      runnerThread.start()

      # It should stop almost immediately after mock-processing all requests
      runnerThread.join(timeout=5)
      self.assertFalse(runnerThread.isAlive())

      mr.close()
      swapperMock.close.assert_called_once_with()

      # Verify loading of model definition
      checkpointMgrInstanceMock.loadModelDefinition.assert_any_call(
        modelID)

      # Verify loading of model from params
      modelFactoryClassMock.create.assert_called_once_with(
        modelConfig=dummyModelParams["modelConfig"])

      # Verify expected saving of model
      totalCheckpoints = (
        (len(requests) // 2) // requestsPerCheckpoint +
        bool((len(requests) // 2) % requestsPerCheckpoint))

      self.assertEqual(checkpointMgrInstanceMock.save.call_count, 1)
      self.assertEqual(
        checkpointMgrInstanceMock.updateCheckpointAttributes.call_count,
        totalCheckpoints - 1)

      self.assertEqual(swapperMock.submitResults.call_count, len(requests) // 2)


  def testInferencePathWithModelNotFound(
    self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's inference-processing error plumbing by sending input
    # rows for a model that hasn't been defined, with mocking of input stream,
    # output, and model access logic.

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = model_checkpoint_mgr.ModelNotFound

    modelID = "abc_expected_not_found"

    # Configure ModelCheckpointMgr mock to raise ModelNotFound for any modelID
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadModelDefinition.side_effect = (
      model_checkpoint_mgr.ModelNotFound)
    checkpointMgrInstanceMock.load.side_effect = (
      model_checkpoint_mgr.ModelNotFound)

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=1, data=[datetime.datetime.utcnow(), 1.0]),
          ModelInputRow(rowID=2, data=[datetime.datetime.utcnow(), 2.0])])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 2)

    requestObjects = requests[0].objects

    self.assertEqual(outputResults[0].rowID, requestObjects[0].rowID)
    self.assertEqual(outputResults[0].status, htmengineerrno.ERR_NO_SUCH_MODEL)
    self.assertIn("Inference failed", outputResults[0].errorMessage)

    self.assertEqual(outputResults[1].rowID, requestObjects[1].rowID)
    self.assertEqual(outputResults[1].status, htmengineerrno.ERR_NO_SUCH_MODEL)
    self.assertIn("Inference failed", outputResults[1].errorMessage)


  def testInferencePathWithGenericError(
    self, modelCheckpointMgrClassMock, modelSwapperInterfaceClassMock):
    # Test ModelRunner's inference-processing error plumbing by sending input
    # rows and simulating a generic Exception, with mocking of input stream,
    # output, and model access logic.

    modelCheckpointMgrClassMock.return_value.loadCheckpointAttributes. \
      side_effect = model_checkpoint_mgr.ModelNotFound

    modelID = "abc"

    # Configure ModelCheckpointMgr mock to raise ModelNotFound for any modelID
    checkpointMgrInstanceMock = modelCheckpointMgrClassMock.return_value
    checkpointMgrInstanceMock.loadModelDefinition.side_effect = Exception(
      "From Generic Exception Error Test")
    checkpointMgrInstanceMock.load.side_effect = Exception(
      "From Generic Exception Error Test")

    # Prepare input requests for ModelRunner
    requests = [
      _ConsumedRequestBatch(
        batchID="foobar",
        ack=Mock(),
        objects=[
          ModelInputRow(rowID=1, data=[datetime.datetime.utcnow(), 1.0]),
          ModelInputRow(rowID=2, data=[datetime.datetime.utcnow(), 2.0])])
    ]

    swapperMock = modelSwapperInterfaceClassMock.return_value
    swapperMock.consumeRequests.return_value = _FakeConsumer(requests)

    # Create and run the model in background thread
    mr = model_runner.ModelRunner(modelID=modelID)

    runnerThread = threading.Thread(target=mr.run)
    runnerThread.setDaemon(True)
    runnerThread.start()

    # It should stop almost immediately after mock-processing the two requests
    runnerThread.join(timeout=5)
    self.assertFalse(runnerThread.isAlive())

    mr.close()
    swapperMock.close.assert_called_once_with()

    # Verify emitted results
    self.assertEqual(swapperMock.submitResults.call_count, 1)
    _, kwargs = swapperMock.submitResults.call_args
    outputModelID = kwargs["modelID"]
    outputResults = kwargs["results"]

    self.assertEqual(outputModelID, modelID)

    self.assertEqual(len(outputResults), 2)

    requestObjects = requests[0].objects

    self.assertEqual(outputResults[0].rowID, requestObjects[0].rowID)
    self.assertEqual(outputResults[0].status, htmengineerrno.ERR)
    self.assertIn("From Generic Exception Error Test",
                  outputResults[0].errorMessage)

    self.assertEqual(outputResults[1].rowID, requestObjects[1].rowID)
    self.assertEqual(outputResults[1].status, htmengineerrno.ERR)
    self.assertIn("From Generic Exception Error Test",
                  outputResults[1].errorMessage)



if __name__ == '__main__':
  unittest.main()
