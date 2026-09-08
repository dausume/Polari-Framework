"""
@cross-cutting
@module scoring.group_display_vote_basis
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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/group_display_vote/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections_basis import (
    ELECTION_MODES, _by_name, _parse, _rows,
    _tally_approval, _tally_ranked, _tally_sole,
)

from scoring.objects.group_display_vote._shared import SEED_GROUP_DISPLAYS, SEED_GROUP_DISPLAY_BALLOTS, SEED_GROUP_DISPLAY_VOTES, VOTE_STATUSES, _text_display, apply_display_vote, tally_display_vote  # noqa: F401
from scoring.objects.group_display_vote.GroupDisplayVote import GroupDisplayVote  # noqa: F401
from scoring.objects.group_display_vote.GroupDisplayBallot import GroupDisplayBallot  # noqa: F401
