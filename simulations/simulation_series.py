"""
@cross-cutting
@module simulations.simulation_series
@tags @xc:bindings

Per-run timeseries extraction — the data feed for graphs-over-time on the
Multi-Scale Simulation Page.

Why this exists: the generic CRUDE list endpoint cannot filter by run or
step (it returns every access-scoped row of a class), and
/runs/{run}/current-state is single-step. A live graph needs "field F of
class C for run R over steps a..b" — this module walks the in-memory
objectTables exactly like on_get_current_state does, but across the step
range, and filters through the SHARED run scope (simulations.run_scope),
so a coupled run's series can read its source runs' classes (e.g. the
wind grid) under the same predicate the renderer and evals use.

`since_step` supports cheap incremental polling: a live graph fetches
only the steps it hasn't seen (since_step = last step it holds).
"""

from typing import Any, Dict, List, Optional

from simulations.run_scope import resolve_run_scope, row_in_run_scope


def build_series(
    manager,
    run_name: str,
    class_name: str,
    fields: List[str],
    step_from: Optional[int] = None,
    step_to: Optional[int] = None,
    since_step: Optional[int] = None,
) -> Dict[str, Any]:
    """Collect `{steps, times, fields}` for one class's rows within the
    run scope of `run_name` (the run + its coupled source runs).

    * fields — empty list means "every numeric field found on the rows"
      (identity fields excluded).
    * step_from/step_to — inclusive step-range clamp.
    * since_step — exclusive lower bound (rows with step > since_step);
      wins over step_from when both are set. For incremental polling.

    Rows are deduped by step (highest-seen wins, matching the runner's
    idempotent re-step semantics) and returned sorted by step.
    """
    scope = resolve_run_scope(manager, run_name)
    table = manager.objectTables.get(class_name, {}) or {}

    by_step: Dict[int, Any] = {}
    for inst in table.values():
        if not row_in_run_scope(inst, scope):
            continue
        raw = getattr(inst, 'step', None)
        try:
            step_val = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            step_val = None
        if step_val is None:
            continue
        if since_step is not None:
            if step_val <= since_step:
                continue
        elif step_from is not None and step_val < step_from:
            continue
        if step_to is not None and step_val > step_to:
            continue
        by_step[step_val] = inst

    steps = sorted(by_step.keys())
    field_names = list(fields) if fields else _numeric_fields(by_step, steps)

    times: List[Optional[float]] = []
    series: Dict[str, List[Any]] = {f: [] for f in field_names}
    for s in steps:
        inst = by_step[s]
        times.append(_as_float(getattr(inst, 'time', None)))
        for f in field_names:
            series[f].append(_as_float(getattr(inst, f, None)))

    return {
        'run': run_name,
        'class': class_name,
        'steps': steps,
        'times': times,
        'fields': series,
        'lastStep': steps[-1] if steps else None,
    }


# Identity/framework fields never useful as a graphed series.
_IDENTITY_FIELDS = {'name', 'simulation_run_ref', 'step', 'time'}


def _numeric_fields(by_step: Dict[int, Any], steps: List[int]) -> List[str]:
    """Discover graphable fields from the first row: public, non-identity,
    numeric-valued attributes (sorted for a stable order)."""
    if not steps:
        return []
    sample = by_step[steps[0]]
    skip = {'manager', 'branch', 'inTree', 'polariId'}
    out = []
    for k, v in vars(sample).items():
        if k.startswith('_') or k in skip or k in _IDENTITY_FIELDS:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        out.append(k)
    return sorted(out)


def _as_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
