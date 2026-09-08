"""
Selftest — Democratic Scorecard revamp Phase 4, mechanism A: Group
Display votes (vote on which Display explains a score best, distinct
from mechanism B's vote on term-weighting worldviews).

Run from polari-framework/:
    python3 -m scoring.group_display_vote_selftest

Covers: approval tally reuses worldview_elections.py's tally functions
correctly (same math, different candidate universe); the real
5-ballot vote produces the honest, by-hand-computed winner (tenant
explainer, 3/5 approvals); apply gate (closed-only); tie refusal
(an endorsed Display is singular); unknown-candidate honesty.
"""

from types import SimpleNamespace

from scoring.group_display_vote_basis import (
    SEED_GROUP_DISPLAY_BALLOTS, SEED_GROUP_DISPLAY_VOTES,
    SEED_GROUP_DISPLAYS, apply_display_vote, tally_display_vote,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list, extra_defaults=None):
    defaults = {'pre_normalized_value': None}
    if extra_defaults:
        defaults.update(extra_defaults)
    return {i: SimpleNamespace(**{**defaults, **r})
            for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'DisplayDefinition': _rows(SEED_GROUP_DISPLAYS),
        'GroupDisplayVote': _rows(
            SEED_GROUP_DISPLAY_VOTES,
            {'elected_display_name': '', 'elected_provenance': ''}),
        'GroupDisplayBallot': _rows(SEED_GROUP_DISPLAY_BALLOTS),
    })


TENANT = 'housing-afford-explainer-tenant'
QUALITY = 'housing-afford-explainer-quality'
SUPPLY = 'housing-afford-explainer-supply'


if __name__ == '__main__':
    print('\nDemocratic Scorecard revamp Phase 4: Group Display votes '
          '(mechanism A)\n')

    print('the real approval vote (hand-computed when this seed was '
          'written)')
    m = _mgr()
    tally = tally_display_vote(m, 'housing-explainer-vote')
    check('tallies ok, 3 known candidates, no unknown candidates',
          tally.get('ok') and len(tally['candidates']) == 3
          and not tally['unknownCandidates'])
    check('5 ballots cast and counted, none refused',
          tally.get('ok') and tally['ballotsCast'] == 5
          and tally['ballotsCounted'] == 5
          and not tally['refusedBallots'])
    check('tenant explainer wins 3/5 approvals (7 total approvals '
          'cast: 3+2+2)',
          tally.get('ok') and tally['winners'] == [TENANT]
          and abs(tally['weights'][TENANT] - 3 / 7) < 1e-6
          and abs(tally['weights'][QUALITY] - 2 / 7) < 1e-6
          and abs(tally['weights'][SUPPLY] - 2 / 7) < 1e-6)

    print('\napply gate: closed-only, singular winner required')
    m = _mgr()
    applied = apply_display_vote(m, 'housing-explainer-vote')
    check('closed vote applies with provenance',
          applied.get('ok') and applied['electedDisplay'] == TENANT
          and 'vote-derived' in applied['electedProvenance'])
    vote_row = next(r for r in m.objectTables['GroupDisplayVote'].values()
                    if r.name == 'housing-explainer-vote')
    check('the vote row itself carries the elected result '
          '(not ScoreGroup — a group may run several display votes)',
          vote_row.elected_display_name == TENANT)

    m2 = _mgr()
    for row in m2.objectTables['GroupDisplayVote'].values():
        row.status = 'open'
    refused = apply_display_vote(m2, 'housing-explainer-vote')
    check('applying an OPEN vote refused naming the status knob',
          not refused['ok']
          and refused['suggestion']['knob'] == 'GroupDisplayVote.status')

    print('\ntie refusal: an endorsed Display is singular')
    m3 = _mgr()
    m3.objectTables['GroupDisplayVote'][50] = SimpleNamespace(
        name='tie-vote', group_name='housing-affordability-assembly',
        concept_name='', mode='approval', status='closed',
        candidate_display_names_json=(
            '["' + TENANT + '", "' + QUALITY + '"]'),
        elected_display_name='', elected_provenance='',
        pre_normalized_value=None)
    for i, (voter, approvals) in enumerate(
            [('v1', [TENANT]), ('v2', [QUALITY])]):
        m3.objectTables['GroupDisplayBallot'][50 + i] = SimpleNamespace(
            name=f'tie-ballot-{i}', vote_name='tie-vote', voter=voter,
            approvals_json=str(approvals).replace("'", '"'),
            sole_choice='', ranking_json='[]',
            pre_normalized_value=None)
    tie_result = apply_display_vote(m3, 'tie-vote')
    check('a 1-1 tie refuses rather than picking arbitrarily',
          not tie_result['ok'] and len(tie_result['winners']) == 2)

    print('\nhonest refusals')
    m4 = _mgr()
    report = tally_display_vote(m4, 'no-such-vote')
    check('unknown vote 404 with known list',
          not report['ok'] and 'knownVotes' in report)
    m4.objectTables['GroupDisplayBallot'] = {}
    report = tally_display_vote(m4, 'housing-explainer-vote')
    check('no ballots = honest refusal, not a zero result',
          not report['ok'] and 'no ballots' in report['error'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
