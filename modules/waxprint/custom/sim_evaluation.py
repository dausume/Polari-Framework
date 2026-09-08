"""
@cross-cutting
@module waxprint.custom.sim_evaluation

The CONDITION GATES for a wax-print run — "do the various conditions get
met?" as data. Given a run's WaxPrintSimState rows + targets, each gate
reports met/not-met with the worst value, the threshold, and which build
steps fail (evidence, per knobs-and-suggestions). These mirror the
SimSpaceEvaluationEquation overlays on the 3D scene (the visual readout)
and back the /sim/evaluate + /sim/run-range endpoints.

Pure functions over row dicts OR row objects (attribute access via _get),
so the seed path, the API, and the selftest all share them.

@consumers
  - waxprint.sim_api (/sim/evaluate, /sim/run-range)
  - waxprint.sim_selftest
"""


def _get(row, key, default=0.0):
    if isinstance(row, dict):
        v = row.get(key, default)
    else:
        v = getattr(row, key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _all_steps(rows, key, predicate):
    """Steps whose field fails the predicate (predicate True = OK)."""
    failing = []
    for r in rows:
        if not predicate(_get(r, key)):
            failing.append(int(_get(r, 'step')))
    return failing


def _gate(name, description, met, worst_value, threshold, failing, knob):
    return {
        'condition': name,
        'description': description,
        'met': bool(met),
        'worst_value': worst_value,
        'threshold': threshold,
        'steps_failing': failing,
        'knob': knob if not met else None,
    }


def evaluate_run(rows, target_voxel_xy_mm=0.45, margin_tol_mm=0.03,
                 melt_floor=0.98, resolution_height_slack=1.5):
    """Evaluate every condition gate over a run's rows. Returns
    {conditions: [...], all_met, met_count, total}."""
    rows = sorted(rows, key=lambda r: _get(r, 'step'))
    if not rows:
        return {'conditions': [], 'all_met': False, 'met_count': 0,
                'total': 0, 'error': 'no rows for this run'}

    gates = []

    fail = _all_steps(rows, 'thermally_safe', lambda v: v >= 1.0)
    gates.append(_gate(
        'thermally-safe', 'Hotend/part stay within the wax + material '
        'safety window at every step.', not fail, 0.0 if fail else 1.0, 1.0,
        fail, 'lower hotend below the wax degradation ceiling / pick a '
        'higher-rated part material'))

    worst_melt = min(_get(r, 'melt_fraction') for r in rows)
    fail = _all_steps(rows, 'melt_fraction', lambda v: v >= melt_floor)
    gates.append(_gate(
        'fully-molten', f'Melt fraction >= {melt_floor:.2f} at every step.',
        not fail, worst_melt, melt_floor, fail,
        'slow the screw (more residence), lengthen the barrel, or raise '
        'the hotend within the safety ceiling'))

    fail = _all_steps(rows, 'printable', lambda v: v >= 1.0)
    gates.append(_gate(
        'printable', 'Melt is safe AND fully molten AND above melt margin.',
        not fail, 0.0 if fail else 1.0, 1.0, fail,
        'address the safety / melt findings above'))

    worst_vox = max(_get(r, 'voxel_xy_mm') for r in rows)
    fail = _all_steps(rows, 'voxel_xy_mm', lambda v: v <= target_voxel_xy_mm)
    gates.append(_gate(
        'voxel-meets-target',
        f'Voxel width <= {target_voxel_xy_mm:.3f} mm at every step.',
        not fail, worst_vox, target_voxel_xy_mm, fail,
        'finer nozzle, more cooling (fridge/fan), lower hotend, or slower '
        'print'))

    worst_margin = max(_get(r, 'margin_mm') for r in rows)
    fail = _all_steps(rows, 'margin_mm', lambda v: v <= margin_tol_mm)
    gates.append(_gate(
        'margin-within-tolerance',
        f'Repeatability margin <= {margin_tol_mm:.3f} mm at every step.',
        not fail, worst_margin, margin_tol_mm, fail,
        'tighter temperature control, or a condition less sensitive to the '
        '±3C band'))

    fail = [int(_get(r, 'step')) for r in rows
            if _get(r, 'movements_viable') < _get(r, 'movements_total')]
    worst_move = min(_get(r, 'movements_viable') for r in rows)
    total_move = _get(rows[0], 'movements_total')
    gates.append(_gate(
        'movements-viable',
        f'All {int(total_move)} movement patterns viable at every step.',
        not fail, worst_move, total_move, fail,
        'the movement limits (spread/blob/sag/stringing) — add cooling or '
        'slow the print'))

    # resolution must not collapse with height: top voxel within slack of
    # the bottom voxel.
    bottom = _get(rows[0], 'voxel_xy_mm')
    top = _get(rows[-1], 'voxel_xy_mm')
    holds = top <= bottom * resolution_height_slack + 1e-9
    gates.append(_gate(
        'resolution-holds-with-height',
        f'Top-of-part voxel within {resolution_height_slack:.1f}x the '
        f'first-layer voxel.', holds, top, bottom * resolution_height_slack,
        [] if holds else [int(_get(rows[-1], 'step'))],
        'active cooling to counter heat build-up, or slow the upper layers'))

    met_count = sum(1 for g in gates if g['met'])
    return {
        'conditions': gates,
        'all_met': met_count == len(gates),
        'met_count': met_count,
        'total': len(gates),
    }
