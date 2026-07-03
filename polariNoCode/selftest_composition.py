"""
Self-test for no-code P3 — solution-as-state composition.

Run from polari-framework/:
    python3 -m polariNoCode.selftest_composition

A SolutionInvocation node runs another SolutionDefinition as ONE
reusable state: caller-side value sources map into the callee's inputs,
the callee runs in an ISOLATED context (no caller leakage — its
contract is the whole interface), and its outputs bind back. Recursion
is allowed and depth-guarded (MAX_INVOCATION_DEPTH), so the litmus here
is the recursion classic: factorial via a solution invoking ITSELF.
"""

import json
from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    MAX_INVOCATION_DEPTH,
    SolutionExecutionEngine,
)
from polariNoCode.stepping import StepConfig

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


# --------------------------------------------------------------------------
# Graph-authoring helpers (same dict shape the editor persists — mirrors
# selftest_turing's builders).
# --------------------------------------------------------------------------

def node(name, cls, fields=None, outs=None, index=0):
    slots = [{'isInput': True, 'connectors': []}]
    for targets in (outs if outs is not None else [[]]):
        slots.append({
            'isInput': False,
            'connectors': [{'targetStateName': t} for t in targets],
        })
    return {
        'stateName': name, 'stateClass': cls, 'boundObjectClass': cls,
        'boundObjectFieldValues': fields or {}, 'slots': slots, 'index': index,
    }


def solution(name, *states):
    return {'solutionName': name,
            'stateInstances': [dict(s, index=i) for i, s in enumerate(states)]}


def entry(name='Start', cls='InitialState', nxt=None):
    return node(name, cls, {}, outs=[[nxt] if nxt else []])


def assign(name, var, value, nxt):
    return node(name, 'VariableAssignment',
                {'variableName': var, 'value': value},
                outs=[[nxt] if nxt else []])


def math(name, res, left, op, right, nxt):
    return node(name, 'MathOperation',
                {'leftOperand': left, 'operationType': op,
                 'rightOperand': right, 'resultVariable': res},
                outs=[[nxt] if nxt else []])


def ret(name, var):
    return node(name, 'ReturnValue',
                {'returnValueSource': 'variable', 'variableName': var},
                outs=[])


def invoke(name, callee, mappings, bindings, nxt):
    return node(name, 'SolutionInvocation',
                {'solutionRef': callee,
                 'inputMappings': mappings,
                 'resultBindings': bindings},
                outs=[[nxt] if nxt else []])


def var_src(path):
    return {'sourceType': 'from_source_object', 'sourceObjectPath': path}


def lit_src(value):
    kind = 'int' if isinstance(value, int) else 'float'
    return {'sourceType': 'direct_assignment', 'directValue': value,
            'directValueType': kind}


def manager_with(*rows):
    """Fake manager whose SolutionDefinition table holds (sol, contract)
    pairs. Each row: (solution_dict, contract_dict_or_None)."""
    table = {}
    for sol, contract in rows:
        name = sol['solutionName']
        table[name] = SimpleNamespace(
            name=name,
            definition=json.dumps(sol),
            contract_json=json.dumps(contract or {}),
            target_runtime='python_backend',
        )
    return SimpleNamespace(objectTables={'SolutionDefinition': table})


def run(sol, manager=None, params=None):
    engine = SolutionExecutionEngine(manager=manager)
    return engine.execute(
        solution_data=sol, input_params=params or {},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend',
    )


def invocation_step(trace):
    for s in trace.steps:
        if s.state_class_name == 'SolutionInvocation':
            return s
    return None


# --------------------------------------------------------------------------
# The callee library used across checks.
# --------------------------------------------------------------------------

SQUARE = solution(
    'square',
    entry('In', 'LogicFlowEntry', 'Sq'),
    math('Sq', 'result', 'x', 'multiply', 'x', 'Out'),
    ret('Out', 'result'),
)
SQUARE_CONTRACT = {
    'description': 'Squares the number you give it.',
    'inputs': [{'name': 'x', 'required': True,
                'description': 'the number to square'}],
    'returns': [{'name': 'return', 'description': 'x squared'}],
    'executionRights': 'invoker',
}

INC = solution(
    'inc',
    entry('In', 'LogicFlowEntry', 'Add'),
    math('Add', 'result', 'x', 'add', '1', 'Out'),
    ret('Out', 'result'),
)

MID = solution(
    'mid',
    entry('In', 'LogicFlowEntry', 'CallInc'),
    invoke('CallInc', 'inc',
           [{'param': 'x', 'valueSource': var_src('x')}],
           [{'output': 'return', 'contextVar': 'bumped'}], 'Out'),
    ret('Out', 'bumped'),
)

OUTER = solution(
    'outer',
    entry('Start', 'InitialState', 'CallMid'),
    invoke('CallMid', 'mid',
           [{'param': 'x', 'valueSource': lit_src(40)}],
           [{'output': 'return', 'contextVar': 'answer'}], 'Out'),
    ret('Out', 'answer'),
)

# factorial: n <= 1 -> 1; else n * factorial(n - 1). A solution invoking
# ITSELF — the recursion litmus.
FACTORIAL = solution(
    'factorial',
    entry('In', 'LogicFlowEntry', 'Base?'),
    node('Base?', 'ConditionalChain',
         {'condition': {'leftOperand': 'n', 'operator': '<=',
                        'rightOperand': '1'}},
         outs=[['One'], ['Minus']]),
    assign('One', 'result', '1', 'Out'),
    math('Minus', 'm', 'n', 'subtract', '1', 'Recurse'),
    invoke('Recurse', 'factorial',
           [{'param': 'n', 'valueSource': var_src('m')}],
           [{'output': 'return', 'contextVar': 'sub'}], 'Times'),
    math('Times', 'result', 'n', 'multiply', 'sub', 'Out'),
    ret('Out', 'result'),
)

FOREVER = solution(
    'forever',
    entry('In', 'LogicFlowEntry', 'Again'),
    invoke('Again', 'forever',
           [{'param': 'n', 'valueSource': var_src('n')}],
           [{'output': 'return', 'contextVar': 'x'}], 'Out'),
    ret('Out', 'x'),
)

LEAK_PROBE = solution(
    'leak-probe',
    entry('In', 'LogicFlowEntry', 'Out'),
    ret('Out', 'secret'),
)


def _composition():
    print('Composition — solution as a reusable state\n')

    # 1. Basic call: square(7) via a caller variable.
    caller = solution(
        'caller-square',
        entry('Start', 'InitialState', 'SetA'),
        assign('SetA', 'a', '7', 'Call'),
        invoke('Call', 'square',
               [{'param': 'x', 'valueSource': var_src('a')}],
               [{'output': 'return', 'contextVar': 'sq'}], 'Out'),
        ret('Out', 'sq'),
    )
    m = manager_with((SQUARE, SQUARE_CONTRACT))
    trace = run(caller, m)
    check('caller invokes square(7) and binds 49',
          trace.status == 'completed' and trace.final_return_value == 49,
          f'status={trace.status} result={trace.final_return_value}')

    # 2. Child-execution summary rides the invocation step + serializes.
    step = invocation_step(trace)
    ce = step.child_execution if step else None
    check('invocation step carries the child-execution summary',
          isinstance(ce, dict) and ce.get('solutionName') == 'square'
          and ce.get('status') == 'completed' and ce.get('stepCount', 0) >= 3
          and ce.get('executionId', '').startswith('exec_'),
          f'childExecution={ce}')
    as_dict = step.to_dict() if step else {}
    check('childExecution serializes into the trace dict (stepping UI shape)',
          as_dict.get('childExecution', {}).get('solutionName') == 'square')

    # 3. Contract violation: required input not mapped.
    bad_caller = solution(
        'caller-bad',
        entry('Start', 'InitialState', 'Call'),
        invoke('Call', 'square', [], [{'output': 'return', 'contextVar': 's'}],
               'Out'),
        ret('Out', 's'),
    )
    trace = run(bad_caller, m)
    check('missing required input fails in plain language',
          trace.status == 'errored'
          and "requires input(s) ['x']" in (trace.error_summary or '')
          and 'Squares the number' in (trace.error_summary or ''),
          f'error={trace.error_summary}')

    # 4. Nested invocation 3 deep: outer -> mid -> inc; 40 -> 41.
    m = manager_with((INC, None), (MID, None), (OUTER, None))
    trace = run(OUTER, m)
    check('nested invocation 3 levels deep (outer→mid→inc, 40→41)',
          trace.final_return_value == 41,
          f'result={trace.final_return_value}')

    # 5. RECURSION LITMUS: factorial(5) = 120 via self-invocation.
    m = manager_with((FACTORIAL, None))
    caller = solution(
        'caller-fact',
        entry('Start', 'InitialState', 'Call'),
        invoke('Call', 'factorial',
               [{'param': 'n', 'valueSource': lit_src(5)}],
               [{'output': 'return', 'contextVar': 'f'}], 'Out'),
        ret('Out', 'f'),
    )
    trace = run(caller, m)
    check('RECURSION: factorial(5) = 120 via a solution invoking itself',
          trace.status == 'completed' and trace.final_return_value == 120,
          f'status={trace.status} result={trace.final_return_value}')

    # 6. Infinite recursion -> readable depth error, never a hang.
    m = manager_with((FOREVER, None))
    caller = solution(
        'caller-forever',
        entry('Start', 'InitialState', 'Call'),
        invoke('Call', 'forever',
               [{'param': 'n', 'valueSource': lit_src(1)}],
               [{'output': 'return', 'contextVar': 'x'}], 'Out'),
        ret('Out', 'x'),
    )
    trace = run(caller, m)
    check('infinite recursion fails with the plain-language depth error',
          trace.status == 'errored'
          and f'exceeded {MAX_INVOCATION_DEPTH} levels'
              in (trace.error_summary or '')
          and 'base case' in (trace.error_summary or ''),
          f'error={(trace.error_summary or "")[:120]}')

    # 7. THE ABSTRACTION BOUNDARY: callee cannot see caller context.
    m = manager_with((LEAK_PROBE, None))
    caller = solution(
        'caller-leak',
        entry('Start', 'InitialState', 'SetSecret'),
        assign('SetSecret', 'secret', '42', 'Call'),
        invoke('Call', 'leak-probe', [],
               [{'output': 'return', 'contextVar': 'stolen'}], 'Out'),
        ret('Out', 'stolen'),
    )
    trace = run(caller, m)
    check('no caller-context leakage (callee cannot read caller vars)',
          trace.status == 'completed' and trace.final_return_value != 42,
          f'callee saw={trace.final_return_value!r}')

    # 8. Named outputs: bind a callee context variable (not just return).
    m = manager_with((SQUARE, SQUARE_CONTRACT))
    caller = solution(
        'caller-named',
        entry('Start', 'InitialState', 'Call'),
        invoke('Call', 'square',
               [{'param': 'x', 'valueSource': lit_src(6)}],
               [{'output': 'result', 'contextVar': 'named'},
                {'output': 'nonsense', 'contextVar': 'missing'}], 'Out'),
        ret('Out', 'named'),
    )
    trace = run(caller, m)
    step = invocation_step(trace)
    notes = ' '.join(step.log_output) if step else ''
    check('named callee outputs bind; missing outputs note + None',
          trace.final_return_value == 36
          and "no output named 'nonsense'" in notes,
          f'result={trace.final_return_value}')

    # 9. executionRights is surfaced in the trace (declarative for now).
    definer_contract = dict(SQUARE_CONTRACT, executionRights='definer')
    m = manager_with((SQUARE, definer_contract))
    caller = solution(
        'caller-rights',
        entry('Start', 'InitialState', 'Call'),
        invoke('Call', 'square',
               [{'param': 'x', 'valueSource': lit_src(2)}],
               [{'output': 'return', 'contextVar': 's'}], 'Out'),
        ret('Out', 's'),
    )
    trace = run(caller, m)
    step = invocation_step(trace)
    notes = ' '.join(step.log_output) if step else ''
    check('executionRights (definer) is stored and surfaced in the trace',
          'rights: definer' in notes, f'notes={notes[:100]}')

    # 10. Missing callee: plain-language error.
    trace = run(caller, manager_with())
    check('missing callee fails plainly',
          trace.status == 'errored'
          and "was not found" in (trace.error_summary or ''))

    # 11. FunctionCall (retired) says so and does nothing.
    legacy = solution(
        'legacy-call',
        entry('Start', 'InitialState', 'Call'),
        node('Call', 'FunctionCall',
             {'functionName': 'ghost', 'resultVariableName': 'r'},
             outs=[['Out']]),
        ret('Out', 'r'),
    )
    trace = run(legacy)
    notes = ' '.join(trace.steps[1].log_output) if len(trace.steps) > 1 else ''
    check('retired FunctionCall no-ops loudly (points at SolutionInvocation)',
          trace.status == 'completed' and trace.final_return_value is None
          and 'did NOT run' in notes and 'SolutionInvocation' in notes)


if __name__ == '__main__':
    _composition()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
