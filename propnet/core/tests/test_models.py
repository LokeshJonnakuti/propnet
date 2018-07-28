import unittest
import os

import math

from glob import glob

import propnet.models as models

from propnet.models import DEFAULT_MODEL_NAMES, DEFAULT_MODEL_DICT, DEFAULT_MODELS
from propnet.symbols import DEFAULT_SYMBOL_TYPE_NAMES
from propnet.core.models import Model, PyModuleModel, PyModel, EquationModel
from propnet.core.symbols import *


# TODO: separate these into specific tests of model functionality
#       and validation of default models
class ModelTest(unittest.TestCase):

    def test_instantiate_all_models(self):
        models_to_test = []
        for model_name in DEFAULT_MODEL_NAMES:
            try:
                model = DEFAULT_MODEL_DICT.get(model_name)
                models_to_test.append(model_name)
            except Exception as e:
                self.fail('Failed to load model {}: {}'.format(model_name, e))

    def test_model_formatting(self):
        # TODO: clean up tests (self.assertNotNone), test reference format too
        for m in DEFAULT_MODELS:
            self.assertIsNotNone(m.name)
            self.assertIsNotNone(m.categories)
            self.assertIsNotNone(m.description)
            self.assertIsNotNone(m.symbol_property_map)
            self.assertTrue(isinstance(m.symbol_property_map, dict))
            self.assertTrue(len(m.symbol_property_map.keys()) > 0)
            for key in m.symbol_property_map.keys():
                self.assertTrue(isinstance(key, str),
                                'Invalid symbol_property_map key: ' + str(key))
                self.assertTrue(isinstance(m.symbol_property_map[key], str) and
                                m.symbol_property_map[key] in DEFAULT_SYMBOL_TYPE_NAMES)
            self.assertTrue(m.connections is not None and isinstance(m.connections, list)
                            and len(m.connections) > 0)
            for item in m.connections:
                self.assertIsNotNone(item)
                self.assertTrue(isinstance(item, dict))
                self.assertTrue('inputs' in item.keys())
                self.assertTrue('outputs' in item.keys())
                self.assertIsNotNone(item['inputs'])
                self.assertIsNotNone(item['outputs'])
                self.assertTrue(isinstance(item['inputs'], list))
                self.assertTrue(isinstance(item['outputs'], list))
                self.assertTrue(len(item['inputs']) > 0)
                self.assertTrue(len(item['outputs']) > 0)
                for in_symb in item['inputs']:
                    self.assertIsNotNone(in_symb)
                    self.assertTrue(isinstance(in_symb, str))
                    self.assertTrue(in_symb in m.symbol_property_map.keys())
                for out_symb in item['outputs']:
                    self.assertIsNotNone(out_symb)
                    self.assertIsNotNone(isinstance(out_symb, str))
                    self.assertTrue(out_symb in m.symbol_property_map.keys())

    def test_validate_all_models(self):
        for model in DEFAULT_MODELS:
            self.assertTrue(model.validate_from_preset_test())

    def test_unit_handling(self):
        """
        Tests unit handling with a simple model that calculates the area of a rectangle as the
        product of two lengths.

        In this case the input lengths are provided in centimeters and meters.
        Tests whether the input units are properly coerced into canonical types.
        Tests whether the output units are properly set.
        Tests whether the model returns as predicted.
        Returns:
            None
        """
        L = Symbol('l', ['L'], ['L'], units=[1.0, [['centimeter', 1.0]]], shape=[1])
        A = Symbol('a', ['A'], ['A'], units=[1.0, [['centimeter', 2.0]]], shape=[1])
        get_area_config = {
            'name': 'area',
            'connections': [{'inputs': ['l1', 'l2'], 'outputs': ['a']}],
            'equations': ['a - l1 * l2'],
            'unit_map': {'l1': "cm", "l2": "cm", 'a': "cm^2"}
        }
        model = EquationModel(**get_area_config)
        out = model.evaluate({'l1': 1 * ureg.Quantity.from_tuple([1.0, [['meter', 1.0]]]),
                              'l2': 2 * L.units})

        self.assertTrue(math.isclose(out['a'].magnitude, 200.0))
        self.assertTrue(out['a'].units == A.units)

    def test_example_code_helper(self):

        example_model = DEFAULT_MODEL_DICT['semiempirical_mobility']

        # TODO: this is ugly, any way to fix it?
        example_code = """
from propnet.models import load_default_model

K = 64
m_e = 0.009

model = load_default_model("semiempirical_mobility")
model.evaluate({
\t'K': K
\t'm_e': m_e
})  # returns {'mu_e': 8994.92312225673}
"""
        self.assertEqual(example_model.example_code, example_code)
