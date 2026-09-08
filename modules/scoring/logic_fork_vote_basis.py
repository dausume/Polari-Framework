"""
@cross-cutting
@module scoring.logic_fork_vote_basis
@tags @xc:bindings

Logic-fork criterion votes — mechanism C of the Democratic Scorecard
revamp (Dustin 2026-07-14): a decision PROCEDURE (a logic diagram —
e.g. a sentencing framework) has named forks (decision points, the
diamond/if-else steps). At any ONE fork, different groups can propose
DIFFERENT CRITERIA for how that fork decides — not a whole competing
procedure, just an alternate condition for ONE existing decision
point. People vote on which criterion at that fork is most valid;
applying records the winner with provenance.

Dustin's own worked example (verbatim intent, not paraphrased away):
a repeat-offense sentencing framework's fork might default to "is
this a repeat offender?" — a proposed ALTERNATE criterion for that
SAME fork could instead be "likelihood that reform actually lasts a
lifetime under their context." Both are real, named, votable
LogicForkCriterion rows for the SAME fork; the vote decides which one
that fork should use to steer sentencing outcomes.

Distinct from mechanism A (`group_display_vote.py` — vote on which
Display best EXPLAINS a score) and mechanism B (`worldview_elections.py`
— vote on which whole ScoreConcept/term-weighting a group reads by):
mechanism C votes at FORK granularity, inside an otherwise-shared
decision procedure, not at whole-object granularity. Reuses
`worldview_elections.py`'s tally functions BY IMPORT — same reason
`group_display_vote.py` does: the tally math (`_tally_approval`/
`_tally_sole`/`_tally_ranked`) is a plain `(ballots, candidates)`
function with zero coupling to what a "candidate" represents.

Scope note (honest, not overclaimed): this module votes on and
RECORDS the winning criterion (name + description + provenance) for
one fork. It does NOT auto-rewrite a live `SolutionDefinition`'s
no-code graph JSON to swap the winning criterion's condition config
into the running `ConditionalChain` node — that would mean parsing
and mutating `polariNoCode/SolutionExecutionEngine.py`'s internal
`boundObjectFieldValues` schema, a real, separate, riskier piece of
engineering not attempted here. `resolved_procedure_summary()` gives
a human-readable "here's what the procedure looks like now" report
instead — real composition-into-an-executable-graph is a documented
follow-up, not silently assumed done.

Honesty rules (identical intent to worldview_elections.py /
group_display_vote.py):
  - Tallying an OPEN vote is fine; APPLYING refuses unless closed.
  - Malformed ballots refused BY NAME, never guessed.
  - Applying writes onto the LogicForkVote row itself (not onto the
    LogicForkCriterion rows — a fork can be re-voted, and each
    criterion may be a candidate in several different votes/contexts).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (logic-fork-vote endpoints)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/logic_fork_vote/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections_basis import (
    ELECTION_MODES, _by_name, _parse, _rows,
    _tally_approval, _tally_ranked, _tally_sole,
)

from scoring.objects.logic_fork_vote._shared import SEED_DECISION_PROCEDURE_EDGES, SEED_LOGIC_FORK_BALLOTS, SEED_LOGIC_FORK_CONTRIBUTORS, SEED_LOGIC_FORK_CRITERIA, SEED_LOGIC_FORK_VOTES, VOTE_STATUSES, apply_logic_fork_vote, resolved_procedure_summary, tally_logic_fork_vote  # noqa: F401
from scoring.objects.logic_fork_vote.LogicForkCriterion import LogicForkCriterion  # noqa: F401
from scoring.objects.logic_fork_vote.LogicForkVote import LogicForkVote  # noqa: F401
from scoring.objects.logic_fork_vote.LogicForkBallot import LogicForkBallot  # noqa: F401
from scoring.objects.logic_fork_vote.DecisionProcedureEdge import DecisionProcedureEdge  # noqa: F401
