"""
Selftest — the subModel stage kind (recursive multi-scale composition).

Run from polari-framework/:
    python3 -m simulations.selftest_sub_model_stage

Covers: a child msim of engineModel stages executes with namespaced
sub.<stage>.<key> derived values; the child's own stage context chains
(stage 2 of the child reads stage 1's output); an incomplete child
stepping stage blocks HONESTLY with the drive-it-yourself suggestion;
direct + transitive cycles refuse naming the path; the depth cap;
read-only sub-model gate; validate_composition typed msimRef check +
static cycle detection.
"""

import json
from types import SimpleNamespace

from materialsScience.engine_model_seed import (
    SEED_ENGINE_MODEL_TEMPLATES,
)
from simulations.sub_model_stage import (
    evaluate_sub_model_gate, run_sub_model_stage,
)
from simulations.simulation_intents import validate_composition

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []

CONTRACT_KEYS = {'achieved', 'winner', 'winners', 'searchComplete',
                 'exhausted', 'totalCandidates', 'attempted',
                 'advancedThisCall', 'attempts', 'backend', 'warnings',
                 'error'}


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _StubDB:
    def saveInstanceInDB(self, row):
        pass


class _StubManager:
    def __init__(self):
        self.objectTables = {}
        self.db = _StubDB()

    def add(self, class_name, row):
        self.objectTables.setdefault(class_name, {})[id(row)] = row
        return row


def _has_skfem():
    try:
        import skfem  # noqa: F401
        return True
    except ImportError:
        return False


def _fem_model(name, matrix_binding):
    return SimpleNamespace(
        name=name, physics_ref='fem-effective-conductivity',
        domain_json='{"inclusion": {"volumeFraction": 0.2}}',
        materials_json=json.dumps({
            'matrix': {'thermalConductivity': matrix_binding},
            'inclusion': {'thermalConductivity': 0.30}}),
        boundary_conditions_json='[]', source_terms_json='{}',
        mesh_json='{"refine": 3}', solver_json='{}',
        last_result_json='{}', last_executed_at='', enabled=True)


def _msim(name, stages):
    return SimpleNamespace(name=name, stages_json=json.dumps(stages),
                           member_simulation_refs_json='[]',
                           coupling_refs_json='[]', panels_json='[]')


def _mgr():
    mgr = _StubManager()
    for seed in SEED_ENGINE_MODEL_TEMPLATES:
        mgr.add('EngineModelTemplate', SimpleNamespace(**seed))
    # Child msim: two chained engineModel stages (stage 2's matrix k is
    # stage 1's computed k_eff — the recursion carries a REAL chain).
    mgr.add('FEMModelDefinition', _fem_model('child-m1', 0.25))
    mgr.add('FEMModelDefinition', _fem_model('child-m2', {
        'kind': 'stageDerived', 'stage': 'c1',
        'key': 'model.effectiveK'}))
    child = _msim('child-msim', [
        {'key': 'c1', 'kind': 'engineModel', 'intent': 'calibrate',
         'modelRef': 'child-m1',
         'derive': {'params': {'derived.k1': 'model.effectiveK'}}},
        {'key': 'c2', 'kind': 'engineModel', 'intent': 'validate',
         'modelRef': 'child-m2'},
    ])
    mgr.add('MultiScaleSimulationDefinition', child)
    return mgr


PARENT_STAGE = {'key': 'nested', 'kind': 'subModel', 'intent': 'search',
                'msimRef': 'child-msim',
                'gate': {'failReason': 'the nested model is incomplete'},
                'derive': {'params': {
                    'derived.k': 'sub.c1.model.effectiveK'}}}


def _execution():
    print('\nsubModel execution (recursive, chained child context)\n')
    mgr = _mgr()
    parent = _msim('parent-msim', [PARENT_STAGE])
    mgr.add('MultiScaleSimulationDefinition', parent)
    report = run_sub_model_stage(mgr, 'parent-msim', PARENT_STAGE, {})
    check('report carries the full contract',
          CONTRACT_KEYS <= set(report),
          f'missing={sorted(CONTRACT_KEYS - set(report))}')
    if _has_skfem():
        check('both child stages executed and achieved',
              report['achieved'] and report['attempted'] == 2,
              f"blockedAt={report['subModel']['blockedAt']}")
        derived = report['winner']['derivedValues']
        check('derived values namespaced sub.<childStage>.<key>',
              'sub.c1.model.effectiveK' in derived,
              f'keys={sorted(derived)[:6]}')
        check("child stage 2 read child stage 1's output through the "
              'child context (REAL nested chain)',
              abs(derived['sub.c2.input.matrixK']
                  - derived['sub.c1.model.effectiveK']) < 1e-12)
    else:
        check('honest non-achievement without scikit-fem',
              not report['achieved'])

    # An incomplete stepping stage blocks honestly.
    stepping_child = _msim('stepping-child', [
        {'key': 'sim', 'kind': 'runToCompletion',
         'simulationRef': 'some-sim', 'intent': 'search',
         'gate': {'solutionRef': 'some-gate'}},
    ])
    mgr.add('MultiScaleSimulationDefinition', stepping_child)
    stage2 = dict(PARENT_STAGE, msimRef='stepping-child')
    r2 = run_sub_model_stage(mgr, 'parent-msim', stage2, {})
    check('incomplete child stepping stage blocks with the '
          'drive-it-yourself suggestion',
          not r2['achieved']
          and r2['subModel']['blockedAt'] == 'sim'
          and 'not auto-run' in r2['attempts'][0]['reason'])


def _cycles():
    print('\ncycles + depth\n')
    mgr = _mgr()
    # a -> b -> a
    a = _msim('a', [{'key': 's', 'kind': 'subModel', 'msimRef': 'b'}])
    b = _msim('b', [{'key': 's', 'kind': 'subModel', 'msimRef': 'a'}])
    mgr.add('MultiScaleSimulationDefinition', a)
    mgr.add('MultiScaleSimulationDefinition', b)
    r = run_sub_model_stage(mgr, 'a', json.loads(a.stages_json)[0], {})
    # The refusal surfaces where the cycle is DETECTED — one level down,
    # as the blocked child stage's reason (the outer walk stays honest:
    # blocked, not errored).
    cycle_text = (r.get('error') or '') + ' '.join(
        att.get('reason') or '' for att in r.get('attempts', []))
    check('transitive cycle refuses naming the path',
          not r['achieved'] and 'cycle' in cycle_text,
          f'text={cycle_text[:120]}')
    # Self-cycle.
    selfy = _msim('selfy', [{'key': 's', 'kind': 'subModel',
                             'msimRef': 'selfy'}])
    mgr.add('MultiScaleSimulationDefinition', selfy)
    r2 = run_sub_model_stage(mgr, 'selfy',
                             json.loads(selfy.stages_json)[0], {})
    check('self-cycle refuses', r2['error'] and 'cycle' in r2['error'])
    # Depth cap: a linear chain deeper than the cap.
    prev = 'child-msim'
    for i in range(10):
        name = f'deep-{i}'
        mgr.add('MultiScaleSimulationDefinition', _msim(
            name, [{'key': 's', 'kind': 'subModel', 'msimRef': prev}]))
        prev = name
    r3 = run_sub_model_stage(
        mgr, 'root', {'key': 's', 'kind': 'subModel', 'msimRef': prev},
        {})
    def _walk(rep):
        # find a depth-cap error anywhere down the attempt chain
        if rep.get('error') and 'depth cap' in rep['error']:
            return True
        return any('depth cap' in (a.get('reason') or '')
                   for a in rep.get('attempts', []))
    check('depth cap refuses honestly somewhere down the chain',
          _walk(r3) or not r3['achieved'])


def _gate_and_intents():
    print('\nread-only gate + validate_composition\n')
    mgr = _mgr()
    verdict = evaluate_sub_model_gate(mgr, PARENT_STAGE)
    check('read-only gate is incomplete before anything ran '
          '(no execution side effects)',
          not verdict['complete'] and 'not complete'
          in verdict['reason'])
    parent = _msim('parent-msim', [PARENT_STAGE])
    mgr.add('MultiScaleSimulationDefinition', parent)
    findings = validate_composition(mgr, parent)
    errors = [f for f in findings if f['level'] == 'error']
    check('subModel stage validates clean (msimRef = candidate space)',
          not errors, f'errors={[e["message"] for e in errors]}')
    ghost = _msim('ghost-parent', [dict(PARENT_STAGE, msimRef='ghost')])
    findings2 = validate_composition(mgr, ghost)
    check('unknown msimRef is an error',
          any('ghost' in f['message'] for f in findings2
              if f['level'] == 'error'))
    # Static cycle detection.
    a = _msim('cyc-a', [{'key': 's', 'kind': 'subModel',
                         'msimRef': 'cyc-b', 'intent': 'search'}])
    b = _msim('cyc-b', [{'key': 's', 'kind': 'subModel',
                         'msimRef': 'cyc-a', 'intent': 'search'}])
    mgr.add('MultiScaleSimulationDefinition', a)
    mgr.add('MultiScaleSimulationDefinition', b)
    findings3 = validate_composition(mgr, a)
    check('static cycle detection errs naming the cycle',
          any('cycle' in f['message'].lower() for f in findings3
              if f['level'] == 'error'),
          f"msgs={[f['message'] for f in findings3 if f['level'] == 'error']}")
    # Regression: the real pendulum + wax msims still validate the same.
    from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
    from materialsScience.wax_derivation_seed import (
        SEED_WAX_DERIVATION_MSIMS,
    )
    from materialsScience.formulation_search_seed import (
        SEED_FORMULATION_SEARCHES,
    )
    mgr2 = _StubManager()
    mgr2.add('FormulationSearchDefinition',
             SimpleNamespace(**SEED_FORMULATION_SEARCHES[0]))
    wax = SimpleNamespace(**SEED_WAX_DERIVATION_MSIMS[0])
    mgr2.add('MultiScaleSimulationDefinition', wax)
    errors_wax = [f for f in validate_composition(mgr2, wax)
                  if f['level'] == 'error']
    check('regression: wax-derivation still validates clean',
          not errors_wax,
          f'errors={[e["message"] for e in errors_wax]}')


if __name__ == '__main__':
    _execution()
    _cycles()
    _gate_and_intents()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
