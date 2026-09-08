"""
@cross-cutting
@module waxprint.custom.sim_runner

Populates WaxPrintSimState rows for a wax-print run. The "time" axis is
BUILD HEIGHT: step i samples the print at height z_i, so the SimSpace3D
scene shows a stacked column of bead voxels growing upward and coarsening
as accumulated heat warms the substrate — the visual "does the physics
make sense" check.

The wax-print sim is driven by the validated wp-1..3 Python engine (like
the msci engines run in Python, not the no-code step engine): a step is
one call to the melt → voxel → movements pipeline at that height. This
module produces rows as plain dicts (for SEEDING via the central loop)
and, for the live API, creates the persisted WaxPrintSimState +
SimulationRun objects so a fresh run renders immediately.

@consumers
  - waxprint.sim_seed (baseline run rows as dicts)
  - waxprint.sim_api (POST /sim/run, /sim/run-range)
  - waxprint.sim_selftest
"""

from waxprint.custom import melt_analysis
from waxprint.custom import movement_analysis
from waxprint.custom import voxel_resolution
from waxprint.custom.bead_analysis import _f, _feed_props

DEFAULT_N_STEPS = 12
DEFAULT_MAX_HEIGHT_MM = 40.0
DEFAULT_TARGET_VOXEL_XY_MM = 0.45
DEFAULT_MARGIN_TOL_MM = 0.03


def compute_step_rows(manager, assembly_name, feedstock_name, condition_name,
                      run_name, n_steps=DEFAULT_N_STEPS,
                      max_height_mm=DEFAULT_MAX_HEIGHT_MM,
                      target_voxel_xy_mm=DEFAULT_TARGET_VOXEL_XY_MM,
                      margin_tol_mm=DEFAULT_MARGIN_TOL_MM, pos_x_offset=0.0):
    """Compute one WaxPrintSimState row DICT per build-height step. Pure
    (no object creation) — used by the seed path and the API path alike.
    Returns {'ok': True, 'rows': [...], 'assembly'..} or an error dict."""
    from waxprint.custom.bead_analysis import _resolve
    rows_in = _resolve(manager, assembly_name, feedstock_name, condition_name)
    if 'error' in rows_in:
        return rows_in
    assembly, feedstock, condition = (
        rows_in['assembly'], rows_in['feedstock'], rows_in['condition'])

    feed = _feed_props(feedstock)
    ambient_c = _f(condition, 'ambient_temp_c', 22.0)
    bed_c = _f(condition, 'bed_temp_c', 22.0)
    melt_pt = feed['melt_point_c']

    rows = []
    n = max(1, int(n_steps))
    for i in range(n):
        height = (i / (n - 1)) * max_height_mm if n > 1 else 0.0
        melt_result, voxel, movements = \
            movement_analysis.movements_for_condition(
                manager, assembly, feedstock, condition, height_mm=height)
        substrate_c = voxel_resolution.substrate_temp_at_height(
            height, bed_c, ambient_c, melt_pt) if height > 0 else bed_c

        safe = 1.0 if melt_result['thermally_safe'] else 0.0
        printable = 1.0 if melt_result['printable'] else 0.0
        resolution_ok = 1.0 if voxel['voxel_xy_mm'] <= target_voxel_xy_mm \
            and voxel['margin_mm'] <= margin_tol_mm else 0.0
        if safe < 1 or printable < 1:
            render_state = 0.0
        elif resolution_ok >= 1:
            render_state = 2.0
        else:
            render_state = 1.0

        rows.append({
            'name': f'{run_name}-wax-print-{i}',
            'simulation_run_ref': run_name,
            'step': i,
            'time': height,
            'assembly_ref': assembly_name,
            'feedstock_ref': feedstock_name,
            'condition_ref': condition_name,
            'height_mm': height,
            'substrate_temp_c': substrate_c,
            'exit_temp_c': melt_result['exit_temp_c'],
            'melt_fraction': melt_result['melt_fraction'],
            'nozzle_pressure_pa': melt_result['nozzle_pressure_pa'],
            'voxel_xy_mm': voxel['voxel_xy_mm'],
            'voxel_z_mm': voxel['voxel_z_mm'],
            'spread_mm': voxel['spread_mm'],
            'margin_mm': voxel['margin_mm'],
            't_solidify_s': voxel['t_solidify_s'],
            'warp_index': voxel['warp_index'],
            'thermally_safe': safe,
            'printable': printable,
            'movements_viable': float(movements['viable_count']),
            'movements_total': float(movements['total']),
            'resolution_ok': resolution_ok,
            'render_state': render_state,
            # column grows UP (Y in math coords); offset X per run so
            # multiple seeded runs render side by side on a plain page.
            'pos_x': pos_x_offset,
            'pos_y': height,
            'pos_z': 0.0,
        })

    return {
        'ok': True,
        'assembly': assembly_name,
        'feedstock': feedstock_name,
        'condition': condition_name,
        'run_name': run_name,
        'rows': rows,
        'targets': {'target_voxel_xy_mm': target_voxel_xy_mm,
                    'margin_tol_mm': margin_tol_mm,
                    'max_height_mm': max_height_mm, 'n_steps': n},
    }


def _unique_run_name(manager, base):
    """Avoid clobbering an existing run's rows: suffix the name until it
    is unused (no reliance on a delete API)."""
    existing = (getattr(manager, 'objectTables', {}) or {}).get(
        'SimulationRun', {}) or {}
    names = {getattr(o, 'name', None) for o in existing.values()}
    if base not in names:
        return base
    i = 2
    while f'{base}-{i}' in names:
        i += 1
    return f'{base}-{i}'


def persist_run(manager, assembly_name, feedstock_name, condition_name,
                run_name=None, **kwargs):
    """Compute + CREATE the WaxPrintSimState rows and a SimulationRun so a
    fresh run renders in the current session. Returns the compute result
    plus the created run name. Requires the SimState + SimulationRun
    classes (imported lazily so pure/selftest paths don't need them)."""
    from waxprint.sim_state_basis import WaxPrintSimState
    base = run_name or f'wax-print-{condition_name}'
    run_name = _unique_run_name(manager, base)
    out = compute_step_rows(manager, assembly_name, feedstock_name,
                            condition_name, run_name, **kwargs)
    if not out.get('ok'):
        return out

    for row in out['rows']:
        WaxPrintSimState(**row, manager=manager)

    # Best-effort SimulationRun row so the run appears in the run list.
    # Resolve the class from an existing instance to avoid a brittle
    # import; rendering does not require it (compile reads the state rows).
    run_cls = _class_from_table(manager, 'SimulationRun')
    if run_cls is not None:
        try:
            run_cls(name=run_name, simulation_ref='wax-print',
                    status='completed', total_steps=len(out['rows']),
                    recorded_steps=len(out['rows']),
                    last_recorded_step=len(out['rows']) - 1,
                    label=f'{feedstock_name} / {condition_name}',
                    manager=manager)
        except Exception:
            pass
    out['run_name'] = run_name
    out['persisted'] = True
    return out


def _class_from_table(manager, class_name):
    """The class object of an already-registered row, or None."""
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) \
        or {}
    for obj in table.values():
        return obj.__class__
    return None
