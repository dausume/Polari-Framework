"""
@module nutrition.objects.workflow.MethodPreference

Row class MethodPreference of the nutrition module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MethodPreference(treeObject):
    """A stated pin — preference beats time-optimality."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 household_name: str = '', task_kind: str = '',
                 method_name: str = '',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.person_name = person_name
        self.household_name = household_name
        self.task_kind = task_kind
        self.method_name = method_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
