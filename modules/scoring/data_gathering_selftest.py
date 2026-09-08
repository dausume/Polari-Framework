"""
Selftest — DataGatheringSolutions on the graph seam.

Run from polari-framework/:
    python3 -m scoring.data_gathering_selftest

Two organizations declare, step by step, how they gather data for
two logically equivalent rent terms (a survey procedure vs an
administrative-records procedure). The procedures COMPILE through
the real graph-compiler seam and EXECUTE in the real engine: all
validations submitted-and-true completes the happy path; a failed
(or unsubmitted) validation routes to a terminal naming exactly the
failed step. Step-credibility assertions require reasons; the
comparison lines both procedures up and deliberately declares NO
winner — legitimacy belongs to votes.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from polariNoCode import graph_builder as gb
from polariNoCode.graph_compilers import compile_with
from scoring import data_gathering_basis as dg

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


SURVEY_STEPS = [
    {'stepId': 'design-sample', 'kind': 'collection',
     'description': 'draw a stratified sample of rental units',
     'method': 'random sample from the rental license registry',
     'toolOrSource': 'moco-licensing-et5s-xste'},
    {'stepId': 'field-survey', 'kind': 'collection',
     'description': 'survey each sampled unit for asked rent',
     'method': 'mailed questionnaire + phone follow-up',
     'toolOrSource': 'survey instrument v3'},
    {'stepId': 'submit-batch', 'kind': 'submission',
     'description': 'submit the collected batch for review',
     'method': 'monthly batch upload', 'toolOrSource': 'portal'},
    {'stepId': 'check-response-rate', 'kind': 'validation',
     'description': 'response rate meets the 60% floor',
     'method': 'responses / sampled >= 0.6', 'toolOrSource': ''},
    {'stepId': 'check-outliers', 'kind': 'validation',
     'description': 'no unexplained rent outliers remain',
     'method': 'IQR fence review, each outlier annotated',
     'toolOrSource': ''},
]

ADMIN_STEPS = [
    {'stepId': 'pull-registry', 'kind': 'collection',
     'description': 'pull registered rents from the rent registry',
     'method': 'bulk export', 'toolOrSource': 'dc-rent-registry'},
    {'stepId': 'dedupe-units', 'kind': 'transformation',
     'description': 'deduplicate units across filings',
     'method': 'address+unit normalization', 'toolOrSource': ''},
    {'stepId': 'submit-extract', 'kind': 'submission',
     'description': 'submit the deduplicated extract',
     'method': 'quarterly extract', 'toolOrSource': 'portal'},
    {'stepId': 'check-coverage', 'kind': 'validation',
     'description': 'extract covers >= 90% of licensed units',
     'method': 'extract rows / licensed units >= 0.9',
     'toolOrSource': ''},
]


def _term(name, equivalents):
    return SimpleNamespace(
        name=name, equivalent_terms_json=json.dumps(equivalents))


def _solution(name, group, term, steps):
    return SimpleNamespace(
        name=name, display_name=name, organization_group=group,
        term_name=term, source_names_json='["census-acs"]',
        steps_json=json.dumps(steps), compiled_solution_name='',
        version=1, status='active', notes='')


def _mgr():
    return SimpleNamespace(idList=[], db=None, objectTables={
        'DataGatheringSolution': {
            'survey-rents': _solution(
                'survey-rents', 'tenant-union', 'surveyed-rent',
                SURVEY_STEPS),
            'admin-rents': _solution(
                'admin-rents', 'housing-office', 'registered-rent',
                ADMIN_STEPS),
        },
        'StepCredibilityAssertion': {},
        'GraphCompilerDefinition': {},
        'ScoreTerm': {
            1: _term('surveyed-rent', ['registered-rent']),
            2: _term('registered-rent', ['surveyed-rent']),
        },
    })


_DUCK_ROW = SimpleNamespace(
    name=dg.GATHERING_COMPILER_NAME, domain='data-gathering',
    compiler_ref=dg.GATHERING_COMPILER_REF, enabled=True)


def _compilation():
    print('the seam client (compile through the REAL contract)')
    m = _mgr()
    result = compile_with(_DUCK_ROW, {'manager': m,
                                      'solution_name': 'survey-rents'})
    definition = result['definition']
    check('procedure compiles to one small solution',
          definition['solutionName'] == 'gathering--survey-rents')
    check('compiled definition carries compiledBy provenance',
          definition['compiledBy']['compiler'] == 'data-gathering'
          and 'step:check-outliers'
          in definition['compiledBy']['sourceRows'])
    classes = [s['stateClass'] for s in definition['stateInstances']]
    check('each validation step is a gating ConditionalChain',
          classes.count('ConditionalChain') == 2)
    check('non-validation steps ride the trace as the procedure '
          'narrative',
          classes.count('VariableAssignment') == 3)
    try:
        compile_with(_DUCK_ROW, {'manager': m,
                                 'solution_name': 'nope'})
        refused = False
    except ValueError as exc:
        refused = 'known' in str(exc)
    check('unknown solution refused listing known ones', refused)

    dup = _mgr()
    bad_steps = SURVEY_STEPS[:1] + SURVEY_STEPS[:1]
    dup.objectTables['DataGatheringSolution'][
        'survey-rents'].steps_json = json.dumps(bad_steps)
    try:
        compile_with(_DUCK_ROW, {'manager': dup,
                                 'solution_name': 'survey-rents'})
        refused = False
    except ValueError as exc:
        refused = 'duplicate stepId' in str(exc)
    check('duplicate stepId is a plain error', refused)


def _walkthrough():
    print('executing the procedure (real engine)')
    m = _mgr()
    run = dg.run_gathering_walkthrough(
        m, 'survey-rents', {'check-response-rate_ok': True,
                            'check-outliers_ok': True})
    check('all validations submitted-and-true -> happy path',
          run['ok'] and run['outcome'] == dg.ALL_PASSED
          and run['validationsPassed']
          == ['check-response-rate', 'check-outliers']
          and not run['validationsFailed'])

    run = dg.run_gathering_walkthrough(
        m, 'survey-rents', {'check-response-rate_ok': True,
                            'check-outliers_ok': False})
    check('a failed validation names exactly the failed step',
          run['ok']
          and run['outcome'] == 'validation-failed:check-outliers'
          and run['validationsFailed'] == ['check-outliers']
          and run['validationsPassed'] == ['check-response-rate'])

    run = dg.run_gathering_walkthrough(m, 'survey-rents', {})
    check('an UNSUBMITTED validation honestly fails (never a '
          'silent pass)',
          run['ok'] and run['validationsFailed']
          == ['check-response-rate']
          and 'check-outliers' in run['validationsUnreached'])

    run = dg.run_gathering_walkthrough(m, 'missing', {})
    check('unknown solution -> honest error with known list',
          not run['ok'] and 'survey-rents' in run['knownSolutions'])
    run = dg.run_gathering_walkthrough(m, 'survey-rents',
                                       'not-a-dict')
    check('non-dict submissions refused plainly',
          not run['ok'] and 'dict' in run['error'])


def _step_assertions():
    print('step-credibility assertions (reasons required)')
    m = _mgr()
    filed = dg.assert_step_credibility(
        m, 'survey-rents', 'check-response-rate', 'adds',
        reason='a response-rate floor guards against '
               'self-selection bias',
        asserted_by='methodologist-a',
        on_behalf_of_group='stats-guild')
    check('assertion with a reason lands as asserted (votes '
          'adjudicate)',
          filed['ok'] and filed['status'] == 'asserted'
          and 'not a ruling' in filed['note'])
    refused = dg.assert_step_credibility(
        m, 'survey-rents', 'check-response-rate', 'subtracts',
        reason='   ', asserted_by='someone')
    check('an empty reason is refused — the WHY is the point',
          not refused['ok'] and 'reason' in refused['error'].lower())
    refused = dg.assert_step_credibility(
        m, 'survey-rents', 'no-such-step', 'adds', reason='r',
        asserted_by='someone')
    check('unknown step lists the valid stepIds',
          not refused['ok']
          and 'design-sample' in refused['validStepIds'])
    refused = dg.assert_step_credibility(
        m, 'survey-rents', 'field-survey', 'sideways', reason='r',
        asserted_by='someone')
    check('direction restricted to adds|subtracts',
          not refused['ok'])

    dg.assert_step_credibility(
        m, 'survey-rents', 'field-survey', 'subtracts',
        reason='phone follow-up rewords questions inconsistently',
        asserted_by='methodologist-b')
    profile = dg.gathering_credibility_profile(m, 'survey-rents')
    by_id = {s['stepId']: s for s in profile['steps']}
    check('profile groups assertions by direction with reasons',
          profile['ok']
          and len(by_id['check-response-rate']
                  ['credibility']['adds']) == 1
          and by_id['field-survey']['credibility']['subtracts'][0]
          ['reason'].startswith('phone follow-up'))
    check('validation coverage counted',
          profile['validationCoverage'] == 2)


def _comparison():
    print('comparing procedures behind equivalent terms')
    m = _mgr()
    dg.assert_step_credibility(
        m, 'admin-rents', 'pull-registry', 'adds',
        reason='registry rents are filings, not recollections',
        asserted_by='methodologist-a')
    comparison = dg.compare_gathering_solutions(m, ['surveyed-rent'])
    check('equivalence expansion pulls BOTH procedures in',
          comparison['ok'] and len(comparison['procedures']) == 2
          and comparison['termsCompared']
          == ['registered-rent', 'surveyed-rent'])
    entries = {e['solution']: e for e in comparison['procedures']}
    check('side-by-side: steps, validation coverage, sources, '
          'assertion counts',
          entries['survey-rents']['validationCoverage'] == 2
          and entries['admin-rents']['validationCoverage'] == 1
          and entries['admin-rents']['credibilityAssertions']['adds']
          == 1
          and entries['survey-rents']['sourcesCited']
          == ['census-acs'])
    all_keys = set(comparison) | {
        key for entry in comparison['procedures'] for key in entry}
    check('NO winner declared (a reading — votes decide legitimacy)',
          not ({'winner', 'ranking', 'best', 'score'} & all_keys)
          and 'votes' in comparison['note'])
    empty = dg.compare_gathering_solutions(m, [])
    check('empty term list refused plainly', not empty['ok'])
    none = dg.compare_gathering_solutions(m, ['no-procedures-term'])
    check('no procedures -> suggestion naming the row knob',
          not none['ok']
          and none['suggestion']['knob'] == 'DataGatheringSolution')


def main():
    _compilation()
    _walkthrough()
    _step_assertions()
    _comparison()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
