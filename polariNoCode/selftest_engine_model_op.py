"""
Standalone self-test for the EngineModelOperation no-code state — the
FEM/DFT engines callable from custom no-code logic (msci-18), extended
to the MD/meso model classes (msci-27).

Run from polari-framework/:
    python3 -m polariNoCode.selftest_engine_model_op

Proves the no-code engine can: compute a model input in-graph, feed it
through an inputBinding into a configured FEM model's stageDerived
binding, run the REAL homogenization solve, map a chosen result key to
a friendly context variable, and keep computing on it downstream —
custom physics logic woven around a real engine call. Also: honest
refusal paths (unknown model, missing input) surface in the trace log
without crashing the graph. The msci-27 case proves an
MDModelDefinition (bead-spring melt) is weavable through the SAME
operation with zero new nodes — find_model covers the new classes.
"""

import json
from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    SolutionExecutionEngine, StepConfig,
)
from simulations.simulation_runner import _extract_final_context
from materialsScience.engine_model_seed import (
    SEED_ENGINE_MODEL_TEMPLATES,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class FakeDB:
    def saveInstanceInDB(self, row):
        pass


class FakeManager:
    def __init__(self):
        self.objectTables = {}
        self.db = FakeDB()

    def add(self, class_name, row):
        self.objectTables.setdefault(class_name, {})[id(row)] = row
        return row


def _mgr():
    m = FakeManager()
    for seed in SEED_ENGINE_MODEL_TEMPLATES:
        m.add('EngineModelTemplate', SimpleNamespace(**seed))
    # A FEM homogenization model whose MATRIX conductivity arrives via a
    # stageDerived binding keyed 'nocode.matrixK' — the no-code graph
    # supplies it through an inputBinding.
    m.add('FEMModelDefinition', SimpleNamespace(
        name='nocode-homogenization',
        physics_ref='fem-effective-conductivity',
        domain_json='{"inclusion": {"volumeFraction": 0.2}}',
        materials_json=json.dumps({
            'matrix': {'thermalConductivity': {
                'kind': 'stageDerived', 'stage': 'nocode',
                'key': 'matrixK'}},
            'inclusion': {'thermalConductivity': 0.30}}),
        boundary_conditions_json='[]', source_terms_json='{}',
        mesh_json='{"refine": 3}', solver_json='{}',
        last_result_json='{}', last_executed_at='', enabled=True))
    # An MD bead-spring melt whose TEMPERATURE arrives in-graph
    # (stageDerived 'nocode.meltT') — tiny system so the REAL run
    # stays fast; bond length is set by FENE+WCA even at this size.
    m.add('MDModelDefinition', SimpleNamespace(
        name='nocode-bead-spring',
        physics_ref='md-bead-spring-melt',
        system_json=json.dumps({'chainLength': 5, 'nChains': 4}),
        thermodynamic_state_json=json.dumps({
            'density': 0.85,
            'temperature': {'kind': 'stageDerived', 'stage': 'nocode',
                            'key': 'meltT'}}),
        integration_json=json.dumps({'steps': 500,
                                     'equilibration': 200,
                                     'dt': 0.004, 'seed': 1234}),
        last_result_json='{}', last_executed_at='', enabled=True))
    return m


def _src_obj(path):
    return {'sourceType': 'from_source_object', 'sourceObjectPath': path}


def _state(name, cls, fields, out_to=None):
    slots = [{'index': 0, 'stateName': name, 'isInput': True,
              'label': 'In', 'connectors': []}]
    out = {'index': 1, 'stateName': name, 'isInput': False,
           'label': 'Out', 'connectors': []}
    if out_to:
        out['connectors'].append({'id': 1, 'sourceSlot': 1,
                                  'targetStateName': out_to,
                                  'sinkSlot': 0})
    slots.append(out)
    return {
        'stateName': name, 'id': f'{name}-state', 'index': 0,
        'stateClass': cls, 'boundObjectClass': cls,
        'boundObjectFieldValues': fields, 'slots': slots,
    }


def _solution(model_ref='nocode-homogenization'):
    """InitialState → EngineModelOperation → ReturnValue: the graph
    binds the instance field `base_k` into the model's stageDerived
    matrix conductivity, solves, and returns the mapped k_eff."""
    op_fields = {
        'modelRef': model_ref,
        'inputBindings': [
            # symbol must match the model's stageDerived '<stage>.<key>'
            {'symbol': 'nocode.matrixK', 'source': _src_obj('self.base_k')},
        ],
        'resultKeyMap': [
            {'resultKey': 'effectiveK', 'contextVar': 'k_eff'},
        ],
        'resultTarget': 'result_variable',
        'resultVariableName': 'solve_report',
    }
    return {
        'solutionName': 'engine-model-op-test',
        'stateInstances': [
            _state('Start', 'InitialState', {'inputParams': []},
                   out_to='Solve'),
            _state('Solve', 'EngineModelOperation', op_fields,
                   out_to='Done'),
            _state('Done', 'ReturnValue', {'returnValue': 'k_eff'}),
        ],
    }


def _md_solution():
    """InitialState → EngineModelOperation → ReturnValue over the MD
    bead-spring model: the graph supplies the melt temperature and
    reads back the chain bond length (msci-27 — no new node)."""
    op_fields = {
        'modelRef': 'nocode-bead-spring',
        'inputBindings': [
            {'symbol': 'nocode.meltT', 'source': _src_obj('self.melt_t')},
        ],
        'resultKeyMap': [
            {'resultKey': 'meanBondLength', 'contextVar': 'bond'},
        ],
        'resultTarget': 'result_variable',
        'resultVariableName': 'md_report',
    }
    return {
        'solutionName': 'md-model-op-test',
        'stateInstances': [
            _state('Start', 'InitialState', {'inputParams': []},
                   out_to='Simulate'),
            _state('Simulate', 'EngineModelOperation', op_fields,
                   out_to='Done'),
            _state('Done', 'ReturnValue', {'returnValue': 'bond'}),
        ],
    }


def _has_skfem():
    try:
        import skfem  # noqa: F401
        return True
    except ImportError:
        return False


def _run(mgr, solution, fields):
    engine = SolutionExecutionEngine(manager=mgr)
    return engine.execute(
        solution_data=solution, input_params={},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend', instance_fields=fields)


def _logs(trace):
    """Per-step log lines joined (log_output lives on each step
    snapshot, not the trace root)."""
    lines = []
    for step in getattr(trace, 'steps', []) or []:
        step_logs = (getattr(step, 'log_output', None)
                     or (step.get('log_output')
                         if isinstance(step, dict) else None) or [])
        lines.extend(step_logs)
    return ' | '.join(lines)


if __name__ == '__main__':
    print('\nEngineModelOperation — no-code engine calls\n')
    mgr = _mgr()
    trace = _run(mgr, _solution(), {'base_k': 0.25})
    final = _extract_final_context(trace)
    logs = _logs(trace)
    if _has_skfem():
        k_eff = final.get('k_eff')
        check('graph-supplied input drove the REAL solve; mapped key '
              'landed in context',
              isinstance(k_eff, float) and 0.25 < k_eff < 0.30,
              f'k_eff={k_eff}')
        check("outputs also written under 'model.<key>'",
              isinstance(final.get('model.effectiveK'), float)
              and final.get('model.withinBounds') is True)
        check('the trace log narrates the solve',
              'EngineModelOperation' in logs and 'nocode-homogenization'
              in logs)
        # Object coherence inside no-code: a different graph input →
        # a different solve.
        trace2 = _run(mgr, _solution(), {'base_k': 0.28})
        k2 = _extract_final_context(trace2).get('k_eff')
        check('changing the graph input changes the solve',
              isinstance(k2, float) and k2 > final['k_eff'],
              f'k_eff(0.28)={k2}')
    else:
        check('honest refusal without scikit-fem (trace, not crash)',
              trace.status == 'completed' and 'refused' in logs)

    # msci-27: an MD model through the SAME operation — find_model
    # resolves MDModelDefinition; the graph feeds T*, the REAL
    # bead-spring engine runs, and the KG-literature bond comes back.
    md_trace = _run(mgr, _md_solution(), {'melt_t': 1.0})
    md_final = _extract_final_context(md_trace)
    md_logs = _logs(md_trace)
    bond = md_final.get('bond')
    check('MD bead-spring model weavable via EngineModelOperation '
          '(bond in the KG band)',
          isinstance(bond, float) and 0.90 <= bond <= 1.05,
          f'bond={bond}')
    check("MD outputs also written under 'model.<key>'",
          isinstance(md_final.get('model.radiusOfGyration'), float)
          and 'nocode-bead-spring' in md_logs)

    # Refusal paths never crash the graph.
    trace3 = _run(mgr, _solution(model_ref='ghost-model'),
                  {'base_k': 0.25})
    logs3 = _logs(trace3)
    check('unknown model = honest trace refusal, graph completes',
          trace3.status == 'completed' and 'refused' in logs3,
          f'status={trace3.status}')
    # Missing input: the stageDerived key never arrives.
    sol = _solution()
    sol['stateInstances'][1]['boundObjectFieldValues'][
        'inputBindings'] = []
    trace4 = _run(mgr, sol, {'base_k': 0.25})
    logs4 = _logs(trace4)
    check('missing stageDerived input refuses naming the binding',
          trace4.status == 'completed'
          and ('stageDerived' in logs4 or 'refused' in logs4))

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
