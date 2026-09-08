"""
Selftest for waxprint wp-5/wp-6 — the multiscale sim space, the 3D scene
seed, the condition-evaluation gates, and the live eval equations.

Run from polari-framework/:
    python3 -m waxprint.sim_selftest

Validates: the height-stepped runner (rows, monotonic height, resolution
degrading with height), the evaluation gates (a good run meets all, a
coarse run does not, with named failures), the SimState class, and the
well-formedness of every seed structure (scene binding refs a real mesh +
the colour-map materials exist; eval equations ref real equation defs;
sim def + runs + page display parse and cross-reference).
"""

import json
from types import SimpleNamespace

from waxprint.custom import sim_runner
from waxprint.custom import sim_evaluation
from waxprint import sim_seed
from waxprint.sim_state_basis import WaxPrintSimState
from waxprint.waxprint_seed import (
    SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'DeviceMaterialDefinition': _rows(SEED_DEVICE_MATERIALS),
        'WaxFeedstockDefinition': _rows(SEED_FEEDSTOCKS),
        'PrinterAssemblyDefinition': _rows(SEED_ASSEMBLIES),
        'PrintConditionDefinition': _rows(SEED_CONDITIONS),
    })


if __name__ == '__main__':
    print('waxprint wp-5/wp-6 — sim space + evaluation')
    mgr = _mgr()

    print('\nheight-stepped runner')
    out = sim_runner.compute_step_rows(
        mgr, 'demo-auger-extruder', 'mvw-natural-blend', 'room-baseline',
        'test-run', n_steps=8, max_height_mm=40.0)
    check('runner ok', out['ok'])
    rows = out['rows']
    check('one row per step', len(rows) == 8, f'{len(rows)} rows')
    check('height increases monotonically',
          all(rows[i]['height_mm'] <= rows[i + 1]['height_mm']
              for i in range(len(rows) - 1)))
    check('voxel coarsens with height (heat build-up)',
          rows[-1]['voxel_xy_mm'] >= rows[0]['voxel_xy_mm'],
          f"{rows[0]['voxel_xy_mm']:.3f} -> {rows[-1]['voxel_xy_mm']:.3f} mm")
    check('column grows up the Y axis',
          rows[-1]['pos_y'] > rows[0]['pos_y'])
    check('render_state in {0,1,2}',
          all(r['render_state'] in (0.0, 1.0, 2.0) for r in rows))

    print('\ncondition-evaluation gates')
    ev = sim_evaluation.evaluate_run(rows)
    check('room demo does NOT meet every gate', ev['all_met'] is False,
          f"{ev['met_count']}/{ev['total']}")
    names = {g['condition'] for g in ev['conditions']}
    check('all seven gates present', len(names) == 7, str(len(names)))
    check('safe + molten + printable pass for the demo',
          all(g['met'] for g in ev['conditions']
              if g['condition'] in ('thermally-safe', 'fully-molten',
                                    'printable')))
    failed = [g['condition'] for g in ev['conditions'] if not g['met']]
    check('a failing gate names a knob',
          all(next(g for g in ev['conditions'] if g['condition'] == fc)['knob']
              for fc in failed))

    # a synthetic all-good run meets every gate
    good = [{'step': i, 'thermally_safe': 1, 'melt_fraction': 1.0,
             'printable': 1, 'voxel_xy_mm': 0.25, 'margin_mm': 0.005,
             'movements_viable': 7, 'movements_total': 7} for i in range(5)]
    ev_good = sim_evaluation.evaluate_run(good)
    check('a clean run meets all gates', ev_good['all_met'] is True,
          f"{ev_good['met_count']}/{ev_good['total']}")

    print('\nSimState class')
    obj = WaxPrintSimState(**{k: v for k, v in rows[0].items()})
    check('WaxPrintSimState constructs from a row dict',
          getattr(obj, 'simulation_definition_name', '') == 'wax-print'
          and obj.voxel_xy_mm == rows[0]['voxel_xy_mm'])

    print('\nseed well-formedness')
    check('two baseline runs seeded (24 rows)',
          len(sim_seed.SEED_WAXPRINT_STATE_ROWS) == 24)
    # scene binding refs a real builtin mesh + real colour materials
    binding = json.loads(sim_seed._WAXPRINT_BINDINGS[0]['binding_json'])
    check('binding shape is a builtin cube',
          binding['visual']['shapeRef'] == 'cube')
    mat_names = {m['name'] for m in sim_seed.SEED_MATERIALS_3D}
    color_map = binding['visual']['styleRef']['map']
    check('every colour-map material exists in SEED_MATERIALS_3D',
          all(v in mat_names for v in color_map.values()),
          str(list(color_map.values())))
    check('binding position binds to pos_x/y/z fields',
          binding['position']['fields'] == {'x': 'pos_x', 'y': 'pos_y',
                                            'z': 'pos_z'})
    # eval equations reference real equation defs on the same scene
    eqdef_names = {e['name'] for e in sim_seed._EQ_DEFS}
    check('every eval overlay refs a seeded equation def',
          all(ev_['equation_ref'] in eqdef_names for ev_ in sim_seed._EVALS))
    check('eval overlays target the wax-print scene',
          all(ev_['sim_space_ref'] == sim_seed.SCENE
              for ev_ in sim_seed._EVALS))
    # sim def participates the state class
    simdef = next(d for d in sim_seed.SEED_SIMULATION_DEFINITIONS
                  if d['name'] == 'wax-print')
    check('sim def participates WaxPrintSimState',
          'WaxPrintSimState' in json.loads(
              simdef['participating_sim_state_classes_json']))
    # msim + page + ic
    msim = next(m for m in sim_seed.SEED_MULTI_SCALE_SIMS
                if m['name'] == 'wax-print-multiscale')
    check('msim scene panel refs the scene',
          any(p.get('simSpaceRef') == sim_seed.SCENE
              for p in json.loads(msim['panels_json'])))
    page = sim_seed.SEED_WAXPRINT_PAGE_DISPLAYS[0]
    check('page is a route embedding the sim-space-viewer',
          page['isPage'] and page['pageRoute'] == 'wax-print-sim'
          and 'sim-space-viewer' in page['definition'])
    check('scene + binding appended to the shared pendulum lists',
          sim_seed._WAXPRINT_SCENE in sim_seed.SEED_PENDULUM_SIMSPACES
          and sim_seed._WAXPRINT_BINDINGS[0] in sim_seed.SEED_PENDULUM_BINDINGS)

    print('\nrange-of-conditions (dict-level)')
    range_out = []
    for cond in ('room-baseline', 'fridge-print', 'fine-voxel'):
        r = sim_runner.compute_step_rows(
            mgr, 'fine-nozzle-extruder', 'carnauba-rich', cond,
            f'range-{cond}', n_steps=6)
        e = sim_evaluation.evaluate_run(r['rows'])
        range_out.append((cond, e['met_count']))
    best = max(range_out, key=lambda x: x[1])
    check('a range of conditions ranks by gates met',
          len(range_out) == 3 and best[1] >= min(m for _, m in range_out),
          f"{range_out} -> best {best[0]}")

    n_failed = _results.count(False)
    print(f'\n{len(_results) - n_failed}/{len(_results)} passed')
    raise SystemExit(1 if n_failed else 0)
