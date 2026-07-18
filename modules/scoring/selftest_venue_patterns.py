"""
Selftest — venue-mismatch pattern analysis.

Run from polari-framework/:
    python3 -m scoring.selftest_venue_patterns

Dustin's two scenarios, each with its LEGITIMATE counter-case pinned
(the honest sequence must never false-positive): a budget rider with
no prior statute matches policy-via-budget-rider, but a statute
enacted first clears it; a ballot initiative starved across budget
cycles matches suppression-by-defunding, but funding it next period
clears it. Findings are sequence matches with evidence — the pinned
vocabulary check proves no accusatory language — and filing lands a
REAL 'asserted' (never confirmed) ScoreAssertion for the scr-6
validity machinery to adjudicate.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import venue_patterns as vp

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
    m = SimpleNamespace(idList=[], db=None, objectTables={
        'VenueActionRecord': {}, 'VenueMismatchPattern': {},
        'ScoreAssertion': {}})
    for seed in vp.SEED_VENUE_PATTERNS:
        m.objectTables['VenueMismatchPattern'][seed['name']] = (
            SimpleNamespace(**seed))
    return m


def _rec(m, name, issue, venue, action, actor='', period='',
         at=''):
    m.objectTables['VenueActionRecord'][name] = SimpleNamespace(
        name=name, issue_name=issue, policy_ref='', venue=venue,
        action=action, actor_subject_name=actor,
        jurisdiction_subject_name='dc', fiscal_period=period,
        occurred_at=at, evidence_url='', provenance_id='', notes='')


def _rider_scenario():
    print('scenario 1: policy crammed into a budget')
    m = _mgr()
    _rec(m, 'r1', 'broadband-rules', 'budget-appropriation',
         'rider-attached', actor='rep-smith', period='fy2026',
         at='2026-03-01T00:00:00Z')
    result = vp.detect_patterns(m, 'broadband-rules')
    finding = next((f for f in result['findings']
                    if f['pattern'] == 'policy-via-budget-rider'),
                   None)
    check('budget rider with NO statute -> policy-via-budget-rider '
          'finding naming the actor',
          result['ok'] and finding is not None
          and finding['actors'] == ['rep-smith'])
    check('the narrative carries venue/period/date evidence',
          finding is not None and 'fy2026' in finding['narrative']
          and 'budget-appropriation' in finding['narrative'])

    legit = _mgr()
    _rec(legit, 's1', 'broadband-rules', 'statute', 'enacted',
         actor='legislature', at='2025-06-01T00:00:00Z')
    _rec(legit, 'r1', 'broadband-rules', 'budget-appropriation',
         'rider-attached', actor='rep-smith', period='fy2026',
         at='2026-03-01T00:00:00Z')
    result = vp.detect_patterns(legit, 'broadband-rules')
    check('COUNTER-CASE: statute enacted BEFORE the rider -> NO '
          'finding (the legitimate sequence never false-positives)',
          result['ok'] and not any(
              f['pattern'] == 'policy-via-budget-rider'
              for f in result['findings']))


def _defunding_scenario():
    print('scenario 2: passed initiative starved of funding')
    m = _mgr()
    _rec(m, 'i1', 'parks-initiative', 'ballot-initiative', 'enacted',
         actor='the-voters', at='2024-11-05T00:00:00Z')
    for i, period in enumerate(('fy2025', 'fy2026', 'fy2027')):
        _rec(m, f'b{i}', 'parks-initiative', 'budget-appropriation',
             'omitted-from-budget', actor='mayor-jones',
             period=period, at=f'202{5 + i}-06-01T00:00:00Z')
    result = vp.detect_patterns(m, 'parks-initiative')
    finding = next((f for f in result['findings']
                    if f['pattern'] == 'suppression-by-defunding'),
                   None)
    check('initiative enacted + 3 omitted budget cycles -> '
          'suppression-by-defunding finding',
          result['ok'] and finding is not None
          and 'mayor-jones' in finding['actors'])

    funded = _mgr()
    _rec(funded, 'i1', 'parks-initiative', 'ballot-initiative',
         'enacted', at='2024-11-05T00:00:00Z')
    _rec(funded, 'b1', 'parks-initiative', 'budget-appropriation',
         'funded', actor='mayor-jones', period='fy2025',
         at='2025-06-01T00:00:00Z')
    result = vp.detect_patterns(funded, 'parks-initiative')
    check('COUNTER-CASE: funded the next period -> NO finding',
          result['ok'] and not any(
              f['pattern'] == 'suppression-by-defunding'
              for f in result['findings']))


def _filing_and_framing():
    print('filing findings as REAL assertions (scr-6 adjudicates)')
    m = _mgr()
    _rec(m, 'r1', 'zoning-rules', 'budget-appropriation',
         'rider-attached', actor='rep-doe', period='fy2026',
         at='2026-02-01T00:00:00Z')
    finding = vp.detect_patterns(m, 'zoning-rules')['findings'][0]
    filed = vp.file_pattern_assertion(m, finding,
                                      asserted_by='analyst-1')
    row = _row(m, 'ScoreAssertion', filed['assertions'][0]['name'])
    check("the filed assertion is status 'asserted' — NEVER "
          'auto-confirmed',
          filed['ok'] and row.status == 'asserted'
          and row.subject_name == 'rep-doe')
    check('re-filing is idempotent',
          vp.file_pattern_assertion(
              m, finding,
              asserted_by='analyst-1')['assertions'][0]['created']
          is False)
    check('filing without asserted_by refused (accountability)',
          not vp.file_pattern_assertion(m, finding, '')['ok'])

    banned = ('devious', 'corrupt', 'illegal')
    text = json.dumps(finding) + row.intent + row.notes
    check('findings carry NO accusatory vocabulary '
          "(pinned: 'devious'/'corrupt'/'illegal' never appear)",
          not any(word in text.lower() for word in banned))


def _honesty():
    print('honest refusals')
    m = _mgr()
    _rec(m, 'r1', 'known-issue', 'statute', 'introduced',
         at='2026-01-01T00:00:00Z')
    result = vp.detect_patterns(m, 'unknown-issue')
    check('unknown issue lists the known issues',
          not result['ok'] and result['knownIssues']
          == ['known-issue'])
    empty = SimpleNamespace(idList=[], db=None, objectTables={
        'VenueActionRecord': {}, 'VenueMismatchPattern': {},
        'ScoreAssertion': {}})
    result = vp.detect_patterns(empty, 'anything')
    check('zero records suggests the VenueActionRecord knob',
          not result['ok']
          and result['suggestion']['knob'] == 'VenueActionRecord')

    bad = _mgr()
    bad.objectTables['VenueMismatchPattern']['broken'] = (
        SimpleNamespace(name='broken', display_name='Broken',
                        description='',
                        sequence_rule_json=json.dumps(
                            {'requires': [{'venue': 'lobby-dinner',
                                           'action': 'enacted'}]}),
                        severity_note='', proposed_by='', enabled=True,
                        notes=''))
    _rec(bad, 'r1', 'x', 'statute', 'introduced',
         at='2026-01-01T00:00:00Z')
    result = vp.detect_patterns(bad, 'x')
    check('a rule naming an unknown venue is a PER-PATTERN error '
          'naming the constants (other patterns still run)',
          result['ok'] and result.get('ruleErrors')
          and 'lobby-dinner' in result['ruleErrors'][0]['error']
          and 'statute' in result['ruleErrors'][0]['error'])


def main():
    _rider_scenario()
    _defunding_scenario()
    _filing_and_framing()
    _honesty()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
