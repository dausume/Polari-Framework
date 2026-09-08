"""
Selftest — ncg-2: judicial adjudication on the no-code seam.

Run from polari-framework/:
    python3 -m scoring.court_case_selftest

Walks a WHOLE case through a two-fork decision procedure with the
judge's determination supplied BETWEEN engine runs (the no-pause
orchestrator pattern): create at the start edge, an illegal
determination refused with the legal outcomes named, consent fork
routes to the harm fork, harm fork routes to a terminal, the audit
log records every step, a concluded case refuses further advances.
Every fork execution goes through the REAL SolutionExecutionEngine
via a graph the registered judicial-fork compiler emitted — this
selftest is the standing litmus that the generalization seam still
serves the judicial client.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring.court_case_basis import (advance_case, case_report,
                                compile_fork_graph, create_court_case,
                                fork_outcomes)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


PROCEDURE = 'demo-trial-procedure'


def _criterion(name, fork, description, default=True):
    return SimpleNamespace(
        name=name, display_name=name, description=description,
        decision_procedure_name=PROCEDURE, fork_name=fork,
        is_current_default=default, proposed_by='selftest')


def _edge(name, from_fork, from_outcome, to_fork='', to_terminal=''):
    return SimpleNamespace(
        name=name, decision_procedure_name=PROCEDURE,
        from_fork=from_fork, from_outcome=from_outcome,
        to_fork=to_fork, to_terminal=to_terminal, description='')


def _mgr():
    """Two-fork procedure: start -> consent-fork; consent-established
    -> harm-fork; consent-not-established -> ACQUITTAL; harm-proven
    -> CONVICTED; harm-not-proven -> ACQUITTAL. idList: the minimum
    treeObjectInit needs to mint ids against a fake manager."""
    return SimpleNamespace(idList=[], objectTables={
        'LogicForkCriterion': {
            1: _criterion('consent-criterion', 'consent-fork',
                          'Was informed consent established beyond '
                          'reasonable doubt?'),
            2: _criterion('harm-criterion', 'harm-fork',
                          'Was material harm proven to result?'),
        },
        'LogicForkVote': {},
        'LogicForkBallot': {},
        'DecisionProcedureEdge': {
            1: _edge('e-start', '', '', to_fork='consent-fork'),
            2: _edge('e-consent-yes', 'consent-fork',
                     'consent-established', to_fork='harm-fork'),
            3: _edge('e-consent-no', 'consent-fork',
                     'consent-not-established',
                     to_terminal='ACQUITTAL'),
            4: _edge('e-harm-yes', 'harm-fork', 'harm-proven',
                     to_terminal='CONVICTED'),
            5: _edge('e-harm-no', 'harm-fork', 'harm-not-proven',
                     to_terminal='ACQUITTAL'),
        },
        'CourtCase': {},
        'GraphCompilerDefinition': {},
    })


def _compiler():
    print('the compiled fork graph (seam client)')
    graph = compile_fork_graph({
        'fork': 'consent-fork',
        'criterion': 'Was consent established?',
        'outcomes': ['consent-established', 'consent-not-established'],
    })
    check('one small solution per fork, named for it',
          graph['solutionName'] == 'fork--consent-fork')
    check('provenance stamps compiler + fork + outcomes',
          graph['compiledBy']['compiler'] == 'judicial-fork'
          and 'fork:consent-fork' in graph['compiledBy']['sourceRows'])
    classes = [s['stateClass'] for s in graph['stateInstances']]
    check('entry + one ConditionalChain per outcome + honest '
          'unrecognized terminal',
          classes.count('ConditionalChain') == 2
          and classes.count('ReturnStatement') == 3)
    check('the criterion text rides the chain for the D3 editor',
          any('Was consent established?'
              in str(s['boundObjectFieldValues'].get('displayName'))
              for s in graph['stateInstances']
              if s['stateClass'] == 'ConditionalChain'))
    try:
        compile_fork_graph({'fork': 'f', 'criterion': 'c',
                            'outcomes': []})
        refused = False
    except ValueError as exc:
        refused = 'DecisionProcedureEdge' in str(exc)
    check('a fork with no outcomes refuses with the edge suggestion',
          refused)


def _lifecycle():
    print('case lifecycle (context flows, judge input between runs)')
    m = _mgr()
    result = create_court_case(
        m, 'case-001', PROCEDURE,
        initial_context={'defendant': 'subject-x',
                         'charge': 'demo-charge'},
        adjudicator_type='jury', adjudicator_name='jury-panel-7')
    check('case opens at the start edge fork',
          result['ok']
          and result['case']['currentFork'] == 'consent-fork'
          and result['case']['status'] == 'in-progress')
    check('duplicate case name refuses',
          not create_court_case(m, 'case-001', PROCEDURE)['ok'])
    check('fork outcomes read from the edge rows',
          fork_outcomes(m, PROCEDURE, 'consent-fork')
          == ['consent-established', 'consent-not-established'])

    bad = advance_case(m, 'case-001', 'maybe-sort-of')
    check('illegal determination refused, legal outcomes named',
          not bad['ok'] and 'consent-established'
          in bad['legalOutcomes'])
    check('a refused determination changes nothing',
          case_report(m, 'case-001')['currentFork'] == 'consent-fork'
          and case_report(m, 'case-001')['executionLog'] == [])

    step1 = advance_case(m, 'case-001', 'consent-established',
                         supplied_by='jury-panel-7')
    check('fork 1 routes through the REAL engine to the next fork',
          step1['ok'] and step1['outcome'] == 'consent-established'
          and step1['nextFork'] == 'harm-fork'
          and step1['compiledSolution'] == 'fork--consent-fork')
    report = case_report(m, 'case-001')
    check('initial context flowed through and survived the run',
          report['context'].get('defendant') == 'subject-x'
          and report['context'].get('charge') == 'demo-charge')
    check('audit log records fork/criterion/determination/next',
          len(report['executionLog']) == 1
          and report['executionLog'][0]['fork'] == 'consent-fork'
          and report['executionLog'][0]['criterion']
          == 'consent-criterion'
          and report['executionLog'][0]['next'] == 'harm-fork')

    step2 = advance_case(m, 'case-001', 'harm-not-proven',
                         supplied_by='jury-panel-7')
    check('fork 2 reaches the terminal and concludes the case',
          step2['ok'] and step2['terminal'] == 'ACQUITTAL'
          and step2['status'] == 'ACQUITTAL')
    report = case_report(m, 'case-001')
    check('concluded case: no current fork, two logged steps',
          report['currentFork'] is None
          and len(report['executionLog']) == 2)
    check('a concluded case refuses further advances',
          not advance_case(m, 'case-001', 'harm-proven')['ok'])


def _review_regressions():
    print('review-fix regressions (verdict hijack + reserved keys)')
    m = _mgr()
    # THE HIJACK (review finding, was silently mis-routing): a case
    # fact KEYED by an outcome label must not become the verdict.
    create_court_case(
        m, 'case-hijack', PROCEDURE,
        initial_context={'consent-established':
                         'consent-not-established'})
    step = advance_case(m, 'case-hijack', 'consent-established')
    check('a fact keyed by an outcome label cannot hijack the '
          'verdict', step['ok']
          and step['outcome'] == 'consent-established'
          and step['nextFork'] == 'harm-fork')
    check("reserved fact key 'determination' refused at create",
          not create_court_case(
              m, 'case-r1', PROCEDURE,
              initial_context={'determination': 'x'})['ok'])
    check('reserved outcome-prefix determination refused',
          not advance_case(m, 'case-hijack',
                           '__outcome__:harm-proven')['ok'])
    check("a case may not be named 'create' (route shadow)",
          not create_court_case(m, 'create', PROCEDURE)['ok'])
    check('non-string case name refused honestly',
          not create_court_case(m, {}, PROCEDURE)['ok']
          and not advance_case(m, ['x'], 'y')['ok'])
    report = case_report(m, 'case-hijack')
    check("the persisted fact bag never carries 'determination'",
          'determination' not in report['context']
          and report['executionLog'][0]['determination']
          == 'consent-established')

    nowhere = _mgr()
    nowhere.objectTables['DecisionProcedureEdge'][3] = _edge(
        'e-broken', 'consent-fork', 'consent-not-established')
    create_court_case(nowhere, 'case-n', PROCEDURE)
    step = advance_case(nowhere, 'case-n', 'consent-not-established')
    check('an edge routing NOWHERE is an error naming the edge row',
          not step['ok'] and 'e-broken' in step['error']
          and case_report(nowhere, 'case-n')['status']
          == 'in-progress')


def _honesty():
    print('honest refusals')
    m = _mgr()
    check('unknown case named plainly',
          not advance_case(m, 'nope', 'x')['ok'])
    check('unknown case report lists known cases',
          case_report(m, 'nope')['knownCases'] == [])
    empty = SimpleNamespace(objectTables={
        'LogicForkCriterion': {}, 'LogicForkVote': {},
        'LogicForkBallot': {}, 'DecisionProcedureEdge': {},
        'CourtCase': {}, 'GraphCompilerDefinition': {}})
    check('procedure without a start edge refuses at creation',
          not create_court_case(empty, 'c', 'nowhere')['ok'])

    m2 = _mgr()
    m2.objectTables['LogicForkCriterion'][1].is_current_default = False
    create_court_case(m2, 'case-002', PROCEDURE)
    unresolved = advance_case(m2, 'case-002', 'consent-established')
    check('fork without a resolved criterion refuses with the knob',
          not unresolved['ok']
          and 'resolved' in unresolved['error'])

    m3 = _mgr()
    m3.objectTables['GraphCompilerDefinition']['judicial-fork'] = (
        SimpleNamespace(name='judicial-fork', domain='judicial',
                        compiler_ref='scoring.court_case_basis'
                                     ':compile_fork_graph',
                        enabled=False))
    create_court_case(m3, 'case-003', PROCEDURE)
    disabled = advance_case(m3, 'case-003', 'consent-established')
    check('disabled compiler row gates advancement (the knob)',
          not disabled['ok'] and 'disabled' in disabled['error'])


def main():
    _compiler()
    _lifecycle()
    _review_regressions()
    _honesty()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
