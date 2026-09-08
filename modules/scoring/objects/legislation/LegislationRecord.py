"""
@module scoring.objects.legislation.LegislationRecord

Row class LegislationRecord of the scoring module — one class per file (design §7), split
from legislation_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LegislationRecord(treeObject):
    """One piece of legislation — API-retrieved or hand-entered,
    the entry_mode flag says which, honestly."""

    @treeObjectInit
    def __init__(self, name: str = '', bill_id: str = '',
                 title: str = '',
                 jurisdiction_subject_name: str = '',
                 legislature: str = '',
                 status: str = 'introduced',
                 # The bill's STATED topic — the germaneness
                 # baseline every provision is read against.
                 declared_subject: str = '',
                 text_url: str = '',
                 # WHO WROTE IT: JSON list of {kind, name,
                 # evidence_url} — multi-author by design.
                 drafted_by_json: str = '[]',
                 entry_mode: str = 'manual',
                 # GovSource / legal-source name it came from ('').
                 source_name: str = '',
                 provenance_id: str = '',
                 retrieved_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.bill_id = bill_id
        self.title = title
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.legislature = legislature
        self.status = status
        self.declared_subject = declared_subject
        self.text_url = text_url
        self.drafted_by_json = drafted_by_json
        self.entry_mode = entry_mode
        self.source_name = source_name
        self.provenance_id = provenance_id
        self.retrieved_at = retrieved_at
        self.notes = notes
