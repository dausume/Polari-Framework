"""
@module scoring.objects.credibility_bases.ClaimAttestation

Row class ClaimAttestation of the scoring module — one class per file (design §7), split
from credibility_bases_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ClaimAttestation(treeObject):
    """One unit's attestation (or dispute) of a claim. Rows are
    immutable; the latest per unit counts (the house voting
    idiom)."""

    @treeObjectInit
    def __init__(self, name: str = '', claim_name: str = '',
                 attester: str = '', on_behalf_of_group: str = '',
                 supports: bool = True, rationale: str = '',
                 cast_at: str = '', notes: str = '', manager=None):
        self.name = name
        self.claim_name = claim_name
        self.attester = attester
        self.on_behalf_of_group = on_behalf_of_group
        self.supports = supports
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes
