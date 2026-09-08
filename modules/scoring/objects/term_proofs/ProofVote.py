"""
@module scoring.objects.term_proofs.ProofVote

Row class ProofVote of the scoring module — one class per file (design §7), split
from term_proofs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProofVote(treeObject):
    """One unit's vote on a proof — vote_kind 'validity' (is the
    demonstration correct) or 'comprehension' (which presentation
    gives the more accurate impression). Rows are immutable; the
    latest per (unit, kind) counts."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_name: str = '',
                 voter: str = '', on_behalf_of_group: str = '',
                 vote_kind: str = '', choice: str = '',
                 rationale: str = '', cast_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_name = proof_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.vote_kind = vote_kind
        self.choice = choice
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes
