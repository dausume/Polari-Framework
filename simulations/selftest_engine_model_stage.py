"""
Selftest — the engineModel stage kind + the stage-context builder.

Run from polari-framework/:
    python3 -m simulations.selftest_engine_model_stage

Covers: stage-search contract keys; readable candidate (resolved
inputs); derivedValues namespacing (model.* / input.*); gate default vs
persisted-result gate; honest refusals (missing modelRef, missing
model); build_stage_context namespacing + incomplete-upstream omission
+ a stageDerived binding resolving THROUGH the built context;
validate_composition passes engineModel stages (kind-aware default
intent + modelRef candidate space + typed existence check).
"""

import json
from types import SimpleNamespace

from materialsScience.engine_model_seed import (
    SEED_ENGINE_MODEL_TEMPLATES, SEED_FEM_MODELS,
)
from simulations.engine_model_stage import (
    build_stage_context, evaluate_engine_model_gate,
    run_engine_model_stage,
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


def _mgr():
    mgr = _StubManager()
    for seed in SEED_ENGINE_MODEL_TEMPLATES:
        mgr.add('EngineModelTemplate', SimpleNamespace(**seed))
    for seed in SEED_FEM_MODELS:
        mgr.add('FEMModelDefinition', SimpleNamespace(
            **{**seed, 'last_result_json': '{}', 'last_executed_at': ''}))
    mgr.add('MaterialScaleDefinition', SimpleNamespace(
        name='beeswax-carnauba-blend@L1',
        parameters_json='{"inputs": {"matrixK": 0.25, '
                        '"inclusionK": 0.30, "volumeFraction": 0.2}}'))
    return mgr


def _msim(stages, name='test-msim'):
    return SimpleNamespace(name=name, stages_json=json.dumps(stages),
                           member_simulation_refs_json='[]',
                           coupling_refs_json='[]',
                           panels_json='[]')


def _has_skfem():
    try:
        import skfem  # noqa: F401
        return True
    except ImportError:
        return False


STAGE = {'key': 'continuum-verify', 'kind': 'engineModel',
         'intent': 'calibrate', 'modelRef': 'wax-thermal-continuum',
         'gate': {'failReason': 'solve refused'},
         'derive': {'params': {'derived.effectiveK': 'model.effectiveK'}}}


def _executor():
    print('\nengineModel executor (stage-search contract)\n')
    mgr = _mgr()
    msim = _msim([STAGE])
    mgr.add('MultiScaleSimulationDefinition', msim)
    report = run_engine_model_stage(mgr, 'test-msim', STAGE, {})
    check('report carries the full contract',
          CONTRACT_KEYS <= set(report),
          f'missing={sorted(CONTRACT_KEYS - set(report))}')
    if _has_skfem():
        check('solve achieved with a single attempt',
              report['achieved'] and report['attempted'] == 1)
        cand = report['attempts'][0]['candidate']
        check('candidate = readable resolved inputs + model name',
              cand.get('matrixK') == 0.25 and cand.get('model')
              == 'wax-thermal-continuum', f'candidate={cand}')
        derived = report['winner']['derivedValues']
        check('derivedValues namespaced model.* + input.*',
              'model.effectiveK' in derived
              and derived['input.matrixK'] == 0.25)
        check('engineModel extras carry provenance + result',
              report['engineModel']['resolved']['matrixK']['kind']
              == 'objectRef'
              and report['engineModel']['result'].get('withinBounds'))
    else:
        check('honest refusal without scikit-fem',
              not report['achieved']
              and report['attempts'][0]['reason'])
    check('missing modelRef refuses honestly',
          'modelRef' in run_engine_model_stage(
              mgr, 'test-msim',
              {'key': 'x', 'kind': 'engineModel'}, {})['error'])
    bad = dict(STAGE, modelRef='nope')
    r2 = run_engine_model_stage(mgr, 'test-msim', bad, {})
    check('missing model = honest failed attempt (not a crash)',
          not r2['achieved'] and r2['attempts'][0]['reason'])
    return mgr


def _gate(mgr):
    print('\nengineModel gate (persisted result)\n')
    model = next(iter(mgr.objectTables['FEMModelDefinition'].values()))
    fresh = SimpleNamespace(**{**vars(model), 'last_result_json': '{}',
                               'last_executed_at': ''})
    verdict = evaluate_engine_model_gate(mgr, STAGE, fresh)
    check('never-executed model gates incomplete with the run hint',
          not verdict['complete'] and 'never executed'
          in verdict['reason'])
    executed = SimpleNamespace(**{
        **vars(model),
        'last_result_json': '{"effectiveK": 0.259, '
                            '"withinBounds": true}',
        'last_executed_at': '2026-07-07T12:00:00+00:00'})
    v2 = evaluate_engine_model_gate(mgr, STAGE, executed)
    check('persisted success completes the default gate with the '
          'flattened outputs',
          v2['complete']
          and v2['derivedValues']['model.effectiveK'] == 0.259)


def _context():
    print('\nbuild_stage_context\n')
    mgr = _mgr()
    executed = SimpleNamespace(
        name='ctx-model', physics_ref='fem-effective-conductivity',
        domain_json='{}', materials_json='{}',
        boundary_conditions_json='[]', source_terms_json='{}',
        mesh_json='{}', solver_json='{}',
        last_result_json='{"effectiveK": 0.259}',
        last_executed_at='2026-07-07T12:00:00+00:00', enabled=True)
    mgr.add('FEMModelDefinition', executed)
    stage1 = {'key': 's1', 'kind': 'engineModel', 'modelRef': 'ctx-model'}
    stage2 = {'key': 's2', 'kind': 'engineModel',
              'modelRef': 'wax-thermal-continuum'}
    msim = _msim([stage1, stage2])
    ctx = build_stage_context(mgr, msim, 's2')
    check('prior complete stage contributes namespaced keys + flag',
          ctx.get('s1.__complete') is True
          and ctx.get('s1.model.effectiveK') == 0.259,
          f'ctx={sorted(ctx)}')
    # Incomplete upstream: a model that never ran.
    never = SimpleNamespace(**{**vars(executed), 'name': 'never-ran',
                               'last_result_json': '{}',
                               'last_executed_at': ''})
    mgr.add('FEMModelDefinition', never)
    msim2 = _msim([{'key': 'sA', 'kind': 'engineModel',
                    'modelRef': 'never-ran'}, stage2])
    ctx2 = build_stage_context(mgr, msim2, 's2')
    check('incomplete upstream contributes ONLY its flag',
          ctx2.get('sA.__complete') is False
          and not any(k.startswith('sA.model.') for k in ctx2))

    # A stageDerived binding resolving THROUGH the built context.
    bound = SimpleNamespace(
        name='bound-model', physics_ref='fem-effective-conductivity',
        domain_json='{"inclusion": {"volumeFraction": 0.2}}',
        materials_json=json.dumps({
            'matrix': {'thermalConductivity': {
                'kind': 'stageDerived', 'stage': 's1',
                'key': 'model.effectiveK'}},
            'inclusion': {'thermalConductivity': 0.30}}),
        boundary_conditions_json='[]', source_terms_json='{}',
        mesh_json='{"refine": 3}', solver_json='{}',
        last_result_json='{}', last_executed_at='', enabled=True)
    mgr.add('FEMModelDefinition', bound)
    stage_b = {'key': 's2', 'kind': 'engineModel',
               'modelRef': 'bound-model', 'intent': 'calibrate'}
    msim3 = _msim([stage1, stage_b])
    mgr.add('MultiScaleSimulationDefinition', msim3)
    report = run_engine_model_stage(mgr, msim3.name, stage_b, {},
                                    msim=msim3)
    if _has_skfem():
        check('stageDerived binding resolves through the built context '
              '(upstream k_eff becomes the matrix k)',
              report['achieved']
              and report['engineModel']['resolved']['matrixK']['kind']
              == 'stageDerived'
              and report['attempts'][0]['candidate']['matrixK'] == 0.259,
              f"resolved={report['engineModel'].get('resolved', {}).get('matrixK')}")
    else:
        check('stageDerived resolution refused honestly without '
              'scikit-fem', not report['achieved'])


def _intents():
    print('\nvalidate_composition — engineModel stages\n')
    mgr = _mgr()
    msim = _msim([STAGE])
    findings = validate_composition(mgr, msim)
    errors = [f for f in findings if f['level'] == 'error']
    check('engineModel stage with derive validates clean '
          '(calibrate is product-bearing; modelRef = candidate space)',
          not errors, f'errors={[e["message"] for e in errors]}')
    no_intent = {k: v for k, v in STAGE.items() if k != 'intent'}
    findings2 = validate_composition(mgr, _msim([no_intent]))
    check('kind-aware default intent (calibrate) keeps it clean',
          not [f for f in findings2 if f['level'] == 'error'])
    bad = dict(STAGE, modelRef='ghost')
    findings3 = validate_composition(mgr, _msim([bad]))
    check('unknown modelRef is an error',
          any('ghost' in f['message'] for f in findings3
              if f['level'] == 'error'))


if __name__ == '__main__':
    mgr = _executor()
    _gate(mgr)
    _context()
    _intents()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
