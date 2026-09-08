"""
@module scoring.objects.legislation.LegislationProvision

Row class LegislationProvision of the scoring module — one class per file (design §7), split
from legislation_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LegislationProvision(treeObject):
    """One part of a bill — the cram-visibility unit: its own topic,
    its own contributors."""

    @treeObjectInit
    def __init__(self, name: str = '', legislation_name: str = '',
                 section_ref: str = '',
                 summary: str = '',
                 # The topic THIS provision actually addresses.
                 issue_name: str = '',
                 # WHAT LOBBIES OR OTHER GROUPS CONTRIBUTED THIS
                 # PART: JSON list of {kind, name, evidence_url}.
                 contributed_by_json: str = '[]',
                 # '' = timing honestly unknown.
                 added_at: str = '',
                 germane_note: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.legislation_name = legislation_name
        self.section_ref = section_ref
        self.summary = summary
        self.issue_name = issue_name
        self.contributed_by_json = contributed_by_json
        self.added_at = added_at
        self.germane_note = germane_note
        self.notes = notes
