"""
Self-test for the pspp-11 wax half: feedstock → virtual state routes,
zero behavior change (canonical resolution untouched, no writes).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_wax_states
"""

import sys
from types import SimpleNamespace

from pspp.wax_states import feedstock_state_route, wax_state_map

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


def test_route():
    print('[one feedstock route]')
    from waxprint.waxprint_seed import SEED_FEEDSTOCKS
    mvw = next(f for f in SEED_FEEDSTOCKS
               if f['name'] == 'mvw-natural-blend')
    route = feedstock_state_route(mvw)
    check('route ok', route['ok'])
    stages = [s['processingStage'] for s in route['states']]
    check('four wax stages in order',
          stages == ['wax-solid', 'wax-softened', 'wax-melt',
                     'wax-superheated'])
    check('states chain solid→…→superheated',
          route['states'][3]['parents']
          == [route['states'][2]['stateKey']])
    check('bounds come from the feedstock row itself',
          route['states'][2]['environmentalSnapshot']
          == {'temperature_c_min': 95.0, 'temperature_c_max': 160.0})
    check('all states virtual (zero writes, zero behavior change)',
          all(s['virtual'] for s in route['states']))
    check('superheated state exists to be citable by refusals',
          'REFUSED' in route['states'][3]['note'])
    orphan = feedstock_state_route({'name': 'ghost',
                                    'wax_material_ref': ''})
    check('feedstock without a material ref refused',
          orphan['ok'] is False)


def test_map_and_zero_behavior():
    print('[map + zero behavior change]')
    m = SimpleNamespace(objectTables={}, idList=[], db=None)
    mapped = wax_state_map(m)
    check('seed fallback maps every feedstock',
          mapped['ok'] and len(mapped['routes']) >= 4)
    check('nothing was written anywhere',
          m.objectTables == {})
    from pspp.state_resolution import resolve_state
    m2 = SimpleNamespace(objectTables={
        'MaterialsScienceMaterial': {
            'w': SimpleNamespace(name='beeswax')},
        'MaterialState': {}}, idList=[], db=None)
    resolved = resolve_state(m2, 'beeswax')
    check('canonical resolution unchanged (waxprint *_ref path '
          'untouched)', resolved['ok']
          and resolved['stateKey'] == 'beeswax#as-defined')


def main():
    test_route()
    test_map_and_zero_behavior()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
