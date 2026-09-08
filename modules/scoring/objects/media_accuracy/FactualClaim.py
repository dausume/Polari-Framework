"""
@module scoring.objects.media_accuracy.FactualClaim

Row class FactualClaim of the scoring module — one class per file (design §7), split
from media_accuracy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FactualClaim(treeObject):
    """One checkable factual statement published by an outlet."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('claim-ledger-texas-lfpr').
        name: str = '',
        display_name: str = '',
        # ScoreSubject (kind 'media-outlet') that published the claim.
        outlet_name: str = '',
        # The statement as published, verbatim.
        statement: str = '',
        # The checkable payload: which measurement the statement is
        # about, in the scoring vocabulary.
        term_name: str = '',
        subject_name: str = '',
        context_names_json: str = '[]',
        claimed_value: float = None,
        claim_date: str = '',
        # The article itself (MediaEvidence names, JSON list).
        evidence_names_json: str = '[]',
        # Contributor who logged the claim.
        contributed_by: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.outlet_name = outlet_name
        self.statement = statement
        self.term_name = term_name
        self.subject_name = subject_name
        self.context_names_json = context_names_json
        self.claimed_value = claimed_value
        self.claim_date = claim_date
        self.evidence_names_json = evidence_names_json
        self.contributed_by = contributed_by
        self.provenance_id = provenance_id
        self.notes = notes
