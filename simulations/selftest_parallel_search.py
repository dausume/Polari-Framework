"""
Self-test for parallel solution-search attempts (Dask track 1):
the pure attempt task, execution backends, and the orchestrator's
parallel path — all against the REAL material-condensation seeds.

Run from polari-framework/:
    python3 -m simulations.selftest_parallel_search
"""

import inspect
import json
from types import SimpleNamespace

from matrices.seed_data import SEED_MATRIX_EQUATIONS
from simulations.attempt_task import build_attempt_spec, execute_attempt_pure
from simulations.execution_backend import (
    BACKENDS, ExecutionBackendError, parallel_map,
)
import simulations.execution_backend as _backend_mod
import simulations.multi_scale_search as _search_mod
import simulations.simulation_runner as _runner_mod
from simulations.multi_scale_search import run_stage_search
from simulations.material_space_seed import (
    MATERIAL_SIM_DEF, GATE_SOLUTION,
    _MC_STEP_DEF, _MC_STEP_META, _GATE_SOLUTION_DEF,
)
from simulations.material_condensation_state import MaterialCondensationState
from simulations.seed_data import SEED_SIMULATION_DEFINITIONS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


_MC = 'MaterialCondensationState'
_FAIL_REASON = ('No solid phase at the tried temperature/pressure — '
                'the ball would be liquid.')


def _stage(candidates):
    return {
        'key': 'material-precondition', 'kind': 'runToCompletion',
        'intent': 'search', 'simulationRef': MATERIAL_SIM_DEF,
        'gate': {'solutionRef': GATE_SOLUTION, 'failReason': _FAIL_REASON},
        'derive': {'params': {
            'newtonian-pendulum-3d.mass': 'ball_mass',
            'newtonian-pendulum-3d.bob_radius': 'ball_radius'}},
        'search': {'candidates': {'kind': 'list', 'values': candidates},
                   'stepsPerAttempt': 20, 'batchSize': 10},
    }


def _fake_manager():
    """A fake manager carrying the REAL material seeds as plain rows."""
    sim_def_row = next(d for d in SEED_SIMULATION_DEFINITIONS
                       if d['name'] == MATERIAL_SIM_DEF)
    fields = [p for p in inspect.signature(
        MaterialCondensationState.__init__).parameters
        if p not in ('self', 'manager')]
    typing = SimpleNamespace(
        classDefinition=MaterialCondensationState,
        polyTypedVarsDict={f: None for f in fields},
    )
    m = SimpleNamespace()
    m.objectTypingDict = {_MC: typing}
    m.objectTables = {
        'SimulationDefinition': {'d': SimpleNamespace(**sim_def_row)},
        'SimulationExecutionSolution': {'s': SimpleNamespace(**_MC_STEP_META)},
        'SolutionDefinition': {
            'step': SimpleNamespace(**_MC_STEP_DEF),
            'gate': SimpleNamespace(**_GATE_SOLUTION_DEF),
        },
        'MatrixEquationDefinition': {
            f'eq{i}': SimpleNamespace(**row)
            for i, row in enumerate(SEED_MATRIX_EQUATIONS)
        },
        'MatrixDefinition': {},
        'EquationDefinition': {},
        'SimulationRun': {},
        'SimulationCouplingDefinition': {},
        'StepCostProfile': {},
        _MC: {},
    }
    return m


def _sim_def(manager):
    return next(iter(manager.objectTables['SimulationDefinition'].values()))


# --- test seams: attempt-run creation + row writing on the fake manager ---

def _fake_create_attempt_run(manager, name, sim_ref, candidate, stage, msim):
    run = SimpleNamespace(
        name=name, simulation_ref=sim_ref, status='pending',
        last_recorded_step=0, time_step_seconds=0.0,
        parameter_overrides_json=json.dumps(candidate),
        coupled_run_refs_json='{}',
        initial_conditions_overrides_json='{}',
        field_save_overrides_json='{}',
        recorded_steps=0,
    )
    manager.objectTables['SimulationRun'][name] = run
    return run


def _fake_create_row(manager, cls_name, fields):
    row = SimpleNamespace(**fields)
    manager.objectTables.setdefault(cls_name, {})[fields.get('name')] = row


def _pure():
    print('Parallel search — the pure attempt task (real material seeds)\n')
    m = _fake_manager()
    stage = _stage([{'target_temp': 260.0, 'pressure_pa': 50000.0}])

    spec_wax = build_attempt_spec(
        m, stage, _sim_def(m), {'target_temp': 260.0, 'pressure_pa': 50000.0})
    check('spec is plain data (json-serializable → picklable)',
          bool(json.dumps(spec_wax)))

    res = execute_attempt_pure(spec_wax)
    check('pure wax attempt completes its gate',
          res['error'] is None and res['gateComplete'] is True,
          f"err={res['error']}")
    ball = (res['derivedValues'] or {}).get('ball_mass')
    check('pure wax attempt derives the exact proven ball',
          ball is not None and abs(float(ball) - 1.9804) < 1e-3,
          f'ball_mass={ball}')
    temp = res['rowsByClass'].get(_MC, {}).get('temperature')
    check('pure physics matches the analytic settle temperature',
          temp is not None and abs(float(temp) - 260.607) < 5e-3,
          f'T={temp}')

    spec_cold = build_attempt_spec(
        m, stage, _sim_def(m),
        {'target_temp': 260.0, 'pressure_pa': 50000.0,
         'melt_temp_ref': 200.0})
    res_cold = execute_attempt_pure(spec_cold)
    check('unmeltable substance fails the gate with the plain reason',
          res_cold['gateComplete'] is False
          and res_cold['gateReason'] == _FAIL_REASON,
          f"reason={res_cold['gateReason']!r}")


def _backends():
    print('\nParallel search — execution backends\n')
    m = _fake_manager()
    stage = _stage([{'target_temp': 260.0 + i, 'pressure_pa': 50000.0}
                    for i in range(4)])
    specs = [build_attempt_spec(m, stage, _sim_def(m),
                                {'target_temp': 260.0 + i,
                                 'pressure_pa': 50000.0})
             for i in range(4)]
    serial = parallel_map(execute_attempt_pure, specs, backend='serial')
    procs = parallel_map(execute_attempt_pure, specs, backend='processes',
                         max_workers=2)
    check('processes backend returns identical results in order',
          serial == procs)
    try:
        parallel_map(execute_attempt_pure, specs, backend='nonsense')
        bad = False
    except ExecutionBackendError:
        bad = True
    check('unknown backend is rejected loudly', bad)

    real_dask = _backend_mod._dask_client

    def _no_dask(n):
        raise ExecutionBackendError(
            "Dask is not installed on this backend. Enable it with: "
            "pip install 'dask[distributed]'")
    _backend_mod._dask_client = _no_dask
    try:
        parallel_map(execute_attempt_pure, specs[:1], backend='dask')
        dask_err = None
    except ExecutionBackendError as exc:
        dask_err = str(exc)
    finally:
        _backend_mod._dask_client = real_dask
    check('missing dask yields a structured how-to-enable error',
          dask_err is not None and 'pip install' in dask_err)


def _orchestrator():
    print('\nParallel search — orchestrator parallel path\n')
    stage = _stage([
        {'target_temp': 400.0, 'pressure_pa': 50000.0},   # too hot: liquid
        {'target_temp': 260.0, 'pressure_pa': 50000.0},   # solid — the winner
        {'target_temp': 410.0, 'pressure_pa': 50000.0},   # never attempted
    ])

    real_create = _search_mod._create_attempt_run
    real_row = _runner_mod._create_row
    _search_mod._create_attempt_run = _fake_create_attempt_run
    _runner_mod._create_row = _fake_create_row
    try:
        m_par = _fake_manager()
        report = run_stage_search(
            m_par, 'demo', stage, batch_size=2, attempt_tag='par',
            execution_backend='processes', max_workers=2)
        check('processes orchestrator achieves with the right candidate',
              report['achieved'] and report['backend'] == 'processes'
              and report['winner']['candidate']['target_temp'] == 260.0,
              f"err={report['error']} winner={report.get('winner')}")
        ball = (report['winner']['derivedValues'] or {}).get('ball_mass')
        check('winner confirmed IN-PROCESS over materialized rows '
              '(derived ball matches)',
              ball is not None and abs(float(ball) - 1.9804) < 1e-3,
              f'ball_mass={ball}')
        run_name = report['winner']['run']
        run = m_par.objectTables['SimulationRun'][run_name]
        rows = [r for r in m_par.objectTables[_MC].values()
                if getattr(r, 'simulation_run_ref', '') == run_name]
        check('attempt runs materialize: final row per class + counters',
              run.last_recorded_step == 20 and len(rows) == 1
              and getattr(rows[0], 'step', 0) == 20
              and run_name == 'demo-material-precondition-par-attempt-1',
              f'last={run.last_recorded_step} rows={len(rows)}')
        check('hot candidate failed with the plain reason; third untouched',
              report['attempts'][0]['complete'] is False
              and report['attempts'][0]['reason'] == _FAIL_REASON
              and report['attempts'][2]['reason'] == 'not attempted yet')

        # Serial baseline on a fresh manager: same winner semantics.
        m_ser = _fake_manager()
        report_ser = run_stage_search(
            m_ser, 'demo', stage, batch_size=3, attempt_tag='ser',
            execution_backend='serial')
        check('serial (real runner loop) agrees on the winner candidate',
              report_ser['achieved']
              and report_ser['winner']['candidate']['target_temp'] == 260.0,
              f"err={report_ser['error']}")

        # Coupled sim → parallel falls back to serial with a warning.
        m_cpl = _fake_manager()
        m_cpl.objectTables['SimulationCouplingDefinition']['c'] = \
            SimpleNamespace(enabled=True,
                            source_simulation_ref=MATERIAL_SIM_DEF,
                            target_simulation_ref='other')
        report_cpl = run_stage_search(
            m_cpl, 'demo', stage, batch_size=1, attempt_tag='cpl',
            execution_backend='processes')
        check('coupled simulation falls back to serial with a warning',
              report_cpl['backend'] == 'serial'
              and any('coupling' in w for w in report_cpl['warnings']))

        # Knobs-and-suggestions: a slow serial search points at the
        # executionBackend knob with measured evidence.
        m_hint = _fake_manager()
        m_hint.objectTables['StepCostProfile']['p'] = SimpleNamespace(
            name=f'{MATERIAL_SIM_DEF}-cost-profile',
            avg_step_seconds=0.1)
        hint = _search_mod._parallel_hint(
            m_hint, MATERIAL_SIM_DEF, target_steps=20, remaining=8,
            winner=None)
        check('parallelHint suggests the executionBackend knob with '
              'measured evidence',
              hint is not None and 'executionBackend' in hint
              and '16s' in hint, f'hint={hint!r}')
    finally:
        _search_mod._create_attempt_run = real_create
        _runner_mod._create_row = real_row


if __name__ == '__main__':
    _pure()
    _backends()
    _orchestrator()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
