"""
Selftest — shape-4: predictive root/plant growth in an aquaponic tower,
with the math-shape tier geometry as the carrying capacity.

Run from polari-framework/:
    python3 -m mathshapes.shape4_selftest

Covers: a WELL-SIZED tier (big pot) predicts healthy growth to maturity
("fits", root ball fits, not geometrically capped); an UNDER-SIZED tier
(small pot) confines a tolerant plant ("fits (dwarfed)", geometrically
capped, realized ≈ tier capacity); an under-sized tier + a taproot plant
names a root-prune cadence ("needs pruning"); an under-sized tier + a
non-dwarfable plant "will fail" with the factor named; a shape-2
modify_parameter (enlarge the pot radius) SHIFTS the forecast from
dwarfed→fits; honest refusals (missing tower, missing root model).
"""

import json
from types import SimpleNamespace

from mathshapes.custom.growth_prediction import tower_growth_forecast
from mathshapes.custom.shape_modify import modify_parameter

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _cyl(radius, height):
    return json.dumps({'radius': radius, 'height': height, 'axis': 'z',
                       'center': [0.0, 0.0, 0.0]})


# --- pot shapes: a big cylinder (roomy) and a small cylinder (cramped) ---
SHAPES = [
    {'name': 'big-pot', 'display_name': 'Big pot', 'family': 'primitive',
     'primitive_kind': 'cylinder', 'quadric_matrix_json': '',
     'csg_json': '', 'parameters_json': _cyl(15.0, 30.0),
     'bounds_json': '', 'provenance_id': 'shape4-test'},
    {'name': 'small-pot', 'display_name': 'Small pot', 'family': 'primitive',
     'primitive_kind': 'cylinder', 'quadric_matrix_json': '',
     'csg_json': '', 'parameters_json': _cyl(6.0, 12.0),
     'bounds_json': '', 'provenance_id': 'shape4-test'},
]

TOWERS = [
    {'name': 'well-tower', 'display_name': 'Well-sized tower',
     'pot_shape_name': 'big-pot', 'n_tiers': 3, 'tier_spacing_cm': 30.0,
     'shared_reservoir': True, 'reservoir_volume_l': 10.0,
     'grow_fraction': 0.6, 'provenance_id': 'shape4-test'},
    {'name': 'cramped-tower', 'display_name': 'Under-sized tower',
     'pot_shape_name': 'small-pot', 'n_tiers': 3, 'tier_spacing_cm': 15.0,
     'shared_reservoir': True, 'reservoir_volume_l': 4.0,
     'grow_fraction': 0.6, 'provenance_id': 'shape4-test'},
]

# --- morph-1 root models (dense root ball drives confinement) ---
ROOTS = [
    {'name': 'sweet-basil-roots', 'plant_name': 'sweet-basil',
     'pattern': 'fibrous', 'natural_spread_radius_mm': 120.0,
     'natural_depth_mm': 200.0, 'root_ball_fraction': 0.5,
     'confinement_tolerance': 0.7, 'dwarfable': True,
     'root_prune_cadence_days': 0.0, 'indefinite_in_pot': True},
    {'name': 'dwarf-pepper-roots', 'plant_name': 'dwarf-pepper',
     'pattern': 'taproot', 'natural_spread_radius_mm': 180.0,
     'natural_depth_mm': 300.0, 'root_ball_fraction': 0.6,
     'confinement_tolerance': 0.45, 'dwarfable': True,
     'root_prune_cadence_days': 365.0, 'indefinite_in_pot': True},
    {'name': 'oak-roots', 'plant_name': 'oak', 'pattern': 'taproot',
     'natural_spread_radius_mm': 500.0, 'natural_depth_mm': 800.0,
     'root_ball_fraction': 0.8, 'confinement_tolerance': 0.1,
     'dwarfable': False, 'root_prune_cadence_days': 0.0,
     'indefinite_in_pot': False},
]


def _part(name, plant, ptype, vmax):
    return {'name': name, 'plant_name': plant, 'part': ptype,
            'mature_volume_cm3': vmax, 'dry_density_g_cm3': 0.3,
            'flux_json': '{}'}


# free_soil_constants() (the real detailed model this test's
# growth_prediction.py now sources its constants from — 2026-07-15)
# requires a PlantDefinition row per species; no PlantGrowthModel rows
# are seeded here, so every part uses PlantDefinition's own
# normalized_growth_rate_per_day FALLBACK rate — deliberately, keeping
# this fixture independent of PlantGrowthModel/aqp-8 specifics.
def _plant(name):
    return {'name': name, 'display_name': name, 'species': name,
            'normalized_growth_rate_per_day': 0.12}


PLANTS = [_plant('sweet-basil'), _plant('dwarf-pepper'), _plant('oak')]


PARTS = [
    _part('basil-leaf', 'sweet-basil', 'leaf', 400.0),
    _part('basil-stem', 'sweet-basil', 'stem', 200.0),
    _part('basil-root', 'sweet-basil', 'root', 200.0),
    _part('pepper-leaf', 'dwarf-pepper', 'leaf', 600.0),
    _part('pepper-fruit', 'dwarf-pepper', 'fruit', 400.0),
    _part('pepper-root', 'dwarf-pepper', 'root', 300.0),
    _part('oak-leaf', 'oak', 'leaf', 3000.0),
    _part('oak-root', 'oak', 'root', 2000.0),
]


def _mgr():
    return SimpleNamespace(objectTables={
        'MathShapeDefinition': _rows(SHAPES),
        'AquaponicTowerDefinition': _rows(TOWERS),
        'RootSystemModel': _rows(ROOTS),
        'PlantPart': _rows(PARTS),
        'PlantDefinition': _rows(PLANTS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('well-sized tower + basil → fits')
    well = tower_growth_forecast(manager, 'well-tower', 'sweet-basil',
                                 days=180.0)
    check('forecast ok + 3 tiers', well['ok'] and len(well['perTier']) == 3)
    t0 = well['perTier'][0]
    check('big-pot tier grow volume is roomy (> mature plant)',
          t0['tierGrowVolumeCm3'] > well['matureUnconfinedVolumeCm3'],
          f"tier={t0['tierGrowVolumeCm3']} mature="
          f"{well['matureUnconfinedVolumeCm3']}")
    check('verdict "fits", not capped, ratio >= 1',
          t0['verdict'] == 'fits' and not t0['geometricallyCapped']
          and t0['confinementRatio'] >= 1.0,
          f"verdict={t0['verdict']} ratio={t0['confinementRatio']}")
    check('all tiers fit', well['summary']['allTiersFit'])

    print('under-sized tower + basil → dwarfed + geometrically capped')
    cramp = tower_growth_forecast(manager, 'cramped-tower', 'sweet-basil',
                                  days=180.0)
    c0 = cramp['perTier'][0]
    check('small-pot tier capacity < mature plant (cap binds)',
          c0['tierGrowVolumeCm3'] < cramp['matureUnconfinedVolumeCm3']
          and c0['geometricallyCapped'])
    check('realized volume ≈ tier capacity (not the full mature size)',
          abs(c0['realizedVolumeCm3'] - c0['tierGrowVolumeCm3']) < 1e-6
          and c0['realizedVolumeCm3'] < cramp['matureUnconfinedVolumeCm3'])
    check('verdict is dwarfed (basil tolerant+dwarfable), root-bound',
          c0['verdict'] == 'fits (dwarfed)'
          and c0['confinementRatio'] < 1.0,
          f"verdict={c0['verdict']} ratio={c0['confinementRatio']}")
    check('time-to-carrying-capacity is reported',
          c0['timeToCarryingCapacityDays'] is not None)

    print('under-sized tower + dwarf pepper → needs pruning (cadence named)')
    pep = tower_growth_forecast(manager, 'cramped-tower', 'dwarf-pepper',
                                days=180.0)
    p0 = pep['perTier'][0]
    check('verdict "needs pruning"', p0['verdict'] == 'needs pruning',
          f"verdict={p0['verdict']}")
    check('root-prune cadence carried + named in limiting factor',
          p0['rootPruneCadenceDays'] == 365.0
          and 'root-prune' in (p0['limitingFactor'] or ''))

    print('under-sized tower + non-dwarfable oak → will fail')
    oak = tower_growth_forecast(manager, 'cramped-tower', 'oak',
                                days=180.0)
    o0 = oak['perTier'][0]
    check('verdict "will fail"', o0['verdict'] == 'will fail',
          f"verdict={o0['verdict']}")
    check('limiting factor names not-dwarfable',
          'not dwarfable' in (o0['limitingFactor'] or ''))
    check('summary flags a failing tier', oak['summary']['anyTierFails'])

    print('shape-2 modify (enlarge pot) SHIFTS the forecast dwarfed→fits')
    before = tower_growth_forecast(manager, 'cramped-tower', 'sweet-basil',
                                   days=180.0)['perTier'][0]['verdict']
    mod = modify_parameter(manager, 'small-pot', 'radius', 24.0)
    check('modify_parameter ok', mod.get('ok', True) is not False)
    after = tower_growth_forecast(manager, 'cramped-tower', 'sweet-basil',
                                  days=180.0)['perTier'][0]
    check('bigger pot → verdict improves to fits',
          before == 'fits (dwarfed)' and after['verdict'] == 'fits',
          f"before={before} after={after['verdict']}")
    check('bigger pot → root ball now fits (ratio >= 1)',
          after['confinementRatio'] >= 1.0)
    # restore for isolation
    modify_parameter(manager, 'small-pot', 'radius', 6.0)

    print('honest refusals')
    check('missing tower refuses',
          not tower_growth_forecast(manager, 'nope', 'sweet-basil').get('ok'))
    check('plant with no root model refuses',
          not tower_growth_forecast(manager, 'well-tower',
                                    'no-such-plant').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
