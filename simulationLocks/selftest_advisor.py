"""
Selftest — xsim-5: overlap advisor (static write-set analysis).

Run from polari-framework/:
    python3 -m simulationLocks.selftest_advisor

Covers: the deliberately-conflicting definition (two stages executing
the SAME model row → evidence-bearing finding + the three
suggestions), provably-disjoint attempt prefixes (no false positive),
dynamic/unresolvable refs → conservative cannot-prove-disjoint,
subModel recursion (overlap detected across nesting) + cycle guard,
manifest = lock vocabulary (dynamic items excluded), and the
validate_composition surfacing.
"""

import json
from types import SimpleNamespace

from simulationLocks.advisor_stages import (
    analyze_write_sets, stage_manifest, stage_write_set,
)
from simulationLocks.overlap_advisor import analyze_branches

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _mgr(stages, extra_msims=()):
    msim = _Row(name='parent-msim', stages_json=json.dumps(stages))
    sim_def = _Row(name='wind-sim',
                   participating_sim_state_classes_json=json.dumps(
                       ['WindFieldGridState']),
                   time_step_seconds=0.01)
    model = _Row(name='thermal-model', physics_ref='fem-thermal')
    tables = {
        'MultiScaleSimulationDefinition':
            {i: m for i, m in enumerate((msim,) + tuple(extra_msims))},
        'SimulationDefinition': {0: sim_def},
        'FEMModelDefinition': {0: model},
        'DFTModelDefinition': {}, 'MDModelDefinition': {},
        'MesoModelDefinition': {},
        'FormulationSearchDefinition': {},
        'SimulationCouplingDefinition': {},
    }
    return SimpleNamespace(objectTables=tables), msim


if __name__ == '__main__':
    print('the deliberately-conflicting definition')
    manager, msim = _mgr([
        {'key': 'calibrate-a', 'kind': 'engineModel',
         'modelRef': 'thermal-model'},
        {'key': 'calibrate-b', 'kind': 'engineModel',
         'modelRef': 'thermal-model'},
    ])
    report = analyze_write_sets(manager, msim)
    check('two stages executing the SAME model row → finding',
          not report['ok'] and len(report['findings']) == 1)
    finding = report['findings'][0] if report['findings'] else {}
    check('evidence names both stage paths + the shared selector',
          finding.get('evidence', {}).get('branchA')
          == 'stage:calibrate-a'
          and finding['evidence']['selectorA']['value']
          == 'thermal-model')
    check('all three relief suggestions present',
          [s['action'].split()[0] for s in finding.get(
              'suggestions', [])] == ['serialize', 'partition', 'give'])

    print('provable disjointness (no false positives)')
    manager, msim = _mgr([
        {'key': 'stage-a', 'kind': 'runToCompletion',
         'simulationRef': 'wind-sim',
         'search': {'candidates': {'kind': 'grid'}}},
        {'key': 'stage-b', 'kind': 'runToCompletion',
         'simulationRef': 'wind-sim',
         'search': {'candidates': {'kind': 'grid'}}},
    ])
    report = analyze_write_sets(manager, msim)
    check('two search stages over the SAME sim: attempt prefixes '
          'provably disjoint → no findings',
          report['ok'] and report['findings'] == [])
    check('manifest covers attempt runs + state rows as RANGE rows '
          '(sweep = one lock row)',
          len(report['writeManifest']) == 4
          and all(m['selector']['kind'] == 'range'
                  for m in report['writeManifest']))

    print('dynamic refs stay conservative')
    manager, msim = _mgr([
        {'key': 'ghost-a', 'kind': 'engineModel', 'modelRef': 'nope-1'},
        {'key': 'ghost-b', 'kind': 'engineModel', 'modelRef': 'nope-2'},
    ])
    report = analyze_write_sets(manager, msim)
    check('unresolvable modelRefs → cannot-prove-disjoint finding',
          not report['ok']
          and report['findings'][0]['evidence']['dynamic'])
    manifest = stage_manifest(
        manager, msim,
        {'key': 'ghost-a', 'kind': 'engineModel', 'modelRef': 'nope-1'})
    check('dynamic items excluded from the LOCK manifest',
          manifest == [])

    print('subModel nesting + cycle guard')
    child = _Row(name='child-msim', stages_json=json.dumps([
        {'key': 'child-calibrate', 'kind': 'engineModel',
         'modelRef': 'thermal-model'}]))
    manager, msim = _mgr([
        {'key': 'own-calibrate', 'kind': 'engineModel',
         'modelRef': 'thermal-model'},
        {'key': 'nested', 'kind': 'subModel', 'msimRef': 'child-msim'},
    ], extra_msims=(child,))
    report = analyze_write_sets(manager, msim)
    check('parent stage vs NESTED child stage writing the same model '
          'row → finding across nesting',
          not report['ok'] and any(
              f['evidence']['branchB'] == 'stage:nested'
              for f in report['findings']))
    loop = _Row(name='loop-msim', stages_json=json.dumps([
        {'key': 'self', 'kind': 'subModel', 'msimRef': 'loop-msim'}]))
    manager2 = SimpleNamespace(objectTables={
        'MultiScaleSimulationDefinition': {0: loop},
        'FEMModelDefinition': {}, 'DFTModelDefinition': {},
        'MDModelDefinition': {}, 'MesoModelDefinition': {},
        'SimulationDefinition': {},
        'FormulationSearchDefinition': {}})
    items = stage_write_set(manager2, 'loop-msim',
                            {'key': 'self', 'kind': 'subModel',
                             'msimRef': 'loop-msim'})
    check('self-referential subModel → dynamic item, no recursion '
          'crash', len(items) == 1 and items[0]['dynamic'])

    print('branch engine directly (vocabulary reuse)')
    report = analyze_branches([
        {'branch': 'x', 'writeSet': [
            {'className': 'T',
             'selector': {'kind': 'range',
                          'value': '{"lo":"a-","hi":"a-~"}'}}]},
        {'branch': 'y', 'writeSet': [
            {'className': 'T',
             'selector': {'kind': 'name', 'value': 'a-thing'}}]},
    ])
    check('range vs contained name overlaps (lock semantics reused)',
          not report['ok'])

    print('validate_composition surfacing')
    manager, msim = _mgr([
        {'key': 'calibrate-a', 'kind': 'engineModel', 'intent':
            'calibrate', 'modelRef': 'thermal-model'},
        {'key': 'calibrate-b', 'kind': 'engineModel', 'intent':
            'calibrate', 'modelRef': 'thermal-model'},
    ])
    from simulations.simulation_intents import validate_composition
    findings = validate_composition(manager, msim)
    check('advisor warning surfaces through validate_composition',
          any('parallel-write-overlap' in f['message']
              or 'both write' in f['message']
              for f in findings if f['level'] == 'warning'))

    total, green = len(_results), sum(_results)
    print(f'\n{green}/{total} checks green')
    raise SystemExit(0 if green == total else 1)
