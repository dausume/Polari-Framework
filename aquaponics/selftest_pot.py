"""
Selftest — aqp-1: self-watering pot geometry + gravity constraint.

Run from polari-framework/:
    python3 -m aquaponics.selftest_pot

Covers: the valid reference pot passes clean and reports its
maintained water level + opposite-side separation; the broken pot
raises exactly the gravity/placement findings it should (output
uphill, inputs not above outputs, same-side); per-hole limits (angle
cap, breaches base, over rim); generate_holes always yields an
invariant-satisfying set that validates clean; size-scaled pair
suggestion; honest refusals.
"""

from types import SimpleNamespace

from aquaponics.pot_geometry import (
    generate_holes, recommend_pair_count, validate_pot,
)
from aquaponics.pot_seed import SEED_POTS, SEED_POT_HOLES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(pots=None, holes=None):
    return SimpleNamespace(objectTables={
        'PotDefinition': _rows(pots if pots is not None
                               else SEED_POTS),
        'PotHole': _rows(holes if holes is not None
                         else SEED_POT_HOLES),
    })


def _kinds(report):
    return {f['kind'] for f in report['findings']}


if __name__ == '__main__':
    print('\naqp-1: self-watering pot geometry\n')

    print('valid reference pot')
    m = _mgr()
    report = validate_pot(m, 'demo-herb-pot')
    check('passes clean (no findings)',
          report['ok'] and report['valid'],
          str([f['kind'] for f in report['findings']]))
    check('2 inputs + 2 outputs counted',
          report['holeCounts'] == {'input': 2, 'output': 2})
    check('maintained water level = lowest output lower lip (39mm)',
          report['maintainedWaterLevelMm'] == 39.0,
          str(report['maintainedWaterLevelMm']))
    check('inputs and outputs read as opposite sides (~180 apart)',
          abs(report['sideSeparationDeg'] - 180.0) < 1e-6)

    print('\nbroken pot (validator exercise)')
    report = validate_pot(m, 'demo-broken-pot')
    kinds = _kinds(report)
    check('output uphill flagged (not gravity-fed)',
          'output-not-gravity-fed' in kinds)
    check('inputs-not-above-output flagged',
          'input-not-above-output' in kinds)
    check('same-side (not-opposite-sides) flagged',
          'not-opposite-sides' in kinds)
    check('the pot is reported invalid',
          not report['valid'])
    check('every finding names a knob',
          all('knob' in f['suggestion'] for f in report['findings']))

    print('\nper-hole limits')
    pot = [{'name': 'p', 'shape': 'cylinder',
            'outer_top_diameter_mm': 200.0,
            'outer_base_diameter_mm': 200.0, 'height_mm': 250.0,
            'wall_thickness_mm': 8.0, 'base_thickness_mm': 12.0}]
    holes = [
        {'name': 'p-in', 'pot_name': 'p', 'kind': 'input',
         'diameter_mm': 10.0, 'height_mm': 200.0, 'azimuth_deg': 0.0,
         'angle_deg': 45.0},   # over the angle limit
        {'name': 'p-out', 'pot_name': 'p', 'kind': 'output',
         'diameter_mm': 12.0, 'height_mm': 14.0, 'azimuth_deg': 180.0,
         'angle_deg': 2.0},   # lower lip 8mm < base 12mm
        {'name': 'p-rim', 'pot_name': 'p', 'kind': 'input',
         'diameter_mm': 10.0, 'height_mm': 248.0, 'azimuth_deg': 90.0,
         'angle_deg': 0.0},   # upper lip 253mm > height 250mm
    ]
    report = validate_pot(_mgr(pot, holes), 'p')
    kinds = _kinds(report)
    check('angle over +/-30 deg flagged', 'angle-exceeds-limit' in kinds)
    check('hole breaching the base flagged', 'breaches-base' in kinds)
    check('hole over the rim flagged', 'over-rim' in kinds)

    print('\ngenerate_holes always satisfies the invariant')
    pot_row = SimpleNamespace(**SEED_POTS[0])
    for n in (1, 2, 3):
        specs = generate_holes(pot_row, n_pairs=n)
        gen_mgr = _mgr([SEED_POTS[0]], specs)
        report = validate_pot(gen_mgr, 'demo-herb-pot')
        check(f'{n} generated pair(s) → valid pot',
              report['valid'] and report['holeCounts']
              == {'input': n, 'output': n},
              str([f['kind'] for f in report['findings']]))
    specs = generate_holes(pot_row, n_pairs=1)
    check('generated inputs are high, outputs low',
          all(s['height_mm'] > 150 for s in specs
              if s['kind'] == 'input')
          and all(s['height_mm'] < 80 for s in specs
                  if s['kind'] == 'output'))
    check('generated outputs are downhill (gravity-fed)',
          all(s['angle_deg'] >= 0 for s in specs
              if s['kind'] == 'output'))

    print('\nsize-scaled suggestions + refusals')
    big = SimpleNamespace(outer_top_diameter_mm=600.0,
                          outer_base_diameter_mm=600.0)
    small = SimpleNamespace(outer_top_diameter_mm=120.0,
                            outer_base_diameter_mm=120.0)
    check('bigger pot suggests more hole pairs',
          recommend_pair_count(big) > recommend_pair_count(small))
    report = validate_pot(_mgr(), 'no-such-pot')
    check('unknown pot honest 404 with known list',
          not report['ok'] and 'demo-herb-pot' in report['knownPots'])
    report = validate_pot(_mgr([SEED_POTS[0]], []), 'demo-herb-pot')
    check('pot with no holes flags no-input + no-output',
          {'no-input-hole', 'no-output-hole'} <= _kinds(report))

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
