"""
@cross-cutting
@module simulations.run_scope
@tags @xc:bindings, @xc:render-shared

Run-scope resolution — THE shared predicate for "which rows belong to
the run the viewer is looking at."

A SimulationRun may be COUPLED to source runs in other simulations (its
`coupled_run_refs_json`, e.g. the wind-forced pendulum run pulling a
wind-field run). A scene rendering that run must also show its coupled
sources' rows, so the run scope is the run itself PLUS its coupled runs.

Historically compile_2d, compile_3d, and equation_evaluation each carried
a byte-identical inline run predicate (they MUST agree, or the readouts
evaluate over different rows than the renderer draws — see the eval
run-scoping fix). This module replaces the three copies with one import,
so agreement holds by construction.

@consumers
  - simSpace.compilers.compile_2d / compile_3d (snapshot row filter)
  - simulations.equation_evaluation (live readout row filter)
@see /OVERLAP_MAP.md
"""

import json
from typing import Optional, Set


def resolve_run_scope(manager, run_filter: Optional[str]) -> Optional[Set[str]]:
    """Expand a requested run name into the set of run names in scope:
    the run itself plus every run named in its `coupled_run_refs_json`
    (values of the {source_sim_name: source_run_name} dict).

    Returns None when no run is requested — callers treat that as
    "no filtering" (all rows pass)."""
    if not run_filter:
        return None
    scope = {run_filter}
    table = manager.objectTables.get('SimulationRun', {}) or {}
    for r in table.values():
        if getattr(r, 'name', '') != run_filter:
            continue
        raw = getattr(r, 'coupled_run_refs_json', '') or '{}'
        try:
            refs = json.loads(raw)
        except (ValueError, TypeError):
            refs = {}
        if isinstance(refs, dict):
            scope.update(
                v for v in refs.values() if isinstance(v, str) and v
            )
        break
    return scope


def row_in_run_scope(inst, scope: Optional[Set[str]]) -> bool:
    """Run-scope predicate. A row passes when no scope is set (no run
    requested), when it carries no `simulation_run_ref` attribute at all
    (freestanding / legacy data), or when its ref is one of the scoped
    runs (the requested run or a coupled source run)."""
    if scope is None:
        return True
    return (not hasattr(inst, 'simulation_run_ref')
            or getattr(inst, 'simulation_run_ref', '') in scope)
