"""
@module scoring.objects.evidence.MediaEvidence

Row class MediaEvidence of the scoring module — one class per file (design §7), split
from evidence_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MediaEvidence(treeObject):
    """One citable proof item."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('evidence-fair-wage-hearing').
        name: str = '',
        display_name: str = '',
        # EVIDENCE_KINDS entry.
        kind: str = 'document',
        url: str = '',
        # Optional objectRef to a stored file/object (JSON).
        file_ref_json: str = '',
        # The cited passage itself.
        quote: str = '',
        # Optional span into the source (JSON {'start','end'}).
        span_json: str = '',
        # ISO date the evidence was captured/archived.
        captured_date: str = '',
        # EVIDENCE_GRADES entry — weight comes from EvidencePolicy.
        evidence_grade: str = 'secondhand',
        # Contributor name (scoring.contributors_basis).
        submitted_by: str = '',
        # ScoreSubject name (kind 'media-outlet') that PUBLISHED this
        # item — ties every cited article to an accountable outlet
        # (scr-15); '' = not outlet-published (official records…).
        outlet_name: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.url = url
        self.file_ref_json = file_ref_json
        self.quote = quote
        self.span_json = span_json
        self.captured_date = captured_date
        self.evidence_grade = evidence_grade
        self.submitted_by = submitted_by
        self.outlet_name = outlet_name
        self.provenance_id = provenance_id
        self.notes = notes
