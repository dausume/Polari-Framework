"""
@module scoring.objects.policy_votes.PolicyVote

Row class PolicyVote of the scoring module — one class per file (design §7), split
from policy_votes_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PolicyVote(treeObject):
    """One recorded vote: politician × policy."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('vote-rivera-fair-wage-act').
        name: str = '',
        # ScoreSubject names (kind 'politician' / kind 'policy').
        politician_name: str = '',
        policy_name: str = '',
        # VOTE_KINDS entry.
        vote: str = 'abstain',
        # ISO date — politician scores are time-scoped through this
        # (scr-4 frames).
        vote_date: str = '',
        chamber: str = '',
        session: str = '',
        source: str = '',
        provenance_id: str = '',
        # Contributor who ingested/recorded this vote.
        contributed_by: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.politician_name = politician_name
        self.policy_name = policy_name
        self.vote = vote
        self.vote_date = vote_date
        self.chamber = chamber
        self.session = session
        self.source = source
        self.provenance_id = provenance_id
        self.contributed_by = contributed_by
        self.notes = notes
