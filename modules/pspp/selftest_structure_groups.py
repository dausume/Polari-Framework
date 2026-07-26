"""
Self-test for pspp.structure_groups (gsp-1/gsp-4) — most-likely
motif rankings from the reference curves and from state descriptors,
plus every honest refusal.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_structure_groups
"""

import json
import sys
from types import SimpleNamespace

from pspp.structure_groups import (
    MOTIFS,
    most_likely_groups,
    reference_groups,
    state_groups,
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


def test_reference_glass():
    print('[reference mode — glass curves]')
    for cation in ('Na', 'K'):
        verdict = reference_groups(cation, 1.0)
        check(f'{cation} mr=1.0 ok', verdict.get('ok') is True)
        if not verdict.get('ok'):
            continue
        groups = verdict['groups']
        check(f'{cation} five motifs ranked',
              [g['motif'] for g in groups
               if g['motif'] in MOTIFS] == [g['motif'] for g in groups]
              and len(groups) == 5)
        total = sum(g['fraction'] for g in groups)
        # payload fractions are rounded to 4 dp — allow that drift
        check(f'{cation} fractions sum ~1 (got {total:.4f})',
              abs(total - 1.0) < 5e-4)
        check(f'{cation} ranks strictly ordered',
              all(groups[i]['fraction'] >= groups[i + 1]['fraction']
                  for i in range(len(groups) - 1)))
        check(f'{cation} descriptions attached',
              all(g['description'] for g in groups))


def test_reference_solution():
    print('[reference mode — solution (Table 5.6)]')
    verdict = reference_groups('Na', 2.0, physical_state='solution')
    check('Na solution at listed MR ok', verdict.get('ok') is True)
    if verdict.get('ok'):
        check('Q4 artifact caveat rides along',
              any('artifact' in c for c in verdict['caveats']))
    k_verdict = reference_groups('K', 2.0, physical_state='solution')
    check('K solution refuses (Na-only mapping)',
          k_verdict.get('ok') is False
          and 'Na' in k_verdict.get('refusal', ''))


def test_reference_refusals():
    print('[reference mode — refusals]')
    bad_cation = reference_groups('Cs', 1.0)
    check('unknown cation refuses with suggestion',
          bad_cation.get('ok') is False
          and bad_cation.get('suggestion'))
    out_of_range = reference_groups('Na', 99.0)
    check('out-of-domain MR refuses',
          out_of_range.get('ok') is False)
    bad_state = reference_groups('Na', 1.0, physical_state='plasma')
    check('unknown physicalState refuses',
          bad_state.get('ok') is False)
    neither = most_likely_groups()
    check('no-args dispatcher refuses with both modes named',
          neither.get('ok') is False
          and 'cation' in neither.get('suggestion', ''))


def _manager(descriptors=None):
    tables = {
        'MaterialsScienceMaterial': {
            '1': SimpleNamespace(name='test-geo')},
        'MaterialState': {},
        'ScaleStructureDefinition': {},
    }
    if descriptors is not None:
        tables['ScaleStructureDefinition']['1'] = SimpleNamespace(
            name='test-geo-structure-L2',
            state_key='test-geo#as-defined',
            scale_level=2, domain_type='gel',
            status='partial',
            descriptors_json=json.dumps(descriptors))
    return SimpleNamespace(objectTables=tables)


def test_state_mode():
    print('[state mode — qDistribution descriptor (gsp-4)]')
    unknown = state_groups(_manager(), 'no-such-material')
    check('unknown material refuses', unknown.get('ok') is False)

    bare = state_groups(_manager(), 'test-geo')
    check('state without descriptor refuses naming the knob',
          bare.get('ok') is False
          and 'qDistribution' in bare.get('refusal', '')
          and 'ScaleStructureDefinition' in bare.get('suggestion', ''))

    manager = _manager({'qDistribution':
                        {'Q0': 5, 'Q1': 10, 'Q2': 42,
                         'Q3': 28, 'Q4': 15}})
    verdict = state_groups(manager, 'test-geo')
    check('percent-scaled descriptor accepted',
          verdict.get('ok') is True)
    if verdict.get('ok'):
        check('Q2 ranks first',
              verdict['groups'][0]['motif'] == 'Q2')
        check('normalization recorded in assumptions',
              isinstance(verdict['assumptions'], list))
        check('source row named',
              verdict['sourceRow'] == 'test-geo-structure-L2')

    broken = _manager({'qDistribution': {'Q0': -1, 'Q2': 3}})
    bad = state_groups(broken, 'test-geo')
    check('malformed descriptor refuses pointing at the row',
          bad.get('ok') is False
          and 'test-geo-structure-L2' in bad.get('suggestion', ''))


def main():
    test_reference_glass()
    test_reference_solution()
    test_reference_refusals()
    test_state_mode()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
