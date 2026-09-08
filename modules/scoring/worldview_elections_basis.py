"""
@cross-cutting
@module scoring.worldview_elections_basis
@tags @xc:bindings

Worldview elections (scr-8) — the scorecard's designed-never-built
WorldviewVote (approval / sole / ranked-condorcet), tallied in
Polari. Election close → tally → a ScoreGroup's member worldviews
get VOTE-DERIVED weights instead of hand-set ones (the weights feed
group aggregation, so an elected definition is what the group
actually reads by).

Honesty rules:
  - Tallying an OPEN election is fine (a running count); APPLYING
    one refuses — results that can still change never silently
    become the group's definition. Close first (an explicit edit).
  - Malformed ballots are refused BY NAME, never guessed.
  - Ranked mode seeks a Condorcet winner; when none exists the
    Copeland fallback is LABELED, pairwise ties included.
  - Elected weights carry provenance onto the group row
    (weights_provenance) — weights without lineage are opinions.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (elections endpoints)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/worldview_elections/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.worldview_elections._shared import ELECTION_MODES, ELECTION_STATUSES, SEED_ASSEMBLY_GROUPS, SEED_WORLDVIEW_BALLOTS, SEED_WORLDVIEW_ELECTIONS, _by_name, _candidates, _parse, _rows, _tally_approval, _tally_ranked, _tally_sole, apply_election, tally_election  # noqa: F401
from scoring.objects.worldview_elections.WorldviewElection import WorldviewElection  # noqa: F401
from scoring.objects.worldview_elections.WorldviewBallot import WorldviewBallot  # noqa: F401
