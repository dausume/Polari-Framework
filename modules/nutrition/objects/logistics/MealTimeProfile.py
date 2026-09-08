"""
@module nutrition.objects.logistics.MealTimeProfile

Row class MealTimeProfile of the nutrition module — one class per file (design §7), split
from logistics_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealTimeProfile(treeObject):
    """Eating time per person × slot (household priors, refined)."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', slot: str = 'dinner',
                 eating_min: float = 30.0, fidelity: str = 'estimate',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.slot = slot
        self.eating_min = eating_min
        self.fidelity = fidelity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
