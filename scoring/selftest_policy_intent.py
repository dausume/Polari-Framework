"""
Selftest — drafter-set PolicyIntent.

Run from polari-framework/:
    python3 -m scoring.selftest_policy_intent

Covers: only the draft's drafters may set intent (the refusal quotes
the participation rule); the supersede chain is append-only and the
current intent resolves; a draft with no intent reads back honestly;
the stated intent feeds the REAL scr-5 abstraction matcher and
yields term suggestions against the col-1 DMV vocabulary; the probe
row the matcher rides never survives the call; multi-author
drafted_by_json fallback works.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring.dmv_col_seed import SEED_DMV_TERMS
from scoring.policy_drafts import create_draft
from scoring.policy_intent import (WHO_MAY_SET, current_intent,
                                   intent_chain, intent_suggestions,
                                   set_policy_intent)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    m = SimpleNamespace(idList=[], objectTables={
        'PolicyDraft': {}, 'PolicyIntent': {}, 'ScoreAssertion': {},
        'ScoreTerm': {}, 'ScoreConcept': {}, 'Contributor': {}},
        db=None)
    for seed in SEED_DMV_TERMS:
        m.objectTables['ScoreTerm'][seed['name']] = SimpleNamespace(
            **seed)
    created = create_draft(m, 'affordable-homes-act',
                           drafted_by='alice',
                           description='starter homes measure')
    assert created['ok'], created
    return m


def _drafter_gate():
    print('who may set intent (the participation rule)')
    m = _mgr()
    ok = set_policy_intent(
        m, 'affordable-homes-act', 'alice',
        'improve how long housing lasts and reduce rent burden',
        expected_outcomes=['more durable starter homes'],
        set_at='2026-07-16T10:00:00')
    check('the drafter sets their own intent', ok['ok']
          and ok['supersedes'] is None)
    refused = set_policy_intent(m, 'affordable-homes-act', 'bob',
                                'gut the bill')
    check('a non-drafter is refused, quoting the rule',
          not refused['ok'] and WHO_MAY_SET in refused['error']
          and refused['drafters'] == ['alice'])
    check('unknown draft refused with known drafts listed',
          'affordable-homes-act' in set_policy_intent(
              m, 'nope', 'alice', 'x')['knownDrafts'])
    check('an empty intent statement is refused',
          not set_policy_intent(m, 'affordable-homes-act', 'alice',
                                '   ')['ok'])


def _supersede_chain():
    print('the append-only supersede chain')
    m = _mgr()
    first = set_policy_intent(m, 'affordable-homes-act', 'alice',
                              'reduce rent burden',
                              set_at='2026-07-16T10:00:00')
    second = set_policy_intent(
        m, 'affordable-homes-act', 'alice',
        'reduce rent burden AND improve housing longevity',
        set_at='2026-07-16T11:00:00')
    check('a restated intent supersedes the first',
          second['ok'] and second['supersedes'] == first['intent'])
    chain = intent_chain(m, 'affordable-homes-act')
    check('the chain keeps both, oldest first, pointer set',
          len(chain) == 2
          and getattr(chain[0], 'superseded_by', '')
          == second['intent']
          and getattr(chain[1], 'superseded_by', '') == '')
    current = current_intent(m, 'affordable-homes-act')
    check('current intent resolves to the latest statement',
          current['intent'] == second['intent']
          and 'longevity' in current['intentText']
          and current['chainLength'] == 2)

    m2 = _mgr()
    none = current_intent(m2, 'affordable-homes-act')
    check('a draft with no intent reads back honestly '
          '(participation is a choice)',
          none['ok'] and none['intent'] is None
          and WHO_MAY_SET in none['note'])


def _suggestions():
    print('intent feeds the REAL scr-5 matcher')
    m = _mgr()
    set_result = set_policy_intent(
        m, 'affordable-homes-act', 'alice',
        'improve how long housing lasts and reduce severe rent '
        'burden for households',
        set_at='2026-07-16T10:00:00')
    result = intent_suggestions(m, set_result['intent'])
    check('suggestions come back for the drafter-stated intent',
          result['ok'] and result.get('suggestions'))
    suggested = json.dumps(result.get('suggestions', []))
    check('a longevity term from the DMV vocabulary is suggested',
          'housing-stock-median-age' in suggested
          or 'structural-problem-rate' in suggested, suggested[:120])
    check('the knobs-not-bindings note rides the result',
          'never auto-applied' in result.get('note', ''))
    check('the transient probe row never survives the call',
          not any(k.startswith('intent-probe--')
                  for k in m.objectTables['ScoreAssertion']))
    check('unknown intent refused listing known ones',
          set_result['intent'] in intent_suggestions(
              m, 'intent-nope')['knownIntents'])


def _multi_author():
    print('multi-author drafted_by_json fallback')
    m = _mgr()
    m.objectTables['PolicyDraft']['omnibus-draft'] = SimpleNamespace(
        name='omnibus-draft', drafted_by='alice',
        drafted_by_json=json.dumps(
            [{'kind': 'legislator', 'name': 'alice'},
             {'kind': 'staff', 'name': 'grace'}]))
    ok = set_policy_intent(m, 'omnibus-draft', 'grace',
                           'co-author states intent',
                           set_at='2026-07-16T10:00:00')
    check('a drafted_by_json co-author may set intent', ok['ok'])
    refused = set_policy_intent(m, 'omnibus-draft', 'mallory', 'x')
    check('a stranger is still refused with the full drafter list',
          not refused['ok']
          and refused['drafters'] == ['alice', 'grace'])


def main():
    _drafter_gate()
    _supersede_chain()
    _suggestions()
    _multi_author()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
