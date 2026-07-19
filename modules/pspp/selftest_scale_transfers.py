"""
Self-test for pspp-5 scale transfers: validation against known
methods, per-state lineage summaries, and the wax retrofit seeds
citing the live msim models.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_scale_transfers
"""

import sys
from types import SimpleNamespace

from pspp.scale_transfers import (
    SEED_SCALE_TRANSFERS, transfers_for_state, validate_transfer,
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


def test_seeds_and_validation():
    print('[wax retrofit seeds + validation]')
    for seed in SEED_SCALE_TRANSFERS:
        check(f"seed {seed['name']!r} validates",
              validate_transfer(seed)['ok'])
    check('wax transfers cite the LIVE msim models (behavior '
          'unchanged)', all(
              seed['transfer_method'].startswith('model:')
              for seed in SEED_SCALE_TRANSFERS))
    check('canonical-state subjects (invariant I1)', all(
        '#as-defined' in seed['source_state_key']
        for seed in SEED_SCALE_TRANSFERS))

    bad = dict(SEED_SCALE_TRANSFERS[0], transfer_method='vibes')
    verdict = validate_transfer(bad)
    check('unknown method refused naming the option kinds',
          verdict['ok'] is False and 'engine key' in verdict['refusal'])
    check('evidence-method transfers allowed (rules-of-mixtures)',
          validate_transfer(dict(SEED_SCALE_TRANSFERS[0],
                                 transfer_method='rules-of-mixtures'))
          ['ok'])
    check('bare material name refused as state key',
          validate_transfer(dict(SEED_SCALE_TRANSFERS[0],
                                 source_state_key='paraffin-wax'))
          ['ok'] is False)
    check('out-of-range scale refused',
          validate_transfer(dict(SEED_SCALE_TRANSFERS[0],
                                 target_scale=7))['ok'] is False)


def test_state_lineage():
    print('[per-state lineage]')
    rows = {s['name']: SimpleNamespace(**s)
            for s in SEED_SCALE_TRANSFERS}
    manager = SimpleNamespace(
        objectTables={'ScaleTransferDefinition': rows})
    lineage = transfers_for_state(manager, 'paraffin-wax#as-defined')
    check('both wax transfers found for the canonical state',
          len(lineage) == 2)
    check('summaries carry method + transported + assumptions', all(
        t['method'] and t['transported'] and t['assumptions']
        for t in lineage))
    check('unrelated state sees nothing',
          transfers_for_state(manager, 'beeswax#as-defined') == [])


def main():
    test_seeds_and_validation()
    test_state_lineage()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
