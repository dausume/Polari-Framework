"""
@module household.objects.household.MethodSkillRequirement

Row class MethodSkillRequirement of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MethodSkillRequirement(treeObject):
    """Skills + safety a StepMethod needs — a row beside the method,
    so "adding skills needed for particular steps" is a row edit."""

    @treeObjectInit
    def __init__(self, name: str = '', method_name: str = '', task_kind: str = '',
                 # [{"skill": "knife-work", "floor": "intermediate"}]
                 skills_json: str = '[]',
                 # minutes the step needs to be done SAFELY at any skill.
                 safety_floor_min: float = 0.0,
                 hazard_tags_json: str = '[]',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.method_name = method_name
        self.task_kind = task_kind
        self.skills_json = skills_json
        self.safety_floor_min = safety_floor_min
        self.hazard_tags_json = hazard_tags_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
