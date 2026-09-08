"""
Selftest — Term Competition (the PSC termcompetition draft, built).

Run from polari-framework/:
    python3 -m scoring.term_competition_selftest

Two groups propose competing composite terms for a DMV housing
Score; relations are asserted (including logically-exclusive-
competing), confirmed, and materialized into the long-dormant
ScoreTerm equivalence/competition fields; context fit ranks the
DMV-contextualized term over the Texas-contextualized rival;
scope votes gate which terms even enter consideration; group-scale
AND global-scale legitimacy elections run through the REAL
worldview-election tally; applying an election marks the winner
elected and only SUGGESTS the concept weight change.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import term_competition_basis as tc
from scoring.dmv_col_seed import (SEED_DMV_GEO_CONTEXTS,
                                  SEED_DMV_TERMS,
                                  SEED_DMV_TIMEFRAMES)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


_TERM_DEFAULTS = {'equivalent_terms_json': '[]',
                  'competitive_terms_json': '[]',
                  'abstract_tags_json': '[]'}

_CITED = [{'sourceTerm': 'median-gross-rent', 'operation': 'base',
           'source_name': 'census-acs',
           'citation_url': 'https://data.census.gov/table/'
                           'ACSDT5Y2023.B25064'}]


def _ctx(name, context_type='location', parent=''):
    return SimpleNamespace(name=name, display_name=name,
                           context_type=context_type,
                           value_json='{}', parent_name=parent,
                           notes='')


def _value(name, term, subject, contexts):
    return SimpleNamespace(
        name=name, term_name=term, subject_name=subject,
        context_names_json=json.dumps(contexts),
        pre_normalized_value=1.0, data_ref_json='',
        normalization_json='', source='', provenance_id='',
        contributed_by='', notes='')


def _mgr():
    m = SimpleNamespace(objectTables={}, idList=[], db=None)
    m.objectTables['ScoreTerm'] = {
        seed['name']: SimpleNamespace(**{**_TERM_DEFAULTS, **seed})
        for seed in SEED_DMV_TERMS}
    m.objectTables['ScoreTerm']['texas-rent-index'] = (
        SimpleNamespace(**{**_TERM_DEFAULTS,
                           'name': 'texas-rent-index',
                           'display_name': 'Texas Rent Index'}))
    m.objectTables['ScoreTerm']['ghost-term'] = SimpleNamespace(
        **{**_TERM_DEFAULTS, 'name': 'ghost-term',
           'display_name': 'Ghost'})
    m.objectTables['ScoreContext'] = {
        seed['name']: SimpleNamespace(**seed)
        for seed in SEED_DMV_GEO_CONTEXTS + SEED_DMV_TIMEFRAMES}
    for extra in (_ctx('country-usa'),
                  _ctx('state-texas', parent='country-usa'),
                  _ctx('year-2022', context_type='timeframe')):
        m.objectTables['ScoreContext'][extra.name] = extra
    m.objectTables['ScoreConcept'] = {
        'dmv-housing-price': SimpleNamespace(
            name='dmv-housing-price',
            display_name='DMV Housing Price',
            required_context_names_json=json.dumps(
                ['dmv-region', 'year-2026']),
            term_weights_json='[]', subject_kind='jurisdiction'),
        'empty-concept': SimpleNamespace(
            name='empty-concept', display_name='Empty',
            required_context_names_json='[]',
            term_weights_json='[]', subject_kind='')}
    m.objectTables['ScoreGroup'] = {
        'group-tenants': SimpleNamespace(
            name='group-tenants', member_concept_names_json='[]'),
        'group-builders': SimpleNamespace(
            name='group-builders', member_concept_names_json='[]')}
    m.objectTables['ContextualizedValue'] = {
        v.name: v for v in (
            _value('mgr-dc', 'median-gross-rent', 'dc',
                   ['dc', 'year-2026']),
            _value('mgr-ffx', 'median-gross-rent', 'va-fairfax',
                   ['va-fairfax', 'year-2026']),
            _value('tri-tx', 'texas-rent-index', 'dc',
                   ['state-texas', 'year-2022']))}
    for table in ('TermProposal', 'TermRelationAssertion',
                  'TermScopeVote', 'WorldviewElection',
                  'WorldviewBallot'):
        m.objectTables[table] = {}
    return m


def _ballot(name, election, voter, choice):
    return SimpleNamespace(
        name=name, election_name=election, voter=voter,
        approvals_json='[]', sole_choice=choice, ranking_json='[]',
        cast_date='2026-07-16', notes='')


def _proposal(m, name):
    return next(r for r in m.objectTables['TermProposal'].values()
                if getattr(r, 'name', '') == name)


def _election(m, name):
    return next(r for r in
                m.objectTables['WorldviewElection'].values()
                if getattr(r, 'name', '') == name)


def _proposals(m):
    print('proposals (composite terms from CITED sources)')
    ok = tc.propose_term(
        m, 'prop-tenants-rent', 'median-gross-rent',
        'dmv-housing-price', 'group-tenants', 'alice', _CITED,
        rationale='official ACS rent, DMV-contextualized')
    check('a cited composite proposal lands', ok['ok']
          and ok['status'] == 'proposed')
    ok = tc.propose_term(
        m, 'prop-builders-tri', 'texas-rent-index',
        'dmv-housing-price', 'group-builders', 'bob',
        [{'sourceTerm': 'x', 'operation': 'index',
          'source_name': 'harvard-jchs',
          'citation_url': 'https://www.jchs.harvard.edu/'}],
        rationale='index approach')
    check('the rival group proposal lands', ok['ok'])
    bad = tc.propose_term(
        m, 'prop-uncited', 'ghost-term', 'dmv-housing-price',
        'group-tenants', 'alice',
        [{'sourceTerm': 'x', 'operation': 'sum'}])
    check('an UNCITED composition is refused naming the fields',
          not bad['ok'] and 'citation_url' in bad['error'])
    check('unknown concept refused listing known ones',
          not tc.propose_term(m, 'p2', 't', 'nope', 'g', 'a',
                              _CITED)['ok'])
    check('duplicate proposal name refused',
          not tc.propose_term(m, 'prop-tenants-rent', 't',
                              'dmv-housing-price', 'g', 'a',
                              _CITED)['ok'])


def _relations(m):
    print('relation assertions + materialization')
    ok = tc.assert_term_relation(
        m, 'rel-compete', 'median-gross-rent', 'texas-rent-index',
        'logically-exclusive-competing', 'alice',
        on_behalf_of_group='group-tenants',
        rationale='identical purpose — must compete for legitimacy')
    check("'logically-exclusive-competing' asserts", ok['ok'])
    ok = tc.assert_term_relation(
        m, 'rel-purpose', 'median-gross-rent', 'fair-market-rent-2br',
        'purpose-equivalent', 'bob',
        rationale='both measure modest rent levels')
    check('purpose-equivalent asserts', ok['ok'])
    check('self-relation refused',
          not tc.assert_term_relation(
              m, 'r-self', 'ghost-term', 'ghost-term',
              'logical-equivalent', 'a', rationale='x')['ok'])
    check('empty rationale refused',
          not tc.assert_term_relation(
              m, 'r-empty', 'a-term', 'b-term',
              'logical-subset', 'a', rationale='  ')['ok'])
    check("'other' without notes refused",
          not tc.assert_term_relation(
              m, 'r-other', 'a-term', 'b-term', 'other', 'a',
              rationale='something else')['ok'])
    check('unknown relation kind lists the vocabulary',
          'logical-subset' in str(tc.assert_term_relation(
              m, 'r-unknown', 'a', 'b', 'superset', 'a',
              rationale='x').get('relations')))

    flip = tc.transition_term_relation(m, 'rel-compete', 'confirmed',
                                       by='panel')
    check('relation confirms through the lifecycle', flip['ok'])
    suggestion = tc.materialize_confirmed_relations(
        m, 'median-gross-rent', apply=False)
    term = m.objectTables['ScoreTerm']['median-gross-rent']
    check('materialize suggests WITHOUT touching the term row',
          suggestion['proposed'].get('competitive_terms_json',
                                     {}).get('add')
          == ['texas-rent-index']
          and term.competitive_terms_json == '[]')
    applied = tc.materialize_confirmed_relations(
        m, 'median-gross-rent', apply=True)
    check('apply=True folds the CONFIRMED relation into '
          'competitive_terms_json (the dormant field, consumed)',
          applied['applied']
          and json.loads(term.competitive_terms_json)
          == ['texas-rent-index'])
    check('unconfirmed purpose-equivalent is NOT materialized',
          json.loads(term.equivalent_terms_json) == [])


def _context_fit(m):
    print('context fit (topic/time/location closest-match)')
    fit = tc.context_fit(m, 'median-gross-rent', 'dmv-housing-price')
    check('DMV-contextualized term fits (descendant geo + exact '
          'year)', fit['ok'] and fit['fit'] >= 0.85,
          f"fit={fit.get('fit')}")
    check('…and is the CLOSEST MATCH among rivals',
          fit['closestMatch'] is True,
          f"rivals={fit.get('rivalFits')}")
    rival = tc.context_fit(m, 'texas-rent-index',
                           'dmv-housing-price')
    check('the Texas-contextualized rival fits poorly and is not '
          'closest', rival['ok'] and rival['fit'] < 0.3
          and rival['closestMatch'] is False,
          f"fit={rival.get('fit')}")
    ghost = tc.context_fit(m, 'ghost-term', 'dmv-housing-price')
    check('a term with NO values reads honest-unfit + suggestion',
          not ghost['ok'] and ghost['fit'] is None
          and ghost['suggestion']['knob'] == 'ContextualizedValue')


def _scope_votes(m):
    print('scope eligibility (which terms even enter consideration)')
    for i, (voter, group, eligible) in enumerate([
            ('alice', 'group-tenants', True),
            ('bob', 'group-builders', True),
            ('carol', '', True)]):
        tc.cast_scope_vote(m, f'sv-mgr-{i}', 'dmv-housing-price',
                           'median-gross-rent', voter, eligible,
                           on_behalf_of_group=group,
                           cast_at=f'2026-07-16T0{i}:00:00')
    tally = tc.scope_tally(m, 'dmv-housing-price',
                           'median-gross-rent')
    check('groups + an individual tally as 3 DISTINCT units, '
          'small-sample flagged',
          tally['units'] == 3 and tally['verdict'] == 'eligible'
          and tally['smallSample'])
    verdict = tc.apply_scope_verdict(m, 'dmv-housing-price',
                                     'median-gross-rent')
    check('the explicit act flips the proposal in-scope',
          verdict['ok'] and verdict['status'] == 'in-scope'
          and _proposal(m, 'prop-tenants-rent').status == 'in-scope')

    for i, (voter, group, eligible) in enumerate([
            ('alice', 'group-tenants', False),
            ('carol', '', False),
            ('bob', 'group-builders', True)]):
        tc.cast_scope_vote(m, f'sv-tri-{i}', 'dmv-housing-price',
                           'texas-rent-index', voter, eligible,
                           on_behalf_of_group=group,
                           cast_at=f'2026-07-16T0{i}:00:00')
    verdict = tc.apply_scope_verdict(m, 'dmv-housing-price',
                                     'texas-rent-index')
    check('majority-ineligible excludes the rival',
          verdict['ok'] and verdict['status'] == 'excluded')

    tc.cast_scope_vote(m, 'sv-tri-flip', 'dmv-housing-price',
                       'texas-rent-index', 'bob', False,
                       on_behalf_of_group='group-builders',
                       cast_at='2026-07-16T09:00:00')
    tally = tc.scope_tally(m, 'dmv-housing-price',
                           'texas-rent-index')
    check("a unit's LATEST vote supersedes its earlier one",
          tally['ineligibleUnits'] == sorted(
              ['group-tenants', 'individual:carol',
               'group-builders']))
    check('no-votes verdict refuses to apply with the vote act '
          'suggested',
          not tc.apply_scope_verdict(
              m, 'empty-concept', 'ghost-term')['ok'])


def _elections(m):
    print('legitimacy elections (group scale + global scale, real '
          'tally)')
    no_scope = tc.open_term_election(m, 'empty-concept', 'global')
    check('no in-scope proposals refuses with the scope-gate '
          'suggestion', not no_scope['ok']
          and 'scope' in no_scope['suggestion']['action'])
    check('unknown scale / groupless group-scale / grouped global '
          'all refused',
          not tc.open_term_election(m, 'dmv-housing-price',
                                    'county')['ok']
          and not tc.open_term_election(m, 'dmv-housing-price',
                                        'group')['ok']
          and not tc.open_term_election(
              m, 'dmv-housing-price', 'global',
              group_name='group-tenants')['ok'])

    grp = tc.open_term_election(m, 'dmv-housing-price', 'group',
                                group_name='group-tenants',
                                mode='sole')
    glob = tc.open_term_election(m, 'dmv-housing-price', 'global',
                                 mode='sole')
    check('group + global elections open over ONLY the in-scope '
          'proposal (excluded rival absent)',
          grp['ok'] and glob['ok']
          and grp['candidates'] == ['prop-tenants-rent']
          and glob['candidates'] == ['prop-tenants-rent'])

    for i, voter in enumerate(['alice', 'dave']):
        m.objectTables['WorldviewBallot'][f'b-grp-{i}'] = _ballot(
            f'b-grp-{i}', grp['election'], voter,
            'prop-tenants-rent')
    for i, voter in enumerate(['erin', 'frank', 'grace']):
        m.objectTables['WorldviewBallot'][f'b-glob-{i}'] = _ballot(
            f'b-glob-{i}', glob['election'], voter,
            'prop-tenants-rent')

    premature = tc.apply_term_election(m, grp['election'])
    check('applying an OPEN election refuses (results can still '
          'change)', not premature['ok']
          and 'closed' in premature['error'])

    concept = m.objectTables['ScoreConcept']['dmv-housing-price']
    for election_name in (grp['election'], glob['election']):
        _election(m, election_name).status = 'closed'
        applied = tc.apply_term_election(m, election_name)
        check(f'{election_name.split("--")[-1]}-scale election '
              'applies through the REAL tally',
              applied['ok'] and applied['elected']
              == 'prop-tenants-rent'
              and applied['suggestion']['proposedWeights']
              == {'median-gross-rent': 1.0})
    check("the winning proposal is 'elected'; the concept row is "
          'UNTOUCHED (weights only SUGGESTED)',
          _proposal(m, 'prop-tenants-rent').status == 'elected'
          and concept.term_weights_json == '[]')
    check('a non-term election name refuses with the known list',
          not tc.apply_term_election(m, 'some-other-election')['ok'])


def _report(m):
    print('the full-flow report')
    report = tc.term_competition_report(m, 'dmv-housing-price')
    mine = next(p for p in report['proposals']
                if p['proposal'] == 'prop-tenants-rent')
    rival = next(p for p in report['proposals']
                 if p['proposal'] == 'prop-builders-tri')
    check('report composes proposals with status/citations/fit/'
          'relations/scope',
          report['ok'] and mine['status'] == 'elected'
          and mine['composition'][0]['source_name'] == 'census-acs'
          and mine['closestMatch'] is True
          and any(r['relation'] == 'logically-exclusive-competing'
                  for r in mine['relations'])
          and rival['status'] == 'excluded')
    check('report carries both elections with real tallies',
          len(report['elections']) == 2
          and all(e['tally']['ok'] for e in report['elections']))


def main():
    m = _mgr()
    _proposals(m)
    _relations(m)
    _context_fit(m)
    _scope_votes(m)
    _elections(m)
    _report(m)
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
