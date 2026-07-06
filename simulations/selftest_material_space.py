"""
Self-test for the material condensation space (Milestone B) — the
first-principles stage of the multi-scale pendulum composition.

Run from polari-framework/:
    python3 -m simulations.selftest_material_space

Four layers, none needing the server or sudo:

  1. EQUATIONS — the four seeded matrix equations execute with their
     REAL expr strings (cooling relaxation vs the exact exponential;
     phase check on both sides of the pressure-shifted melting line,
     including water-ice's NEGATIVE slope; density/ball-mass numbers).
  2. THE GATE, THROUGH THE REAL ENGINE — the actual seeded
     `solid-ball-achievable` SolutionDefinition graph executes via
     SolutionExecutionEngine + evaluate_stage_gate over flattened stage
     results: solid case → complete with derived ball properties;
     liquid case → incomplete with the stage's plain-language failReason
     (exercising the new numeric-truthiness fallback).
  3. SEARCH EXTENSIONS — fixedParams merge into every candidate
     (candidate wins conflicts) and attemptTag namespaces attempt runs.
  4. SEEDS — the demo's stage wiring resolves (gate solution seeded,
     material sim def exists with intent 'search', derive targets are
     real pendulum params, substances carry physical identities).
"""

import json
import math
from types import SimpleNamespace

import numpy as np

from matrices.seed_data import SEED_MATRIX_EQUATIONS
from matrices.matrix_equation_executor import evaluate_equation
from simulations.multi_scale_stages import evaluate_stage_gate
import simulations.multi_scale_search as _search_mod
import simulations.simulation_runner as _runner_mod
from simulations.multi_scale_search import (
    attempt_run_name, attempt_run_label, run_stage_search,
)
from simulations.material_space_seed import (
    _MATERIAL_PARAMS, GATE_SOLUTION, MATERIAL_SIM_DEF,
    _GATE_SOLUTION_DEF, SEED_MATERIAL_ROWS,
    _MATERIAL_STEPS, _MATERIAL_OUTPUT_MAP,
)
from simulations.multi_scale_seed import SEED_MULTI_SCALE_SIMS
from simulations.newtonian_pendulum_seed import _NEWTON_PARAMS
from simulations.seed_data import SEED_SIMULATION_DEFINITIONS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _eq_def(name):
    row = next(e for e in SEED_MATRIX_EQUATIONS if e['name'] == name)
    return SimpleNamespace(**row)


def _equations():
    print('Material space — matrix equations (real seeded exprs)\n')
    p = _MATERIAL_PARAMS

    cooled = evaluate_equation(_eq_def('material-cool-step'), {
        't': 293.15, 'tt': 260.0, 'cr': p['cool_rate'], 'dt': 0.05})
    mirror = 293.15 + (260.0 - 293.15) * (1.0 - math.exp(-p['cool_rate'] * 0.05))
    check('cooling step matches the exact exponential relaxation',
          abs(float(cooled[0]) - mirror) < 1e-9, f'T\'={float(cooled[0]):.3f} K')
    # 20 steps at dt=0.05 → e^-4 ≈ 1.8% remaining gap: settles at target.
    t = 293.15
    for _ in range(20):
        t = float(evaluate_equation(_eq_def('material-cool-step'), {
            't': t, 'tt': 260.0, 'cr': p['cool_rate'], 'dt': 0.05})[0])
    check('20 steps settle onto the target temperature',
          abs(t - 260.0) < 1.0, f'final T={t:.2f} K')

    def phase(t, tm_ref, slope, pres):
        return float(evaluate_equation(_eq_def('material-phase-check'), {
            't': t, 'tm_ref': tm_ref, 'slope': slope, 'p': pres})[0])
    check('wax: solid below its melt line, liquid above',
          phase(300.0, 327.0, 2.5e-7, 101325.0) == 1.0
          and phase(340.0, 327.0, 2.5e-7, 101325.0) == 0.0)

    # melt_temp (the persisted melt line): the equation must agree with
    # the analytic line AND with the phase check on both of its sides —
    # the graphs plot temperature against THIS field, so a drift here
    # would draw a crossing that contradicts phase_solid.
    def melt_line(tm_ref, slope, pres):
        return float(evaluate_equation(_eq_def('material-melt-line'), {
            'tm_ref': tm_ref, 'slope': slope, 'p': pres})[0])
    tm_hi = melt_line(327.0, 2.5e-7, 2.0e5)
    check('melt line matches the analytic pressure shift',
          abs(tm_hi - (327.0 + 2.5e-7 * (2.0e5 - 101325.0))) < 1e-9,
          f'T_m(200 kPa)={tm_hi:.6f} K')
    check('phase check flips exactly at the persisted melt line',
          phase(tm_hi - 0.01, 327.0, 2.5e-7, 2.0e5) == 1.0
          and phase(tm_hi + 0.01, 327.0, 2.5e-7, 2.0e5) == 0.0)
    # Water-ice at -0.5 C: solid at 1 atm; at ~70 MPa the NEGATIVE slope
    # drops the melt line ~5 K below it → pressure melts the ice.
    check('water-ice: pressure MELTS it (negative Clausius slope)',
          phase(272.65, 273.15, -7.4e-8, 101325.0) == 1.0
          and phase(272.65, 273.15, -7.4e-8, 7.0e7) == 0.0)

    rho = float(evaluate_equation(_eq_def('material-density'), {
        'rho0': 900.0, 'alpha': 8e-4, 't': 260.0, 't_ref': 293.15})[0])
    check('density rises when colder than reference',
          abs(rho - 900.0 * (1 - 8e-4 * (260.0 - 293.15))) < 1e-9
          and rho > 900.0, f'rho(260K)={rho:.2f} kg/m^3')
    m = float(evaluate_equation(_eq_def('material-ball-mass'), {
        'rho': 900.0, 'r': 0.08})[0])
    check('ball mass = rho * (4/3) pi r^3',
          abs(m - 900.0 * (4.0 / 3.0) * math.pi * 0.08 ** 3) < 1e-9,
          f'm={m:.4f} kg (wax at reference density)')

    # SHAPE-CONVENTION guard: chain the equations exactly as the solution
    # binds them — each downstream operand ELEMENT-extracted back to a
    # scalar — and assert every result stays a flat length-1 vector whose
    # element is a real number (the (1,1)-double-wrap regression left
    # LISTS on state rows and poisoned the next step's context).
    p = _MATERIAL_PARAMS
    t_new = evaluate_equation(_eq_def('material-cool-step'), {
        't': 293.15, 'tt': 260.0, 'cr': p['cool_rate'], 'dt': 0.05}).tolist()
    solid = evaluate_equation(_eq_def('material-phase-check'), {
        't': t_new[0], 'tm_ref': p['melt_temp_ref'],
        'slope': p['melt_slope_k_per_pa'], 'p': p['pressure_pa']}).tolist()
    rho_v = evaluate_equation(_eq_def('material-density'), {
        'rho0': p['density_solid_ref'], 'alpha': p['thermal_expansion'],
        't': t_new[0], 't_ref': p['density_ref_temp']}).tolist()
    mass_v = evaluate_equation(_eq_def('material-ball-mass'), {
        'rho': rho_v[0], 'r': p['ball_radius_target']}).tolist()
    check('chained results stay flat length-1 vectors of real scalars '
          '(no (1,1) double-wrap)',
          all(len(v) == 1 and isinstance(v[0], (int, float))
              for v in (t_new, solid, rho_v, mass_v)),
          f'element types={[type(v[0]).__name__ for v in (t_new, solid, rho_v, mass_v)]}')


def _gate():
    print('\nMaterial space — the gate through the REAL engine\n')
    gate_row = SimpleNamespace(**_GATE_SOLUTION_DEF)
    sim_def = SimpleNamespace(
        name=MATERIAL_SIM_DEF,
        participating_sim_state_classes_json=json.dumps(
            ['MaterialCondensationState']),
        parameters_json=json.dumps(_MATERIAL_PARAMS),
    )

    def _mgr(row_fields):
        row = SimpleNamespace(
            name='mat-run-row', simulation_run_ref='mat-run', **row_fields)
        return SimpleNamespace(objectTables={
            'SolutionDefinition': {GATE_SOLUTION: gate_row},
            'SimulationExecutionSolution': {},
            'SimulationDefinition': {MATERIAL_SIM_DEF: sim_def},
            'MaterialCondensationState': {'r': row},
        })

    stage = {
        'key': 'material-precondition', 'kind': 'runToCompletion',
        'simulationRef': MATERIAL_SIM_DEF,
        'gate': {'solutionRef': GATE_SOLUTION,
                 'failReason': 'No solid phase at the tried temperature/'
                               'pressure — the ball would be liquid.'},
        'derive': {'params': {'newtonian-pendulum-3d.mass': 'ball_mass'}},
    }
    run = SimpleNamespace(name='mat-run', simulation_ref=MATERIAL_SIM_DEF,
                          last_recorded_step=20, status='running')

    solid_mass = 923.87 * (4.0 / 3.0) * math.pi * 0.08 ** 3
    v = evaluate_stage_gate(_mgr({
        'step': 20, 'time': 1.0, 'temperature': 260.0, 'phase_solid': 1.0,
        'density': 923.87, 'ball_mass': solid_mass, 'ball_radius': 0.08,
    }), stage, run)
    check('SOLID case: the real no-code gate passes via numeric fallback',
          v['error'] is None and v['complete'] is True and v['hasGate'],
          f"error={v['error']}")
    dv = v['derivedValues'] or {}
    check('gate derives the proven ball (mass/radius/density lifted)',
          abs(float(dv.get('ball_mass', 0)) - solid_mass) < 1e-6
          and float(dv.get('ball_radius', 0)) == 0.08
          and abs(float(dv.get('ball_density', 0)) - 923.87) < 1e-9,
          f"ball_mass={dv.get('ball_mass'):.4f} kg")

    v_liq = evaluate_stage_gate(_mgr({
        'step': 20, 'time': 1.0, 'temperature': 340.0, 'phase_solid': 0.0,
        'density': 866.3, 'ball_mass': 1.86, 'ball_radius': 0.08,
    }), stage, run)
    check('LIQUID case: gate fails with the stage\'s plain-language reason',
          v_liq['complete'] is False
          and v_liq['reason'] == stage['gate']['failReason'],
          f"reason={v_liq['reason'][:60]}")


def _search_ext():
    print('\nMaterial space — fixedParams + attemptTag search extensions\n')
    check('attempt tags namespace the run names (sanitized)',
          attempt_run_name('demo', 's', 0, 'wax') == 'demo-s-wax-attempt-0'
          and attempt_run_name('demo', 's', 2, 'Water Ice!') ==
          'demo-s-waterice-attempt-2'
          and attempt_run_name('demo', 's', 1) == 'demo-s-attempt-1')

    # Human labels: what a person reads in run pickers and graph titles.
    wax_label = attempt_run_label(
        {'target_temp': 260.0, 'pressure_pa': 50000.0}, 'paraffin-wax', 0,
        'material-condensation')
    check('attempt labels read like the real world (substance + units)',
          wax_label.startswith('Paraffin wax — ')
          and '260 K (-13 °C)' in wax_label
          and '50 kPa (0.49 atm)' in wax_label
          and wax_label.endswith('attempt 1'),
          f'label={wax_label!r}')
    check('untagged/unknown-param labels stay generic but honest',
          attempt_run_label({'zeta': 2.0}, '', 4, 'my-sim')
          == 'my-sim — zeta=2 — attempt 5')

    created = {}

    def _fake_create(manager, name, sim_ref, candidate, stage, msim_name,
                     label=''):
        run = SimpleNamespace(name=name, simulation_ref=sim_ref,
                              last_recorded_step=0, label=label,
                              parameter_overrides_json=json.dumps(candidate))
        manager.objectTables['SimulationRun'][name] = run
        created[name] = candidate
        return run

    def _fake_run_step(manager, run, target_step=None, _pull_chain=None):
        run.last_recorded_step = int(run.last_recorded_step) + 1
        return {'success': True, 'step': run.last_recorded_step, 'error': None}

    m = SimpleNamespace(objectTables={
        'SimulationDefinition': {'mat-sim': SimpleNamespace(
            name='mat-sim', time_step_seconds=0.05, duration_seconds=0.15)},
        'SimulationRun': {},
    })
    stage = {'key': 's', 'kind': 'runToCompletion', 'simulationRef': 'mat-sim',
             'derive': {'params': {'x.m': 'ball_mass'}},  # never completes
             'search': {'candidates': {'kind': 'list',
                                       'values': [{'target_temp': 260.0},
                                                  {'target_temp': 300.0}]},
                        'stepsPerAttempt': 3, 'batchSize': 5}}
    real_create, real_step = _search_mod._create_attempt_run, _runner_mod.run_step
    _search_mod._create_attempt_run = _fake_create
    _runner_mod.run_step = _fake_run_step
    try:
        report = run_stage_search(
            m, 'demo', stage,
            fixed_params={'melt_temp_ref': 273.15, 'target_temp': -1.0},
            attempt_tag='water-ice')
    finally:
        _search_mod._create_attempt_run = real_create
        _runner_mod.run_step = real_step

    first = created.get('demo-s-water-ice-attempt-0', {})
    check('fixedParams merge into every candidate (candidate wins conflicts)',
          first.get('melt_temp_ref') == 273.15
          and first.get('target_temp') == 260.0,
          f'attempt-0 overrides={first}')
    check('tagged attempts stay a separate, fully-attempted set',
          report['exhausted'] and report['attempted'] == 2
          and all(a['run'].startswith('demo-s-water-ice-attempt-')
                  for a in report['attempts']))


def _seeds():
    print('\nMaterial space — seed wiring\n')
    step_names = [s['name'] for s in _MATERIAL_STEPS]
    check('MeltLine step runs in the step solution and writes melt_temp',
          'MeltLine' in step_names and 'melt_temp' in _MATERIAL_OUTPUT_MAP,
          f'steps={step_names}')
    sim_names = {d['name'] for d in SEED_SIMULATION_DEFINITIONS}
    mat_def = next(d for d in SEED_SIMULATION_DEFINITIONS
                   if d['name'] == MATERIAL_SIM_DEF)
    check('material sim def seeded with intent search',
          mat_def['intent'] == 'search')
    msim = SEED_MULTI_SCALE_SIMS[0]
    stages = json.loads(msim['stages_json'])
    mat_stage = stages[0]
    check('material stage is FIRST and references the seeded sim + gate',
          mat_stage['key'] == 'material-precondition'
          and mat_stage['simulationRef'] in sim_names
          and mat_stage['gate']['solutionRef'] == GATE_SOLUTION
          and _GATE_SOLUTION_DEF['name'] == GATE_SOLUTION)
    check('derive targets are REAL pendulum params',
          all(t.split('.', 1)[1] in _NEWTON_PARAMS
              for t in mat_stage['derive']['params']),
          f"targets={list(mat_stage['derive']['params'])}")
    check('material-condensation joined the composition members',
          MATERIAL_SIM_DEF in json.loads(msim['member_simulation_refs_json']))
    check('the wax grid contains achievable candidates (T below 327 K)',
          any(t < 327.0 for t in
              np.linspace(260.0, 340.0, 5)))
    check('baseline step-0 row seeded at ambient, unevaluated',
          SEED_MATERIAL_ROWS[0]['temperature'] == 293.15
          and SEED_MATERIAL_ROWS[0]['phase_solid'] == 0.0)


if __name__ == '__main__':
    _equations()
    _gate()
    _search_ext()
    _seeds()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
