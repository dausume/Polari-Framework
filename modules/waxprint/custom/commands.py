"""
@cross-cutting
@module waxprint.custom.commands

The wax-printer COMMAND layer — one dispatch surface the no-code
WaxPrintOperation node calls, and the extension point toward direct
printer control (Dustin 2026-07-17: "different commands need to be able
to be done via no-code ... simulate optimizing particular shapes and
turning that into direct control of the 3D printer").

Every command takes a flat inputs dict (row NAMES + scalars, exactly what
a no-code graph can supply) and returns a flat outputs dict (scalars the
graph can read back) — so a command composes in a solution graph and is
testable through the SolutionExecutionEngine. The same command vocabulary
is the seam that will later emit real machine instructions over the gRPC
hardware bridge (move-to / set-temp / extrude), so a simulated toolpath
and a printed one speak one language.

Commands (this phase — simulation/physics):
  melt        two-zone auger melt → exit temp, melt fraction, pressure,
              safety verdict.
  bead-voxel  the deposited bead at a build height → voxel + margin.
  movement    a movement pattern's viability at a build height.
  print-step  the full per-height print state (melt + voxel + movements)
              — this is what the no-code SIM STEP projects onto a
              WaxPrintSimState row.

Planned (printer control — stubs declared, not wired): move-to, set-temp,
extrude, retract → gRPC bridge machine instructions.

@consumers
  - waxprint.waxprint_operation (no-code node dispatch)
  - waxprint.sim_seed / sim_runner (the print-step command)
  - waxprint.selftest_commands
"""

from waxprint.custom import melt_analysis
from waxprint.custom import bead_analysis
from waxprint.custom import movement_analysis
from waxprint.custom import movement_patterns
from waxprint.custom.bead_analysis import _resolve

#: Print-parameter OVERRIDES any physics command accepts as scalar inputs
#: on top of the named condition row — so a no-code graph can MANIPULATE
#: any knob (sweep the hotend temp, shrink the nozzle, chill the ambient,
#: add a fan) without editing a row. `wind_mm_s` is shorthand for the fan
#: vector's x-component. Empty/absent = use the condition's own value.
OVERRIDE_INPUTS = [
    'auger_temp_c', 'hotend_temp_c', 'rpm', 'nozzle_diameter_mm',
    'ambient_temp_c', 'bed_temp_c', 'print_speed_mm_s', 'layer_height_mm',
    'convection_preset', 'fan_wind_vx_mm_s', 'fan_wind_vy_mm_s',
    'fan_wind_vz_mm_s', 'wind_mm_s']

_CONDITION_FIELDS = [
    'name', 'auger_temp_c', 'hotend_temp_c', 'rpm', 'nozzle_diameter_mm',
    'ambient_temp_c', 'bed_temp_c', 'convection_preset', 'fan_wind_vx_mm_s',
    'fan_wind_vy_mm_s', 'fan_wind_vz_mm_s', 'print_speed_mm_s',
    'layer_height_mm']

#: Declared command vocabulary — name → {inputs, outputs, purpose}. The
#: no-code node reads this for its schema; the planned printer-control
#: commands are listed with computable=False so the gap is honest. Every
#: `computable` physics command ALSO accepts OVERRIDE_INPUTS.
COMMAND_SPECS = {
    'melt': {
        'purpose': 'Two-zone auger melt + wax thermal-safety verdict.',
        'inputs': ['assembly', 'feedstock', 'condition'],
        'outputs': ['exit_temp_c', 'melt_fraction', 'nozzle_pressure_pa',
                    'exit_viscosity_pa_s', 'thermally_safe', 'printable'],
        'computable': True},
    'bead-voxel': {
        'purpose': 'Deposited bead → print voxel + repeatability margin.',
        'inputs': ['assembly', 'feedstock', 'condition', 'height_mm'],
        'outputs': ['voxel_xy_mm', 'voxel_z_mm', 'spread_mm', 'margin_mm',
                    't_solidify_s', 'warp_index', 'resolution_class_ord'],
        'computable': True},
    'movement': {
        'purpose': 'Viability of one movement pattern at a build height.',
        'inputs': ['assembly', 'feedstock', 'condition', 'pattern',
                   'height_mm'],
        'outputs': ['viable', 'verdict_ord', 'value'],
        'computable': True},
    'print-step': {
        'purpose': 'Full per-height print state (melt + voxel + movements) '
                   '— the no-code sim step.',
        'inputs': ['assembly', 'feedstock', 'condition', 'height_mm'],
        'outputs': ['exit_temp_c', 'melt_fraction', 'nozzle_pressure_pa',
                    'voxel_xy_mm', 'voxel_z_mm', 'spread_mm', 'margin_mm',
                    't_solidify_s', 'warp_index', 'thermally_safe',
                    'printable', 'movements_viable', 'movements_total',
                    'substrate_temp_c'],
        'computable': True},
    'optimize': {
        'purpose': 'Sweep temps/nozzle/environment for one assembly+wax → '
                   'the best print recipe (finest repeatable voxel, safe).',
        'inputs': ['assembly', 'feedstock'],
        'outputs': ['best_voxel_xy_mm', 'best_margin_mm', 'best_score',
                    'best_hotend_temp_c', 'best_nozzle_diameter_mm',
                    'finest_voxel_xy_mm', 'trials_scored'],
        'computable': True},
    'resolution-profile': {
        'purpose': 'Voxel resolution vs build height → finest/coarsest + '
                   'degradation with height.',
        'inputs': ['assembly', 'feedstock', 'condition'],
        'outputs': ['finest_voxel_xy_mm', 'coarsest_voxel_xy_mm',
                    'degradation_mm'],
        'computable': True},
    'evaluate-run': {
        'purpose': 'Evaluate the condition GATES for an existing sim run → '
                   'how many are met.',
        'inputs': ['run'],
        'outputs': ['met_count', 'total', 'all_met'],
        'computable': True},
    # --- planned: direct printer control (gRPC bridge) ---
    'move-to': {'purpose': 'Machine instruction: move to (x,y,z).',
                'inputs': ['x_mm', 'y_mm', 'z_mm', 'feedrate_mm_s'],
                'outputs': [], 'computable': False},
    'set-temp': {'purpose': 'Machine instruction: set a zone temperature.',
                 'inputs': ['zone', 'temp_c'], 'outputs': [],
                 'computable': False},
    'extrude': {'purpose': 'Machine instruction: extrude a length of wax.',
                'inputs': ['length_mm', 'feedrate_mm_s'], 'outputs': [],
                'computable': False},
}

_RES_ORD = {'ultra-fine': 3.0, 'fine': 2.0, 'standard': 1.0, 'coarse': 0.0}
_VERDICT_ORD = {'viable': 2.0, 'marginal': 1.0, 'fail': 0.0}


def _b(v):
    return 1.0 if v else 0.0


def _num(inputs, key):
    v = inputs.get(key, None)
    if v is None or v == '':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def condition_with_overrides(condition, inputs):
    """A synthetic PrintConditionDefinition-like object = the base
    condition with any OVERRIDE_INPUTS the graph supplied applied on top.
    This is what makes every knob no-code-manipulable without editing a
    row. Returns the original condition when nothing is overridden."""
    from waxprint.custom.bead_analysis import _f
    from types import SimpleNamespace
    fields = {k: getattr(condition, k, None) for k in _CONDITION_FIELDS}
    changed = False
    for k in OVERRIDE_INPUTS:
        if k == 'wind_mm_s':
            continue
        val = inputs.get(k, None)
        if val is None or val == '':
            continue
        if k == 'convection_preset':
            fields[k] = str(val)
        else:
            n = _num(inputs, k)
            if n is not None:
                fields[k] = n
        changed = True
    wind = _num(inputs, 'wind_mm_s')
    if wind is not None:
        fields['fan_wind_vx_mm_s'] = wind
        changed = True
    if not changed:
        return condition
    # keep any fields the base row had that we didn't enumerate
    base = {k: getattr(condition, k, None) for k in _CONDITION_FIELDS}
    base.update({k: v for k, v in fields.items() if v is not None})
    base['name'] = getattr(condition, 'name', 'override') or 'override'
    return SimpleNamespace(**base)


def run_command(manager, command, inputs):
    """Dispatch one command. `inputs` is a flat dict of row names +
    scalars (+ optional OVERRIDE_INPUTS). Returns {'ok': True,
    'outputs': {...}} or an error dict."""
    spec = COMMAND_SPECS.get(command)
    if spec is None:
        return {'ok': False, 'error': f'unknown command "{command}"',
                'known': sorted(COMMAND_SPECS)}
    if not spec['computable']:
        return {'ok': False, 'error': f'command "{command}" is a declared '
                f'printer-control instruction, not yet wired to the gRPC '
                f'bridge', 'planned': True}

    # commands that don't need the assembly/feedstock/condition triple
    if command == 'evaluate-run':
        return _cmd_evaluate_run(manager, inputs)
    if command == 'optimize':
        return _cmd_optimize(manager, inputs)

    a = inputs.get('assembly', '')
    f = inputs.get('feedstock', '')
    c = inputs.get('condition', '')
    height = float(inputs.get('height_mm', 0.0) or 0.0)
    rows = _resolve(manager, a, f, c)
    if 'error' in rows:
        return rows
    assembly, feedstock = rows['assembly'], rows['feedstock']
    # apply any scalar overrides so every knob is no-code-manipulable
    condition = condition_with_overrides(rows['condition'], inputs)

    if command == 'resolution-profile':
        from waxprint.custom import voxel_resolution
        from waxprint.custom.bead_analysis import _feed_props, _env, _f
        mr, _voxel, _e = bead_analysis.voxel_for_condition(
            manager, assembly, feedstock, condition)
        feed = _feed_props(feedstock)
        env = _env(manager, assembly, condition)
        prof = voxel_resolution.resolution_profile(
            mr['exit_temp_c'], mr['nozzle_diameter_mm'],
            _f(condition, 'layer_height_mm', 0.2), feed, env)
        return {'ok': True, 'outputs': {
            'finest_voxel_xy_mm': prof['finest_voxel_xy_mm'],
            'coarsest_voxel_xy_mm': prof['coarsest_voxel_xy_mm'],
            'degradation_mm': prof['degradation_mm']}}

    if command == 'melt':
        r = melt_analysis.evaluate_melt(manager, assembly, feedstock,
                                        condition)[0]
        return {'ok': True, 'outputs': {
            'exit_temp_c': r['exit_temp_c'], 'melt_fraction': r['melt_fraction'],
            'nozzle_pressure_pa': r['nozzle_pressure_pa'],
            'exit_viscosity_pa_s': r['exit_viscosity_pa_s'],
            'thermally_safe': _b(r['thermally_safe']),
            'printable': _b(r['printable'])}}

    if command == 'bead-voxel':
        _mr, voxel, _env = bead_analysis.voxel_for_condition(
            manager, assembly, feedstock, condition, height_mm=height)
        return {'ok': True, 'outputs': {
            'voxel_xy_mm': voxel['voxel_xy_mm'],
            'voxel_z_mm': voxel['voxel_z_mm'], 'spread_mm': voxel['spread_mm'],
            'margin_mm': voxel['margin_mm'],
            't_solidify_s': voxel['t_solidify_s'],
            'warp_index': voxel['warp_index'],
            'resolution_class_ord': _RES_ORD.get(
                voxel['resolution_class'], 0.0)}}

    if command == 'movement':
        pattern = inputs.get('pattern', 'perimeter')
        _mr, sim, moves = movement_analysis.movements_for_condition(
            manager, assembly, feedstock, condition, height_mm=height)
        one = next((p for p in moves['patterns'] if p['pattern'] == pattern),
                   None)
        if one is None:
            return {'ok': False, 'error': f'unknown pattern "{pattern}"',
                    'known': [p['pattern'] for p in moves['patterns']]}
        return {'ok': True, 'outputs': {
            'viable': _b(one['verdict'] == 'viable'),
            'verdict_ord': _VERDICT_ORD.get(one['verdict'], 0.0),
            'value': float(one.get('value') or 0.0)}}

    if command == 'print-step':
        mr, voxel, moves = movement_analysis.movements_for_condition(
            manager, assembly, feedstock, condition, height_mm=height)
        return {'ok': True, 'outputs': {
            'exit_temp_c': mr['exit_temp_c'], 'melt_fraction': mr['melt_fraction'],
            'nozzle_pressure_pa': mr['nozzle_pressure_pa'],
            'voxel_xy_mm': voxel['voxel_xy_mm'], 'voxel_z_mm': voxel['voxel_z_mm'],
            'spread_mm': voxel['spread_mm'], 'margin_mm': voxel['margin_mm'],
            't_solidify_s': voxel['t_solidify_s'],
            'warp_index': voxel['warp_index'],
            'thermally_safe': _b(mr['thermally_safe']),
            'printable': _b(mr['printable']),
            'movements_viable': float(moves['viable_count']),
            'movements_total': float(moves['total']),
            'substrate_temp_c': _substrate_at(feedstock, condition, height)}}

    return {'ok': False, 'error': f'command "{command}" not implemented'}


def _cmd_evaluate_run(manager, inputs):
    from waxprint.custom import sim_evaluation
    run = inputs.get('run', '')
    if not run:
        return {'ok': False, 'error': 'evaluate-run needs a "run" input'}
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        'WaxPrintSimState', {}) or {}
    rows = [o for o in table.values()
            if getattr(o, 'simulation_run_ref', None) == run]
    if not rows:
        return {'ok': False, 'error': f'no rows for run "{run}"'}
    tgt = {}
    for k in ('target_voxel_xy_mm', 'margin_tol_mm'):
        n = _num(inputs, k)
        if n is not None:
            tgt[k] = n
    ev = sim_evaluation.evaluate_run(rows, **tgt)
    return {'ok': True, 'outputs': {
        'met_count': float(ev['met_count']), 'total': float(ev['total']),
        'all_met': _b(ev['all_met'])}}


def _cmd_optimize(manager, inputs):
    from waxprint.custom import print_optimizer
    a = inputs.get('assembly', '')
    f = inputs.get('feedstock', '')
    if not (a and f):
        return {'ok': False, 'error': 'optimize needs assembly + feedstock'}
    rep = print_optimizer.optimize(manager, [a], [f])
    if not rep.get('ok'):
        return rep
    best = rep.get('best_recipe')
    if not best:
        return {'ok': True, 'outputs': {
            'best_voxel_xy_mm': 0.0, 'best_margin_mm': 0.0, 'best_score': 0.0,
            'best_hotend_temp_c': 0.0, 'best_nozzle_diameter_mm': 0.0,
            'finest_voxel_xy_mm': 0.0,
            'trials_scored': float(rep.get('trials_scored', 0))},
            'note': 'no safe/printable recipe in the swept space'}
    return {'ok': True, 'outputs': {
        'best_voxel_xy_mm': best['voxel_xy_mm'],
        'best_margin_mm': best['margin_mm'], 'best_score': best['score'],
        'best_hotend_temp_c': best['hotend_temp_c'],
        'best_nozzle_diameter_mm': best['nozzle_diameter_mm'],
        'finest_voxel_xy_mm': rep.get('finest_voxel_xy_mm') or
        best['voxel_xy_mm'],
        'trials_scored': float(rep.get('trials_scored', 0))}}


def _substrate_at(feedstock, condition, height):
    from waxprint.custom import voxel_resolution
    from waxprint.custom.bead_analysis import _f
    if height <= 0:
        return _f(condition, 'bed_temp_c', 22.0)
    return voxel_resolution.substrate_temp_at_height(
        height, _f(condition, 'bed_temp_c', 22.0),
        _f(condition, 'ambient_temp_c', 22.0),
        _f(feedstock, 'melt_point_c', 82.0))
