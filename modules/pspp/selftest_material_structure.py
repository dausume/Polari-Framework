"""
Self-test for pspp-3 structure layer: state-attached structure rows,
L2 multi-domain, the 5-descriptor mandatory core, and the
require_descriptors gate refusing with the exact knob.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_material_structure
"""

import json
import sys
from types import SimpleNamespace

from pspp.material_structure import (
    L2_DOMAIN_TYPES, MANDATORY_DESCRIPTORS, descriptors_for_state,
    require_descriptors, structure_profile,
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


GP = 'metakaolin-geopolymer#cured-solid'


def _row(name, state, level, domain='', status='defined', **descriptors):
    return SimpleNamespace(
        name=name, state_key=state, scale_level=level,
        domain_type=domain, characteristic_length_min_m=0.0,
        characteristic_length_max_m=0.0,
        representation_type='descriptor-summary',
        representation_class='', representation_ref='',
        descriptors_json=json.dumps(descriptors), status=status,
        provenance_id='', notes='')


def _manager():
    rows = {
        # L0 measured core.
        f'{GP}@L0': _row(f'{GP}@L0', GP, 0,
                         bulkDensity=1850.0, totalPorosity=0.28,
                         moistureState='saturated',
                         reactionExtent=0.85),
        # L2: TWO domain rows for the same state+level (the design).
        f'{GP}@L2-gel': _row(
            f'{GP}@L2-gel', GP, 2, domain='gel-domain',
            phaseFractions={'gel': 0.62, 'unreacted-mk': 0.15,
                            'quartz': 0.23}),
        f'{GP}@L2-pores': _row(
            f'{GP}@L2-pores', GP, 2, domain='capillary-pore',
            openPorosity=0.19, connectedPorosity=0.11),
        # planned row: schema present, honestly absent from queries.
        f'{GP}@L3': _row(f'{GP}@L3', GP, 3, status='planned',
                         qDistribution={'Q4': 0.8}),
    }
    return SimpleNamespace(
        objectTables={'ScaleStructureDefinition': rows})


def test_core_and_domains():
    print('[mandatory core + L2 domains]')
    check('mandatory core is exactly the converged five',
          MANDATORY_DESCRIPTORS == (
              'bulkDensity', 'phaseFractions', 'totalPorosity',
              'moistureState', 'reactionExtent'))
    check('book-grounded L2 domain vocabulary present', all(
        d in L2_DOMAIN_TYPES for d in
        ('gel-domain', 'capillary-pore', 'reaction-rim',
         'microcrack-network')))
    manager = _manager()
    have = descriptors_for_state(manager, GP)
    check('descriptors merge across rows (L0 + both L2 domains)',
          have['bulkDensity']['value'] == 1850.0
          and have['phaseFractions']['domainType'] == 'gel-domain'
          and have['connectedPorosity']['sourceRow'] == f'{GP}@L2-pores')
    check("'planned' rows are absent from queries (gates treat as "
          'missing)', 'qDistribution' not in have)
    domainOnly = descriptors_for_state(manager, GP, scale_level=2,
                                       domain_type='capillary-pore')
    check('domain-scoped query sees only its domain',
          sorted(domainOnly) == ['connectedPorosity', 'openPorosity'])


def test_profile_and_gate():
    print('[profile + require_descriptors gate]')
    manager = _manager()
    profile = structure_profile(manager, GP)
    check('profile reports full mandatory-core coverage',
          all(profile['mandatoryCore'].values()))
    check('profile lists all rows incl. planned',
          len(profile['rows']) == 4)

    water = require_descriptors(
        manager, GP, ('openPorosity', 'connectedPorosity'))
    check('water-transport needs met (engine-declared requirements)',
          water['ok'])

    elastic = require_descriptors(
        manager, GP, ('bulkDensity', 'phaseFractions', 'totalPorosity',
                      'microcrackDensity'))
    check('missing microcrackDensity refused naming the descriptor',
          elastic['ok'] is False
          and elastic['missing'] == ['microcrackDensity'])
    check('refusal suggestion points at the descriptors_json knob',
          'descriptors_json' in elastic['suggestion'])

    empty = require_descriptors(manager,
                                'beeswax#as-defined', ('bulkDensity',))
    check('state with no structure rows refused, not defaulted',
          empty['ok'] is False)


def main():
    test_core_and_domains()
    test_profile_and_gate()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
