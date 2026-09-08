"""
@module scoring.objects.venue_patterns.VenueMismatchPattern

Row class VenueMismatchPattern of the scoring module — one class per file (design §7), split
from venue_patterns_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VenueMismatchPattern(treeObject):
    """One catalog entry — a contestable framing, editable/votable
    content, never baked-in judgment."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 sequence_rule_json: str = '{}',
                 severity_note: str = '', proposed_by: str = '',
                 enabled: bool = True, notes: str = '',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.sequence_rule_json = sequence_rule_json
        self.severity_note = severity_note
        self.proposed_by = proposed_by
        self.enabled = enabled
        self.notes = notes
