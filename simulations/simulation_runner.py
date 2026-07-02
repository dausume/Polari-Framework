"""
@cross-cutting
@module simulations.simulation_runner
@tags @xc:bindings

SimulationRunner — orchestrates per-timestep execution of a
SimulationRun. Pure orchestration: no state-graph walking, no trace
bookkeeping, no SymPy. Delegates each step solution to the existing
`SolutionExecutionEngine`, then projects the resulting ExecutionTrace's
final context onto a new `*SimState` row.

Model: a SimulationDefinition lists `participating_sim_state_classes_json`
(the classes whose rows it advances). For each class, the runner pulls
every SimulationExecutionSolution row where `simulation_definition_ref`
+ `sim_state_class_name` match and `enabled` is true, sorted by
`order_index`. Cross-class dependencies live on those rows' union of
`depends_on_json`, which the runner topo-sorts before executing.

Initial-conditions hybrid model (step=0):
  * each *SimState class's `default_initial_field_values` (class attr)
    is the baseline
  * the SimulationDefinition's `initial_conditions_overrides_json` is
    a dict keyed BY CLASS NAME of per-class field overrides (sim wins)

The single public entry point is `run_step()` — advance the run by
exactly one timestep. The proposal layers (`/run` background loop,
STOMP streaming) wrap this same primitive; if `run_step` works for
the single-step "is this coherent?" check, the multi-step loop works
by induction.

Failure model: a single solution's failure aborts the step. Partial
rows are NOT persisted — either every class's row lands for the
target step or none of them do. The caller gets a structured error
listing which solution failed and why; the SimulationRun.status is
left untouched (the orchestration layer above decides whether to mark
it failed).

@consumers
  - simSpace.sim_space_api (/step endpoint)
  - (future) background /run loop with STOMP streaming
@see /OVERLAP_MAP.md
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine
from polariNoCode.stepping import StepConfig
from simulations.simulation_coupling import apply_couplings


def run_step(
    manager,
    run,
    target_step: Optional[int] = None,
    _pull_chain: Optional[frozenset] = None,
) -> Dict[str, Any]:
    """Advance a SimulationRun by exactly one timestep.

    `target_step` defaults to `run.last_recorded_step + 1` (or 0 if no
    rows have been written yet). Passing it explicitly lets a caller
    re-run a step idempotently (the runner will delete existing rows
    for that step before re-emitting).

    `_pull_chain` is internal: the set of run names currently being
    advanced up-stack when this call is a coupling's lazy pull (see
    simulations.simulation_coupling). It guards against coupling cycles;
    external callers leave it unset.

    Returns:
        {
          'success': bool,
          'step': int,
          'time': float,
          'rows_by_class': { '<SimStateClass>': {<fields>}, ... },
          'solution_traces': [ { solution, status, trace_id, error? }, ... ],
          'warnings': [str, ...],
          'error': str | None,    # set when success=False
        }
    """
    warnings: List[str] = []
    try:
        # 1. Find the SimulationDefinition the run belongs to.
        sim_def = _find_simulation_definition(manager, run)
        if sim_def is None:
            return _err('SimulationRun has no resolvable SimulationDefinition.', warnings)

        # 2. Determine target_step and the corresponding time value.
        if target_step is None:
            last = int(getattr(run, 'last_recorded_step', 0) or 0)
            target_step = last + 1 if _has_any_rows_for_run(manager, sim_def, run) else 0
        # Per-run dt overrides the sim def's value when > 0 — lets the
        # same sim def be replayed at different resolutions per-run.
        run_dt = float(getattr(run, 'time_step_seconds', 0.0) or 0.0)
        sim_dt = float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01)
        dt = run_dt if run_dt > 0 else sim_dt
        time_value = target_step * dt

        # 3. Resolve participating *SimState classes from the sim def's
        #    explicit roster.
        participating_classes = _participating_classes(sim_def)
        if not participating_classes:
            return _err(
                'SimulationDefinition has no participating_sim_state_classes_json.',
                warnings,
            )

        # 4. For each class, gather enabled SimulationExecutionSolution
        #    rows targeting it. Empty groups are allowed at step=0 (the
        #    initial-conditions write doesn't need a solution) but
        #    warned about at step>=1.
        solutions_by_class = _solutions_by_class(manager, sim_def, participating_classes)

        # 5. Topo-sort participating classes by union of solutions' deps.
        ordered_classes = _topo_sort_classes(participating_classes, solutions_by_class)
        if ordered_classes is None:
            return _err('Cycle in cross-class dependencies.', warnings)

        # 6. Pre-build common context pieces that don't change per solution.
        params = _parse_json(getattr(sim_def, 'parameters_json', '{}') or '{}', {})
        sim_overrides = _parse_json(
            getattr(sim_def, 'initial_conditions_overrides_json', '{}') or '{}', {}
        )
        if not isinstance(sim_overrides, dict):
            sim_overrides = {}
        run_overrides = _parse_json(
            getattr(run, 'initial_conditions_overrides_json', '{}') or '{}', {}
        )
        if not isinstance(run_overrides, dict):
            run_overrides = {}

        # 7. Execute. Collect rows in memory first; only persist after
        #    all classes succeed (atomic-per-step).
        engine = SolutionExecutionEngine(manager=manager)
        step_cfg = StepConfig(mode='step', record_context=True)
        deps_outputs: Dict[str, Dict[str, Any]] = {}
        rows_to_persist: List[Tuple[str, Dict[str, Any]]] = []
        solution_traces: List[Dict[str, Any]] = []

        # Convention: step=0 is the initial-conditions snapshot. We
        # write it WITHOUT running the engine — there's no "previous
        # step" to integrate from at t=0. The engine kicks in at
        # step=1 (the first advance).
        if target_step == 0:
            # Gather merged initial conditions per class up front so the
            # validator (if any) can inspect them before we persist
            # anything. Validation gates step 0 — a failed verdict aborts
            # the step with the validator's reason.
            initial_by_class: Dict[str, Dict[str, Any]] = {}
            for cls_name in ordered_classes:
                initial_by_class[cls_name] = _initial_field_values(
                    manager, cls_name, sim_overrides, run_overrides,
                )

            verdict = validate_initial_conditions(manager, sim_def, initial_by_class)
            if verdict['hasValidator']:
                if verdict['error']:
                    return _err(
                        f"Initial-conditions validator failed: {verdict['error']}",
                        warnings,
                    )
                if not verdict['valid']:
                    return _err(
                        f"Initial conditions invalid: {verdict['reason']}",
                        warnings,
                    )
                # If the validator returned repairedValues, fold them in
                # so the persisted step-0 row reflects the corrected
                # state (e.g. tension recomputed from theta).
                repaired = verdict.get('repairedValues') or {}
                if isinstance(repaired, dict):
                    for cls_name, repairs in repaired.items():
                        if cls_name in initial_by_class and isinstance(repairs, dict):
                            initial_by_class[cls_name].update(repairs)

            for cls_name in ordered_classes:
                new_row_fields = _project_context_onto_class(
                    initial_by_class[cls_name], cls_name, manager,
                    target_step, time_value, run,
                    sim_def=sim_def,
                )
                rows_to_persist.append((cls_name, new_row_fields))
                solution_traces.append({
                    'solution': '',
                    'simStateClass': cls_name,
                    'status': 'initial-conditions',
                    'stepCount': 0,
                })
            rows_by_class: Dict[str, Dict[str, Any]] = {}
            for cls_name, fields in rows_to_persist:
                _delete_existing_row(manager, run, cls_name, target_step)
                _create_row(manager, cls_name, fields)
                rows_by_class[cls_name] = fields
            _bump_run_counters(manager, run, target_step)
            return {
                'success': True,
                'step': target_step,
                'time': time_value,
                'rowsByClass': rows_by_class,
                'solutionTraces': solution_traces,
                'warnings': warnings,
                'error': None,
            }

        # Walk classes in topo order. Per class, classify the group's
        # solutions into one of three roles:
        #
        #   simStepComplete    — monolithic step solution; ends at
        #                        SimStepNextState.
        #   simStepPartial     — emits a SimStepContribution payload
        #                        (sparse field deltas with per-field
        #                        ops). Zero-or-more per class.
        #   simStepComposition — receives `_step_contributions` + the
        #                        already-merged accumulated context;
        #                        ends at SimStepNextState. At most one
        #                        per class.
        for cls_name in ordered_classes:
            group = solutions_by_class.get(cls_name, [])
            if not group:
                warnings.append(
                    f"Class '{cls_name}' has no enabled SimulationExecutionSolution rows; "
                    f"skipping (no new row will be written for this step)."
                )
                continue

            prev_row = _load_prev_row(
                manager, run, cls_name, target_step - 1, warnings,
            )
            baseline: Dict[str, Any] = _compose_instance_fields(
                prev_row=prev_row,
                params=params,
                deps_outputs=deps_outputs,
                dt=dt,
                time_value=time_value,
                step=target_step,
            )

            # Cross-simulation couplings: lazy-pull each coupled source
            # run to cover this step's time, sample its field, and inject
            # the values (or the coupling's defaults) into the baseline.
            # Soft-fail — a coupling that can't sample warns and leaves
            # its defaults; the step itself still runs.
            apply_couplings(
                manager, run, sim_def, cls_name, baseline, time_value,
                warnings,
                pull_chain=(_pull_chain
                            or frozenset({getattr(run, 'name', '')})),
            )

            # Resolve each solution's role from its no-code graph.
            # '__unset__' marks a wrapper row whose solution_definition_ref
            # is empty (scheduled but not yet authored); skip with warning.
            classified: List[Tuple[Any, str, Optional[Dict[str, Any]]]] = []
            for s in group:
                sname = getattr(s, 'solution_definition_ref', '') or ''
                if not sname:
                    classified.append((s, '__unset__', None))
                    continue
                sdata = _load_solution_data(manager, sname)
                if sdata is None:
                    return _err(
                        f"SimulationExecutionSolution '{getattr(s, 'name', '')}' "
                        f"references missing SolutionDefinition '{sname}'.",
                        warnings,
                    )
                classified.append((s, _detect_step_role(sdata), sdata))

            partial_solutions = [(s, sdata) for s, role, sdata in classified
                                 if role == 'simStepPartial']
            composition_solutions = [(s, sdata) for s, role, sdata in classified
                                     if role == 'simStepComposition']
            complete_solutions = [(s, sdata) for s, role, sdata in classified
                                  if role == 'simStepComplete']

            # Mixed roles validation. A class can run as ALL-Complete
            # OR Partial(+Composition); never both.
            if partial_solutions and complete_solutions:
                return _err(
                    f"Class '{cls_name}' has both Complete and Partial step "
                    f"solutions wired — pick one mode.",
                    warnings,
                    solution_traces=solution_traces,
                )
            if len(composition_solutions) > 1:
                return _err(
                    f"Class '{cls_name}' has {len(composition_solutions)} "
                    f"Composition solutions — only one is allowed per class.",
                    warnings,
                    solution_traces=solution_traces,
                )
            if composition_solutions and not partial_solutions:
                warnings.append(
                    f"Class '{cls_name}' has a Composition solution but no "
                    f"Partials — it will run with no `_step_contributions` to merge."
                )

            for s, role, _ in classified:
                if role == '__unset__':
                    warnings.append(
                        f"Solution '{getattr(s, 'name', '')}' has no "
                        f"solution_definition_ref — skipping."
                    )
                    solution_traces.append({
                        'solution': getattr(s, 'name', ''),
                        'simStateClass': cls_name,
                        'status': 'skipped',
                        'reason': 'no solution_definition_ref',
                    })

            # --- Partial(+Composition) path ------------------------------
            if partial_solutions:
                contributions: List[Dict[str, Any]] = []
                for s, sdata in partial_solutions:
                    trace = engine.execute(
                        solution_data=sdata,
                        input_params={},
                        config=step_cfg,
                        target_runtime='python_backend',
                        instance_fields=dict(baseline),
                    )
                    if trace.status != 'completed':
                        err = getattr(trace, 'error_summary', None) or 'engine error'
                        return _err(
                            f"Partial solution '{getattr(s, 'name', '')}' did not complete: {err}",
                            warnings,
                            solution_traces=solution_traces + [{
                                'solution': getattr(s, 'name', ''),
                                'simStateClass': cls_name,
                                'role': 'simStepPartial',
                                'status': trace.status,
                                'error': str(err),
                                'traceId': getattr(trace, 'execution_id', ''),
                            }],
                        )
                    final_context = _extract_final_context(trace)
                    emitted = final_context.get('_step_contributions') or []
                    if isinstance(emitted, list):
                        contributions.extend(emitted)
                    else:
                        warnings.append(
                            f"Partial solution '{getattr(s, 'name', '')}': "
                            f"`_step_contributions` was not a list — ignored."
                        )
                    solution_traces.append({
                        'solution': getattr(s, 'name', ''),
                        'simStateClass': cls_name,
                        'role': 'simStepPartial',
                        'orderIndex': int(getattr(s, 'order_index', 0) or 0),
                        'status': 'completed',
                        'contributionsEmitted': len(emitted) if isinstance(emitted, list) else 0,
                        'traceId': getattr(trace, 'execution_id', ''),
                        'stepCount': len(getattr(trace, 'steps', []) or []),
                    })

                merged = _apply_step_contributions(
                    baseline=baseline,
                    contributions=contributions,
                    target_class=cls_name,
                    warnings=warnings,
                )

                if composition_solutions:
                    comp_s, comp_sdata = composition_solutions[0]
                    comp_fields = dict(merged)
                    comp_fields['_step_contributions'] = contributions
                    trace = engine.execute(
                        solution_data=comp_sdata,
                        input_params={},
                        config=step_cfg,
                        target_runtime='python_backend',
                        instance_fields=comp_fields,
                    )
                    if trace.status != 'completed':
                        err = getattr(trace, 'error_summary', None) or 'engine error'
                        return _err(
                            f"Composition solution '{getattr(comp_s, 'name', '')}' did not "
                            f"complete: {err}",
                            warnings,
                            solution_traces=solution_traces + [{
                                'solution': getattr(comp_s, 'name', ''),
                                'simStateClass': cls_name,
                                'role': 'simStepComposition',
                                'status': trace.status,
                                'error': str(err),
                                'traceId': getattr(trace, 'execution_id', ''),
                            }],
                        )
                    final = _extract_final_context(trace)
                    merged.update(final)
                    solution_traces.append({
                        'solution': getattr(comp_s, 'name', ''),
                        'simStateClass': cls_name,
                        'role': 'simStepComposition',
                        'status': 'completed',
                        'partialsMerged': len(contributions),
                        'traceId': getattr(trace, 'execution_id', ''),
                        'stepCount': len(getattr(trace, 'steps', []) or []),
                    })

                new_row_fields = _project_context_onto_class(
                    merged, cls_name, manager, target_step, time_value, run,
                    sim_def=sim_def,
                )
                deps_outputs[cls_name] = merged
                rows_to_persist.append((cls_name, new_row_fields))
                continue

            # --- Complete-only path --------------------------------------
            # Multiple Complete solutions still chain sequentially.
            accumulated: Dict[str, Any] = dict(baseline)
            group_had_real_run = False
            for s, sdata in complete_solutions:
                trace = engine.execute(
                    solution_data=sdata,
                    input_params={},
                    config=step_cfg,
                    target_runtime='python_backend',
                    instance_fields=dict(accumulated),
                )
                if trace.status != 'completed':
                    err = getattr(trace, 'error_summary', None) or 'engine error'
                    return _err(
                        f"Solution '{getattr(s, 'name', '')}' execution did not complete: {err}",
                        warnings,
                        solution_traces=solution_traces + [{
                            'solution': getattr(s, 'name', ''),
                            'simStateClass': cls_name,
                            'role': 'simStepComplete',
                            'status': trace.status,
                            'error': str(err),
                            'traceId': getattr(trace, 'execution_id', ''),
                        }],
                    )
                final_context = _extract_final_context(trace)
                accumulated.update(final_context)
                group_had_real_run = True
                solution_traces.append({
                    'solution': getattr(s, 'name', ''),
                    'simStateClass': cls_name,
                    'role': 'simStepComplete',
                    'status': 'completed',
                    'traceId': getattr(trace, 'execution_id', ''),
                    'stepCount': len(getattr(trace, 'steps', []) or []),
                })

            if not group_had_real_run:
                continue

            new_row_fields = _project_context_onto_class(
                accumulated, cls_name, manager, target_step, time_value, run,
                sim_def=sim_def,
            )
            deps_outputs[cls_name] = accumulated
            rows_to_persist.append((cls_name, new_row_fields))

        # 8. Atomic persist — wipe pre-existing rows for this step
        #    (idempotent re-step) and write the new ones.
        rows_by_class: Dict[str, Dict[str, Any]] = {}
        for cls_name, fields in rows_to_persist:
            _delete_existing_row(manager, run, cls_name, target_step)
            _create_row(manager, cls_name, fields)
            rows_by_class[cls_name] = fields

        # 9. Update the SimulationRun's counters.
        _bump_run_counters(manager, run, target_step)

        return {
            'success': True,
            'step': target_step,
            'time': time_value,
            'rowsByClass': rows_by_class,
            'solutionTraces': solution_traces,
            'warnings': warnings,
            'error': None,
        }

    except Exception as exc:
        return _err(f'{type(exc).__name__}: {exc}', warnings)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(
    msg: str,
    warnings: List[str],
    solution_traces: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        'success': False,
        'step': None,
        'time': None,
        'rowsByClass': {},
        'solutionTraces': solution_traces or [],
        'warnings': warnings,
        'error': msg,
    }


def _parse_json(text: str, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def _find_simulation_definition(manager, run):
    name = getattr(run, 'simulation_ref', '')
    if not name:
        return None
    table = manager.objectTables.get('SimulationDefinition', {}) or {}
    for r in table.values():
        if getattr(r, 'name', '') == name:
            return r
    return None


def _participating_classes(sim_def) -> List[str]:
    raw = getattr(sim_def, 'participating_sim_state_classes_json', '[]') or '[]'
    parsed = _parse_json(raw, [])
    if not isinstance(parsed, list):
        return []
    return [c for c in parsed if isinstance(c, str) and c]


def _solutions_by_class(
    manager,
    sim_def,
    participating_classes: List[str],
) -> Dict[str, List]:
    """Pull enabled SimulationExecutionSolution rows for this sim_def,
    grouped by `sim_state_class_name` and sorted internally by
    `order_index` (then by name as a stable tiebreaker).

    Rows naming a class NOT in the sim's participating roster are
    ignored — the roster is the source of truth for "what this sim
    advances."
    """
    sim_def_name = getattr(sim_def, 'name', '')
    participating = set(participating_classes)
    table = manager.objectTables.get('SimulationExecutionSolution', {}) or {}
    out: Dict[str, List] = {c: [] for c in participating_classes}
    for s in table.values():
        if getattr(s, 'simulation_definition_ref', '') != sim_def_name:
            continue
        if not getattr(s, 'enabled', True):
            continue
        cls = getattr(s, 'sim_state_class_name', '') or ''
        if cls not in participating:
            continue
        out[cls].append(s)
    for cls in out:
        out[cls].sort(
            key=lambda r: (
                int(getattr(r, 'order_index', 0) or 0),
                getattr(r, 'name', ''),
            )
        )
    return out


def _topo_sort_classes(
    participating_classes: List[str],
    solutions_by_class: Dict[str, List],
) -> Optional[List[str]]:
    """Topologically order the participating classes by the UNION of
    their solutions' `depends_on_json`. Classes with no solutions still
    appear in the output (they'll be skipped with a warning during
    execution; they shouldn't affect topo ordering).

    Returns None on cycle.
    """
    deps_union: Dict[str, set] = {c: set() for c in participating_classes}
    participating_set = set(participating_classes)
    for cls, solutions in solutions_by_class.items():
        for s in solutions:
            raw = getattr(s, 'depends_on_json', '[]') or '[]'
            deps = _parse_json(raw, [])
            if not isinstance(deps, list):
                continue
            deps_union[cls].update(
                d for d in deps
                if isinstance(d, str) and d in participating_set and d != cls
            )

    indegree: Dict[str, int] = {c: len(d) for c, d in deps_union.items()}
    ready = sorted([c for c, d in indegree.items() if d == 0])
    ordered: List[str] = []
    while ready:
        cls = ready.pop(0)
        ordered.append(cls)
        for other_cls, other_deps in deps_union.items():
            if cls in other_deps:
                indegree[other_cls] -= 1
                if indegree[other_cls] == 0:
                    ready.append(other_cls)
        ready.sort()

    if len(ordered) != len(deps_union):
        return None
    return ordered


def _has_any_rows_for_run(manager, sim_def, run) -> bool:
    """True if any participating *SimState class has at least one row
    tagged with this run's name."""
    run_name = getattr(run, 'name', '')
    for cls_name in _participating_classes(sim_def):
        rows = manager.objectTables.get(cls_name, {}) or {}
        for r in rows.values():
            if getattr(r, 'simulation_run_ref', '') == run_name:
                return True
    return False


def _initial_field_values(
    manager,
    cls_name: str,
    sim_overrides: Dict[str, Any],
    run_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge class-level `default_initial_field_values` with the sim's
    per-class overrides and any per-run overrides.

    Resolution order (later wins):
      1. class `default_initial_field_values`
      2. SimulationDefinition.initial_conditions_overrides_json[cls]
      3. SimulationRun.initial_conditions_overrides_json[cls]

    The per-run layer lets users tweak the starting state for a one-off
    run without mutating the saved sim def.
    """
    out: Dict[str, Any] = {}
    typing_obj = manager.objectTypingDict.get(cls_name)
    cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
    defaults = getattr(cls, 'default_initial_field_values', None) if cls else None
    if isinstance(defaults, dict):
        out.update(defaults)
    cls_sim_overrides = sim_overrides.get(cls_name) if isinstance(sim_overrides, dict) else None
    if isinstance(cls_sim_overrides, dict):
        out.update(cls_sim_overrides)
    if isinstance(run_overrides, dict):
        cls_run_overrides = run_overrides.get(cls_name)
        if isinstance(cls_run_overrides, dict):
            out.update(cls_run_overrides)
    return out


def validate_initial_conditions(
    manager,
    sim_def,
    initial_conditions_by_class: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Run the sim def's `initial_conditions_validator_ref` solution
    against the proposed initial conditions and return a structured
    verdict.

    Returns:
        {
          'valid':     bool,  # True when no validator OR validator says OK
          'hasValidator': bool,
          'reason':    str,   # populated when valid=False
          'repairedValues': dict[str, dict[str, Any]] | None,
          'error':     str | None,  # populated when validator execution fails
        }

    Context passed to the validator:
      * `<className>.<field>` keys for each participating class's merged
        initial values (e.g. `PendulumBobSimState.theta`)
      * `params.<key>` for each entry in `parameters_json`
      * `participating_classes` — list of class names in this sim

    The validator solution's terminator is expected to be a
    `ValidationResult` end state with bound `outcome`, `reason`, and
    optionally `repairedValues` fields.
    """
    validator_ref = getattr(sim_def, 'initial_conditions_validator_ref', '') or ''
    if not validator_ref:
        return {
            'valid': True,
            'hasValidator': False,
            'reason': '',
            'repairedValues': None,
            'error': None,
        }
    sdata = _load_solution_data(manager, validator_ref)
    if sdata is None:
        return {
            'valid': False,
            'hasValidator': True,
            'reason': '',
            'repairedValues': None,
            'error': f"validator solution '{validator_ref}' not found",
        }

    # Flatten initial conditions into '<class>.<field>' keys + add the
    # sim's parameters under 'params.<key>'.
    flat: Dict[str, Any] = {}
    for cls_name, fields in initial_conditions_by_class.items():
        if not isinstance(fields, dict):
            continue
        for fname, fval in fields.items():
            flat[f'{cls_name}.{fname}'] = fval
    params = _parse_json(getattr(sim_def, 'parameters_json', '{}') or '{}', {})
    if isinstance(params, dict):
        for k, v in params.items():
            flat[f'params.{k}'] = v
    flat['participating_classes'] = list(initial_conditions_by_class.keys())

    engine = SolutionExecutionEngine(manager=manager)
    step_cfg = StepConfig(mode='step', record_context=True)
    try:
        trace = engine.execute(
            solution_data=sdata,
            input_params={},
            config=step_cfg,
            target_runtime='python_backend',
            instance_fields=flat,
        )
    except Exception as exc:
        return {
            'valid': False,
            'hasValidator': True,
            'reason': '',
            'repairedValues': None,
            'error': f'{type(exc).__name__}: {exc}',
        }
    if trace.status != 'completed':
        err = getattr(trace, 'error_summary', None) or 'engine error'
        return {
            'valid': False,
            'hasValidator': True,
            'reason': '',
            'repairedValues': None,
            'error': str(err),
        }
    final = _extract_final_context(trace)
    outcome = (final.get('outcome') or '').strip().lower()
    reason = str(final.get('reason') or '').strip()
    repaired = final.get('repairedValues')
    if not isinstance(repaired, dict):
        repaired = None
    valid = outcome == 'valid'
    return {
        'valid': valid,
        'hasValidator': True,
        'reason': reason if not valid else '',
        'repairedValues': repaired,
        'error': None,
    }


def _load_solution_data(manager, solution_name: str) -> Optional[Dict]:
    """Resolve a solution name. Tries SolutionDefinition first, then
    SimulationExecutionSolution wrapper rows that dereference to one.
    Direct SolutionDefinition wins to avoid an extra hop when callers
    point straight at the graph.
    """
    sol_def_table = manager.objectTables.get('SolutionDefinition', {}) or {}
    for inst in sol_def_table.values():
        if getattr(inst, 'name', '') != solution_name:
            continue
        return _parse_definition(getattr(inst, 'definition', '{}'))

    metadata_table = manager.objectTables.get('SimulationExecutionSolution', {}) or {}
    for inst in metadata_table.values():
        if getattr(inst, 'name', '') != solution_name:
            continue
        target = getattr(inst, 'solution_definition_ref', '') or ''
        if not target:
            return None
        for sol_inst in sol_def_table.values():
            if getattr(sol_inst, 'name', '') == target:
                return _parse_definition(getattr(sol_inst, 'definition', '{}'))
        return None

    return None


def _parse_definition(raw: Any) -> Optional[Dict]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _load_prev_row(
    manager,
    run,
    cls_name: str,
    prev_step: int,
    warnings: List[str],
) -> Dict[str, Any]:
    table = manager.objectTables.get(cls_name, {}) or {}
    for r in table.values():
        if getattr(r, 'simulation_run_ref', '') != getattr(run, 'name', ''):
            continue
        # Important: do NOT collapse a legit step=0 with `or -1`.
        raw = getattr(r, 'step', None)
        try:
            step_val = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            step_val = None
        if step_val != prev_step:
            continue
        return _row_as_dict(r)
    warnings.append(
        f"No previous {cls_name} row at step={prev_step} for run "
        f"'{getattr(run, 'name', '')}' — treating prev values as zeros."
    )
    return {}


def _row_as_dict(row) -> Dict[str, Any]:
    """Snapshot a row's public attributes as a dict. Skips private and
    framework-injected names."""
    skip = {'manager', 'branch', 'inTree', 'polariId'}
    out = {}
    for k, v in vars(row).items():
        if k.startswith('_') or k in skip:
            continue
        out[k] = v
    return out


def _compose_instance_fields(
    prev_row: Dict[str, Any],
    params: Dict[str, Any],
    deps_outputs: Dict[str, Dict[str, Any]],
    dt: float,
    time_value: float,
    step: int,
) -> Dict[str, Any]:
    """Merge order — earliest wins; later overrides.

    Order (later overrides earlier):
      1. prev_row's fields (the previous timestep's outputs)
      2. params (g, L, mass, ...)
      3. deps_outputs values (current-step outputs of dep SimStates)
      4. step metadata (dt, time, step) — always wins
    """
    out: Dict[str, Any] = {}
    out.update(prev_row or {})
    out.update(params or {})
    for _cls, ctx in (deps_outputs or {}).items():
        out.update(ctx)
    out['dt'] = dt
    out['time'] = time_value
    out['step'] = step
    return out


def _extract_final_context(trace) -> Dict[str, Any]:
    """Read the variables dict from the trace's last step's context_after,
    unwrapping each entry. InstanceContextSnapshot stores variables as
    `{name, type, value, sourceStateName}` wrapped records; the runner
    needs the raw values."""
    steps = getattr(trace, 'steps', None) or []
    if not steps:
        return {}
    last = steps[-1]
    context_after = getattr(last, 'context_after', None)
    if context_after is None:
        return {}
    variables = getattr(context_after, 'variables', None)
    if not isinstance(variables, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in variables.items():
        if isinstance(v, dict) and 'value' in v and 'name' in v:
            out[k] = v.get('value')
        else:
            out[k] = v
    return out


def _project_context_onto_class(
    context: Dict[str, Any],
    cls_name: str,
    manager,
    step: int,
    time_value: float,
    run,
    sim_def=None,
) -> Dict[str, Any]:
    """Build the kwargs dict for a new `*SimState` row constructor.

    Honors the merged class + sim-def + per-run `field_save_policy` —
    fields whose effective policy resolves to 'derivable' or 'skip'
    (or that fall outside their per-field interval) are omitted from
    the kwargs, so the row instance falls back to the constructor's
    default value (typically 0.0 for floats).

    Identity fields (`name`, `simulation_run_ref`, `step`, `time`) are
    always stamped regardless of policy — they're framework-owned, not
    a user-declared part of the schema.
    """
    typing_obj = manager.objectTypingDict.get(cls_name)
    field_names = set()
    if typing_obj is not None:
        ptv_dict = getattr(typing_obj, 'polyTypedVarsDict', {}) or {}
        field_names.update(ptv_dict.keys())
        if not field_names:
            field_names.update(getattr(typing_obj, 'kwDefaultParams', []) or [])

    rules = _effective_field_save_rules(manager, sim_def, run, cls_name)

    out: Dict[str, Any] = {}
    for k, v in context.items():
        if field_names and k not in field_names:
            continue
        rule = rules.get(k, {'policy': 'core', 'interval': 0})
        if not _field_persists_at_step(rule, step):
            continue
        out[k] = v

    out['name'] = _row_name_for(cls_name, run, step)
    out['simulation_run_ref'] = getattr(run, 'name', '')
    out['step'] = step
    out['time'] = round(time_value, 6)
    return out


def _field_save_policy_for(manager, cls_name: str) -> Dict[str, str]:
    """Read the class-declared `field_save_policy` dict, defaulting
    each unlisted field to 'core'. Returns an empty dict when the
    class isn't registered — callers treat absent entries as 'core'."""
    typing_obj = manager.objectTypingDict.get(cls_name) if manager else None
    cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
    raw = getattr(cls, 'field_save_policy', None) if cls else None
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}


def _effective_field_save_rules(
    manager,
    sim_def,
    run,
    cls_name: str,
) -> Dict[str, Dict[str, Any]]:
    """Merge class-level `field_save_policy` with the sim def's and the
    run's `field_save_overrides_json`. Returns a dict keyed by
    fieldName of `{policy, interval}`:
      * policy: 'core' | 'derivable' | 'skip' — final decision
      * interval: int — per-field recording interval override (0 = use
        sim def's recording_interval_steps)

    Resolution (later wins):
      1. class.field_save_policy[field]                (policy only)
      2. sim_def.field_save_overrides_json[<cls>.<field>]
      3. run.field_save_overrides_json[<cls>.<field>]
    """
    out: Dict[str, Dict[str, Any]] = {}
    base = _field_save_policy_for(manager, cls_name)
    for fname, policy in base.items():
        out[fname] = {'policy': policy, 'interval': 0}

    def _apply(source: Any) -> None:
        if not isinstance(source, dict):
            return
        prefix = f'{cls_name}.'
        for key, rule in source.items():
            if not isinstance(key, str) or not key.startswith(prefix):
                continue
            fname = key[len(prefix):]
            if not fname:
                continue
            entry = out.setdefault(fname, {'policy': 'core', 'interval': 0})
            if isinstance(rule, dict):
                if isinstance(rule.get('policy'), str):
                    entry['policy'] = rule['policy']
                try:
                    iv = int(rule.get('interval') or 0)
                    if iv > 0:
                        entry['interval'] = iv
                except (TypeError, ValueError):
                    pass

    _apply(_parse_json(
        getattr(sim_def, 'field_save_overrides_json', '{}') or '{}', {}
    ))
    if run is not None:
        _apply(_parse_json(
            getattr(run, 'field_save_overrides_json', '{}') or '{}', {}
        ))
    return out


def _field_persists_at_step(rule: Dict[str, Any], step: int) -> bool:
    """Apply a single field's effective rule against a target step.
    'skip' → never; 'derivable' → never (unless an override flipped it
    to 'core'). 'core' fields with no explicit per-field interval
    persist on EVERY step — the live runner writes one row per step
    and we want core fields fully populated in each. A field with an
    explicit `interval > 1` (Phase B override) gets sparser.

    Important: the sim def's `recording_interval_steps` is NOT used
    here. That setting is about sampling the run (which rows to
    persist) — a row-level concern handled elsewhere — not which
    fields to populate inside an already-being-written row. Conflating
    the two writes rows with constructor defaults (0.0) on off-interval
    steps, which looks like the bob snapping back to the pivot.
    """
    policy = rule.get('policy', 'core')
    if policy == 'skip' or policy == 'derivable':
        return False
    if step == 0:
        return True
    try:
        interval = int(rule.get('interval') or 0)
    except (TypeError, ValueError):
        interval = 0
    if interval <= 1:
        return True
    return (step % interval) == 0


def _row_name_for(cls_name: str, run, step: int) -> str:
    """Composite-name convention: `<run>-<role>-<step>` where role is a
    lower-case slug derived from the class name (PendulumBobSimState
    → 'bob')."""
    role = cls_name
    for tail in ('SimState', 'State'):
        if role.endswith(tail):
            role = role[: -len(tail)]
            break
    role_slug = _to_kebab(role).lower()
    return f"{getattr(run, 'name', '')}-{role_slug}-{step}"


def _to_kebab(camel: str) -> str:
    out = []
    for i, ch in enumerate(camel):
        if ch.isupper() and i > 0 and not camel[i - 1].isupper():
            out.append('-')
        out.append(ch.lower())
    return ''.join(out)


def _delete_existing_row(manager, run, cls_name: str, step: int) -> None:
    """Idempotent re-step: drop any row with the same (run, step)."""
    table = manager.objectTables.get(cls_name, {}) or {}
    to_remove = []
    run_name = getattr(run, 'name', '')
    for key, inst in table.items():
        if getattr(inst, 'simulation_run_ref', '') != run_name:
            continue
        raw = getattr(inst, 'step', None)
        try:
            step_val = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            step_val = None
        if step_val != step:
            continue
        to_remove.append(key)
    for key in to_remove:
        try:
            del table[key]
        except Exception:
            pass


def _create_row(manager, cls_name: str, fields: Dict[str, Any]) -> None:
    """Instantiate via the typing-recorded class AND persist it through the
    object-tree standard path.

    Constructing a treeObject only registers it in the manager's in-memory
    `objectTables` (see objectTreeDecorators.__init__) — it does NOT write to
    the DB. Every standard create path (e.g. polariCRUDE) follows construction
    with `manager.db.saveInstanceInDB(inst)`; the runner must do the same or
    stepped rows live only in memory and are lost on restart / invisible to any
    DB-backed tooling.
    """
    typing_obj = manager.objectTypingDict.get(cls_name)
    if typing_obj is None:
        raise RuntimeError(f"Class '{cls_name}' not registered in objectTypingDict.")
    cls = getattr(typing_obj, 'classDefinition', None)
    if cls is None:
        table = manager.objectTables.get(cls_name, {}) or {}
        for inst in table.values():
            cls = inst.__class__
            break
    if cls is None:
        raise RuntimeError(f"Cannot resolve constructor for class '{cls_name}'.")
    inst = cls(**fields, manager=manager)
    # Persist to the DB via the standard object-tree call (mirrors polariCRUDE).
    db = getattr(manager, 'db', None)
    if db is not None:
        db.saveInstanceInDB(inst)


def _bump_run_counters(manager, run, target_step: int) -> None:
    last = int(getattr(run, 'last_recorded_step', 0) or 0)
    if target_step > last:
        run.last_recorded_step = target_step
        try:
            run.recorded_steps = int(getattr(run, 'recorded_steps', 0) or 0) + 1
        except (TypeError, ValueError):
            run.recorded_steps = 1
        # Persist the counter mutation through the standard object-tree path,
        # so a restart doesn't revert the run to step 0 while its rows persist.
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(run)


def _detect_step_role(solution_data: Dict[str, Any]) -> str:
    """Determine the simStepRole declared by a step solution's entry state.
    Returns one of 'simStepComplete' | 'simStepPartial' | 'simStepComposition'.
    """
    if not isinstance(solution_data, dict):
        raise ValueError("Solution data is not a dict; cannot detect simStepRole.")
    states = solution_data.get('stateInstances') or solution_data.get('states') or []
    if not isinstance(states, list):
        raise ValueError("Solution `stateInstances` is not a list.")
    valid_roles = ('simStepComplete', 'simStepPartial', 'simStepComposition')
    for s in states:
        if not isinstance(s, dict):
            continue
        cls = s.get('stateClass') or s.get('boundObjectClass') or ''
        if cls != 'SimulationStateStep':
            continue
        fv = s.get('boundObjectFieldValues') or {}
        role_raw = fv.get('simStepRole')
        if not isinstance(role_raw, str) or not role_raw.strip():
            raise ValueError(
                f"SimulationStateStep entry '{s.get('stateName', '?')}' "
                f"has no simStepRole declared. Required one of: "
                f"{' | '.join(valid_roles)}."
            )
        role = role_raw.strip()
        if role not in valid_roles:
            raise ValueError(
                f"SimulationStateStep entry '{s.get('stateName', '?')}': "
                f"unknown simStepRole={role_raw!r}. Expected one of: "
                f"{' | '.join(valid_roles)}."
            )
        return role
    raise ValueError(
        "Step solution has no SimulationStateStep entry state."
    )


def _apply_step_contributions(
    baseline: Dict[str, Any],
    contributions: List[Dict[str, Any]],
    target_class: str,
    warnings: List[str],
) -> Dict[str, Any]:
    """Apply a sequence of SimStepContribution payloads onto a baseline
    context dict, producing the merged next-step field map.

    Ops applied in ARRIVAL ORDER:
        set : merged[f] = value
        add : merged[f] = (merged[f] or 0) + value
        mul : merged[f] = (merged[f] or 0) * value
        min : merged[f] = min(merged[f], value)
        max : merged[f] = max(merged[f], value)
    """
    merged: Dict[str, Any] = dict(baseline)
    for c in contributions:
        if not isinstance(c, dict):
            continue
        c_target = c.get('targetClass') or ''
        if c_target and c_target != target_class:
            warnings.append(
                f"SimStepContribution targets class '{c_target}' but was "
                f"emitted under class '{target_class}' group — ignoring."
            )
            continue
        deltas = c.get('fieldDeltas') or {}
        if not isinstance(deltas, dict):
            continue
        for field_name, delta in deltas.items():
            if not isinstance(delta, dict):
                continue
            value = delta.get('value')
            op = (delta.get('op') or 'set').strip().lower()
            current = merged.get(field_name)
            try:
                if op == 'set':
                    merged[field_name] = value
                elif op == 'add':
                    merged[field_name] = (current or 0) + value
                elif op == 'mul':
                    merged[field_name] = (current or 0) * value
                elif op == 'min':
                    merged[field_name] = (
                        value if current is None else min(current, value)
                    )
                elif op == 'max':
                    merged[field_name] = (
                        value if current is None else max(current, value)
                    )
                else:
                    warnings.append(
                        f"SimStepContribution on '{field_name}' uses "
                        f"unknown op '{op}' — applied as 'set'."
                    )
                    merged[field_name] = value
            except (TypeError, ValueError) as e:
                warnings.append(
                    f"SimStepContribution merge failed on field "
                    f"'{field_name}' (op={op}, value={value!r}, "
                    f"current={current!r}): {e}"
                )
    return merged
