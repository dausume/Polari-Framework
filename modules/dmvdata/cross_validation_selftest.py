"""
Selftest — cross-validation + provider reliability.

Run from polari-framework/:
    python3 -m dmvdata.cross_validation_selftest

Two groups pull the same official data on their own instances and
compare: identical duplicates CONFIRM (and each additional distinct
confirmer RAISES the credibility reading), planted mismatches yield
partial/contradicted verdicts naming the exact key+field,
self-confirmation is refused, credibility is always a READING (never
a truth declaration), and provider groups aggregate into reliability
readings + engine-scoreable ContextualizedValues.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from dmvdata import cross_validation_basis as cv
from dmvdata.gov_sources_basis import SEED_GOV_SOURCES, record_retrieval

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


ROWS = [{'geo': 'dc', 'rent': 2150}, {'geo': 'md-montgomery',
                                      'rent': 2050},
        {'geo': 'va-fairfax', 'rent': 2200},
        {'geo': 'va-arlington', 'rent': 2450}]


def _mgr():
    mgr = SimpleNamespace(idList=[], objectTables={
        'GovSource': {}, 'SourceRetrieval': {},
        'RetrievalConfirmation': {}, 'ContextualizedValue': {},
        'ScoreTerm': {}, 'ScoreConcept': {}, 'ScoreSubject': {},
        'ScoreContext': {}, 'ScoreGroup': {}, 'Contributor': {}},
        db=None)
    acs = next(s for s in SEED_GOV_SOURCES
               if s['name'] == 'census-acs')
    mgr.objectTables['GovSource']['census-acs'] = (
        SimpleNamespace(**acs))
    for group in ('group-alpha', 'group-beta', 'group-gamma'):
        mgr.objectTables['ScoreGroup'][group] = SimpleNamespace(
            name=group, display_name=group)
    return mgr


def _retrieve(mgr, by, group, stamp, what='B25064-2023'):
    result = record_retrieval(
        mgr, 'census-acs', endpoint_name='census-acs5-b25064',
        what=what, retrieved_by=by, retrieved_by_group=group,
        row_count=len(ROWS), retrieved_at=stamp)
    assert result['ok'], result
    return result['retrieval']['name']


def _confirmations():
    print('confirmation verdicts (per-key comparison)')
    m = _mgr()
    subject = _retrieve(m, 'alice', 'group-alpha',
                        '2026-07-16T10:00:00+00:00')
    confirming = _retrieve(m, 'bob', 'group-beta',
                           '2026-07-16T11:00:00+00:00')
    result = cv.confirm_retrieval(
        m, subject, confirming, ROWS, [dict(r) for r in ROWS],
        'geo', 'bob', 'group-beta',
        compared_at='2026-07-16T11:05:00+00:00')
    check('identical duplicate rows -> confirmed',
          result['ok']
          and result['comparison']['verdict'] == 'confirmed'
          and result['comparison']['mismatches'] == 0)

    cred1 = cv.sourcing_credibility(m, subject)
    third = _retrieve(m, 'carol', 'group-gamma',
                      '2026-07-16T12:00:00+00:00')
    cv.confirm_retrieval(
        m, subject, third, ROWS, [dict(r) for r in ROWS], 'geo',
        'carol', 'group-gamma',
        compared_at='2026-07-16T12:05:00+00:00')
    cred2 = cv.sourcing_credibility(m, subject)
    check('a SECOND distinct-group confirmation strictly raises '
          'credibility', cred2['score'] > cred1['score'],
          f"{cred1['score']} -> {cred2['score']}")
    check('distinct groups counted', cred2['distinctGroups'] == 2)

    planted = [dict(r) for r in ROWS]
    planted[1]['rent'] = 9999
    m2 = _mgr()
    s2 = _retrieve(m2, 'alice', 'group-alpha',
                   '2026-07-16T10:00:00+00:00')
    c2 = _retrieve(m2, 'bob', 'group-beta',
                   '2026-07-16T11:00:00+00:00')
    result = cv.confirm_retrieval(
        m2, s2, c2, ROWS, planted, 'geo', 'bob', 'group-beta',
        compared_at='2026-07-16T11:05:00+00:00')
    detail = result['comparison']['mismatchDetail']
    check('a planted mismatch yields contradicted/partial per the '
          'share knob (1/4 rows > 0.2 -> contradicted)',
          result['comparison']['verdict'] == 'contradicted',
          result['comparison']['verdict'])
    check('mismatch detail names the exact key and field',
          detail and detail[0]['id'] == 'md-montgomery'
          and detail[0]['field'] == 'rent'
          and detail[0]['newValue'] == 9999)


def _refusals():
    print('honest refusals')
    m = _mgr()
    subject = _retrieve(m, 'alice', 'group-alpha',
                        '2026-07-16T10:00:00+00:00')
    own = _retrieve(m, 'alice', 'group-alpha',
                    '2026-07-16T10:30:00+00:00')
    result = cv.confirm_retrieval(
        m, subject, own, ROWS, ROWS, 'geo', 'alice', 'group-alpha')
    check('self-confirmation refused plainly',
          not result['ok']
          and 'self-confirmation' in result['error'])
    result = cv.confirm_retrieval(
        m, 'nope', own, ROWS, ROWS, 'geo', 'bob', 'group-beta')
    check('unknown subject retrieval lists known retrievals',
          not result['ok'] and subject
          in result['knownRetrievals'])
    result = cv.confirm_retrieval(
        m, subject, 'nope', ROWS, ROWS, 'geo', 'bob', 'group-beta')
    check("unknown confirming retrieval names record_retrieval as "
          'the missing act', not result['ok']
          and 'record_retrieval' in result['error'])


def _credibility_readings():
    print('credibility readings (never truth declarations)')
    m = _mgr()
    subject = _retrieve(m, 'alice', 'group-alpha',
                        '2026-07-16T10:00:00+00:00')
    zero = cv.sourcing_credibility(m, subject)
    check('zero confirmations -> score None + the confirm act '
          'suggested', zero['score'] is None
          and zero['suggestion']['knob'] == 'confirm_retrieval')

    confirming = _retrieve(m, 'bob', 'group-beta',
                           '2026-07-16T11:00:00+00:00')
    cv.confirm_retrieval(m, subject, confirming, ROWS,
                         [dict(r) for r in ROWS], 'geo', 'bob',
                         'group-beta',
                         compared_at='2026-07-16T11:05:00+00:00')
    confirmed_only = cv.sourcing_credibility(m, subject)
    check('small-sample flagged under 5 confirmations',
          confirmed_only['smallSample'] is True)

    planted = [dict(r) for r in ROWS]
    planted[0]['rent'] = 1
    third = _retrieve(m, 'carol', 'group-gamma',
                      '2026-07-16T12:00:00+00:00')
    cv.confirm_retrieval(m, subject, third, ROWS, planted, 'geo',
                         'carol', 'group-gamma',
                         compared_at='2026-07-16T12:05:00+00:00')
    with_contradiction = cv.sourcing_credibility(m, subject)
    check('a contradiction LOWERS the score',
          with_contradiction['score'] < confirmed_only['score'],
          f"{confirmed_only['score']} -> "
          f"{with_contradiction['score']}")
    reading_text = json.dumps(with_contradiction).lower()
    check("the reading never declares 'true'/'verified' as a status",
          '"reading": "a credibility reading' in reading_text
          and '"verified"' not in reading_text
          and '"true":' not in reading_text)
    by_source = cv.sourcing_credibility(m, 'census-acs',
                                        subject='source')
    check('source-level credibility aggregates its retrievals',
          by_source['ok']
          and by_source['confirmationCount'] == 2)


def _provider():
    print('provider reliability + engine-scoreable values')
    m = _mgr()
    stamps = ['2026-07-16T0{}:00:00+00:00'.format(i)
              for i in range(1, 4)]
    names = [_retrieve(m, 'alice', 'group-alpha', s,
                       what=f'B2506{i}-2023')
             for i, s in enumerate(stamps)]
    validators = [('bob', 'group-beta'), ('carol', 'group-gamma'),
                  ('dave', 'group-beta')]
    datasets = [[dict(r) for r in ROWS],
                [dict(r) for r in ROWS], None]
    bad = [dict(r) for r in ROWS]
    for row in bad:
        row['rent'] = row['rent'] + 1000
    datasets[2] = bad
    for name, (who, group), rows in zip(names, validators,
                                        datasets):
        cv.confirm_retrieval(m, name,
                             _retrieve(m, who, group,
                                       '2026-07-16T09:00:00+00:00',
                                       what=f'val-{name[-4:]}'),
                             ROWS, rows, 'geo', who, group,
                             compared_at='2026-07-16T13:00:00+00:00')
    reading = cv.provider_reliability(m, 'group-alpha')
    check('provider aggregation: 2 confirmed + 1 contradicted of 3',
          reading['ok'] and reading['volume'] == 3
          and reading['confirmedRetrievals'] == 2
          and reading['contradictedRetrievals'] == 1)
    check('rates + span + small-sample honest',
          abs(reading['confirmationRate'] - 2 / 3) < 1e-4
          and reading['smallSample'] is True
          and reading['span']['first'] < reading['span']['last'])
    check('unknown provider group refused',
          not cv.provider_reliability(m, 'group-nobody')['ok'])

    pushed = cv.push_provider_scores(m, 'group-alpha', 'year-2026')
    again = cv.push_provider_scores(m, 'group-alpha', 'year-2026')
    values = {getattr(v, 'name', ''):
              getattr(v, 'pre_normalized_value', None)
              for v in m.objectTables['ContextualizedValue'].values()}
    check('push writes idempotent engine-readable values',
          pushed['ok'] and again['written'] == pushed['written']
          and len(values) == 3
          and abs(values['data-confirmation-rate@group-alpha-'
                         'year-2026'] - 2 / 3) < 1e-4
          and values['data-retrieval-volume@group-alpha-year-2026']
          == 3.0)
    check('derivation provenance counts the confirmations',
          '3 confirmations over 3 retrievals'
          in pushed['provenance'])

    from scoring.scoring_basis import (ScoreContext, ScoreSubject,
                                       ScoreTerm)
    from scoring.score_concept_basis import ScoreConcept
    for seed in cv.SEED_PROVIDER_TERMS:
        m.objectTables['ScoreTerm'][seed['name']] = ScoreTerm(
            **seed, manager=None)
    for seed in cv.SEED_PROVIDER_CONCEPT:
        m.objectTables['ScoreConcept'][seed['name']] = ScoreConcept(
            **seed, manager=None)
    m.objectTables['ScoreSubject']['group-alpha'] = ScoreSubject(
        name='group-alpha', display_name='Group Alpha',
        kind='group', manager=None)
    m.objectTables['ScoreContext']['year-2026'] = ScoreContext(
        name='year-2026', display_name='2026',
        context_type='timeframe', manager=None)
    from scoring.custom.scoring_engine import score_concept
    scored = score_concept(m, 'data-provider-reliability')
    subject_scores = scored.get('subjects') or scored.get(
        'perSubject') or []
    check('the STANDARD engine scores the provider concept to a '
          'number', scored.get('ok') and bool(subject_scores),
          str(scored)[:120] if not scored.get('ok') else '')


def main():
    _confirmations()
    _refusals()
    _credibility_readings()
    _provider()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
