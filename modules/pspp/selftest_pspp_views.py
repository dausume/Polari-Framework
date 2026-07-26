"""
Self-test for the PSPP view-builders + progress engine v1 — the
chart payloads the frontend proofs against the book, and the
measured-curve-only cure progress with its honest refusals.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_pspp_views
"""

import sys
from types import SimpleNamespace

from pspp.pspp_views import (
    dataset_catalog, dataset_curve, grade_payload, network_graph,
    state_dag,
)
from pspp.progress_engine import cure_progress

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


EMPTY = SimpleNamespace(objectTables={})


def test_catalog_and_curves():
    print('[dataset catalog + curves]')
    catalog = dataset_catalog(EMPTY)
    check('catalog serves all 13 datasets from seeds when no live '
          'rows exist', catalog['ok']
          and len(catalog['datasets']) == 13)
    check('every catalog entry carries citation + validity + '
          'digitization honesty', all(
              d['source'] and d['extrapolationPolicy'] == 'UNSUPPORTED'
              for d in catalog['datasets']))

    q = dataset_curve(EMPTY, 'na-glass-q-distribution-vs-mr')
    check('Q-curve payload: source points + sampled band curve',
          q['ok'] and len(q['series']) == 1
          and len(q['series'][0]['sourcePoints']) == 6
          and len(q['series'][0]['sampled']) == 61)
    mid = next(s for s in q['series'][0]['sampled']
               if abs(s['x'] - 1.5) < 0.03)
    check('sampled points carry per-point method + band',
          mid['method'] == 'interpolated' and 'Q3' in mid['band'])

    visc = dataset_curve(EMPTY,
                         'silicate-solution-viscosity-vs-temperature')
    check('viscosity splits into the two labeled series',
          visc['ok'] and sorted(s['series'] for s in visc['series'])
          == ['K-silicate MR=2.2', 'Na-silicate MR=2'])

    discrete = dataset_curve(EMPTY,
                             'mk750-k-silicate-setting-class-vs-mr')
    check('discrete dataset renders points only (no invented curve)',
          discrete['ok'] and discrete['series'][0]['sampled'] == [])

    sol = dataset_curve(EMPTY,
                        'na-siloxonate-solubility-vs-temperature')
    check('re-shot Fig 5.22 now renders three labeled series',
          sol['ok'] and len(sol['series']) == 3)
    check('unknown dataset refused with the catalog pointer',
          'catalog' in dataset_curve(EMPTY, 'nope')['suggestion'])


def test_network_and_grading():
    print('[network graph + composition grading]')
    net = network_graph(EMPTY)
    ruleNodes = [n for n in net['nodes'] if n['kind'] == 'rule']
    speciesIds = {n['id'] for n in net['nodes']
                  if n['kind'] == 'species'}
    from pspp.reaction_network import SEED_REACTION_RULES
    check('graph carries all seed rules + species',
          len(ruleNodes) == len(SEED_REACTION_RULES)
          and len(speciesIds) >= 25)
    check('every edge endpoint exists as a node', all(
        (e['from'] in speciesIds
         or any(n['id'] == e['from'] for n in ruleNodes))
        and (e['to'] in speciesIds
             or any(n['id'] == e['to'] for n in ruleNodes))
        for e in net['edges']))
    check('rule nodes carry evidence styling hooks (hypothesis, '
          'site, kinetics, stage index)', all(
              'hypothesisStatus' in n and 'siteConstraint' in n
              and n['stageIndex'] >= 0 for n in ruleNodes))

    graded = grade_payload(
        EMPTY, {'SiO2': 24.0, 'Al2O3': 10.2, 'Na2O': 6.8,
                'H2O': 59.0}, basis='mass', family='na-k-pss')
    check('mass-basis grading returns ratios + family windows',
          graded['ok'] and len(graded['windows']) == 4)
    check('families enumerated for the picker',
          graded['families'] == ['k-ps-kaliophilite', 'na-k-pss'])
    noFamily = grade_payload(EMPTY, {'SiO2': 50.0, 'H2O': 50.0})
    check('no family selected → grading refuses, names the families',
          noFamily['ok']
          and noFamily['grading']['ok'] is False
          and 'k-ps-kaliophilite' in noFamily['grading']['suggestion'])
    check('empty composition refused',
          grade_payload(EMPTY, {})['ok'] is False)


def test_states_and_progress():
    print('[state DAG + cure progress v1]')
    manager = SimpleNamespace(objectTables={
        'MaterialsScienceMaterial': {
            'mk-gp': SimpleNamespace(name='mk-gp')},
        'MaterialState': {},
    })
    dag = state_dag(manager, 'mk-gp')
    check('DAG serves the implicit canonical for a bare material',
          dag['ok'] and dag['states'][0]['virtual']
          and dag['edges'] == [])

    fast = cure_progress(EMPTY, 1.23)
    check('MR=1.23 at 80C: ultra-rapid, completes at 1h',
          fast['ok'] and fast['completionHours'] == 1.0
          and fast['curve'][-1]['reactionExtent'] == 1.0)
    slow = cure_progress(EMPTY, 1.83)
    check('MR=1.83 completes at 4h; assumptions declare the linear '
          'placeholder', slow['ok'] and slow['completionHours'] == 4.0
          and any('placeholder' in a for a in slow['assumptions']))
    never = cure_progress(EMPTY, 2.85)
    check('MR=2.85 refuses (never hardens) pointing at data entry',
          never['ok'] is False and 'DigitizedDataset' in
          never['suggestion'])
    scaled = cure_progress(EMPTY, 1.83, cure_temperature_c=60.0)
    check('MR=1.83 at 60C scales by the Fig 8.20 ladder '
          '(90min vs interpolated 80C reference)',
          scaled['ok'] and scaled['completionHours'] > 4.0
          and any('Fig 8.20' in a or 'peak-time' in a
                  for a in scaled['assumptions']))
    offMap = cure_progress(EMPTY, 1.23, cure_temperature_c=60.0)
    check('temperature scaling off MR=1.83 refuses honestly',
          offMap['ok'] is False and 'Fig 8.20' in offMap['refusal'])


def main():
    test_catalog_and_curves()
    test_network_and_grading()
    test_states_and_progress()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
