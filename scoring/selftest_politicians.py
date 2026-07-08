"""
Selftest — scr-6: politician voting records → vote-weighted scores.

Run from polari-framework/:
    python3 -m scoring.selftest_politicians

Covers: vote-weighted politician scores (yea carries the policy's
stance, nay inverts, abstention = participation gap outside the
math); hand-computed parity through the full chain (assertions →
policy stance → vote → politician score); time-scoped scoring off
vote dates (scr-4 contexts); cohort reads (per-member scores +
per-policy vote cohesion banded through the editable
AgreementPolicy); vote ingestion from ANY class (the api-profiler
seam) with refusal knobs and idempotency.
"""

import json
from types import SimpleNamespace

from scoring.agreement_policy import SEED_AGREEMENT_POLICIES
from scoring.assertion_seed import (
    SEED_MEDIA_EVIDENCE, SEED_POLICY_SUBJECTS, SEED_SCORE_ASSERTIONS,
    SEED_VALIDITY_VOTES,
)
from scoring.contributors import SEED_CONTRIBUTORS
from scoring.evidence import SEED_EVIDENCE_POLICIES
from scoring.policy_votes import (
    SEED_COHORT_GROUPS, SEED_POLICY_VOTES, SEED_POLITICIAN_SUBJECTS,
    ingest_votes_from_class,
)
from scoring.politician_scoring import cohort_report, politician_score
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
    SEED_SCORE_CONTEXTS, SEED_SCORE_GROUPS, SEED_SCORE_SUBJECTS,
    SEED_SCORE_TERMS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**{'pre_normalized_value': None, **r})
            for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'ScoreTerm': _rows(SEED_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS
                              + SEED_POLICY_SUBJECTS
                              + SEED_POLITICIAN_SUBJECTS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_SCORE_GROUPS + SEED_COHORT_GROUPS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'Contributor': _rows(SEED_CONTRIBUTORS),
        'EvidencePolicy': _rows(SEED_EVIDENCE_POLICIES),
        'MediaEvidence': _rows(SEED_MEDIA_EVIDENCE),
        'ScoreAssertion': _rows(SEED_SCORE_ASSERTIONS),
        'AssertionValidityVote': _rows(SEED_VALIDITY_VOTES),
        'PolicyVote': _rows(SEED_POLICY_VOTES),
        'FEMModelDefinition': {},
    })


#: Chain parity, hand-computed: fair-wage stance = 491/571 (scr-5
#: selftest), labor-standards stance = +1.
FAIR_WAGE_STANCE = 491 / 571
RIVERA_SCORE = ((FAIR_WAGE_STANCE + 1.0) / 2 + 1.0) / 2  # mean, then map
STONE_SCORE = (-FAIR_WAGE_STANCE + 1.0) / 2


if __name__ == '__main__':
    print('\nscr-6: politicians, votes, cohorts\n')

    print('vote-weighted politician scores')
    m = _mgr()
    report = politician_score(m, 'pol-rivera', 'labor-quality')
    check('rivera (yea + yea): mean of both policy stances',
          report['ok'] and abs(report['score'] - RIVERA_SCORE) < 1e-4,
          f"got {report.get('score')}")
    check('rivera: 2 decisive votes, participation 1.0',
          report['decisiveVotes'] == 2
          and report['participation'] == 1.0)
    check('every contribution itemized with the policy stance',
          all('policyStance' in c and 'contribution' in c
              for c in report['voteBreakdown']))
    report = politician_score(m, 'pol-stone', 'labor-quality')
    check('stone (nay): the policy stance INVERTS',
          report['ok'] and abs(report['score'] - STONE_SCORE) < 1e-4,
          f"got {report.get('score')}")
    check('stone: abstention = participation gap, not a stance',
          len(report['abstains']) == 1
          and report['participation'] == 0.5)
    report = politician_score(m, 'no-such', 'labor-quality')
    check('unknown politician honest 404', not report['ok'])
    # A politician whose only votes hit unscoreable policies.
    m.objectTables['PolicyVote'][90] = SimpleNamespace(
        name='vote-x', politician_name='pol-rivera',
        policy_name='alabama', vote='yea', vote_date='2024-01-01',
        pre_normalized_value=None)
    report = politician_score(m, 'pol-rivera', 'labor-quality')
    check('votes on unscoreable policies named, not silently dropped',
          report['ok']
          and report['unscoreablePolicies'][0]['policy'] == 'alabama')

    print('\ntime-scoped scoring (scr-4 contexts)')
    m = _mgr()
    m.objectTables['ScoreContext'][90] = SimpleNamespace(
        name='year-2024', display_name='2024',
        context_type='timeframe', parent_name='',
        value_json=json.dumps(
            {'start': '2024-01-01', 'end': '2024-12-31'}),
        pre_normalized_value=None)
    report = politician_score(m, 'pol-rivera', 'labor-quality',
                              timeframe_context='year-2024')
    check('2024 frame: only the 2024 vote counts, the 2020 one is '
          'out of scope',
          report['ok'] and report['decisiveVotes'] == 1
          and report['votesOutOfTimeframe'] == 1
          and abs(report['stance'] - FAIR_WAGE_STANCE) < 1e-4)
    report = politician_score(m, 'pol-rivera', 'labor-quality',
                              timeframe_context='year-2022')
    check('a frame with no decisive votes refuses honestly',
          not report['ok'] and 'no decisive vote' in report['error'])
    report = politician_score(m, 'pol-rivera', 'labor-quality',
                              timeframe_context='state-texas')
    check('non-timeframe context refused naming the knob',
          not report['ok']
          and 'timeframe' in report['suggestion']['knob'])

    print('\ncohort reads (party/committee accountability)')
    m = _mgr()
    report = cohort_report(m, 'demo-assembly-labor-committee',
                           'labor-quality')
    by_member = {mem['politician']: mem for mem in report['members']}
    check('per-member scores through the full chain',
          report['ok']
          and abs(by_member['pol-rivera']['score'] - RIVERA_SCORE)
          < 1e-4
          and abs(by_member['pol-stone']['score'] - STONE_SCORE)
          < 1e-4)
    expected_mean = (round(RIVERA_SCORE, 6) + round(STONE_SCORE, 6)) / 2
    check('cohort mean travels',
          abs(report['cohortMeanScore'] - expected_mean) < 1e-6)
    cohesion = {c['policy']: c for c in report['voteCohesion']}
    check('split vote on fair-wage = divisive (same bands as '
          'worldview agreement)',
          cohesion['policy-fair-wage-act']['band'] == 'divisive'
          and cohesion['policy-fair-wage-act']['dominantFraction']
          == 0.5)
    check('unanimous-among-decisive labor-standards = consensus, '
          'abstention visible',
          cohesion['policy-labor-standards-2020']['band']
          == 'consensus'
          and cohesion['policy-labor-standards-2020']['abstain'] == 1)
    report = cohort_report(m, 'demo-political-group', 'labor-quality')
    check('worldview-only group refuses the cohort read naming the '
          'members knob',
          not report['ok'] and 'member_subject_names_json'
          in report['suggestion']['knob'])
    report = cohort_report(m, 'no-such', 'labor-quality')
    check('unknown group honest 404 with known list',
          not report['ok'] and 'knownGroups' in report)

    print('\nvote ingestion (any class → PolicyVote rows)')
    m = _mgr()
    m.objectTables['RollCallRow'] = _rows([
        {'name': 'rc-1', 'legislator': 'Sen. Novak',
         'bill': 'policy-fair-wage-act', 'position': 'Yea',
         'when': '2024-04-15'},
        {'name': 'rc-2', 'legislator': 'Sen. Novak',
         'bill': 'policy-labor-standards-2020', 'position': 'Present',
         'when': '2020-06-15'},
    ])
    payload = {
        'source_class': 'RollCallRow',
        'mapping': {'politicianField': 'legislator',
                    'policyField': 'bill', 'voteField': 'position',
                    'dateField': 'when'},
        'vote_values': {'Yea': 'yea', 'Nay': 'nay'},
    }
    result = ingest_votes_from_class(m, payload)
    check('unknown politician refused naming the create knob',
          not result['ok']
          and result['suggestion']['knob']
          == 'create_missing_politicians')
    import scoring.policy_votes as votes_mod

    def _factory(class_name, mgr):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            table = mgr.objectTables.setdefault(class_name, {})
            table[f'ing-{len(table)}'] = row
            return row
        return make

    orig = (votes_mod.PolicyVote, votes_mod.ScoreSubject)
    votes_mod.PolicyVote = _factory('PolicyVote', m)
    votes_mod.ScoreSubject = _factory('ScoreSubject', m)
    try:
        result = ingest_votes_from_class(
            m, {**payload, 'create_missing_politicians': True})
        check('with the knob: politician created, yea ingested, '
              'unmapped position refused with the vote_values hint',
              result['ok']
              and result['createdPoliticians'] == ['sen.-novak']
              and len(result['created']) == 1
              and 'vote_values' in result['refused'][0]['error'])
        again = ingest_votes_from_class(
            m, {**payload, 'create_missing_politicians': True})
        check('re-ingest skips existing votes (idempotent, never '
              'clobbers)',
              again['ok'] and again['skipped'] == result['created'])
        forced = ingest_votes_from_class(
            m, {**payload, 'create_missing_politicians': True,
                'overwrite': True})
        check('overwrite knob updates explicitly',
              forced['ok'] and forced['updated'] == result['created'])
    finally:
        votes_mod.PolicyVote, votes_mod.ScoreSubject = orig
    result = ingest_votes_from_class(m, {'source_class': 'RollCallRow',
                                         'mapping': {}})
    check('incomplete mapping refused', not result['ok'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
