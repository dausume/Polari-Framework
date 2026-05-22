"""
@cross-cutting
@module simulations.equation_evaluation
@tags @xc:render-shared, @xc:bindings

Pre-evaluation of SimSpaceEvaluationEquation rows during snapshot
compile. Produces one value per recorded step so the frontend scrubber
can switch readouts instantly (no per-tick backend roundtrip).

The pre-evaluation:
  1. Collect SimSpaceEvaluationEquation rows scoped to the SimSpace.
  2. For each, resolve the referenced EquationDefinition (LaTeX +
     operation type + result spec).
  3. Walk every recorded step that all referenced simState classes have
     a row for. For each step:
       a. Build a {symbol: value} bindings dict by resolving each source
          (const / param / simState).
       b. Call equation_executor.execute_equation().
       c. Record (step, time, per-symbol-values, numeric result).
  4. Look up the result SimVariable (if declared) for unit + precision.

Output is embedded in the snapshot response so the viewer can render
the three views without any further backend work.

@consumers
  - simSpace.sim_space_api (calls evaluate_for_snapshot after compile)
@see /OVERLAP_MAP.md
"""

import json
from typing import Any, Dict, List, Optional

import sympy
from sympy.parsing.latex import parse_latex

# Per-process LaTeX-expression cache. `parse_latex` is the dominant cost
# of the snapshot pre-evaluation; re-parsing the same expression for
# every step turns a sub-second pass into a tens-of-seconds blocker.
# The cache is keyed by the raw LaTeX string so equations with the same
# text share a parse regardless of which EquationDefinition row they
# live on.
_LATEX_PARSE_CACHE: Dict[str, Any] = {}


def _parse_latex_cached(latex_expression: str):
    """parse_latex with a process-wide cache. Returns None on parse
    failure so callers can record an error per evaluation instead of
    raising. Sympifies the result if parse_latex returns a string."""
    if not latex_expression:
        return None
    key = latex_expression.strip()
    if key in _LATEX_PARSE_CACHE:
        return _LATEX_PARSE_CACHE[key]
    try:
        expr = parse_latex(key.strip('$').strip())
    except Exception:
        _LATEX_PARSE_CACHE[key] = None
        return None
    _LATEX_PARSE_CACHE[key] = expr
    return expr


def collect_evaluation_metadata(
    manager,
    sim_space_row,
    warnings: List[str],
) -> List[Dict]:
    """List the SimSpaceEvaluationEquations scoped to this scene without
    evaluating them. Embedded in the snapshot response so the viewer
    knows which overlays to render and which inputs to feed when it
    issues an on-demand evaluation call (per scrubber stop).

    The shape matches `evaluate_at_step` minus the `perStep` payload —
    every overlay carries the same identity, bindings, anchor, unit, and
    precision the live-evaluation pass would have produced.
    """
    return _collect_evaluations(
        manager, sim_space_row, warnings,
        include_perstep=False, target_step=None,
    )


def evaluate_at_step(
    manager,
    sim_space_row,
    warnings: List[str],
    *,
    step: Optional[int] = None,
    time_value: Optional[float] = None,
) -> List[Dict]:
    """Evaluate every SimSpaceEvaluationEquation scoped to this scene at
    ONE specific simulation step (or time). Returns one perStep entry
    per overlay — the value the viewer's debounced fetch needs to update
    its readouts when the user pauses the scrubber.

    Exactly one of `step` / `time_value` should be provided. When `step`
    is given, the matching row is picked exactly; with `time_value`, the
    latest recorded step whose time is ≤ the requested value is used.
    When neither is set, the earliest recorded step wins (the initial
    frame).
    """
    return _collect_evaluations(
        manager, sim_space_row, warnings,
        include_perstep=True,
        target_step=step,
        target_time=time_value,
    )


def _collect_evaluations(
    manager,
    sim_space_row,
    warnings: List[str],
    *,
    include_perstep: bool,
    target_step: Optional[int] = None,
    target_time: Optional[float] = None,
) -> List[Dict]:
    sim_space_name = getattr(sim_space_row, 'name', '')
    if not sim_space_name:
        return []

    equation_defs = _equation_def_table(manager)
    sim_variables = _sim_variable_table(manager)
    simulation_defs = _simulation_def_table(manager)

    out: List[Dict] = []
    eval_rows = _iter_evaluations_for(manager, sim_space_name)
    eval_rows.sort(key=lambda r: (getattr(r, 'sort_order', 0), getattr(r, 'name', '')))

    for ev_row in eval_rows:
        if not getattr(ev_row, 'enabled', True):
            continue

        equation_ref = getattr(ev_row, 'equation_ref', '') or ''
        eq_def = equation_defs.get(equation_ref) if equation_ref else None
        if eq_def is None:
            warnings.append(
                f"SimSpaceEvaluationEquation '{ev_row.name}' references "
                f"missing EquationDefinition '{equation_ref}'; skipping."
            )
            continue

        eq_config = _parse_json(getattr(eq_def, 'definition', '{}') or '{}', {})
        latex_expression = eq_config.get('latexExpression', '') or ''
        operation_type = eq_config.get('operationType', 'evaluate') or 'evaluate'

        bindings_cfg = _parse_json(
            getattr(ev_row, 'variable_bindings_json', '[]') or '[]', []
        )
        if not isinstance(bindings_cfg, list):
            warnings.append(
                f"SimSpaceEvaluationEquation '{ev_row.name}' bindings JSON not a list; skipping."
            )
            continue

        # Look up SimVariable for unit + precision (if declared).
        result_var_ref = getattr(ev_row, 'result_variable_ref', '') or ''
        result_var = sim_variables.get(result_var_ref) if result_var_ref else None
        unit = getattr(result_var, 'unit', '') if result_var is not None else ''
        precision = (
            getattr(result_var, 'precision', 2) if result_var is not None else 2
        )

        # Resolve the SimulationDefinition (for parameters_json).
        sim_def = _resolve_simulation_definition(
            manager, simulation_defs, bindings_cfg,
            evaluation_name=getattr(ev_row, 'name', ''), warnings=warnings,
        )
        params_dict: Dict[str, Any] = {}
        if sim_def is not None:
            params_dict = _parse_json(
                getattr(sim_def, 'parameters_json', '{}') or '{}', {}
            )

        # Group simState bindings by class so we can iterate rows once.
        sim_state_classes = sorted({
            b['source'].get('class', '')
            for b in bindings_cfg
            if isinstance(b, dict) and isinstance(b.get('source'), dict)
            and b['source'].get('kind') == 'simState'
            and b['source'].get('class')
        })
        # Metadata-only pass — the snapshot endpoint never computes
        # values. The viewer computes on-demand when the user stops on
        # a particular time. Skip both LaTeX parse + row scan for this
        # path so the snapshot endpoint stays near-instant.
        if not include_perstep:
            out.append(_build_metadata_entry(
                ev_row=ev_row,
                latex_expression=latex_expression,
                operation_type=operation_type,
                bindings_cfg=bindings_cfg,
                unit=unit, precision=precision,
                result_var_ref=result_var_ref,
                per_step=[],
            ))
            continue

        # Per-evaluation LaTeX parse — only on the on-demand path. The
        # process-wide cache makes repeated stops near-free.
        sympy_expr = (
            _parse_latex_cached(latex_expression)
            if operation_type == 'evaluate' else None
        )

        rows_by_step = _intersect_rows_by_step(
            manager, sim_state_classes, warnings,
            evaluation_name=ev_row.name,
        )

        # On-demand pass — pick ONE row matching the requested step or
        # time. With neither set, use the earliest recorded step (the
        # initial frame). Anything else is the user pausing the scrubber
        # on a specific moment.
        target_rows = _pick_target_row(
            rows_by_step, target_step=target_step, target_time=target_time,
        )

        per_step: List[Dict] = []
        for step, time_value, class_to_row in target_rows:
            symbol_values, resolution_error = _build_symbol_values(
                bindings_cfg, params_dict, class_to_row,
            )
            if resolution_error is not None:
                per_step.append({
                    'step': step,
                    'time': time_value,
                    'values': symbol_values,
                    'result': None,
                    'error': resolution_error,
                })
                continue

            # SymPy's parse_latex strips the leading backslash on Greek
            # symbols (`\omega` → `omega`). The frontend keeps the
            # LaTeX-form symbol for its string-replace views; SymPy needs
            # the stripped form to match free symbols.
            sympy_bindings = {
                _sympy_symbol_key(sym): val
                for sym, val in symbol_values.items()
            }

            if sympy_expr is not None:
                # Fast path: substitute into the pre-parsed expression and
                # numeric-eval. Skips the per-step parse_latex (the
                # dominant cost) and the per-step result-LaTeX render.
                try:
                    substituted = sympy_expr.subs(sympy_bindings)
                    numeric_val = float(substituted.evalf())
                except Exception as exc:
                    per_step.append({
                        'step': step,
                        'time': time_value,
                        'values': symbol_values,
                        'result': None,
                        'error': f'{type(exc).__name__}: {exc}',
                    })
                    continue
                per_step.append({
                    'step': step,
                    'time': time_value,
                    'values': symbol_values,
                    'result': numeric_val,
                })
            else:
                # Fallback for non-`evaluate` operations (or parse
                # failure): use the general executor. This path is
                # intentionally slow — pre-evaluating a per-step
                # derivative/integral over a recorded trajectory isn't
                # the live-readout use case, but the door stays open.
                from polariNoCode.equation_executor import execute_equation
                bounds = eq_config.get('bounds') or None
                options = eq_config.get('options') or {}
                try:
                    result = execute_equation(
                        latex_expression=latex_expression,
                        operation_type=operation_type,
                        variable_bindings=sympy_bindings,
                        bounds=bounds,
                        options=options,
                    )
                except Exception as exc:
                    per_step.append({
                        'step': step, 'time': time_value, 'values': symbol_values,
                        'result': None, 'error': f'{type(exc).__name__}: {exc}',
                    })
                    continue
                if not result.get('success', False):
                    per_step.append({
                        'step': step, 'time': time_value, 'values': symbol_values,
                        'result': None, 'error': result.get('error', 'evaluation failed'),
                    })
                    continue
                per_step.append({
                    'step': step, 'time': time_value, 'values': symbol_values,
                    'result': result.get('result_numeric'),
                    'resultLatex': result.get('result_latex'),
                })

        out.append(_build_metadata_entry(
            ev_row=ev_row,
            latex_expression=latex_expression,
            operation_type=operation_type,
            bindings_cfg=bindings_cfg,
            unit=unit, precision=precision,
            result_var_ref=result_var_ref,
            per_step=per_step,
        ))

    return out


def _build_metadata_entry(
    ev_row,
    latex_expression: str,
    operation_type: str,
    bindings_cfg: List[Dict],
    unit: str,
    precision: int,
    result_var_ref: str,
    per_step: List[Dict],
) -> Dict:
    """Build the shared response shape used by both metadata-only and
    single-step evaluation passes. `perStep` is empty in the metadata
    pass and length-1 in the on-demand pass."""
    return {
        'id': f'SimSpaceEvaluationEquation:{getattr(ev_row, "name", "")}',
        'name': getattr(ev_row, 'name', ''),
        'description': getattr(ev_row, 'description', ''),
        'mathLatex': latex_expression,
        'operationType': operation_type,
        'bindings': [
            {
                'symbol': b.get('symbol', ''),
                'softwareName': b.get('softwareName', '') or b.get('symbol', ''),
                'source': b.get('source') or {},
            }
            for b in bindings_cfg
            if isinstance(b, dict)
        ],
        'unit': unit,
        'precision': precision,
        'resultVariableRef': result_var_ref,
        'anchorKind': getattr(ev_row, 'anchor_kind', 'screen'),
        'anchorData': _parse_json(
            getattr(ev_row, 'anchor_data_json', '{}') or '{}', {}
        ),
        'sortOrder': getattr(ev_row, 'sort_order', 0),
        'perStep': per_step,
    }


def _pick_target_row(
    rows_by_step: List,
    target_step: Optional[int],
    target_time: Optional[float],
) -> List:
    """Pick exactly one (step, time, class_to_row) tuple from the
    intersected row set per the on-demand selector. Falls back to the
    earliest row when no selector is set."""
    if not rows_by_step:
        return []
    if target_step is not None:
        for entry in rows_by_step:
            if entry[0] == target_step:
                return [entry]
        # No exact match — pick the closest step that doesn't exceed it.
        candidates = [e for e in rows_by_step if e[0] <= target_step]
        return [candidates[-1]] if candidates else [rows_by_step[0]]
    if target_time is not None:
        candidates = [e for e in rows_by_step if e[1] <= target_time + 1e-9]
        return [candidates[-1]] if candidates else [rows_by_step[0]]
    return [rows_by_step[0]]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_evaluations_for(manager, sim_space_name: str) -> List:
    table = manager.objectTables.get('SimSpaceEvaluationEquation', {}) or {}
    return [
        r for r in table.values()
        if getattr(r, 'sim_space_ref', '') == sim_space_name
    ]


def _equation_def_table(manager) -> Dict[str, Any]:
    table = manager.objectTables.get('EquationDefinition', {}) or {}
    return {getattr(r, 'name', ''): r for r in table.values()}


def _sim_variable_table(manager) -> Dict[str, Any]:
    table = manager.objectTables.get('SimVariable', {}) or {}
    return {getattr(r, 'name', ''): r for r in table.values()}


def _simulation_def_table(manager) -> Dict[str, Any]:
    table = manager.objectTables.get('SimulationDefinition', {}) or {}
    return {getattr(r, 'name', ''): r for r in table.values()}


def _parse_json(text: str, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def _resolve_simulation_definition(
    manager,
    simulation_defs: Dict[str, Any],
    bindings_cfg: List[Dict],
    evaluation_name: str,
    warnings: List[str],
):
    """Find the SimulationDefinition implied by the bindings — the
    `*SimState` classes referenced declare their `simulation_definition_name`
    as a class-level attribute; we read it off the class object."""
    for b in bindings_cfg:
        if not isinstance(b, dict):
            continue
        src = b.get('source') or {}
        if src.get('kind') != 'simState':
            continue
        class_name = src.get('class', '')
        if not class_name:
            continue
        typing_obj = manager.objectTypingDict.get(class_name)
        if typing_obj is None:
            continue
        # The typing object stores the actual class in `classDefinition` for
        # classes registered via signature analysis; instance-derived typings
        # don't have it, so fall back to a registered table sample's class.
        cls = getattr(typing_obj, 'classDefinition', None)
        if cls is None:
            sample_table = manager.objectTables.get(class_name, {}) or {}
            for inst in sample_table.values():
                cls = inst.__class__
                break
        sim_def_name = getattr(cls, 'simulation_definition_name', '') if cls else ''
        if sim_def_name and sim_def_name in simulation_defs:
            return simulation_defs[sim_def_name]
    warnings.append(
        f"SimSpaceEvaluationEquation '{evaluation_name}' has no simState "
        f"binding pointing to a SimulationDefinition; param-kind bindings "
        f"will resolve to 0."
    )
    return None


def _intersect_rows_by_step(
    manager,
    sim_state_classes: List[str],
    warnings: List[str],
    evaluation_name: str,
) -> List:
    """Find every (step, time, {class: row}) tuple where ALL referenced
    simState classes have a row. Returns an ordered list sorted by step."""
    if not sim_state_classes:
        return []

    per_class_rows: Dict[str, Dict[int, Any]] = {}
    for cls_name in sim_state_classes:
        table = manager.objectTables.get(cls_name, {}) or {}
        per_class_rows[cls_name] = {}
        for inst in table.values():
            step = getattr(inst, 'step', None)
            if step is None:
                continue
            try:
                step_int = int(step)
            except (TypeError, ValueError):
                continue
            per_class_rows[cls_name][step_int] = inst

    if not per_class_rows:
        return []

    # Intersect step sets.
    step_sets = [set(rows.keys()) for rows in per_class_rows.values()]
    if not step_sets:
        return []
    intersected = sorted(set.intersection(*step_sets))
    if not intersected:
        warnings.append(
            f"SimSpaceEvaluationEquation '{evaluation_name}' has no steps "
            f"common to all referenced simState classes."
        )

    out: List = []
    for step in intersected:
        class_to_row = {cls: rows[step] for cls, rows in per_class_rows.items()}
        # Time is read off the first class's row — all simState classes in
        # a coherent simulation should agree on time per step.
        first_row = next(iter(class_to_row.values()))
        time_value = float(getattr(first_row, 'time', 0.0) or 0.0)
        out.append((step, time_value, class_to_row))
    return out


def _build_symbol_values(
    bindings_cfg: List[Dict],
    params_dict: Dict[str, Any],
    class_to_row: Dict[str, Any],
):
    """Resolve every binding's source to a numeric value. Returns
    (values_dict, error_string_or_None). On the first failure, returns
    the partial values_dict and the error message."""
    values: Dict[str, Any] = {}
    for b in bindings_cfg:
        if not isinstance(b, dict):
            continue
        symbol = b.get('symbol', '')
        if not symbol:
            continue
        src = b.get('source') or {}
        kind = src.get('kind', '')
        if kind == 'const':
            values[symbol] = _as_number(src.get('value'))
        elif kind == 'param':
            param_name = src.get('name', '')
            if param_name not in params_dict:
                return values, f"missing param '{param_name}' for symbol '{symbol}'"
            values[symbol] = _as_number(params_dict.get(param_name))
        elif kind == 'simState':
            cls_name = src.get('class', '')
            field = src.get('field', '')
            row = class_to_row.get(cls_name)
            if row is None:
                return values, f"no {cls_name} row available for symbol '{symbol}'"
            if not hasattr(row, field):
                return values, f"{cls_name} has no field '{field}' (symbol '{symbol}')"
            values[symbol] = _as_number(getattr(row, field))
        else:
            return values, f"unknown source kind '{kind}' for symbol '{symbol}'"
    return values, None


def _sympy_symbol_key(symbol: str) -> str:
    """Translate a LaTeX-form symbol to its SymPy free-symbol name.
    `\\omega` → `omega`, `\\theta` → `theta`, plain `m` → `m`. Used only
    when building the bindings dict passed to execute_equation."""
    if symbol.startswith('\\'):
        return symbol[1:]
    return symbol


def _as_number(v: Any) -> Any:
    """Coerce JSON-decoded values into something the executor accepts as
    a numeric binding. Falls through unchanged for arrays/strings (the
    executor handles those for dataseries ops)."""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v)
        except (TypeError, ValueError):
            return v
    return v
