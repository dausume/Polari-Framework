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


# State classes that serve as initial entry points
INITIAL_STATE_CLASSES = {
    'InitialState', 'DirectInvocation', 'FormSubscription',
    'LogicFlowEntry', 'BackendStateChange'
}

# State classes that are terminal (no further traversal)
TERMINAL_STATE_CLASSES = {
    'ReturnStatement', 'ReturnValue'
}

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

    return None


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

    def execute(self, solution_data, input_params, config=None, target_runtime='python_backend', instance_fields=None):
        """
        Execute a solution by walking its state graph.

        Args:
            solution_data: The solution definition dict (will be deep-cloned)
            input_params: Dict of input parameter values
            config: Optional StepConfig for controlling step behavior
            target_runtime: 'python_backend' or 'typescript_frontend'
            instance_fields: Optional dict of instance field values (merged before input_params)

        Returns:
            ExecutionTrace with full step snapshots
        """
        if config is None:
            config = StepConfig(mode='step', record_context=True)

        # ISOLATION: Deep-clone solution_data
        solution_data = copy.deepcopy(solution_data)

        solution_name = solution_data.get('solutionName', 'untitled')
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

        # Walk the state graph
        current_state = initial_state
        step_index = 0
        max_steps = 1000  # Safety limit to prevent infinite loops
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
                try:
                    result = self._evaluate_state(
                        state_class, field_values, context, state_name, log_output
                    )
                    execution_result = result.get('result')
                    branch_taken = result.get('branch_taken')
                    branch_label = result.get('branch_label')
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

                # Determine next state via connector traversal
                next_state = self._get_next_state(
                    current_state, states_by_name, context, branch_taken
                )
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

    def _evaluate_state(self, state_class, field_values, context, state_name, log_output):
        """
        Evaluate a state's operation, modifying context as needed.

        Returns a dict with:
            'result': the execution result value (if any)
            'branch_taken': which branch was taken (for conditionals)
            'branch_label': human-readable label for the branch
        """
        # ===== TOP-LEVEL DEBUG =====
        # print(f'[ENGINE DEBUG] _evaluate_state: state_name={state_name!r} state_class={state_class!r}', flush=True)
        # print(f'[ENGINE DEBUG]   field_values keys={list(field_values.keys())}', flush=True)
        # ============================

        result = {'result': None, 'branch_taken': None, 'branch_label': None}

        if state_class in ('InitialState', 'DirectInvocation'):
            # Sets input params in context (already done by caller)
            # Extract declared input params for documentation
            input_params = field_values.get('inputParams', [])
            result['result'] = f'Entry point with {len(input_params)} parameters'
            # Log input parameters
            param_strs = []
            for p in input_params:
                p_name = p.get('name', '?')
                p_val = context.get(p_name, '<not provided>')
                param_strs.append(f'{p_name}={p_val!r}')
            log_output.append(f'[{state_name}] Entering with params: {", ".join(param_strs) if param_strs else "(none)"}')

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
            # Capture loop config in context (full loop execution in v2)
            iterator = field_values.get('iterator', 'i')
            start = _safe_resolve_value(field_values.get('start', '0'), context)
            end = _safe_resolve_value(field_values.get('end', '10'), context)
            step = _safe_resolve_value(field_values.get('step', '1'), context)
            context[iterator] = start
            result['result'] = {'loop': 'for', 'iterator': iterator, 'start': start, 'end': end, 'step': step}
            log_output.append(f'[{state_name}] for {iterator} in range({start}, {end}, {step})')

        elif state_class == 'WhileLoop':
            condition = field_values.get('condition', '')
            result['result'] = {'loop': 'while', 'condition': str(condition)}
            log_output.append(f'[{state_name}] while {condition}')

        elif state_class == 'ForEachLoop':
            item = field_values.get('item', 'item')
            collection_str = field_values.get('collection', '[]')
            collection = _safe_resolve_value(collection_str, context)
            if isinstance(collection, (list, tuple)) and len(collection) > 0:
                context[item] = collection[0]
            coll_size = len(collection) if isinstance(collection, (list, tuple)) else 0
            result['result'] = {'loop': 'foreach', 'item': item, 'collection_size': coll_size}
            log_output.append(f'[{state_name}] for each {item} in collection ({coll_size} items)')

        elif state_class == 'FunctionCall':
            func_name = field_values.get('functionName', '')
            result_var = field_values.get('resultVariableName', '')
            # Record the call (actual invocation in v2)
            if result_var:
                context[result_var] = None  # Placeholder
            result['result'] = f'Called {func_name}'
            log_output.append(f'[{state_name}] Calling {func_name}() -> {result_var or "(void)"}')

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
                        # Prefer the LaTeX result for `equation`-typed targets;
                        # fall back to the numeric result when no LaTeX was emitted.
                        computed = exec_result.get('result_latex')
                        if computed is None:
                            computed = exec_result.get('result_numeric')
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

        elif state_class == 'FilterList':
            source_var = field_values.get('sourceVariable', '')
            result_var = field_values.get('resultVariable', '')
            filter_condition = field_values.get('filterCondition', {})
            source = context.get(source_var, [])
            # Basic filtering - pass through for now
            if result_var:
                context[result_var] = source
            result['result'] = f'Filtered {len(source) if isinstance(source, list) else 0} items'

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
