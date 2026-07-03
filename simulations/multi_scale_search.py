"""
@cross-cutting
@module simulations.multi_scale_search
@tags @xc:bindings

Solution search for first-principles stages — attempt MULTIPLE candidate
solutions per simulation to reach ONE valid solution.

A candidate is an ordinary SimulationRun of the stage's simulation whose
`parameter_overrides_json` carries that candidate's parameter point
(e.g. one temperature/pressure pair). The orchestrator:

  1. generates the candidate set from the stage's `search.candidates`
     config (grid cartesian product or an explicit list; a gradient-
     descent `solver` kind is the reserved next step — same orchestrator,
     different candidate generator),
  2. creates/continues attempt runs (named `<msim>-<stage>-attempt-<k>`),
  3. steps each candidate to its target step count (batchSize attempts
     per call, so one HTTP request stays bounded),
  4. gate-evaluates every attempted candidate (the SAME no-code gate the
     stage declares),
  5. reports: ACHIEVED with the winning run + derived values (first
     candidate whose gate passes), or in-progress, or EXHAUSTED with the
     full attempts record.

The attempts record IS the downstream "disabled with reason and data":
when no candidate achieves the condition, the searched ranges and every
attempt's plain-language reason travel with the disabled choice.

STATELESS + RESUMABLE by design: attempts are ordinary named runs, so
progress is always derivable from the DB — repeated calls continue where
the last left off; nothing extra to persist or clean up.

@consumers
  - simulations.simulation_api (stage search endpoint)
  - frontend multi-scale page (stage stepper's "Search for a solution")
@see /OVERLAP_MAP.md
"""

import math
import re
from typing import Any, Dict, List, Optional

from simulations.attempt_task import build_attempt_base, execute_attempt_pure
from simulations.execution_backend import ExecutionBackendError, parallel_map
from simulations.multi_scale_stages import evaluate_stage_gate
from simulations.simulation_runner import _parse_json

# Hard ceilings — a mis-configured grid should fail loudly, not grind.
MAX_CANDIDATES = 500
DEFAULT_BATCH_SIZE = 4


def generate_candidates(search_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The ordered candidate parameter sets for a stage search.

    kinds:
      * grid — {"parameters": {name: {"from", "to", "steps"}}} → cartesian
        product, each axis linearly spaced (steps=1 → the midpoint).
      * list — {"values": [{...}, ...]} explicit candidate dicts.
      * solver — reserved (gradient-descent generation; Milestone E).
    """
    cand_cfg = (search_cfg or {}).get('candidates') or {}
    kind = cand_cfg.get('kind') or 'grid'

    if kind == 'list':
        values = cand_cfg.get('values') or []
        out = [dict(v) for v in values if isinstance(v, dict)]
        return out[:MAX_CANDIDATES]

    if kind == 'grid':
        params = cand_cfg.get('parameters') or {}
        axes: List[List[tuple]] = []
        for name in sorted(params.keys()):
            spec = params[name] or {}
            try:
                lo = float(spec.get('from', 0.0))
                hi = float(spec.get('to', lo))
                steps = max(1, int(spec.get('steps', 1)))
            except (TypeError, ValueError):
                continue
            if steps == 1:
                points = [(lo + hi) / 2.0]
            else:
                span = (hi - lo) / (steps - 1)
                points = [lo + span * i for i in range(steps)]
            axes.append([(name, round(p, 10)) for p in points])
        combos: List[Dict[str, Any]] = [{}]
        for axis in axes:
            combos = [dict(c, **{k: v}) for c in combos for (k, v) in axis]
            if len(combos) > MAX_CANDIDATES:
                return combos[:MAX_CANDIDATES]
        return combos if axes else []

    raise ValueError(f"unknown candidate kind {kind!r} "
                     f"(grid | list; 'solver' is not implemented yet)")


def sanitize_tag(tag: str) -> str:
    """Attempt tags become run-name segments: lowercase [a-z0-9-] only."""
    return re.sub(r'[^a-z0-9-]', '', str(tag or '').lower())


def attempt_run_name(msim_name: str, stage_key: str, index: int,
                     tag: str = '') -> str:
    """Attempt runs are ordinary named runs. A TAG (e.g. the substance —
    'wax', 'water-ice') keeps different fixedParams searches in separate,
    independently-resumable attempt sets."""
    tag = sanitize_tag(tag)
    if tag:
        return f'{msim_name}-{stage_key}-{tag}-attempt-{index}'
    return f'{msim_name}-{stage_key}-attempt-{index}'


def run_stage_search(
    manager,
    msim_name: str,
    stage: Dict[str, Any],
    batch_size: Optional[int] = None,
    fixed_params: Optional[Dict[str, Any]] = None,
    attempt_tag: str = '',
    execution_backend: Optional[str] = None,
    max_workers: Optional[int] = None,
    dask_scheduler: Optional[str] = None,
) -> Dict[str, Any]:
    """Advance a stage's solution search by one batch and report status.

    `dask_scheduler` (dask backend only; default POLARI_DASK_SCHEDULER
    env): address of an existing distributed scheduler — the cross-
    instance path (workers on ANY Polari joined to that scheduler
    execute this search's attempts; the report's `workerSplit` shows
    where tasks actually ran).

    `fixed_params` are merged into EVERY candidate's parameter overrides
    (candidates win on key conflicts — fixed params are the substance's
    identity, candidates are the searched process point). `attempt_tag`
    namespaces the attempt runs so per-substance searches stay separate
    and separately resumable.

    `execution_backend` ('serial' | 'processes' | 'dask'): how FRESH
    candidates in this batch execute. None = the stage's
    search.executionBackend, else serial. Parallel backends run attempts
    as PURE tasks (simulations.attempt_task) — no shared manager — and
    materialize the results (attempt run + final row per class) back
    in-process, so gates/series/scrubber see ordinary (sparse: final
    step only) runs. Coupled simulations fall back to serial with a
    warning — pure attempts cannot do live cross-run reads.

    Returns:
        {
          'achieved': bool,
          'winner': {run, candidate, derivedValues} | None,
          'exhausted': bool,
          'totalCandidates': int,
          'attempted': int,               # runs stepped to target so far
          'advancedThisCall': int,
          'attempts': [ {run, candidate, stepped, complete, reason,
                         error} ... ],    # ALL candidates, in order
          'backend': str,                 # what actually executed
          'warnings': [str, ...],
          'parallelHint': str | None,     # knob-pointing suggestion
          'error': str | None,
        }
    """
    search_cfg = stage.get('search') or {}
    sim_ref = stage.get('simulationRef') or ''
    stage_key = stage.get('key') or ''
    try:
        candidates = generate_candidates(search_cfg)
    except ValueError as exc:
        return _err(str(exc))
    if not candidates:
        return _err('search.candidates produced no candidate parameter sets')
    if not sim_ref:
        return _err('stage has no simulationRef to search over')

    sim_def = _find_by_name(manager, 'SimulationDefinition', sim_ref)
    if sim_def is None:
        return _err(f"SimulationDefinition '{sim_ref}' not found")
    target_steps = _target_steps(search_cfg, sim_def)
    batch = max(1, int(batch_size or search_cfg.get('batchSize')
                       or DEFAULT_BATCH_SIZE))

    from simulations.simulation_runner import run_step

    fixed = fixed_params if isinstance(fixed_params, dict) else {}
    report_warnings: List[str] = []
    backend = str(execution_backend or search_cfg.get('executionBackend')
                  or 'serial').strip().lower()
    if backend != 'serial' and _sim_is_coupled(manager, sim_ref, search_cfg):
        report_warnings.append(
            f"Simulation '{sim_ref}' participates in couplings — parallel "
            f"attempts need a pure (uncoupled) simulation, so this search "
            f"runs serially."
        )
        backend = 'serial'

    if backend != 'serial':
        return _run_search_parallel(
            manager, msim_name, stage, sim_def, candidates, target_steps,
            batch, fixed, attempt_tag, backend, max_workers, report_warnings,
            dask_scheduler,
        )

    attempts: List[Dict[str, Any]] = []
    winner = None
    advanced = 0
    attempted = 0
    for idx, candidate in enumerate(candidates):
        name = attempt_run_name(msim_name, stage_key, idx, attempt_tag)
        run = _find_by_name(manager, 'SimulationRun', name)
        entry: Dict[str, Any] = {
            'run': name, 'candidate': candidate, 'stepped': 0,
            'complete': False, 'reason': '', 'error': None,
        }
        attempts.append(entry)

        # Advance this candidate only while the batch allows and no
        # winner exists yet (first-valid short-circuits the rest). One
        # batch slot = one candidate worked on this call (created and/or
        # stepped to its target).
        if winner is None and advanced < batch:
            did_work = False
            if run is None:
                run = _create_attempt_run(manager, name, sim_ref,
                                          {**fixed, **candidate},
                                          stage, msim_name)
                if run is None:
                    entry['error'] = 'failed to create attempt run'
                    advanced += 1
                    continue
                did_work = True
            # Step until the run actually REACHES the target (the step-0
            # initial-conditions write doesn't advance last_recorded_step,
            # so a fixed-count loop under-steps a fresh run by one).
            if int(getattr(run, 'last_recorded_step', 0) or 0) < target_steps:
                did_work = True
                guard = 0
                while (int(getattr(run, 'last_recorded_step', 0) or 0)
                       < target_steps and guard <= target_steps + 2):
                    guard += 1
                    result = run_step(manager, run)
                    if not result.get('success'):
                        entry['error'] = result.get('error')
                        break
            if did_work:
                advanced += 1

        if run is None:
            entry['reason'] = 'not attempted yet'
            continue
        entry['stepped'] = int(getattr(run, 'last_recorded_step', 0) or 0)
        if entry['stepped'] >= target_steps:
            attempted += 1
            verdict = evaluate_stage_gate(manager, stage, run)
            entry['complete'] = bool(verdict.get('complete'))
            entry['reason'] = verdict.get('reason') or ''
            entry['error'] = entry['error'] or verdict.get('error')
            if entry['complete'] and winner is None:
                winner = {
                    'run': name,
                    'candidate': candidate,
                    'derivedValues': verdict.get('derivedValues'),
                }
        elif not entry['reason']:
            entry['reason'] = (f"in progress ({entry['stepped']}/"
                               f"{target_steps} steps)")

    exhausted = winner is None and attempted >= len(candidates)
    return {
        'achieved': winner is not None,
        'winner': winner,
        'exhausted': exhausted,
        'totalCandidates': len(candidates),
        'attempted': attempted,
        'advancedThisCall': advanced,
        'attempts': attempts,
        'backend': 'serial',
        'warnings': report_warnings,
        'parallelHint': _parallel_hint(
            manager, sim_ref, target_steps,
            remaining=len(candidates) - attempted,
            winner=winner,
        ),
        'workerSplit': None,
        'error': None,
    }


# ---------------------------------------------------------------------------
# Parallel execution path (pure attempts in workers, materialized back)
# ---------------------------------------------------------------------------


def _run_search_parallel(
    manager, msim_name, stage, sim_def, candidates, target_steps, batch,
    fixed, attempt_tag, backend, max_workers, report_warnings,
    dask_scheduler=None,
) -> Dict[str, Any]:
    """Same report shape + winner semantics as the serial loop, but FRESH
    candidates in this batch execute as pure tasks on the chosen backend.
    Existing runs are reconciled/gated exactly as in serial (under-stepped
    ones are finished serially — they are partial in-process investments).
    Each pure result is materialized as an ordinary attempt run holding
    its FINAL row per class (that sparseness is the point of an attempt);
    a pure winner is confirmed in-process before it counts."""
    from simulations.simulation_runner import (
        run_step, _bump_run_counters, _create_row, _row_name_for,
    )
    sim_ref = stage.get('simulationRef') or ''
    stage_key = stage.get('key') or ''
    dt = float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01)

    attempts: List[Dict[str, Any]] = []
    runs_by_idx: Dict[int, Any] = {}
    winner = None
    advanced = 0
    attempted = 0
    understepped: List[int] = []
    fresh: List[int] = []

    # Pass 1 — reconcile what already exists (no stepping budget spent).
    for idx, candidate in enumerate(candidates):
        name = attempt_run_name(msim_name, stage_key, idx, attempt_tag)
        run = _find_by_name(manager, 'SimulationRun', name)
        runs_by_idx[idx] = run
        entry: Dict[str, Any] = {
            'run': name, 'candidate': candidate, 'stepped': 0,
            'complete': False, 'reason': '', 'error': None,
        }
        attempts.append(entry)
        if run is None:
            entry['reason'] = 'not attempted yet'
            fresh.append(idx)
            continue
        entry['stepped'] = int(getattr(run, 'last_recorded_step', 0) or 0)
        if entry['stepped'] >= target_steps:
            attempted += 1
            verdict = evaluate_stage_gate(manager, stage, run)
            entry['complete'] = bool(verdict.get('complete'))
            entry['reason'] = verdict.get('reason') or ''
            entry['error'] = verdict.get('error')
            if entry['complete'] and winner is None:
                winner = {'run': name, 'candidate': candidate,
                          'derivedValues': verdict.get('derivedValues')}
        else:
            entry['reason'] = (f"in progress ({entry['stepped']}/"
                               f"{target_steps} steps)")
            understepped.append(idx)

    # Pass 2 — finish under-stepped existing runs serially (budget-bound).
    for idx in understepped:
        if winner is not None or advanced >= batch:
            break
        run = runs_by_idx[idx]
        entry = attempts[idx]
        advanced += 1
        guard = 0
        while (int(getattr(run, 'last_recorded_step', 0) or 0) < target_steps
               and guard <= target_steps + 2):
            guard += 1
            result = run_step(manager, run)
            if not result.get('success'):
                entry['error'] = result.get('error')
                break
        entry['stepped'] = int(getattr(run, 'last_recorded_step', 0) or 0)
        if entry['stepped'] >= target_steps:
            attempted += 1
            verdict = evaluate_stage_gate(manager, stage, run)
            entry['complete'] = bool(verdict.get('complete'))
            entry['reason'] = verdict.get('reason') or ''
            if entry['complete'] and winner is None:
                winner = {'run': entry['run'], 'candidate': entry['candidate'],
                          'derivedValues': verdict.get('derivedValues')}

    # Pass 3 — fresh candidates, PURE + PARALLEL, within remaining budget.
    attribution: Dict[str, Any] = {}
    take = [] if winner is not None else fresh[:max(0, batch - advanced)]
    if take:
        base = build_attempt_base(manager, stage, sim_def)
        specs = []
        for idx in take:
            merged = dict(base['baseParams'])
            merged.update(fixed)
            merged.update(candidates[idx])
            specs.append({**base, 'params': merged})
        try:
            results = parallel_map(execute_attempt_pure, specs,
                                   backend=backend, max_workers=max_workers,
                                   scheduler_address=dask_scheduler,
                                   attribution_out=attribution)
        except ExecutionBackendError as exc:
            report = _err(str(exc))
            report['attempts'] = attempts
            report['totalCandidates'] = len(candidates)
            report['attempted'] = attempted
            report['backend'] = backend
            report['warnings'] = report_warnings
            return report

        for idx, res in zip(take, results):
            entry = attempts[idx]
            advanced += 1
            run = _create_attempt_run(
                manager, entry['run'], sim_ref,
                {**fixed, **candidates[idx]}, stage, msim_name)
            if run is None:
                entry['error'] = 'failed to create attempt run'
                continue
            if res.get('error'):
                entry['error'] = res['error']
                entry['reason'] = 'attempt failed'
                continue
            # Materialize the pure result: the FINAL row per class, named
            # and tagged like any runner-written row.
            for cls_name, fields in (res.get('rowsByClass') or {}).items():
                row = dict(fields)
                row['name'] = _row_name_for(cls_name, run, target_steps)
                row['simulation_run_ref'] = entry['run']
                row['step'] = target_steps
                row['time'] = round(target_steps * dt, 6)
                _create_row(manager, cls_name, row)
            _bump_run_counters(manager, run, target_steps)
            entry['stepped'] = target_steps
            attempted += 1
            entry['complete'] = bool(res.get('gateComplete'))
            entry['reason'] = res.get('gateReason') or ''
            if entry['complete'] and winner is None:
                # Belt and braces: a pure winner must also pass the
                # in-process gate over its materialized rows.
                verdict = evaluate_stage_gate(manager, stage, run)
                if verdict.get('complete'):
                    winner = {'run': entry['run'],
                              'candidate': candidates[idx],
                              'derivedValues': verdict.get('derivedValues')}
                else:
                    entry['complete'] = False
                    entry['reason'] = (verdict.get('reason')
                                       or entry['reason'])
                    report_warnings.append(
                        f"Pure attempt '{entry['run']}' passed its gate but "
                        f"the in-process check disagreed — trusting the "
                        f"in-process verdict."
                    )

    exhausted = winner is None and attempted >= len(candidates)
    return {
        'achieved': winner is not None,
        'winner': winner,
        'exhausted': exhausted,
        'totalCandidates': len(candidates),
        'attempted': attempted,
        'advancedThisCall': advanced,
        'attempts': attempts,
        'backend': backend,
        'warnings': report_warnings,
        'parallelHint': None,
        # Where tasks actually executed (dask only) — e.g. across two
        # Polari instances' workers: {'a-worker': 6, 'b-worker': 4}.
        'workerSplit': attribution.get('workerSplit') or None,
        'error': None,
    }


def _sim_is_coupled(manager, sim_ref: str, search_cfg: Dict[str, Any]) -> bool:
    """True when the sim participates in any enabled coupling (either
    side) or the search itself declares coupled source runs — pure
    attempts cannot do live cross-run reads."""
    if (search_cfg or {}).get('coupledRunRefs'):
        return True
    table = manager.objectTables.get('SimulationCouplingDefinition', {}) or {}
    for c in table.values():
        if not getattr(c, 'enabled', True):
            continue
        if sim_ref in (getattr(c, 'source_simulation_ref', ''),
                       getattr(c, 'target_simulation_ref', '')):
            return True
    return False


def _parallel_hint(manager, sim_ref: str, target_steps: int,
                   remaining: int, winner) -> Optional[str]:
    """Knobs-and-suggestions: when the measured step cost says the rest
    of a serial search will take a while, point at the executionBackend
    knob with the evidence. Never auto-applies."""
    if winner is not None or remaining <= 0:
        return None
    profile = _find_by_name(manager, 'StepCostProfile',
                            f'{sim_ref}-cost-profile')
    if profile is None:
        return None
    try:
        avg = float(getattr(profile, 'avg_step_seconds', 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    est = avg * target_steps * remaining
    if est <= 10.0:
        return None
    import os as _os
    scheduler = _os.environ.get('POLARI_DASK_SCHEDULER') or ''
    tail = (f"set executionBackend to 'dask' to spread them across the "
            f"connected instances' workers (scheduler {scheduler}), or "
            f"'processes' to parallelize on this instance alone."
            if scheduler else
            "set executionBackend to 'processes' (or 'dask') on this "
            "search to try several at once.")
    return (f"The remaining {remaining} candidates would take roughly "
            f"{est:.0f}s at this simulation's measured ~{avg * 1000:.0f} ms "
            f"per step. These attempts are independent — {tail}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(msg: str) -> Dict[str, Any]:
    return {
        'achieved': False, 'winner': None, 'exhausted': False,
        'totalCandidates': 0, 'attempted': 0, 'advancedThisCall': 0,
        'attempts': [], 'backend': 'serial', 'warnings': [],
        'parallelHint': None, 'workerSplit': None, 'error': msg,
    }


def _find_by_name(manager, class_name: str, name: str):
    if not name:
        return None
    for inst in (manager.objectTables.get(class_name, {}) or {}).values():
        if getattr(inst, 'name', '') == name:
            return inst
    return None


def _target_steps(search_cfg: Dict[str, Any], sim_def) -> int:
    """Steps each attempt runs before its gate is judged — explicit
    stepsPerAttempt, else the sim's full duration at its dt."""
    try:
        explicit = int(search_cfg.get('stepsPerAttempt') or 0)
    except (TypeError, ValueError):
        explicit = 0
    if explicit > 0:
        return explicit
    try:
        duration = float(getattr(sim_def, 'duration_seconds', 0.0) or 0.0)
        dt = float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01)
        return max(1, int(math.ceil(duration / dt)))
    except (TypeError, ValueError, ZeroDivisionError):
        return 1


def _create_attempt_run(manager, name: str, sim_ref: str,
                        candidate: Dict[str, Any], stage: Dict[str, Any],
                        msim_name: str):
    """One candidate = one ordinary SimulationRun carrying the candidate's
    parameter point as per-run overrides. Coupled sources pass through
    when the stage's search declares them (rare for a first-principles
    space, but the channel exists)."""
    import json as _json
    from simulations.simulation_run import SimulationRun
    search_cfg = stage.get('search') or {}
    coupled = search_cfg.get('coupledRunRefs') or {}
    try:
        return SimulationRun(
            name=name,
            simulation_ref=sim_ref,
            status='pending',
            label=(f'{msim_name} / {stage.get("key", "")} — solution '
                   f'attempt: {candidate}'),
            parameter_overrides_json=_json.dumps(candidate),
            coupled_run_refs_json=_json.dumps(
                coupled if isinstance(coupled, dict) else {}),
            manager=manager,
        )
    except Exception:
        return None
