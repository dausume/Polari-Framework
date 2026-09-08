"""
@module casting.objects.demold.DemoldPlanDefinition

Row class DemoldPlanDefinition of the casting module — one class per file (design §7), split
from demold_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from casting.objects.demold._shared import DEMOLD_METHODS

class DemoldPlanDefinition(treeObject):
    """A derived demold verdict for one mold — method, parting
    result, gates. Re-planning reconverges (derived-row rule)."""

    @treeObjectInit
    def __init__(self, name: str = '', mold_ref: str = '',
                 method: str = 'mechanical',
                 parting_json: str = '{}', gates_json: str = '[]',
                 release_coating_required: bool = False,
                 verdict: str = '', is_prior: bool = True,
                 notes: str = '', provenance_id: str = '',
                 manager=None):
        self.name = name
        self.mold_ref = mold_ref
        self.method = (method if method in DEMOLD_METHODS
                       else 'mechanical')
        self.parting_json = parting_json
        self.gates_json = gates_json
        self.release_coating_required = release_coating_required
        self.verdict = verdict
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
