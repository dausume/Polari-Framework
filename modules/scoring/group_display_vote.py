"""
@cross-cutting
@module scoring.group_display_vote
@tags @xc:bindings

Group Display votes — mechanism A of the Democratic Scorecard revamp
(Dustin 2026-07-14): within a ScoreGroup, members vote on which of
several candidate Displays (`polariApiServer.displayDefinition.
DisplayDefinition`) best explains a score's terms and why they
matter — a DIFFERENT axis from mechanism B (`worldview_elections.py`
— vote on which member WORLDVIEW/ScoreConcept the group reads by).
Mechanism A never touches term weights; it only says "of these
explanatory Displays, which one actually helps people understand?"

Reuses `worldview_elections.py`'s tally functions (`_tally_approval`/
`_tally_sole`/`_tally_ranked` — plain `(ballots, candidates)`
functions with no ScoreGroup/WorldviewElection coupling) BY IMPORT
rather than duplicating them: same honesty rules (malformed ballots
refused by name, ranked mode's Copeland fallback labeled, apply
gated on closed status) apply identically here.

Investigated first (2026-07-14) rather than guessed: DisplayDefinition
(`polariApiServer/displayDefinition.py`) has NO existing field tying a
Display to a ScoreGroup or ScoreConcept — `source_class` is a bare
Polari class name (e.g. 'PotDefinition'), not a group/instance
reference, and DISPLAY_COMPONENT_REGISTRY is a frontend-only Angular
rendering lookup with no backend counterpart. So this module owns the
group↔Display relationship itself (`candidate_display_names_json` on
the vote row) rather than repurposing an unrelated field — the SAME
reason `WorldviewElection.candidate_concept_names_json` exists instead
of forcing Display names through it.

Honesty rules (identical intent to worldview_elections.py):
  - Tallying an OPEN vote is fine (a running count); APPLYING one
    refuses unless closed — results that can still change never
    silently become "the group's endorsed Display".
  - Malformed ballots are refused BY NAME, never guessed.
  - Applying writes onto the GroupDisplayVote row itself (NOT onto
    ScoreGroup — ScoreGroup's schema is shared/stable and a group can
    run several display votes, e.g. one per concept it holds; keeping
    the elected result local to the vote row avoids clobbering that).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (display-vote endpoints)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections import (
    ELECTION_MODES, _by_name, _parse, _rows,
    _tally_approval, _tally_ranked, _tally_sole,
)

VOTE_STATUSES = ('open', 'closed')


class GroupDisplayVote(treeObject):
    """One vote over candidate Displays for a ScoreGroup (optionally
    scoped to one of the group's member concepts)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The ScoreGroup this vote is about.
        group_name: str = '',
        # Optional: which ScoreConcept (if the group holds several)
        # this Display explains; '' = the group's Displays generally.
        concept_name: str = '',
        # Candidate DisplayDefinition names (JSON list) — required;
        # unlike WorldviewElection there's no "group's members" default
        # to fall back to (a group's members are worldview CONCEPTS,
        # not Displays).
        candidate_display_names_json: str = '[]',
        # ELECTION_MODES entry (approval/sole/ranked-condorcet) —
        # reuses worldview_elections.py's vocabulary directly.
        mode: str = 'approval',
        # VOTE_STATUSES entry — apply requires 'closed'.
        status: str = 'open',
        opens_date: str = '',
        closes_date: str = '',
        # Written by apply_display_vote() — the winning Display name,
        # '' until applied.
        elected_display_name: str = '',
        # Provenance for elected_display_name — vote-derived weights
        # without lineage are just opinions (same rule as ScoreGroup.
        # weights_provenance).
        elected_provenance: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.group_name = group_name
        self.concept_name = concept_name
        self.candidate_display_names_json = candidate_display_names_json
        self.mode = mode
        self.status = status
        self.opens_date = opens_date
        self.closes_date = closes_date
        self.elected_display_name = elected_display_name
        self.elected_provenance = elected_provenance
        self.provenance_id = provenance_id
        self.notes = notes


class GroupDisplayBallot(treeObject):
    """One contributor's ballot in one GroupDisplayVote — identical
    payload shape to WorldviewBallot (mode-dependent field)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        vote_name: str = '',
        voter: str = '',
        approvals_json: str = '[]',
        sole_choice: str = '',
        ranking_json: str = '[]',
        cast_date: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.vote_name = vote_name
        self.voter = voter
        self.approvals_json = approvals_json
        self.sole_choice = sole_choice
        self.ranking_json = ranking_json
        self.cast_date = cast_date
        self.notes = notes


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


#: Mechanism A demo (Phase 4 of the Democratic Scorecard revamp):
#: the SAME three professional/interest groups from Phase 2's Housing
#: Affordability Context Tree each propose their own explanatory
#: Display for the group's score — a different axis from mechanism B
#: (which votes on term-WEIGHTING worldviews, not on which explanation
#: communicates best). Real, uncontrived approval-vote outcome below.
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

#: A real, uncontrived 5-ballot approval vote (tenant-affordability
#: coalition wins 3/5 approvals — computed by hand when this seed was
#: authored, not staged): each voter approves what they'd actually
#: find persuasive given their own stance from the Phase 2 election.
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
