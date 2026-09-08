"""
@module mealoptions.objects.affinity.IngredientRole

Row class IngredientRole of the mealoptions module — one class per file (design §7), split
from affinity_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IngredientRole(treeObject):
    """One role a food can play in a dish."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
