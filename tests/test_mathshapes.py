"""
Math-defined shapes (shape-1..4) — analysis-layer tests.

Pure/duck-typed: these drive the mathshapes analysis functions against a
SimpleNamespace manager built from the real SEED_* lists — no live server,
no DB, no worker. Fast and deterministic.

Covers:
  shape-1  quadric classify, analytic vs grid volume, CSG difference,
           point inside/outside, surface sampling
  shape-2  modify_parameter (dependent-CSG volume drop), tower geometry
  shape-4  tower growth forecast (fits / dwarfed / refusal)

Run (in the backend container):
    python3 -m unittest tests.test_mathshapes -v
"""

import math
import unittest
from types import SimpleNamespace

from mathshapes.custom.shape_analysis import (
    classify_quadric_matrix, evaluate_point, sample_surface, shape_properties,
)
from mathshapes.custom.shape_geometry import primitive_properties
from mathshapes.shape_seed import SEED_MATH_SHAPES
from mathshapes.tower_seed import SEED_TOWERS
from mathshapes.custom import shape_modify
from mathshapes.custom import tower_analysis
from mathshapes.custom import growth_prediction


def _table(seed_list):
    return {i: SimpleNamespace(**dict(row)) for i, row in enumerate(seed_list)}


def _shapes_manager():
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _table(SEED_MATH_SHAPES),
    })


class QuadricClassifyTests(unittest.TestCase):
    def _Q(self, diag):
        Q = [[0.0] * 4 for _ in range(4)]
        for i, v in enumerate(diag):
            Q[i][i] = float(v)
        return Q

    def test_sphere(self):
        self.assertEqual(classify_quadric_matrix(
            self._Q([1, 1, 1, -1]))['type'], 'sphere')

    def test_ellipsoid(self):
        self.assertEqual(classify_quadric_matrix(
            self._Q([0.25, 1, 1, -1]))['type'], 'ellipsoid')

    def test_cylinder(self):
        self.assertEqual(classify_quadric_matrix(
            self._Q([1, 1, 0, -1]))['type'], 'cylinder')

    def test_cone(self):
        self.assertEqual(classify_quadric_matrix(
            self._Q([1, 1, -1, 0]))['type'], 'cone')


class PrimitiveVolumeTests(unittest.TestCase):
    def test_sphere_analytic(self):
        vol, area, bounds, centroid = primitive_properties(
            'sphere', {'radius': 2.0})
        self.assertAlmostEqual(vol, 4.0 / 3.0 * math.pi * 8.0, places=6)

    def test_cylinder_analytic(self):
        vol, _, _, _ = primitive_properties(
            'cylinder', {'radius': 1.0, 'height': 4.0, 'axis': 'z'})
        self.assertAlmostEqual(vol, math.pi * 1.0 * 4.0, places=6)


class ShapePropertiesTests(unittest.TestCase):
    def setUp(self):
        self.mgr = _shapes_manager()

    def test_grid_sphere_matches_analytic(self):
        r = shape_properties(self.mgr, 'unit-sphere', resolution=40)
        self.assertTrue(r['ok'])
        analytic = 4.0 / 3.0 * math.pi
        self.assertLess(abs(r['volumeCm3'] - analytic) / analytic, 0.05)

    def test_csg_difference_less_than_base(self):
        pot = shape_properties(self.mgr, 'frustum-pot', resolution=28)
        holed = shape_properties(self.mgr, 'pot-with-holes', resolution=28)
        self.assertTrue(pot['ok'] and holed['ok'])
        self.assertLess(holed['volumeCm3'], pot['volumeCm3'])

    def test_missing_shape_refuses(self):
        self.assertFalse(shape_properties(self.mgr, 'nope').get('ok'))


class EvaluateAndSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.mgr = _shapes_manager()

    def test_origin_inside_unit_sphere(self):
        r = evaluate_point(self.mgr, 'unit-sphere', 0, 0, 0)
        self.assertTrue(r['ok'] and r['inside'])

    def test_far_point_outside(self):
        r = evaluate_point(self.mgr, 'unit-sphere', 5, 5, 5)
        self.assertTrue(r['ok'] and not r['inside'])

    def test_surface_has_points(self):
        s = sample_surface(self.mgr, 'unit-sphere', n=16)
        self.assertTrue(s['ok'] and s['count'] > 0 and len(s['points']) > 0)

    def test_primitive_surface_has_triangles(self):
        s = sample_surface(self.mgr, 'frustum-pot', n=16)
        self.assertTrue(s['ok'] and len(s['points']) > 0)


class ModifyTests(unittest.TestCase):
    def test_enlarging_hole_reduces_dependent_pot(self):
        mgr = _shapes_manager()
        r = shape_modify.modify_parameter(mgr, 'hole-cylinder-a',
                                          'radius', 2.0)
        self.assertTrue(r['ok'])
        dep = r['after'].get('dependentPots', {})
        self.assertIn('pot-with-holes', dep)
        self.assertLess(dep['pot-with-holes'],
                        r['before']['dependentPots']['pot-with-holes'])


class TowerGeometryTests(unittest.TestCase):
    def _mgr(self):
        return SimpleNamespace(objectTables={
            'MathShapeDefinition': _table(SEED_MATH_SHAPES),
            'AquaponicTowerDefinition': _table(SEED_TOWERS),
        })

    def test_tower_geometry_sums_tiers(self):
        r = tower_analysis.tower_geometry(self._mgr(), 'demo-herb-tower')
        self.assertTrue(r['ok'])
        self.assertEqual(len(r['perTier']), 4)

    def test_missing_tower_refuses(self):
        self.assertFalse(
            tower_analysis.tower_geometry(self._mgr(), 'nope').get('ok'))


class GrowthForecastTests(unittest.TestCase):
    def _mgr(self):
        tables = {
            'MathShapeDefinition': _table(SEED_MATH_SHAPES),
            'AquaponicTowerDefinition': _table(SEED_TOWERS),
        }
        # pull in the plant/root/growth seeds the forecast couples to
        try:
            from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
            tables['PlantGrowthModel'] = _table(SEED_PLANT_GROWTH_MODELS)
        except Exception:
            pass
        try:
            from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
            tables['PlantDefinition'] = _table(SEED_PLANTS)
            tables['PlantPart'] = _table(SEED_PLANT_PARTS)
        except Exception:
            pass
        try:
            from plant_morphology.morphology_seed import (
                SEED_ROOT_MODELS, SEED_ORGAN_MODELS,
            )
            tables['RootSystemModel'] = _table(SEED_ROOT_MODELS)
            tables['OrganModel'] = _table(SEED_ORGAN_MODELS)
        except Exception:
            pass
        return SimpleNamespace(objectTables=tables)

    def test_forecast_returns_per_tier_verdicts(self):
        r = growth_prediction.tower_growth_forecast(
            self._mgr(), 'demo-herb-tower', 'sweet-basil', days=120)
        self.assertTrue(r.get('ok'), msg=str(r))
        self.assertEqual(len(r['perTier']), 4)
        for tier in r['perTier']:
            self.assertIn('verdict', tier)

    def test_missing_plant_refuses(self):
        r = growth_prediction.tower_growth_forecast(
            self._mgr(), 'demo-herb-tower', 'no-such-plant', days=30)
        self.assertFalse(r.get('ok'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
