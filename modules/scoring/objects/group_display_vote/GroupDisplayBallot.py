"""
@module scoring.objects.group_display_vote.GroupDisplayBallot

Row class GroupDisplayBallot of the scoring module — one class per file (design §7), split
from group_display_vote_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
