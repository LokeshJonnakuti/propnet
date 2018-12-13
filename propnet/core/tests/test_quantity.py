import unittest
import os

import numpy as np
from monty import tempfile
import networkx as nx

from pymatgen.util.testing import PymatgenTest
from propnet.core.symbols import Symbol
from propnet.core.exceptions import SymbolConstraintError
from propnet.core.quantity import Quantity, NumQuantity, ObjQuantity
from propnet.core.materials import Material
from propnet.core.graph import Graph
from propnet.core.provenance import ProvenanceElement
from propnet import ureg


TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class QuantityTest(unittest.TestCase):
    def setUp(self):
        self.custom_symbol = Symbol("A", units='dimensionless')
        self.constraint_symbol = Symbol("A", constraint="A > 0",
                                        units='dimensionless')

    def test_quantity_construction(self):
        # From custom symbol
        q = Quantity.factory(self.custom_symbol, 5.0)
        self.assertEqual(q.value.magnitude, 5.0)
        self.assertIsInstance(q.value, ureg.Quantity)
        # From canonical symbol
        q = Quantity.factory("bulk_modulus", 100)
        self.assertEqual(q.value.magnitude, 100)
        # From custom symbol with constraint
        with self.assertRaises(SymbolConstraintError):
            Quantity.factory(self.constraint_symbol, -500)
        # From canonical symbol with constraint
        with self.assertRaises(SymbolConstraintError):
            Quantity.factory("bulk_modulus", -500)

    def test_from_default(self):
        default = Quantity.from_default('temperature')
        self.assertEqual(default, Quantity.factory('temperature', 300))
        default = Quantity.from_default('relative_permeability')
        self.assertEqual(default, Quantity.factory("relative_permeability", 1))

    def test_from_weighted_mean(self):
        qlist = [Quantity.factory(self.custom_symbol, val)
                 for val in np.arange(1, 2.01, 0.01)]
        qagg = NumQuantity.from_weighted_mean(qlist)
        self.assertAlmostEqual(qagg.magnitude, 1.5)
        self.assertAlmostEqual(qagg.uncertainty, 0.2915475947422652)

    def test_is_cyclic(self):
        # Simple test
        pass

    def test_pretty_string(self):
        quantity = Quantity.factory('bulk_modulus', 100)
        self.assertEqual(quantity.pretty_string(3), "100 GPa")

    def test_to(self):
        quantity = Quantity.factory('band_gap', 3.0, 'eV')
        new = quantity.to('joules')
        self.assertEqual(new.magnitude, 4.80652959e-19)
        self.assertEqual(new.units, 'joule')

    def test_properties(self):
        # Test units, magnitude
        q = Quantity.factory("bulk_modulus", 100)
        self.assertIsInstance(q, NumQuantity)
        self.assertEqual(q.units, "gigapascal")
        self.assertEqual(q.magnitude, 100)

        # Ensure non-pint values raise error with units, magnitude
        structure = PymatgenTest.get_structure('Si')
        q = Quantity.factory("structure", structure)
        self.assertIsInstance(q, ObjQuantity)

    def test_get_provenance_graph(self):
        g = Graph()
        qs = [Quantity.factory("bulk_modulus", 100),
              Quantity.factory("shear_modulus", 50),
              Quantity.factory("density", 8.96)]
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

        scalar_quantity = Quantity.factory(A, float('nan'))
        non_scalar_quantity = Quantity.factory(B, [[1.0, float('nan')],
                                           [float('nan'), 1.0]])
        complex_scalar_quantity = Quantity.factory(C, complex('nan+nanj'))
        complex_non_scalar_quantity = Quantity.factory(D, [[complex(1.0), complex('nanj')],
                                                   [complex('nan'), complex(1.0)]])

        self.assertTrue(scalar_quantity.contains_nan_value())
        self.assertTrue(non_scalar_quantity.contains_nan_value())
        self.assertTrue(complex_scalar_quantity.contains_nan_value())
        self.assertTrue(complex_non_scalar_quantity.contains_nan_value())

        scalar_quantity = Quantity.factory(A, 1.0)
        non_scalar_quantity = Quantity.factory(B, [[1.0, 2.0],
                                           [2.0, 1.0]])
        complex_scalar_quantity = Quantity.factory(C, complex('1+1j'))
        complex_non_scalar_quantity = Quantity.factory(D, [[complex(1.0), complex('5j')],
                                                   [complex('5'), complex(1.0)]])

        self.assertFalse(scalar_quantity.contains_nan_value())
        self.assertFalse(non_scalar_quantity.contains_nan_value())
        self.assertFalse(complex_scalar_quantity.contains_nan_value())
        self.assertFalse(complex_non_scalar_quantity.contains_nan_value())

        non_numerical = Quantity.factory(E, 'test')
        self.assertFalse(non_numerical.contains_nan_value())

    def test_complex_and_imaginary_checking(self):
        A = Symbol('a', ['A'], ['A'], units='dimensionless', shape=1)
        B = Symbol('b', ['B'], ['B'], units='dimensionless', shape=[2, 2])
        # TODO: Revisit this when splitting quantity class into non-numerical and numerical
        C = Symbol('c', ['C'], ['C'], category='object', shape=1)

        real_float_scalar = Quantity.factory(A, 1.0)
        real_float_non_scalar = Quantity.factory(B, [[1.0, 1.0],
                                             [1.0, 1.0]])

        complex_scalar = Quantity.factory(A, complex(1+1j))
        complex_non_scalar = Quantity.factory(B, [[complex(1.0), complex(1.j)],
                                          [complex(1.j), complex(1.0)]])

        complex_scalar_zero_imaginary = Quantity.factory(A, complex(1.0))
        complex_non_scalar_zero_imaginary = Quantity.factory(B, [[complex(1.0), complex(1.0)],
                                                         [complex(1.0), complex(1.0)]])

        complex_scalar_appx_zero_imaginary = Quantity.factory(A, complex(1.0+1e-10j))
        complex_non_scalar_appx_zero_imaginary = Quantity.factory(B, [[complex(1.0), complex(1.0+1e-10j)],
                                                              [complex(1.0+1e-10j), complex(1.0)]])

        non_numerical = Quantity.factory(C, 'test')

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

    def test_numpy_scalar_conversion(self):
        # From custom symbol
        q_int = Quantity.factory(self.custom_symbol, np.int64(5))
        q_float = Quantity.factory(self.custom_symbol, np.float64(5.0))
        q_complex = Quantity.factory(self.custom_symbol, np.complex64(5.0+1.j))

        self.assertTrue(isinstance(q_int.magnitude, int))
        self.assertTrue(isinstance(q_float.magnitude, float))
        self.assertTrue(isinstance(q_complex.magnitude, complex))

        q_int_uncertainty = Quantity.factory(self.custom_symbol, 5, uncertainty=np.int64(1))
        q_float_uncertainty = Quantity.factory(self.custom_symbol, 5.0, uncertainty=np.float64(1.0))
        q_complex_uncertainty = Quantity.factory(self.custom_symbol, 5.0+1j, uncertainty=np.complex64(1.0 + 0.1j))

        self.assertTrue(isinstance(q_int_uncertainty.uncertainty.magnitude, int))
        self.assertTrue(isinstance(q_float_uncertainty.uncertainty.magnitude, float))
        self.assertTrue(isinstance(q_complex_uncertainty.uncertainty.magnitude, complex))

    def test_as_dict_from_dict(self):
        q = Quantity.factory(self.custom_symbol, 5, tags='experimental', uncertainty=1)
        d = q.as_dict()
        d_storage = q.as_dict(for_storage=True)
        d_storage_omit = q.as_dict(for_storage=True, omit_value=True)
        self.assertEqual(d, {"@module": "propnet.core.quantity",
                             "@class": "Quantity",
                             "value": 5,
                             "units": "dimensionless",
                             "provenance": None,
                             "symbol_type": self.custom_symbol.name})

        self.assertEqual(d_storage, {"@module": "propnet.core.quantity",
                                     "@class": "Quantity",
                                     "value": 5,
                                     "units": "dimensionless",
                                     "provenance": None,
                                     "internal_id": q._internal_id,
                                     "symbol_type": self.custom_symbol.name})

        self.assertEqual(d_storage_omit, {"@module": "propnet.core.quantity",
                                          "@class": "Quantity",
                                          "value": None,
                                          "units": None,
                                          "provenance": None,
                                          "internal_id": q._internal_id,
                                          "symbol_type": self.custom_symbol.name})

        q = Quantity.factory(self.custom_symbol, 5, tags='experimental', uncertainty=1, provenance=ProvenanceElement())
        d = q.as_dict()
        d_storage = q.as_dict(for_storage=True)
        self.assertEqual(d, {"@module": "propnet.core.quantity",
                             "@class": "Quantity",
                             "value": 5,
                             "units": "dimensionless",
                             "provenance": q._provenance,
                             "symbol_type": self.custom_symbol.name})

        # Need more tests for provenance as_dict() method
        self.assertEqual(d_storage, {"@module": "propnet.core.quantity",
                                     "@class": "Quantity",
                                     "value": 5,
                                     "units": "dimensionless",
                                     "provenance": q._provenance.as_dict(),
                                     "internal_id": q._internal_id,
                                     "symbol_type": self.custom_symbol.name})

        self.assertIsInstance(d_storage['provenance'], dict)
        #
        # self.assertEqual(d_storage_omit, {"@module": "propnet.core.quantity",
        #                                   "@class": "Quantity",
        #                                   "value": None,
        #                                   "units": None,
        #                                   "provenance": None,
        #                                   "internal_id": q._internal_id,
        #                                   "symbol_type": self.custom_symbol.name})
