"""
Self-test for mtt-2 ceramics escalation ladder: the geopolymer-oven ->
steelmaking bootstrapping path, its physical-consistency validation
(lining fireable below + surviving here), the bio-galvanized-steel
unlock, and the honest CNT-atmosphere branch.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_ceramics_ladder
"""

import sys

from pspp.ceramics_ladder import (
    SEED_LADDER_RUNGS, ladder_path, rung_unlocking, validate_ladder,
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


def test_path():
    print('[ladder: the bootstrapping climb]')
    path = ladder_path()
    main = [r for r in path if r['gateKind'] == 'thermal']
    check('the climb starts at the geopolymer oven (no prerequisite)',
          main[0]['name'] == 'geopolymer-oven'
          and main[0]['prerequisiteRung'] == '')
    # Temperatures escalate up to the refractory furnace; the final
    # steelmaking rung is LINING-CHEMISTRY-gated (basic refractory),
    # not hotter — so the climb is not strictly monotonic at the top.
    climb = [r for r in main if r['name'] != 'steelmaking-furnace']
    check('temperatures escalate along the thermal climb (to the '
          'refractory furnace)',
          [r['maxTempC'] for r in climb]
          == sorted(r['maxTempC'] for r in climb))
    check('each thermal rung (after the first) names its prerequisite',
          all(r['prerequisiteRung'] for r in main[1:]))
    check('the top rung is the steelmaking furnace (lining-gated)',
          main[-1]['name'] == 'steelmaking-furnace')


def test_steel_unlock():
    print('[ladder: bio-galvanized-steel unlock]')
    hit = rung_unlocking('bio-galvanized-steel')
    check('bio-galvanized-steel is unlocked by the steelmaking furnace',
          hit['ok'] and hit['rung'] == 'steelmaking-furnace')
    steel = next(r for r in ladder_path()
                 if r['name'] == 'steelmaking-furnace')
    tracks = {opt['track'] for opt in steel['liningOptions']}
    check('steel furnace offers BOTH a local and a non-local lining',
          tracks == {'local', 'non-local'})
    olivine = next(o for o in steel['liningOptions']
                   if o['sample'] == 'forsterite-olivine')
    check('the non-local option is the olivine forsterite lining',
          olivine['track'] == 'non-local')


def test_cnt_branch_is_honest():
    print('[ladder: CNT branch — reachable temp, specialized gate]')
    cnt = next(r for r in ladder_path()
               if r['name'] == 'cnt-cvd-reactor')
    check('CNT rung is gated by ATMOSPHERE, not temperature',
          cnt['gateKind'] == 'atmosphere')
    check('its temperature is modest + reachable mid-ladder',
          cnt['maxTempC'] <= 1200)
    check('it branches off the firebrick furnace, not the top',
          cnt['prerequisiteRung'] == 'firebrick-furnace')
    check('notes are explicit that heat is not the real gate',
          'not just a hotter furnace' in cnt['notes'])


def test_bootstrapping_consistency():
    print('[ladder: physical bootstrapping consistency]')
    result = validate_ladder()
    errors = [f for f in result['findings']
              if f['severity'] == 'error']
    check('no rung requires a lining that cannot survive it '
          '(no errors)', result['ok'] and not errors)
    check('validation explains the fireable-below + survive-here rule',
          'SURVIVE' in result['note'] or 'survive' in result['note'])
    # Deliberately break it: a lining that melts below its rung.
    from pspp.ceramics_samples import SEED_CERAMIC_SAMPLES
    broken = [dict(s) for s in SEED_CERAMIC_SAMPLES]
    for s in broken:
        if s['name'] == 'forsterite-olivine':
            s['max_service_temp_c'] = 500.0  # can't survive 1650
    bad = validate_ladder(samples=broken)
    check('a lining that fails its rung is caught as an error',
          any(f['severity'] == 'error'
              and f['lining'] == 'forsterite-olivine'
              for f in bad['findings']))


def main():
    test_path()
    test_steel_unlock()
    test_cnt_branch_is_honest()
    test_bootstrapping_consistency()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
