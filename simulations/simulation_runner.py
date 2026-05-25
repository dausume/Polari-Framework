"""
@cross-cutting
@module simulations.simulation_runner
@tags @xc:bindings

SimulationRunner — orchestrates per-timestep execution of a
SimulationRun by composing one no-code solution per participating
`*SimState` class. Pure orchestration: no state-graph walking, no
trace bookkeeping, no SymPy. Delegates each binding's step solution to
the existing `SolutionExecutionEngine`, then maps the resulting
ExecutionTrace's final context onto a new `*SimState` row.

The single public entry point is `run_step()` — advance the run by
exactly one timestep. The proposal layers (`/run` background loop,
STOMP streaming) wrap this same primitive; if `run_step` works for
the single-step "is this coherent?" check, the multi-step loop works
by induction.

Failure model: a single binding's failure aborts the step. Partial
rows are NOT persisted — either every binding's row lands for the
target step or none of them do. The caller gets a structured error
listing which binding failed and why; the SimulationRun.status is
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


def run_step(
    manager,
    run,
    target_step: Optional[int] = None,
) -> Dict[str, Any]:
    """Advance a SimulationRun by exactly one timestep.

    `target_step` defaults to `run.last_recorded_step + 1` (or 0 if no
    rows have been written yet). Passing it explicitly lets a caller
    re-run a step idempotently (the runner will delete existing rows
    for that step before re-emitting).

    Returns:
        {
          'success': bool,
          'step': int,
          'time': float,
          'rows_by_class': { '<SimStateClass>': {<fields>}, ... },
          'binding_traces': [ { binding, status, trace_id, error? }, ... ],
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
        dt = float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01)
        time_value = target_step * dt

        # 3. Gather enabled SimStateStepBindings for this simulation.
        bindings = _enabled_bindings_for(manager, sim_def, warnings)
        if not bindings:
            return _err(
                'No enabled SimStateStepBindings for this simulation.',
                warnings,
            )

        # 4. Group by SimState class, topo-sort the GROUPS by inter-
        #    class deps, and within each group order by order_index.
        ordered_groups = _topo_sort_binding_groups(bindings)
        if ordered_groups is None:
            return _err('Cycle in SimStateStepBinding dependencies.', warnings)

        # 5. Pre-build common context pieces that don't change per binding.
        params = _parse_json(getattr(sim_def, 'parameters_json', '{}') or '{}', {})
        initial_conditions = _parse_json(
            getattr(sim_def, 'initial_conditions_json', '{}') or '{}', {}
        )

        # 6. Execute each binding in order. Collect rows in memory first;
        #    only persist after all bindings succeed (atomic-per-step).
        engine = SolutionExecutionEngine(manager=manager)
        step_cfg = StepConfig(mode='step', record_context=True)
        deps_outputs: Dict[str, Dict[str, Any]] = {}
        rows_to_persist: List[Tuple[str, Dict[str, Any]]] = []
        binding_traces: List[Dict[str, Any]] = []

        # Convention: step=0 is the initial-conditions snapshot. We
        # write it WITHOUT running the engine — there's no "previous
        # step" to integrate from at t=0. The engine kicks in at
        # step=1 (the first advance). Matches the precomputed-seed
        # convention where step 0 holds the starting (theta, omega).
        if target_step == 0:
            # Each SimState class participating in the simulation gets
            # exactly one row with the initial-conditions fields. Even
            # with multiple bindings per class, the t=0 row is a single
            # write — the no-code engine doesn't run on step 0.
            for cls_name, group in ordered_groups:
                new_row_fields = _project_context_onto_class(
                    initial_conditions, cls_name, manager,
                    target_step, time_value, run,
                )
                rows_to_persist.append((cls_name, new_row_fields))
                for binding in group:
                    binding_traces.append({
                        'binding': binding.name,
                        'simStateClass': cls_name,
                        'status': 'initial-conditions',
                        'stepCount': 0,
                    })
            rows_by_class: Dict[str, Dict[str, Any]] = {}
            for cls_name, fields in rows_to_persist:
                _delete_existing_row(manager, run, cls_name, target_step)
                _create_row(manager, cls_name, fields)
                rows_by_class[cls_name] = fields
            _bump_run_counters(run, target_step)
            return {
                'success': True,
                'step': target_step,
                'time': time_value,
                'rowsByClass': rows_by_class,
                'bindingTraces': binding_traces,
                'warnings': warnings,
                'error': None,
            }

        # Walk classes in topo order. Per class, classify the group's
        # bindings into one of three roles:
        #
        #   simStepComplete    — monolithic step solution; ends at
        #                        SimStepNextState. Single-solution-per-
        #                        class closed-form update path.
        #   simStepPartial     — emits a SimStepContribution payload
        #                        (sparse field deltas with per-field
        #                        ops). Zero-or-more per class; runner
        #                        aggregates the deltas after each
        #                        binding's trace.
        #   simStepComposition — receives `_step_contributions` + the
        #                        already-merged accumulated context;
        #                        ends at SimStepNextState. At most one
        #                        per class; required when a non-
        #                        additive composition of partials is
        #                        needed.
        #
        # Modes per group:
        #   - All Complete bindings: sequential pipeline — each
        #     binding's final context feeds the next, last context
        #     projects onto the row.
        #   - Partial(+Composition) mix: each partial runs against the
        #     prev-step baseline (NOT the running merge — preserves
        #     parallel-batch semantics for same-order_index partials).
        #     After all partials, the merged context is either projected
        #     directly (no Composition) or handed off to the
        #     Composition solution.
        for cls_name, group in ordered_groups:
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

            # Resolve each binding's role from its solution graph.
            # `__unset__` marks a binding with an empty step_solution_ref
            # (the user wired a binding but hasn't authored a solution
            # yet); those drop into the skip-with-warning path below.
            classified: List[Tuple[Any, str, Optional[Dict[str, Any]]]] = []
            for b in group:
                sname = getattr(b, 'step_solution_ref', '') or ''
                if not sname:
                    classified.append((b, '__unset__', None))
                    continue
                sdata = _load_solution_data(manager, sname)
                if sdata is None:
                    return _err(
                        f"Binding '{b.name}' references missing "
                        f"SolutionDefinition '{sname}'.",
                        warnings,
                    )
                classified.append((b, _detect_step_role(sdata), sdata))

            partial_bindings = [(b, sdata) for b, role, sdata in classified
                                if role == 'simStepPartial']
            composition_bindings = [(b, sdata) for b, role, sdata in classified
                                    if role == 'simStepComposition']
            complete_bindings = [(b, sdata) for b, role, sdata in classified
                                 if role == 'simStepComplete']

            # Mixed roles validation. A class can run as ALL-Complete
            # OR Partial(+Composition); never both.
            if partial_bindings and complete_bindings:
                return _err(
                    f"Class '{cls_name}' has both Complete and Partial step "
                    f"solutions wired — pick one mode. Either delete the "
                    f"Complete binding or convert it to a Partial.",
                    warnings,
                    binding_traces=binding_traces,
                )
            if len(composition_bindings) > 1:
                return _err(
                    f"Class '{cls_name}' has {len(composition_bindings)} "
                    f"Composition solutions — only one is allowed per class.",
                    warnings,
                    binding_traces=binding_traces,
                )
            if composition_bindings and not partial_bindings:
                warnings.append(
                    f"Class '{cls_name}' has a Composition solution but no "
                    f"Partial bindings — it will run with no "
                    f"`_step_contributions` to merge."
                )

            # Warn about and record any unset (no step_solution_ref)
            # bindings up front so the role-aware branches below can
            # treat their input lists as fully resolved.
            for b, role, _ in classified:
                if role == '__unset__':
                    warnings.append(
                        f"Binding '{b.name}': step_solution_ref empty — skipping. "
                        f"Author a no-code solution and point this binding at it."
                    )
                    binding_traces.append({
                        'binding': b.name,
                        'simStateClass': cls_name,
                        'status': 'skipped',
                        'reason': 'no step_solution_ref',
                    })

            # --- Partial(+Composition) path ------------------------------
            if partial_bindings:
                contributions: List[Dict[str, Any]] = []
                for b, sdata in partial_bindings:
                    trace = engine.execute(
                        solution_data=sdata,
                        input_params={},
                        config=step_cfg,
                        target_runtime='python_backend',
                        # Partials read the SAME prev-step baseline.
                        # Ordering semantics live in the merge step, not
                        # in chaining contexts (which would defeat the
                        # "parallel batch" intent of same-order_index
                        # partials).
                        instance_fields=dict(baseline),
                    )
                    if trace.status != 'completed':
                        err = getattr(trace, 'error_summary', None) or 'engine error'
                        return _err(
                            f"Partial binding '{b.name}' did not complete: {err}",
                            warnings,
                            binding_traces=binding_traces + [{
                                'binding': b.name,
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
                            f"Partial binding '{b.name}': "
                            f"`_step_contributions` was not a list — ignored."
                        )
                    binding_traces.append({
                        'binding': b.name,
                        'simStateClass': cls_name,
                        'role': 'simStepPartial',
                        'orderIndex': int(getattr(b, 'order_index', 0) or 0),
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

                # Either run the Composition solution to compose the
                # final row, or use the additively-merged context as
                # the row directly.
                if composition_bindings:
                    comp_b, comp_sdata = composition_bindings[0]
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
                            f"Composition binding '{comp_b.name}' did not "
                            f"complete: {err}",
                            warnings,
                            binding_traces=binding_traces + [{
                                'binding': comp_b.name,
                                'simStateClass': cls_name,
                                'role': 'simStepComposition',
                                'status': trace.status,
                                'error': str(err),
                                'traceId': getattr(trace, 'execution_id', ''),
                            }],
                        )
                    final = _extract_final_context(trace)
                    merged.update(final)
                    binding_traces.append({
                        'binding': comp_b.name,
                        'simStateClass': cls_name,
                        'role': 'simStepComposition',
                        'status': 'completed',
                        'partialsMerged': len(contributions),
                        'traceId': getattr(trace, 'execution_id', ''),
                        'stepCount': len(getattr(trace, 'steps', []) or []),
                    })

                new_row_fields = _project_context_onto_class(
                    merged, cls_name, manager, target_step, time_value, run,
                )
                deps_outputs[cls_name] = merged
                rows_to_persist.append((cls_name, new_row_fields))
                continue

            # --- Complete-only path --------------------------------------
            # Multiple Complete bindings still chain sequentially: each
            # binding's final context feeds the next, last one's context
            # projects onto the row. Useful for "force calculator →
            # integrator" pipelines that aren't worth splitting into
            # Partials.
            accumulated: Dict[str, Any] = dict(baseline)
            group_had_real_run = False
            for b, sdata in complete_bindings:
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
                        f"Binding '{b.name}' execution did not complete: {err}",
                        warnings,
                        binding_traces=binding_traces + [{
                            'binding': b.name,
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
                binding_traces.append({
                    'binding': b.name,
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
            )
            deps_outputs[cls_name] = accumulated
            rows_to_persist.append((cls_name, new_row_fields))

        # 7. Atomic persist — wipe any pre-existing rows for this step
        #    (idempotent re-step) and write the new ones.
        rows_by_class: Dict[str, Dict[str, Any]] = {}
        for cls_name, fields in rows_to_persist:
            _delete_existing_row(manager, run, cls_name, target_step)
            _create_row(manager, cls_name, fields)
            rows_by_class[cls_name] = fields

        # 8. Update the SimulationRun's counters.
        _bump_run_counters(run, target_step)

        return {
            'success': True,
            'step': target_step,
            'time': time_value,
            'rowsByClass': rows_by_class,
            'bindingTraces': binding_traces,
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
    binding_traces: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        'success': False,
        'step': None,
        'time': None,
        'rowsByClass': {},
        'bindingTraces': binding_traces or [],
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


def _has_any_rows_for_run(manager, sim_def, run) -> bool:
    """True if any SimState class participating in this simulation has
    at least one row tagged with this run's name."""
    sim_def_name = getattr(sim_def, 'name', '')
    bindings = manager.objectTables.get('SimStateStepBinding', {}) or {}
    for b in bindings.values():
        if getattr(b, 'simulation_definition_ref', '') != sim_def_name:
            continue
        cls_name = getattr(b, 'sim_state_class_name', '')
        rows = manager.objectTables.get(cls_name, {}) or {}
        for r in rows.values():
            if getattr(r, 'simulation_run_ref', '') == getattr(run, 'name', ''):
                return True
    return False


def _enabled_bindings_for(manager, sim_def, warnings: List[str]) -> List:
    sim_def_name = getattr(sim_def, 'name', '')
    table = manager.objectTables.get('SimStateStepBinding', {}) or {}
    out = []
    for b in table.values():
        if getattr(b, 'simulation_definition_ref', '') != sim_def_name:
            continue
        if not getattr(b, 'enabled', True):
            continue
        out.append(b)
    return out


def _topo_sort_binding_groups(bindings: List) -> Optional[List]:
    """Group bindings by sim_state_class_name and order the GROUPS by
    cross-class dependencies. Each group's bindings are themselves
    ordered by ascending `order_index` (and stable by name as a
    tiebreaker) so a "force calculator" → "integrator" pipeline runs
    in the right sequence.

    Returns a list of (cls_name, [binding, ...]) tuples, or None on
    cycle. Returns an empty list when there are no bindings.

    A binding's depends_on_json names OTHER SimState classes whose
    current-step values it needs to read. Cycles between classes are
    fatal (Kahn's algorithm yields fewer items than input).
    """
    groups: Dict[str, List] = {}
    deps_union: Dict[str, set] = {}
    for b in bindings:
        cls = getattr(b, 'sim_state_class_name', '')
        if not cls:
            continue
        groups.setdefault(cls, []).append(b)
        deps = _parse_json(getattr(b, 'depends_on_json', '[]') or '[]', [])
        if not isinstance(deps, list):
            deps = []
        # Union the deps across every binding in the same group — if
        # ANY binding in the group declares the dep, the whole class
        # group must wait for it.
        deps_union.setdefault(cls, set()).update(deps)

    # Restrict deps to classes that are themselves grouped here;
    # external references are ignored (the solution may still read
    # them but we don't enforce ordering for non-participating classes).
    for cls in deps_union:
        deps_union[cls] &= set(groups.keys())

    # Sort each group internally by order_index, then by name.
    for cls in groups:
        groups[cls].sort(
            key=lambda b: (
                int(getattr(b, 'order_index', 0) or 0),
                getattr(b, 'name', ''),
            )
        )

    indegree: Dict[str, int] = {cls: len(deps) for cls, deps in deps_union.items()}
    ready = sorted([c for c, d in indegree.items() if d == 0])
    ordered: List = []
    while ready:
        cls = ready.pop(0)
        ordered.append((cls, groups[cls]))
        for other_cls, other_deps in deps_union.items():
            if cls in other_deps:
                indegree[other_cls] -= 1
                if indegree[other_cls] == 0:
                    ready.append(other_cls)
        ready.sort()

    if len(ordered) != len(groups):
        return None
    return ordered


def _load_solution_data(manager, solution_name: str) -> Optional[Dict]:
    """Resolve a step_solution_ref by name.

    The reference can be either:
      - A `SolutionDefinition` name (direct — the no-code editor's
        canonical solutions table)
      - A `SimulationExecutionSolution` name (metadata wrapper —
        dereferences to a SolutionDefinition via `solution_definition_ref`)

    Direct SolutionDefinition wins first to avoid an extra hop when
    bindings point straight at the graph; metadata wrappers are
    consulted when no SolutionDefinition matches.
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


def _initial_pseudo_row(
    initial_conditions: Dict[str, Any],
    cls_name: str,
    manager,
) -> Dict[str, Any]:
    """Synthesize a 'previous' row at step=-1 from the simulation's
    initial_conditions_json. Only the keys named in initial_conditions
    are populated — the step solution should treat anything else as
    starting at zero (or its declared default)."""
    return dict(initial_conditions)


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
        # Important: do NOT collapse a legit step=0 with `or -1`. The
        # `or` short-circuit would treat 0 as falsy and substitute -1,
        # causing the step-0 row to be invisible to every subsequent
        # step. Use a sentinel check on the raw value instead.
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
    framework-injected names so we don't leak them into the engine
    context."""
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
    """Merge order — earliest wins; later overrides. The 'self.*' style
    paths used by no-code value-source configs flatten over this dict,
    so we keep top-level names matching field names.

    Order (later overrides earlier):
      1. prev_row's fields (the previous timestep's outputs)
      2. params (g, L, mass, ...)
      3. deps_outputs values (current-step outputs of dep SimStates)
      4. step metadata (dt, time, step) — always wins so the solution
         can't accidentally shadow them with a same-named row field.
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


def _deps_subset(
    deps_outputs: Dict[str, Dict[str, Any]],
    binding,
) -> Dict[str, Dict[str, Any]]:
    """Pick only the deps_outputs entries this binding actually declares
    a dependency on, so cross-talk between unrelated SimStates can't
    leak via overlapping field names."""
    declared = _parse_json(getattr(binding, 'depends_on_json', '[]') or '[]', [])
    if not isinstance(declared, list):
        return {}
    return {cls: deps_outputs[cls] for cls in declared if cls in deps_outputs}


def _extract_final_context(trace) -> Dict[str, Any]:
    """Read the variables dict from the trace's last step's
    context_after, unwrapping each entry. InstanceContextSnapshot
    stores variables as `{name, type, value, sourceStateName}` wrapped
    records; the runner needs the raw values, otherwise a wrapped
    dict gets written to the new *SimState row instead of a number."""
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
        # Unwrap the snapshot's record shape.
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
) -> Dict[str, Any]:
    """Build the kwargs dict for a new `*SimState` row constructor.
    Picks keys from context that match the class's declared field
    names, then stamps the row's identity fields (name, run ref, step,
    time)."""
    typing_obj = manager.objectTypingDict.get(cls_name)
    field_names = set()
    if typing_obj is not None:
        # The typing object's polyTypedVarsDict has one entry per declared
        # field. Fall back to kwDefaultParams when the dict isn't ready.
        ptv_dict = getattr(typing_obj, 'polyTypedVarsDict', {}) or {}
        field_names.update(ptv_dict.keys())
        if not field_names:
            field_names.update(getattr(typing_obj, 'kwDefaultParams', []) or [])

    out: Dict[str, Any] = {}
    for k, v in context.items():
        if not field_names or k in field_names:
            out[k] = v

    # Identity / always-set fields. Overwrite whatever the solution may
    # have placed in them — the runner is authoritative for these.
    out['name'] = _row_name_for(cls_name, run, step)
    out['simulation_run_ref'] = getattr(run, 'name', '')
    out['step'] = step
    out['time'] = round(time_value, 6)
    return out


def _row_name_for(cls_name: str, run, step: int) -> str:
    """Composite-name convention matching the precomputed seed:
    `<run>-<role>-<step>` where role is a lower-case slug derived from
    the class name (PendulumBobSimState → 'bob'). Stable + unique
    across all participating SimState classes for one run."""
    role = cls_name
    for tail in ('SimState', 'State'):
        if role.endswith(tail):
            role = role[: -len(tail)]
            break
    # Snake-case the leading class-name (PendulumBob → pendulum-bob).
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
    """For an idempotent re-step: if a row with the same name (or matching
    run + step composite key) already exists, drop it from the table."""
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
    """Instantiate via the typing-recorded class. The @treeObjectInit
    decorator on every *SimState handles table insertion and DB write."""
    typing_obj = manager.objectTypingDict.get(cls_name)
    if typing_obj is None:
        raise RuntimeError(f"Class '{cls_name}' not registered in objectTypingDict.")
    cls = getattr(typing_obj, 'classDefinition', None)
    if cls is None:
        # Fallback — pull a sample existing row's class.
        table = manager.objectTables.get(cls_name, {}) or {}
        for inst in table.values():
            cls = inst.__class__
            break
    if cls is None:
        raise RuntimeError(f"Cannot resolve constructor for class '{cls_name}'.")
    cls(**fields, manager=manager)


def _bump_run_counters(run, target_step: int) -> None:
    """Move last_recorded_step forward (never backward — re-stepping an
    earlier step is allowed but doesn't roll the counter back) and
    increment recorded_steps when this is a new high-water mark."""
    last = int(getattr(run, 'last_recorded_step', 0) or 0)
    if target_step > last:
        run.last_recorded_step = target_step
        try:
            run.recorded_steps = int(getattr(run, 'recorded_steps', 0) or 0) + 1
        except (TypeError, ValueError):
            run.recorded_steps = 1


def _detect_step_role(solution_data: Dict[str, Any]) -> str:
    """Determine the simStepRole declared by a step solution's entry
    state. Returns one of:
        'simStepComplete' | 'simStepPartial' | 'simStepComposition'

    Raises ValueError if the solution has no SimulationStateStep entry
    state, or if that entry state has no simStepRole declared, or if
    the declared role is unknown. The runner is authoritative for what
    a step solution looks like; mis-pointed bindings should fail loudly
    rather than silently degrading to a default mode.
    """
    if not isinstance(solution_data, dict):
        raise ValueError(
            "Solution data is not a dict; cannot detect simStepRole."
        )
    # Solutions store their state graph under `stateInstances` (the
    # canonical key the engine reads from); `states` is the no-code
    # editor's in-memory shorthand and isn't what gets persisted.
    states = solution_data.get('stateInstances') or solution_data.get('states') or []
    if not isinstance(states, list):
        raise ValueError(
            "Solution `stateInstances` is not a list."
        )
    valid_roles = (
        'simStepComplete', 'simStepPartial', 'simStepComposition'
    )
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
        "Step solution has no SimulationStateStep entry state — "
        "is this binding pointing at the wrong SolutionDefinition?"
    )


def _apply_step_contributions(
    baseline: Dict[str, Any],
    contributions: List[Dict[str, Any]],
    target_class: str,
    warnings: List[str],
) -> Dict[str, Any]:
    """Apply a sequence of SimStepContribution payloads onto a baseline
    context dict, producing the merged next-step field map.

    Each contribution has shape:
        {
          'targetClass': 'PendulumBobSimState',  # filter
          'fieldDeltas': {
            '<fieldName>': {'value': <resolved>, 'op': 'add'|...},
            ...
          },
        }

    Ops applied in ARRIVAL ORDER (which the caller has already sorted
    by binding `order_index`):
        set : merged[f] = value
        add : merged[f] = (merged[f] or 0) + value
        mul : merged[f] = (merged[f] or 0) * value
        min : merged[f] = min(merged[f], value)   (skip if merged[f] None)
        max : merged[f] = max(merged[f], value)

    Contributions whose targetClass doesn't match are silently
    skipped — a single graph CAN emit cross-class payloads, but those
    are aggregated by the SimulationRunner under the OTHER class's
    group, not here. We surface a warning so the analyst can see it
    happened.
    """
    merged: Dict[str, Any] = dict(baseline)
    for c in contributions:
        if not isinstance(c, dict):
            continue
        c_target = c.get('targetClass') or ''
        if c_target and c_target != target_class:
            warnings.append(
                f"SimStepContribution targets class '{c_target}' but was "
                f"emitted under class '{target_class}' group — ignoring "
                f"(cross-class contribution routing is not yet implemented)."
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
