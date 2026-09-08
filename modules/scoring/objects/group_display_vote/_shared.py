"""@module scoring.objects.group_display_vote._shared — what the group_display_vote row classes share (constants, seeds, helpers); split from group_display_vote_basis.py (sap-2c)."""
from scoring.worldview_elections_basis import (
    ELECTION_MODES, _by_name, _parse, _rows,
    _tally_approval, _tally_ranked, _tally_sole,
)
import json

VOTE_STATUSES = ('open', 'closed')
def tally_display_vote(manager, vote_name):
    """The running (or final) tally for one GroupDisplayVote — same
    shape/semantics as worldview_elections.tally_election(), over
    Display candidates instead of worldview concepts."""
    vote = _by_name(manager, 'GroupDisplayVote').get(vote_name)
    if vote is None:
        return {'ok': False,
                'error': f"no GroupDisplayVote named '{vote_name}'",
                'knownVotes': sorted(
                    _by_name(manager, 'GroupDisplayVote'))}
    mode = getattr(vote, 'mode', 'approval')
    if mode not in ELECTION_MODES:
        return {'ok': False,
                'error': f"unknown mode '{mode}'",
                'modes': list(ELECTION_MODES)}
    candidates = _parse(
        getattr(vote, 'candidate_display_names_json', '[]'), '[]')
    if not candidates:
        return {'ok': False,
                'error': 'vote has no candidate Displays',
                'suggestion': {
                    'knob': 'candidate_display_names_json',
                    'action': 'name the DisplayDefinition rows being '
                              'voted on — unlike WorldviewElection, '
                              "there's no default to fall back to "
                              '(a group\'s members are worldview '
                              'concepts, not Displays)'}}
    known_displays = set(_by_name(manager, 'DisplayDefinition'))
    unknown_candidates = [c for c in candidates if c not in known_displays]
    ballots = [b for b in _rows(manager, 'GroupDisplayBallot')
               if getattr(b, 'vote_name', '') == vote_name]
    if not ballots:
        return {'ok': False,
                'error': 'no ballots cast',
                'candidates': candidates}

    pairwise = None
    if mode == 'approval':
        per, winners, weights, refused, note = _tally_approval(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    elif mode == 'sole':
        per, winners, weights, refused, note = _tally_sole(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    else:
        per, winners, weights, refused, note, pairwise, counted = \
            _tally_ranked(ballots, candidates)

    report = {
        'ok': True,
        'vote': vote_name,
        'displayName': getattr(vote, 'display_name', '') or vote_name,
        'group': getattr(vote, 'group_name', ''),
        'concept': getattr(vote, 'concept_name', ''),
        'mode': mode,
        'status': getattr(vote, 'status', 'open'),
        'candidates': candidates,
        # Candidates that name no real DisplayDefinition row — surfaced
        # honestly rather than silently tallied as if they were real.
        'unknownCandidates': unknown_candidates,
        'ballotsCast': len(ballots),
        'ballotsCounted': counted,
        'refusedBallots': refused,
        'results': per,
        'winners': winners,
        'weights': {c: round(w, 6) for c, w in weights.items()},
        'note': note,
        'suggestion': {
            'knob': f'POST /api/scoring/display-votes/{vote_name}/apply',
            'action': "close the vote (status = 'closed'), then apply "
                      'to record the winning Display on this vote row '
                      '(explicit, provenance-stamped)'},
    }
    if pairwise is not None:
        report['pairwise'] = pairwise
    return report
def apply_display_vote(manager, vote_name):
    """Write a CLOSED vote's winning Display onto the GroupDisplayVote
    row itself (elected_display_name + elected_provenance). A tie
    (multiple winners) refuses — an endorsed Display is singular by
    definition; re-vote or break the tie explicitly rather than
    picking one arbitrarily."""
    tally = tally_display_vote(manager, vote_name)
    if not tally.get('ok'):
        return tally
    if tally['status'] != 'closed':
        return {'ok': False,
                'error': f"vote '{vote_name}' is '{tally['status']}' "
                         '— only closed votes apply',
                'suggestion': {
                    'knob': 'GroupDisplayVote.status',
                    'action': "set 'closed' first (an explicit edit) "
                              'so the applied result is final'}}
    if len(tally['winners']) != 1:
        return {'ok': False,
                'error': f"{len(tally['winners'])} winners tied "
                         f"({', '.join(tally['winners']) or 'none'}) "
                         '— an endorsed Display is singular; re-vote '
                         'or break the tie explicitly rather than '
                         'picking one arbitrarily',
                'winners': tally['winners']}
    vote = _by_name(manager, 'GroupDisplayVote').get(vote_name)
    winner = tally['winners'][0]
    vote.elected_display_name = winner
    vote.elected_provenance = (
        f"vote-derived from '{vote_name}' ({tally['mode']}, "
        f"{tally['ballotsCounted']} ballots counted)")
    try:
        manager.db.saveInstanceInDB(vote)
    except Exception:
        pass  # in-memory managers (selftests) have no db
    return {'ok': True,
            'vote': vote_name,
            'group': tally['group'],
            'concept': tally['concept'],
            'electedDisplay': winner,
            'electedProvenance': vote.elected_provenance,
            'note': 'this vote row now names the group\'s endorsed '
                    'Display for explaining this score'}
def _text_display(name, description, source_class, heading, body):
    """One minimal, honest DisplayDefinition: a single 'text' item
    (DisplayItem.type='text', item=a plain string — verified against
    `polari-platform-angular/.../DisplayItem.ts`, not guessed). No
    componentProps/registered component name is used, so this renders
    without depending on any particular Angular component being
    registered in DISPLAY_COMPONENT_REGISTRY."""
    return {
        'name': name,
        'description': description,
        'source_class': source_class,
        'isPage': False,
        'pageRoute': '',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 200,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': f'{name}-item', 'index': 0, 'type': 'text',
                'item': f'{heading}\n\n{body}',
                'items': [], 'nestedRows': [], 'componentProps': {},
                'rowSegmentsUsed': 12, 'title': heading,
                'visible': True, 'collapsed': False,
            }],
        }]}),
    }
SEED_GROUP_DISPLAYS = [
    _text_display(
        'housing-afford-explainer-tenant',
        'Tenant Affordability Coalition’s explanation of the '
        'Housing Affordability score.',
        'ScoreConcept',
        'What renters actually feel',
        'Price-to-income and rent burden are what decide whether a '
        'household can stay housed THIS YEAR. Construction quality and '
        'permitting numbers are long-run policy levers — real, but '
        'they don’t pay this month’s rent. If a state scores '
        'well here, that means today’s households are less '
        'squeezed, full stop.',
    ),
    _text_display(
        'housing-afford-explainer-quality',
        'Building Quality & Codes Coalition’s explanation of the '
        'Housing Affordability score.',
        'ScoreConcept',
        'Why cheap housing often isn’t actually cheap',
        'A low price-to-income ratio can just mean weak building codes '
        'and short-lived construction — costs that don’t '
        'disappear, they get pushed onto repairs, energy bills, and '
        'disaster recovery later. This score weights construction '
        'quality heavily on purpose: durable housing is the long-run '
        'affordable option even when it costs more up front.',
    ),
    _text_display(
        'housing-afford-explainer-supply',
        'Housing Supply Economists Network’s explanation of the '
        'Housing Affordability score.',
        'ScoreConcept',
        'Follow the permits, not just the price',
        'Price and rent burden are downstream symptoms of how much '
        'housing actually gets built. New-permits-per-capita is the '
        'leading indicator: states that build more relieve price '
        'pressure over time, even if today’s price looks high '
        'while that supply is still under construction.',
    ),
]
SEED_GROUP_DISPLAY_VOTES = [{
    'name': 'housing-explainer-vote',
    'display_name': 'Which explanation of Housing Affordability is '
                    'most persuasive?',
    'description': 'Approval vote over the assembly\'s three '
                   'candidate explanatory Displays — mechanism A: '
                   'voting on explanatory quality, never on term '
                   'weights (that\'s mechanism B, see '
                   'housing-affordability-election).',
    'group_name': 'housing-affordability-assembly',
    'concept_name': '',
    'candidate_display_names_json': json.dumps([
        'housing-afford-explainer-tenant',
        'housing-afford-explainer-quality',
        'housing-afford-explainer-supply']),
    'mode': 'approval',
    'status': 'closed',
    'opens_date': '2026-06-21', 'closes_date': '2026-07-05',
    'provenance_id': 'Phase 4 mechanism-A seed',
}]
SEED_GROUP_DISPLAY_BALLOTS = [
    {
        'name': 'display-ballot-tenant-coalition',
        'vote_name': 'housing-explainer-vote',
        'voter': 'tenant-affordability-coalition',
        'approvals_json': json.dumps(['housing-afford-explainer-tenant']),
        'cast_date': '2026-06-22',
    },
    {
        'name': 'display-ballot-quality-guild',
        'vote_name': 'housing-explainer-vote',
        'voter': 'building-quality-professionals-guild',
        'approvals_json': json.dumps([
            'housing-afford-explainer-quality',
            'housing-afford-explainer-supply']),
        'cast_date': '2026-06-23',
    },
    {
        'name': 'display-ballot-supply-economists',
        'vote_name': 'housing-explainer-vote',
        'voter': 'housing-supply-economists-network',
        'approvals_json': json.dumps([
            'housing-afford-explainer-supply',
            'housing-afford-explainer-tenant']),
        'cast_date': '2026-06-24',
    },
    {
        'name': 'display-ballot-renter',
        'vote_name': 'housing-explainer-vote',
        'voter': 'demo-renter-voter',
        'approvals_json': json.dumps(['housing-afford-explainer-tenant']),
        'cast_date': '2026-06-25',
    },
    {
        'name': 'display-ballot-tradesperson',
        'vote_name': 'housing-explainer-vote',
        'voter': 'demo-tradesperson-voter',
        'approvals_json': json.dumps(['housing-afford-explainer-quality']),
        'cast_date': '2026-06-26',
    },
]
