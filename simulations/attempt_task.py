"""
@cross-cutting
@module simulations.attempt_task
@tags @xc:bindings

PURE solution-search attempts — one candidate executed with NO manager,
so attempts can run in parallel workers (processes / Dask) without ever
touching the process-singleton manager or its in-memory objectTables
(the non-negotiable constraint from DISTRIBUTED_COMPUTE_PLAN.md).

Two halves:

  * `build_attempt_spec(manager, stage, sim_def, candidate_params)` —
    runs IN-PROCESS, walking the real manager ONCE to collect everything
    an attempt needs as plain picklable data: the participating classes'
    field lists / defaults / save rules, the step-solution graphs +
    roles, every Matrix/Equation/MatrixEquation DEFINITION row (by-name
    lookup tables for the engine), the gate graph, dt and target steps.
    Definitions only — never state rows.

  * `execute_attempt_pure(spec)` — runs ANYWHERE (a worker process, a
    Dask worker, or in-process for the serial fallback): builds a
    minimal shim manager exposing only the definition lookup tables,
    then mirrors the runner's step loop (baseline compose → engine per
    solution role → contribution merge → field projection) using the
    runner's own pure helpers, accumulating rows as plain dicts. The
    stage gate evaluates over the final flattened context. Returns a
    plain result dict; NEVER raises.

Scope note: COUPLINGS are out of scope for pure attempts — a coupled
simulation needs live cross-run reads through the real manager. The
search orchestrator falls back to serial for coupled sims (the material
condensation space, like most first-principles spaces, is uncoupled).
Pure attempts also skip the initial-conditions validator (search
candidates vary PARAMETERS, not initial conditions).

@consumers
  - simulations.multi_scale_search (parallel execution path)
  - simulations.execution_backend (the worker function)
@see /OVERLAP_MAP.md
"""

import inspect
import json
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

# Definition tables the engine + matrix executors look up by name.
_DEFINITION_TABLES = (
    'SolutionDefinition',
    'MatrixEquationDefinition',
    'MatrixDefinition',
    'EquationDefinition',
)

# Definition-row attributes worth carrying into the spec (superset of what
# the executors read; unknown attrs are simply absent on the shim rows).
_DEFINITION_FIELDS = (
    'name', 'description', 'definition', 'operation_json', 'operands_json',
    'latex', 'tags', 'rows', 'cols', 'values_json', 'kind', 'source_class',
    'function_name', 'target_runtime',
)


def build_attempt_spec(
    manager,
    stage: Dict[str, Any],
    sim_def,
    candidate_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Collect one attempt's full execution context as plain data.
    For a batch, call `build_attempt_base` once and vary the params."""
    base = build_attempt_base(manager, stage, sim_def)
    merged = dict(base['baseParams'])
    merged.update(candidate_params or {})
    spec = dict(base)
    spec['params'] = merged
    return spec


def build_attempt_base(manager, stage: Dict[str, Any], sim_def) -> Dict[str, Any]:
    """The candidate-independent part of an attempt spec (built once per
    search batch, in-process, against the real manager)."""
    from simulations.simulation_runner import (
        _effective_field_save_rules,
        _parse_json,
    )
    from simulations.multi_scale_search import _target_steps

    sim_ref = getattr(sim_def, 'name', '')
    search_cfg = stage.get('search') or {}

    # Participating classes: field lists, defaults, merged save rules.
    participating = [
        c for c in _parse_json(
            getattr(sim_def, 'participating_sim_state_classes_json', '') or '[]',
            [],
        ) if isinstance(c, str)
    ]
    classes: Dict[str, Dict[str, Any]] = {}
    for cls_name in participating:
        typing_obj = manager.objectTypingDict.get(cls_name)
        cls = getattr(typing_obj, 'classDefinition', None) if typing_obj else None
        fields: List[str] = []
        if typing_obj is not None:
            fields = list((getattr(typing_obj, 'polyTypedVarsDict', {}) or {}).keys())
        ctor_defaults: Dict[str, Any] = {}
        if cls is not None:
            if not fields:
                fields = [p for p in inspect.signature(cls.__init__).parameters
                          if p not in ('self', 'manager')]
            for pname, p in inspect.signature(cls.__init__).parameters.items():
                if pname in ('self', 'manager') or p.default is inspect.Parameter.empty:
                    continue
                ctor_defaults[pname] = p.default
        classes[cls_name] = {
            'fields': fields,
            'constructorDefaults': ctor_defaults,
            'initialDefaults': dict(
                getattr(cls, 'default_initial_field_values', {}) or {}),
            'saveRules': _effective_field_save_rules(
                manager, sim_def, None, cls_name),
        }

    # Step solutions for this sim def (same filter the runner applies).
    solutions: Dict[str, List[Dict[str, Any]]] = {c: [] for c in participating}
    table = manager.objectTables.get('SimulationExecutionSolution', {}) or {}
    for s in table.values():
        if getattr(s, 'simulation_definition_ref', '') != sim_ref:
            continue
        if not getattr(s, 'enabled', True):
            continue
        cls = getattr(s, 'sim_state_class_name', '') or ''
        if cls not in solutions:
            continue
        solutions[cls].append({
            'name': getattr(s, 'name', ''),
            'order_index': int(getattr(s, 'order_index', 0) or 0),
            'depends_on': _parse_json(
                getattr(s, 'depends_on_json', '[]') or '[]', []),
            'solution_definition_ref':
                getattr(s, 'solution_definition_ref', '') or '',
        })
    for cls in solutions:
        solutions[cls].sort(key=lambda r: (r['order_index'], r['name']))

    # Definition lookup tables for the shim manager (plain dicts).
    definitions: Dict[str, List[Dict[str, Any]]] = {}
    for table_name in _DEFINITION_TABLES:
        rows = []
        for inst in (manager.objectTables.get(table_name, {}) or {}).values():
            row = {}
            for f in _DEFINITION_FIELDS:
                if hasattr(inst, f):
                    row[f] = getattr(inst, f)
            if row.get('name'):
                rows.append(row)
        definitions[table_name] = rows

    gate = stage.get('gate') or {}
    return {
        'simRef': sim_ref,
        'dt': float(getattr(sim_def, 'time_step_seconds', 0.01) or 0.01),
        'targetSteps': _target_steps(search_cfg, sim_def),
        'participating': participating,
        'classes': classes,
        'solutions': solutions,
        'definitions': definitions,
        'simIcOverrides': _parse_json(
            getattr(sim_def, 'initial_conditions_overrides_json', '{}') or '{}',
            {},
        ),
        'baseParams': _parse_json(
            getattr(sim_def, 'parameters_json', '{}') or '{}', {}),
        'gateSolutionRef': gate.get('solutionRef') or '',
        'gateFailReason': gate.get('failReason') or '',
        'params': {},  # filled per candidate by build_attempt_spec
    }


# ---------------------------------------------------------------------------
# The pure worker function
# ---------------------------------------------------------------------------


def execute_attempt_pure(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Run one attempt from a spec, manager-free. Returns
    {steps, rowsByClass, gateComplete, gateReason, derivedValues, error}
    — plain data, never raises."""
    try:
        return _execute_attempt(spec)
    except Exception as exc:  # noqa: BLE001 — a worker must report, not die
        return {
            'steps': 0, 'rowsByClass': {}, 'gateComplete': False,
            'gateReason': '', 'derivedValues': None,
            'error': f'{type(exc).__name__}: {exc}',
        }


def _shim_manager(definitions: Dict[str, List[Dict[str, Any]]]):
    """The minimal manager the engine needs: objectTables holding ONLY
    the by-name definition rows (as attribute objects)."""
    tables: Dict[str, Dict[str, Any]] = {}
    for table_name, rows in (definitions or {}).items():
        tables[table_name] = {
            f'{table_name}-{i}': SimpleNamespace(**row)
            for i, row in enumerate(rows)
        }
    return SimpleNamespace(objectTables=tables, objectTypingDict={})


def _execute_attempt(spec: Dict[str, Any]) -> Dict[str, Any]:
    # Runner pure helpers — importable without a real manager.
    from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine
    from polariNoCode.stepping import StepConfig
    from simulations.simulation_runner import (
        _apply_step_contributions,
        _compose_instance_fields,
        _detect_step_role,
        _extract_final_context,
        _field_persists_at_step,
        _topo_sort_classes,
    )

    manager = _shim_manager(spec.get('definitions') or {})
    engine = SolutionExecutionEngine(manager=manager)
    step_cfg = StepConfig(mode='step', record_context=True)

    participating: List[str] = list(spec.get('participating') or [])
    classes: Dict[str, Dict[str, Any]] = spec.get('classes') or {}
    params: Dict[str, Any] = dict(spec.get('params') or {})
    dt = float(spec.get('dt') or 0.01)
    target_steps = int(spec.get('targetSteps') or 1)

    # Solution graphs by name (from the shim's SolutionDefinition rows).
    graphs: Dict[str, Optional[Dict]] = {}
    for row in (spec.get('definitions') or {}).get('SolutionDefinition', []):
        raw = row.get('definition')
        try:
            graphs[row['name']] = raw if isinstance(raw, dict) else json.loads(raw)
        except (ValueError, TypeError):
            graphs[row['name']] = None

    # Topo order — reuse the runner's sorter over shim solution rows.
    solutions_ns = {
        cls: [SimpleNamespace(depends_on_json=json.dumps(s['depends_on']))
              for s in sols]
        for cls, sols in (spec.get('solutions') or {}).items()
    }
    ordered = _topo_sort_classes(participating, solutions_ns)
    if ordered is None:
        return _result(0, {}, False, '', None,
                       'Cycle in cross-class dependencies.')

    # Step 0 — initial conditions (class defaults + sim overrides). No
    # validator in the pure path (candidates vary params, not ICs).
    sim_ic = spec.get('simIcOverrides') or {}
    rows: Dict[str, Dict[str, Any]] = {}
    for cls_name in ordered:
        meta = classes.get(cls_name) or {}
        initial = dict(meta.get('initialDefaults') or {})
        cls_over = sim_ic.get(cls_name) if isinstance(sim_ic, dict) else None
        if isinstance(cls_over, dict):
            initial.update(cls_over)
        rows[cls_name] = initial

    # Steps 1..target — the runner's loop, distilled to its pure core.
    for step in range(1, target_steps + 1):
        time_value = step * dt
        deps_outputs: Dict[str, Dict[str, Any]] = {}
        new_rows: Dict[str, Dict[str, Any]] = {}
        for cls_name in ordered:
            sols = (spec.get('solutions') or {}).get(cls_name) or []
            if not sols:
                continue
            meta = classes.get(cls_name) or {}
            baseline = _compose_instance_fields(
                prev_row=rows.get(cls_name) or {},
                params=params,
                deps_outputs=deps_outputs,
                dt=dt,
                time_value=time_value,
                step=step,
            )

            partials, compositions, completes = [], [], []
            for s in sols:
                sdata = graphs.get(s['solution_definition_ref'])
                if sdata is None:
                    return _result(step - 1, rows, False, '', None,
                                   f"missing solution graph "
                                   f"'{s['solution_definition_ref']}'")
                role = _detect_step_role(sdata)
                {'simStepPartial': partials,
                 'simStepComposition': compositions,
                 'simStepComplete': completes}[role].append((s, sdata))

            warnings: List[str] = []
            if partials:
                contributions: List[Dict[str, Any]] = []
                for s, sdata in partials:
                    trace = engine.execute(
                        solution_data=sdata, input_params={}, config=step_cfg,
                        target_runtime='python_backend',
                        instance_fields=dict(baseline))
                    if trace.status != 'completed':
                        return _result(step - 1, rows, False, '', None,
                                       f"partial '{s['name']}' failed: "
                                       f"{getattr(trace, 'error_summary', '')}")
                    emitted = _extract_final_context(trace).get(
                        '_step_contributions') or []
                    if isinstance(emitted, list):
                        contributions.extend(emitted)
                merged = _apply_step_contributions(
                    baseline, contributions, cls_name, warnings)
                if compositions:
                    comp_fields = dict(merged)
                    comp_fields['_step_contributions'] = contributions
                    trace = engine.execute(
                        solution_data=compositions[0][1], input_params={},
                        config=step_cfg, target_runtime='python_backend',
                        instance_fields=comp_fields)
                    if trace.status != 'completed':
                        return _result(step - 1, rows, False, '', None,
                                       'composition failed: '
                                       f"{getattr(trace, 'error_summary', '')}")
                    merged.update(_extract_final_context(trace))
                context = merged
            else:
                context = dict(baseline)
                for s, sdata in completes:
                    trace = engine.execute(
                        solution_data=sdata, input_params={}, config=step_cfg,
                        target_runtime='python_backend',
                        instance_fields=dict(context))
                    if trace.status != 'completed':
                        return _result(step - 1, rows, False, '', None,
                                       f"solution '{s['name']}' failed: "
                                       f"{getattr(trace, 'error_summary', '')}")
                    context.update(_extract_final_context(trace))

            deps_outputs[cls_name] = context
            new_rows[cls_name] = _project_pure(context, meta, step)
        rows.update(new_rows)

    # Gate over the flattened final results.
    gate_ref = spec.get('gateSolutionRef') or ''
    if not gate_ref:
        return _result(target_steps, rows, target_steps > 0, '', None, None)
    gate_graph = graphs.get(gate_ref)
    if gate_graph is None:
        return _result(target_steps, rows, False, '', None,
                       f"gate solution '{gate_ref}' not found in spec")

    flat: Dict[str, Any] = {}
    for k, v in params.items():
        flat[f'params.{k}'] = v
    for cls_name, row in rows.items():
        for k, v in row.items():
            flat[f'{cls_name}.{k}'] = v
    flat['run.last_recorded_step'] = target_steps
    flat['run.status'] = 'running'
    flat['participating_classes'] = participating

    trace = engine.execute(
        solution_data=gate_graph, input_params={}, config=step_cfg,
        target_runtime='python_backend', instance_fields=flat)
    if trace.status != 'completed':
        return _result(target_steps, rows, False, '', None,
                       f"gate failed: {getattr(trace, 'error_summary', '')}")

    from simulations.multi_scale_stages import GATE_PASS_OUTCOMES, _truthy_numeric
    final = _extract_final_context(trace)
    outcome = (str(final.get('outcome') or '')).strip().lower()
    complete = (outcome in GATE_PASS_OUTCOMES if outcome
                else _truthy_numeric(final.get('complete')))
    derived = final.get('derivedValues')
    if not isinstance(derived, dict):
        derived = {k: v for k, v in final.items()
                   if k not in ('outcome', 'reason')}
    reason = str(final.get('reason') or '').strip()
    if not complete and not reason:
        reason = (spec.get('gateFailReason')
                  or 'The condition evaluated as not met (complete=0).')
    return _result(target_steps, rows, complete, reason, derived, None)


def _project_pure(context: Dict[str, Any], meta: Dict[str, Any],
                  step: int) -> Dict[str, Any]:
    """Mirror _project_context_onto_class for a plain-dict row: keep real
    class fields whose save rule persists at this step; missing fields
    fall back to constructor defaults (the derivable-reset semantics)."""
    from simulations.simulation_runner import _field_persists_at_step
    fields = set(meta.get('fields') or [])
    rules = meta.get('saveRules') or {}
    row = dict(meta.get('constructorDefaults') or {})
    for k, v in context.items():
        if fields and k not in fields:
            continue
        rule = rules.get(k, {'policy': 'core', 'interval': 0})
        if not _field_persists_at_step(rule, step):
            continue
        row[k] = v
    return row


def _result(steps, rows, complete, reason, derived, error):
    return {
        'steps': int(steps),
        'rowsByClass': {c: dict(r) for c, r in (rows or {}).items()},
        'gateComplete': bool(complete),
        'gateReason': reason or '',
        'derivedValues': derived,
        'error': error,
    }
