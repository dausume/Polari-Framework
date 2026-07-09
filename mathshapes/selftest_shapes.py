"""
Selftest — shape-1: math-defined shapes core (quadric / primitive / CSG).

Run from polari-framework/:
    python3 -m mathshapes.selftest_shapes

Covers the shape-1 acceptance: quadric classification from the matrix Q
(sphere/ellipsoid/cylinder/cone); analytic primitive volumes match their
formulas; a grid-sampled sphere converges to 4/3π; a CSG difference
(pot minus holes) has LESS volume than the base pot; inside/outside is
correct for known points; honest refusals; sample_surface returns
render points (+ triangles for primitives).
"""

import math
from types import SimpleNamespace

from mathshapes.shape_analysis import (
    classify_quadric_matrix, evaluate_point, quadric_classify,
    sample_surface, shape_properties,
)
from mathshapes.shape_seed import SEED_MATH_SHAPES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': {i: SimpleNamespace(**r)
                                for i, r in enumerate(SEED_MATH_SHAPES)}})


def _diag(a, b, c, d):
    return [[a, 0, 0, 0], [0, b, 0, 0], [0, 0, c, 0], [0, 0, 0, d]]


if __name__ == '__main__':
    manager = _mgr()

    print('quadric classification (from the matrix Q)')
    check("diag(1,1,1,-1) -> 'sphere'",
          classify_quadric_matrix(_diag(1, 1, 1, -1)).get('type') == 'sphere')
    check("diag(0.25,1,1,-1) -> 'ellipsoid'",
          classify_quadric_matrix(_diag(0.25, 1, 1, -1)).get('type')
          == 'ellipsoid')
    check("diag(1,1,0,-1) -> 'cylinder'",
          classify_quadric_matrix(_diag(1, 1, 0, -1)).get('type')
          == 'cylinder')
    check("diag(1,1,-1,0) -> 'cone'",
          classify_quadric_matrix(_diag(1, 1, -1, 0)).get('type') == 'cone')
    check('seeded unit-sphere classifies as sphere (via manager)',
          quadric_classify(manager, 'unit-sphere').get('type') == 'sphere')

    print('analytic primitive volumes match formulas')
    cyl = shape_properties(manager, 'demo-cylinder')
    check('demo-cylinder volume = π r² h (r=1, h=4)',
          abs(cyl['volumeCm3'] - math.pi * 1 * 1 * 4) < 1e-3,
          f"got {cyl['volumeCm3']}")
    check('demo-cylinder method is analytic', cyl['method'] == 'analytic')

    print('grid-sampled quadric converges to the analytic volume')
    sphere = shape_properties(manager, 'unit-sphere', resolution=40)
    analytic = (4.0 / 3.0) * math.pi
    err = abs(sphere['volumeCm3'] - analytic) / analytic
    check('unit-sphere grid volume within 5% of 4/3π',
          err < 0.05, f"got {sphere['volumeCm3']} vs {analytic:.4f} "
          f"({err * 100:.2f}%)")
    check('grid method is labelled', 'grid-sample' in sphere['method'])

    print('CSG difference has less volume than the base solid')
    frustum = shape_properties(manager, 'frustum-pot', resolution=28)
    holed = shape_properties(manager, 'pot-with-holes', resolution=28)
    check('pot-with-holes < frustum-pot (holes remove material)',
          holed['volumeCm3'] < frustum['volumeCm3'],
          f"{holed['volumeCm3']} < {frustum['volumeCm3']}")

    print('inside / outside at known points')
    check('origin is inside the unit sphere',
          evaluate_point(manager, 'unit-sphere', 0, 0, 0)['inside'] is True)
    check('(5,5,5) is outside the unit sphere',
          evaluate_point(manager, 'unit-sphere', 5, 5, 5)['inside'] is False)
    check('a point on the pot axis is inside frustum-pot',
          evaluate_point(manager, 'frustum-pot', 0, 0, 0)['inside'] is True)
    check('a far point is outside frustum-pot',
          evaluate_point(manager, 'frustum-pot', 50, 0, 0)['inside'] is False)

    print('honest refusals')
    check('evaluate on a missing shape refuses',
          not evaluate_point(manager, 'nope', 0, 0, 0).get('ok'))
    check('properties on a missing shape refuses',
          not shape_properties(manager, 'nope').get('ok'))
    check('classify on a missing shape refuses',
          not quadric_classify(manager, 'nope').get('ok'))
    check('classify on a non-quadric (demo-cylinder) refuses',
          not quadric_classify(manager, 'demo-cylinder').get('ok'))

    print('surface sampling returns render points')
    ss = sample_surface(manager, 'unit-sphere')
    check('unit-sphere surface has points',
          ss['count'] > 0 and len(ss['points']) > 0, f"count={ss['count']}")
    fr = sample_surface(manager, 'frustum-pot')
    check('frustum-pot surface has points + triangles',
          fr['count'] > 0 and len(fr['triangles']) > 0,
          f"pts={fr['count']} tris={len(fr['triangles'])}")

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
