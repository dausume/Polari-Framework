"""
Selftest — scr-8: worldview elections → vote-derived group weights.

Run from polari-framework/:
    python3 -m scoring.selftest_elections

Covers: ranked-condorcet tally (pairwise matrix, Condorcet winner,
Copeland-share weights, labeled fallback on cycles); approval + sole
modes; malformed ballots refused by name; apply gate (closed-only,
provenance-stamped) and the downstream effect — weighted group
aggregation flips a large-majority read to consensus when the
zero-weight dissenter loses his voice, while unweighted groups keep
exact scr-3 behavior.
"""

import json
from types import SimpleNamespace

from scoring.agreement_policy import SEED_AGREEMENT_POLICIES
from scoring.group_aggregation import aggregate_group
from scoring.scoring_seed import (
    SEED_SCORE_CONCEPTS, SEED_SCORE_GROUPS, SEED_SCORE_TERMS,
)
from scoring.worldview_elections import (
    SEED_ASSEMBLY_GROUPS, SEED_WORLDVIEW_BALLOTS,
    SEED_WORLDVIEW_ELECTIONS, apply_election, tally_election,
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
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_SCORE_GROUPS + SEED_ASSEMBLY_GROUPS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'WorldviewElection': _rows(SEED_WORLDVIEW_ELECTIONS),
        'WorldviewBallot': _rows(SEED_WORLDVIEW_BALLOTS),
    })


CAROL, ALICE, BOB, DAN = ('member-labor-carol', 'member-labor-alice',
                          'member-labor-bob', 'member-labor-dan')


if __name__ == '__main__':
    print('\nscr-8: worldview elections, vote-derived weights\n')

    print('ranked-condorcet (the seeded election)')
    m = _mgr()
    tally = tally_election(m, 'demo-labor-definition-election')
    check('carol is the Condorcet winner (beats all pairwise)',
          tally['ok'] and tally['winners'] == [CAROL]
          and 'condorcet' in tally['note'])
    check('Copeland-share weights: 3/6, 2/6, 1/6, 0',
          abs(tally['electedWeights'][CAROL] - 0.5) < 1e-6
          and abs(tally['electedWeights'][ALICE] - 1 / 3) < 1e-4
          and abs(tally['electedWeights'][BOB] - 1 / 6) < 1e-4
          and tally['electedWeights'][DAN] == 0.0)
    check('pairwise matrix travels with the result',
          len(tally['pairwise']) == 6
          and all('wins' in p for p in tally['pairwise']))
    check('3 ballots cast, 3 counted, none refused',
          tally['ballotsCast'] == 3 and tally['ballotsCounted'] == 3
          and not tally['refusedBallots'])
    check('the suggestion points at the apply knob',
          'apply' in tally['suggestion']['knob'])

    print('\ncopeland fallback (cycle, labeled)')
    m = _mgr()
    m.objectTables['WorldviewElection'][50] = SimpleNamespace(
        name='cycle-election', group_name='demo-town-assembly',
        candidate_concept_names_json=json.dumps([ALICE, BOB, CAROL]),
        mode='ranked-condorcet', status='open',
        pre_normalized_value=None)
    for i, ranking in enumerate([[ALICE, BOB, CAROL],
                                 [BOB, CAROL, ALICE],
                                 [CAROL, ALICE, BOB]]):
        m.objectTables['WorldviewBallot'][50 + i] = SimpleNamespace(
            name=f'cycle-ballot-{i}', election_name='cycle-election',
            voter=f'v{i}', ranking_json=json.dumps(ranking),
            pre_normalized_value=None)
    tally = tally_election(m, 'cycle-election')
    check('rock-paper-scissors cycle: no Condorcet winner, fallback '
          'LABELED, three-way tie honest',
          tally['ok'] and 'copeland-fallback' in tally['note']
          and sorted(tally['winners']) == sorted([ALICE, BOB, CAROL]))

    print('\napproval + sole modes')
    m = _mgr()
    m.objectTables['WorldviewElection'][51] = SimpleNamespace(
        name='approval-election', group_name='demo-town-assembly',
        candidate_concept_names_json='[]', mode='approval',
        status='open', pre_normalized_value=None)
    ballots = [
        {'name': 'ap-1', 'voter': 'v1',
         'approvals_json': json.dumps([CAROL, ALICE])},
        {'name': 'ap-2', 'voter': 'v2',
         'approvals_json': json.dumps([CAROL])},
        {'name': 'ap-3', 'voter': 'v3', 'approvals_json': '[]'},
        {'name': 'ap-4', 'voter': 'v4',
         'approvals_json': json.dumps(['no-such-worldview'])},
    ]
    for i, b in enumerate(ballots):
        m.objectTables['WorldviewBallot'][60 + i] = SimpleNamespace(
            election_name='approval-election',
            pre_normalized_value=None, **b)
    tally = tally_election(m, 'approval-election')
    check('approval: candidates default to the group members, '
          'shares = approval fractions',
          tally['ok'] and tally['winners'] == [CAROL]
          and abs(tally['electedWeights'][CAROL] - 2 / 3) < 1e-4
          and abs(tally['electedWeights'][ALICE] - 1 / 3) < 1e-4)
    refused = {r['ballot'] for r in tally['refusedBallots']}
    check('empty + unknown-candidate ballots refused BY NAME',
          refused == {'ap-3', 'ap-4'}
          and tally['ballotsCounted'] == 2)
    m.objectTables['WorldviewElection'][52] = SimpleNamespace(
        name='sole-election', group_name='demo-town-assembly',
        candidate_concept_names_json='[]', mode='sole',
        status='open', pre_normalized_value=None)
    for i, (voter, choice) in enumerate(
            [('v1', BOB), ('v2', BOB), ('v3', ALICE), ('v4', '')]):
        m.objectTables['WorldviewBallot'][70 + i] = SimpleNamespace(
            name=f'sole-{i}', election_name='sole-election',
            voter=voter, sole_choice=choice,
            pre_normalized_value=None)
    tally = tally_election(m, 'sole-election')
    check('sole: first-past shares, missing choice refused',
          tally['ok'] and tally['winners'] == [BOB]
          and abs(tally['electedWeights'][BOB] - 2 / 3) < 1e-4
          and len(tally['refusedBallots']) == 1)

    print('\napply gate + weighted aggregation downstream')
    m = _mgr()
    baseline = aggregate_group(m, 'demo-town-assembly')
    min_wage = next(t for t in baseline['terms']
                    if t['key'] == 'minimum-wage')
    check('unweighted baseline: 3-vs-1 minimum-wage = '
          'large-majority (scr-3 parity)',
          not baseline['weighted']
          and min_wage['directionClass'] == 'large-majority'
          and min_wage['dominantFraction'] == 0.75)
    # An open election never applies.
    for row in m.objectTables['WorldviewElection'].values():
        if row.name == 'demo-labor-definition-election':
            row.status = 'open'
    refused = apply_election(m, 'demo-labor-definition-election')
    check('applying an OPEN election refused naming the status knob',
          not refused['ok']
          and refused['suggestion']['knob']
          == 'WorldviewElection.status')
    for row in m.objectTables['WorldviewElection'].values():
        if row.name == 'demo-labor-definition-election':
            row.status = 'closed'
    applied = apply_election(m, 'demo-labor-definition-election')
    check('closed election applies with provenance',
          applied['ok']
          and 'vote-derived' in applied['weightsProvenance']
          and 'ranked-condorcet' in applied['weightsProvenance'])
    weighted = aggregate_group(m, 'demo-town-assembly')
    min_wage = next(t for t in weighted['terms']
                    if t['key'] == 'minimum-wage')
    check("dan's zero weight silences his dissent: minimum-wage "
          'reads consensus under the ELECTED definition',
          weighted['weighted']
          and min_wage['directionClass'] == 'consensus'
          and min_wage['dominantFraction'] == 1.0)
    check('weights + provenance travel on the aggregate',
          weighted['memberWeights'][CAROL] == 0.5
          and 'vote-derived' in weighted['weightsProvenance'])
    other = aggregate_group(m, 'demo-political-group')
    check('groups without weights keep exact equal-voice behavior',
          other['ok'] and not other['weighted']
          and other['memberWeights'] is None)

    print('\nhonest refusals')
    m = _mgr()
    report = tally_election(m, 'no-such')
    check('unknown election 404 with known list',
          not report['ok'] and 'knownElections' in report)
    m.objectTables['WorldviewBallot'] = {}
    report = tally_election(m, 'demo-labor-definition-election')
    check('no ballots = honest refusal, not a zero score',
          not report['ok'] and 'no ballots' in report['error'])
    m = _mgr()
    m.objectTables['WorldviewElection'][53] = SimpleNamespace(
        name='empty-election', group_name='no-such-group',
        candidate_concept_names_json='[]', mode='approval',
        status='open', pre_normalized_value=None)
    report = tally_election(m, 'empty-election')
    check('no candidates refused naming both knobs',
          not report['ok'] and 'candidates' in report['error'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
