"""
Selftest — policy drafts as scoreable subjects.

Run from polari-framework/:
    python3 -m scoring.policy_drafts_selftest

Covers: the validated draft lifecycle (+ invalid transitions refused
with history intact), THE key capability — a draft's ScoreSubject
binds a REAL ScoreAssertion through the unchanged assertions.py
machinery and a REAL ScoreConcept scores it through the standard
engine — enactment linking, carryover queryability, and terminal
statuses refusing further movement.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import policy_drafts_basis as pd
from scoring.assertions_basis import ScoreAssertion, transition_assertion
from scoring.score_concept_basis import ScoreConcept
from scoring.scoring_basis import (ContextualizedValue, ScoreContext,
                                   ScoreSubject, ScoreTerm)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def _row(m, table, name):
    return next((r for r in m.objectTables[table].values()
                 if getattr(r, 'name', '') == name), None)


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    return SimpleNamespace(idList=[], db=None, objectTables={
        'PolicyDraft': {}, 'ScoreSubject': {}, 'ScoreAssertion': {},
        'ContextualizedValue': {}, 'ScoreTerm': {},
        'ScoreConcept': {}, 'ScoreContext': {}})


def _lifecycle():
    print('draft lifecycle (validated transitions + history)')
    m = _mgr()
    result = pd.create_draft(
        m, 'rent-relief-act-draft',
        display_name='Rent Relief Act',
        drafted_by='contrib-alice', jurisdiction_subject_name='dc')
    check('draft created at status draft',
          result['ok'] and result['status'] == 'draft')
    check('duplicate name refused',
          not pd.create_draft(m, 'rent-relief-act-draft')['ok'])

    moved = pd.transition_draft(m, 'rent-relief-act-draft',
                                'introduced', by='contrib-alice')
    check('draft -> introduced allowed',
          moved['ok'] and moved['historyLength'] == 1)
    bad = pd.transition_draft(m, 'rent-relief-act-draft', 'enacted')
    draft = _row(m, 'PolicyDraft', 'rent-relief-act-draft')
    check('introduced -> enacted refused (must pass first), '
          'history intact',
          not bad['ok'] and 'enacted' not in bad['allowed']
          and len(json.loads(draft.history_json)) == 1)
    check('the refusal names the allowed transitions',
          not bad['ok'] and 'in-committee' in bad['allowed'])
    check('unknown status refused listing statuses',
          not pd.transition_draft(m, 'rent-relief-act-draft',
                                  'vibing')['ok'])

    pd.transition_draft(m, 'rent-relief-act-draft', 'withdrawn')
    stuck = pd.transition_draft(m, 'rent-relief-act-draft',
                                'introduced')
    check('withdrawn is terminal — refuses further transitions',
          not stuck['ok'] and stuck['allowed'] == [])


def _scoring_binds():
    print('THE capability: assertions + concepts bind to drafts '
          'through the UNCHANGED machinery')
    m = _mgr()
    pd.create_draft(m, 'wage-floor-draft',
                    display_name='Wage Floor Update')
    made = pd.ensure_draft_subject(m, 'wage-floor-draft')
    check('draft subject minted (kind policy-draft, objectRef '
          'anchored)',
          made['ok'] and made['created']
          and _row(m, 'ScoreSubject', made['subject']).kind == 'policy-draft')
    check('ensure is idempotent',
          pd.ensure_draft_subject(
              m, 'wage-floor-draft')['created'] is False)

    subject = made['subject']
    assertion = ScoreAssertion(
        name='assert-wage-floor-draft-impact',
        subject_name=subject,
        intent='raises the wage floor for hourly workers',
        assertion_type='score-impact', direction='supports',
        asserted_by='contrib-bob', status='asserted',
        manager=None)
    m.objectTables['ScoreAssertion'][assertion.name] = assertion
    moved = transition_assertion(m, assertion.name, 'under-review',
                                 by='reviewer-1')
    check('a REAL assertions.py transition works on the draft-bound '
          'assertion', moved.get('ok', False) is not False
          and assertion.status == 'under-review')

    m.objectTables['ScoreTerm']['draft-support-share'] = ScoreTerm(
        name='draft-support-share', display_name='Support share',
        unit='ratio', is_positive=True, manager=None)
    m.objectTables['ScoreContext']['year-2026'] = ScoreContext(
        name='year-2026', display_name='2026',
        context_type='timeframe', manager=None)
    m.objectTables['ContextualizedValue']['dss@draft'] = (
        ContextualizedValue(
            name='dss@draft', term_name='draft-support-share',
            subject_name=subject,
            context_names_json='["year-2026"]',
            pre_normalized_value=0.62, manager=None))
    m.objectTables['ScoreConcept']['draft-viability'] = ScoreConcept(
        name='draft-viability', display_name='Draft viability',
        subject_kind='policy-draft',
        subject_names_json=json.dumps([subject]),
        term_weights_json=json.dumps(
            [{'term': 'draft-support-share', 'weight': 1}]),
        manager=None)
    from scoring.custom.scoring_engine import score_concept
    scored = score_concept(m, 'draft-viability')
    subjects = scored.get('subjects') or scored.get('perSubject') \
        or []
    check('the STANDARD engine scores a concept over the DRAFT '
          'subject (real score_concept run)',
          scored.get('ok') and bool(subjects),
          str(scored)[:120] if not scored.get('ok') else '')


def _enactment():
    print('enactment link + carryover')
    m = _mgr()
    pd.create_draft(m, 'transit-fund-draft')
    pd.ensure_draft_subject(m, 'transit-fund-draft')
    subject = pd.draft_subject_name('transit-fund-draft')
    m.objectTables['ScoreAssertion']['a1'] = ScoreAssertion(
        name='a1', subject_name=subject,
        intent='expands transit funding', asserted_by='c1',
        manager=None)
    for status in ('introduced', 'in-committee', 'passed'):
        pd.transition_draft(m, 'transit-fund-draft', status)

    missing = pd.enact_draft(m, 'transit-fund-draft',
                             'policy-transit-fund')
    check('enactment refuses when the policy subject does not '
          'exist yet', not missing['ok']
          and missing['suggestion']['knob'] == 'ScoreSubject')
    m.objectTables['ScoreSubject']['policy-transit-fund'] = (
        ScoreSubject(name='policy-transit-fund', kind='policy',
                     manager=None))
    enacted = pd.enact_draft(m, 'transit-fund-draft',
                             'policy-transit-fund', by='clerk')
    draft = _row(m, 'PolicyDraft', 'transit-fund-draft')
    check('passed -> enacted + policy link recorded',
          enacted['ok'] and draft.status == 'enacted'
          and draft.enacted_policy_subject_name
          == 'policy-transit-fund')
    carry = pd.draft_score_carryover(m, 'transit-fund-draft')
    check('carryover: draft-era assertions queryable FOR the '
          'enacted policy with provenance intact',
          carry['ok']
          and carry['enactedPolicySubject'] == 'policy-transit-fund'
          and len(carry['assertions']) == 1
          and carry['assertions'][0]['name'] == 'a1')
    check('enacted is terminal',
          not pd.transition_draft(m, 'transit-fund-draft',
                                  'introduced')['ok'])
    check('unknown draft carryover honest',
          not pd.draft_score_carryover(m, 'nope')['ok'])


def main():
    _lifecycle()
    _scoring_binds()
    _enactment()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
