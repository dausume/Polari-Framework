"""
@module scoring.objects.group_display_vote.GroupDisplayVote

Row class GroupDisplayVote of the scoring module — one class per file (design §7), split
from group_display_vote_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
