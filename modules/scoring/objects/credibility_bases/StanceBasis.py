"""
@module scoring.objects.credibility_bases.StanceBasis

Row class StanceBasis of the scoring module — one class per file (design §7), split
from credibility_bases_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StanceBasis(treeObject):
    """THE LINK: one stance (rebuttal / vote / relation assertion)
    declared to be spoken FROM one CredibilityClaim. Additive — the
    stance rows themselves are never edited."""

    @treeObjectInit
    def __init__(self, name: str = '', stance_kind: str = '',
                 stance_name: str = '', claim_name: str = '',
                 attached_at: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.stance_kind = stance_kind
        self.stance_name = stance_name
        self.claim_name = claim_name
        self.attached_at = attached_at
        self.notes = notes
