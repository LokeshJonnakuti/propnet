import unittest
import os

import numpy as np
from monty import tempfile
import networkx as nx
import copy

from pymatgen.util.testing import PymatgenTest
from propnet.core.symbols import Symbol
from propnet.symbols import DEFAULT_SYMBOLS
from propnet.core.exceptions import SymbolConstraintError
from propnet.core.quantity import QuantityFactory, NumQuantity, ObjQuantity
from propnet.core.materials import Material
from propnet.core.graph import Graph
from propnet import ureg
from propnet.core.provenance import ProvenanceElement

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class QuantityTest(unittest.TestCase):
    def setUp(self):
        self.custom_symbol = Symbol("A", units='dimensionless')
        self.constraint_symbol = Symbol("A", constraint="A > 0",
                                        units='dimensionless')
        self.custom_object_symbol = Symbol("B", category='object')

    def test_quantity_construction(self):
        # From custom numerical symbol
        q = QuantityFactory.create_quantity(self.custom_symbol, 5.0)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertAlmostEqual(q.value.magnitude, 5.0)
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')
        # From canonical numerical symbol
        q = QuantityFactory.create_quantity("bulk_modulus", 100)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertEqual(q.value.magnitude, 100)
        self.assertEqual(q.value.units.format_babel(), 'gigapascal')
        # From custom symbol with constraint
        with self.assertRaises(SymbolConstraintError):
            QuantityFactory.create_quantity(self.constraint_symbol, -500)
        # From canonical symbol with constraint
        with self.assertRaises(SymbolConstraintError):
            QuantityFactory.create_quantity("bulk_modulus", -500)

        # Test np.array value with custom symbol
        value_list_array = [[1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9]]
        value_np_array = np.array(value_list_array)
        q = QuantityFactory.create_quantity(self.custom_symbol, value_np_array)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertTrue(np.allclose(q.value.magnitude, value_np_array))
        self.assertIsInstance(q.value.magnitude, np.ndarray)
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')

        # Test list coercion
        q = QuantityFactory.create_quantity(self.custom_symbol, value_list_array)
        self.assertIsInstance(q, NumQuantity)
        self.assertTrue(np.allclose(q.value.magnitude, value_list_array))
        self.assertIsInstance(q.value.magnitude, np.ndarray)
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')

        # From custom numerical symbol with uncertainty
        q = QuantityFactory.create_quantity(self.custom_symbol, 5.0, uncertainty=0.1)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertIsInstance(q.uncertainty, ureg.Quantity)
        self.assertAlmostEqual(q.value.magnitude, 5.0)
        self.assertAlmostEqual(q.uncertainty.magnitude, 0.1)
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')
        self.assertEqual(q.uncertainty.units.format_babel(), 'dimensionless')

        # From canonical numerical symbol with uncertainty
        q = QuantityFactory.create_quantity("bulk_modulus", 100, uncertainty=1)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertIsInstance(q.uncertainty, ureg.Quantity)
        self.assertEqual(q.value.magnitude, 100)
        self.assertEqual(q.uncertainty.magnitude, 1)
        self.assertEqual(q.value.units.format_babel(), 'gigapascal')
        self.assertEqual(q.uncertainty.units.format_babel(), 'gigapascal')

        # Test np.array value with custom symbol with uncertainty
        uncertainty_list_array = [[vv*0.05 for vv in v] for v in value_list_array]
        value_np_array = np.array(value_list_array)
        uncertainty_np_array = np.array(uncertainty_list_array)
        q = QuantityFactory.create_quantity(self.custom_symbol, value_np_array,
                                            uncertainty=uncertainty_np_array)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertIsInstance(q.uncertainty, ureg.Quantity)
        self.assertIsInstance(q.value.magnitude, np.ndarray)
        self.assertIsInstance(q.uncertainty.magnitude, np.ndarray)
        self.assertTrue(np.allclose(q.value.magnitude, value_np_array))
        self.assertTrue(np.allclose(q.uncertainty.magnitude, uncertainty_np_array))
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')
        self.assertEqual(q.uncertainty.units.format_babel(), 'dimensionless')

        # Test uncertainty list coercion
        q = QuantityFactory.create_quantity(self.custom_symbol, value_list_array,
                                            uncertainty=uncertainty_list_array)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertIsInstance(q.uncertainty, ureg.Quantity)
        self.assertIsInstance(q.value.magnitude, np.ndarray)
        self.assertIsInstance(q.uncertainty.magnitude, np.ndarray)
        self.assertTrue(np.allclose(q.value.magnitude, value_list_array))
        self.assertTrue(np.allclose(q.uncertainty.magnitude, uncertainty_np_array))
        self.assertEqual(q.value.units.format_babel(), 'dimensionless')
        self.assertEqual(q.uncertainty.units.format_babel(), 'dimensionless')

        # Test uncertainty NumQuantity coercion with unit conversion
        value_symbol = Symbol('E', units='joule')
        uncertainty_symbol = Symbol('u', units='calorie')
        incompatible_uncertainty_symbol = Symbol('u', units='meter')

        u = NumQuantity(uncertainty_symbol, 0.1)
        self.assertIsInstance(u, NumQuantity)
        self.assertIsInstance(u.value, ureg.Quantity)
        self.assertAlmostEqual(u.value.magnitude, 0.1)
        self.assertEqual(u.value.units.format_babel(), 'calorie')

        q = QuantityFactory.create_quantity(value_symbol, 126.1, uncertainty=u)
        self.assertIsInstance(q, NumQuantity)
        self.assertIsInstance(q.value, ureg.Quantity)
        self.assertIsInstance(q.uncertainty, ureg.Quantity)
        self.assertAlmostEqual(q.value.magnitude, 126.1)
        self.assertEqual(q.value.units.format_babel(), 'joule')
        self.assertAlmostEqual(q.uncertainty.magnitude, 0.4184)
        self.assertEqual(q.uncertainty.units.format_babel(), 'joule')

        u = NumQuantity(incompatible_uncertainty_symbol, 0.1)
        self.assertIsInstance(u, NumQuantity)
        self.assertIsInstance(u.value, ureg.Quantity)
        self.assertAlmostEqual(u.value.magnitude, 0.1)
        self.assertEqual(u.value.units.format_babel(), 'meter')

        with self.assertRaises(ValueError):
            q = QuantityFactory.create_quantity(value_symbol, 126.1, uncertainty=u)


        # From custom object symbol
        q = QuantityFactory.create_quantity(self.custom_object_symbol, 'test')
        self.assertIsInstance(q, ObjQuantity)
        self.assertIsInstance(q.value, str)
        self.assertEqual(q.value, 'test')

        # From canonical object symbol
        q = QuantityFactory.create_quantity("is_metallic", False)
        self.assertIsInstance(q, ObjQuantity)
        self.assertIsInstance(q.value, bool)
        self.assertEqual(q.value, False)

        # Test failure with invalid symbol name
        with self.assertRaises(ValueError):
            q = QuantityFactory.create_quantity("my_invalid_symbol_name", 1)

        # Test failure with incorrect type as symbol
        with self.assertRaises(TypeError):
            q = QuantityFactory.create_quantity(self.custom_symbol.as_dict(), 100)

        # Test failure on instantiating NumQuantity with non-numeric types
        with self.assertRaises(TypeError):
            value = 'test_string'
            q = NumQuantity(self.custom_symbol, value)
        with self.assertRaises(TypeError):
            value = np.array(['test', 'string', 'list'])
            q = NumQuantity(self.custom_symbol, value)

    def test_from_default(self):
        default = QuantityFactory.from_default('temperature')
        new_q = QuantityFactory.create_quantity('temperature', 300)
        # This test used to check for equality of the quantity objects,
        # but bc new definition of equality checks provenance, equality
        # between these objects fails (they originate from different models).
        # Now checking explicitly for symbol and value equality.
        self.assertEqual(default.symbol, new_q.symbol)
        self.assertEqual(default.value, new_q.value)
        default = QuantityFactory.from_default('relative_permeability')
        new_q = QuantityFactory.create_quantity("relative_permeability", 1)
        self.assertEqual(default.symbol, new_q.symbol)
        self.assertEqual(default.value, new_q.value)

    def test_from_weighted_mean(self):
        qlist = [QuantityFactory.create_quantity(self.custom_symbol, val, tags=['testing'])
                 for val in np.arange(1, 2.01, 0.01)]
        qagg = NumQuantity.from_weighted_mean(qlist)
        self.assertAlmostEqual(qagg.magnitude, 1.5)
        self.assertAlmostEqual(qagg.uncertainty, 0.2915475947422652)
        self.assertListEqual(qagg.tags, ['testing'])

        qlist.append(QuantityFactory.create_quantity(Symbol('B', units='dimensionless'), 15))
        with self.assertRaises(ValueError):
            qagg = NumQuantity.from_weighted_mean(qlist)

        with self.assertRaises(ValueError):
            qlist = [QuantityFactory.create_quantity(self.custom_object_symbol, str(val))
                     for val in np.arange(1, 2.01, 0.01)]
            qagg = NumQuantity.from_weighted_mean(qlist)

    def test_is_cyclic(self):
        b = Symbol("B", units="dimensionless")
        q_lowest_layer = QuantityFactory.create_quantity(self.custom_symbol, 1)
        q_middle_layer = QuantityFactory.create_quantity(b, 2,
                                                         provenance=ProvenanceElement(model='A_to_B',
                                                                                      inputs=[q_lowest_layer]))
        q_highest_layer = QuantityFactory.create_quantity(self.custom_symbol, 1,
                                                          provenance=ProvenanceElement(model='B_to_A',
                                                                                       inputs=[q_middle_layer]))
        self.assertFalse(q_lowest_layer.is_cyclic())
        self.assertFalse(q_middle_layer.is_cyclic())
        self.assertTrue(q_highest_layer.is_cyclic())

    def test_pretty_string(self):
        quantity = QuantityFactory.create_quantity('bulk_modulus', 100)
        self.assertEqual(quantity.pretty_string(3), "100 GPa")

        quantity = QuantityFactory.create_quantity('bulk_modulus', 100,
                                                   uncertainty=1.23456)
        self.assertEqual(quantity.pretty_string(3), "100\u00B11.235 GPa")

    def test_to(self):
        quantity = QuantityFactory.create_quantity('band_gap', 3.0, 'eV')
        new = quantity.to('joules')
        self.assertAlmostEqual(new.magnitude, 4.80652959e-19)
        self.assertEqual(new.units, 'joule')

        # Test with uncertainty
        quantity = QuantityFactory.create_quantity('band_gap', 3.0, 'eV',
                                                   uncertainty=0.1)
        new = quantity.to('joules')
        self.assertAlmostEqual(new.magnitude, 4.80652959e-19)
        self.assertEqual(new.units, 'joule')
        self.assertAlmostEqual(new.uncertainty.magnitude, 1.60217653e-20)
        self.assertEqual(new.uncertainty.units.format_babel(), 'joule')

    def test_properties(self):
        # Test units, magnitude
        q = QuantityFactory.create_quantity("bulk_modulus", 100)
        self.assertIsInstance(q, NumQuantity)
        self.assertEqual(q.units, "gigapascal")
        self.assertEqual(q.magnitude, 100)

        # Ensure non-pint values raise error with units, magnitude
        structure = PymatgenTest.get_structure('Si')
        q = QuantityFactory.create_quantity("structure", structure)
        self.assertIsInstance(q, ObjQuantity)

    def test_get_provenance_graph(self):
        g = Graph()
        qs = [QuantityFactory.create_quantity("bulk_modulus", 100),
              QuantityFactory.create_quantity("shear_modulus", 50),
              QuantityFactory.create_quantity("density", 8.96)]
        mat = Material(qs)
        evaluated = g.evaluate(mat)
        # TODO: this should be tested more thoroughly
        out = list(evaluated['vickers_hardness'])[0]
        with tempfile.ScratchDir('.'):
            out.draw_provenance_graph("out.png")
        pgraph = out.get_provenance_graph()
        end = list(evaluated['vickers_hardness'])[0]
        shortest_lengths = nx.shortest_path_length(pgraph, qs[0])
        self.assertEqual(shortest_lengths[end], 4)

        # This test is useful if one wants to actually make a plot, leaving
        # it in for now
        # from propnet.ext.matproj import MPRester
        # mpr = MPRester()
        # mat = mpr.get_material_for_mpid("mp-66")
        # evaluated = g.evaluate(mat)
        # out = list(evaluated['vickers_hardness'])[-1]
        # out.draw_provenance_graph("out.png", prog='dot')

    def test_nan_checking(self):
        A = Symbol('a', ['A'], ['A'], units='dimensionless', shape=1)
        B = Symbol('b', ['B'], ['B'], units='dimensionless', shape=[2, 2])
        C = Symbol('c', ['C'], ['C'], units='dimensionless', shape=1)
        D = Symbol('d', ['D'], ['D'], units='dimensionless', shape=[2, 2])
        E = Symbol('e', ['E'], ['E'], category='object', shape=1)

        scalar_quantity = QuantityFactory.create_quantity(A, float('nan'))
        non_scalar_quantity = QuantityFactory.create_quantity(B, [[1.0, float('nan')],
                                                                  [float('nan'), 1.0]])
        complex_scalar_quantity = QuantityFactory.create_quantity(C, complex('nan+nanj'))
        complex_non_scalar_quantity = QuantityFactory.create_quantity(D, [[complex(1.0), complex('nanj')],
                                                                          [complex('nan'), complex(1.0)]])

        self.assertTrue(scalar_quantity.contains_nan_value())
        self.assertTrue(non_scalar_quantity.contains_nan_value())
        self.assertTrue(complex_scalar_quantity.contains_nan_value())
        self.assertTrue(complex_non_scalar_quantity.contains_nan_value())

        scalar_quantity = QuantityFactory.create_quantity(A, 1.0)
        non_scalar_quantity = QuantityFactory.create_quantity(B, [[1.0, 2.0],
                                                                  [2.0, 1.0]])
        complex_scalar_quantity = QuantityFactory.create_quantity(C, complex('1+1j'))
        complex_non_scalar_quantity = QuantityFactory.create_quantity(D, [[complex(1.0), complex('5j')],
                                                                          [complex('5'), complex(1.0)]])

        self.assertFalse(scalar_quantity.contains_nan_value())
        self.assertFalse(non_scalar_quantity.contains_nan_value())
        self.assertFalse(complex_scalar_quantity.contains_nan_value())
        self.assertFalse(complex_non_scalar_quantity.contains_nan_value())

        non_numerical = QuantityFactory.create_quantity(E, 'test')
        self.assertFalse(non_numerical.contains_nan_value())

    def test_complex_and_imaginary_checking(self):
        A = Symbol('a', ['A'], ['A'], units='dimensionless', shape=1)
        B = Symbol('b', ['B'], ['B'], units='dimensionless', shape=[2, 2])
        # TODO: Revisit this when splitting quantity class into non-numerical and numerical
        C = Symbol('c', ['C'], ['C'], category='object', shape=1)

        real_float_scalar = QuantityFactory.create_quantity(A, 1.0)
        real_float_non_scalar = QuantityFactory.create_quantity(B, [[1.0, 1.0],
                                                                    [1.0, 1.0]])

        complex_scalar = QuantityFactory.create_quantity(A, complex(1 + 1j))
        complex_non_scalar = QuantityFactory.create_quantity(B, [[complex(1.0), complex(1.j)],
                                                                 [complex(1.j), complex(1.0)]])

        complex_scalar_zero_imaginary = QuantityFactory.create_quantity(A, complex(1.0))
        complex_non_scalar_zero_imaginary = QuantityFactory.create_quantity(B, [[complex(1.0), complex(1.0)],
                                                                                [complex(1.0), complex(1.0)]])

        complex_scalar_appx_zero_imaginary = QuantityFactory.create_quantity(A, complex(1.0 + 1e-10j))
        complex_non_scalar_appx_zero_imaginary = QuantityFactory.create_quantity(B,
                                                                                 [[complex(1.0), complex(1.0 + 1e-10j)],
                                                                                  [complex(1.0 + 1e-10j),
                                                                                   complex(1.0)]])

        non_numerical = QuantityFactory.create_quantity(C, 'test')

        # Test is_complex_type() with...
        # ...Quantity objects
        self.assertFalse(NumQuantity.is_complex_type(real_float_scalar))
        self.assertFalse(NumQuantity.is_complex_type(real_float_non_scalar))
        self.assertTrue(NumQuantity.is_complex_type(complex_scalar))
        self.assertTrue(NumQuantity.is_complex_type(complex_non_scalar))
        self.assertTrue(NumQuantity.is_complex_type(complex_scalar_zero_imaginary))
        self.assertTrue(NumQuantity.is_complex_type(complex_non_scalar_zero_imaginary))
        self.assertTrue(NumQuantity.is_complex_type(complex_scalar_appx_zero_imaginary))
        self.assertTrue(NumQuantity.is_complex_type(complex_non_scalar_appx_zero_imaginary))
        self.assertFalse(NumQuantity.is_complex_type(non_numerical))

        # ...primitive types
        self.assertFalse(NumQuantity.is_complex_type(1))
        self.assertFalse(NumQuantity.is_complex_type(1.))
        self.assertTrue(NumQuantity.is_complex_type(1j))
        self.assertFalse(NumQuantity.is_complex_type('test'))

        # ...np.array types
        self.assertFalse(NumQuantity.is_complex_type(np.array([1])))
        self.assertFalse(NumQuantity.is_complex_type(np.array([1.])))
        self.assertTrue(NumQuantity.is_complex_type(np.array([1j])))
        self.assertFalse(NumQuantity.is_complex_type(np.array(['test'])))

        # ...ureg Quantity objects
        self.assertFalse(NumQuantity.is_complex_type(ureg.Quantity(1)))
        self.assertFalse(NumQuantity.is_complex_type(ureg.Quantity(1.)))
        self.assertTrue(NumQuantity.is_complex_type(ureg.Quantity(1j)))
        self.assertFalse(NumQuantity.is_complex_type(ureg.Quantity([1])))
        self.assertFalse(NumQuantity.is_complex_type(ureg.Quantity([1.])))
        self.assertTrue(NumQuantity.is_complex_type(ureg.Quantity([1j])))

        # Check member functions
        self.assertFalse(real_float_scalar.contains_complex_type())
        self.assertFalse(real_float_scalar.contains_imaginary_value())
        self.assertFalse(real_float_non_scalar.contains_complex_type())
        self.assertFalse(real_float_non_scalar.contains_imaginary_value())

        self.assertTrue(complex_scalar.contains_complex_type())
        self.assertTrue(complex_scalar.contains_imaginary_value())
        self.assertTrue(complex_non_scalar.contains_complex_type())
        self.assertTrue(complex_non_scalar.contains_imaginary_value())

        self.assertTrue(complex_scalar_zero_imaginary.contains_complex_type())
        self.assertFalse(complex_scalar_zero_imaginary.contains_imaginary_value())
        self.assertTrue(complex_non_scalar_zero_imaginary.contains_complex_type())
        self.assertFalse(complex_non_scalar_zero_imaginary.contains_imaginary_value())

        self.assertTrue(complex_scalar_appx_zero_imaginary.contains_complex_type())
        self.assertFalse(complex_scalar_appx_zero_imaginary.contains_imaginary_value())
        self.assertTrue(complex_non_scalar_appx_zero_imaginary.contains_complex_type())
        self.assertFalse(complex_non_scalar_appx_zero_imaginary.contains_imaginary_value())

        self.assertFalse(non_numerical.contains_complex_type())
        self.assertFalse(non_numerical.contains_imaginary_value())

    def test_value_coercion(self):
        # Numerical value coercion
        q_int = QuantityFactory.create_quantity(self.custom_symbol, np.int64(5))
        q_float = QuantityFactory.create_quantity(self.custom_symbol, np.float64(5.0))
        q_complex = QuantityFactory.create_quantity(self.custom_symbol, np.complex64(5.0 + 1.j))

        self.assertTrue(isinstance(q_int.magnitude, int))
        self.assertTrue(isinstance(q_float.magnitude, float))
        self.assertTrue(isinstance(q_complex.magnitude, complex))

        q_int_uncertainty = QuantityFactory.create_quantity(self.custom_symbol, 5, uncertainty=np.int64(1))
        q_float_uncertainty = QuantityFactory.create_quantity(self.custom_symbol, 5.0, uncertainty=np.float64(1.0))
        q_complex_uncertainty = QuantityFactory.create_quantity(self.custom_symbol, 5.0 + 1j,
                                                                uncertainty=np.complex64(1.0 + 0.1j))

        self.assertTrue(isinstance(q_int_uncertainty.uncertainty.magnitude, int))
        self.assertTrue(isinstance(q_float_uncertainty.uncertainty.magnitude, float))
        self.assertTrue(isinstance(q_complex_uncertainty.uncertainty.magnitude, complex))

        # Object value coercion for primitive type
        q = QuantityFactory.create_quantity("is_metallic", 0)
        self.assertIsInstance(q, ObjQuantity)
        self.assertIsInstance(q.value, bool)
        self.assertEqual(q.value, False)

        # For custom class
        # Test failure if module not imported
        s = Symbol('A', category='object',
                   object_type='propnet.core.tests.external_test_class.ACoercibleClass')
        with self.assertRaises(NameError):
            q = QuantityFactory.create_quantity(s, 55)

        # Test coercion after module imported
        from propnet.core.tests.external_test_class import ACoercibleClass, AnIncoercibleClass
        q = QuantityFactory.create_quantity(s, 55)
        self.assertIsInstance(q, ObjQuantity)
        self.assertIsInstance(q.value, ACoercibleClass)

        # Test coercion failure by failed typecasting
        s = Symbol('A', category='object',
                   object_type='propnet.core.tests.external_test_class.AnIncoercibleClass')
        with self.assertRaises(TypeError):
            q = QuantityFactory.create_quantity(s, 55)

        # Test lack of coercion when no type specified
        q = QuantityFactory.create_quantity(self.custom_object_symbol, AnIncoercibleClass(5, 6))
        self.assertIsInstance(q, ObjQuantity)
        self.assertIsInstance(q.value, AnIncoercibleClass)

    def test_as_dict_from_dict(self):
        q = QuantityFactory.create_quantity(self.custom_symbol, 5, tags='experimental', uncertainty=1)
        d = q.as_dict()

        self.assertDictEqual(d, {"@module": "propnet.core.quantity",
                                 "@class": "NumQuantity",
                                 "value": 5,
                                 "units": "dimensionless",
                                 "provenance": q.provenance.as_dict(),
                                 "symbol_type": self.custom_symbol.as_dict(),
                                 "tags": ['experimental'],
                                 "uncertainty": (1, ())
                                 })

        q_from = QuantityFactory.from_dict(d)

        self.assertIsInstance(q_from, NumQuantity)
        self.assertEqual(q_from.symbol, q.symbol)
        self.assertEqual(q_from.value, q.value)
        self.assertEqual(q_from.units, q.units)
        self.assertEqual(q_from.tags, q.tags)
        self.assertEqual(q_from.uncertainty, q.uncertainty)
        self.assertEqual(q_from.provenance, q.provenance)

        q_from = NumQuantity.from_dict(d)

        self.assertIsInstance(q_from, NumQuantity)
        self.assertEqual(q_from.symbol, q.symbol)
        self.assertEqual(q_from.value, q.value)
        self.assertEqual(q_from.units, q.units)
        self.assertEqual(q_from.tags, q.tags)
        self.assertEqual(q_from.uncertainty, q.uncertainty)
        self.assertEqual(q_from.provenance, q.provenance)

        q = QuantityFactory.create_quantity(DEFAULT_SYMBOLS['debye_temperature'],
                                            500, tags='experimental', uncertainty=10)
        d = q.as_dict()

        self.assertDictEqual(d, {"@module": "propnet.core.quantity",
                                 "@class": "NumQuantity",
                                 "value": 500,
                                 "units": "kelvin",
                                 "provenance": q.provenance.as_dict(),
                                 "symbol_type": "debye_temperature",
                                 "tags": ['experimental'],
                                 "uncertainty": (10, (('kelvin', 1.0),))
                                 })

        q_from = QuantityFactory.from_dict(d)

        self.assertIsInstance(q_from, NumQuantity)
        self.assertEqual(q_from.symbol, q.symbol)
        self.assertEqual(q_from.value, q.value)
        self.assertEqual(q_from.units, q.units)
        self.assertEqual(q_from.tags, q.tags)
        self.assertEqual(q_from.uncertainty, q.uncertainty)
        self.assertEqual(q_from.provenance, q.provenance)

        q_from = NumQuantity.from_dict(d)

        self.assertIsInstance(q_from, NumQuantity)
        self.assertEqual(q_from.symbol, q.symbol)
        self.assertEqual(q_from.value, q.value)
        self.assertEqual(q_from.units, q.units)
        self.assertEqual(q_from.tags, q.tags)
        self.assertEqual(q_from.uncertainty, q.uncertainty)
        self.assertEqual(q_from.provenance, q.provenance)

    def test_equality(self):
        q1 = QuantityFactory.create_quantity(self.custom_symbol, 5, tags='experimental', uncertainty=1)
        q1_copy = copy.deepcopy(q1)
        q2 = QuantityFactory.create_quantity(self.custom_symbol, 6, tags='experimental', uncertainty=2)
        q3 = QuantityFactory.create_quantity(self.custom_symbol, 6, tags='experimental')
        q4 = QuantityFactory.create_quantity(Symbol('test_symbol', units='dimensionless'), 5)

        self.assertEqual(q1, q1_copy)
        self.assertEqual(q1.symbol, q1_copy.symbol)
        self.assertEqual(q1.value, q1_copy.value)
        self.assertEqual(q1.units, q1_copy.units)
        self.assertEqual(q1.tags, q1_copy.tags)
        self.assertEqual(q1.uncertainty, q1_copy.uncertainty)
        self.assertEqual(q1.provenance, q1_copy.provenance)

        self.assertNotEqual(q1, q2)
        self.assertNotEqual(q2, q3)

        self.assertTrue(q1.has_eq_value_to(q1_copy))
        self.assertTrue(q1.has_eq_value_to(q4))
        self.assertFalse(q1.has_eq_value_to(q2))
        self.assertTrue(q2.has_eq_value_to(q3))
        with self.assertRaises(TypeError):
            q1.has_eq_value_to(5)

        q_ev = QuantityFactory.create_quantity('band_gap', 1, units='eV')
        q_ev_slightly_bigger = QuantityFactory.create_quantity('band_gap', 1 + 1e-8, units='eV')
        q_ev_too_big = QuantityFactory.create_quantity('band_gap', 1 + 1e-4, units='eV')
        q_ev_zero = QuantityFactory.create_quantity('band_gap', 0, units='eV')
        q_ev_close_to_zero = QuantityFactory.create_quantity('band_gap', 1e-8, units='eV')
        q_ev_really_small_1 = QuantityFactory.create_quantity('band_gap', 1e-12, units='eV')
        q_ev_really_small_2 = QuantityFactory.create_quantity('band_gap', 1e-15, units='eV')

        q_hartree = q_ev.to('hartree')  # Comparable magnitude to eV

        q_joule = q_ev.to('joule')
        q_joule_slightly_bigger = q_ev_slightly_bigger.to('joule')
        q_joule_too_big = q_ev_too_big.to('joule')
        q_joule_zero = q_ev_zero.to('joule')
        q_joule_close_to_zero = q_ev_close_to_zero.to('joule')

        self.assertTrue(NumQuantity.values_are_close(q_ev.value, q_hartree.value))
        self.assertTrue(NumQuantity.values_are_close(q_ev.value, q_ev_slightly_bigger.value))
        self.assertFalse(NumQuantity.values_are_close(q_ev.value, q_ev_too_big.value))
        self.assertTrue(NumQuantity.values_are_close(q_ev_zero.value, q_ev_close_to_zero.value))

        self.assertTrue(NumQuantity.values_are_close(q_ev_close_to_zero.value, q_ev_zero.value))
        self.assertTrue(NumQuantity.values_are_close(q_ev_really_small_1.value, q_ev_really_small_2.value))

        self.assertTrue(NumQuantity.values_are_close(q_ev.value, q_joule.value))
        self.assertTrue(NumQuantity.values_are_close(q_joule.value, q_joule_slightly_bigger.value))
        self.assertFalse(NumQuantity.values_are_close(q_joule.value, q_joule_too_big.value))
        self.assertTrue(NumQuantity.values_are_close(q_joule_zero.value, q_joule_close_to_zero.value))

        fields = list(q1.__dict__.keys())

        # This is to check to see if we modified the fields in the object, in case we need to add
        # to our equality statement
        self.assertListEqual(fields, ['_value', '_symbol_type',
                                      '_tags', '_provenance',
                                      '_internal_id', '_uncertainty'])

