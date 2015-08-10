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

import uuid

import unittest

from htmengine.model_checkpoint_mgr.model_checkpoint_mgr import (
    ModelCheckpointMgr, ModelNotFound, ModelAlreadyExists)
from htmengine.model_checkpoint_mgr.model_checkpoint_test_utils import (
    ModelCheckpointStoragePatch)
from nupic.frameworks.opf.modelfactory import ModelFactory


# Disable warning: Access to a protected member
# pylint: disable=W0212

# Disable warning: Method could be a function
# pylint: disable=R0201



@ModelCheckpointStoragePatch()
class TestModelCheckpointMgr(unittest.TestCase):


  def testStorageDirOverrideViaEnvironmentVariable(self):
    with ModelCheckpointStoragePatch() as storagePatch:
      checkpointMgr = ModelCheckpointMgr()

      tempModelCheckpointDir = storagePatch.tempModelCheckpointDir
      modelEntryDir = checkpointMgr._getModelDir(modelID="abc", mustExist=False)

    self.assertIn(tempModelCheckpointDir, modelEntryDir)


  def testRemoveAndGetModelIDs(self):
    """
    Test getModelIDs and remove methods
    """
    checkpointMgr = ModelCheckpointMgr()

    # Should be empty at first
    ids = checkpointMgr.getModelIDs()
    self.assertListEqual(ids, [])


    # Create some checkpoints using meta info
    expModelIDs = [uuid.uuid1().hex, uuid.uuid1().hex]
    expModelIDs.sort()
    for modelID in expModelIDs:
      checkpointMgr.define(modelID, definition={'a':1})

    ids = checkpointMgr.getModelIDs()
    ids.sort()
    self.assertListEqual(ids, expModelIDs)


    # Delete one of them
    checkpointMgr.remove(expModelIDs[0])
    expModelIDs.remove(expModelIDs[0])

    ids = checkpointMgr.getModelIDs()
    ids.sort()
    self.assertListEqual(ids, expModelIDs)


    # Delete all of them
    for modelID in expModelIDs:
      checkpointMgr.remove(modelID)
    ids = checkpointMgr.getModelIDs()
    self.assertListEqual(ids, [])


    # If we try and delete a non-existing model, should get an exception
    self.assertRaises(ModelNotFound, checkpointMgr.remove, "IDx")


  def testRemoveAll(self):
    """
    Test removeAll
    """
    checkpointMgr = ModelCheckpointMgr()

    # Should be empty at first
    ids = checkpointMgr.getModelIDs()
    self.assertSequenceEqual(ids, [])


    # Create some checkpoints using meta info
    expModelIDs = [uuid.uuid1().hex, uuid.uuid1().hex]
    expModelIDs.sort()
    for modelID in expModelIDs:
      checkpointMgr.define(modelID, definition={'a':1})

    ids = checkpointMgr.getModelIDs()
    self.assertItemsEqual(ids, expModelIDs)

    # Delete checkpoint store
    ModelCheckpointMgr.removeAll()

    ids = checkpointMgr.getModelIDs()
    self.assertSequenceEqual(ids, [])


  def testDefineModel(self):
    """ Test support for defining a model """
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex
    modelDefinition = {'a': 1, 'b': 2, 'c':3}

    # Calling loadModelDefinition when the model doesn't exist should raise
    #  ModelNotFound
    self.assertRaises(ModelNotFound, checkpointMgr.loadModelDefinition, modelID)

    # Define the model
    checkpointMgr.define(modelID, definition=modelDefinition)

    # Load model definition and verify integrity of model definition object
    retrievedModelDefinition = checkpointMgr.loadModelDefinition(modelID)
    self.assertDictEqual(retrievedModelDefinition, modelDefinition)


  def _getModelParams(self, variantName="foo"):
    """ Return model params dict that can be used to construct a model

    variantName: A string embedded into the information returned from
                  model.getFieldInfo(). This can be used to make each
                  model params uniquely identifiable for testing
    """


    return {
      # Type of model that the rest of these parameters apply to.
      'model': "CLA",

      # Version that specifies the format of the config.
      'version': 1,

      # Intermediate variables used to compute fields in modelParams and also
      # referenced from the control section.
      'aggregationInfo': {'days': 0,
          'fields': [('consumption', 'sum')],
          'hours': 1,
          'microseconds': 0,
          'milliseconds': 0,
          'minutes': 0,
          'months': 0,
          'seconds': 0,
          'weeks': 0,
          'years': 0},

      'predictAheadTime': None,

      # Model parameter dictionary.
      'modelParams': {
          # The type of inference that this model will perform
          'inferenceType': 'TemporalMultiStep',

          'sensorParams': {
              # Sensor diagnostic output verbosity control;
              # if > 0: sensor region will print out on screen what it's sensing
              # at each step 0: silent; >=1: some info; >=2: more info;
              # >=3: even more info (see compute() in py/regions/RecordSensor.py
              # )
              'verbosity' : 0,

              # Example:
              #     dsEncoderSchema = [
              #       DeferredDictLookup('__field_name_encoder'),
              #     ],
              #
              # (value generated from DS_ENCODER_SCHEMA)
              'encoders': {'consumption': {
                                     'clipInput': True,
                                     'fieldname': u'consumption',
                                     'n': 100,
                                     'name': u'consumption',
                                     'type': 'AdaptiveScalarEncoder',
                                     'w': 21},
                  'timestamp_dayOfWeek': {
                                             'dayOfWeek': (21, 1),
                                             'fieldname': u'timestamp',
                                             'name': u'timestamp_dayOfWeek',
                                             'type': 'DateEncoder'},
                  'timestamp_timeOfDay': {
                                             'fieldname': u'timestamp',
                                             'name': u'timestamp_timeOfDay',
                                             'timeOfDay': (21, 1),
                                             'type': 'DateEncoder'},
                  variantName: {
                                           'fieldname': variantName,
                                           'name': variantName,
                                           'type': 'AdaptiveScalarEncoder',
                                           'n': 100,
                                           'w': 21}},


              # A dictionary specifying the period for automatically-generated
              # resets from a RecordSensor;
              #
              # None = disable automatically-generated resets (also disabled if
              # all of the specified values evaluate to 0).
              # Valid keys is the desired combination of the following:
              #   days, hours, minutes, seconds, milliseconds, microseconds,
              #   weeks
              #
              # Example for 1.5 days: sensorAutoReset = dict(days=1,hours=12),
              #
              # (value generated from SENSOR_AUTO_RESET)
              'sensorAutoReset' : None,
          },

          'spEnable': False,

          'spParams': {},

          # Controls whether TP is enabled or disabled;
          # TP is necessary for making temporal predictions, such as predicting
          # the next inputs.  Without TP, the model is only capable of
          # reconstructing missing sensor inputs (via SP).
          'tpEnable' : False,

          'tpParams': {},

          'clParams': {
              'regionName' : 'CLAClassifierRegion',

              # Classifier diagnostic output verbosity control;
              # 0: silent; [1..6]: increasing levels of verbosity
              'clVerbosity' : 0,

              # This controls how fast the classifier learns/forgets. Higher
              # values  make it adapt faster and forget older patterns faster.
              'alpha': 0.0001,

              # This is set after the call to updateConfigFromSubConfig and is
              # computed from the aggregationInfo and predictAheadTime.
              'steps': '1,5',
          },

          'trainSPNetOnlyIfRequested': False,
      },
    }


  def testModelCheckpointSaveAndLoadSupport(self):
    """ Test saving and loading models """
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex

    # Calling load when the model doesn't exist should raise an
    #  exception
    self.assertRaises(ModelNotFound, checkpointMgr.load, modelID)

    # Create a model that we can save
    originalModel = ModelFactory.create(self._getModelParams("variant1"))

    # Save it
    checkpointMgr.define(modelID, definition=dict(a=1, b=2))

    # Attempting to load model that hasn't been checkpointed should raise
    # ModelNotFound
    self.assertRaises(ModelNotFound, checkpointMgr.load, modelID)

    # Save the checkpoint
    checkpointMgr.save(modelID, originalModel, attributes="attributes1")

    # Load the model from the saved checkpoint
    loadedModel = checkpointMgr.load(modelID)
    self.assertEqual(str(loadedModel.getFieldInfo()),
                     str(originalModel.getFieldInfo()))
    del loadedModel
    del originalModel

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     "attributes1")

    # Make sure we can replace an existing model
    model2 = ModelFactory.create(self._getModelParams("variant2"))
    checkpointMgr.save(modelID, model2, attributes="attributes2")
    model = checkpointMgr.load(modelID)
    self.assertEqual(str(model.getFieldInfo()), str(model2.getFieldInfo()))

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     "attributes2")

    model3 = ModelFactory.create(self._getModelParams("variant3"))
    checkpointMgr.save(modelID, model3, attributes="attributes3")
    model = checkpointMgr.load(modelID)
    self.assertEqual(str(model.getFieldInfo()), str(model3.getFieldInfo()))

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     "attributes3")

    # Simulate a failure during checkpointing and make sure it doesn't mess
    #  up our already existing checkpoint
    try:
      checkpointMgr.save(modelID, "InvalidModel", attributes="attributes4")
    except AttributeError:
      pass
    model = checkpointMgr.load(modelID)
    self.assertEqual(str(model.getFieldInfo()), str(model3.getFieldInfo()))

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     "attributes3")


  def testUpdateCheckpointAttributesNoModelEntry(self):
    """ When a model entry doesn't exist, calling  updateCheckpointAttributes
    should raise ModelNotFound
    """
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex

    # Calling updateCheckpointAttributes when the model entry doesn't exist
    # should raise an exception
    with self.assertRaises(ModelNotFound):
      checkpointMgr.updateCheckpointAttributes(modelID, "attributes")


  def testUpdateCheckpointAttributesWithNoModeCheckpointException(self):
    """ When a model entry exists, but a checkpoint hasn't been saved yet,
    calling  updateCheckpointAttributes should raise ModelNotFound
    """
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex

    # Save its definition
    checkpointMgr.define(modelID, definition=dict(a=1, b=2))

    with self.assertRaises(ModelNotFound):
      checkpointMgr.updateCheckpointAttributes(modelID, "attributes")


  def testUpdateCheckpointAttributes(self):
    """ Test updateCheckpointAttributes """
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex

    # Create a model that we can save
    originalModel = ModelFactory.create(self._getModelParams("variant1"))

    # Save its definition
    checkpointMgr.define(modelID, definition=dict(a=1, b=2))

    # Save the checkpoint
    checkpointMgr.save(modelID, originalModel, attributes="attributes1")

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     "attributes1")

    # Update model checkpoint attribes
    newAttributes = dict(this=[1, 2, 3], that="abc")
    checkpointMgr.updateCheckpointAttributes(modelID, newAttributes)

    self.assertEqual(checkpointMgr.loadCheckpointAttributes(modelID),
                     newAttributes)


  def testCloneModelFromNonExistentSourceRaisesModelNotFound(self):
    checkpointMgr = ModelCheckpointMgr()

    # Create the source model with meta-info only
    modelID = uuid.uuid1().hex
    destModelID = uuid.uuid1().hex

    # Calling clone when the source model archive doesn't exist should
    # raise an exception
    with self.assertRaises(ModelNotFound):
      checkpointMgr.clone(modelID, destModelID)

    # Let's try it again to make sure that the first attempt did not create
    # unwanted side-effect
    with self.assertRaises(ModelNotFound):
      checkpointMgr.clone(modelID, destModelID)


  def testCloneModelWithDefinitionOnly(self):
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex
    destModelID = uuid.uuid1().hex

    # Create the source model with meta-info only (no checkpoint)
    modelDef = {'a': 1, 'b': 2, 'c':3}
    checkpointMgr.define(modelID, modelDef)

    # Clone the source model
    checkpointMgr.clone(modelID, destModelID)

    # Verify that the destination model's definition is the same as the
    # source model's
    destModelDef = checkpointMgr.loadModelDefinition(destModelID)
    self.assertDictEqual(destModelDef, modelDef)

    # Calling load when the model checkpoint doesn't exist should raise an
    #  exception
    with self.assertRaises(ModelNotFound):
      checkpointMgr.load(destModelID)

    # Calling clone when the destination model archive already exists should
    # raise an exception
    with self.assertRaises(ModelAlreadyExists):
      checkpointMgr.clone(modelID, destModelID)


  def testCloneModelWithCheckpoint(self):
    checkpointMgr = ModelCheckpointMgr()

    modelID = uuid.uuid1().hex
    destModelID = uuid.uuid1().hex

    # Create the source model with meta-info only (no checkpoint)
    modelDef = {'a': 1, 'b': 2, 'c':3}
    checkpointMgr.define(modelID, modelDef)

    # Create a model that we can clone
    model1 = ModelFactory.create(self._getModelParams("variant1"))
    checkpointMgr.save(modelID, model1, attributes="attributes1")

    # Clone the source model
    checkpointMgr.clone(modelID, destModelID)

    # Discard the source model checkpoint
    checkpointMgr.remove(modelID)

    # Verify that the destination model's definition is the same as the
    # source model's
    destModelDef = checkpointMgr.loadModelDefinition(destModelID)
    self.assertDictEqual(destModelDef, modelDef)

    # Verify that the destination model's attributes match the source's
    attributes = checkpointMgr.loadCheckpointAttributes(destModelID)
    self.assertEqual(attributes, "attributes1")

    # Attempt to load the cloned model from checkpoint
    model = checkpointMgr.load(destModelID)
    self.assertEqual(str(model.getFieldInfo()), str(model1.getFieldInfo()))



if __name__ == '__main__':
  unittest.main()
