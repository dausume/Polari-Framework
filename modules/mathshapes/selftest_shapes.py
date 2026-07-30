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

    print('CSG surfaces are triangulated (mag-7)')
    import json as _json_mod
    tube_rows = manager.objectTables['MathShapeDefinition']
    base = max(tube_rows) + 1
    tube_rows[base] = SimpleNamespace(
        name='t-outer', family='primitive', primitive_kind='cylinder',
        parameters_json=_json_mod.dumps(
            {'radius': 2.0, 'height': 1.0, 'axis': 'y',
             'center': [0.0, 0.0, 0.0]}))
    tube_rows[base + 1] = SimpleNamespace(
        name='t-bore', family='primitive', primitive_kind='cylinder',
        parameters_json=_json_mod.dumps(
            {'radius': 1.0, 'height': 1.4, 'axis': 'y',
             'center': [0.0, 0.0, 0.0]}))
    tube_rows[base + 2] = SimpleNamespace(
        name='t-ring', family='csg',
        csg_json=_json_mod.dumps(
            {'op': 'difference', 'shapes': ['t-outer', 't-bore']}),
        bounds_json=_json_mod.dumps(
            [[-2.2, 2.2], [-0.8, 0.8], [-2.2, 2.2]]))
    ring = sample_surface(manager, 't-ring', n=24)
    check('coaxial-cylinder difference gets the exact tube mesh',
          ring.get('ok') and 'parametric tube' in ring['method']
          and len(ring['triangles']) == 8 * 24,
          f"method={ring.get('method')} tris={len(ring.get('triangles', []))}")
    # points are rounded to 4 decimals — tolerance must exceed that
    radii_ok = all(
        1.0 - 1e-3 <= math.hypot(p[0], p[2]) <= 2.0 + 1e-3
        for p in ring['points'])
    check('every tube vertex sits between bore and outer radius',
          radii_ok)
    holed_mesh = sample_surface(manager, 'pot-with-holes', n=20)
    check('general CSG marching now returns triangles (voxel-face '
          'mesh), honestly labelled blocky',
          holed_mesh.get('ok') and len(holed_mesh['triangles']) > 0
          and 'blocky' in holed_mesh['method'],
          f"method={holed_mesh.get('method')}")
    # An off-axis bore must NOT match the tube special case.
    tube_rows[base + 3] = SimpleNamespace(
        name='t-bore-off', family='primitive', primitive_kind='cylinder',
        parameters_json=_json_mod.dumps(
            {'radius': 0.5, 'height': 1.4, 'axis': 'y',
             'center': [0.8, 0.0, 0.0]}))
    tube_rows[base + 4] = SimpleNamespace(
        name='t-ring-off', family='csg',
        csg_json=_json_mod.dumps(
            {'op': 'difference', 'shapes': ['t-outer', 't-bore-off']}),
        bounds_json=_json_mod.dumps(
            [[-2.2, 2.2], [-0.8, 0.8], [-2.2, 2.2]]))
    off = sample_surface(manager, 't-ring-off', n=16)
    check('off-axis bore falls back to the voxel-face mesh',
          off.get('ok') and 'voxel-face' in off['method']
          and len(off['triangles']) > 0, f"method={off.get('method')}")

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
