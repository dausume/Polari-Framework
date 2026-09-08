"""
Selftest — plant-growth-sim phase 9 (2026-07-15): source-sink nutrient
TRANSPORT between plant parts (aquaponics.plant_growth_normalized_basis.
transport_factor) — the missing whole-plant coupling Dustin flagged:
"Are there nutrient propagation mechanisms from part to part inside
the plant we may not yet be accounting for?"

Run from polari-framework/:
    python3 -m aquaponics.plant_transport_selftest

Covers the pure geometry/capacity function directly (fast, precise),
then proves the REAL cross-part effect through advance_growth against
real seed data: a small leaf measurably throttles STEM growth (a
THIRD, unrelated part) — not just the leaf's own growth — the
strongest possible demonstration that this is genuine whole-plant
coupling, not each part still suffering independently.
"""

import json
from types import SimpleNamespace

from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.light_seed import SEED_LIGHT_SOURCES, SEED_LIGHT_SPECTRA
from aquaponics.media_seed import SEED_SOILS, SEED_WATERS
from aquaponics.plant_growth_normalized_basis import (
    REFERENCE_SATURATING_PPFD, SEED_RESERVE_FLOOR, advance_growth,
    constrained_limits, transport_factor,
)
from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.plant_stress_seed import SEED_STRESS_CURVES
from aquaponics.pot_seed import SEED_POTS
from aquaponics.pot_system_seed import SEED_POT_SYSTEMS
from plant_morphology.morphology_seed import (
    SEED_ORGAN_MODELS, SEED_ROOT_MODELS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(plantings=None):
    return SimpleNamespace(objectTables={
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'PotDefinition': _rows(SEED_POTS),
        'PotPlanting': _rows(
            plantings if plantings is not None else SEED_POT_PLANTINGS),
        'PotSystemDefinition': _rows(SEED_POT_SYSTEMS),
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'WaterDefinition': _rows(SEED_WATERS),
        'SoilDefinition': _rows(SEED_SOILS),
        'StressResponseCurve': _rows(SEED_STRESS_CURVES),
        'MatrixEquationDefinition': {},
        'LightSpectrumDefinition': _rows(SEED_LIGHT_SPECTRA),
        'LightSourceDefinition': _rows(SEED_LIGHT_SOURCES),
    })


HEALTHY_PLANTING = 'demo-herb-pot-basil-1'


if __name__ == '__main__':
    manager = _mgr()
    limits = constrained_limits(manager, 'demo-herb-pot', 'sweet-basil')

    print('transport_factor — pure geometry/capacity, no live data row')
    ceiling = limits['normalizedGrowthCeiling']
    fresh_growth = {}   # nothing advanced yet -> every part at epsilon
    factor, evidence = transport_factor(fresh_growth, limits, {})
    check('a fresh (just-germinated) planting floors at '
          'SEED_RESERVE_FLOOR, never stalls to 0 (a real seed has its '
          'own reserves to bootstrap growth before roots/leaves exist)',
          factor == SEED_RESERVE_FLOOR and evidence['flooredBySeedReserve'])

    mature_growth = {'root': ceiling * 0.9, 'leaf': ceiling * 0.9,
                     'stem': ceiling * 0.9}
    factor2, evidence2 = transport_factor(mature_growth, limits, {})
    check('a well-grown plant (90% of ceiling) clears the floor — '
          'genuine capacity, not the bootstrap value',
          factor2 > SEED_RESERVE_FLOOR
          and evidence2['rootCapacity'] > 0.8
          and evidence2['leafCapacity'] > 0.8)

    small_leaf_growth = {'root': ceiling * 0.8, 'leaf': ceiling * 0.05,
                         'stem': ceiling * 0.8}
    factor3, evidence3 = transport_factor(small_leaf_growth, limits, {})
    check('a disproportionately SMALL leaf (defoliated-plant proxy) '
          'becomes the binding constraint, named honestly',
          evidence3['limitingCapacity'] == 'leaf-photosynthesis'
          and factor3 < factor2)

    small_root_growth = {'root': ceiling * 0.05, 'leaf': ceiling * 0.8,
                         'stem': ceiling * 0.8}
    factor4, evidence4 = transport_factor(small_root_growth, limits, {})
    check('a disproportionately SMALL root becomes the binding '
          'constraint instead, named honestly',
          evidence4['limitingCapacity'] == 'root-uptake'
          and factor4 < factor2)

    print('transport_factor — real light-magnitude driver (phase 8 '
          'integration, distinct from the 0-1 light stress CURVE)')
    bright = transport_factor(
        mature_growth, limits, {'leaf': REFERENCE_SATURATING_PPFD * 2})
    dim = transport_factor(mature_growth, limits, {'leaf': 30.0})
    check('abundant light (>= saturation) is capped at light_factor '
          '1.0, never rewarded beyond full capacity',
          bright[1]['leafLightFactor'] == 1.0)
    check('dim light measurably lowers leaf capacity below the '
          'size-only value',
          dim[1]['leafCapacity'] < mature_growth['leaf'] / ceiling)
    check('no light data at all -> neutral (assume adequate light), '
          'an honest "not modeled here" default, not a penalty',
          transport_factor(mature_growth, limits, {})[1][
              'leafLightFactor'] == 1.0)

    print('transport_factor — honest no-op when the species has no '
          'distinguishable root or leaf part')
    no_root_limits = {'partCeilings': {'leaf': limits['partCeilings'][
        'leaf'], 'stem': limits['partCeilings']['stem']}}
    check('missing root -> factor 1.0, no evidence (nothing to couple)',
          transport_factor({}, no_root_limits, {}) == (1.0, None))

    print("advance_growth — THE REAL cross-part effect: a stunted "
          "leaf measurably slows STEM growth (a THIRD, unrelated "
          "part), not just the leaf's own growth")
    # Two identical plantings, differing ONLY in their starting
    # part_growth_json — one with leaf/root/stem evenly grown, one
    # with an ARTIFICIALLY stunted leaf relative to an already-
    # substantial root/stem (simulating real damage/defoliation).
    # Bound to 'basil-aquaponic-sealed' (no light_source_name set,
    # unlike 'basil-aquaponic-tent') deliberately — isolates this to
    # the SIZE-only half of the transport signal; the real light-
    # magnitude half is already covered directly above via
    # transport_factor() itself, and the real demo grow-light's own
    # computed absorption (self-shading + incidence losses) turns out
    # low enough to floor BOTH scenarios identically here, which would
    # mask the size effect this test is specifically after.
    normal_seed = dict(SEED_POT_PLANTINGS[0], name='transport-normal',
                       system_name='basil-aquaponic-sealed',
                       part_growth_json=json.dumps(
                           {'root': ceiling * 0.5, 'stem': ceiling * 0.5,
                            'leaf': ceiling * 0.5}))
    stunted_seed = dict(SEED_POT_PLANTINGS[0], name='transport-stunted',
                        system_name='basil-aquaponic-sealed',
                        part_growth_json=json.dumps(
                            {'root': ceiling * 0.5, 'stem': ceiling * 0.5,
                             'leaf': ceiling * 0.05}))
    mgr_normal = _mgr(plantings=[normal_seed])
    mgr_stunted = _mgr(plantings=[stunted_seed])

    normal_result = advance_growth(mgr_normal, 'transport-normal',
                                   dt_days=5.0)
    stunted_result = advance_growth(mgr_stunted, 'transport-stunted',
                                    dt_days=5.0)
    check('both runs ok, stress-equations mode (real system bound)',
          normal_result['ok'] and stunted_result['ok']
          and normal_result['mode'] == 'stress-equations'
          and stunted_result['mode'] == 'stress-equations')
    check("STEM's transportFactor is measurably lower in the stunted-"
          "leaf run — the whole-plant bottleneck, not the leaf's own "
          'local condition',
          stunted_result['parts']['stem']['transportFactor']
          < normal_result['parts']['stem']['transportFactor'])
    check("STEM's ACTUAL realized growth is measurably less in the "
          "stunted-leaf run — reaches real numbers, not just a "
          'reported diagnostic (this IS the missing propagation '
          'mechanism now wired in)',
          stunted_result['parts']['stem']['normalizedGrowth']
          < normal_result['parts']['stem']['normalizedGrowth'])
    check("ROOT is equally affected (same shared transportFactor) — "
          'genuine whole-plant coupling, not a leaf-stem-only special '
          'case',
          stunted_result['parts']['root']['transportFactor']
          == stunted_result['parts']['stem']['transportFactor'])
    check('top-level transport evidence names leaf-photosynthesis as '
          'the limiting capacity in the stunted run',
          stunted_result['transport']['limitingCapacity']
          == 'leaf-photosynthesis')

    print('advance_growth — manual override still bypasses transport '
          'entirely (backward compatible)')
    manual = advance_growth(mgr_stunted, 'transport-stunted',
                            dt_days=5.0, water_supply_factor=1.0,
                            soil_supply_factor=1.0)
    check('manual mode: every part reports transportFactor == 1.0 '
          '(the neutral default, never computed)',
          all(p['transportFactor'] == 1.0
              for p in manual['parts'].values())
          and 'transport' not in manual)

    print('advance_growth — no-linkage mode also bypasses transport')
    no_system_planting = dict(SEED_POT_PLANTINGS[0],
                              name='no-system-transport',
                              system_name='')
    mgr_no_system = _mgr(plantings=[no_system_planting])
    no_system_result = advance_growth(mgr_no_system,
                                      'no-system-transport', dt_days=5.0)
    check('no-linkage mode: transportFactor == 1.0 for every part, no '
          'top-level transport evidence',
          no_system_result['mode'] == 'no-linkage'
          and all(p['transportFactor'] == 1.0
                  for p in no_system_result['parts'].values())
          and 'transport' not in no_system_result)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
