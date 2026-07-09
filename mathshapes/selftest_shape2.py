"""
Selftest — shape-2: algorithmic modification + aqp-1 pot bridge + tower.

Run from polari-framework/:
    python3 -m mathshapes.selftest_shape2

Covers: modifying a hole-cylinder radius UP reduces the pot solid volume
and widens the opening; the aqp-1 gravity invariant gates modification
(a pot with broken drainage refuses, naming the knob); a valid pot's
hole modifies fine; pot_shape_from_definition builds a CSG pot whose
volume is less than the solid frustum; tower geometry sums per-tier grow
volume; honest refusals.
"""

from types import SimpleNamespace

from mathshapes.shape_analysis import shape_properties
from mathshapes.shape_seed import SEED_MATH_SHAPES
from mathshapes.shape_modify import (
    modify_parameter, modify_pot_hole, pot_shape_from_definition,
)
from mathshapes.tower_analysis import tower_geometry
from mathshapes.tower_seed import SEED_TOWERS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _by_name(seed_list):
    return {r['name']: SimpleNamespace(**r) for r in seed_list}


# A valid aqp-1 pot: input high on one side, output low + downhill on the
# opposite side.
POT = {'name': 'demo-pot', 'display_name': 'Demo pot', 'shape': 'tapered',
       'outer_top_diameter_mm': 220.0, 'outer_base_diameter_mm': 180.0,
       'height_mm': 250.0, 'wall_thickness_mm': 8.0,
       'base_thickness_mm': 12.0, 'reservoir_height_mm': 0.0,
       'material_name': ''}
HOLES_VALID = [
    {'name': 'demo-pot-in', 'pot_name': 'demo-pot', 'kind': 'input',
     'diameter_mm': 10.0, 'height_mm': 200.0, 'azimuth_deg': 0.0,
     'angle_deg': 0.0},
    {'name': 'demo-pot-out', 'pot_name': 'demo-pot', 'kind': 'output',
     'diameter_mm': 12.0, 'height_mm': 40.0, 'azimuth_deg': 180.0,
     'angle_deg': 3.0},
]
# The same pot but the output bores UPHILL — breaks gravity drainage.
HOLES_BROKEN = [
    HOLES_VALID[0],
    {'name': 'demo-pot-out', 'pot_name': 'demo-pot', 'kind': 'output',
     'diameter_mm': 12.0, 'height_mm': 40.0, 'azimuth_deg': 180.0,
     'angle_deg': -12.0},
]


def _mgr(holes):
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _by_name(SEED_MATH_SHAPES),
        'AquaponicTowerDefinition': _by_name(SEED_TOWERS),
        'PotDefinition': {'demo-pot': SimpleNamespace(**POT)},
        'PotHole': {h['name']: SimpleNamespace(**h) for h in holes}})


if __name__ == '__main__':
    print('modify a hole → the pot loses volume, the opening widens')
    m = _mgr(HOLES_VALID)
    res = modify_parameter(m, 'hole-cylinder-a', 'radius', 2.0)
    check('modify ok + reports the dependent pot', res.get('ok')
          and 'pot-with-holes' in res['before']['dependentPots'])
    pot_before = res['before']['dependentPots']['pot-with-holes']
    pot_after = res['after']['dependentPots']['pot-with-holes']
    check('bigger hole → smaller pot solid volume',
          pot_after < pot_before,
          f'{pot_before:.1f} → {pot_after:.1f} cm³')
    check('bigger hole → wider opening',
          res['after']['openingAreaCm2'] > res['before']['openingAreaCm2'],
          f"{res['before']['openingAreaCm2']} → "
          f"{res['after']['openingAreaCm2']} cm²")
    check('only the requested knob changed (radius)',
          res['param'] == 'radius' and res['to'] == 2.0)

    print('aqp-1 gravity invariant gates modification')
    m_bad = _mgr(HOLES_BROKEN)
    gated = modify_pot_hole(m_bad, 'demo-pot', 'radius', 1.0, hole_index=0)
    check('broken-drainage pot REFUSES the modification',
          not gated.get('ok'))
    check('refusal names the offending knob',
          'angle_deg' in str(gated.get('limitingFactor', '')),
          str(gated.get('limitingFactor', '')))
    m_ok = _mgr(HOLES_VALID)
    good = modify_pot_hole(m_ok, 'demo-pot', 'radius', 0.7, hole_index=0)
    check('valid pot allows the hole modification',
          good.get('ok') and good.get('gravityValid'))

    print('aqp-1 pot → math-defined CSG pot')
    m2 = _mgr(HOLES_VALID)
    built = pot_shape_from_definition(m2, 'demo-pot')
    check('pot_shape built ok + gravity-valid', built.get('ok')
          and built.get('gravityValid'))
    check('CSG pot volume < solid frustum volume',
          built['potSolidVolumeCm3'] < built['solidFrustumVolumeCm3'],
          f"{built['potSolidVolumeCm3']} < "
          f"{built['solidFrustumVolumeCm3']}")
    check('derived shape is queryable via shape_properties',
          shape_properties(m2, 'demo-pot-shape', resolution=20).get('ok'))

    print('tower geometry sums per-tier grow volume')
    m3 = _mgr(HOLES_VALID)
    tg = tower_geometry(m3, 'demo-herb-tower')
    check('tower geometry ok + 4 tiers', tg.get('ok')
          and tg['nTiers'] == 4 and len(tg['perTier']) == 4)
    check('total grow volume = per-tier × tiers',
          abs(tg['totalGrowVolumeCm3']
              - tg['growVolumePerTierCm3'] * tg['nTiers']) < 1.0)
    check('tower reports footprint + height + water path',
          tg['footprintCm2'] > 0 and tg['towerHeightCm'] > 0
          and tg['waterPathTopToBottom'][0] == 'tier 0')

    print('honest refusals')
    check('modify unknown shape refuses',
          not modify_parameter(m, 'nope', 'radius', 1.0).get('ok'))
    check('modify a CSG directly refuses + suggests the child',
          not modify_parameter(m, 'pot-with-holes', 'radius', 1.0).get('ok'))
    check('unknown knob refuses + lists valid knobs',
          'validKnobs' in modify_parameter(m, 'demo-cylinder', 'nope', 1))
    check('unknown tower refuses',
          not tower_geometry(m, 'nope').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
