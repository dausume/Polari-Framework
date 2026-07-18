"""
Self-test for the no-code engine's Turing-floor repair (P1 + P2).

Run from polari-framework/:
    python3 -m polariNoCode.selftest_turing

Every check authors a real state graph (the same dict shape the editor
saves) and executes it through the REAL SolutionExecutionEngine:

  P2 — real control flow: ForLoop / WhileLoop / ForEachLoop with the
  body(slot 0)/done(slot 1) convention and auto-return bodies; nesting;
  Break/Continue; iteration budgets with plain-language errors;
  Filter/Map/Reduce; CollectionOperation dict/list verbs.

  P1 — contract fixes: InitialConditionsValidatorEntry accepted as an
  entry; ValidationResult binds the verdict the validator/gate consumers
  read; EmitEvent lands in `_emitted_events` with the documented shape.

  LITMUS: iterative Fibonacci(20) = 6765 — variables + a while loop +
  arithmetic, i.e. "this is a programming language now".
"""

from polariNoCode.SolutionExecutionEngine import (
    EMITTED_EVENTS_KEY,
    SolutionExecutionEngine,
)
from polariNoCode.stepping import StepConfig

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


# ---------------------------------------------------------------------------
# Graph-authoring helpers — promoted to polariNoCode.graph_builder (ncg-1);
# this gate now exercises the SAME seam domain compilers build through.
# ---------------------------------------------------------------------------

from polariNoCode.graph_builder import (node, solution, entry, assign,
                                        math, ret, execute)
from polariNoCode.graph_compilers import final_context_of as final_context


def run(sol, params=None):
    return execute(sol, params=params)


# ---------------------------------------------------------------------------
# P2 — loops
# ---------------------------------------------------------------------------

def _loops():
    print('Turing floor — real loops\n')

    # ForLoop: sum 1..10 (range semantics: end exclusive → end 11).
    sol = solution(
        'sum-1-to-10',
        entry(),
        assign('InitSum', 'sum', '0', 'Loop'),
        node('Loop', 'ForLoop',
             {'iteratorVariable': 'i', 'startValue': 1, 'endValue': 11,
              'stepValue': 1},
             outs=[['Add'], ['Done']]),
        math('Add', 'sum', 'sum', 'add', 'i', ''),  # body dead-ends → auto-return
        ret('Done', 'sum'),
    )
    # Wire entry → InitSum
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitSum'}]
    trace = run(sol)
    check('ForLoop sums 1..10 = 55 (auto-return body)',
          trace.status == 'completed' and trace.final_return_value == 55,
          f'status={trace.status} result={trace.final_return_value}')

    # WhileLoop countdown from 5.
    sol = solution(
        'countdown',
        entry(),
        assign('InitN', 'n', '5', 'InitCount'),
        assign('InitCount', 'count', '0', 'Loop'),
        node('Loop', 'WhileLoop', {'condition': 'n > 0'},
             outs=[['Dec'], ['Done']]),
        math('Dec', 'n', 'n', 'subtract', '1', 'Inc'),
        math('Inc', 'count', 'count', 'add', '1', ''),
        ret('Done', 'count'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitN'}]
    trace = run(sol)
    ctx = final_context(trace)
    check('WhileLoop counts 5 down to 0',
          trace.final_return_value == 5 and ctx.get('n') == 0,
          f'count={trace.final_return_value} n={ctx.get("n")}')

    # ForEachLoop over a JSON literal collection, with index variable.
    sol = solution(
        'total-items',
        entry(),
        assign('InitTotal', 'total', '0', 'Loop'),
        node('Loop', 'ForEachLoop',
             {'itemVariable': 'item', 'indexVariable': 'idx',
              'collection': '[1, 2, 3, 4]'},
             outs=[['Add'], ['Done']]),
        math('Add', 'total', 'total', 'add', 'item', ''),
        ret('Done', 'total'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitTotal'}]
    trace = run(sol)
    ctx = final_context(trace)
    check('ForEachLoop totals [1,2,3,4] = 10 with index var',
          trace.final_return_value == 10 and ctx.get('idx') == 3,
          f'total={trace.final_return_value} idx={ctx.get("idx")}')

    # Nested loops: 3×3 grid count.
    sol = solution(
        'nested-3x3',
        entry(),
        assign('InitCells', 'cells', '0', 'Outer'),
        node('Outer', 'ForLoop',
             {'iteratorVariable': 'i', 'startValue': 0, 'endValue': 3},
             outs=[['Inner'], ['Done']]),
        node('Inner', 'ForLoop',
             {'iteratorVariable': 'j', 'startValue': 0, 'endValue': 3},
             outs=[['Count'], []]),  # inner done-slot unwired → auto-return to Outer
        math('Count', 'cells', 'cells', 'add', '1', ''),
        ret('Done', 'cells'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitCells'}]
    trace = run(sol)
    check('nested 3×3 loops count 9 cells (inner exits to outer via dead-end)',
          trace.final_return_value == 9,
          f'cells={trace.final_return_value}')

    # Break: stop counting when i reaches 4.
    sol = solution(
        'break-at-4',
        entry(),
        assign('InitCount', 'count', '0', 'Loop'),
        node('Loop', 'ForLoop',
             {'iteratorVariable': 'i', 'startValue': 1, 'endValue': 100},
             outs=[['Check'], ['Done']]),
        node('Check', 'ConditionalChain', {'condition': {
            'leftOperand': 'i', 'operator': '>=', 'rightOperand': '4'}},
             outs=[['Stop'], ['Count']]),
        node('Stop', 'BreakStatement', {}, outs=[[]]),
        math('Count', 'count', 'count', 'add', '1', ''),
        ret('Done', 'count'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitCount'}]
    trace = run(sol)
    check('Break exits to the loop\'s done-slot (counted 3 before i=4)',
          trace.final_return_value == 3,
          f'count={trace.final_return_value}')

    # Continue: skip item 3.
    sol = solution(
        'skip-3',
        entry(),
        assign('InitTotal', 'total', '0', 'Loop'),
        node('Loop', 'ForEachLoop',
             {'itemVariable': 'item', 'collection': '[1, 2, 3, 4, 5]'},
             outs=[['Check'], ['Done']]),
        node('Check', 'ConditionalChain', {'condition': {
            'leftOperand': 'item', 'operator': '==', 'rightOperand': '3'}},
             outs=[['Skip'], ['Add']]),
        node('Skip', 'ContinueStatement', {}, outs=[[]]),
        math('Add', 'total', 'total', 'add', 'item', ''),
        ret('Done', 'total'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitTotal'}]
    trace = run(sol)
    check('Continue skips the matched item (1+2+4+5 = 12)',
          trace.final_return_value == 12,
          f'total={trace.final_return_value}')

    # Budget exhaustion: an honest, plain-language error.
    sol = solution(
        'runaway',
        entry(),
        node('Loop', 'WhileLoop',
             {'condition': '1 == 1', 'maxIterations': 5},
             outs=[['Noop'], ['Done']]),
        node('Noop', 'LogOutput', {'messageTemplate': 'tick'}, outs=[[]]),
        ret('Done', 'never'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'Loop'}]
    trace = run(sol)
    check('iteration budget exhausts with a plain-language error',
          trace.status == 'errored'
          and 'iteration budget' in (trace.error_summary or '')
          and 'maxIterations' in (trace.error_summary or ''),
          f'error={trace.error_summary}')

    # Break outside a loop: honest error.
    sol = solution(
        'stray-break',
        entry(),
        node('Stray', 'BreakStatement', {}, outs=[[]]),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'Stray'}]
    trace = run(sol)
    check('Break outside a loop errors plainly',
          trace.status == 'errored'
          and 'outside of a loop' in (trace.error_summary or ''),
          f'error={trace.error_summary}')


# ---------------------------------------------------------------------------
# P2 — collections
# ---------------------------------------------------------------------------

def _collections():
    print('\nTuring floor — collections\n')

    # Filter (x > 3) → Map (x * x) → Reduce (acc + x): [4,5,6] → [16,25,36] → 77.
    sol = solution(
        'filter-map-reduce',
        entry(),
        assign('InitList', 'nums', '[1, 2, 3, 4, 5, 6]', 'Filter'),
        node('Filter', 'FilterList',
             {'sourceVariable': 'nums', 'resultVariable': 'big',
              'itemVariable': 'x', 'filterCondition': {
                  'leftOperand': 'x', 'operator': '>', 'rightOperand': '3'}},
             outs=[['Map']]),
        node('Map', 'MapList',
             {'sourceVariable': 'big', 'resultVariable': 'squares',
              'itemVariable': 'x', 'expression': 'x * x'},
             outs=[['Reduce']]),
        node('Reduce', 'ReduceList',
             {'sourceVariable': 'squares', 'resultVariable': 'sum',
              'itemVariable': 'x', 'accumulatorVariable': 'acc',
              'initialValue': 0, 'expression': 'acc + x'},
             outs=[['Done']]),
        ret('Done', 'sum'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitList'}]
    trace = run(sol)
    ctx = final_context(trace)
    check('Filter → Map → Reduce chain (squares of >3 summed = 77)',
          trace.final_return_value == 77
          and ctx.get('big') == [4, 5, 6]
          and ctx.get('squares') == [16, 25, 36],
          f'sum={trace.final_return_value} big={ctx.get("big")}')
    check('element variable does not leak out of list operations',
          'x' not in ctx, f'x={ctx.get("x", "<absent>")!r}')

    # Dict + list verbs.
    sol = solution(
        'dict-and-list',
        entry(),
        node('SetA', 'CollectionOperation',
             {'operationType': 'dictSet', 'targetVariable': 'd',
              'key': '"a"', 'value': '5'}, outs=[['GetA']]),
        node('GetA', 'CollectionOperation',
             {'operationType': 'dictGet', 'targetVariable': 'd',
              'key': '"a"', 'resultVariable': 'got'}, outs=[['Push']]),
        node('Push', 'CollectionOperation',
             {'operationType': 'listAppend', 'targetVariable': 'lst',
              'value': 'got'}, outs=[['Push2']]),
        node('Push2', 'CollectionOperation',
             {'operationType': 'listAppend', 'targetVariable': 'lst',
              'value': '7'}, outs=[['Len']]),
        node('Len', 'CollectionOperation',
             {'operationType': 'listLength', 'targetVariable': 'lst',
              'resultVariable': 'n'}, outs=[['Done']]),
        ret('Done', 'n'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'SetA'}]
    trace = run(sol)
    ctx = final_context(trace)
    check('dict set/get + list append/length work',
          trace.final_return_value == 2 and ctx.get('got') == 5
          and ctx.get('lst') == [5, 7] and ctx.get('d') == {'a': 5},
          f'd={ctx.get("d")} lst={ctx.get("lst")}')


# ---------------------------------------------------------------------------
# P1 — validator entry, ValidationResult, EmitEvent
# ---------------------------------------------------------------------------

def _contracts():
    print('\nContract fixes — validator entry, verdicts, events\n')

    sol = solution(
        'gate-check',
        node('Enter', 'InitialConditionsValidatorEntry', {}, outs=[['Verdict']]),
        node('Verdict', 'ValidationResult',
             {'outcome': '"valid"',
              'reason': '"the ball holds together"',
              'derivedValues': {'ball_mass': {
                  'sourceType': 'from_source_object',
                  'sourceObjectPath': 'measured_mass'}}},
             outs=[]),
    )
    trace = run(sol, params={'measured_mass': 1.98})
    ctx = final_context(trace)
    check('InitialConditionsValidatorEntry is a working entry (no '
          '"No initial state found")',
          trace.status == 'completed', f'status={trace.status}')
    check('ValidationResult binds outcome + reason + derivedValues '
          '(the validator/gate contract)',
          ctx.get('outcome') == 'valid'
          and ctx.get('reason') == 'the ball holds together'
          and ctx.get('derivedValues') == {'ball_mass': 1.98},
          f'outcome={ctx.get("outcome")!r} derived={ctx.get("derivedValues")}')

    sol = solution(
        'pinger',
        entry(),
        node('Ping', 'EmitEvent',
             {'eventName': 'ping',
              'payload': {'value': {'sourceType': 'from_source_object',
                                    'sourceObjectPath': 'x'},
                          'label': '"hello"'}},
             outs=[]),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'Ping'}]
    trace = run(sol, params={'x': 42})
    ctx = final_context(trace)
    events = ctx.get(EMITTED_EVENTS_KEY) or []
    check('EmitEvent lands in _emitted_events with the documented shape',
          trace.status == 'completed' and len(events) == 1
          and events[0]['name'] == 'ping'
          and events[0]['payload'] == {'value': 42, 'label': 'hello'}
          and events[0]['sourceState'] == 'Ping',
          f'events={events}')


# ---------------------------------------------------------------------------
# THE LITMUS — iterative Fibonacci through the real engine.
# ---------------------------------------------------------------------------

def _litmus():
    print('\nLitmus — this is a programming language now\n')
    sol = solution(
        'fibonacci',
        entry(),
        assign('InitA', 'a', '0', 'InitB'),
        assign('InitB', 'b', '1', 'InitI'),
        assign('InitI', 'i', '0', 'Loop'),
        node('Loop', 'WhileLoop', {'condition': 'i < n'},
             outs=[['SaveB'], ['Done']]),
        assign('SaveB', 't', 'b', 'NextB'),
        math('NextB', 'b', 'a', 'add', 'b', 'ShiftA'),
        assign('ShiftA', 'a', 't', 'Inc'),
        math('Inc', 'i', 'i', 'add', '1', ''),
        ret('Done', 'a'),
    )
    sol['stateInstances'][0]['slots'][1]['connectors'] = [
        {'targetStateName': 'InitA'}]
    trace = run(sol, params={'n': 20})
    check('iterative Fibonacci(20) = 6765',
          trace.status == 'completed' and trace.final_return_value == 6765,
          f'result={trace.final_return_value}')
    trace30 = run(sol, params={'n': 30})
    check('and Fibonacci(30) = 832040 (same graph, different input)',
          trace30.final_return_value == 832040,
          f'result={trace30.final_return_value}')


if __name__ == '__main__':
    _loops()
    _collections()
    _contracts()
    _litmus()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
