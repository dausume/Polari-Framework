"""
@module pspp.objects.claims.ValidationClaim

Row class ValidationClaim of the pspp module — one class per file (design §7), split
from claims_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ValidationClaim(treeObject):
    """A validation statement ABOUT other claims/states ('the L1
    elastic claim matched the 7-day compression test within 8%') —
    the evidence that upgrades a claim's standing."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject_state_key: str = '',
        # The claim row this validates ('' = validates the state
        # itself, e.g. 'phase identity confirmed by XRD').
        validated_claim_name: str = '',
        # 'confirmed' | 'contradicted' | 'inconclusive'
        verdict: str = 'inconclusive',
        statement: str = '',
        evidence_method: str = 'measured',
        assumptions_json: str = '[]',
        source_execution_id: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_state_key = subject_state_key
        self.validated_claim_name = validated_claim_name
        self.verdict = verdict
        self.statement = statement
        self.evidence_method = evidence_method
        self.assumptions_json = assumptions_json
        self.source_execution_id = source_execution_id
        self.provenance_id = provenance_id
        self.notes = notes
