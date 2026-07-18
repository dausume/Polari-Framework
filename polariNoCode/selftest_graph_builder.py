"""
Selftest — ncg-1: graph_builder + the compiler/orchestrator seam.

Run from polari-framework/:
    python3 -m polariNoCode.selftest_graph_builder

Covers: the promoted builder emits BYTE-IDENTICAL definitions to the
proven selftest dialect it was promoted from (the regression bar for
migrating the gates); built graphs execute through the real engine;
ConditionalChain slot-order semantics hold as documented; provenance
stamping rides the artifact without touching execution; the compiler
contract resolves/refuses/normalizes; advance() runs one orchestrator
step (merge -> execute -> outcome + final context).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


# --- the legacy dialect, verbatim (selftest_composition's shapes) ---

def _legacy_node(name, cls, fields=None, outs=None, index=0):
    slots = [{'isInput': True, 'connectors': []}]
    for targets in (outs if outs is not None else [[]]):
        slots.append({
            'isInput': False,
            'connectors': [{'targetStateName': t} for t in targets],
        })
    return {
        'stateName': name, 'stateClass': cls, 'boundObjectClass': cls,
        'boundObjectFieldValues': fields or {}, 'slots': slots,
        'index': index,
    }


def _legacy_solution(name, *states):
    return {'solutionName': name,
            'stateInstances': [dict(s, index=i)
                               for i, s in enumerate(states)]}


def _equivalence():
    print('builder ≡ proven selftest dialect')
    legacy = _legacy_solution(
        'sum-1-to-10',
        _legacy_node('Start', 'InitialState', {},
                     outs=[['InitSum']]),
        _legacy_node('InitSum', 'VariableAssignment',
                     {'variableName': 'sum', 'value': '0'},
                     outs=[['Loop']]),
        _legacy_node('Loop', 'ForLoop',
                     {'iteratorVariable': 'i', 'startValue': 1,
                      'endValue': 11, 'stepValue': 1},
                     outs=[['Add'], ['Done']]),
        _legacy_node('Add', 'MathOperation',
                     {'leftOperand': 'sum', 'operationType': 'add',
                      'rightOperand': 'i', 'resultVariable': 'sum'},
                     outs=[[]]),  # nxt='' = dead-end body (auto-return)
        _legacy_node('Done', 'ReturnValue',
                     {'returnValueSource': 'variable',
                      'variableName': 'sum'}, outs=[]),
    )
    built = gb.solution(
        'sum-1-to-10',
        gb.entry(nxt='InitSum'),
        gb.assign('InitSum', 'sum', '0', 'Loop'),
        gb.for_loop('Loop', 'i', 1, 11, 'Add', 'Done'),
        gb.math('Add', 'sum', 'sum', 'add', 'i', ''),
        gb.ret('Done', 'sum'),
    )
    check('identical definition dicts (the migration regression bar)',
          built == legacy)
    trace = gb.execute(built)
    check('built graph executes: sum 1..10 = 55',
          trace.status == 'completed'
          and trace.final_return_value == 55,
          f'status={trace.status} result={trace.final_return_value}')


def _conditionals():
    print('conditional slot-order semantics')
    sol = gb.solution(
        'age-gate',
        gb.entry(nxt='Check'),
        gb.cond('Check',
                [gb.link(gb.var_src('self.age'), 'greaterThanOrEqual',
                         gb.lit_src(18))],
                'Adult', 'Minor'),
        gb.ret_statement('Adult', 'adult'),
        gb.ret_statement('Minor', 'minor'),
    )
    adult = gb.execute(sol, params={'age': 30})
    minor = gb.execute(sol, params={'age': 12})
    check('true branch = FIRST output slot',
          adult.final_return_value == 'adult',
          f'got {adult.final_return_value!r}')
    check('false branch = second output slot',
          minor.final_return_value == 'minor',
          f'got {minor.final_return_value!r}')
    check('lit_src types bool before int (bool subclasses int)',
          gb.lit_src(True)['directValueType'] == 'bool'
          and gb.lit_src(1)['directValueType'] == 'int')
    wired = gb.wire(gb.cond('W', [], None, None), 1, 'Elsewhere')
    check('wire() rewires a chosen output slot post-hoc',
          wired['slots'][2]['connectors']
          == [{'targetStateName': 'Elsewhere'}])


def toy_compiler(domain_rows):
    """Fork-shaped toy: one criterion row -> one small graph."""
    threshold = domain_rows['threshold']
    return gb.solution(
        'toy-fork',
        gb.entry(nxt='Judge'),
        gb.cond('Judge',
                [gb.link(gb.var_src('self.determination'),
                         'greaterThanOrEqual', gb.lit_src(threshold))],
                'Met', 'NotMet'),
        gb.ret_statement('Met', 'criterion-met'),
        gb.ret_statement('NotMet', 'criterion-not-met'),
    )


class _Row:
    """Duck-typed compiler row (real GraphCompilerDefinition rows are
    exercised against a live manager in ncg-2)."""
    name = 'toy'
    domain = 'selftest'
    compiler_ref = ('polariNoCode.selftest_graph_builder'
                    ':toy_compiler')
    enabled = True


def _compiler_contract():
    print('compiler contract')
    result = gc.compile_with(_Row(), {'threshold': 3})
    definition = result['definition']
    check('bare-definition compilers normalize to {definition, artifacts}',
          result['artifacts'] == []
          and definition['solutionName'] == 'toy-fork')
    check('provenance auto-stamped with compiler + source rows',
          definition['compiledBy']['compiler'] == 'toy'
          and definition['compiledBy']['sourceRows'] == ['threshold'])
    trace = gb.execute(definition, params={'determination': 5})
    check('stamped definition still executes (engines ignore the stamp)',
          trace.status == 'completed'
          and trace.final_return_value == 'criterion-met')
    disabled = _Row()
    disabled.enabled = False
    try:
        gc.compile_with(disabled, {})
        refused = False
    except RuntimeError as exc:
        refused = 'disabled' in str(exc)
    check('disabled compiler refuses plainly (the knob)', refused)
    try:
        gc.resolve_compiler('no-colon-here')
        bad_ref = False
    except ValueError:
        bad_ref = True
    check("malformed compiler_ref fails with a plain error", bad_ref)


def _orchestrator():
    print('orchestrator step (advance)')
    compiled = toy_compiler({'threshold': 10})
    stored = {'case_fact': 'accumulated', 'determination': 0}
    step = gc.advance(compiled, stored, {'determination': 12})
    check('fresh input overrides stored context for this step',
          step['outcome'] == 'criterion-met'
          and step['status'] == 'completed')
    check('final_context carries the merged facts back for persisting',
          step['final_context'].get('case_fact') == 'accumulated'
          and step['final_context'].get('determination') == 12)
    step = gc.advance(compiled, stored, {})
    check('absent input falls back to stored context (not-met path)',
          step['outcome'] == 'criterion-not-met')


def main():
    _equivalence()
    _conditionals()
    _compiler_contract()
    _orchestrator()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
