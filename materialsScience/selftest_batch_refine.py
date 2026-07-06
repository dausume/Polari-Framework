"""
Self-test for batch-incremental refinement (msci-10).

Run from polari-framework/:
    python3 -m materialsScience.selftest_batch_refine
"""

import sys

from materialsScience.batch_refine import gap_analysis, refine_formulation
from materialsScience.composite_search import (
    load_legacy_seed_data, normalize_targets,
)
from materialsScience.thermal_windows import (
    SEED_THERMAL_PROFILES, profiles_from_rows,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


DATA = load_legacy_seed_data()
BASE = {'ShrinkageRate': 3.0, 'FlexuralModulus': 40.0}
TARGETS = normalize_targets([
    {'propertyName': 'ShrinkageRate', 'optimumValue': 1.0,
     'optimumRangeMin': 0.5, 'optimumRangeMax': 2.0,
     'hardMinimum': 0.0, 'hardMaximum': 2.0, 'weight': 1.0},
    {'propertyName': 'FlexuralModulus', 'optimumValue': 90.0,
     'optimumRangeMin': 60.0, 'optimumRangeMax': 120.0,
     'hardMinimum': 20.0, 'hardMaximum': 300.0, 'weight': 1.0},
])


def test_stepping():
    print('[batch stepping hits targets]')
    result = refine_formulation(BASE, TARGETS, DATA['additives'],
                                DATA['effects'], loadingStep=2.5)
    check('outcome met', result['outcome'] == 'met')
    check('best meets with no violations',
          result['best']['meets'] and result['best']['violations'] == [])
    check('trajectory starts at start and improves monotonically',
          result['trajectory'][0]['move'] == 'start' and all(
              result['trajectory'][i]['score']
              <= result['trajectory'][i + 1]['score']
              for i in range(len(result['trajectory']) - 1)))
    check('every step names its move', all(
        t['move'] for t in result['trajectory']))
    # A tight optimum band no single 2.5% increment can land in —
    # forces genuine multi-batch stepping.
    tight = normalize_targets([
        {'propertyName': 'ShrinkageRate', 'optimumValue': 0.5,
         'optimumRangeMin': 0.4, 'optimumRangeMax': 0.6,
         'hardMinimum': 0.0, 'hardMaximum': 2.0, 'weight': 1.0}])
    stepped = refine_formulation(BASE, tight, DATA['additives'],
                                 DATA['effects'], loadingStep=2.5)
    check('tight band takes multiple batches',
          stepped['outcome'] == 'met' and stepped['batches'] >= 2)
    check('tight-band result inside the band',
          0.4 <= stepped['best']['predicted']['ShrinkageRate'] <= 0.6)


def test_convergence_and_gaps():
    print('[closest-approach + gap analysis when targets unreachable]')
    impossible = normalize_targets([
        {'propertyName': 'ShrinkageRate', 'optimumValue': -5.0,
         'weight': 1.0},   # nothing can push shrinkage to -5
        {'propertyName': 'MeltingPoint', 'optimumValue': 62.0,
         'weight': 1.0},   # nothing quantified moves MeltingPoint
    ])
    result = refine_formulation(BASE, impossible, DATA['additives'],
                                DATA['effects'], maxBatches=25)
    check('outcome converged (honest best-effort)',
          result['outcome'] in ('converged', 'batch-limit'))
    check('best still returned with a score',
          0.0 <= result['best']['score'] <= 1.0)
    gaps = result['gapAnalysis']
    unpredicted = [g for g in gaps if g['status'] == 'unpredicted']
    check('unpredicted target named with evidence',
          len(unpredicted) == 1
          and unpredicted[0]['propertyName'] == 'MeltingPoint'
          and 'cannot see it' in unpredicted[0]['evidence'])
    offTarget = [g for g in gaps if g['status'] == 'off-target']
    check('off-target gap carries delta + movers', all(
        'delta' in g and isinstance(g['movers'], list)
        for g in offTarget))


def test_thermal_gate_in_refinement():
    print('[thermal gate steers the steps]')
    profiles = profiles_from_rows(SEED_THERMAL_PROFILES)
    result = refine_formulation(
        BASE, TARGETS, DATA['additives'], DATA['effects'],
        loadingStep=2.5, process='3d-print',
        base_material_name='beeswax', thermal_profiles=profiles)
    check('gated refinement still reaches an outcome',
          result['outcome'] in ('met', 'converged', 'batch-limit'))
    best = result['best']
    check('winner (if met) has an open window',
          result['outcome'] != 'met' or best['thermal']['ok'])
    check('components all thermally accounted', 'thermal' in best)


def main():
    test_stepping()
    test_convergence_and_gaps()
    test_thermal_gate_in_refinement()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
