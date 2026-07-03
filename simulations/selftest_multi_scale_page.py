"""
Self-test for the Multi-Scale Simulation Page backend (Phase 1):
timeseries extraction, the stage/gate model, and the demo seeds.

Run from polari-framework/:
    python3 -m simulations.selftest_multi_scale_page
"""

import json
import math
from types import SimpleNamespace

from simulations.simulation_series import build_series
from simulations.multi_scale_stages import (
    apply_derive,
    evaluate_stage_gate,
    find_stage,
    flatten_stage_results,
    parse_stages,
)
import simulations.multi_scale_search as _search_mod
import simulations.simulation_runner as _runner_mod
from simulations.multi_scale_search import (
    attempt_run_name,
    generate_candidates,
    run_stage_search,
)
from simulations.multi_scale_seed import (
    SEED_MULTI_SCALE_SIMS, SEED_IC_INTERFACES, SEED_MSIM_GRAPHS,
    MSIM_NAME, IC_MATERIAL_PICKER,
)
from simulations.seed_data import (
    SEED_SIMULATION_DEFINITIONS, SEED_SIMULATION_RUNS, SEED_PENDULUM_SIMSPACES,
)
from simulations.wind_field_seed import (
    SEED_SIMULATION_COUPLINGS, WIND_RUN_NAME, NEWTON_WIND_RUN_NAME, WIND_SIM_DEF,
)
from simulations.newtonian_pendulum_seed import _NEWTON_BOB_RADIUS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _row(cls_prefix, run, step, **fields):
    return SimpleNamespace(
        name=f'{run}-{cls_prefix}-{step}', simulation_run_ref=run,
        step=step, time=round(step * 0.01, 6), **fields,
    )


def _series_manager():
    bob_rows = [_row('bob', NEWTON_WIND_RUN_NAME, s,
                     energy_total=1.3 - 0.01 * s, pz=0.001 * s, label='x')
                for s in range(6)]
    wind_rows = [SimpleNamespace(
        name=f'{WIND_RUN_NAME}-grid-{s}', simulation_run_ref=WIND_RUN_NAME,
        step=s, time=s * 0.1, cells_json='[]') for s in range(2)]
    m = SimpleNamespace()
    m.objectTables = {
        'NewtonianPendulumBobSimState': {r.name: r for r in bob_rows},
        'WindFieldGridState': {r.name: r for r in wind_rows},
        'SimulationRun': {
            NEWTON_WIND_RUN_NAME: SimpleNamespace(
                name=NEWTON_WIND_RUN_NAME,
                coupled_run_refs_json=json.dumps({WIND_SIM_DEF: WIND_RUN_NAME}),
            ),
        },
    }
    return m


def _series():
    print('Multi-scale page — /series extraction\n')
    m = _series_manager()

    out = build_series(m, NEWTON_WIND_RUN_NAME, 'NewtonianPendulumBobSimState',
                       ['energy_total', 'pz'])
    check('series returns all steps for the run, sorted',
          out['steps'] == list(range(6)) and out['lastStep'] == 5)
    check('requested fields come back aligned per step',
          len(out['fields']['energy_total']) == 6
          and abs(out['fields']['pz'][5] - 0.005) < 1e-12)

    out_auto = build_series(m, NEWTON_WIND_RUN_NAME,
                            'NewtonianPendulumBobSimState', [])
    check('empty fields → numeric fields auto-discovered (identity + '
          'non-numeric excluded)',
          sorted(out_auto['fields'].keys()) == ['energy_total', 'pz'],
          f"fields={sorted(out_auto['fields'].keys())}")

    out_inc = build_series(m, NEWTON_WIND_RUN_NAME,
                           'NewtonianPendulumBobSimState', ['pz'], since_step=3)
    check('sinceStep returns only newer steps (incremental polling)',
          out_inc['steps'] == [4, 5])

    out_range = build_series(m, NEWTON_WIND_RUN_NAME,
                             'NewtonianPendulumBobSimState', ['pz'],
                             step_from=1, step_to=3)
    check('stepFrom/stepTo clamp inclusively', out_range['steps'] == [1, 2, 3])

    out_wind = build_series(m, NEWTON_WIND_RUN_NAME, 'WindFieldGridState', [])
    check('coupled source class is readable through the PRIMARY run '
          '(shared run scope)', out_wind['steps'] == [0, 1],
          f"steps={out_wind['steps']}")


def _stages():
    print('\nMulti-scale page — stage/gate model\n')
    msim = SimpleNamespace(**SEED_MULTI_SCALE_SIMS[0])
    stages = parse_stages(msim)
    check('demo stages parse (single coStep stage)',
          len(stages) == 1 and stages[0]['kind'] == 'coStep')
    check('find_stage resolves by key',
          find_stage(msim, 'pendulum-in-wind') is not None
          and find_stage(msim, 'nope') is None)

    # No-gate runToCompletion semantics: complete once the run has stepped.
    stage = {'key': 's1', 'kind': 'runToCompletion', 'simulationRef': 'x'}
    m = SimpleNamespace(objectTables={})
    fresh = SimpleNamespace(name='r', simulation_ref='x', last_recorded_step=0, status='pending')
    ran = SimpleNamespace(name='r', simulation_ref='x', last_recorded_step=7, status='running')
    v0 = evaluate_stage_gate(m, stage, fresh)
    v1 = evaluate_stage_gate(m, stage, ran)
    check('gateless stage: incomplete before running, complete after',
          v0['complete'] is False and v1['complete'] is True
          and v0['hasGate'] is False)

    # "Defined AND achieved": a first-principles stage (one later stages
    # derive from) is NEVER complete without a gate, even after running.
    stage_fp = dict(stage, derive={'params': {'x.mass': 'ball_mass'}})
    v_fp = evaluate_stage_gate(m, stage_fp, ran)
    check('derive-source stage without a gate is incomplete (condition '
          'must be DEFINED, not just run)',
          v_fp['complete'] is False and 'not defined' in v_fp['reason'])

    # Missing gate solution → structured error, never a crash.
    stage_bad = dict(stage, gate={'solutionRef': 'does-not-exist'})
    m_bad = SimpleNamespace(objectTables={
        'SolutionDefinition': {}, 'SimulationExecutionSolution': {},
    })
    v_bad = evaluate_stage_gate(m_bad, stage_bad, ran)
    check('missing gate solution degrades to an error verdict',
          v_bad['complete'] is False and 'not found' in (v_bad['error'] or ''))

    # Context assembly for gates: params + latest rows + run info.
    sim_def = SimpleNamespace(
        name='mat-sim',
        participating_sim_state_classes_json=json.dumps(['MatState']),
        parameters_json=json.dumps({'pressure': 2.0}),
    )
    rows = [_row('mat', 'mat-run', s, phase_solid=float(s >= 2), ball_r=0.05)
            for s in range(3)]
    m_ctx = SimpleNamespace(objectTables={
        'SimulationDefinition': {'mat-sim': sim_def},
        'MatState': {r.name: r for r in rows},
    })
    run_ctx = SimpleNamespace(name='mat-run', simulation_ref='mat-sim',
                              last_recorded_step=2, status='running')
    flat = flatten_stage_results(
        m_ctx, {'key': 's', 'simulationRef': 'mat-sim'}, run_ctx)
    check('gate context: params + LATEST row fields + run info, '
          'validator-style keys',
          flat['params.pressure'] == 2.0
          and flat['MatState.phase_solid'] == 1.0
          and flat['MatState.ball_r'] == 0.05
          and flat['run.last_recorded_step'] == 2,
          f"keys={sorted(k for k in flat if '.' in k)}")

    # Derive mapping: gate outputs → later stages' params/fields.
    stage_d = {'key': 's', 'derive': {
        'params': {'newtonian-pendulum-3d.mass': 'ball_mass',
                   'newtonian-pendulum-3d.bob_radius': 'ball_radius',
                   'newtonian-pendulum-3d.missing': 'not_produced'},
        'fields': {'newtonian-pendulum-3d.NewtonianPendulumBobSimState.py': 'start_y'},
    }}
    resolved = apply_derive(stage_d, {'ball_mass': 1.97, 'ball_radius': 0.05,
                                      'start_y': -0.9})
    check('derive resolves outputs into per-sim param/field bundles '
          '(missing outputs skipped)',
          resolved['params']['newtonian-pendulum-3d'] ==
          {'mass': 1.97, 'bob_radius': 0.05}
          and resolved['fields']['newtonian-pendulum-3d']
          ['NewtonianPendulumBobSimState'] == {'py': -0.9})


def _seeds():
    print('\nMulti-scale page — demo seeds\n')
    msim = SEED_MULTI_SCALE_SIMS[0]
    members = json.loads(msim['member_simulation_refs_json'])
    couplings = json.loads(msim['coupling_refs_json'])
    panels = json.loads(msim['panels_json'])
    compare = json.loads(msim['compare_run_policy_json'])

    sim_names = {d['name'] for d in SEED_SIMULATION_DEFINITIONS}
    run_names = {r['name'] for r in SEED_SIMULATION_RUNS}
    coupling_names = {c['name'] for c in SEED_SIMULATION_COUPLINGS}
    scene_names = {s['name'] for s in SEED_PENDULUM_SIMSPACES}
    ic_names = {i['name'] for i in SEED_IC_INTERFACES}
    graph_names = {g['name'] for g in SEED_MSIM_GRAPHS}

    check('demo members reference seeded SimulationDefinitions',
          set(members) <= sim_names, f'members={members}')
    check('demo coupling reference resolves',
          set(couplings) <= coupling_names)
    check('primary sim is a member',
          msim['primary_simulation_ref'] in members)
    check('panel refs resolve (scene + graphs + IC interface)',
          all((p['kind'] != 'scene' or p['simSpaceRef'] in scene_names)
              and (p['kind'] != 'graph' or p['graphRef'] in graph_names)
              and (p['kind'] != 'ic' or p['icInterfaceRef'] in ic_names)
              for p in panels), f'panels={[p["kind"] for p in panels]}')
    check('graph seeds: wrapped graphConfig form with real bob row fields',
          all(f in ('energy_total', 'ke', 'pe', 'fwind_x', 'fwind_y', 'fwind_z',
                    'pz', 'vz')
              for g in SEED_MSIM_GRAPHS
              for f in json.loads(g['definition'])['graphConfig']['yDimensions']))
    check('comparison runs reference seeded runs',
          set(compare.get('runs', [])) <= run_names)

    ic = SEED_IC_INTERFACES[0]
    cfg = json.loads(ic['config_json'])
    vol = (4.0 / 3.0) * math.pi * _NEWTON_BOB_RADIUS ** 3
    ice = next(c for c in cfg['choices'] if c['key'] == 'ice')
    lead = next(c for c in cfg['choices'] if c['key'] == 'lead')
    check('material choices carry real density-derived masses',
          abs(ice['setParams']['mass'] - 917.0 * vol) < 1e-3
          and abs(lead['setParams']['mass'] - 11340.0 * vol) < 1e-3,
          f"ice={ice['setParams']['mass']}kg lead={lead['setParams']['mass']}kg")
    check('derived geometry params configured for the wind drag',
          'bob_cross_section' in cfg['derivedParams'])
    check('demo names stable', msim['name'] == MSIM_NAME
          and ic['name'] == IC_MATERIAL_PICKER)


def _intents():
    print('\nMulti-scale page — intents taxonomy + composition coherence\n')
    from simulations.simulation_intents import (
        INTENTS, PRODUCT_BEARING, intents_catalog, validate_composition,
    )
    cat = intents_catalog()
    check('taxonomy has all 8 intents with checklists',
          len(INTENTS) == 8
          and all(i['requires'] and i['produces'] and i['plugPoints']
                  for i in INTENTS.values()))
    check('product-bearing set matches the design',
          set(PRODUCT_BEARING) ==
          {'search', 'feasibility', 'optimize', 'calibrate'}
          and set(cat['continuous']) == {'observe'})

    def _mgr(stages, members=('mat-sim',), couplings=()):
        sims = {
            'mat-sim': SimpleNamespace(name='mat-sim', intent='observe'),
            'obs-sim': SimpleNamespace(name='obs-sim', intent='observe'),
        }
        return SimpleNamespace(objectTables={
            'SimulationDefinition': sims,
            'SimulationCouplingDefinition': {},
        }), SimpleNamespace(
            member_simulation_refs_json=json.dumps(list(members)),
            coupling_refs_json=json.dumps(list(couplings)),
            stages_json=json.dumps(stages),
        )

    # Coherent demo-shaped composition → no errors.
    m, msim = _mgr([{'key': 's', 'kind': 'coStep', 'intent': 'observe',
                     'primarySimulationRef': 'obs-sim'}],
                   members=('mat-sim', 'obs-sim'))
    check('coherent composition validates clean',
          validate_composition(m, msim) == [])

    # Rule: derive source must be product-bearing.
    m, msim = _mgr([{'key': 's', 'kind': 'runToCompletion',
                     'intent': 'observe', 'simulationRef': 'mat-sim',
                     'derive': {'params': {'x.m': 'ball_mass'}}}])
    f = validate_composition(m, msim)
    check('observe stage with a derive map is rejected (must be '
          'product-bearing)',
          any(x['level'] == 'error' and 'does not produce a solution'
              in x['message'] for x in f))

    # Rule: search intent needs candidates or at least a gate.
    m, msim = _mgr([{'key': 's', 'kind': 'runToCompletion',
                     'intent': 'search', 'simulationRef': 'mat-sim'}])
    f = validate_composition(m, msim)
    check('search stage without candidates or gate is rejected',
          any('neither candidates' in x['message'] for x in f))

    # Rule: compare can never be causal.
    m, msim = _mgr([{'key': 's', 'kind': 'coStep', 'intent': 'compare',
                     'primarySimulationRef': 'mat-sim'}])
    f = validate_composition(m, msim)
    check('compare stage is rejected (never a causal member)',
          any('causally independent' in x['message'] for x in f))

    # Rule: missing refs are errors, in plain language.
    m, msim = _mgr([{'key': 's', 'kind': 'coStep', 'intent': 'observe',
                     'primarySimulationRef': 'ghost-sim'}],
                   members=('mat-sim', 'ghost-member'),
                   couplings=('ghost-coupling',))
    f = validate_composition(m, msim)
    check('missing member/sim/coupling references are all reported',
          sum(1 for x in f if x['level'] == 'error') >= 3,
          f'findings={len(f)}')


def _search():
    print('\nMulti-scale page — solution search (multiple attempts per stage)\n')

    grid = generate_candidates({'candidates': {'kind': 'grid', 'parameters': {
        'temperature': {'from': 250, 'to': 350, 'steps': 3},
        'pressure': {'from': 1, 'to': 100, 'steps': 2},
    }}})
    check('grid candidates: cartesian product, ordered',
          len(grid) == 6 and grid[0] == {'pressure': 1.0, 'temperature': 250.0}
          and grid[-1] == {'pressure': 100.0, 'temperature': 350.0},
          f'n={len(grid)}')
    mid = generate_candidates({'candidates': {'kind': 'grid', 'parameters': {
        't': {'from': 10, 'to': 20, 'steps': 1}}}})
    check('single-step axis uses the midpoint', mid == [{'t': 15.0}])
    lst = generate_candidates({'candidates': {'kind': 'list',
                                              'values': [{'a': 1}, {'a': 2}]}})
    check('list candidates pass through', lst == [{'a': 1}, {'a': 2}])
    try:
        generate_candidates({'candidates': {'kind': 'solver'}})
        solver_raises = False
    except ValueError:
        solver_raises = True
    check('solver kind is loudly not-implemented (reserved)', solver_raises)

    # Orchestrator with a stubbed runner + attempt factory (the real
    # engine path is exercised live once a searchable stage exists).
    def _search_manager(steps_per_attempt=3):
        sim_def = SimpleNamespace(name='mat-sim', time_step_seconds=0.01,
                                  duration_seconds=0.05)
        m = SimpleNamespace(objectTables={
            'SimulationDefinition': {'mat-sim': sim_def},
            'SimulationRun': {},
        })
        return m

    def _fake_create(manager, name, sim_ref, candidate, stage, msim_name):
        run = SimpleNamespace(name=name, simulation_ref=sim_ref,
                              last_recorded_step=0,
                              parameter_overrides_json=json.dumps(candidate))
        manager.objectTables['SimulationRun'][name] = run
        return run

    def _fake_run_step(manager, run, target_step=None, _pull_chain=None):
        run.last_recorded_step = int(run.last_recorded_step) + 1
        return {'success': True, 'step': run.last_recorded_step, 'error': None}

    real_create = _search_mod._create_attempt_run
    real_run_step = _runner_mod.run_step
    _search_mod._create_attempt_run = _fake_create
    _runner_mod.run_step = _fake_run_step
    try:
        # ACHIEVED: a gateless stage with no derive completes once run →
        # the FIRST candidate wins and the rest are never attempted.
        stage = {'key': 's', 'kind': 'runToCompletion', 'simulationRef': 'mat-sim',
                 'search': {'candidates': {'kind': 'list',
                                           'values': [{'t': 1}, {'t': 2}, {'t': 3}]},
                            'stepsPerAttempt': 3, 'batchSize': 4}}
        m = _search_manager()
        report = run_stage_search(m, 'demo', stage)
        check('first valid solution wins and short-circuits the search',
              report['achieved'] and report['winner']['candidate'] == {'t': 1}
              and report['attempts'][1]['reason'] == 'not attempted yet',
              f"winner={report['winner']['run'] if report['winner'] else None}")
        check('attempt runs carry the candidate as parameter overrides',
              json.loads(m.objectTables['SimulationRun'][
                  attempt_run_name('demo', 's', 0)].parameter_overrides_json)
              == {'t': 1})

        # EXHAUSTED with data: derive-source stage without a gate can
        # NEVER complete → every attempt records the reason.
        stage_x = dict(stage, derive={'params': {'x.m': 'ball_mass'}})
        m = _search_manager()
        r1 = run_stage_search(m, 'demo', stage_x, batch_size=2)
        check('batching bounds work per call (2 of 3 attempted)',
              not r1['achieved'] and r1['attempted'] == 2
              and r1['advancedThisCall'] == 2)
        r2 = run_stage_search(m, 'demo', stage_x, batch_size=2)
        check('search is stateless/resumable (second call finishes it)',
              r2['attempted'] == 3 and r2['exhausted']
              and all('not defined' in a['reason'] for a in r2['attempts']),
              f"attempted={r2['attempted']}")
        check('exhausted report carries every attempt (the disabled-choice '
              'reason AND data)',
              len(r2['attempts']) == 3
              and all(a['candidate'] for a in r2['attempts']))
    finally:
        _search_mod._create_attempt_run = real_create
        _runner_mod.run_step = real_run_step


if __name__ == '__main__':
    _series()
    _stages()
    _seeds()
    _intents()
    _search()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
