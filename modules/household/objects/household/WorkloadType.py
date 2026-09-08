"""
@module household.objects.household.WorkloadType

Row class WorkloadType of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WorkloadType(treeObject):
    """The distinct kinds of meal-prep work (authorable)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 default_skills_json: str = '[]', is_prior: bool = True,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.default_skills_json = default_skills_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
