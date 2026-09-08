"""
@module nutrition.objects.exclusion.FoodAllergenFlag

Row class FoodAllergenFlag of the nutrition module — one class per file (design §7), split
from exclusion_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FoodAllergenFlag(treeObject):
    """One food × one allergen class it contains by identity."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('cheese-cheddar-milk').
        name: str = '',
        food_name: str = '',
        # ALLERGEN_CLASSES entry.
        allergen_class: str = '',
        # why the flag holds ('is a dairy product').
        basis: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.allergen_class = allergen_class
        self.basis = basis
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
