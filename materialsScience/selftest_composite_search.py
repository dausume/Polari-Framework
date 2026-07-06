"""
Self-test for the wax-composite target search (msci-5, Track C).

Run from polari-framework/:
    python3 -m materialsScience.selftest_composite_search
"""

import sys

from materialsScience.composite_search import (
    load_legacy_seed_data, normalize_targets, predictable_properties,
    search_composites, search_for_profile,
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


def test_seed_loading():
    print('[legacy seed loading]')
    data = load_legacy_seed_data()
    check('28 additives', len(data['additives']) == 28)
    check('62 effects', len(data['effects']) == 62)
    props = predictable_properties(data['effects'])
    check('predictable properties are the quantified four',
          props == ['FlexuralModulus', 'ShrinkageRate',
                    'ThermalConductivity', 'Viscosity'])
    normalized = normalize_targets(
        [t for t in data['targets']
         if t['profileId'] == 'profile-min-viable-wax-filament'])
    shrink = next(t for t in normalized
                  if t['propertyName'] == 'ShrinkageRate')
    check('hard bound 0.0 normalized to None (seed convention)',
          shrink['hardMinimum'] is None and shrink['hardMaximum'] == 2.0)


def test_winnable_search():
    print('[winnable search — synthetic 2-target wax profile]')
    data = load_legacy_seed_data()
    # Base wax: shrinkage too high (3.0 vs hard max 2.0), modulus low.
    base = {'ShrinkageRate': 3.0, 'FlexuralModulus': 40.0}
    targets = normalize_targets([
        {'propertyName': 'ShrinkageRate', 'optimumValue': 1.0,
         'optimumRangeMin': 0.5, 'optimumRangeMax': 2.0,
         'hardMinimum': 0.0, 'hardMaximum': 2.0, 'weight': 1.0},
        {'propertyName': 'FlexuralModulus', 'optimumValue': 90.0,
         'optimumRangeMin': 60.0, 'optimumRangeMax': 120.0,
         'hardMinimum': 20.0, 'hardMaximum': 300.0, 'weight': 1.0},
    ])
    result = search_composites(base, targets, data['additives'],
                               data['effects'], data['compatibilizers'],
                               maxAdditives=2, loadingStep=5.0)
    check('candidates evaluated', result['evaluated'] > 100)
    check('sweep not capped', not result['sweepCapped'])
    check('winners found', len(result['winners']) > 0)
    best = result['ranked'][0]
    check('best candidate meets all targets', best['meets'])
    check('best fixes the shrinkage hard bound',
          best['predicted']['ShrinkageRate'] <= 2.0)
    check('best raises modulus into range',
          60.0 <= best['predicted']['FlexuralModulus'] <= 120.0)
    check('no violations on the winner', best['violations'] == [])
    check('assumptions declared',
          any('manually supplied' in a for a in result['assumptions']))

    # Base already fails hard max; a no-additive formulation can't win —
    # every winner must actually contain additives.
    check('winners contain additives', all(
        len(w['components']) >= 1 for w in result['winners']))

    firstWinner = search_composites(
        base, targets, data['additives'], data['effects'],
        data['compatibilizers'], stopPolicy='first-winner',
        continueAfterWinner=False)
    check('first-winner stops early',
          firstWinner['evaluated'] < result['evaluated']
          and len(firstWinner['winners']) == 1)

    capped = search_composites(
        base, targets, data['additives'], data['effects'],
        data['compatibilizers'], maxCandidates=50)
    check('sweep cap reported, never silent',
          capped['sweepCapped'] and capped['evaluated'] == 50)


def test_honest_mvw_run():
    print('[Minimum Viable Wax Filament — honest data-gap reporting]')
    result = search_for_profile(
        'profile-min-viable-wax-filament',
        base_properties={'ShrinkageRate': 3.0, 'FlexuralModulus': 40.0})
    check('profile search runs', result['ok'])
    best = result['ranked'][0]
    check('4 targets honestly unpredicted (seed data gap)',
          sorted(best['unpredicted']) == [
              'AirSolidificationRate', 'ExtrusionPressure',
              'LayerAdhesionStrength', 'ShoreHardness'])
    check('nothing meets while data is missing',
          len(result['winners']) == 0)
    check('but ranking still orders by predictable score',
          best['score'] >= result['ranked'][-1]['score'])

    missing = search_for_profile('profile-does-not-exist', {})
    check('unknown profile lists known ones',
          missing['ok'] is False
          and 'profile-min-viable-wax-filament' in missing['knownProfiles'])


def main():
    test_seed_loading()
    test_winnable_search()
    test_honest_mvw_run()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
