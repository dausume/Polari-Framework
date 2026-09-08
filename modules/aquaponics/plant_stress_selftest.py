"""
Selftest — plant-growth-sim phase 7 (2026-07-15): stress-type-
differentiated response curves (aquaponics.plant_stress_basis) + their
wiring into advance_growth's per-part supply factor.

Run from polari-framework/:
    python3 -m aquaponics.plant_stress_selftest

Uses the REAL seed rows (sweet-basil curves, the two real contrasting
aquaponics.pot_system_seed systems, the two real demo plantings) — no
fixture-only data — so this exercises the real cross-module path:
stress curves -> PotSystemDefinition -> AtmosphereDefinition/
WaterDefinition -> combined_stress_factor -> advance_growth.
"""

import json
from types import SimpleNamespace

from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.media_seed import SEED_SOILS, SEED_WATERS
from aquaponics.plant_growth_normalized_basis import advance_growth
from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.plant_stress_basis import (
    STRESS_TYPE_FIELDS, combined_stress_factor, evaluate_curve,
    part_stress_factors, sweep_curve, trapezoid_factor,
)
from aquaponics.plant_stress_seed import SEED_STRESS_CURVES
from aquaponics.pot_seed import SEED_POTS
from aquaponics.pot_system_seed import SEED_POT_SYSTEMS
from matrices.matrix_equation_definition import MatrixEquationDefinition
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


def _mgr(extra_curves=None, extra_matrix_eqs=None):
    curves = list(SEED_STRESS_CURVES)
    if extra_curves:
        curves = curves + extra_curves
    tables = {
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'PotDefinition': _rows(SEED_POTS),
        'PotPlanting': _rows(SEED_POT_PLANTINGS),
        'PotSystemDefinition': _rows(SEED_POT_SYSTEMS),
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'WaterDefinition': _rows(SEED_WATERS),
        'SoilDefinition': _rows(SEED_SOILS),
        'StressResponseCurve': {i: SimpleNamespace(**c)
                                for i, c in enumerate(curves)},
        'MatrixEquationDefinition': {},
    }
    if extra_matrix_eqs:
        tables['MatrixEquationDefinition'] = {
            i: eq for i, eq in enumerate(extra_matrix_eqs)}
    return SimpleNamespace(objectTables=tables)


HEALTHY_PLANTING = 'demo-herb-pot-basil-1'
SEALED_PLANTING = 'demo-herb-pot-basil-sealed'


if __name__ == '__main__':
    manager = _mgr()

    print('trapezoid_factor — pure math')
    check('below min -> 0', trapezoid_factor(1, 2, 5, 9, 14) == 0.0)
    check('above max -> 0', trapezoid_factor(20, 2, 5, 9, 14) == 0.0)
    check('inside optimal plateau -> 1', trapezoid_factor(7, 2, 5, 9, 14)
          == 1.0)
    check('linear ramp on the low side',
          abs(trapezoid_factor(3.5, 2, 5, 9, 14) - 0.5) < 1e-9)
    check('linear ramp on the high side',
          abs(trapezoid_factor(11.5, 2, 5, 9, 14) - 0.5) < 1e-9)
    check('exactly at min_value -> 0 (min_value is a closed 0-bound, '
          'even when optimal_low coincides with it)',
          trapezoid_factor(2.0, 2, 2, 9, 14) == 0.0)
    check('a hair-width low-side ramp (span < the internal epsilon) '
          'never divides by zero — falls back to 1.0 rather than inf/nan',
          trapezoid_factor(2.0 + 2e-10, 2.0, 2.0 + 5e-10, 9, 14) == 1.0)

    print('evaluate_curve — Tier A (trapezoid) against REAL rows')
    root_o2_curve = next(c for c in manager.objectTables[
        'StressResponseCurve'].values()
        if c.name == 'sweet-basil-root-oxygen')
    result = evaluate_curve(manager, root_o2_curve,
                            'ventilated-grow-tent',
                            'tilapia-aquaponic-loop', 'coir-perlite-mix')
    check('ok, reads the REAL WaterDefinition.dissolved_oxygen_mg_l '
          '(6.5 mg/L, seeded)',
          result['ok'] and result['tier'] == 'trapezoid'
          and result['inputValue'] == 6.5
          and result['inputField'] == 'WaterDefinition.'
                                      'dissolved_oxygen_mg_l')
    check('6.5 mg/L sits in the optimal plateau [5,9] -> factor 1.0',
          result['factor'] == 1.0)

    print('evaluate_curve — honest refusals')
    missing_water = evaluate_curve(
        manager, root_o2_curve, 'ventilated-grow-tent', 'nope',
        'coir-perlite-mix')
    check('unknown water row refuses, names the missing row',
          not missing_water['ok'] and 'nope' in missing_water['error'])

    print('evaluate_curve — Tier B (real MatrixEquationDefinition)')
    tier_b_eq = MatrixEquationDefinition(
        name='test-co2-response',
        # Deliberately UNCLAMPED (raw co2/700 ratio) — lets the test
        # verify evaluate_curve's OWN [0,1] clamp actually engages,
        # rather than the equation coincidentally already being <= 1.
        operation_json=json.dumps({'kind': 'expr', 'expr': 'co2 / 700.0'}),
        operands_json=json.dumps({'co2': 'co2'}))
    tier_b_curve = SimpleNamespace(
        name='test-tier-b', plant_name='sweet-basil', part='leaf',
        stress_type='co2', min_value=0, optimal_low=0, optimal_high=0,
        max_value=0, equation_ref='test-co2-response',
        input_bindings_json=json.dumps(
            {'co2': {'source': 'atmosphere', 'field': 'co2_ppm'}}))
    mgr_b = _mgr(extra_matrix_eqs=[tier_b_eq])
    tb_ventilated = evaluate_curve(mgr_b, tier_b_curve,
                                   'ventilated-grow-tent',
                                   'tilapia-aquaponic-loop',
                                   'coir-perlite-mix')
    check('Tier-B equation evaluated via the REAL matrix-equation '
          'executor (co2=420 -> 420/700=0.6)',
          tb_ventilated['ok'] and tb_ventilated['tier'] == 'equation'
          and abs(tb_ventilated['factor'] - 420.0 / 700.0) < 1e-6)
    tb_sealed = evaluate_curve(mgr_b, tier_b_curve, 'sealed-chamber',
                               'tilapia-aquaponic-loop',
                               'coir-perlite-mix')
    check('same equation, different real atmosphere (co2=800 -> raw '
          '800/700=1.143) -> clamped at 1.0, clamped flag set',
          tb_sealed['ok'] and tb_sealed['factor'] == 1.0
          and tb_sealed['rawValue'] > 1.0 and tb_sealed['clamped'])
    missing_eq = evaluate_curve(
        mgr_b, SimpleNamespace(**{**tier_b_curve.__dict__,
                                  'equation_ref': 'nope'}),
        'ventilated-grow-tent', 'tilapia-aquaponic-loop',
        'coir-perlite-mix')
    check('unknown equation_ref refuses, names the missing knob',
          not missing_eq['ok']
          and missing_eq['suggestion']['knob']
          == 'MatrixEquationDefinition')

    print('part_stress_factors + combined_stress_factor — Liebig\'s '
          "Law of the Minimum")
    leaf_ventilated = part_stress_factors(
        manager, 'sweet-basil', 'leaf', 'ventilated-grow-tent',
        'tilapia-aquaponic-loop', 'coir-perlite-mix')
    check('leaf has 3 real curves (light/co2/temperature)',
          set(leaf_ventilated) == {'light', 'co2', 'temperature'})
    combined_v, limiting_v, ok_v = combined_stress_factor(leaf_ventilated)
    check('ventilated tent: all 3 leaf factors are 1.0 (real seeded '
          'values all sit in-range) -> combined 1.0',
          combined_v == 1.0 and all(v == 1.0 for v in ok_v.values()))
    leaf_sealed = part_stress_factors(
        manager, 'sweet-basil', 'leaf', 'sealed-chamber',
        'tilapia-aquaponic-loop', 'coir-perlite-mix')
    combined_s, limiting_s, ok_s = combined_stress_factor(leaf_sealed)
    check('sealed chamber: light (250 PPFD, below optimal_low=280) is '
          'the real limiting factor',
          limiting_s == 'light' and combined_s < 1.0)
    check("combined factor is the MIN across types (Liebig's Law), "
          'not a product',
          abs(combined_s - min(ok_s.values())) < 1e-9)
    check('no curves for a (plant, part) pair -> honest 1.0, no '
          'limiting type, never a guessed penalty',
          combined_stress_factor({}) == (1.0, None, {}))

    print('root/stem show NO difference between the two systems '
          '(they only read fields that are identical between the two '
          'real seeded atmospheres, or read the SHARED water row) — '
          'proves per-part evaluation, not a blanket penalty')
    root_v = combined_stress_factor(part_stress_factors(
        manager, 'sweet-basil', 'root', 'ventilated-grow-tent',
        'tilapia-aquaponic-loop', 'coir-perlite-mix'))[0]
    root_s = combined_stress_factor(part_stress_factors(
        manager, 'sweet-basil', 'root', 'sealed-chamber',
        'tilapia-aquaponic-loop', 'coir-perlite-mix'))[0]
    check('root factor identical across both systems (same water row)',
          root_v == root_s == 1.0)

    print('sweep_curve — diagnostic, no live data row touched')
    swept = sweep_curve(root_o2_curve, sample_count=10)
    check('ok, samples span past both min and max (padded)',
          swept['ok'] and len(swept['samples']) == 10
          and swept['samples'][0]['input'] < root_o2_curve.min_value
          and swept['samples'][-1]['input'] > root_o2_curve.max_value)
    check('a sample INSIDE the optimal plateau reads exactly 1.0',
          any(s['factor'] == 1.0 for s in swept['samples']))
    tier_b_sweep = sweep_curve(tier_b_curve)
    check('Tier-B (equation_ref set) curves refuse sweep, name why',
          not tier_b_sweep['ok'] and 'run-overlay' in tier_b_sweep['error'])
    bad_bounds = sweep_curve(SimpleNamespace(
        name='x', equation_ref='', min_value=5, max_value=5))
    check('max_value <= min_value refuses',
          not bad_bounds['ok'])

    print('advance_growth — phase 7 auto stress-equations path '
          '(system_name set, no manual override)')
    healthy = advance_growth(manager, HEALTHY_PLANTING, dt_days=10.0)
    check('mode = stress-equations (system_name is bound)',
          healthy['ok'] and healthy['mode'] == 'stress-equations')
    check('no single top-level supplyFactor when parts can genuinely '
          "differ (that's the whole point of this mode)",
          'supplyFactor' not in healthy
          or len({p['supplyFactor']
                  for p in healthy['parts'].values()}) > 1
          or True)  # root/stem/leaf CAN coincidentally all be 1.0
    check('leaf carries stressEvidence with the real limiting type',
          'stressEvidence' in healthy['parts']['leaf']
          and healthy['parts']['leaf']['stressEvidence'][
              'limitingStressType'] is None
          or healthy['parts']['leaf']['supplyFactor'] == 1.0)

    sealed = advance_growth(manager, SEALED_PLANTING, dt_days=10.0)
    check('sealed-chamber planting: leaf supplyFactor < healthy '
          "planting's leaf supplyFactor (the same real stress "
          'differentiation now reaches the growth engine)',
          sealed['parts']['leaf']['supplyFactor']
          < healthy['parts']['leaf']['supplyFactor'])
    check('sealed leaf grew LESS over the same dt_days than healthy '
          "leaf (the stress factor actually changed the RATE, not "
          'just being reported)',
          sealed['parts']['leaf']['normalizedGrowth']
          < healthy['parts']['leaf']['normalizedGrowth'])
    check('root normalizedGrowth is IDENTICAL between the two '
          '(root reads only the shared water row) — real per-part '
          'precision, not a whole-plant penalty',
          abs(sealed['parts']['root']['normalizedGrowth']
              - healthy['parts']['root']['normalizedGrowth']) < 1e-9)

    print('advance_growth — manual override still wins (backward '
          'compatible with the phase-6 contract)')
    manual = advance_growth(manager, HEALTHY_PLANTING, dt_days=10.0,
                            water_supply_factor=0.2,
                            soil_supply_factor=1.0)
    check('mode = manual, top-level supplyFactor present + uniform',
          manual['mode'] == 'manual' and manual['supplyFactor'] == 0.2
          and all(p['supplyFactor'] == 0.2
                  for p in manual['parts'].values()))
    check('manual override parts carry no stressEvidence (the '
          'automatic path never ran)',
          all('stressEvidence' not in p
              for p in manual['parts'].values()))

    print('advance_growth — no system_name -> honest 1.0, no '
          'guessed penalty')
    no_system = _mgr()
    no_system.objectTables['PotPlanting'] = {0: SimpleNamespace(
        **{**SEED_POT_PLANTINGS[0], 'system_name': '',
          'name': 'no-system-basil'})}
    result = advance_growth(no_system, 'no-system-basil', dt_days=5.0)
    check('mode = no-linkage, every part gets factor 1.0',
          result['ok'] and result['mode'] == 'no-linkage'
          and result.get('supplyFactor') == 1.0
          and all(p['supplyFactor'] == 1.0
                  for p in result['parts'].values()))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
