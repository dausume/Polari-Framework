#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Solution Execution Engine for Polari No-Code System

Walks the state graph from the initial state, evaluating operations
at each step, building an ExecutionTrace with full snapshots.

ISOLATION: Deep-clones solution_data before processing.
Original data is never mutated.
"""

import copy
import json
import time
import uuid
import operator
from datetime import datetime, timezone

from polariNoCode.ExecutionTrace.ExecutionTrace import ExecutionTrace
from polariNoCode.ExecutionTrace.ExecutionStepSnapshot import (
    ExecutionStepSnapshot,
    InstanceContextSnapshot,
    ContextDiff,
)
from polariNoCode.stepping import StepConfig, step_checkpoint


# State classes that serve as initial entry points. Each one tags a
# solution with a specific INVOCATION INTENT — generic InitialState,
# backend-only DirectInvocation, frontend FormSubscription, etc.
# `SimulationStateStep` marks solutions authored as one timestep of a
# simulation: the runner expects them to read prev-step *SimState
# fields + params + dt/step, and to terminate at one of:
#   - `SimStepNextState` for simStepComplete / simStepComposition
#     solutions (full next-row producers).
#   - `SimStepContribution` for simStepPartial solutions (sparse
#     field-delta payloads merged by the runner).
# Editor tooling filters on this so the simulation editor only offers
# valid step solutions when wiring a SimulationExecutionSolution row.
INITIAL_STATE_CLASSES = {
    'InitialState', 'DirectInvocation', 'FormSubscription',
    'LogicFlowEntry', 'BackendStateChange',
    'SimulationStateStep',
    # Validator entry — the graph the IC validator / stage-gate flow
    # executes starts here (was authorable in the editor but missing
    # from this set, so those solutions errored with "No initial state
    # found" — the P1 contract fix).
    'InitialConditionsValidatorEntry',
}

# State classes that are terminal (no further traversal)
TERMINAL_STATE_CLASSES = {
    'ReturnStatement', 'ReturnValue',
    # SimStepNextState is the terminator for `simStepComplete` and
    # `simStepComposition` SimulationStateStep solutions — it declares
    # the new *SimState row's field values that the SimulationRunner
    # persists for the current timestep.
    'SimStepNextState',
    # SimStepContribution is the terminator for `simStepPartial` step
    # solutions. Instead of writing the FULL next row, it emits a
    # sparse `{field → {value, op}}` payload into the context's
    # `_step_contributions` list. The SimulationRunner reads that list
    # back out of the trace and either additively merges the payloads
    # (when no SimStepComposition solution is wired) or surfaces them
    # to a SimStepComposition solution's context for explicit
    # composition.
    'SimStepContribution',
    # ValidationResult terminates validator/gate graphs: it binds its
    # configured outcome / reason / derived values into the final
    # context, which validate_initial_conditions and
    # evaluate_stage_gate read back out (P1 — previously authorable
    # but unregistered, so verdicts were silently lost).
    'ValidationResult',
    # EmitEvent terminates event-emitting graphs: the resolved payload
    # lands in the context's `_emitted_events` list (shape below) for
    # the display/event bridge to consume.
    'EmitEvent',
    # EmitFrontendEvent is EmitEvent with channel='frontend' — the
    # execution response carries it out and the client-side display
    # event bus (displayEvents$) dispatches it to subscribers (P4).
    'EmitFrontendEvent',
}

# Sentinel context key EmitEvent appends to. Each entry is
#   { 'name': <event name>, 'payload': {<key>: <resolved value>, ...},
#     'sourceState': <state name>, 'channel': 'backend' | 'frontend' }
# Consumers (the display event bridge, tests, callers of
# _extract_final_context) read the list off the final context. Events
# with channel='frontend' are dispatched on the client's displayEvents$
# bus by the display-solution-runner after execution.
EMITTED_EVENTS_KEY = '_emitted_events'

# Sentinel context keys the FormValidation handler writes:
#   FORM_VALIDATION_KEY  — {fieldName: {'valid': bool, 'errors': [str]}}
#   'form_valid'         — overall bool
#   '_invalid_fields'    — [fieldName, ...] in field order
# StateChangeCommit appends {'className', 'instance', 'fields'} records:
FORM_VALIDATION_KEY = '_form_validation'
COMMITTED_CHANGES_KEY = '_committed_changes'

# State classes whose handler picks the outgoing branch via
# result['branch_taken'] (an index into the node's OUTPUT slots).
# FormValidation differs from ConditionalChain in overflow behavior:
# an unusable branch ENDS traversal instead of falling back to the last
# slot — an invalid form must never proceed down "All Valid".
BRANCHING_STATE_CLASSES = {'ConditionalChain', 'FormValidation'}

# Maximum SolutionInvocation nesting depth. Recursion is ALLOWED (a
# solution may invoke itself — the factorial pattern), so the chain may
# repeat names; this cap is what turns an infinite recursion (missing
# base case) into a plain-language error instead of a hang. 16 levels is
# generous for composed logic while keeping worst-case nested traces
# manageable.
MAX_INVOCATION_DEPTH = 16

# Sentinel context key the SimStepContribution terminator appends to.
# Resolution solutions read this same key to access prior partial
# contributions. The SimulationRunner harvests it after each binding's
# trace completes so it never leaks across bindings.
STEP_CONTRIBUTIONS_KEY = '_step_contributions'

# Comparison operators mapping (supports symbols, snake_case, and camelCase)
COMPARISON_OPS = {
    '==': operator.eq,
    '!=': operator.ne,
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    'equals': operator.eq,
    'notEquals': operator.ne,
    'greaterThan': operator.gt,
    'lessThan': operator.lt,
    'greaterThanOrEqual': operator.ge,
    'lessThanOrEqual': operator.le,
    'not_equals': operator.ne,
    'greater_than': operator.gt,
    'less_than': operator.lt,
    'greater_than_or_equal': operator.ge,
    'less_than_or_equal': operator.le,
    'contains': lambda a, b: b in a if hasattr(a, '__contains__') else False,
    'notContains': lambda a, b: b not in a if hasattr(a, '__contains__') else True,
    'not_contains': lambda a, b: b not in a if hasattr(a, '__contains__') else True,
    'startsWith': lambda a, b: str(a).startswith(str(b)),
    'endsWith': lambda a, b: str(a).endswith(str(b)),
    'isNull': lambda a, b: a is None,
    'isNotNull': lambda a, b: a is not None,
    'isTrue': lambda a, b: bool(a) is True,
    'isFalse': lambda a, b: bool(a) is False,
}

# Arithmetic operators mapping
ARITHMETIC_OPS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
    '**': operator.pow,
    'add': operator.add,
    'subtract': operator.sub,
    'multiply': operator.mul,
    'divide': operator.truediv,
    'modulo': operator.mod,
    'power': operator.pow,
}


def _generate_snapshot_id():
    return f'snap_{uuid.uuid4().hex[:12]}'


def _generate_execution_id():
    return f'exec_{uuid.uuid4().hex[:12]}'


def _resolve_value_source_config(config, context):
    """Resolve a ValueSourceConfig dict to an actual value from the context.

    ValueSourceConfig has:
        sourceType: 'from_input' | 'from_source_object' | 'direct_assignment'
        sourceObjectPath: e.g. 'self.num_a'  (for from_source_object)
        inputVariableName: variable name     (for from_input)
        inputSlotIndex: slot index           (for from_input)
        directValue: literal value           (for direct_assignment)
        directValueType: 'int'|'str'|'bool'|'float' (for direct_assignment)
    """
    if not isinstance(config, dict) or 'sourceType' not in config:
        return config

    source_type = config.get('sourceType', '')

    if source_type == 'from_source_object':
        path = config.get('sourceObjectPath', '')
        return _resolve_context_path(path, context)

    elif source_type == 'from_input':
        var_name = config.get('inputVariableName', '')
        if var_name and var_name in context:
            return context[var_name]
        return None

    elif source_type == 'direct_assignment':
        value = config.get('directValue')
        value_type = config.get('directValueType', 'str')
        if value is None:
            return None
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'bool':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1')
            else:
                return value
        except (ValueError, TypeError):
            return value

    elif source_type == 'from_field':
        # Legacy: field path on instance, e.g. 'self.originalData'
        path = config.get('fieldPath', config.get('sourceObjectPath', ''))
        return _resolve_context_path(path, context)

    elif source_type == 'literal':
        # Legacy: inline literal value
        value = config.get('literalValue', config.get('directValue'))
        if value is None:
            return None
        value_type = config.get('directValueType', config.get('valueType', 'str'))
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'bool':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1')
            else:
                return value
        except (ValueError, TypeError):
            return value

    elif source_type == 'from_latex':
        # Inline LaTeX expression evaluated against the current context.
        # Every free symbol in the expression is resolved by looking up
        # the symbol's name (backslash-stripped) in the context — same
        # convention the simulation pre-eval pass uses. Lets a
        # SimStepNextState node carry per-output math without having to
        # seed a full EquationDefinition for every computation step.
        latex = config.get('latexExpression', '') or ''
        if not latex:
            return None
        return _evaluate_latex_against_context(latex, context)

    elif source_type == 'array':
        # Build a vector/array from a list of element sources. Each element
        # is itself a ValueSourceConfig (or a literal). Enables no-code
        # authoring of vectors, e.g. n = [plane_nx, plane_ny, plane_nz].
        elements = config.get('elements', []) or []
        out = []
        for el in elements:
            if isinstance(el, dict) and 'sourceType' in el:
                out.append(_resolve_value_source_config(el, context))
            else:
                out.append(el)
        return out

    elif source_type == 'element':
        # Extract one component from an array-valued source, e.g. world[0].
        src = config.get('source')
        idx = config.get('index', 0)
        base = _resolve_value_source_config(src, context) if isinstance(src, dict) else src
        try:
            return base[int(idx)]
        except (TypeError, ValueError, IndexError, KeyError):
            return None

    elif source_type == 'json_decode':
        # Parse a JSON-string source into its value. The read half of
        # MATRIX-VALUED STATE FIELDS: a *SimState field like `cells_json`
        # (an N×M matrix serialized per the `*_json` TEXT convention)
        # becomes a nested list that MatrixEquationOperation operands
        # np.asarray directly. Non-string values pass through untouched
        # (already decoded); malformed JSON resolves to None.
        src = config.get('source')
        base = _resolve_value_source_config(src, context) if isinstance(src, dict) else src
        if not isinstance(base, str):
            return base
        try:
            return json.loads(base)
        except (ValueError, TypeError):
            return None

    elif source_type == 'json_encode':
        # Serialize a source's value to a JSON string — the write half of
        # matrix-valued state fields (a computed matrix lands in context as
        # a nested list via .tolist(); this maps it back onto a `*_json`
        # TEXT field in a SimStepNextState output mapping).
        src = config.get('source')
        base = _resolve_value_source_config(src, context) if isinstance(src, dict) else src
        try:
            return json.dumps(base)
        except (ValueError, TypeError):
            return None

    return None


def _evaluate_latex_against_context(latex_expression, context):
    """Parse + numeric-evaluate a LaTeX expression with every free
    symbol resolved from the engine context. Tolerates parse failures
    (returns None).

    Critical detail: SymPy's `parse_latex` treats multi-letter
    identifiers (`alpha`, `dt`, `mass`) as products of single-letter
    symbols (`a*l*p*h*a`, `d*t`, `m*a*s*s`). To keep the no-code
    authoring experience clean — where the user types
    `\\omega + alpha \\cdot dt` and means it — we PRE-SUBSTITUTE every
    multi-letter context key with its numeric value before invoking
    the parser. Single-letter symbols (`m`, `L`, `g`) and Greek
    commands (`\\omega`, `\\theta`) flow through to parse_latex and
    are bound the normal way.

    For full equation operations (derivative, integral, dataseries),
    use CalculusOperation referencing a saved EquationDefinition.
    """
    if not latex_expression:
        return None
    try:
        # Lazy import — keeps the engine module importable in
        # environments without sympy until from_latex is requested.
        from polariNoCode.equation_executor import execute_equation
    except Exception:
        return None

    # Pre-substitute every multi-letter context key (longest first so
    # `omega_new` is substituted before `omega`). We also drop the
    # multi-letter keys into the bindings dict — that handles the
    # Greek-form path (`\theta` → SymPy free symbol `theta` → resolved
    # via bindings['theta']) AND the pre-substitution path (bare
    # `theta` in the source string gets replaced literally) without
    # the two stepping on each other.
    import re
    pre_subbed = latex_expression
    bindings = {}
    keys = sorted(
        [k for k, v in (context or {}).items()
         if isinstance(k, str) and isinstance(v, (int, float))
         and not k.startswith('self.')],
        key=len, reverse=True,
    )
    for k in keys:
        v = context[k]
        bindings[k] = v
        if len(k) >= 2 and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', k):
            # Multi-letter — replace where the name appears bounded
            # by non-word characters so we don't chew the middle of
            # other words (or LaTeX commands like \sin / \mathrm).
            # Excluding `\` in the lookbehind protects `\theta` from
            # having `theta` substituted under it.
            pre_subbed = re.sub(
                rf'(?<![A-Za-z_0-9\\]){re.escape(k)}(?![A-Za-z_0-9])',
                f'({v})', pre_subbed,
            )

    result = execute_equation(
        latex_expression=pre_subbed,
        operation_type='evaluate',
        variable_bindings=bindings,
    )
    if not result.get('success'):
        return None
    numeric = result.get('result_numeric')
    return numeric


def _resolve_context_path(path, context):
    """Resolve a dotted path like 'self.num_a' against the execution context.

    Tries:
      1. Exact match: context['self.num_a']
      2. Strip 'self.' prefix: context['num_a']
    """
    if not path:
        return None

    # Exact match
    if path in context:
        return context[path]

    # Strip 'self.' prefix and try the bare field name
    if path.startswith('self.'):
        bare = path[5:]  # len('self.') == 5
        if bare in context:
            return context[bare]

    return None


def _safe_resolve_value(value_str, context):
    """Safely resolve a value string, checking context for variable references.

    Also handles ValueSourceConfig dicts from the frontend.
    """
    if value_str is None:
        return None

    # Handle ValueSourceConfig dicts from the frontend
    if isinstance(value_str, dict) and 'sourceType' in value_str:
        return _resolve_value_source_config(value_str, context)

    # If it's already a non-string type, return as-is
    if not isinstance(value_str, str):
        return value_str

    stripped = value_str.strip()

    # Check if it's a variable reference in the context
    if stripped in context:
        return context[stripped]

    # Handle 'self.' prefix paths (e.g., 'self.num_a' → look up 'num_a')
    if stripped.startswith('self.'):
        bare = stripped[5:]
        if bare in context:
            return context[bare]

    # Try to parse as a literal
    # Boolean
    if stripped.lower() == 'true':
        return True
    if stripped.lower() == 'false':
        return False
    if stripped.lower() == 'none' or stripped.lower() == 'null':
        return None

    # Number
    try:
        if '.' in stripped and not stripped.startswith('self.'):
            return float(stripped)
        elif '.' not in stripped:
            return int(stripped)
    except (ValueError, TypeError):
        pass

    # JSON
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass

    # String literal (strip quotes if present)
    if (stripped.startswith('"') and stripped.endswith('"')) or \
       (stripped.startswith("'") and stripped.endswith("'")):
        return stripped[1:-1]

    # Return as string
    return stripped


def _evaluate_condition(condition_data, context):
    """Evaluate a conditional expression against the execution context.

    condition_data can be:
    - A dict with 'leftOperand', 'operator', 'rightOperand'
    - A dict with 'conditions' list (for compound conditions)
    - A simple string expression
    """
    if isinstance(condition_data, str):
        # Simple string condition - resolve from context
        val = _safe_resolve_value(condition_data, context)
        return bool(val)

    if not isinstance(condition_data, dict):
        return False

    # Compound condition (AND/OR)
    if 'conditions' in condition_data:
        conditions = condition_data['conditions']
        logical_op = condition_data.get('logicalOperator', 'AND').upper()
        if logical_op == 'OR':
            return any(_evaluate_condition(c, context) for c in conditions)
        else:  # AND
            return all(_evaluate_condition(c, context) for c in conditions)

    # Single condition
    left_str = condition_data.get('leftOperand', condition_data.get('left', ''))
    op_str = condition_data.get('operator', condition_data.get('comparisonOperator', '=='))
    right_str = condition_data.get('rightOperand', condition_data.get('right', ''))

    left_val = _safe_resolve_value(left_str, context)
    right_val = _safe_resolve_value(right_str, context)

    op_func = COMPARISON_OPS.get(op_str, operator.eq)
    try:
        return op_func(left_val, right_val)
    except (TypeError, ValueError):
        return False


DEFAULT_LOOP_BUDGET = 10_000


def _loop_frame_for(loop_stack, state_name):
    """The active frame for this loop node, or None on first entry."""
    for frame in reversed(loop_stack):
        if frame['name'] == state_name:
            return frame
    return None


def _loop_budget(field_values):
    try:
        budget = int(field_values.get('maxIterations') or 0)
    except (TypeError, ValueError):
        budget = 0
    return budget if budget > 0 else DEFAULT_LOOP_BUDGET


def _check_loop_budget(frame, state_name):
    if frame['iterations'] > frame['budget']:
        raise ValueError(
            f"Loop '{state_name}' exceeded its iteration budget "
            f"({frame['budget']}). If this many iterations is intended, "
            f"raise maxIterations on the loop node."
        )


def _coerce_number(value, default):
    """Best-effort numeric coercion for loop bounds (int preferred)."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return value
    try:
        f = float(value)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return default


def _resolve_collection(source_var, field_values, context):
    """Resolve a list source: a context variable name, a
    ValueSourceConfig under 'sourceValue', or a literal."""
    raw = field_values.get('sourceValue')
    if isinstance(raw, dict) and 'sourceType' in raw:
        resolved = _resolve_value_source_config(raw, context)
    elif source_var:
        resolved = _safe_resolve_value(source_var, context)
    else:
        resolved = []
    if isinstance(resolved, tuple):
        resolved = list(resolved)
    return resolved if isinstance(resolved, list) else []


class _scoped_vars:
    """Temporarily bind loop/element variables in the flat context,
    restoring (or removing) them afterwards so element bindings never
    leak into later states."""

    def __init__(self, context, names):
        self.context = context
        self.names = names
        self.saved = {}

    def __enter__(self):
        sentinel = object()
        self._sentinel = sentinel
        for n in self.names:
            self.saved[n] = self.context.get(n, sentinel)

        def set_var(name, value):
            self.context[name] = value
        return set_var

    def __exit__(self, exc_type, exc, tb):
        for n, old in self.saved.items():
            if old is self._sentinel:
                self.context.pop(n, None)
            else:
                self.context[n] = old
        return False


def _collection_operation(context, op, target_var, key, value, state_name):
    """Basic dict/list verbs over a context variable."""
    target = context.get(target_var)
    if op == 'dictSet':
        if not isinstance(target, dict):
            target = {}
            context[target_var] = target
        target[key] = value
        return target
    if op == 'dictGet':
        return target.get(key) if isinstance(target, dict) else None
    if op == 'dictKeys':
        return list(target.keys()) if isinstance(target, dict) else []
    if op == 'dictDelete':
        if isinstance(target, dict):
            target.pop(key, None)
        return target
    if op == 'listAppend':
        if not isinstance(target, list):
            target = []
            context[target_var] = target
        target.append(value)
        return target
    if op == 'listGet':
        try:
            return target[int(key)] if isinstance(target, list) else None
        except (IndexError, TypeError, ValueError):
            return None
    if op == 'listSet':
        if isinstance(target, list):
            try:
                target[int(key)] = value
            except (IndexError, TypeError, ValueError):
                pass
        return target
    if op == 'listLength':
        return len(target) if isinstance(target, (list, dict, str)) else 0
    raise ValueError(
        f"'{state_name}': unknown collection operation {op!r}. Expected "
        f"one of: dictGet, dictSet, dictKeys, dictDelete, listAppend, "
        f"listGet, listSet, listLength."
    )


class SolutionExecutionEngine:
    """
    Walks the state graph from initial state, evaluating operations,
    building an ExecutionTrace with snapshots at each step.

    ISOLATION: Deep-clones solution_data before processing.
    Original data is never mutated.

    Optional `manager` reference is used by handlers that need to look
    up other Polari entities at runtime (e.g. the CalculusOperation
    handler resolves an EquationDefinition by name through
    `manager.objectTables['EquationDefinition']`).
    """

    def __init__(self, manager=None):
        self.manager = manager

    def execute(self, solution_data, input_params, config=None, target_runtime='python_backend', instance_fields=None, _invocation_chain=()):
        """
        Execute a solution by walking its state graph.

        Args:
            solution_data: The solution definition dict (will be deep-cloned)
            input_params: Dict of input parameter values
            config: Optional StepConfig for controlling step behavior
            target_runtime: 'python_backend' or 'typescript_frontend'
            instance_fields: Optional dict of instance field values (merged before input_params)
            _invocation_chain: internal — tuple of solution names already
                on the call stack when this execution is a nested
                SolutionInvocation. Drives the depth guard; external
                callers leave it unset.

        Returns:
            ExecutionTrace with full step snapshots
        """
        if config is None:
            config = StepConfig(mode='step', record_context=True)

        # The invocation chain this execution sits on (self included once
        # the handler pushes the callee). Stored per-execution; nested
        # invocations create a FRESH engine instance, so a caller's chain
        # is never clobbered by its callee.
        self._invocation_chain = tuple(_invocation_chain)
        self._step_config = config

        # ISOLATION: Deep-clone solution_data
        solution_data = copy.deepcopy(solution_data)

        solution_name = solution_data.get('solutionName', 'untitled')
        self._solution_name = solution_name
        execution_id = _generate_execution_id()
        trace = ExecutionTrace(execution_id, solution_name, target_runtime)

        state_instances = solution_data.get('stateInstances', [])
        if not state_instances:
            trace.error('No state instances found in solution')
            return trace

        # ===== DEBUG: dump the state-class chain we're about to walk =====
        # print(f'[ENGINE DEBUG] execute() solution={solution_name!r} '
        #       f'with {len(state_instances)} states', flush=True)
        # for s in state_instances:
        #     print(f'[ENGINE DEBUG]   state {s.get("stateName")!r}: '
        #           f'stateClass={s.get("stateClass")!r} '
        #           f'boundObjectClass={s.get("boundObjectClass")!r}', flush=True)
        # ================================================================

        # Sort states by index
        sorted_states = sorted(state_instances, key=lambda s: s.get('index', 0))

        # Build states_by_name map
        states_by_name = {}
        for s in sorted_states:
            name = s.get('stateName')
            if name:
                states_by_name[name] = s

        # Find initial state
        initial_state = None
        for s in sorted_states:
            cls = s.get('boundObjectClass', s.get('stateClass', ''))
            if cls in INITIAL_STATE_CLASSES:
                initial_state = s
                break

        if not initial_state:
            trace.error('No initial state found in solution')
            return trace

        # Initialize execution context: instance fields first, then input params (params take precedence)
        context = {}
        if instance_fields:
            context.update(instance_fields)
        if input_params:
            context.update(input_params)

        # Walk the state graph.
        #
        # LOOP FRAMES: real iteration lives here, not in hand-wired
        # back-edges. When a loop node (ForLoop/WhileLoop/ForEachLoop)
        # decides to iterate, execution enters its BODY (output slot 0);
        # when the body path ends — either at a node with no outgoing
        # connector (auto-return) or via an explicit connector back to
        # the loop node — the loop node re-evaluates. When the loop is
        # done it exits via output slot 1 ("done"). BreakStatement jumps
        # to the innermost loop's done-slot; ContinueStatement jumps back
        # to the innermost loop node. Each frame carries an iteration
        # budget (node's maxIterations, default 10 000) with a plain-
        # language error on exhaustion.
        #
        # BOUNDED-BUT-LARGE, honestly: the global visit cap below is a
        # backstop against runaway graphs, not a semantic limit. True
        # unbounded execution is intentionally not offered — with
        # per-loop budgets + this backstop the engine is Turing complete
        # for any computation that fits the budgets, which is the same
        # practical deal every real machine makes with finite memory.
        current_state = initial_state
        step_index = 0
        max_steps = 200_000  # Global visit backstop (see note above)
        loop_stack = []      # Innermost frame last
        trace_collector = []

        try:
            while current_state is not None and step_index < max_steps:
                state_name = current_state.get('stateName', f'Step_{step_index}')
                state_class = current_state.get('boundObjectClass', current_state.get('stateClass', ''))
                field_values = current_state.get('boundObjectFieldValues', {})

                # Capture context_before snapshot
                context_before = InstanceContextSnapshot(
                    state_name=state_name,
                    solution_name=solution_name,
                    execution_id=execution_id,
                    variables=self._snapshot_variables(context, state_name),
                )

                # Step checkpoint
                step_checkpoint(step_index, state_name, state_class, context, config, trace_collector)

                start_time = time.time()
                execution_result = None
                execution_error = None
                log_output = []
                branch_taken = None
                branch_label = None
                status = 'completed'

                # Evaluate the state's operation
                loop_action = None
                child_execution = None
                try:
                    result = self._evaluate_state(
                        state_class, field_values, context, state_name, log_output,
                        loop_stack=loop_stack,
                    )
                    execution_result = result.get('result')
                    branch_taken = result.get('branch_taken')
                    branch_label = result.get('branch_label')
                    loop_action = result.get('loop_action')
                    child_execution = result.get('child_execution')
                except Exception as e:
                    execution_error = str(e)
                    status = 'errored'

                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                # Capture context_after snapshot
                context_after = InstanceContextSnapshot(
                    state_name=state_name,
                    solution_name=solution_name,
                    execution_id=execution_id,
                    variables=self._snapshot_variables(context, state_name),
                )

                # Compute context diff
                context_diff = ContextDiff.compute(context_before, context_after)

                # Build ExecutionStepSnapshot
                snapshot = ExecutionStepSnapshot(
                    snapshot_id=_generate_snapshot_id(),
                    step_index=step_index,
                    state_name=state_name,
                    state_class_name=state_class,
                    context_before=context_before,
                    context_after=context_after,
                    context_diff=context_diff,
                    status=status,
                    execution_result=execution_result,
                    execution_error=execution_error,
                    start_time=datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                    end_time=datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat(),
                    duration_ms=round(duration_ms, 3),
                    branch_taken=branch_taken,
                    branch_label=branch_label,
                    log_output=log_output,
                    child_execution=child_execution,
                )
                trace.add_step(snapshot)

                # If errored, stop execution
                if status == 'errored':
                    trace.error(execution_error)
                    return trace

                # Check if terminal state
                if state_class in TERMINAL_STATE_CLASSES:
                    trace.complete(execution_result)
                    return trace

                # Determine next state. Loop actions route explicitly;
                # everything else follows connectors as before.
                if loop_action == 'body':
                    # Enter the loop body (slot 0). An empty body loops
                    # straight back to the loop node (budget-guarded).
                    next_state = self._slot_target(
                        current_state, states_by_name, 0
                    ) or current_state
                elif loop_action == 'exit':
                    # The loop handler already popped its frame; leave
                    # via the done-slot (slot 1). A missing done
                    # connector falls through to the dead-end rule so
                    # an enclosing loop resumes (or execution ends).
                    next_state = self._slot_target(
                        current_state, states_by_name, 1
                    )
                elif loop_action == 'break':
                    frame = loop_stack.pop()
                    loop_node = states_by_name.get(frame['name'])
                    next_state = (
                        self._slot_target(loop_node, states_by_name, 1)
                        if loop_node else None
                    )
                elif loop_action == 'continue':
                    next_state = states_by_name.get(loop_stack[-1]['name'])
                else:
                    next_state = self._get_next_state(
                        current_state, states_by_name, context, branch_taken
                    )

                # Dead-end rule: a body path that simply ends returns to
                # the innermost active loop for its next iteration.
                if next_state is None and loop_stack:
                    next_state = states_by_name.get(loop_stack[-1]['name'])

                current_state = next_state
                step_index += 1

            # If we hit max_steps, mark as completed (or errored)
            if step_index >= max_steps:
                trace.error(f'Execution exceeded maximum step limit ({max_steps})')
            else:
                trace.complete()

        except Exception as e:
            trace.error(str(e))

        return trace

    # ------------------------------------------------------------------
    # SolutionInvocation — solution-as-state composition
    # ------------------------------------------------------------------

    def _invoke_solution(self, field_values, context, state_name, log_output):
        """Run another SolutionDefinition as a nested execution and bind
        its outputs back into the caller's context.

        Node config:
            solutionRef:    name of the callee SolutionDefinition
            inputMappings:  [{param, valueSource}] — caller-side value
                            sources resolved into the callee's inputs
            resultBindings: [{output, contextVar}] — callee outputs bound
                            into caller context. output 'return' is the
                            callee's ReturnValue; any other name reads
                            the callee's final context (so terminals
                            like ValidationResult expose named outputs).

        Returns the child-execution SUMMARY dict for the trace snapshot.
        Raises ValueError with plain-language messages on: missing
        callee, contract violations, depth exhaustion, child failure.
        """
        callee_name = (field_values.get('solutionRef')
                       or field_values.get('solutionName') or '').strip()
        if not callee_name:
            raise ValueError(
                f"SolutionInvocation '{state_name}': no solutionRef "
                f"configured — pick which solution to invoke."
            )

        # Depth guard. Recursion is allowed; this is what turns a missing
        # base case into a readable error instead of a hang.
        chain = getattr(self, '_invocation_chain', ())
        caller_name = getattr(self, '_solution_name', '(caller)')
        if len(chain) >= MAX_INVOCATION_DEPTH:
            path = ' -> '.join(chain + (caller_name, callee_name))
            raise ValueError(
                f"SolutionInvocation '{state_name}': call nesting exceeded "
                f"{MAX_INVOCATION_DEPTH} levels ({path}). If this is "
                f"recursion, make sure the base case is reachable; if the "
                f"nesting is intentional, flatten some of the chain."
            )

        row = self._load_solution_row(callee_name)
        if row is None:
            raise ValueError(
                f"SolutionInvocation '{state_name}': solution "
                f"'{callee_name}' was not found."
            )
        try:
            child_data = json.loads(getattr(row, 'definition', '{}') or '{}')
        except (ValueError, TypeError):
            child_data = None
        if not isinstance(child_data, dict) or not child_data.get('stateInstances'):
            raise ValueError(
                f"SolutionInvocation '{state_name}': solution "
                f"'{callee_name}' has no executable definition."
            )

        # Resolve the caller-side inputs.
        child_inputs = {}
        for m in (field_values.get('inputMappings') or []):
            if not isinstance(m, dict):
                continue
            param = (m.get('param') or '').strip()
            if not param:
                continue
            src = m.get('valueSource')
            child_inputs[param] = (
                _resolve_value_source_config(src, context)
                if isinstance(src, dict) else src
            )

        # Contract validation (only what the callee declares).
        try:
            contract = json.loads(getattr(row, 'contract_json', '{}') or '{}')
        except (ValueError, TypeError):
            contract = {}
        declared_inputs = contract.get('inputs') or []
        missing = [
            i.get('name') for i in declared_inputs
            if isinstance(i, dict) and i.get('required')
            and child_inputs.get(i.get('name')) is None
        ]
        if missing:
            desc = contract.get('description') or ''
            raise ValueError(
                f"SolutionInvocation '{state_name}': solution "
                f"'{callee_name}' requires input(s) {missing} that were "
                f"not provided (or resolved to nothing). "
                + (f"It describes itself as: {desc}" if desc else
                   "Map each required input in the invocation's settings.")
            )
        if declared_inputs:
            declared_names = {
                i.get('name') for i in declared_inputs if isinstance(i, dict)
            }
            for extra in set(child_inputs) - declared_names:
                log_output.append(
                    f"[{state_name}] note: input '{extra}' is not in "
                    f"'{callee_name}'s contract — passed through anyway."
                )

        rights = (contract.get('executionRights') or 'invoker')
        # Declarative for now (see SolutionDefinition.contract_json) —
        # recorded in the trace so intent is visible before enforcement
        # arrives with the auth/authz node family.
        log_output.append(
            f"[{state_name}] invoking '{callee_name}' "
            f"(depth {len(chain) + 1}, rights: {rights}) with "
            f"{sorted(child_inputs.keys())}"
        )

        # Fresh engine, fresh context (ONLY the mapped inputs) — the
        # abstraction boundary. The callee never sees caller variables.
        child_engine = SolutionExecutionEngine(manager=self.manager)
        child_runtime = getattr(row, 'target_runtime', '') or 'python_backend'
        child_trace = child_engine.execute(
            child_data,
            input_params=dict(child_inputs),
            config=getattr(self, '_step_config', None),
            target_runtime=child_runtime,
            _invocation_chain=chain + (caller_name,),
        )

        if child_trace.status != 'completed':
            raise ValueError(
                f"SolutionInvocation '{state_name}': solution "
                f"'{callee_name}' failed: "
                f"{child_trace.error_summary or 'unknown engine error'}"
            )

        # Bind outputs back into the CALLER's context.
        child_outputs = self._extract_child_outputs(child_trace)
        for b in (field_values.get('resultBindings') or []):
            if not isinstance(b, dict):
                continue
            output = (b.get('output') or 'return').strip()
            var = (b.get('contextVar') or '').strip()
            if not var:
                continue
            if output == 'return':
                value = child_trace.final_return_value
            elif output in child_outputs:
                value = child_outputs[output]
            else:
                log_output.append(
                    f"[{state_name}] note: '{callee_name}' produced no "
                    f"output named '{output}' — '{var}' set to None. "
                    f"Available: {sorted(child_outputs.keys())[:12]}"
                )
                value = None
            context[var] = value
            log_output.append(f'[{state_name}] {var} = {value!r} (from {output})')

        log_output.append(
            f"[{state_name}] '{callee_name}' completed in "
            f"{len(child_trace.steps)} steps"
        )

        summary = {
            'executionId': child_trace.execution_id,
            'solutionName': callee_name,
            'status': child_trace.status,
            'stepCount': len(child_trace.steps),
        }
        try:
            json.dumps(child_trace.final_return_value)
            summary['finalReturnValue'] = child_trace.final_return_value
        except (TypeError, ValueError):
            summary['finalReturnValue'] = str(child_trace.final_return_value)
        return summary

    def _load_solution_row(self, solution_name):
        """The callee SolutionDefinition row, by name (same lookup the
        gate/validator flows use)."""
        if self.manager is None or not hasattr(self.manager, 'objectTables'):
            return None
        table = self.manager.objectTables.get('SolutionDefinition', {}) or {}
        for inst in table.values():
            if getattr(inst, 'name', '') == solution_name:
                return inst
        return None

    @staticmethod
    def _extract_child_outputs(child_trace):
        """The callee's final context as {name: value} — its NAMED
        outputs. Mirrors the unwrap the SimulationRunner uses on traces
        (variables stored as {name, type, value, ...} records)."""
        steps = getattr(child_trace, 'steps', None) or []
        if not steps:
            return {}
        context_after = getattr(steps[-1], 'context_after', None)
        variables = getattr(context_after, 'variables', None)
        if not isinstance(variables, dict):
            return {}
        out = {}
        for k, v in variables.items():
            if isinstance(v, dict) and 'value' in v and 'name' in v:
                out[k] = v.get('value')
            else:
                out[k] = v
        return out

    def _snapshot_variables(self, context, state_name):
        """Create a serializable snapshot of the current context variables."""
        variables = {}
        for name, value in context.items():
            try:
                # Ensure value is JSON-serializable
                json.dumps(value, default=str)
                snap_value = value
            except (TypeError, ValueError):
                snap_value = str(value)

            variables[name] = {
                'name': name,
                'type': type(value).__name__ if value is not None else 'NoneType',
                'value': snap_value,
                'sourceStateName': state_name,
            }
        return variables

    def _evaluate_state(self, state_class, field_values, context, state_name,
                        log_output, loop_stack=None):
        """
        Evaluate a state's operation, modifying context as needed.

        Returns a dict with:
            'result': the execution result value (if any)
            'branch_taken': which branch was taken (for conditionals)
            'branch_label': human-readable label for the branch
            'loop_action': 'body' | 'exit' | 'break' | 'continue' when a
                loop/break/continue node routed execution (None otherwise)
        """
        if loop_stack is None:
            loop_stack = []
        # ===== TOP-LEVEL DEBUG =====
        # print(f'[ENGINE DEBUG] _evaluate_state: state_name={state_name!r} state_class={state_class!r}', flush=True)
        # print(f'[ENGINE DEBUG]   field_values keys={list(field_values.keys())}', flush=True)
        # ============================

        result = {'result': None, 'branch_taken': None, 'branch_label': None,
                  'loop_action': None}

        if state_class in ('InitialState', 'DirectInvocation', 'SimulationStateStep',
                           'FormSubscription', 'LogicFlowEntry',
                           'BackendStateChange', 'InitialConditionsValidatorEntry'):
            # Entry-point states — input params have already been merged
            # into context by the caller. We log what was supplied so the
            # ExecutionTrace shows the starting state. SimulationStateStep
            # additionally surfaces its declared `simStateClassName` /
            # `expectedFields` for the analyst when reviewing the trace.
            input_params = field_values.get('inputParams', [])
            param_strs = []
            for p in input_params:
                p_name = p.get('name', '?')
                p_val = context.get(p_name, '<not provided>')
                param_strs.append(f'{p_name}={p_val!r}')
            if state_class == 'SimulationStateStep':
                target = field_values.get('simStateClassName', '?')
                expected = field_values.get('expectedFields', []) or []
                supplied = [
                    f'{f}={context.get(f, "<missing>")!r}' for f in expected
                ]
                # `simStepRole` is REQUIRED and selects the runner
                # dispatch mode for this solution:
                #   simStepComplete    → terminates at SimStepNextState;
                #                        one per (sim, class). Closed-form
                #                        full-step solution — no
                #                        contribution merging.
                #   simStepPartial     → terminates at SimStepContribution;
                #                        many per (sim, class). Emits a
                #                        sparse field-delta payload that
                #                        the runner aggregates.
                #   simStepComposition → terminates at SimStepNextState;
                #                        one per (sim, class). Reads
                #                        `_step_contributions` + merged
                #                        baseline to compose the final row
                #                        when additive merge isn't
                #                        expressive enough.
                # Missing/invalid values are a hard error.
                role_raw = field_values.get('simStepRole')
                valid_roles = (
                    'simStepComplete', 'simStepPartial', 'simStepComposition'
                )
                if not isinstance(role_raw, str) or not role_raw.strip():
                    raise ValueError(
                        f"SimulationStateStep '{state_name}': simStepRole is "
                        f"required (one of: {' | '.join(valid_roles)})."
                    )
                role = role_raw.strip()
                if role not in valid_roles:
                    raise ValueError(
                        f"SimulationStateStep '{state_name}': unknown "
                        f"simStepRole={role_raw!r}. Expected one of: "
                        f"{' | '.join(valid_roles)}."
                    )
                result['result'] = (
                    f"Simulation step entry — target={target}, "
                    f"role={role}, expected={len(expected)} fields"
                )
                log_output.append(
                    f'[{state_name}] (SimulationStateStep target={target} role={role}) '
                    f'entering with: {", ".join(supplied) if supplied else "(no expectedFields declared)"}'
                )
            else:
                result['result'] = f'Entry point with {len(input_params)} parameters'
                log_output.append(
                    f'[{state_name}] Entering with params: '
                    f'{", ".join(param_strs) if param_strs else "(none)"}'
                )

        elif state_class == 'VariableAssignment':
            var_name = field_values.get('variableName', '')
            value_str = field_values.get('value', '')

            # Check for ValueSourceConfig in assignmentConfig
            assignment_config = field_values.get('assignmentConfig', {})
            value_source_config = assignment_config.get('valueSource') if assignment_config else None

            if var_name:
                # Prefer resolving from ValueSourceConfig if present
                if value_source_config and isinstance(value_source_config, dict) and 'sourceType' in value_source_config:
                    resolved = _resolve_value_source_config(value_source_config, context)
                else:
                    resolved = _safe_resolve_value(value_str, context)

                context[var_name] = resolved
                # Also store with bare name if self. prefixed
                if var_name.startswith('self.'):
                    context[var_name[5:]] = resolved
                result['result'] = resolved
                log_output.append(f'[{state_name}] {var_name} = {resolved!r} (type: {type(resolved).__name__})')

        elif state_class == 'ConditionalChain':
            # Frontend stores chain data as 'links' with ValueSourceConfig objects;
            # legacy format uses 'conditions'
            links = field_values.get('links', [])
            conditions = field_values.get('conditions', [])
            condition = field_values.get('condition', '')
            default_op = field_values.get('defaultLogicalOperator', 'AND').upper()

            if links and len(links) > 0:
                # Evaluate links with ValueSourceConfig support
                # Respect per-link logicalOperator for sequential combination
                link_results = []
                for link in links:
                    link_result = self._evaluate_chain_link(link, context, log_output)
                    link_results.append((link_result, link.get('logicalOperator', default_op).upper()))

                # Combine sequentially using each link's logical operator
                combined = link_results[0][0]
                for i in range(1, len(link_results)):
                    result_val, op = link_results[i]
                    # The operator on link[i] says how to combine link[i-1]'s result with link[i]
                    prev_op = link_results[i - 1][1]  # operator from the previous link
                    if prev_op == 'OR':
                        combined = combined or result_val
                    elif prev_op == 'NOT':
                        combined = combined and (not result_val)
                    elif prev_op == 'XOR':
                        combined = combined ^ result_val
                    else:  # AND (default)
                        combined = combined and result_val

                if combined:
                    result['branch_taken'] = 0
                    result['branch_label'] = 'true'
                else:
                    result['branch_taken'] = 1
                    result['branch_label'] = 'false'
                log_output.append(f'[{state_name}] Condition result: {combined} -> branch {result["branch_label"]}')

            elif conditions and len(conditions) > 0:
                # Legacy: evaluate each condition in the chain
                for i, cond in enumerate(conditions):
                    if _evaluate_condition(cond, context):
                        result['branch_taken'] = i
                        result['branch_label'] = cond.get('label', f'Branch {i}')
                        break
                else:
                    # No condition matched - take else branch
                    result['branch_taken'] = len(conditions)
                    result['branch_label'] = 'else'
                log_output.append(f'[{state_name}] Condition result -> branch {result["branch_label"]}')
            elif condition:
                # Simple if/else
                if _evaluate_condition(condition, context):
                    result['branch_taken'] = 0
                    result['branch_label'] = 'true'
                else:
                    result['branch_taken'] = 1
                    result['branch_label'] = 'false'
                log_output.append(f'[{state_name}] Condition result -> branch {result["branch_label"]}')
            else:
                result['branch_taken'] = 0
                result['branch_label'] = 'default'
                log_output.append(f'[{state_name}] No condition defined -> branch default')

        elif state_class == 'ForLoop':
            # Real indexed loop. Editor fields: iteratorVariable/
            # startValue/endValue/stepValue/maxIterations (legacy names
            # iterator/start/end/step accepted). Range semantics match
            # Python's range(): end is EXCLUSIVE; negative steps count
            # down. Body = output slot 0, done = output slot 1.
            iterator = (field_values.get('iteratorVariable')
                        or field_values.get('iterator') or 'i')
            frame = _loop_frame_for(loop_stack, state_name)
            if frame is None:
                start = _coerce_number(_safe_resolve_value(
                    field_values.get('startValue',
                                     field_values.get('start', 0)), context), 0)
                end = _coerce_number(_safe_resolve_value(
                    field_values.get('endValue',
                                     field_values.get('end', 10)), context), 10)
                step = _coerce_number(_safe_resolve_value(
                    field_values.get('stepValue',
                                     field_values.get('step', 1)), context), 1)
                if step == 0:
                    raise ValueError(
                        f"Loop '{state_name}': step is 0 — the loop would "
                        f"never advance. Use a positive or negative step."
                    )
                frame = {
                    'name': state_name, 'kind': 'for', 'current': start,
                    'end': end, 'step': step, 'iterations': 0,
                    'budget': _loop_budget(field_values),
                }
                loop_stack.append(frame)
            else:
                frame['current'] += frame['step']
            cont = ((frame['step'] > 0 and frame['current'] < frame['end'])
                    or (frame['step'] < 0 and frame['current'] > frame['end']))
            if cont:
                frame['iterations'] += 1
                _check_loop_budget(frame, state_name)
                context[iterator] = frame['current']
                result['loop_action'] = 'body'
                result['result'] = {'loop': 'for', 'iterator': iterator,
                                    'value': frame['current'],
                                    'iteration': frame['iterations']}
                log_output.append(
                    f'[{state_name}] iteration {frame["iterations"]}: '
                    f'{iterator} = {frame["current"]}'
                )
            else:
                loop_stack.remove(frame)
                result['loop_action'] = 'exit'
                result['result'] = {'loop': 'for', 'completed': True,
                                    'iterations': frame['iterations']}
                log_output.append(
                    f'[{state_name}] done after {frame["iterations"]} iterations'
                )

        elif state_class == 'WhileLoop':
            # Real condition loop. `condition` accepts a ConditionalChain
            # dict (links), a legacy condition dict, or a plain string
            # like "x < 10". Body = slot 0, done = slot 1.
            condition = field_values.get('condition', '')
            frame = _loop_frame_for(loop_stack, state_name)
            if frame is None:
                frame = {'name': state_name, 'kind': 'while',
                         'iterations': 0, 'budget': _loop_budget(field_values)}
                loop_stack.append(frame)
            cond_ok = self._evaluate_condition_any(condition, context, log_output)
            if cond_ok:
                frame['iterations'] += 1
                _check_loop_budget(frame, state_name)
                result['loop_action'] = 'body'
                result['result'] = {'loop': 'while',
                                    'iteration': frame['iterations']}
                log_output.append(
                    f'[{state_name}] condition true — iteration '
                    f'{frame["iterations"]}'
                )
            else:
                loop_stack.remove(frame)
                result['loop_action'] = 'exit'
                result['result'] = {'loop': 'while', 'completed': True,
                                    'iterations': frame['iterations']}
                log_output.append(
                    f'[{state_name}] condition false — done after '
                    f'{frame["iterations"]} iterations'
                )

        elif state_class == 'ForEachLoop':
            # Real collection loop. `collection` may be a context variable
            # name, a ValueSourceConfig, or a JSON literal; the element
            # lands in `item` (editor: itemVariable) and its position in
            # `indexVariable` (default '<item>_index').
            item = (field_values.get('itemVariable')
                    or field_values.get('item') or 'item')
            index_var = field_values.get('indexVariable') or f'{item}_index'
            frame = _loop_frame_for(loop_stack, state_name)
            if frame is None:
                raw = field_values.get('collection', '[]')
                if isinstance(raw, dict) and 'sourceType' in raw:
                    collection = _resolve_value_source_config(raw, context)
                else:
                    collection = _safe_resolve_value(raw, context)
                if not isinstance(collection, (list, tuple)):
                    log_output.append(
                        f'[{state_name}] collection is not a list '
                        f'({type(collection).__name__}) — treating as empty.'
                    )
                    collection = []
                frame = {'name': state_name, 'kind': 'foreach',
                         'items': list(collection), 'index': 0,
                         'iterations': 0, 'budget': _loop_budget(field_values)}
                loop_stack.append(frame)
            else:
                frame['index'] += 1
            if frame['index'] < len(frame['items']):
                frame['iterations'] += 1
                _check_loop_budget(frame, state_name)
                context[item] = frame['items'][frame['index']]
                context[index_var] = frame['index']
                result['loop_action'] = 'body'
                result['result'] = {'loop': 'foreach', 'index': frame['index'],
                                    'item': context[item]}
                log_output.append(
                    f'[{state_name}] item {frame["index"] + 1}/'
                    f'{len(frame["items"])}: {item} = {context[item]!r}'
                )
            else:
                loop_stack.remove(frame)
                result['loop_action'] = 'exit'
                result['result'] = {'loop': 'foreach', 'completed': True,
                                    'iterations': frame['iterations']}
                log_output.append(
                    f'[{state_name}] done after {len(frame["items"])} items'
                )

        elif state_class == 'BreakStatement':
            if not loop_stack:
                raise ValueError(
                    f"'{state_name}': Break used outside of a loop — there "
                    f"is no loop to break out of."
                )
            result['loop_action'] = 'break'
            result['result'] = f'break out of {loop_stack[-1]["name"]}'
            log_output.append(
                f'[{state_name}] breaking out of loop '
                f'\'{loop_stack[-1]["name"]}\''
            )

        elif state_class == 'ContinueStatement':
            if not loop_stack:
                raise ValueError(
                    f"'{state_name}': Continue used outside of a loop — "
                    f"there is no loop to continue."
                )
            result['loop_action'] = 'continue'
            result['result'] = f'continue loop {loop_stack[-1]["name"]}'
            log_output.append(
                f'[{state_name}] continuing loop '
                f'\'{loop_stack[-1]["name"]}\''
            )

        elif state_class == 'SolutionInvocation':
            # THE composition primitive: run another SolutionDefinition as
            # a single reusable state (Dustin's "re-wrap a solution into a
            # more generic state"). The callee runs in a FRESH context
            # seeded ONLY with the mapped inputs — no caller-context
            # leakage; the contract is the whole interface. Outputs bind
            # back per resultBindings. Recursion is allowed; depth is
            # guarded (MAX_INVOCATION_DEPTH) so a missing base case fails
            # in plain language instead of hanging.
            summary = self._invoke_solution(
                field_values, context, state_name, log_output,
            )
            result['result'] = (
                f"{summary['solutionName']} -> {summary['status']} "
                f"({summary['stepCount']} steps)"
            )
            result['child_execution'] = summary

        elif state_class == 'AwaitBackendCall':
            # The explicit cross-runtime bridge. From a CLIENT-executing
            # graph this node ships one named solution to the backend
            # engine over HTTP. Here — already ON the backend — the
            # "backend call" is simply an in-process invocation with the
            # same input-mapping / result-binding semantics, so a graph
            # authored for the client runs unchanged on the backend.
            normalized = dict(field_values)
            normalized['solutionRef'] = (
                field_values.get('solutionRef')
                or field_values.get('solutionName')
                or field_values.get('backendSolution') or ''
            )
            log_output.append(
                f'[{state_name}] backend-side await: running '
                f'\'{normalized["solutionRef"]}\' in-process (no bridge '
                f'needed — this engine IS the backend)'
            )
            summary = self._invoke_solution(
                normalized, context, state_name, log_output,
            )
            result['result'] = (
                f"{summary['solutionName']} -> {summary['status']} "
                f"({summary['stepCount']} steps)"
            )
            result['child_execution'] = summary

        elif state_class == 'FunctionCall':
            # RETIRED (authoring-only): superseded by SolutionInvocation,
            # which actually invokes another solution with a contract.
            # Kept recognizable so legacy graphs don't error, but it does
            # nothing and says so in the trace.
            func_name = field_values.get('functionName', '')
            result_var = field_values.get('resultVariableName', '')
            if result_var:
                context[result_var] = None  # Placeholder
            result['result'] = f'FunctionCall is not executable (use SolutionInvocation)'
            log_output.append(
                f'[{state_name}] FunctionCall "{func_name}" is an authoring-only '
                f'legacy node and did NOT run. Use a SolutionInvocation node to '
                f'call solution logic; {result_var or "(no result var)"} was set '
                f'to None.'
            )

        elif state_class in ('ReturnValue', 'ReturnStatement'):
            return_value_str = field_values.get('returnValue', '')
            return_source = field_values.get('returnValueSource', 'literal')

            # If returnValueSource is a ValueSourceConfig dict, resolve it directly
            if isinstance(return_source, dict) and 'sourceType' in return_source:
                resolved = _resolve_value_source_config(return_source, context)
            elif return_source == 'variable' or (not return_value_str and field_values.get('variableName')):
                var_name = field_values.get('variableName', return_value_str)
                resolved = context.get(var_name, _safe_resolve_value(return_value_str, context))
            else:
                resolved = _safe_resolve_value(return_value_str, context)

            result['result'] = resolved
            log_output.append(f'[{state_name}] Returning: {resolved!r} (type: {type(resolved).__name__})')

        elif state_class == 'LogOutput':
            msg_template = field_values.get('messageTemplate', '')
            # Simple template substitution from context
            msg = msg_template
            for var_name, var_value in context.items():
                msg = msg.replace('{' + var_name + '}', str(var_value))
            log_output.append(msg)
            result['result'] = msg

        elif state_class == 'MathOperation':
            # Resolve operands — supports both ValueSourceConfig dicts and plain strings
            left_raw = field_values.get('leftOperand', field_values.get('left', '0'))
            right_raw = field_values.get('rightOperand', field_values.get('right', '0'))

            left_val = _safe_resolve_value(left_raw, context)
            right_val = _safe_resolve_value(right_raw, context)

            # Resolve operator — frontend sends 'operationType' (e.g. 'add'),
            # legacy sends 'operator' (e.g. '+')
            op_str = field_values.get('operator', field_values.get('operationType', '+'))
            op_symbol = {
                'add': '+', 'subtract': '-', 'multiply': '*', 'divide': '/',
                'modulo': '%', 'power': '**',
            }.get(op_str, op_str)
            arith_func = ARITHMETIC_OPS.get(op_str, operator.add)

            try:
                computed = arith_func(left_val, right_val)
            except (TypeError, ZeroDivisionError) as e:
                computed = None
                log_output.append(f'[{state_name}] MathOperation error: {e}')

            # Determine result variable name — supports 'resultVariable',
            # 'resultFieldPath' (e.g. 'self.sum_result'), and 'resultVariableName'
            result_var = field_values.get('resultVariable', '')
            if not result_var:
                result_var = field_values.get('resultFieldPath', '')
            if not result_var:
                result_var = field_values.get('resultVariableName', '')
            if not result_var:
                result_var = field_values.get('variableName', '')

            if result_var:
                # Store with the original key
                context[result_var] = computed
                # Also store with the bare name (strip 'self.' prefix)
                if result_var.startswith('self.'):
                    context[result_var[5:]] = computed

            result['result'] = computed
            if computed is not None:
                display_var = result_var.replace('self.', '') if result_var.startswith('self.') else result_var
                log_output.append(f'[{state_name}] {display_var} = {left_val!r} {op_symbol} {right_val!r} = {computed!r}')

        elif state_class == 'CalculusOperation':
            # Hosts a saved EquationDefinition. The equation declares each
            # symbol's `defaultSource` (typically a `self.<field>` path on the
            # equation's `source_class`); the host state may override per-
            # symbol via its own `bindings` list. Symbols not overridden fall
            # back to the equation's defaultSource so equations bound to a
            # specific class (e.g. CalcTester) work without per-state wiring.
            equation_name = field_values.get('equationName', '') or field_values.get('equationId', '')
            bindings_list = field_values.get('bindings', []) or []
            result_target = field_values.get('resultTarget', 'result_variable')
            result_field_path = field_values.get('resultFieldPath', '')
            result_var_name = field_values.get('resultVariableName', 'result')

            # ===== DEBUG =====
            # print(f'[CalcOp DEBUG] === Entering state {state_name!r} ===', flush=True)
            # print(f'[CalcOp DEBUG]   equation_name={equation_name!r}', flush=True)
            # print(f'[CalcOp DEBUG]   field_values keys={list(field_values.keys())}', flush=True)
            # print(f'[CalcOp DEBUG]   host bindings_list ({len(bindings_list)}):', flush=True)
            # for b in bindings_list:
            #     print(f'[CalcOp DEBUG]     - {b!r}', flush=True)
            # print(f'[CalcOp DEBUG]   resultTarget={result_target!r} resultFieldPath={result_field_path!r} resultVar={result_var_name!r}', flush=True)
            # print(f'[CalcOp DEBUG]   context keys={list(context.keys())}', flush=True)
            # for k in list(context.keys()):
            #     print(f'[CalcOp DEBUG]     context[{k!r}] = {context[k]!r}', flush=True)
            # =================

            # Map symbol → host-supplied source (overrides equation default).
            host_overrides = {}
            for b in bindings_list:
                if not isinstance(b, dict):
                    continue
                sym = (b.get('symbol') or '').strip()
                src = b.get('source')
                if sym and src is not None:
                    host_overrides[sym] = src
            # print(f'[CalcOp DEBUG]   host_overrides keys={list(host_overrides.keys())}', flush=True)

            # Locate the EquationDefinition by name via the manager's object table.
            eq_definition = None
            try:
                if self.manager is not None and hasattr(self.manager, 'objectTables'):
                    eq_table = self.manager.objectTables.get('EquationDefinition')
                    # print(f'[CalcOp DEBUG]   EquationDefinition table type={type(eq_table).__name__}', flush=True)
                    if eq_table is not None:
                        # names_seen = []
                        for inst_id, inst in eq_table.items():
                            nm = getattr(inst, 'name', None)
                            # names_seen.append(nm)
                            if nm == equation_name:
                                eq_definition = inst
                                break
                        # print(f'[CalcOp DEBUG]   names in table: {names_seen}', flush=True)
                    # else:
                    #     print('[CalcOp DEBUG]   EquationDefinition table is None', flush=True)
            except Exception as e:
                log_output.append(f'[{state_name}] CalculusOperation: error locating equation `{equation_name}`: {e}')
                # print(f'[CalcOp DEBUG]   EXCEPTION locating equation: {e}', flush=True)

            computed = None
            if eq_definition is None:
                log_output.append(f'[{state_name}] CalculusOperation: equation `{equation_name}` not found.')
                # print(f'[CalcOp DEBUG]   eq_definition is None — equation NOT FOUND', flush=True)
            else:
                # print(f'[CalcOp DEBUG]   eq_definition found: id={getattr(eq_definition, "id", "?")}', flush=True)
                # Parse the stored definition JSON.
                try:
                    raw = getattr(eq_definition, 'definition', '') or ''
                    eq_config = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except Exception as e:
                    eq_config = {}
                    log_output.append(f'[{state_name}] CalculusOperation: failed to parse equation `{equation_name}`: {e}')

                latex_expression = eq_config.get('latexExpression', '')
                operation_type = eq_config.get('operationType', 'evaluate')
                bounds = eq_config.get('bounds') or None
                options = eq_config.get('options') or {}
                equation_bindings = eq_config.get('variableBindings', []) or []

                # print(f'[CalcOp DEBUG]   latex={latex_expression!r}', flush=True)
                # print(f'[CalcOp DEBUG]   op={operation_type!r} bounds={bounds!r} options={options!r}', flush=True)
                # print(f'[CalcOp DEBUG]   equation_bindings ({len(equation_bindings)}):', flush=True)
                # for eb in equation_bindings:
                #     print(f'[CalcOp DEBUG]     - {eb!r}', flush=True)

                # Build runtime bindings: walk equation-declared symbols, prefer
                # host overrides, fall back to each equation binding's defaultSource.
                runtime_bindings = {}
                for eb in equation_bindings:
                    if not isinstance(eb, dict):
                        continue
                    sym = (eb.get('symbol') or '').strip()
                    if not sym:
                        continue
                    src = host_overrides.get(sym, eb.get('defaultSource'))
                    # print(f'[CalcOp DEBUG]   resolving sym={sym!r} from src={src!r}', flush=True)
                    if src is None:
                        # print(f'[CalcOp DEBUG]     -> src is None, skipping', flush=True)
                        continue
                    try:
                        resolved = _resolve_value_source_config(src, context)
                        runtime_bindings[sym] = resolved
                        # print(f'[CalcOp DEBUG]     -> resolved {sym!r} = {resolved!r}', flush=True)
                    except Exception as e:
                        log_output.append(f'[{state_name}] CalculusOperation: failed to resolve binding `{sym}`: {e}')
                        # print(f'[CalcOp DEBUG]     -> EXCEPTION: {e}', flush=True)

                # Pull in any host-only symbols the equation didn't declare
                # (defensive — usually empty when host matches equation).
                for sym, src in host_overrides.items():
                    if sym in runtime_bindings:
                        continue
                    try:
                        runtime_bindings[sym] = _resolve_value_source_config(src, context)
                    except Exception as e:
                        log_output.append(f'[{state_name}] CalculusOperation: failed to resolve host binding `{sym}`: {e}')

                try:
                    from polariNoCode.equation_executor import execute_equation
                    # print(f'[CalcOp DEBUG]   calling execute_equation('
                    #       f'latex={latex_expression!r}, op={operation_type!r}, '
                    #       f'bindings={runtime_bindings!r}, bounds={bounds!r})', flush=True)
                    exec_result = execute_equation(
                        latex_expression=latex_expression,
                        operation_type=operation_type,
                        variable_bindings=runtime_bindings,
                        bounds=bounds,
                        options=options,
                    )
                    # print(f'[CalcOp DEBUG]   execute_equation returned: {exec_result!r}', flush=True)
                    if exec_result.get('success'):
                        # Prefer the numeric result when present — most
                        # simulation-step math (theta, omega, energy, …)
                        # is numeric and downstream states need a number,
                        # not the string-form of one. Fall back to the
                        # LaTeX result for symbolic operations
                        # (derivative / integral / simplify) where the
                        # output IS the expression itself.
                        numeric_val = exec_result.get('result_numeric')
                        if numeric_val is not None:
                            computed = numeric_val
                        else:
                            computed = exec_result.get('result_latex')
                        log_output.append(
                            f'[{state_name}] CalculusOperation `{equation_name}` ('
                            f'{", ".join(f"{k}={v!r}" for k, v in runtime_bindings.items())}) '
                            f'→ {computed!r}'
                        )
                    else:
                        err = exec_result.get('error') or 'unknown error'
                        log_output.append(f'[{state_name}] CalculusOperation `{equation_name}` failed: {err}')
                except Exception as e:
                    log_output.append(f'[{state_name}] CalculusOperation `{equation_name}` exception: {e}')

            # Store the computed value into the context using the resultTarget
            # convention (mirrors MathOperation).
            if result_target == 'solution_field' and result_field_path:
                # Path like 'self.result_expression' or 'result_expression'
                key = result_field_path
                if key.startswith('self.'):
                    bare = key[5:]
                    context[key] = computed
                    context[bare] = computed
                else:
                    context[key] = computed
                    context[f'self.{key}'] = computed
            else:
                if result_var_name:
                    context[result_var_name] = computed

            result['result'] = computed

        elif state_class == 'MatrixEquationOperation':
            # Hosts a saved MatrixEquationDefinition — makes the matrix /
            # vector engine callable from no-code. Operand symbols are bound
            # from the solution context (scalars OR arrays, via the 'array'
            # source kind); the result (an array or scalar) is stored back
            # into the context, where downstream states extract components
            # via the 'element' source kind.
            meq_name = field_values.get('matrixEquationName', '') or field_values.get('matrixEquationRef', '')
            operand_bindings = field_values.get('operandBindings', []) or []
            result_target = field_values.get('resultTarget', 'result_variable')
            result_field_path = field_values.get('resultFieldPath', '')
            result_var_name = field_values.get('resultVariableName', 'result')

            binding_values = {}
            for b in operand_bindings:
                if not isinstance(b, dict):
                    continue
                sym = (b.get('symbol') or '').strip()
                src = b.get('source')
                if not sym or src is None:
                    continue
                try:
                    binding_values[sym] = _resolve_value_source_config(src, context)
                except Exception as e:
                    log_output.append(f'[{state_name}] MatrixEquationOperation: failed to resolve operand `{sym}`: {e}')

            meq_def = None
            try:
                if self.manager is not None and hasattr(self.manager, 'objectTables'):
                    tbl = self.manager.objectTables.get('MatrixEquationDefinition')
                    if tbl is not None:
                        for _id, inst in tbl.items():
                            if getattr(inst, 'name', None) == meq_name:
                                meq_def = inst
                                break
            except Exception as e:
                log_output.append(f'[{state_name}] MatrixEquationOperation: error locating `{meq_name}`: {e}')

            computed = None
            if meq_def is None:
                log_output.append(f'[{state_name}] MatrixEquationOperation: matrix equation `{meq_name}` not found.')
            else:
                try:
                    from matrices.matrix_equation_executor import evaluate_equation as _eval_meq
                    arr = _eval_meq(meq_def, binding_values=binding_values, manager=self.manager)
                    if hasattr(arr, 'ndim') and arr.ndim == 0:
                        computed = arr.item()
                    elif hasattr(arr, 'tolist'):
                        computed = arr.tolist()
                    else:
                        computed = arr
                    log_output.append(
                        f'[{state_name}] MatrixEquationOperation `{meq_name}` ('
                        f'{", ".join(f"{k}={v!r}" for k, v in binding_values.items())}) → {computed!r}'
                    )
                except Exception as e:
                    log_output.append(f'[{state_name}] MatrixEquationOperation `{meq_name}` exception: {e}')

            if result_target == 'solution_field' and result_field_path:
                key = result_field_path
                if key.startswith('self.'):
                    bare = key[5:]
                    context[key] = computed
                    context[bare] = computed
                else:
                    context[key] = computed
                    context[f'self.{key}'] = computed
            else:
                if result_var_name:
                    context[result_var_name] = computed

            result['result'] = computed

        elif state_class == 'EngineModelOperation':
            # Hosts a configured FEM/DFT model definition (msci-15) —
            # makes the physics/chemistry engines callable from no-code,
            # so custom logic can compute a model's inputs, run a real
            # solve, and keep computing on its outputs.
            #
            # inputBindings feed the model's stageDerived bindings: each
            # {'symbol', 'source'} resolves through the solution context
            # and lands in the model's stage_context under `symbol` —
            # symbols must therefore match the model's stageDerived keys
            # ('<stage>.<key>'). Models bound purely by value/objectRef
            # need no inputBindings at all.
            #
            # Outputs: every result key is written into the context as
            # 'model.<key>'; resultKeyMap entries {'resultKey',
            # 'contextVar'} additionally copy chosen keys to friendly
            # variables; the shared resultTarget convention stores the
            # whole result dict like every other operation.
            model_ref = (field_values.get('modelRef', '')
                         or field_values.get('modelName', ''))
            input_bindings = field_values.get('inputBindings', []) or []
            result_key_map = field_values.get('resultKeyMap', []) or []
            result_target = field_values.get('resultTarget',
                                             'result_variable')
            result_field_path = field_values.get('resultFieldPath', '')
            result_var_name = field_values.get('resultVariableName',
                                               'model_result')

            stage_context = {}
            for b in input_bindings:
                if not isinstance(b, dict):
                    continue
                sym = (b.get('symbol') or '').strip()
                src = b.get('source')
                if not sym or src is None:
                    continue
                try:
                    stage_context[sym] = _resolve_value_source_config(
                        src, context)
                except Exception as e:
                    log_output.append(
                        f'[{state_name}] EngineModelOperation: failed '
                        f'to resolve input `{sym}`: {e}')

            computed = None
            if not model_ref:
                log_output.append(
                    f'[{state_name}] EngineModelOperation: no modelRef '
                    'configured.')
            else:
                try:
                    from materialsScience.model_execution import (
                        execute_model,
                    )
                    report = execute_model(
                        self.manager, model_ref,
                        stage_context=stage_context or None)
                except Exception as e:
                    report = {'ok': False, 'error': str(e)}
                if report.get('ok'):
                    computed = report.get('result', {})
                    for k, v in computed.items():
                        context[f'model.{k}'] = v
                    for m in result_key_map:
                        if not isinstance(m, dict):
                            continue
                        rk = m.get('resultKey', '')
                        cv = m.get('contextVar', '')
                        if rk and cv:
                            if rk in computed:
                                context[cv] = computed[rk]
                            else:
                                log_output.append(
                                    f'[{state_name}] EngineModelOperation'
                                    f': result has no key `{rk}` '
                                    f'(available: '
                                    f'{sorted(computed)[:8]})')
                    log_output.append(
                        f'[{state_name}] EngineModelOperation '
                        f'`{model_ref}` via {report.get("engine", "?")}'
                        f' → {sorted(computed)[:6]}')
                else:
                    bits = [report.get('error', 'engine refused')]
                    for refusal in report.get('refusals', []) or []:
                        bits.append(refusal.get('error', ''))
                    log_output.append(
                        f'[{state_name}] EngineModelOperation '
                        f'`{model_ref}` refused: '
                        f'{"; ".join(b for b in bits if b)}')

            if result_target == 'solution_field' and result_field_path:
                key = result_field_path
                if key.startswith('self.'):
                    context[key] = computed
                    context[key[5:]] = computed
                else:
                    context[key] = computed
                    context[f'self.{key}'] = computed
            else:
                if result_var_name:
                    context[result_var_name] = computed

            result['result'] = computed

        elif state_class == 'SimStepContribution':
            # Terminator for `simStepPartial` SimulationStateStep
            # solutions. Emits a sparse `{fieldName → {value, op}}`
            # payload into the per-trace `_step_contributions` list.
            # The SimulationRunner harvests this list after the
            # binding's trace completes, then either:
            #   - aggregates additively (when no simStepComposition
            #     solution is wired for the target class), or
            #   - re-injects the union of all partial payloads into a
            #     simStepComposition solution's context under the same
            #     sentinel key, letting the composition graph express
            #     any non-additive merge it wants.
            #
            # Schema mirrors SimStepNextState's `outputMappings` so the
            # editor can share the same row-builder UI, with one extra
            # `op` field per mapping:
            #   {
            #     'simStateClassName': 'PendulumBobSimState',
            #     'outputMappings': [
            #       {'outputFieldName': 'theta',
            #        'valueSource': {...},
            #        'op': 'add'},   # set | add | mul | min | max
            #       ...
            #     ],
            #   }
            target_class = field_values.get('simStateClassName', '') or ''
            output_mappings = field_values.get('outputMappings', []) or []
            field_deltas: Dict[str, Any] = {}
            written: list = []
            for mapping in output_mappings:
                if not isinstance(mapping, dict):
                    continue
                field_name = mapping.get('outputFieldName', '')
                if not field_name:
                    continue
                value_source = mapping.get('valueSource')
                if isinstance(value_source, dict) and 'sourceType' in value_source:
                    resolved = _resolve_value_source_config(value_source, context)
                else:
                    resolved = _safe_resolve_value(
                        mapping.get('literal', ''), context
                    )
                op_raw = mapping.get('op')
                if not isinstance(op_raw, str) or not op_raw.strip():
                    raise ValueError(
                        f"SimStepContribution '{state_name}' mapping for "
                        f"'{field_name}': `op` is required "
                        f"(set | add | mul | min | max)."
                    )
                op = op_raw.strip().lower()
                if op not in ('set', 'add', 'mul', 'min', 'max'):
                    raise ValueError(
                        f"SimStepContribution '{state_name}' mapping for "
                        f"'{field_name}': unknown op={op_raw!r}. "
                        f"Expected one of: set | add | mul | min | max."
                    )
                field_deltas[field_name] = {'value': resolved, 'op': op}
                written.append(f'{field_name}{op}={resolved!r}')

            contribution = {
                'targetClass': target_class,
                'sourceState': state_name,
                'fieldDeltas': field_deltas,
            }
            existing = context.get(STEP_CONTRIBUTIONS_KEY)
            if not isinstance(existing, list):
                existing = []
            existing.append(contribution)
            context[STEP_CONTRIBUTIONS_KEY] = existing

            tag = (
                f'SimStepContribution({target_class})'
                if target_class else 'SimStepContribution'
            )
            result['result'] = (
                f'{tag} → {len(written)} deltas: {", ".join(written)}'
                if written else f'{tag}: no outputMappings'
            )
            log_output.append(f'[{state_name}] {result["result"]}')

        elif state_class == 'SimStepNextState':
            # SimStepNextState — terminator for `simStepComplete` and
            # `simStepComposition` SimulationStateStep solutions.
            # Declares the new *SimState row's field values for this
            # timestep. Carries an outputMappings list of
            # {outputFieldName, valueSource} pairs; each valueSource is
            # resolved against the current context and written back so
            # the SimulationRunner can project the final context onto a
            # new row.
            #
            # `simStateClassName` must match the entry's
            # SimulationStateStep declaration — the editor pairs them
            # so the analyst can tell at a glance which class a
            # solution is producing.
            output_mappings = field_values.get('outputMappings', []) or []
            target_class = field_values.get('simStateClassName', '')
            written: list = []
            for mapping in output_mappings:
                if not isinstance(mapping, dict):
                    continue
                field_name = mapping.get('outputFieldName', '')
                value_source = mapping.get('valueSource')
                if not field_name:
                    continue
                if isinstance(value_source, dict) and 'sourceType' in value_source:
                    resolved = _resolve_value_source_config(value_source, context)
                else:
                    # Allow a literal-string fallback (rare).
                    resolved = _safe_resolve_value(
                        mapping.get('literal', ''), context
                    )
                context[field_name] = resolved
                context[f'self.{field_name}'] = resolved
                written.append(f'{field_name}={resolved!r}')
            tag = (
                f'SimStepNextState({target_class})'
                if target_class else 'SimStepNextState'
            )
            result['result'] = (
                f'{tag} → {len(written)} fields: {", ".join(written)}'
                if written else f'{tag}: no outputMappings'
            )
            log_output.append(f'[{state_name}] {result["result"]}')

        elif state_class == 'FilterList':
            # Real filtering: each element is bound to `itemVariable`
            # (default 'x') and kept when the condition holds. Condition
            # accepts the same shapes WhileLoop does.
            source_var = field_values.get('sourceVariable', '')
            result_var = field_values.get('resultVariable', '')
            item_var = field_values.get('itemVariable', 'x')
            condition = (field_values.get('filterCondition')
                         or field_values.get('condition') or {})
            source = _resolve_collection(source_var, field_values, context)
            kept = []
            with _scoped_vars(context, [item_var]) as set_var:
                for el in source:
                    set_var(item_var, el)
                    if self._evaluate_condition_any(condition, context, None):
                        kept.append(el)
            if result_var:
                context[result_var] = kept
            result['result'] = kept
            log_output.append(
                f'[{state_name}] kept {len(kept)} of {len(source)} items'
                + (f' -> {result_var}' if result_var else '')
            )

        elif state_class == 'MapList':
            # Transform each element: bind to `itemVariable` (default
            # 'x'), evaluate `valueSource` (a ValueSourceConfig — incl.
            # from_latex for real math) or `expression` (simple
            # space-separated "left op right" arithmetic, e.g. "x * x").
            source_var = field_values.get('sourceVariable', '')
            result_var = field_values.get('resultVariable', '')
            item_var = field_values.get('itemVariable', 'x')
            source = _resolve_collection(source_var, field_values, context)
            mapped = []
            with _scoped_vars(context, [item_var]) as set_var:
                for el in source:
                    set_var(item_var, el)
                    mapped.append(self._eval_element_expression(
                        field_values, context, item_var))
            if result_var:
                context[result_var] = mapped
            result['result'] = mapped
            log_output.append(
                f'[{state_name}] mapped {len(mapped)} items'
                + (f' -> {result_var}' if result_var else '')
            )

        elif state_class == 'ReduceList':
            # Fold the list: `accumulatorVariable` (default 'acc') starts
            # at `initialValue`, each element binds to `itemVariable`,
            # and the expression/valueSource computes the next
            # accumulator.
            source_var = field_values.get('sourceVariable', '')
            result_var = field_values.get('resultVariable', '')
            item_var = field_values.get('itemVariable', 'x')
            acc_var = field_values.get('accumulatorVariable', 'acc')
            initial = _safe_resolve_value(
                field_values.get('initialValue', 0), context)
            source = _resolve_collection(source_var, field_values, context)
            acc = initial
            with _scoped_vars(context, [item_var, acc_var]) as set_var:
                for el in source:
                    set_var(item_var, el)
                    set_var(acc_var, acc)
                    acc = self._eval_element_expression(
                        field_values, context, item_var)
            if result_var:
                context[result_var] = acc
            result['result'] = acc
            log_output.append(
                f'[{state_name}] reduced {len(source)} items to {acc!r}'
                + (f' -> {result_var}' if result_var else '')
            )

        elif state_class == 'CollectionOperation':
            # Basic dict/list mutation — the missing collection verbs.
            # operationType: dictGet | dictSet | dictKeys | dictDelete |
            # listAppend | listGet | listSet | listLength.
            op = field_values.get('operationType', '')
            target_var = field_values.get('targetVariable', '')
            key = _safe_resolve_value(field_values.get('key', ''), context)
            raw_value = field_values.get('value', None)
            if isinstance(raw_value, dict) and 'sourceType' in raw_value:
                value = _resolve_value_source_config(raw_value, context)
            else:
                value = _safe_resolve_value(raw_value, context)
            result_var = field_values.get('resultVariable', '')
            out = _collection_operation(
                context, op, target_var, key, value, state_name)
            if result_var:
                context[result_var] = out
            result['result'] = out
            log_output.append(f'[{state_name}] {op} on {target_var!r} -> {out!r}')

        elif state_class == 'ValidationResult':
            # Terminal for validator/gate graphs — binds the verdict into
            # the final context, exactly the contract
            # validate_initial_conditions / evaluate_stage_gate read:
            # outcome ('valid'|'complete'|'pass' passes; numeric
            # `complete` fallback also honored), reason, derivedValues /
            # repairedValues, plus free-form outputMappings.
            def _resolve_flexible(raw):
                if isinstance(raw, dict) and 'sourceType' in raw:
                    return _resolve_value_source_config(raw, context)
                return _safe_resolve_value(raw, context)

            wrote = []
            for key in ('outcome', 'reason', 'complete'):
                if key in field_values:
                    context[key] = _resolve_flexible(field_values[key])
                    wrote.append(key)
            for key in ('derivedValues', 'repairedValues'):
                mapping = field_values.get(key)
                if isinstance(mapping, dict) and 'sourceType' not in mapping:
                    context[key] = {
                        k: _resolve_flexible(v) for k, v in mapping.items()
                    }
                    wrote.append(key)
                elif mapping is not None:
                    context[key] = _resolve_flexible(mapping)
                    wrote.append(key)
            for mapping in field_values.get('outputMappings', []) or []:
                if not isinstance(mapping, dict):
                    continue
                out_name = mapping.get('outputFieldName', '')
                if out_name:
                    context[out_name] = _resolve_value_source_config(
                        mapping.get('valueSource'), context)
                    wrote.append(out_name)
            result['result'] = context.get('outcome', context.get('complete'))
            log_output.append(
                f'[{state_name}] validation verdict bound: '
                f'{", ".join(wrote) if wrote else "(nothing configured)"}'
            )

        elif state_class == 'EmitEvent':
            # Terminal for event-emitting graphs — the resolved payload
            # lands in context[EMITTED_EVENTS_KEY] (shape documented at
            # the constant) for the display/event bridge to consume.
            event_name = (field_values.get('eventName')
                          or field_values.get('name') or state_name)
            payload = {}
            raw_payload = field_values.get('payload')
            if isinstance(raw_payload, dict) and 'sourceType' not in raw_payload:
                for k, v in raw_payload.items():
                    if isinstance(v, dict) and 'sourceType' in v:
                        payload[k] = _resolve_value_source_config(v, context)
                    else:
                        payload[k] = _safe_resolve_value(v, context)
            for mapping in field_values.get('payloadMappings', []) or []:
                if not isinstance(mapping, dict):
                    continue
                out_name = mapping.get('outputFieldName', '')
                if out_name:
                    payload[out_name] = _resolve_value_source_config(
                        mapping.get('valueSource'), context)
            event = {'name': event_name, 'payload': payload,
                     'sourceState': state_name, 'channel': 'backend'}
            context.setdefault(EMITTED_EVENTS_KEY, []).append(event)
            result['result'] = event
            log_output.append(
                f'[{state_name}] emitted event {event_name!r} with '
                f'{len(payload)} payload field(s)'
            )

        elif state_class == 'EmitFrontendEvent':
            # EmitEvent's frontend twin: identical resolution, but the
            # event is tagged channel='frontend' so the execution
            # response's consumer (the display-solution-runner) dispatches
            # it on the client displayEvents$ bus. The engine itself does
            # no client dispatch — it can't; it records intent.
            event_name = (field_values.get('eventName')
                          or field_values.get('name') or state_name)
            payload = {}
            raw_payload = field_values.get('payload')
            if isinstance(raw_payload, dict) and 'sourceType' not in raw_payload:
                for k, v in raw_payload.items():
                    if isinstance(v, dict) and 'sourceType' in v:
                        payload[k] = _resolve_value_source_config(v, context)
                    else:
                        payload[k] = _safe_resolve_value(v, context)
            for mapping in field_values.get('payloadMappings', []) or []:
                if not isinstance(mapping, dict):
                    continue
                out_name = mapping.get('outputFieldName', '')
                if out_name:
                    payload[out_name] = _resolve_value_source_config(
                        mapping.get('valueSource'), context)
            event = {'name': event_name, 'payload': payload,
                     'sourceState': state_name, 'channel': 'frontend'}
            context.setdefault(EMITTED_EVENTS_KEY, []).append(event)
            result['result'] = event
            log_output.append(
                f'[{state_name}] emitted FRONTEND event {event_name!r} with '
                f'{len(payload)} payload field(s)'
            )

        elif state_class == 'FormValidation':
            # REAL per-field validation with BRANCHING (P4 — previously a
            # silent pass-through that let invalid forms proceed ungated
            # down the "All Valid" slot).
            #
            # Config: fields = [{fieldName, displayName, fieldType,
            #   required, enabled, minValue?, maxValue?, minLength?,
            #   maxLength?, pattern?/regex?}]. Values are read from
            # context (the submitted form payload arrives as the entry's
            # input params). Client-side concerns in the config
            # (debounceMs) are ignored here — they belong to the display
            # bridge.
            #
            # Writes: FORM_VALIDATION_KEY per-field verdicts,
            # 'form_valid', '_invalid_fields'.
            # Branches (indices into OUTPUT slots): valid → 0 (the
            # "All Valid" slot by convention); invalid → the FIRST
            # invalid field's own output slot when the graph wires one
            # (per-field slots are the authored pattern), else 1 when a
            # generic invalid slot exists, else traversal ENDS (see
            # _get_next_state — no fallback to "All Valid", ever).
            fields_cfg = [f for f in (field_values.get('fields') or [])
                          if isinstance(f, dict) and f.get('enabled', True)]
            verdicts = {}
            invalid_fields = []
            for f in fields_cfg:
                fname = f.get('fieldName', '')
                if not fname:
                    continue
                label = f.get('displayName') or fname
                value = context.get(fname)
                errors = []
                missing = value is None or (isinstance(value, str)
                                            and value.strip() == '')
                if missing:
                    if f.get('required', False):
                        errors.append(f'{label} is required.')
                else:
                    ftype = (f.get('fieldType') or '').lower()
                    num_val = None
                    if ftype in ('int', 'integer'):
                        try:
                            num_val = int(str(value))
                        except (TypeError, ValueError):
                            errors.append(f'{label} must be a whole number.')
                    elif ftype in ('float', 'number', 'num'):
                        try:
                            num_val = float(str(value))
                        except (TypeError, ValueError):
                            errors.append(f'{label} must be a number.')
                    elif ftype in ('bool', 'boolean'):
                        if not isinstance(value, bool) and str(value).lower() \
                                not in ('true', 'false', '0', '1'):
                            errors.append(f'{label} must be true or false.')
                    if num_val is not None:
                        if 'minValue' in f and f['minValue'] is not None \
                                and num_val < f['minValue']:
                            errors.append(
                                f"{label} must be at least {f['minValue']}.")
                        if 'maxValue' in f and f['maxValue'] is not None \
                                and num_val > f['maxValue']:
                            errors.append(
                                f"{label} must be at most {f['maxValue']}.")
                    if isinstance(value, str):
                        if f.get('minLength') and len(value) < f['minLength']:
                            errors.append(
                                f"{label} must be at least "
                                f"{f['minLength']} characters.")
                        if f.get('maxLength') and len(value) > f['maxLength']:
                            errors.append(
                                f"{label} must be at most "
                                f"{f['maxLength']} characters.")
                        pattern = f.get('pattern') or f.get('regex')
                        if pattern:
                            import re as _re
                            try:
                                if not _re.search(pattern, value):
                                    errors.append(
                                        f'{label} does not match the '
                                        f'expected format.')
                            except _re.error:
                                errors.append(
                                    f'{label} has an invalid validation '
                                    f'pattern (fix the rule in the editor).')
                verdicts[fname] = {'valid': not errors, 'errors': errors}
                if errors:
                    invalid_fields.append(fname)

            form_valid = not invalid_fields
            context[FORM_VALIDATION_KEY] = verdicts
            context['form_valid'] = form_valid
            context['_invalid_fields'] = invalid_fields
            result['result'] = form_valid

            # Routing happens in _get_next_state (it owns the slots):
            # valid → the first output slot ("All Valid"); invalid → the
            # first invalid field's own wired slot, else a wired generic
            # second slot, else traversal ENDS. branch_taken here is
            # informational for the trace.
            if form_valid:
                result['branch_taken'] = 0
                result['branch_label'] = 'All Valid'
                log_output.append(
                    f'[{state_name}] all {len(fields_cfg)} field(s) valid '
                    f'— proceeding down "All Valid"'
                )
            else:
                result['branch_taken'] = 1
                result['branch_label'] = 'Invalid'
                first_errs = verdicts[invalid_fields[0]]['errors']
                log_output.append(
                    f'[{state_name}] validation FAILED for '
                    f'{", ".join(invalid_fields)} — '
                    f'{first_errs[0] if first_errs else "invalid"}'
                )

        elif state_class == 'StateChangeCommit':
            # Persist field changes onto an EXISTING instance through the
            # standard object-tree path (attribute writes +
            # saveInstanceInDB — mirrors polariCRUDE / the runner).
            # PERMISSION-BLIND for now: the P6 auth/authz nodes add
            # identity + permission checks; until then treat like any
            # backend-trusted mutation. Scope: changeType 'update' only
            # ('create'/'delete' arrive with the data-access node family).
            # NOT terminal — commits and continues if wired onward;
            # traversal ends naturally when no output connector exists.
            #
            # Config: targetClassName, instanceRef (value-source dict or
            # literal name/id string), fieldMappings [{fieldName,
            # valueSource}] and/or fields {name: source|literal}. Legacy
            # thin config (targetFieldName only) maps that single context
            # var onto the instance field of the same name.
            change_type = (field_values.get('changeType') or 'update').lower()
            if change_type != 'update':
                raise ValueError(
                    f"StateChangeCommit '{state_name}': changeType "
                    f"'{change_type}' is not supported yet — only 'update' "
                    f"of an existing instance. Create/delete arrive with "
                    f"the data-access nodes."
                )
            target_cls = (field_values.get('targetClassName') or '').strip()
            if not target_cls:
                raise ValueError(
                    f"StateChangeCommit '{state_name}': targetClassName is "
                    f"required — which class's instance should be updated?"
                )
            ref_cfg = field_values.get('instanceRef')
            if isinstance(ref_cfg, dict) and 'sourceType' in ref_cfg:
                inst_ref = _resolve_value_source_config(ref_cfg, context)
            else:
                inst_ref = _safe_resolve_value(ref_cfg, context) \
                    if ref_cfg is not None else None
            if inst_ref is None:
                raise ValueError(
                    f"StateChangeCommit '{state_name}': instanceRef did not "
                    f"resolve — which instance should be updated?"
                )
            inst_ref = str(inst_ref)

            table = {}
            if self.manager is not None and hasattr(self.manager, 'objectTables'):
                table = self.manager.objectTables.get(target_cls, {}) or {}
            target = None
            for inst in table.values():
                if str(getattr(inst, 'name', '')) == inst_ref \
                        or str(getattr(inst, 'id', '')) == inst_ref \
                        or str(getattr(inst, 'polariId', '')) == inst_ref:
                    target = inst
                    break
            if target is None:
                raise ValueError(
                    f"StateChangeCommit '{state_name}': no {target_cls} "
                    f"instance matching '{inst_ref}' was found."
                )

            # Gather the field writes.
            writes = {}
            for mapping in field_values.get('fieldMappings', []) or []:
                if not isinstance(mapping, dict):
                    continue
                fname = mapping.get('fieldName') or mapping.get('outputFieldName')
                if fname:
                    writes[fname] = _resolve_value_source_config(
                        mapping.get('valueSource'), context)
            raw_fields = field_values.get('fields')
            if isinstance(raw_fields, dict) and 'sourceType' not in raw_fields:
                for k, v in raw_fields.items():
                    if isinstance(v, dict) and 'sourceType' in v:
                        writes[k] = _resolve_value_source_config(v, context)
                    else:
                        writes[k] = _safe_resolve_value(v, context)
            legacy = field_values.get('targetFieldName')
            if legacy and not writes:
                writes[legacy] = context.get(legacy)
            if not writes:
                raise ValueError(
                    f"StateChangeCommit '{state_name}': nothing to commit — "
                    f"configure fieldMappings (or fields) with at least one "
                    f"field."
                )

            for k, v in writes.items():
                setattr(target, k, v)
            db = getattr(self.manager, 'db', None) if self.manager else None
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(target)
            committed = {'className': target_cls, 'instance': inst_ref,
                         'fields': dict(writes)}
            context.setdefault(COMMITTED_CHANGES_KEY, []).append(committed)
            result['result'] = committed
            log_output.append(
                f'[{state_name}] committed {len(writes)} field(s) onto '
                f'{target_cls} "{inst_ref}": '
                f'{", ".join(f"{k}={v!r}" for k, v in writes.items())}'
            )

        else:
            # Pass-through for unhandled types
            result['result'] = f'State {state_name} ({state_class}) - no evaluation'

        return result

    def _evaluate_chain_link(self, link, context, log_output=None):
        """Evaluate a single ConditionalChain link with ValueSourceConfig support.

        A link has:
            leftSource / rightSource: ValueSourceConfig dicts
            conditionType: 'equals', 'greaterThan', etc.
            fieldName / conditionValue: legacy string fields
        """
        if log_output is None:
            log_output = []

        # Resolve left side — prefer ValueSourceConfig, fall back to legacy
        left_source = link.get('leftSource')
        if left_source and isinstance(left_source, dict) and 'sourceType' in left_source:
            left_val = _resolve_value_source_config(left_source, context)
        else:
            left_val = _safe_resolve_value(link.get('fieldName', ''), context)

        # Resolve right side
        right_source = link.get('rightSource')
        if right_source and isinstance(right_source, dict) and 'sourceType' in right_source:
            right_val = _resolve_value_source_config(right_source, context)
        else:
            right_val = _safe_resolve_value(link.get('conditionValue', ''), context)

        # Get comparison operator
        condition_type = link.get('conditionType', 'equals')
        op_func = COMPARISON_OPS.get(condition_type, operator.eq)

        link_display = link.get('displayName', f'{condition_type}')
        log_output.append(f'  Evaluating: {left_val!r} {condition_type} {right_val!r}')

        try:
            result = op_func(left_val, right_val)
            log_output.append(f'  Link result: {result}')
            return result
        except (TypeError, ValueError) as e:
            log_output.append(f'  Link evaluation error: {e}')
            return False

    def _evaluate_condition_any(self, condition, context, log_output=None):
        """Evaluate any condition shape the editor produces:
        - a ConditionalChain-style dict with 'links' (ValueSourceConfig
          operands) — combined with each link's logicalOperator;
        - a legacy condition dict (leftOperand/operator/rightOperand or
          compound 'conditions');
        - a plain string: either "left op right" (spaced, symbol
          operators) or a bare variable evaluated for truthiness.
        """
        if log_output is None:
            log_output = []
        if isinstance(condition, dict) and condition.get('links'):
            links = condition['links']
            default_op = condition.get('defaultLogicalOperator', 'AND').upper()
            combined = None
            prev_op = default_op
            for link in links:
                link_result = self._evaluate_chain_link(link, context, log_output)
                if combined is None:
                    combined = link_result
                else:
                    if prev_op == 'OR':
                        combined = combined or link_result
                    elif prev_op == 'NOT':
                        combined = combined and (not link_result)
                    elif prev_op == 'XOR':
                        combined = combined ^ link_result
                    else:
                        combined = combined and link_result
                prev_op = link.get('logicalOperator', default_op).upper()
            return bool(combined)
        if isinstance(condition, dict):
            return _evaluate_condition(condition, context)
        if isinstance(condition, str) and condition.strip():
            parts = condition.split()
            if len(parts) == 3 and parts[1] in COMPARISON_OPS:
                left = _safe_resolve_value(parts[0], context)
                right = _safe_resolve_value(parts[2], context)
                try:
                    return bool(COMPARISON_OPS[parts[1]](left, right))
                except (TypeError, ValueError):
                    return False
            return bool(_safe_resolve_value(condition, context))
        return False

    def _eval_element_expression(self, field_values, context, item_var):
        """Per-element expression for Map/Reduce: a `valueSource`
        (ValueSourceConfig — including from_latex for real math) or an
        `expression` string, either "left op right" (spaced, arithmetic
        symbol/name operators) or a single resolvable term."""
        value_source = field_values.get('valueSource')
        if isinstance(value_source, dict) and 'sourceType' in value_source:
            return _resolve_value_source_config(value_source, context)
        expression = str(field_values.get('expression', item_var)).strip()
        parts = expression.split()
        if len(parts) == 3 and parts[1] in ARITHMETIC_OPS:
            left = _safe_resolve_value(parts[0], context)
            right = _safe_resolve_value(parts[2], context)
            try:
                return ARITHMETIC_OPS[parts[1]](left, right)
            except (TypeError, ZeroDivisionError):
                return None
        return _safe_resolve_value(expression, context)

    def _slot_target(self, state, states_by_name, slot_index):
        """The state a given OUTPUT slot's first connector points to
        (slot 0 = loop body, slot 1 = loop done). None when the slot or
        its connector is absent."""
        if not state:
            return None
        output_slots = [s for s in state.get('slots', [])
                        if not s.get('isInput', False)]
        if slot_index >= len(output_slots):
            return None
        for conn in output_slots[slot_index].get('connectors', []):
            target_name = conn.get('targetStateName')
            if target_name and target_name in states_by_name:
                return states_by_name[target_name]
        return None

    def _get_next_state(self, current_state, states_by_name, context, branch_taken):
        """
        Determine the next state by traversing the connector graph.

        For ConditionalChain: uses branch_taken to pick the correct output slot.
        For other states: follows the first output slot connector.
        """
        slots = current_state.get('slots', [])
        state_class = current_state.get('boundObjectClass', current_state.get('stateClass', ''))

        # Separate input and output slots
        output_slots = [s for s in slots if not s.get('isInput', False)]

        if not output_slots:
            return None

        if state_class == 'FormValidation':
            # Verdict-driven routing (the handler wrote form_valid /
            # _invalid_fields into context). CRITICAL INVARIANT: an
            # invalid form NEVER proceeds down "All Valid" — when no
            # invalid branch is wired, traversal ends and the verdict
            # lives in the context/result.
            def _follow(slot):
                for conn in slot.get('connectors', []) or []:
                    target_name = conn.get('targetStateName')
                    if target_name and target_name in states_by_name:
                        return states_by_name.get(target_name)
                return None

            if bool(context.get('form_valid')):
                # First output slot = "All Valid" by convention.
                return _follow(output_slots[0]) if output_slots else None

            fields_cfg = (current_state.get('boundObjectFieldValues', {})
                          or {}).get('fields', []) or []
            slot_by_abs_index = {s.get('index'): s for s in output_slots}
            # Per-field routing: the first invalid field whose declared
            # outputSlotIndex is wired wins (the authored seed pattern).
            for fname in context.get('_invalid_fields') or []:
                f_cfg = next((f for f in fields_cfg
                              if isinstance(f, dict)
                              and f.get('fieldName') == fname), None)
                if not f_cfg:
                    continue
                slot = slot_by_abs_index.get(f_cfg.get('outputSlotIndex'))
                if slot and slot.get('connectors'):
                    nxt = _follow(slot)
                    if nxt is not None:
                        return nxt
            # Generic invalid slot convention: the SECOND output slot —
            # but ONLY for the simple Valid/Invalid shape (no per-field
            # outputSlotIndex declared anywhere). With per-field slots
            # declared, an unwired invalid field must NOT route down some
            # other field's slot. Never fall back further.
            has_per_field_slots = any(
                isinstance(f, dict) and f.get('outputSlotIndex') is not None
                for f in fields_cfg
            )
            if (not has_per_field_slots and len(output_slots) > 1
                    and output_slots[1].get('connectors')):
                return _follow(output_slots[1])
            return None

        if state_class == 'ConditionalChain' and branch_taken is not None:
            # For conditional chains, output slots correspond to branches
            # Slot at branch_taken index (if available)
            if branch_taken < len(output_slots):
                target_slot = output_slots[branch_taken]
            else:
                # Fallback to last output slot (else branch)
                target_slot = output_slots[-1] if output_slots else None

            if target_slot:
                connectors = target_slot.get('connectors', [])
                if connectors:
                    target_name = connectors[0].get('targetStateName')
                    if target_name:
                        return states_by_name.get(target_name)
            return None

        # For non-conditional states, follow the first output slot's connector
        for slot in output_slots:
            connectors = slot.get('connectors', [])
            for conn in connectors:
                target_name = conn.get('targetStateName')
                if target_name and target_name in states_by_name:
                    return states_by_name.get(target_name)

        return None
