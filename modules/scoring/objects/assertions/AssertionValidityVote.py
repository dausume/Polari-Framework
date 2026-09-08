"""
@module scoring.objects.assertions.AssertionValidityVote

Row class AssertionValidityVote of the scoring module — one class per file (design §7), split
from assertions_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AssertionValidityVote(treeObject):
    """One contributor's vote, in one round, on one assertion's
    validity (the scorecard's multi-round design)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        assertion_name: str = '',
        # Contributor name — votes are accountable too.
        voter: str = '',
        round_number: int = 1,
        # 'valid' | 'invalid' | 'abstain'.
        vote: str = 'abstain',
        rationale: str = '',
        # Optional counter-/supporting evidence (JSON name list).
        evidence_names_json: str = '[]',
        cast_date: str = '',
        manager=None,
    ):
        self.name = name
        self.assertion_name = assertion_name
        self.voter = voter
        self.round_number = round_number
        self.vote = vote
        self.rationale = rationale
        self.evidence_names_json = evidence_names_json
        self.cast_date = cast_date
