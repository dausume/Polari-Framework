"""
@cross-cutting
@module scoring.politician_scoring
@tags @xc:bindings

Politician scoring (scr-6) — a politician's concept score is a
VOTE-WEIGHTED aggregation over policy scores: yea on a policy that
supports the concept contributes positively, nay inverts, abstention
is a PARTICIPATION GAP (surfaced, never scored as a stance). Dustin
2026-07-08: "Politician scoring through Policy Scoring via Score
Assertions onto policies. We should track politician voting on
policies."

Time-scoped: votes carry dates, so a politician scores per timeframe
(pass a timeframe ScoreContext name — scr-4 native). Every vote's
contribution is itemized; policies that can't score (no confirmed
assertions) are named, not dropped silently.

Cohorts: a ScoreGroup with member_subject_names_json (party,
committee) gets a cohort read — per-member scores + how often the
cohort actually votes together, banded through the SAME editable
AgreementPolicy as worldview agreement (divisive/consensus votes are
comparable to divisive/consensus definitions).

@consumers
  - scoring.scoring_api (GET /api/scoring/politicians/{name}/score,
    GET /api/scoring/cohorts/{name}/report)
@see /OVERLAP_MAP.md
"""

import json
from datetime import date

from scoring.agreement_policy import classify_max, policy_bands
from scoring.policy_scoring import score_policy
from scoring.timeframes import frame_of_context


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _vote_in_frame(vote_row, frame):
    if frame is None:
        return True
    raw = getattr(vote_row, 'vote_date', '') or ''
    try:
        when = date.fromisoformat(raw[:10])
    except (ValueError, TypeError):
        return False  # undated votes can't satisfy a time scope
    return frame[0] <= when <= frame[1]


def politician_score(manager, politician_name, concept_name,
                     timeframe_context='', evidence_policy=''):
    """One politician's concept score from their voting record.

    stance = mean over decisive votes of (±1 per yea/nay) × the
    policy's stance for the concept; score = (stance + 1) / 2.
    Abstentions and unscoreable policies are itemized outside the
    math."""
    subjects = _by_name(manager, 'ScoreSubject')
    politician = subjects.get(politician_name)
    if politician is None:
        return {'ok': False,
                'error': f"no ScoreSubject named '{politician_name}'"}

    frame, frame_error = None, None
    if timeframe_context:
        contexts = _by_name(manager, 'ScoreContext')
        ctx = contexts.get(timeframe_context)
        frame = frame_of_context(ctx) if ctx is not None else None
        if frame is None:
            return {'ok': False,
                    'error': f"'{timeframe_context}' is not a "
                             'timeframe ScoreContext',
                    'suggestion': {'knob': 'timeframe',
                                   'action': 'pass a ScoreContext '
                                             'name whose value_json '
                                             'has start/end dates'}}

    votes = [v for v in _rows(manager, 'PolicyVote')
             if getattr(v, 'politician_name', '') == politician_name]
    in_scope = [v for v in votes if _vote_in_frame(v, frame)]
    out_of_scope = len(votes) - len(in_scope)
    if not votes:
        return {'ok': False,
                'error': f"no PolicyVote rows for "
                         f"'{politician_name}'",
                'suggestion': {'knob': 'POST /api/scoring/'
                                       'ingest-votes',
                               'action': 'ingest a voting record '
                                         '(api-profiler a public '
                                         'vote API, then map its '
                                         'class)'}}

    contributions, abstains, unscoreable = [], [], []
    stance_sum, decisive = 0.0, 0
    policy_cache = {}
    for v in in_scope:
        policy_name = getattr(v, 'policy_name', '')
        kind = getattr(v, 'vote', 'abstain')
        base = {'policy': policy_name, 'vote': kind,
                'voteDate': getattr(v, 'vote_date', ''),
                'chamber': getattr(v, 'chamber', '')}
        if kind == 'abstain':
            abstains.append(base)
            continue
        if policy_name not in policy_cache:
            policy_cache[policy_name] = score_policy(
                manager, policy_name, concept_name,
                evidence_policy=evidence_policy)
        policy_report = policy_cache[policy_name]
        if not policy_report.get('ok'):
            unscoreable.append({
                **base,
                'error': policy_report.get('error', ''),
                'suggestion': policy_report.get('suggestion')})
            continue
        sign = 1.0 if kind == 'yea' else -1.0
        contribution = sign * policy_report['stance']
        stance_sum += contribution
        decisive += 1
        contributions.append({
            **base,
            'policyStance': policy_report['stance'],
            'policyScore': policy_report['score'],
            'contribution': round(contribution, 6)})

    if not decisive:
        return {'ok': False,
                'error': f"'{politician_name}' cast no decisive vote "
                         f"on a policy scoreable for "
                         f"'{concept_name}'",
                'abstains': abstains,
                'unscoreablePolicies': unscoreable,
                'suggestion': {
                    'knob': 'ScoreAssertion',
                    'action': 'confirm assertions binding the voted '
                              'policies to this concept'}}

    stance = stance_sum / decisive
    participation = decisive / (decisive + len(abstains)) \
        if (decisive + len(abstains)) else None
    return {
        'ok': True,
        'politician': politician_name,
        'displayName': getattr(politician, 'display_name', '')
        or politician_name,
        'concept': concept_name,
        'timeframe': timeframe_context or None,
        'stance': round(stance, 6),
        'score': round((stance + 1.0) / 2.0, 6),
        'decisiveVotes': decisive,
        'abstains': abstains,
        'participation': round(participation, 4)
        if participation is not None else None,
        'unscoreablePolicies': unscoreable,
        'votesOutOfTimeframe': out_of_scope,
        'voteBreakdown': contributions,
        'note': 'stance = mean over decisive votes of ±(policy '
                'stance); abstentions are a participation gap, '
                'never a stance; unscoreable policies are named',
    }


def cohort_report(manager, group_name, concept_name,
                  policy_name='', timeframe_context=''):
    """A politician cohort (ScoreGroup.member_subject_names_json):
    per-member concept scores + per-policy vote cohesion, banded
    through the editable AgreementPolicy."""
    groups = _by_name(manager, 'ScoreGroup')
    group = groups.get(group_name)
    if group is None:
        return {'ok': False,
                'error': f"no ScoreGroup named '{group_name}'",
                'knownGroups': sorted(groups)}
    try:
        members = json.loads(
            getattr(group, 'member_subject_names_json', '') or '[]')
    except Exception:
        members = []
    if not members:
        return {'ok': False,
                'error': f"group '{group_name}' has no subject "
                         'members',
                'suggestion': {
                    'knob': 'ScoreGroup.member_subject_names_json',
                    'action': 'list the politician ScoreSubject '
                              'names that form this cohort'}}

    policies = _rows(manager, 'AgreementPolicy')
    wanted = policy_name or 'default-agreement'
    agreement = next((p for p in policies
                      if getattr(p, 'name', '') == wanted),
                     policies[0] if policies else None)
    bands = policy_bands(agreement)['direction'] \
        if agreement is not None else []

    member_scores = []
    for member in members:
        report = politician_score(manager, member, concept_name,
                                  timeframe_context)
        member_scores.append(
            {'politician': member,
             'score': report.get('score'),
             'stance': report.get('stance'),
             'participation': report.get('participation'),
             'error': None if report.get('ok')
             else report.get('error')})

    # Vote cohesion per policy the cohort actually voted on.
    votes_by_policy = {}
    for v in _rows(manager, 'PolicyVote'):
        if getattr(v, 'politician_name', '') in members:
            votes_by_policy.setdefault(
                getattr(v, 'policy_name', ''), []).append(v)
    cohesion = []
    for pname, vrows in sorted(votes_by_policy.items()):
        tally = {'yea': 0, 'nay': 0, 'abstain': 0}
        for v in vrows:
            kind = getattr(v, 'vote', 'abstain')
            tally[kind if kind in tally else 'abstain'] += 1
        decisive = tally['yea'] + tally['nay']
        dominant = (max(tally['yea'], tally['nay']) / decisive
                    if decisive else 0.5)
        cohesion.append({
            'policy': pname, **tally,
            'dominantFraction': round(dominant, 4),
            'band': classify_max(dominant, bands) if bands
            else 'unclassified'})

    scored = [m['score'] for m in member_scores
              if m['score'] is not None]
    return {
        'ok': True,
        'group': group_name,
        'displayName': getattr(group, 'display_name', '')
        or group_name,
        'groupType': getattr(group, 'group_type', ''),
        'concept': concept_name,
        'timeframe': timeframe_context or None,
        'agreementPolicy': getattr(agreement, 'name', None)
        if agreement is not None else None,
        'members': member_scores,
        'cohortMeanScore': round(sum(scored) / len(scored), 6)
        if scored else None,
        'voteCohesion': cohesion,
        'note': 'cohesion bands use the same editable '
                'AgreementPolicy as worldview agreement — divisive '
                'votes and divisive definitions read on one scale',
    }
