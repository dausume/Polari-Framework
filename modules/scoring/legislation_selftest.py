"""
Selftest — legislation tracking (Dustin 2026-07-16): who drafted
what, who voted yes/no, what lobbies/groups contributed which parts,
and the burial-pattern findings.

Run from polari-framework/:
    python3 -m scoring.legislation_selftest

Fixture: 'transportation-funding-act' (declared subject: highway
funding) with a germane maintenance provision, a BURIED firearm
provision contributed by a lobby, and a provision inserted 2 days
before the floor vote; a 5-legislator roster whose declared counts
are DELIBERATELY wrong (yes=4 vs roster 3) to pin the reconciliation
warning. Detection must find EXACTLY the two planted patterns, the
germane provision must produce NO finding, and no narrative may use
accusatory vocabulary — findings are evidence, votes adjudicate.
"""

import json
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import legislation_basis as lg

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


LEGISLATORS = ['pol-ana-reyes', 'pol-bo-chen', 'pol-cy-drum',
               'pol-di-eze', 'pol-ed-fay']


def _mgr():
    m = SimpleNamespace(idList=[], db=None, objectTables={
        'LegislationRecord': {}, 'LegislationProvision': {},
        'LegislativeVoteEvent': {}, 'ScoreAssertion': {},
        'ScoreSubject': {
            name: SimpleNamespace(name=name, kind='politician')
            for name in LEGISLATORS},
    })
    return m


def _seed_bill(m):
    entered = lg.enter_legislation(m, {
        'name': 'transportation-funding-act',
        'bill_id': 'HB-2100', 'title': 'Transportation Funding Act',
        'legislature': 'va-general-assembly',
        'declared_subject': 'highway funding',
        'drafted_by': [
            {'kind': 'legislator', 'name': 'pol-ana-reyes',
             'evidence_url': 'https://lis.virginia.gov/example'},
            {'kind': 'staff', 'name': 'committee-staff-two',
             'evidence_url': ''}],
    })
    assert entered['ok'], entered
    for payload in (
        {'name': 'tfa-sec-101', 'section_ref': '§101',
         'legislation_name': 'transportation-funding-act',
         'issue_name': 'highway maintenance funding',
         'summary': 'allocates maintenance funds',
         'contributed_by': [{'kind': 'group',
                             'name': 'road-builders-association',
                             'evidence_url': 'https://example.gov'}],
         'added_at': '2026-01-05'},
        {'name': 'tfa-sec-402b', 'section_ref': '§402(b)',
         'legislation_name': 'transportation-funding-act',
         'issue_name': 'firearm carry rules',
         'summary': 'concealed carry in rest areas',
         'contributed_by': [{'kind': 'lobby',
                             'name': 'example-firearm-lobby',
                             'evidence_url':
                                 'https://example.gov/evidence'}],
         'added_at': '2026-01-05'},
        {'name': 'tfa-sec-500', 'section_ref': '§500',
         'legislation_name': 'transportation-funding-act',
         'issue_name': 'toll road funding formula',
         'summary': 'revises toll formulas',
         'contributed_by': [],
         'added_at': '2026-02-12'},
    ):
        assert lg.enter_provision(m, payload)['ok']
    vote = lg.enter_vote_event(m, {
        'name': 'tfa-house-vote-1',
        'legislation_name': 'transportation-funding-act',
        'chamber': 'house', 'occurred_at': '2026-02-14',
        'result': 'passed',
        'counts': {'yes': 4, 'no': 2},  # DELIBERATE mismatch
        'votes': {LEGISLATORS[0]: 'yes', LEGISLATORS[1]: 'yes',
                  LEGISLATORS[2]: 'yes', LEGISLATORS[3]: 'no',
                  LEGISLATORS[4]: 'no'},
    })
    assert vote['ok'], vote
    return m


def _entry_validation():
    print('manual entry: validation + honest refusals')
    m = _mgr()
    bad = lg.enter_provision(m, {'name': 'p', 'legislation_name':
                                 'nope'})
    check('provision on unknown legislation lists known bills',
          not bad['ok'] and bad['knownLegislation'] == [])
    _seed_bill(m)
    bad = lg.enter_legislation(m, {
        'name': 'x-act', 'drafted_by': [{'kind': 'wizard',
                                         'name': 'someone'}]})
    check('malformed contributor kind names the documented kinds',
          not bad['ok'] and 'lobby' in bad['error'])
    dup = lg.enter_legislation(m, {
        'name': 'transportation-funding-act'})
    check('duplicate legislation refused', not dup['ok'])
    ghost = lg.enter_vote_event(m, {
        'name': 'tfa-vote-2',
        'legislation_name': 'transportation-funding-act',
        'occurred_at': '2026-02-20', 'result': 'failed',
        'votes': {'pol-ghost': 'yes'}})
    check('unknown legislator is a SUGGESTION (recorded, knob '
          'named), not silent acceptance',
          ghost['ok']
          and ghost['suggestion']['knob'] == 'ScoreSubject'
          and 'pol-ghost' in ghost['suggestion']['action'])
    bad = lg.enter_vote_event(m, {
        'name': 'v', 'legislation_name':
        'transportation-funding-act',
        'votes': {LEGISLATORS[0]: 'maybe'}})
    check('unknown vote choice refused naming the choices',
          not bad['ok'] and 'abstain' in bad['error'])
    row = next(r for r in
               m.objectTables['LegislationRecord'].values()
               if r.name == 'transportation-funding-act')
    check("manual paths stamp entry_mode 'manual'",
          row.entry_mode == 'manual')


def _queries():
    print('who drafted / who voted / contributions / records')
    m = _seed_bill(_mgr())
    drafted = lg.who_drafted(m, 'transportation-funding-act')
    check('who_drafted returns the multi-author list',
          drafted['ok'] and len(drafted['draftedBy']) == 2
          and drafted['draftedBy'][0]['name'] == 'pol-ana-reyes')
    voted = lg.who_voted(m, 'transportation-funding-act')
    event = voted['voteEvents'][0]
    check('who_voted returns the full roster',
          voted['ok'] and len(event['roster']) == 5
          and event['roster'][LEGISLATORS[3]] == 'no')
    check('declared-counts vs roster mismatch is WARNED '
          '(yes declared 4, roster 3)',
          'warning' in event
          and 'declared 4 vs roster 3' in event['warning'])
    check('roster tallies computed correctly',
          event['rosterTallies']['yes'] == 3
          and event['rosterTallies']['no'] == 2)
    contrib = lg.contributions_for(m, 'transportation-funding-act')
    lobby = next(p for p in contrib['provisions']
                 if p['provision'] == 'tfa-sec-402b')
    check('per-provision contributor breakdown names the lobby',
          contrib['ok']
          and lobby['contributedBy'][0]['kind'] == 'lobby'
          and lobby['contributedBy'][0]['name']
          == 'example-firearm-lobby')
    record = lg.legislator_voting_record(m, LEGISLATORS[4])
    check('legislator voting record reads back',
          record['ok'] and record['tallies']['no'] == 1)
    missing = lg.legislator_voting_record(m, 'pol-nobody')
    check('no-votes legislator gets the roster-key suggestion',
          not missing['ok']
          and 'ScoreSubject' in missing['suggestion']['action'])


def _detection():
    print('burial-pattern findings (evidence, never verdicts)')
    m = _seed_bill(_mgr())
    result = lg.detect_burial_patterns(
        m, 'transportation-funding-act')
    findings = result['findings']
    patterns = sorted(f['pattern'] for f in findings)
    check('EXACTLY the two planted findings, no more',
          result['ok']
          and patterns == ['last-minute-insertion',
                           'non-germane-provision'],
          f'{patterns}')
    buried = next(f for f in findings
                  if f['pattern'] == 'non-germane-provision')
    check('non-germane finding quotes BOTH topics',
          'firearm carry rules' in buried['narrative']
          and 'highway funding' in buried['narrative']
          and buried['provision'] == 'tfa-sec-402b')
    late = next(f for f in findings
                if f['pattern'] == 'last-minute-insertion')
    check('last-minute finding names the day gap',
          late['provision'] == 'tfa-sec-500'
          and late['evidence']['gapDays'] == 2
          and '2 day(s)' in late['narrative'])
    check('the germane provision produces NO finding (the '
          'legitimate case must not false-positive)',
          not any(f['provision'] == 'tfa-sec-101'
                  for f in findings))
    all_text = json.dumps(findings).lower()
    check('no accusatory vocabulary in any narrative',
          not re.search(r'devious|corrupt|sneaky|illegal|crime',
                        all_text))
    check('implicated = contributors + drafters, roles labeled',
          any(e['role'] == 'contributor'
              and e['name'] == 'example-firearm-lobby'
              for e in buried['implicated'])
          and any(e['role'] == 'drafter'
                  and e['name'] == 'pol-ana-reyes'
                  for e in buried['implicated']))
    filed = lg.file_burial_assertion(m, buried, 'citizen-watch-1')
    row = next(r for r in
               m.objectTables['ScoreAssertion'].values()
               if r.name == filed['assertion'])
    check("finding files as a REAL assertion, status 'asserted' "
          '(votes adjudicate)',
          filed['ok'] and row.status == 'asserted'
          and row.subject_name == 'pol-ana-reyes'
          and row.asserted_by == 'citizen-watch-1')
    check('re-filing the same finding refused',
          not lg.file_burial_assertion(m, buried, 'x')['ok'])
    empty = lg.detect_burial_patterns(_mgr(), 'nope')
    check('unknown legislation refused listing known',
          not empty['ok'])


def _sources():
    print('legislative API registrations (dmvdata/legis_sources)')
    from polariApiProfiler.apiDomain import APIDomain
    from polariApiProfiler.apiEndpoint import APIEndpoint
    from dmvdata.gov_sources_basis import GovSource
    from dmvdata.legis_sources_seed import (SEED_LEGIS_DOMAINS,
                                       SEED_LEGIS_ENDPOINTS,
                                       SEED_LEGIS_GOV_SOURCES)
    for seed in SEED_LEGIS_DOMAINS:
        APIDomain(**seed, manager=None)
    for seed in SEED_LEGIS_ENDPOINTS:
        APIEndpoint(**seed, manager=None)
    for seed in SEED_LEGIS_GOV_SOURCES:
        GovSource(**seed, manager=None)
    check('all legis seed rows construct against the real classes',
          True)
    domain_names = {d['name'] for d in SEED_LEGIS_DOMAINS}
    check('every endpoint references a seeded domain',
          all(e['domainName'] in domain_names
              for e in SEED_LEGIS_ENDPOINTS))
    keyed = [e for e in SEED_LEGIS_ENDPOINTS
             if e.get('authType') in ('apikey', 'bearer')]
    check('keyed endpoints name env knobs, never literals',
          keyed and all(e['authConfig'].startswith('env:POLARI_')
                        for e in keyed))
    blob = json.dumps(SEED_LEGIS_DOMAINS + SEED_LEGIS_ENDPOINTS
                      + SEED_LEGIS_GOV_SOURCES)
    check('no literal-key-looking string anywhere in the seeds',
          re.search(r'[a-fA-F0-9]{32,}', blob) is None)
    md = next(s for s in SEED_LEGIS_GOV_SOURCES
              if s['name'] == 'md-mga')
    check('MD honesty: no official API is SAID, not papered over',
          'NO official public API' in md['description']
          and md['requires_api_key'] is False)
    congress = next(s for s in SEED_LEGIS_GOV_SOURCES
                    if s['name'] == 'congress-gov')
    check('Congress.gov: key requirement + endpoints linked',
          congress['requires_api_key']
          and congress['api_key_env'] == 'POLARI_CONGRESS_API_KEY'
          and 'congress-house-votes'
          in congress['api_endpoint_names_json'])


def main():
    _entry_validation()
    _queries()
    _detection()
    _sources()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
