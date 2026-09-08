"""
@module scoring.objects.term_proofs.ProofRebuttal

Row class ProofRebuttal of the scoring module — one class per file (design §7), split
from term_proofs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProofRebuttal(treeObject):
    """A structured answer to a proof: challenge its DATA, its
    FRAMING, or its GENERALITY. Standing open rebuttals change how
    the proof reads."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_name: str = '',
                 challenge_kind: str = '', rationale: str = '',
                 demonstration_json: str = '[]',
                 status: str = 'open', raised_by: str = '',
                 on_behalf_of_group: str = '', raised_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_name = proof_name
        self.challenge_kind = challenge_kind
        self.rationale = rationale
        self.demonstration_json = demonstration_json
        self.status = status
        self.raised_by = raised_by
        self.on_behalf_of_group = on_behalf_of_group
        self.raised_at = raised_at
        self.notes = notes
