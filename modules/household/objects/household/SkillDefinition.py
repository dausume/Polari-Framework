"""
@module household.objects.household.SkillDefinition

Row class SkillDefinition of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SkillDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 is_safety: bool = False, is_prior: bool = True,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.is_safety = is_safety
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
