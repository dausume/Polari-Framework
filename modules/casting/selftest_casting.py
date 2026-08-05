"""
Selftest — cast-1: the inversion primitive.

Run from polari-framework/:
    python3 -m casting.selftest_casting

Covers: mold body derived as stock DIFFERENCE part with correct field
signs and grid volume; auto stock sizing; exact shrink scaling on both
the quadric and the primitive path; derived rows reconverge over
hand-edits with the drift named; honest refusals (missing part,
imported-mesh trap, non-volumetric family, bad allowance).
"""

import json
import math
from types import SimpleNamespace

from casting.casting_seed import SEED_CASTING_MODULES, SEED_MOLDS
from casting.mold_geometry import derive_mold, scale_quadric_flat
from mathshapes.shape_analysis import evaluate_point, shape_properties
from mathshapes.shape_seed import SEED_MATH_SHAPES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _table(seed_list):
    return {r['name']: SimpleNamespace(**r) for r in seed_list}


def _mgr(extra_molds=()):
    molds = [dict(m) for m in SEED_MOLDS] + [dict(m) for m in extra_molds]
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _table(SEED_MATH_SHAPES),
        'MoldDefinition': _table(molds)})


if __name__ == '__main__':
    manager = _mgr()

    print('the inversion: unit-sphere mold')
    r = derive_mold(manager, 'demo-sphere-mold')
    check('derivation ok', r.get('ok'), r.get('error', ''))
    body = manager.objectTables['MathShapeDefinition'].get(
        r.get('bodyShape', ''))
    spec = json.loads(getattr(body, 'csg_json', '{}') or '{}')
    check('body = stock DIFFERENCE part',
          spec.get('op') == 'difference'
          and spec.get('shapes') == [r['stockShape'], 'unit-sphere'])
    stock = manager.objectTables['MathShapeDefinition'].get(
        r['stockShape'])
    sp = json.loads(getattr(stock, 'parameters_json', '{}'))
    check('auto stock = part AABB + 1cm margin each side (4×4×4 box)',
          sp.get('size') == [4.0, 4.0, 4.0]
          and sp.get('center') == [0.0, 0.0, 0.0])

    print('field signs (the negative is a negative)')
    inside_void = evaluate_point(manager, r['bodyShape'], 0.0, 0.0, 0.0)
    in_body = evaluate_point(manager, r['bodyShape'], 1.7, 1.7, 1.7)
    outside = evaluate_point(manager, r['bodyShape'], 5.0, 0.0, 0.0)
    check('cavity void (part interior) is NOT in the mold body',
          inside_void.get('ok') and inside_void.get('inside') is False)
    check('stock corner (outside part) IS mold body',
          in_body.get('ok') and in_body.get('inside') is True)
    check('beyond the stock is outside', outside.get('inside') is False)

    print('volumes (grid instrument)')
    vc = r.get('volumeCheck', {})
    sphere = 4.0 / 3.0 * math.pi
    check('volume cross-check ok', vc.get('ok'),
          f"dev={vc.get('relDeviation')}")
    check('body ≈ 64 − 4π/3',
          vc.get('bodyCm3') is not None
          and abs(vc['bodyCm3'] - (64.0 - sphere)) / 64.0 < 0.05,
          f"body={vc.get('bodyCm3')}")

    print('shrink allowance (primitive path, +2%)')
    r2 = derive_mold(manager, 'pot-frustum-mold')
    check('derivation ok', r2.get('ok'), r2.get('error', ''))
    check('scaled copy emitted', r2.get('scaledPartShape'))
    frustum = math.pi * 20.0 / 3.0 * (36.0 + 54.0 + 81.0)
    sc = shape_properties(manager, r2['scaledPartShape'])
    check('scaled part volume ≈ s³ × part volume (analytic primitive)',
          sc.get('ok')
          and abs(sc['volumeCm3'] - frustum * 1.02 ** 3) / frustum < 0.01,
          f"scaled={sc.get('volumeCm3')}")

    print('shrink allowance (quadric path, exact matrix transform)')
    q = json.loads('[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,-1]')
    q_scaled = scale_quadric_flat(q, 1.1)

    def _qval(q16, x, y, z):
        p = (x, y, z, 1.0)
        return sum(q16[4 * i + j] * p[i] * p[j]
                   for i in range(4) for j in range(4))
    check('scaled sphere surface sits at r=1.1 (F(1.1,0,0)=0)',
          abs(_qval(q_scaled, 1.1, 0.0, 0.0)) < 1e-9)
    check('r=1.05 inside, r=1.15 outside the scaled sphere',
          _qval(q_scaled, 1.05, 0, 0) < 0 < _qval(q_scaled, 1.15, 0, 0))

    print('derived rows reconverge — hand-edits are named, not kept')
    body.csg_json = json.dumps({'op': 'union',
                                'shapes': ['unit-sphere']})
    r3 = derive_mold(manager, 'demo-sphere-mold')
    recon = {c['name']: c['fields'] for c in r3.get('reconverged', [])}
    check('hand-edited body row was overwritten and named',
          'csg_json' in recon.get(r['bodyShape'], [])
          and r3.get('handEditNote'))
    spec_after = json.loads(body.csg_json)
    check('body restored to the derived difference',
          spec_after.get('op') == 'difference')

    print('honest refusals')
    bad = _mgr(extra_molds=[
        {'name': 'mesh-mold', 'part_shape_ref': 'bracket-v2',
         'part_source': 'imported-cad'},
        {'name': 'ghost-mold', 'part_shape_ref': 'no-such-shape',
         'part_source': 'mathshape'},
        {'name': 'winding-mold', 'part_shape_ref': 'a-winding',
         'part_source': 'mathshape'},
        {'name': 'neg-mold', 'part_shape_ref': 'unit-sphere',
         'part_source': 'mathshape', 'shrink_allowance_pct': -120.0},
    ])
    bad.objectTables['MathShapeDefinition']['a-winding'] = (
        SimpleNamespace(name='a-winding', family='winding'))
    mesh = derive_mold(bad, 'mesh-mold')
    check('imported-mesh part refuses, naming the silent-outside trap',
          not mesh.get('ok') and 'EMPTY' in mesh.get('error', '')
          and 'cast-2' in mesh.get('error', ''))
    check('missing part refuses',
          not derive_mold(bad, 'ghost-mold').get('ok'))
    wind = derive_mold(bad, 'winding-mold')
    check('non-volumetric family refuses as a named absence',
          not wind.get('ok') and 'winding' in wind.get('error', ''))
    check('nonsensical shrink refuses',
          not derive_mold(bad, 'neg-mold').get('ok'))
    check('unknown mold refuses',
          not derive_mold(bad, 'nope').get('ok'))

    print('module identity')
    check('PolariModule row present + owns MoldDefinition',
          SEED_CASTING_MODULES[0]['name'] == 'Casting-Mold-Nesting'
          and 'MoldDefinition' in json.loads(
              SEED_CASTING_MODULES[0]['manifest_json'])['objects'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
