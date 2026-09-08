"""
@module household.objects.household.SafetyRule

Row class SafetyRule of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SafetyRule(treeObject):
    """hazard tag → the safety level required, else supervised."""

    @treeObjectInit
    def __init__(self, name: str = '', hazard_tag: str = '', skill_name: str = 'kitchen-safety',
                 required_level: str = 'intermediate',
                 below_floor: str = 'supervised',   # supervised | unassigned
                 rule_text: str = '', citation: str = '', confidence: str = 'transcribed',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.hazard_tag = hazard_tag
        self.skill_name = skill_name
        self.required_level = required_level
        self.below_floor = below_floor
        self.rule_text = rule_text
        self.citation = citation
        self.confidence = confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
