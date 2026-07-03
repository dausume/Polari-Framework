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
) -> Dict[str, Any]:
    """Advance a stage's solution search by one batch and report status.

    `fixed_params` are merged into EVERY candidate's parameter overrides
    (candidates win on key conflicts — fixed params are the substance's
    identity, candidates are the searched process point). `attempt_tag`
    namespaces the attempt runs so per-substance searches stay separate
    and separately resumable.

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
        'error': None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(msg: str) -> Dict[str, Any]:
    return {
        'achieved': False, 'winner': None, 'exhausted': False,
        'totalCandidates': 0, 'attempted': 0, 'advancedThisCall': 0,
        'attempts': [], 'error': msg,
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
