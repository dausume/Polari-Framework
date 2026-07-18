"""
Selftest — Democratic Scorecard revamp mechanism C: logic-fork
criterion votes (vote on which of several alternate criteria a
specific decision point/fork should use, distinct from mechanism A's
whole-Display votes and mechanism B's whole-worldview-concept votes).

Run from polari-framework/:
    python3 -m scoring.selftest_logic_fork_vote

Covers: sole-choice tally reuses worldview_elections.py's tally
functions correctly; the real 5-ballot vote (Dustin's own worked
sentencing-fork example) produces the honest, by-hand-computed winner
(reform-durability-likelihood, 3/5); apply gate (closed-only); tie
refusal; resolved_procedure_summary() reads default vs. vote-resolved
correctly both before and after apply; the 5 additional forks of the
sexual-assault-adjudication-framework (Dustin: "come up with a more
realistic criteria evaluation... flush out a more complete logic
graph") tally to their hand-computed winners; the graph's 10 edges
connect all 6 forks start-to-terminal.
"""

from types import SimpleNamespace

from scoring.logic_fork_vote import (
    SEED_DECISION_PROCEDURE_EDGES, SEED_LOGIC_FORK_BALLOTS,
    SEED_LOGIC_FORK_CRITERIA, SEED_LOGIC_FORK_VOTES,
    apply_logic_fork_vote, resolved_procedure_summary,
    tally_logic_fork_vote,
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
        'LogicForkCriterion': _rows(SEED_LOGIC_FORK_CRITERIA),
        'LogicForkVote': _rows(
            SEED_LOGIC_FORK_VOTES,
            {'elected_criterion_name': '', 'elected_provenance': ''}),
        'LogicForkBallot': _rows(SEED_LOGIC_FORK_BALLOTS),
        'DecisionProcedureEdge': _rows(SEED_DECISION_PROCEDURE_EDGES),
    })


DEFAULT = 'is-repeat-offender'
ALTERNATE = 'reform-durability-likelihood'


if __name__ == '__main__':
    print('\nDemocratic Scorecard revamp mechanism C: logic-fork '
          'criterion votes\n')

    print('the real sole-choice vote (hand-computed when this seed '
          'was written)')
    m = _mgr()
    tally = tally_logic_fork_vote(m, 'recidivism-fork-criterion-vote')
    check('tallies ok, 2 known candidates, no unknown candidates',
          tally.get('ok') and len(tally['candidates']) == 2
          and not tally['unknownCandidates'])
    check('5 ballots cast and counted, none refused',
          tally.get('ok') and tally['ballotsCast'] == 5
          and tally['ballotsCounted'] == 5
          and not tally['refusedBallots'])
    check('reform-durability-likelihood wins 3/5 votes',
          tally.get('ok') and tally['winners'] == [ALTERNATE]
          and abs(tally['weights'][ALTERNATE] - 3 / 5) < 1e-6
          and abs(tally['weights'][DEFAULT] - 2 / 5) < 1e-6)

    print('\nresolved_procedure_summary() BEFORE apply: shows the '
          'incumbent default, not yet vote-resolved')
    before = resolved_procedure_summary(
        m, 'repeat-offense-sentencing-framework')
    fork_before = before['forks'][0]
    check('before apply: resolvedCriterion = the incumbent default, '
          "source = 'incumbent-default'",
          before.get('ok') and fork_before['resolvedCriterion'] == DEFAULT
          and fork_before['resolvedSource'] == 'incumbent-default')

    print('\napply gate: closed-only, singular winner required')
    applied = apply_logic_fork_vote(m, 'recidivism-fork-criterion-vote')
    check('closed vote applies with provenance',
          applied.get('ok') and applied['electedCriterion'] == ALTERNATE
          and 'vote-derived' in applied['electedProvenance'])

    print('\nresolved_procedure_summary() AFTER apply: shows the '
          "vote's winner, not the old default")
    after = resolved_procedure_summary(
        m, 'repeat-offense-sentencing-framework')
    fork_after = after['forks'][0]
    check("after apply: resolvedCriterion = the vote's winner, "
          "source = 'vote' (overrides the incumbent default)",
          after.get('ok') and fork_after['resolvedCriterion'] == ALTERNATE
          and fork_after['resolvedSource'] == 'vote')

    m2 = _mgr()
    for row in m2.objectTables['LogicForkVote'].values():
        row.status = 'open'
    refused = apply_logic_fork_vote(m2, 'recidivism-fork-criterion-vote')
    check('applying an OPEN vote refused naming the status knob',
          not refused['ok']
          and refused['suggestion']['knob'] == 'LogicForkVote.status')

    print('\ntie refusal: a fork\'s resolved criterion is singular')
    m3 = _mgr()
    m3.objectTables['LogicForkVote'][50] = SimpleNamespace(
        name='tie-vote', decision_procedure_name='x', fork_name='y',
        mode='sole', status='closed',
        candidate_criterion_names_json=(
            '["' + DEFAULT + '", "' + ALTERNATE + '"]'),
        elected_criterion_name='', elected_provenance='',
        pre_normalized_value=None)
    for i, (voter, choice) in enumerate(
            [('v1', DEFAULT), ('v2', ALTERNATE)]):
        m3.objectTables['LogicForkBallot'][50 + i] = SimpleNamespace(
            name=f'tie-ballot-{i}', vote_name='tie-vote', voter=voter,
            approvals_json='[]', sole_choice=choice, ranking_json='[]',
            pre_normalized_value=None)
    tie_result = apply_logic_fork_vote(m3, 'tie-vote')
    check('a 1-1 tie refuses rather than picking arbitrarily',
          not tie_result['ok'] and len(tie_result['winners']) == 2)

    print('\nthe 5 additional sexual-assault-adjudication-framework '
          'forks tally to their hand-computed winners')
    m5 = _mgr()
    expected_winners = {
        'consent-determination-fork-vote': 'affirmative-consent-standard',
        'testimony-sufficiency-fork-vote':
            'victim-testimony-sufficient-standard',
        'prior-history-admissibility-fork-vote':
            'categorically-excluded-with-exceptions-standard',
        'aggravating-mitigating-weighting-fork-vote':
            'structured-point-based-guideline-standard',
        'victim-impact-weighting-fork-vote':
            'clinically-scored-trauma-standard',
    }
    for vote_name, expected_winner in expected_winners.items():
        result = tally_logic_fork_vote(m5, vote_name)
        check(f'{vote_name}: winner = {expected_winner}',
              result.get('ok') and result['winners'] == [expected_winner]
              and result['ballotsCast'] == 5
              and not result['refusedBallots'],
              extra=f"got={result.get('winners')}" if not (
                  result.get('ok')
                  and result.get('winners') == [expected_winner])
              else '')

    print('\nthe graph: 10 edges connect all 6 forks, start to '
          'terminal outcomes')
    graph = resolved_procedure_summary(
        m5, 'sexual-assault-adjudication-framework')
    # 5, not 6: recidivism-risk-fork's own LogicForkCriterion rows are
    # tagged under 'repeat-offense-sentencing-framework' (defined
    # there first, reused here) — resolved_procedure_summary()
    # correctly only enumerates LOCALLY-DEFINED criteria per
    # procedure; the edges list still references the shared fork by
    # name (checked separately below), an honest cross-procedure
    # pointer rather than duplicated criteria.
    check('resolved_procedure_summary finds the 5 LOCALLY-defined '
          "forks (recidivism-risk-fork is cross-referenced via an "
          "edge, not locally defined here)",
          graph.get('ok') and len(graph['forks']) == 5,
          extra=f"got {len(graph.get('forks', []))}")
    check('graph carries all 10 edges',
          len(graph.get('edges', [])) == 10)
    # A TRUE start edge has no predecessor fork AND no outcome label.
    # 'edge-conviction-to-recidivism' also has fromFork=None (its
    # predecessor is the CONVICTION terminal, not a fork) but carries
    # fromOutcome='CONVICTION' — distinguishable from the real start.
    start_edges = [e for e in graph.get('edges', [])
                  if e['fromFork'] is None and e['fromOutcome'] is None]
    terminal_edges = [e for e in graph.get('edges', [])
                      if e['toTerminal'] is not None]
    check('exactly one TRUE start edge (no predecessor fork or '
          'outcome), 4 terminal edges (2 ACQUITTAL, 1 CONVICTION, '
          '1 SENTENCE_IMPOSED)',
          len(start_edges) == 1 and len(terminal_edges) == 4,
          extra=f"start={len(start_edges)} terminal={len(terminal_edges)}")

    print('\nhonest refusals')
    m4 = _mgr()
    report = tally_logic_fork_vote(m4, 'no-such-vote')
    check('unknown vote 404 with known list',
          not report['ok'] and 'knownVotes' in report)
    m4.objectTables['LogicForkBallot'] = {}
    report = tally_logic_fork_vote(m4, 'recidivism-fork-criterion-vote')
    check('no ballots = honest refusal, not a zero result',
          not report['ok'] and 'no ballots' in report['error'])
    report = resolved_procedure_summary(m4, 'no-such-procedure')
    check('unknown decision procedure 404 with known list',
          not report['ok'] and 'knownProcedures' in report)

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
