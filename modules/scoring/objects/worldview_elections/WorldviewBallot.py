"""
@module scoring.objects.worldview_elections.WorldviewBallot

Row class WorldviewBallot of the scoring module — one class per file (design §7), split
from worldview_elections_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WorldviewBallot(treeObject):
    """One contributor's ballot in one election. Which payload field
    counts depends on the election's mode."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        election_name: str = '',
        # Contributor name — ballots are accountable (pseudonyms ok).
        voter: str = '',
        # approval mode: JSON list of approved candidate names.
        approvals_json: str = '[]',
        # sole mode: exactly one candidate name.
        sole_choice: str = '',
        # ranked-condorcet mode: JSON list, most-preferred first;
        # unranked candidates count below every ranked one.
        ranking_json: str = '[]',
        cast_date: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.election_name = election_name
        self.voter = voter
        self.approvals_json = approvals_json
        self.sole_choice = sole_choice
        self.ranking_json = ranking_json
        self.cast_date = cast_date
        self.notes = notes
