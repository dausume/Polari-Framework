"""
@module mealoptions.objects.affinity.FoodRole

Row class FoodRole of the mealoptions module — one class per file (design §7), split
from affinity_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FoodRole(treeObject):
    """One (food, role) membership."""

    @treeObjectInit
    def __init__(self, name: str = '', food_name: str = '',
                 role_name: str = '',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.food_name = food_name
        self.role_name = role_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
