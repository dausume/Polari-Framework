"""
Assertion Evaluator

Evaluates ExecutionStepAssertions against an ExecutionTrace.
Reuses COMPARISON_OPS from SolutionExecutionEngine for consistent comparison logic.
"""

from polariNoCode.SolutionExecutionEngine import COMPARISON_OPS
import json


def evaluate_assertion(assertion, trace):
    """
    Evaluate a single assertion against an execution trace.

    Args:
        assertion: An ExecutionStepAssertion instance (or dict with same fields)
        trace: An ExecutionTrace (with .steps list and .to_dict() support),
               or a plain dict from trace.to_dict()

    Returns:
        dict with keys: assertion_id, passed, actual_value, expected_value, message
    """
    a_type = _get(assertion, 'assertion_type', 'context_value')
    step_index = _get(assertion, 'step_index', 0)
    state_name = _get(assertion, 'state_name', '')
    comparison = _get(assertion, 'comparison_operator', 'equals')
    assertion_id = _get(assertion, 'polariId', '') or _get(assertion, 'id', '')

    # Get steps from trace (support both object and dict)
    if isinstance(trace, dict):
        steps = trace.get('steps', [])
        final_return = trace.get('finalReturnValue')
    else:
        steps = getattr(trace, 'steps', [])
        final_return = getattr(trace, 'final_return_value', None)
        if final_return is None:
            final_return = getattr(trace, 'finalReturnValue', None)

    # Find the target step
    step = _find_step(steps, step_index, state_name)
    if step is None and a_type != 'return_value':
        return _result(assertion_id, False, None, None,
                       f'Step not found (index={step_index}, state_name="{state_name}")')

    if a_type == 'context_value':
        return _eval_context_value(assertion, step, comparison, assertion_id)
    elif a_type == 'branch_taken':
        return _eval_branch_taken(assertion, step, assertion_id)
    elif a_type == 'status':
        return _eval_status(assertion, step, assertion_id)
    elif a_type == 'return_value':
        return _eval_return_value(assertion, final_return, comparison, assertion_id)
    else:
        return _result(assertion_id, False, None, None,
                       f'Unknown assertion_type: {a_type}')


def evaluate_all_assertions(assertions, trace):
    """
    Evaluate a list of assertions against a trace.

    Args:
        assertions: list of ExecutionStepAssertion instances or dicts
        trace: ExecutionTrace object or dict

    Returns:
        list of assertion result dicts
    """
    results = []
    for assertion in assertions:
        enabled = _get(assertion, 'enabled', True)
        if not enabled:
            continue
        results.append(evaluate_assertion(assertion, trace))
    return results


def _eval_context_value(assertion, step, comparison, assertion_id):
    variable_name = _get(assertion, 'variable_name', '')
    expected_raw = _get(assertion, 'expected_value', '')

    # Get context_after variables
    context_after = _get_nested(step, 'contextAfter') or _get_nested(step, 'context_after') or {}
    variables = context_after.get('variables', {}) if isinstance(context_after, dict) else {}

    if variable_name not in variables:
        return _result(assertion_id, False, None, expected_raw,
                       f'Variable "{variable_name}" not found in context_after')

    actual = variables[variable_name]
    expected = _coerce_type(expected_raw, actual)

    comp_fn = COMPARISON_OPS.get(comparison)
    if comp_fn is None:
        return _result(assertion_id, False, actual, expected,
                       f'Unknown comparison operator: {comparison}')

    try:
        passed = comp_fn(actual, expected)
    except Exception as e:
        return _result(assertion_id, False, actual, expected, f'Comparison error: {e}')

    msg = f'{variable_name}: {actual} {comparison} {expected}' if passed else \
          f'{variable_name}: expected {expected} ({comparison}), got {actual}'
    return _result(assertion_id, passed, actual, expected, msg)


def _eval_branch_taken(assertion, step, assertion_id):
    expected_branch = _get(assertion, 'expected_branch_taken', '')
    expected_label = _get(assertion, 'expected_branch_label', '')

    actual_branch = _get_nested(step, 'branchTaken') or _get_nested(step, 'branch_taken') or ''
    actual_label = _get_nested(step, 'branchLabel') or _get_nested(step, 'branch_label') or ''

    passed = True
    messages = []

    if expected_branch:
        if actual_branch != expected_branch:
            passed = False
            messages.append(f'branch: expected "{expected_branch}", got "{actual_branch}"')
    if expected_label:
        if actual_label != expected_label:
            passed = False
            messages.append(f'label: expected "{expected_label}", got "{actual_label}"')

    msg = 'Branch assertion passed' if passed else '; '.join(messages)
    return _result(assertion_id, passed, actual_branch or actual_label,
                   expected_branch or expected_label, msg)


def _eval_status(assertion, step, assertion_id):
    expected_status = _get(assertion, 'expected_status', 'completed')
    actual_status = _get_nested(step, 'status') or ''

    passed = actual_status == expected_status
    msg = f'Status: {actual_status}' if passed else \
          f'Status: expected "{expected_status}", got "{actual_status}"'
    return _result(assertion_id, passed, actual_status, expected_status, msg)


def _eval_return_value(assertion, final_return, comparison, assertion_id):
    expected_raw = _get(assertion, 'expected_value', '')
    expected = _coerce_type(expected_raw, final_return)

    comp_fn = COMPARISON_OPS.get(comparison)
    if comp_fn is None:
        return _result(assertion_id, False, final_return, expected,
                       f'Unknown comparison operator: {comparison}')

    try:
        passed = comp_fn(final_return, expected)
    except Exception as e:
        return _result(assertion_id, False, final_return, expected,
                       f'Comparison error: {e}')

    msg = f'Return value: {final_return}' if passed else \
          f'Return value: expected {expected} ({comparison}), got {final_return}'
    return _result(assertion_id, passed, final_return, expected, msg)


# --- Helpers ---

def _get(obj, key, default=None):
    """Get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_nested(obj, key):
    """Get a nested value from an object or dict."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _find_step(steps, step_index, state_name):
    """Find a step by index or state_name."""
    if steps and 0 <= step_index < len(steps):
        step = steps[step_index]
        # If state_name specified, verify it matches
        if state_name:
            s_name = _get_nested(step, 'stateName') or _get_nested(step, 'state_name') or ''
            if s_name == state_name:
                return step
        else:
            return step

    # Fallback: search by state_name
    if state_name:
        for s in (steps or []):
            s_name = _get_nested(s, 'stateName') or _get_nested(s, 'state_name') or ''
            if s_name == state_name:
                return s

    return None


def _coerce_type(expected_str, actual):
    """Try to coerce expected_str to match actual's type for comparison."""
    if not isinstance(expected_str, str):
        return expected_str

    # Try JSON parse first (handles booleans, numbers, null, arrays, objects)
    try:
        return json.loads(expected_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # If actual is numeric, try numeric coercion
    if isinstance(actual, (int, float)):
        try:
            if '.' in expected_str:
                return float(expected_str)
            return int(expected_str)
        except (ValueError, TypeError):
            pass

    return expected_str


def _result(assertion_id, passed, actual_value, expected_value, message):
    return {
        'assertionId': assertion_id,
        'passed': passed,
        'actualValue': actual_value,
        'expectedValue': expected_value,
        'message': message,
    }
