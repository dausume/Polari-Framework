"""
@module scoring.objects.term_competition.TermScopeVote

Row class TermScopeVote of the scoring module — one class per file (design §7), split
from term_competition_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TermScopeVote(treeObject):
    """One voting unit's stance on whether a term MEETS CRITERIA for
    consideration in a Score's term scope."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        concept_name: str = '',
        term_name: str = '',
        voter: str = '',
        # '' = the voter acts as an individual unit.
        on_behalf_of_group: str = '',
        eligible: bool = True,
        rationale: str = '',
        cast_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.concept_name = concept_name
        self.term_name = term_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.eligible = eligible
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes
