"""
Self-test for the wind-field space + its coupling into the Newtonian
pendulum (the first multi-scale composition).

Run from polari-framework/:
    python3 -m simulations.selftest_wind_coupling

Five layers, none needing the server or sudo:

  1. EQUATIONS — the three seeded matrix equations execute with their
     REAL expr strings: wind-field-evolve (shape/centers/determinism),
     field-sample-nearest (picks the right cell), newton-wind-drag
     (exact vacuum zero at wind_on=0; magnitude/direction vs a NumPy
     mirror at wind_on=1).
  2. ENGINE SOURCES — json_decode / json_encode round-trip matrix-valued
     state through the value-source layer.
  3. SOLUTION WIRING — the wind evolve solution is a Complete tagged to
     wind-field-3d, the drag Partial is tagged to newtonian-pendulum-3d
     (regression guard for the seed ref-tag bug), and the drag Partial
     contributes adds on f_app_* + sets on fwind_*.
  4. COUPLING — apply_couplings: defaults on an uncoupled run; zero-order
     -hold sampling of the right wind row on a coupled run; lazy pull
     advances the source run exactly to coverage (stubbed run_step);
     cycle guard.
  5. SCENE — compile_3d over the seeded newtonian scene with the COUPLED
     run filter shows the bob AND the wind-field cell arrows (run-scope
     expansion), while the vacuum run filter shows no wind cells.
"""

import json
from types import SimpleNamespace

import numpy as np

from matrices.seed_data import SEED_MATRIX_EQUATIONS
from matrices.matrix_equation_executor import evaluate_equation
from polariNoCode.SolutionExecutionEngine import _resolve_value_source_config
from simSpace.compilers.compile_3d import compile_3d
from simSpace.compilers.field_projection import emit_field_3d, _decimation_hash
from simulations.seed_data import SEED_PENDULUM_SIMSPACES, SEED_PENDULUM_BINDINGS
from simulations.simulation_runner import _detect_step_role
from simulations.simulation_coupling import apply_couplings
from simulations.wind_field_grid_sim_state import build_initial_cells
from simulations.newtonian_pendulum_seed import NEWTON_SIM_DEF, _NB
# Importing wind_field_seed extends the shared seed lists + the newtonian
# scene's bound classes in place — required before the scene compile check.
from simulations.wind_field_seed import (
    _WIND_STEP_DEF, _WIND_STEP_META, _WIND_DRAG_DEF, _WIND_DRAG_META,
    SEED_SIMULATION_COUPLINGS,
    SEED_NEWTON_WIND_BOB_ROWS, SEED_NEWTON_WIND_ROD_ROWS,
    WIND_SIM_DEF, WIND_RUN_NAME, NEWTON_WIND_RUN_NAME,
    _WIND_DT, _WIND_PARAMS,
)
import simulations.simulation_runner as _runner_mod

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _eq_def(name):
    row = next(e for e in SEED_MATRIX_EQUATIONS if e['name'] == name)
    return SimpleNamespace(**row)


# ---------------------------------------------------------------------------
# 1. The three matrix equations, with their real seeded exprs.
# ---------------------------------------------------------------------------
def _equations():
    print('Wind coupling — matrix equations (real seeded exprs)\n')

    cells = np.asarray(build_initial_cells())
    bindings = {
        'cells': cells.tolist(), 't': 0.1,
        'a': _WIND_PARAMS['wind_amp'], 'w': _WIND_PARAMS['wind_freq'],
        'bx': _WIND_PARAMS['wind_base_x'], 'bz': _WIND_PARAMS['wind_base_z'],
    }
    out1 = evaluate_equation(_eq_def('wind-field-evolve'), bindings)
    out2 = evaluate_equation(_eq_def('wind-field-evolve'), bindings)
    check('evolve keeps the N×6 shape', out1.shape == cells.shape,
          f'shape={out1.shape}')
    check('evolve carries cell centers through unchanged',
          np.allclose(out1[:, :3], cells[:, :3]))
    speeds = np.linalg.norm(out1[:, 3:], axis=1)
    check('evolve produces nonzero, finite, spatially-varying wind',
          np.isfinite(out1).all() and speeds.max() > 1.0
          and speeds.std() > 0.01,
          f'|w| range=[{speeds.min():.2f}, {speeds.max():.2f}] m/s')
    check('evolve is deterministic (same inputs → same field)',
          np.array_equal(out1, out2))

    sample_cells = [[0.5, -0.9, 0.0, 2.0, 0.5, 1.0],
                    [-1.0, -1.0, -1.0, 9.0, 9.0, 9.0]]
    picked = evaluate_equation(
        _eq_def('field-sample-nearest'),
        {'cells': sample_cells, 'pos': [0.45, -0.85, 0.05]},
    )
    check('nearest-cell sampler picks the closest cell\'s velocity',
          np.allclose(picked, [2.0, 0.5, 1.0]), f'picked={picked.tolist()}')

    rho, cd, area = 1.225, 0.47, 0.0201
    w_vec, v_vec = [5.0, 0.0, 1.0], [1.0, 0.0, 0.0]
    drag_off = evaluate_equation(
        _eq_def('newton-wind-drag'),
        {'won': 0.0, 'rho': rho, 'cd': cd, 'area': area, 'w': w_vec, 'v': v_vec},
    )
    check('drag is EXACTLY zero at wind_on=0 (vacuum run preserved)',
          np.allclose(drag_off, [0.0, 0.0, 0.0]), f'F={drag_off.tolist()}')
    drag_on = evaluate_equation(
        _eq_def('newton-wind-drag'),
        {'won': 1.0, 'rho': rho, 'cd': cd, 'area': area, 'w': w_vec, 'v': v_vec},
    )
    rel = np.asarray(w_vec) - np.asarray(v_vec)
    mirror = 0.5 * rho * cd * area * np.linalg.norm(rel) * rel
    check('drag matches the NumPy mirror of ½ρ·C_d·A·|w−v|·(w−v)',
          np.allclose(drag_on, mirror),
          f'F={np.round(drag_on, 5).tolist()} N')
    check('drag points along the relative flow (w−v)',
          np.dot(drag_on, rel) > 0)


# ---------------------------------------------------------------------------
# 2. json_decode / json_encode value sources.
# ---------------------------------------------------------------------------
def _sources():
    print('\nWind coupling — engine json value sources\n')
    ctx = {'cells_json': '[[1.0, 2.0], [3.0, 4.0]]', 'cells_new': [[5, 6]]}
    decoded = _resolve_value_source_config(
        {'sourceType': 'json_decode',
         'source': {'sourceType': 'from_source_object', 'sourceObjectPath': 'self.cells_json'}},
        ctx,
    )
    check('json_decode parses a matrix-valued state field',
          decoded == [[1.0, 2.0], [3.0, 4.0]], f'decoded={decoded}')
    encoded = _resolve_value_source_config(
        {'sourceType': 'json_encode',
         'source': {'sourceType': 'from_source_object', 'sourceObjectPath': 'cells_new'}},
        ctx,
    )
    check('json_encode serializes a computed matrix back to JSON text',
          json.loads(encoded) == [[5, 6]], f'encoded={encoded}')
    malformed = _resolve_value_source_config(
        {'sourceType': 'json_decode',
         'source': {'sourceType': 'from_source_object', 'sourceObjectPath': 'cells_json'}},
        {'cells_json': '{not json'},
    )
    check('json_decode degrades to None on malformed text', malformed is None)


# ---------------------------------------------------------------------------
# 3. Solution wiring (roles + sim-def ref tags + contribution ops).
# ---------------------------------------------------------------------------
def _wiring():
    print('\nWind coupling — solution wiring\n')
    check('wind evolve solution is a Complete',
          _detect_step_role(json.loads(_WIND_STEP_DEF['definition'])) == 'simStepComplete')
    check('wind evolve solution is tagged to wind-field-3d (ref-tag guard)',
          _WIND_STEP_META['simulation_definition_ref'] == WIND_SIM_DEF,
          f"ref={_WIND_STEP_META['simulation_definition_ref']}")
    check('drag solution is a Partial',
          _detect_step_role(json.loads(_WIND_DRAG_DEF['definition'])) == 'simStepPartial')
    check('drag Partial is tagged to newtonian-pendulum-3d (ref-tag guard)',
          _WIND_DRAG_META['simulation_definition_ref'] == NEWTON_SIM_DEF,
          f"ref={_WIND_DRAG_META['simulation_definition_ref']}")
    graph = json.loads(_WIND_DRAG_DEF['definition'])
    terminator = next(s for s in graph['stateInstances']
                      if s.get('stateClass') == 'SimStepContribution')
    ops = {m['outputFieldName']: m['op']
           for m in terminator['boundObjectFieldValues']['outputMappings']}
    check('drag Partial ADDS into f_app_* and SETS fwind_*',
          ops.get('f_app_x') == 'add' and ops.get('f_app_y') == 'add'
          and ops.get('f_app_z') == 'add' and ops.get('fwind_x') == 'set'
          and ops.get('fwind_z') == 'set',
          f'ops={ops}')


# ---------------------------------------------------------------------------
# 4. Coupling pre-pass (defaults / ZOH sampling / lazy pull / cycle guard).
# ---------------------------------------------------------------------------
def _coupling_manager(grid_rows, wind_last_step=10):
    eq_row = _eq_def('field-sample-nearest')
    wind_def = SimpleNamespace(name=WIND_SIM_DEF, time_step_seconds=_WIND_DT)
    wind_run = SimpleNamespace(
        name=WIND_RUN_NAME, simulation_ref=WIND_SIM_DEF,
        last_recorded_step=wind_last_step, time_step_seconds=0.0,
    )
    coupled_run = SimpleNamespace(
        name=NEWTON_WIND_RUN_NAME, simulation_ref=NEWTON_SIM_DEF,
        coupled_run_refs_json=json.dumps({WIND_SIM_DEF: WIND_RUN_NAME}),
    )
    vacuum_run = SimpleNamespace(
        name='newtonian-pendulum-run', simulation_ref=NEWTON_SIM_DEF,
        coupled_run_refs_json='{}',
    )
    m = SimpleNamespace()
    m.objectTables = {
        'SimulationCouplingDefinition': {
            c['name']: SimpleNamespace(**c) for c in SEED_SIMULATION_COUPLINGS
        },
        'SimulationRun': {r.name: r for r in (wind_run, coupled_run, vacuum_run)},
        'SimulationDefinition': {wind_def.name: wind_def},
        'MatrixEquationDefinition': {eq_row.name: eq_row},
        'WindFieldGridState': {r.name: r for r in grid_rows},
    }
    return m, coupled_run, vacuum_run, wind_run


def _grid_row(step, time, cells):
    return SimpleNamespace(
        name=f'{WIND_RUN_NAME}-wind-field-grid-{step}',
        simulation_run_ref=WIND_RUN_NAME, step=step, time=time,
        cells_json=json.dumps(cells),
    )


def _coupling():
    print('\nWind coupling — apply_couplings pre-pass\n')
    sim_def = SimpleNamespace(name=NEWTON_SIM_DEF)
    near_bob = [0.5, -0.87, 0.0]
    rows = [
        _grid_row(0, 0.0, [near_bob + [2.0, 0.0, 1.0], [-1, -1, -1, 9, 9, 9]]),
        _grid_row(1, 0.1, [near_bob + [4.0, 0.5, 3.0], [-1, -1, -1, 9, 9, 9]]),
    ]

    # Uncoupled run → defaults only.
    m, coupled_run, vacuum_run, wind_run = _coupling_manager(rows)
    baseline = {'px': 0.5, 'py': -0.866, 'pz': 0.0}
    warnings = []
    apply_couplings(m, vacuum_run, sim_def, _NB, baseline, 0.05, warnings,
                    pull_chain=frozenset({vacuum_run.name}))
    check('uncoupled run gets the defaults (wind_on=0, w=0)',
          baseline.get('wind_on') == 0.0 and baseline.get('wind_vx') == 0.0
          and not warnings, f'baseline wind_on={baseline.get("wind_on")}')

    # Coupled run at t=0.05 → ZOH picks the step-0 wind row (0.1 > 0.05).
    baseline = {'px': 0.5, 'py': -0.866, 'pz': 0.0}
    warnings = []
    apply_couplings(m, coupled_run, sim_def, _NB, baseline, 0.05, warnings,
                    pull_chain=frozenset({coupled_run.name}))
    check('coupled run samples the nearest cell of the latest wind row ≤ t',
          baseline.get('wind_on') == 1.0 and baseline.get('wind_vx') == 2.0
          and baseline.get('wind_vz') == 1.0,
          f'w=({baseline.get("wind_vx")}, {baseline.get("wind_vy")}, {baseline.get("wind_vz")})')

    # t=0.15 → ZOH advances to the step-1 wind row.
    baseline = {'px': 0.5, 'py': -0.866, 'pz': 0.0}
    apply_couplings(m, coupled_run, sim_def, _NB, baseline, 0.15, [],
                    pull_chain=frozenset({coupled_run.name}))
    check('zero-order hold advances with time (t=0.15 → wind step 1)',
          baseline.get('wind_vx') == 4.0 and baseline.get('wind_vz') == 3.0,
          f'wind_vx={baseline.get("wind_vx")}')

    # Lazy pull: wind run behind (last=0), target t=0.35 → exactly 4 pulls
    # (0.4 s coverage) via a stubbed run_step.
    m, coupled_run, _, wind_run = _coupling_manager(rows, wind_last_step=0)
    pulls = []
    real_run_step = _runner_mod.run_step

    def _stub_run_step(mgr, run, target_step=None, _pull_chain=None):
        pulls.append(run.name)
        run.last_recorded_step = int(run.last_recorded_step) + 1
        return {'success': True, 'step': run.last_recorded_step, 'error': None}

    _runner_mod.run_step = _stub_run_step
    try:
        baseline = {'px': 0.5, 'py': -0.866, 'pz': 0.0}
        warnings = []
        apply_couplings(m, coupled_run, sim_def, _NB, baseline, 0.35, warnings,
                        pull_chain=frozenset({coupled_run.name}))
    finally:
        _runner_mod.run_step = real_run_step
    check('lazy pull advances the wind run exactly to coverage (4 × dt=0.1 ≥ 0.35)',
          pulls == [WIND_RUN_NAME] * 4 and wind_run.last_recorded_step == 4,
          f'pulls={len(pulls)}')
    check('sampling still lands after the pull (ZOH on existing rows)',
          baseline.get('wind_on') == 1.0)

    # Cycle guard: the wind run already in the pull chain → no pull, but
    # sampling proceeds on whatever rows exist.
    m, coupled_run, _, wind_run = _coupling_manager(rows, wind_last_step=0)
    baseline = {'px': 0.5, 'py': -0.866, 'pz': 0.0}
    warnings = []
    apply_couplings(m, coupled_run, sim_def, _NB, baseline, 0.35, warnings,
                    pull_chain=frozenset({coupled_run.name, WIND_RUN_NAME}))
    check('coupling cycle is guarded (warns, samples existing rows)',
          any('cycle' in w.lower() for w in warnings)
          and baseline.get('wind_on') == 1.0,
          f'warnings={warnings[:1]}')


# ---------------------------------------------------------------------------
# 5. Field projection + full scene compile with run-scope expansion.
# ---------------------------------------------------------------------------
def _field_binding_dict():
    row = next(b for b in SEED_PENDULUM_BINDINGS
               if b['name'] == 'WindFieldGridState-3d')
    return json.loads(row['binding_json'])


def _scene():
    print('\nWind coupling — field projection + scene compile (run scope)\n')

    # Determinism + hiding rules of the emitter itself.
    strong = [[0.1 * i, -0.5, 0.0, 5.0, 0.0, 2.0] for i in range(8)]
    weak_idx = 3
    strong[weak_idx][3:] = [0.05, 0.0, 0.0]   # below the magnitude floor
    inst = SimpleNamespace(name='row-1', simulation_run_ref=WIND_RUN_NAME,
                           step=1, time=0.1, cells_json=json.dumps(strong))
    binding = _field_binding_dict()
    out1 = emit_field_3d('WindFieldGridState', {'k': inst}, binding,
                         'WindFieldGridState-3d', None, [])
    out2 = emit_field_3d('WindFieldGridState', {'k': inst}, binding,
                         'WindFieldGridState-3d', None, [])
    check('field emitter emits one entry per cell (hidden cells included)',
          len(out1) == 8, f'count={len(out1)}')
    check('field emitter is deterministic (scrub-safe)', out1 == out2)
    keys = [v['key'] for v in out1]
    check('per-cell keys are distinct and stable-format',
          len(set(keys)) == 8 and keys[0].endswith(':0'), f'key0={keys[0]}')
    weak_vec = out1[weak_idx]['vec']
    check('below-floor cell emits a ZERO vector (arrow hidden, not stale)',
          weak_vec == [0.0, 0.0, 0.0])
    visible = [v for v in out1 if v['vec'] != [0.0, 0.0, 0.0]]
    density = binding['decimation']['density']
    expected_visible = [
        i for i in range(8)
        if i != weak_idx and _decimation_hash(i, 1) < density
    ]
    check('decimation matches the deterministic hash exactly',
          len(visible) == len(expected_visible)
          and 0 < len(visible) < 8,
          f'visible={len(visible)}/8 at density={density}')

    # Full scene compile: coupled run shows bob + wind cells; vacuum doesn't.
    scene = next(s for s in SEED_PENDULUM_SIMSPACES
                 if s['name'] == 'newtonian-pendulum-viz')
    bound = [e['className'] for e in json.loads(scene['bound_classes_json'])]
    check('newtonian scene now binds the wind grid class',
          'WindFieldGridState' in bound, f'bound={bound}')

    def _rows(seed_rows):
        return {r['name']: SimpleNamespace(**r) for r in seed_rows}

    grid_row = SimpleNamespace(
        name=f'{WIND_RUN_NAME}-wind-field-grid-1', simulation_run_ref=WIND_RUN_NAME,
        step=1, time=0.1, cells_json=json.dumps(strong),
    )
    mgr = SimpleNamespace()
    mgr.objectTypingDict = {}
    mgr.objectTables = {
        'NewtonianPendulumBobSimState': _rows(SEED_NEWTON_WIND_BOB_ROWS),
        'NewtonianPendulumRodSimState': _rows(SEED_NEWTON_WIND_ROD_ROWS),
        'WindFieldGridState': {grid_row.name: grid_row},
        'SimSpaceBindingDefinition': {
            b['name']: SimpleNamespace(**b) for b in SEED_PENDULUM_BINDINGS
        },
        'SimulationRun': {
            NEWTON_WIND_RUN_NAME: SimpleNamespace(
                name=NEWTON_WIND_RUN_NAME,
                coupled_run_refs_json=json.dumps({WIND_SIM_DEF: WIND_RUN_NAME}),
            ),
            'newtonian-pendulum-run': SimpleNamespace(
                name='newtonian-pendulum-run', coupled_run_refs_json='{}',
            ),
        },
    }
    scene_row = SimpleNamespace(**scene)

    objects, connections, vectors = compile_3d(
        mgr, scene_row, [], [], run_filter=NEWTON_WIND_RUN_NAME,
    )
    field_vecs = [v for v in vectors
                  if v['classRef']['className'] == 'WindFieldGridState']
    bob_objs = [o for o in objects
                if o.get('classRef', {}).get('className') == _NB]
    check('coupled run filter renders the bob AND the wind cells together',
          len(bob_objs) == 1 and len(field_vecs) == 8,
          f'bob={len(bob_objs)} windCells={len(field_vecs)}')

    objects_v, _, vectors_v = compile_3d(
        mgr, scene_row, [], [], run_filter='newtonian-pendulum-run',
    )
    field_vecs_v = [v for v in vectors_v
                    if v['classRef']['className'] == 'WindFieldGridState']
    check('vacuum run filter shows NO wind cells (scope not expanded)',
          len(field_vecs_v) == 0, f'windCells={len(field_vecs_v)}')


if __name__ == '__main__':
    _equations()
    _sources()
    _wiring()
    _coupling()
    _scene()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
