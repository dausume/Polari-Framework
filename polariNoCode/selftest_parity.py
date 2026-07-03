"""
Self-test for no-code P5 — engine PARITY (Python side).

Run from polari-framework/:
    python3 -m polariNoCode.selftest_parity

THE CONFIGURATION IS THE ARTIFACT: the stored SolutionDefinition JSON is
interpreted by TWO engines — this Python engine on the backend and the
TypeScript mirror in the browser (polari-platform-angular
src/app/services/no-code-services/solution-engine/). The shared vectors
in polariNoCode/parity_vectors/*.json are executed by BOTH engines
(TS side: `npm run parity` in polari-platform-angular) and must produce
the same results AND the same user-facing error wording. This file is
the Python half of that contract.

Vector schema:
    solutions:   [{name, targetRuntime, contractJson?, definition}]
    entry:       which solution to execute
    inputParams: the entry inputs
    expect:      status / finalReturnValue / context / contextAbsent /
                 errorContains / events / verdictErrors
"""

import json
import os
from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine
from polariNoCode.stepping import StepConfig

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


VECTORS_DIR = os.path.join(os.path.dirname(__file__), 'parity_vectors')


def load_vectors():
    files = sorted(
        f for f in os.listdir(VECTORS_DIR) if f.endswith('.json'))
    out = []
    for fname in files:
        with open(os.path.join(VECTORS_DIR, fname)) as fh:
            out.append((fname, json.load(fh)))
    return out


def fake_manager(solutions):
    """Rows shaped like SolutionDefinition instances (name / definition /
    contract_json / target_runtime), keyed into objectTables the way
    _load_solution_row expects."""
    table = {}
    for i, s in enumerate(solutions):
        table[i] = SimpleNamespace(
            name=s['name'],
            definition=json.dumps(s['definition']),
            contract_json=json.dumps(s.get('contractJson') or {}),
            target_runtime=s.get('targetRuntime', 'python_backend'),
        )
    return SimpleNamespace(objectTables={'SolutionDefinition': table})


def final_context(trace):
    """Last step's context_after, unwrapped to plain {name: value}."""
    if not trace.steps:
        return {}
    variables = getattr(trace.steps[-1].context_after, 'variables', None) or {}
    out = {}
    for k, v in variables.items():
        out[k] = v.get('value') if isinstance(v, dict) and 'value' in v else v
    return out


def values_equal(expected, actual):
    """== with bool/number kept distinct (True must not satisfy 1)."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) \
            and expected == actual
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) \
            and all(values_equal(e, a) for e, a in zip(expected, actual))
    if isinstance(expected, dict):
        return isinstance(actual, dict) \
            and set(expected.keys()) == set(actual.keys()) \
            and all(values_equal(v, actual[k]) for k, v in expected.items())
    return expected == actual


def run_vector(fname, vector):
    print(f'\n--- {fname}: {vector["description"]}')
    solutions = {s['name']: s for s in vector['solutions']}
    entry = solutions[vector['entry']]
    engine = SolutionExecutionEngine(manager=fake_manager(vector['solutions']))
    trace = engine.execute(
        entry['definition'],
        input_params=dict(vector.get('inputParams') or {}),
        config=StepConfig(mode='step', record_context=True),
        target_runtime=entry.get('targetRuntime', 'python_backend'),
    )
    expect = vector['expect']
    ctx = final_context(trace)

    check(f'status == {expect["status"]}',
          trace.status == expect['status'],
          f'(got {trace.status}; error: {trace.error_summary})'
          if trace.status != expect['status'] else '')

    if 'finalReturnValue' in expect:
        check(f'finalReturnValue == {expect["finalReturnValue"]!r}',
              values_equal(expect['finalReturnValue'], trace.final_return_value),
              f'(got {trace.final_return_value!r})')

    for name, want in (expect.get('context') or {}).items():
        check(f'context[{name!r}] == {want!r}',
              name in ctx and values_equal(want, ctx[name]),
              f'(got {ctx.get(name)!r})')

    for name in expect.get('contextAbsent') or []:
        check(f'context has no {name!r}', name not in ctx,
              f'(got {ctx.get(name)!r})')

    for fragment in expect.get('errorContains') or []:
        summary = trace.error_summary or ''
        check(f'error mentions {fragment!r}', fragment in summary,
              f'(error was: {summary!r})')

    if 'events' in expect:
        emitted = ctx.get('_emitted_events') or []
        check(f'{len(expect["events"])} event(s) emitted',
              len(emitted) == len(expect['events']),
              f'(got {len(emitted)})')
        for want, got in zip(expect['events'], emitted):
            ok = isinstance(got, dict) \
                and got.get('name') == want['name'] \
                and got.get('channel') == want['channel'] \
                and (('payload' not in want)
                     or values_equal(want['payload'], got.get('payload')))
            check(f'event {want["name"]!r} on {want["channel"]!r} channel',
                  ok, f'(got {got!r})')

    for field, want_errors in (expect.get('verdictErrors') or {}).items():
        verdicts = ctx.get('_form_validation') or {}
        got_errors = (verdicts.get(field) or {}).get('errors')
        check(f'verdict for {field!r}: {want_errors!r}',
              values_equal(want_errors, got_errors),
              f'(got {got_errors!r})')


def main():
    vectors = load_vectors()
    print(f'Engine parity vectors (Python side): {len(vectors)} vector(s) '
          f'from {VECTORS_DIR}')
    for fname, vector in vectors:
        run_vector(fname, vector)
    passed, total = sum(results), len(results)
    print(f'\n{"=" * 60}\nParity (Python): {passed}/{total} checks passed')
    if passed != total:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
